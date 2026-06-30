from dotenv import load_dotenv
import os

load_dotenv()

# VietOCR Configuration
VIETOCR_WEIGHTS_PATH = os.getenv("VIETOCR_WEIGHTS_PATH", "/root/.vietocr/vgg_transformer.pth")
VIETOCR_CONFIG_NAME = os.getenv("VIETOCR_CONFIG_NAME", "vgg_transformer")
