import logging
import httpx
from fastapi import APIRouter, Request
from schemas import StatusResponse, PreprocessConfig
from const import PYTORCH_SERVICE_URL, PADDLE_SERVICE_URL

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.get("/config/default", response_model=PreprocessConfig)
def get_default_config():
    return PreprocessConfig()


@router.get("/status", response_model=StatusResponse)
async def get_status(request: Request):
    client: httpx.AsyncClient = request.app.state.http_client

    paddleocr_installed = False
    paddle_structure_installed = False
    vietocr_installed = False
    gpu_acceleration = False
    gpu_type = "None"
    pytorch_version = "Unknown"
    device_allocated = "CPU"

    try:
        r = await client.get(f"{PYTORCH_SERVICE_URL}/api/status")
        if r.status_code == 200:
            data = r.json()
            vietocr_installed = True
            if data.get("gpu_acceleration", False):
                gpu_acceleration = True
                gpu_type = data.get("gpu_type", "None")
                device_allocated = data.get("device_allocated", "CPU")
            if data.get("pytorch_version"):
                pytorch_version = data.get("pytorch_version")
    except Exception as e:
        logger.warning("Could not reach PyTorch service at %s: %s", PYTORCH_SERVICE_URL, e)

    try:
        r = await client.get(f"{PADDLE_SERVICE_URL}/api/status")
        if r.status_code == 200:
            data = r.json()
            paddleocr_installed = data.get("paddleocr_installed", False)
            paddle_structure_installed = data.get("paddle_structure_installed", False)
    except Exception as e:
        logger.warning("Could not reach PaddleOCR service at %s: %s", PADDLE_SERVICE_URL, e)

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

