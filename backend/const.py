import os
from dotenv import load_dotenv

# Load environment variables from .env file (useful for local development)
load_dotenv()

# Internal Service Routing
IMAGE_PROCESSOR_URL = os.getenv("IMAGE_PROCESSOR_URL", "http://image-processor:8004")

ENGINE_ROUTING_MAP = {
    'easyocr': os.getenv("PYTORCH_SERVICE_URL", "http://ocr-pytorch:8002"),
    'vietocr': os.getenv("PYTORCH_SERVICE_URL", "http://ocr-pytorch:8002"),
    'paddleocr': os.getenv("PADDLE_SERVICE_URL", "http://ocr-paddle:8003"),
    'paddle_structure': os.getenv("PADDLE_SERVICE_URL", "http://ocr-paddle:8003"),
}

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "ocr-images")
