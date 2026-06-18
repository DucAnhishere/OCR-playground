import os
import httpx
from fastapi import APIRouter
from schemas import StatusResponse, PreprocessConfig

router = APIRouter(prefix="/api")

@router.get("/config/default", response_model=PreprocessConfig)
def get_default_config():
    return PreprocessConfig()

@router.get("/status", response_model=StatusResponse)
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
