import time
import base64
import uuid
import httpx
from const import IMAGE_PROCESSOR_URL, ENGINE_ROUTING_MAP
from exceptions import ImageProcessorError, OCRServiceError, UnsupportedEngineError
from services.supabase_service import upload_to_supabase
from utils.ocr_utils import merge_adjacent_words


async def process_image(client: httpx.AsyncClient, base64_image: str, config_dict: dict) -> dict:
    """Calls the Image Processor microservice to preprocess an image."""
    proc_resp = await client.post(
        f"{IMAGE_PROCESSOR_URL}/api/process",
        json={
            "image": base64_image,
            "config": config_dict
        }
    )
    if proc_resp.status_code != 200:
        raise ImageProcessorError(
            status_code=proc_resp.status_code,
            detail=proc_resp.text
        )
    return proc_resp.json()


async def run_ocr_engine(client: httpx.AsyncClient, engine: str, base64_image: str, languages_list: list) -> dict:
    """Routes an OCR request to the appropriate OCR microservice."""
    base_url = ENGINE_ROUTING_MAP.get(engine)
    if not base_url:
        raise UnsupportedEngineError(engine=engine)

    target_service_url = f"{base_url}/api/ocr"
    resp = await client.post(
        target_service_url,
        json={
            "image": base64_image,
            "engine": engine,
            "languages": languages_list
        }
    )

    if resp.status_code != 200:
        raise OCRServiceError(
            status_code=resp.status_code,
            detail=resp.text
        )
    return resp.json()


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

    original_base64 = f"data:{content_type};base64," + base64.b64encode(file_bytes).decode('utf-8')
    ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'jpg'

    # Upload original image to Supabase
    orig_filename = f"original_{uuid.uuid4().hex}.{ext}"
    original_url = await upload_to_supabase(client, file_bytes, orig_filename, content_type)

    # 1. Route to Image Processor
    proc_data = await process_image(client, original_base64, config_dict)
    processed_base64 = proc_data["image"]
    meta = proc_data["meta"]

    # Ensure processed image has data URI prefix for frontend display
    if not processed_base64.startswith("data:"):
        processed_base64 = f"data:image/jpeg;base64,{processed_base64}"

    # 2. Route to OCR Microservice
    resp_data = await run_ocr_engine(client, engine, processed_base64, languages_list)

    words = resp_data.get("words", [])
    preprocessed_image = resp_data.get("preprocessed_image")
    detected_tables = resp_data.get("detected_tables", [])

    # Extract real GPU status from the OCR service response
    gpu_active = resp_data.get("gpu_accelerated", False)

    elapsed = time.time() - start_time

    # Decide which image to use for the frontend bounding box display
    if preprocessed_image:
        final_display_base64 = preprocessed_image
        final_filename = f"unwarped_{uuid.uuid4().hex}.jpg"
    else:
        final_display_base64 = processed_base64
        final_filename = f"processed_{uuid.uuid4().hex}.jpg"
        
    # Upload the chosen final image to Supabase ONCE
    try:
        final_bytes = base64.b64decode(final_display_base64.split(",", 1)[-1])
        processed_url = await upload_to_supabase(client, final_bytes, final_filename, "image/jpeg")
    except Exception as e:
        processed_url = None

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
            "detected_tables": detected_tables
        },
        "engine": engine,
        "execution_time_seconds": round(elapsed, 3),
        "gpu_accelerated": gpu_active
    }

