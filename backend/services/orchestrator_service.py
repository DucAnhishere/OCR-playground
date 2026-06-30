import base64
import asyncio
import logging
import time
import uuid

import httpx

from const import PADDLE_SERVICE_URL, PYTORCH_SERVICE_URL, IMAGE_PROCESSOR_URL, ENGINE_ROUTING_MAP, OCR_TIMEOUT_SECONDS, PREPROCESS_TIMEOUT_SECONDS
from exceptions import ImageProcessorError, OCRServiceError, UnsupportedEngineError
from services.supabase_service import is_storage_configured, upload_to_supabase
from shared.contracts import ModelSelectionRequest, ModelSelectionResponse, OCRServiceRequest, OCRServiceResponse
from utils.ocr_utils import merge_adjacent_words

logger = logging.getLogger(__name__)


def model_selection_targets(engine: str) -> list[tuple[str, str]]:
    if engine == "easyocr":
        return [(PYTORCH_SERVICE_URL, "easyocr"), (PADDLE_SERVICE_URL, "easyocr")]
    if engine == "vietocr":
        return [(PADDLE_SERVICE_URL, "paddle_layout"), (PYTORCH_SERVICE_URL, "vietocr")]
    if engine == "paddleocr":
        return [(PADDLE_SERVICE_URL, "paddleocr"), (PYTORCH_SERVICE_URL, "paddleocr")]
    if engine == "paddle_structure":
        return [(PADDLE_SERVICE_URL, "paddle_structure"), (PYTORCH_SERVICE_URL, "paddle_structure")]
    raise UnsupportedEngineError(engine=engine)


async def select_ocr_models(client: httpx.AsyncClient, engine: str, languages_list: list) -> dict:
    start_time = time.time()

    async def select_service_model(service_url: str, target_engine: str) -> ModelSelectionResponse:
        request_payload = ModelSelectionRequest(engine=target_engine, languages=languages_list)
        try:
            resp = await client.post(
                f"{service_url}/api/models/select",
                json=request_payload.model_dump(),
                timeout=OCR_TIMEOUT_SECONDS,
            )
        except httpx.TimeoutException as e:
            raise OCRServiceError(
                status_code=504,
                detail=f"Model selection timed out for {target_engine} at {service_url}: {e}",
            )
        except httpx.RemoteProtocolError as e:
            raise OCRServiceError(
                status_code=502,
                detail=f"Model selection service disconnected for {target_engine} at {service_url}: {e}",
            )
        except httpx.HTTPError as e:
            raise OCRServiceError(
                status_code=502,
                detail=f"Could not call model selection for {target_engine} at {service_url}: {e}",
            )
        if resp.status_code != 200:
            raise OCRServiceError(status_code=resp.status_code, detail=resp.text)
        try:
            selection = ModelSelectionResponse.model_validate(resp.json())
        except Exception as e:
            raise OCRServiceError(
                status_code=502,
                detail=f"Invalid model selection response from {service_url}: {e}",
            )
        return selection

    selections = await asyncio.gather(
        *[
            select_service_model(service_url, target_engine)
            for service_url, target_engine in model_selection_targets(engine)
        ]
    )
    warnings = [warning for selection in selections for warning in selection.warnings]
    elapsed = round(time.time() - start_time, 3)
    logger.info("Model selection for engine=%s completed in %.3fs", engine, elapsed)

    return {
        "success": True,
        "engine": engine,
        "services": [selection.model_dump() for selection in selections],
        "model_selection_seconds": elapsed,
        "warnings": warnings,
    }


async def process_image(client: httpx.AsyncClient, base64_image: str, config_dict: dict) -> dict:
    """Calls the Image Processor microservice to preprocess an image."""
    proc_resp = await client.post(
        f"{IMAGE_PROCESSOR_URL}/api/process",
        json={
            "image": base64_image,
            "config": config_dict
        }
        ,
        timeout=PREPROCESS_TIMEOUT_SECONDS,
    )
    if proc_resp.status_code != 200:
        raise ImageProcessorError(
            status_code=proc_resp.status_code,
            detail=proc_resp.text
        )
    return proc_resp.json()


async def run_ocr_engine(
    client: httpx.AsyncClient,
    engine: str,
    base64_image: str,
    languages_list: list,
    layout_words: list[dict] | None = None,
) -> OCRServiceResponse:
    """Routes an OCR request to the appropriate OCR microservice."""
    base_url = ENGINE_ROUTING_MAP.get(engine)
    if not base_url:
        raise UnsupportedEngineError(engine=engine)

    request_payload = OCRServiceRequest(
        image=base64_image,
        engine=engine,
        languages=languages_list,
        layout_words=layout_words,
    )
    target_service_url = f"{base_url}/api/ocr"
    try:
        resp = await client.post(
            target_service_url,
            json=request_payload.model_dump(),
            timeout=OCR_TIMEOUT_SECONDS,
        )
    except httpx.TimeoutException as e:
        raise OCRServiceError(
            status_code=504,
            detail=f"{engine} service timed out after {OCR_TIMEOUT_SECONDS}s: {e}",
        )
    except httpx.RemoteProtocolError as e:
        raise OCRServiceError(
            status_code=502,
            detail=f"{engine} service disconnected before sending a response: {e}",
        )
    except httpx.HTTPError as e:
        raise OCRServiceError(
            status_code=502,
            detail=f"Could not call {engine} service at {target_service_url}: {e}",
        )

    if resp.status_code != 200:
        raise OCRServiceError(
            status_code=resp.status_code,
            detail=resp.text
        )
    try:
        return OCRServiceResponse.model_validate(resp.json())
    except Exception as e:
        raise OCRServiceError(
            status_code=502,
            detail=f"Invalid OCR service response from {engine}: {e}",
        )


