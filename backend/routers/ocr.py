import json
import traceback
import httpx
from fastapi import APIRouter, HTTPException, File, UploadFile, Form

from schemas import PreprocessRequest, PreprocessResponse, OCRResponse
from services.orchestrator_service import process_image, execute_ocr_pipeline

router = APIRouter(prefix="/api")

@router.post("/preprocess", response_model=PreprocessResponse)
async def api_preprocess(request: PreprocessRequest):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            proc_data = await process_image(client, request.image, request.config.model_dump())
            
        return {
            "success": True,
            "processed_image": proc_data["image"],
            "metadata": proc_data["meta"]
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Preprocessing error: {str(e)}")

@router.post("/ocr", response_model=OCRResponse)
async def api_ocr(
    file: UploadFile = File(...),
    config: str = Form(...),
    engine: str = Form("easyocr"),
    languages: str = Form("[\"vi\", \"en\"]"),
    merge_boxes: bool = Form(True)
):
    try:
        file_bytes = await file.read()
        config_dict = json.loads(config)
        languages_list = json.loads(languages)
        
        return await execute_ocr_pipeline(
            file_bytes=file_bytes,
            filename=file.filename,
            content_type=file.content_type,
            config_dict=config_dict,
            engine=engine,
            languages_list=languages_list,
            merge_boxes=merge_boxes
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"OCR Orchestrator execution failed: {str(e)}"
        )
