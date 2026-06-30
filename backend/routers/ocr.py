import json
import logging
from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Request

from schemas import PreprocessRequest, PreprocessResponse, OCRResponse
from services.orchestrator_service import process_image, execute_ocr_pipeline, select_ocr_models
from shared.contracts import ModelSelectionRequest
from exceptions import (
    ImageProcessorError,
    OCRServiceError,
    UnsupportedEngineError,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.post("/preprocess", response_model=PreprocessResponse)
async def api_preprocess(request_data: PreprocessRequest, request: Request):
    client = request.app.state.http_client
    try:
        proc_data = await process_image(client, request_data.image, request_data.config.model_dump())
        return {
            "success": True,
            "processed_image": proc_data["image"],
            "metadata": proc_data["meta"]
        }
    except ImageProcessorError as e:
        logger.error("Image Processor service error: %s", e)
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error during preprocessing")
        raise HTTPException(status_code=500, detail=f"Preprocessing error: {str(e)}")


@router.post("/ocr", response_model=OCRResponse)
async def api_ocr(
    request: Request,
    file: UploadFile = File(...),
    config: str = Form(...),
    engine: str = Form("easyocr"),
    languages: str = Form("[\"vi\", \"en\"]"),
    merge_boxes: bool = Form(True)
):
    client = request.app.state.http_client
    try:
        file_bytes = await file.read()
        config_dict = json.loads(config)
        languages_list = json.loads(languages)

        return await execute_ocr_pipeline(
            client=client,
            file_bytes=file_bytes,
            filename=file.filename,
            content_type=file.content_type,
            config_dict=config_dict,
            engine=engine,
            languages_list=languages_list,
            merge_boxes=merge_boxes
        )
    except UnsupportedEngineError as e:
        logger.warning("Unsupported OCR engine requested: %s", e.engine)
        raise HTTPException(status_code=400, detail=str(e))
    except (ImageProcessorError, OCRServiceError) as e:
        logger.error("Upstream service error: %s", e)
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in OCR pipeline")
        raise HTTPException(
            status_code=500,
            detail=f"OCR Orchestrator execution failed: {str(e)}"
        )


@router.post("/models/select")
async def api_select_models(request_data: ModelSelectionRequest, request: Request):
    client = request.app.state.http_client
    try:
        return await select_ocr_models(
            client=client,
            engine=request_data.engine,
            languages_list=request_data.languages,
        )
    except UnsupportedEngineError as e:
        logger.warning("Unsupported OCR engine requested for model selection: %s", e.engine)
        raise HTTPException(status_code=400, detail=str(e))
    except OCRServiceError as e:
        logger.error("Model selection service error: %s", e)
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error during model selection")
        raise HTTPException(status_code=500, detail=f"Model selection failed: {str(e)}")
