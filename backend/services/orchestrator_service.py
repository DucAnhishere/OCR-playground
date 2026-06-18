import time
import base64
import uuid
import httpx
from fastapi import HTTPException
from const import IMAGE_PROCESSOR_URL, ENGINE_ROUTING_MAP
from services.supabase_service import upload_to_supabase
from utils.ocr_utils import merge_adjacent_words

async def process_image(client: httpx.AsyncClient, base64_image: str, config_dict: dict):
    proc_resp = await client.post(
        f"{IMAGE_PROCESSOR_URL}/api/process",
        json={
            "image": base64_image,
            "config": config_dict
        }
    )
    if proc_resp.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Image Processor failed: {proc_resp.text}")
    return proc_resp.json()

async def run_ocr_engine(client: httpx.AsyncClient, engine: str, base64_image: str, languages_list: list):
    base_url = ENGINE_ROUTING_MAP.get(engine)
    if not base_url:
        raise HTTPException(status_code=400, detail=f"Unsupported OCR Engine: {engine}")
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
        raise HTTPException(
            status_code=500,
            detail=f"OCR Service failed with status {resp.status_code}: {resp.text}"
        )
    return resp.json()

async def execute_ocr_pipeline(
    file_bytes: bytes,
    filename: str,
    content_type: str,
    config_dict: dict,
    engine: str,
    languages_list: list,
    merge_boxes: bool
) -> dict:
    start_time = time.time()
    
    original_base64 = f"data:{content_type};base64," + base64.b64encode(file_bytes).decode('utf-8')
    
    ext = filename.split('.')[-1] if '.' in filename else 'jpg'
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Upload original image to Supabase
        orig_filename = f"original_{uuid.uuid4().hex}.{ext}"
        original_url = await upload_to_supabase(client, file_bytes, orig_filename, content_type)
        
        # 1. Route to Image Processor
        proc_data = await process_image(client, original_base64, config_dict)
        processed_base64 = proc_data["image"]
        meta = proc_data["meta"]
        
        # Ensure it has data URI prefix for frontend
        if not processed_base64.startswith("data:"):
            processed_base64 = f"data:image/jpeg;base64,{processed_base64}"
        
        # 2. Route to OCR Microservice
        resp_data = await run_ocr_engine(client, engine, processed_base64, languages_list)
        
    words = resp_data.get("words", [])
    preprocessed_image = resp_data.get("preprocessed_image")
    detected_tables = resp_data.get("detected_tables", [])
    gpu_active = False # You could parse from status/response if needed
        
    elapsed = time.time() - start_time
    
    if preprocessed_image:
        processed_base64 = preprocessed_image
        
    # 3. Perform box merging
    if merge_boxes:
        words = merge_adjacent_words(words)
        
    return {
        "success": True,
        "preprocessed_image": processed_base64, # Legacy fallback
        "original_image_url": original_url,
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
