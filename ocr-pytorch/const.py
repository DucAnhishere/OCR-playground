import os
from dotenv import load_dotenv

load_dotenv()

# Internal Service Routing
PADDLE_SERVICE_URL = os.getenv("PADDLE_SERVICE_URL", "http://ocr-paddle:8003")

# VietOCR Configuration
VIETOCR_WEIGHTS_PATH = os.getenv("VIETOCR_WEIGHTS_PATH", "/root/.vietocr/vgg_transformer.pth")
VIETOCR_CONFIG_NAME = os.getenv("VIETOCR_CONFIG_NAME", "vgg_transformer")
