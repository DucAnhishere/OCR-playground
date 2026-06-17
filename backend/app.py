import os
import traceback
import httpx
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ocr_engines.ocr_utils import merge_adjacent_words
from schemas import (
    PreprocessConfig,
    PreprocessRequest,
    OCRRequest,
    StatusResponse,
    PreprocessResponse,
    OCRResponse
)

app = FastAPI(
    title="OCR Playground Orchestrator (BFF)",
    description="FastAPI orchestrator that routes requests to image processor and OCR microservices."
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration mapping
ENGINE_ROUTING_MAP = {
    'easyocr': os.getenv("PYTORCH_SERVICE_URL", "http://ocr-pytorch:8002"),
    'vietocr': os.getenv("PYTORCH_SERVICE_URL", "http://ocr-pytorch:8002"),
    'paddleocr': os.getenv("PADDLE_SERVICE_URL", "http://ocr-paddle:8003"),
    'paddle_structure': os.getenv("PADDLE_SERVICE_URL", "http://ocr-paddle:8003"),
}

IMAGE_PROCESSOR_URL = os.getenv("IMAGE_PROCESSOR_URL", "http://image-processor:8004")

@app.get("/api/config/default", response_model=PreprocessConfig)
def get_default_config():
    return PreprocessConfig()

@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    paddleocr_installed = False
    paddle_structure_installed = False
    vietocr_installed = False
    gpu_acceleration = False
    gpu_type = "None"
    pytorch_version = "Unknown"
    device_allocated = "CPU"
    
    pytorch_url = os.getenv("PYTORCH_SERVICE_URL", "http://ocr-pytorch:8002")
    paddle_url = os.getenv("PADDLE_SERVICE_URL", "http://ocr-paddle:8003")
    
    async with httpx.AsyncClient(timeout=2.0) as client:
        try:
            r = await client.get(f"{pytorch_url}/api/status")
            if r.status_code == 200:
                data = r.json()
                vietocr_installed = True
                if data.get("gpu_acceleration", False):
                    gpu_acceleration = True
                    gpu_type = data.get("gpu_type", "None")
                    device_allocated = data.get("device_allocated", "CPU")
                if data.get("pytorch_version"):
                    pytorch_version = data.get("pytorch_version")
        except Exception:
            pass
            
        try:
            r = await client.get(f"{paddle_url}/api/status")
            if r.status_code == 200:
                data = r.json()
                paddleocr_installed = data.get("paddleocr_installed", False)
                paddle_structure_installed = data.get("paddle_structure_installed", False)
        except Exception:
            pass
            
    return {
        "status": "online",
        "gpu_acceleration": gpu_acceleration,
        "gpu_type": gpu_type,
        "paddleocr_installed": paddleocr_installed,
        "paddle_structure_installed": paddle_structure_installed,
        "vietocr_installed": vietocr_installed,
        "pytorch_version": pytorch_version,
        "device_allocated": device_allocated
    }

@app.post("/api/preprocess", response_model=PreprocessResponse)
async def api_preprocess(request: PreprocessRequest):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            proc_resp = await client.post(
                f"{IMAGE_PROCESSOR_URL}/api/process",
                json={
                    "image": request.image,
                    "config": request.config.model_dump()
                }
            )
            if proc_resp.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Image Processor failed: {proc_resp.text}")
            
            proc_data = proc_resp.json()
            
        return {
            "success": True,
            "processed_image": proc_data["image"],
            "metadata": proc_data["meta"]
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Preprocessing error: {str(e)}")

@app.post("/api/ocr", response_model=OCRResponse)
async def api_ocr(request: OCRRequest):
    try:
        start_time = time.time()
        
        # 1. Route to Image Processor
        async with httpx.AsyncClient(timeout=30.0) as client:
            proc_resp = await client.post(
                f"{IMAGE_PROCESSOR_URL}/api/process",
                json={
                    "image": request.image,
                    "config": request.config.model_dump()
                }
            )
            if proc_resp.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Image Processor failed: {proc_resp.text}")
            
            proc_data = proc_resp.json()
            processed_base64 = proc_data["image"]
            meta = proc_data["meta"]
            
        # 2. Route to OCR Microservice
        base_url = ENGINE_ROUTING_MAP.get(request.engine)
        if not base_url:
            raise HTTPException(status_code=400, detail=f"Unsupported OCR Engine: {request.engine}")
        target_service_url = f"{base_url}/api/ocr"
            
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                target_service_url,
                json={
                    "image": processed_base64,
                    "engine": request.engine,
                    "languages": request.languages
                }
            )
            
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"OCR Service failed with status {resp.status_code}: {resp.text}"
                )
                
            resp_data = resp.json()
            
        words = resp_data.get("words", [])
        preprocessed_image = resp_data.get("preprocessed_image")
        detected_tables = resp_data.get("detected_tables", [])
        gpu_active = False # You could parse from status/response if needed
            
        elapsed = time.time() - start_time
        
        if preprocessed_image:
            processed_base64 = preprocessed_image
            
        # 3. Perform box merging
        if request.merge_boxes:
            words = merge_adjacent_words(words)
            
        return {
            "success": True,
            "preprocessed_image": processed_base64,
            "results": words,
            "metadata": {
                **meta,
                "words_count": len(words),
                # We can't get resolution from OpenCV here easily, so we omit or fake it, 
                # but let's just return what we have
                "detected_tables": detected_tables
            },
            "engine": request.engine,
            "execution_time_seconds": round(elapsed, 3),
            "gpu_accelerated": gpu_active
        }
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"OCR Orchestrator execution failed: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