async def run_ocr_workflow(
    client: httpx.AsyncClient,
    engine: str,
    processed_base64: str,
    languages_list: list,
) -> OCRServiceResponse:
    if engine != "vietocr":
        return await run_ocr_engine(client, engine, processed_base64, languages_list)

    layout_response = await run_ocr_engine(client, "paddle_layout", processed_base64, languages_list)
    layout_words = [word.model_dump() for word in layout_response.words]
    if not layout_words:
        return OCRServiceResponse(
            words=[],
            preprocessed_image=layout_response.preprocessed_image,
            detected_tables=layout_response.detected_tables,
            gpu_accelerated=layout_response.gpu_accelerated,
            warnings=[
                *layout_response.warnings,
                "Paddle layout did not detect text regions; VietOCR recognition was skipped.",
            ],
        )
    recognition_image = layout_response.preprocessed_image or processed_base64
    viet_response = await run_ocr_engine(
        client,
        "vietocr",
        recognition_image,
        languages_list,
        layout_words=layout_words,
    )

    return OCRServiceResponse(
        words=viet_response.words,
        preprocessed_image=layout_response.preprocessed_image or viet_response.preprocessed_image,
        detected_tables=layout_response.detected_tables or viet_response.detected_tables,
        gpu_accelerated=viet_response.gpu_accelerated,
        warnings=[*layout_response.warnings, *viet_response.warnings],
    )


async def upload_best_effort(
    client: httpx.AsyncClient,
    file_bytes: bytes,
    filename: str,
    content_type: str,
    warnings: list[str],
) -> tuple[str | None, str]:
    if not is_storage_configured():
        warnings.append("Supabase storage is disabled or not configured; using base64 fallback.")
        return None, "disabled"

    try:
        return await upload_to_supabase(client, file_bytes, filename, content_type), "uploaded"
    except Exception as e:
        logger.warning("Supabase upload failed for %s: %s", filename, e)
        warnings.append(f"Supabase upload failed for {filename}; using base64 fallback.")
        return None, "failed"


async def execute_ocr_pipeline(
    client: httpx.AsyncClient,
    file_bytes: bytes,
    filename: str,
    content_type: str,
    config_dict: dict,
    engine: str,
    languages_list: list,
    merge_boxes: bool
) -> dict:
    """
    Orchestrates the full OCR pipeline:
    1. Upload the original image to Supabase.
    2. Preprocess the image via the Image Processor service.
    3. Upload the preprocessed image to Supabase.
    4. Run OCR via the appropriate engine microservice.
    5. Merge adjacent word bounding boxes (optional).
    """
    start_time = time.time()
    warnings = []

    if engine not in ENGINE_ROUTING_MAP:
        raise UnsupportedEngineError(engine=engine)

    original_base64 = f"data:{content_type};base64," + base64.b64encode(file_bytes).decode('utf-8')
    ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'jpg'

    # Upload original image to Supabase as a best-effort side effect.
    orig_filename = f"original_{uuid.uuid4().hex}.{ext}"
    original_url, original_storage_status = await upload_best_effort(
        client, file_bytes, orig_filename, content_type, warnings
    )

    # 1. Route to Image Processor
    proc_data = await process_image(client, original_base64, config_dict)
    processed_base64 = proc_data["image"]
    meta = proc_data["meta"]

    # Ensure processed image has data URI prefix for frontend display
    if not processed_base64.startswith("data:"):
        processed_base64 = f"data:image/jpeg;base64,{processed_base64}"

    # 2. Run the OCR workflow. BFF owns multi-service orchestration.
    resp_data = await run_ocr_workflow(client, engine, processed_base64, languages_list)

    words = [word.model_dump() for word in resp_data.words]
    preprocessed_image = resp_data.preprocessed_image
    detected_tables = [table.model_dump() for table in resp_data.detected_tables]
    warnings.extend(resp_data.warnings)

    # Extract real GPU status from the OCR service response
    gpu_active = resp_data.gpu_accelerated

    elapsed = time.time() - start_time

    # Decide which image to use for the frontend bounding box display
    if preprocessed_image:
        final_display_base64 = preprocessed_image
        final_filename = f"unwarped_{uuid.uuid4().hex}.jpg"
    else:
        final_display_base64 = processed_base64
        final_filename = f"processed_{uuid.uuid4().hex}.jpg"
        
    # Upload the chosen final image to Supabase as a best-effort side effect.
    final_bytes = base64.b64decode(final_display_base64.split(",", 1)[-1])
    processed_url, processed_storage_status = await upload_best_effort(
        client, final_bytes, final_filename, "image/jpeg", warnings
    )

    # 3. Perform box merging
    if merge_boxes:
        words = merge_adjacent_words(words)

    return {
        "success": True,
        "preprocessed_image": final_display_base64,  # Legacy fallback for frontend
        "original_image_url": original_url,
        "processed_image_url": processed_url,
        "results": words,
        "metadata": {
            **meta,
            "words_count": len(words),
            "detected_tables": detected_tables,
            "storage_status": "uploaded"
            if original_storage_status == "uploaded" and processed_storage_status == "uploaded"
            else ("disabled" if "disabled" in {original_storage_status, processed_storage_status} else "failed"),
        },
        "engine": engine,
        "execution_time_seconds": round(elapsed, 3),
        "gpu_accelerated": gpu_active,
        "warnings": warnings,
    }
