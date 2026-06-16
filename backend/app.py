import os
import traceback
import cv2
import numpy as np
import httpx
import time
import pytesseract
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from image_filters import decode_image, encode_image, preprocess_pipeline
from ocr_engines.ocr_utils import merge_adjacent_words
from schemas import (
    PreprocessConfig,
    PreprocessRequest,
    OCRRequest,
    StatusResponse,
    SampleResponse,
    PreprocessResponse,
    OCRResponse
)
from structured_parser import extract_structured_data

app = FastAPI(
    title="OCR Playground API Gateway",
    description="FastAPI gateway backend orchestrating OpenCV preprocessing and microservice OCR routing."
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local sandbox development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def is_tesseract_available() -> bool:
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False

# API Endpoints
@app.get("/api/config/default", response_model=PreprocessConfig)
def get_default_config():
    """Returns the default image preprocessing configuration from the schemas module."""
    return PreprocessConfig()

@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """Returns capabilities status by querying local binaries and other microservices."""
    tesseract_installed = is_tesseract_available()
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
        # 1. Query PyTorch service (for EasyOCR & VietOCR)
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
            
        # 2. Query Paddle service (for PaddleOCR & PP-Structure)
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
        "tesseract_installed": tesseract_installed,
        "paddleocr_installed": paddleocr_installed,
        "paddle_structure_installed": paddle_structure_installed,
        "vietocr_installed": vietocr_installed,
        "pytorch_version": pytorch_version,
        "device_allocated": device_allocated
    }

@app.get("/api/sample", response_model=SampleResponse)
def get_sample(type: str = Query("skewed_receipt", description="Type of mock image: 'skewed_receipt' or 'shadow_invoice'")):
    """
    Programmatically generates sample images to test OCR & filters.
    """
    try:
        h, w = 550, 380
        img = np.ones((h, w, 3), dtype=np.uint8) * 255
        
        def draw_text(text, y_pos, font_scale=0.5, thickness=1, style=cv2.FONT_HERSHEY_SIMPLEX, centered=False):
            text_size = cv2.getTextSize(text, style, font_scale, thickness)[0]
            x = (w - text_size[0]) // 2 if centered else 25
            cv2.putText(img, text, (x, y_pos), style, font_scale, (0, 0, 0), thickness, cv2.LINE_AA)
            
        draw_text("COFFEE SHOP", 50, font_scale=0.8, thickness=2, style=cv2.FONT_HERSHEY_DUPLEX, centered=True)
        draw_text("123 Ly Thuong Kiet St, Q11", 85, font_scale=0.45, centered=True)
        draw_text("SDT: 0908765432", 110, font_scale=0.45, centered=True)
        draw_text("-" * 34, 140, font_scale=0.5)
        draw_text("HOA DON BAN LE (RECEIPT)", 170, font_scale=0.5, thickness=1, centered=True)
        draw_text("Ngay: 27/05/2026 17:30", 200, font_scale=0.45)
        draw_text("-" * 34, 230, font_scale=0.5)
        draw_text("Capuccino XL     x1    60.000 d", 260, font_scale=0.45)
        draw_text("Croissant Cream  x1    40.000 d", 290, font_scale=0.45)
        draw_text("Espresso Shot    x1    30.000 d", 320, font_scale=0.45)
        draw_text("-" * 34, 350, font_scale=0.5)
        draw_text("TONG CONG (TOTAL): 130.000 d", 385, font_scale=0.55, thickness=2)
        draw_text("-" * 34, 420, font_scale=0.5)
        draw_text("Email: support@coffeeshop.vn", 450, font_scale=0.45)
        draw_text("Thank you & see you again!", 490, font_scale=0.5, style=cv2.FONT_HERSHEY_ITALIC, centered=True)
        
        if type == "skewed_receipt":
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, -12, 0.9)
            img = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(220, 220, 220))
        elif type == "shadow_invoice":
            y, x = np.mgrid[0:h, 0:w]
            shadow = 0.25 + 0.75 * ((x + y) / (w + h))
            shadow = np.clip(shadow, 0.0, 1.0)
            for c in range(3):
                img[:, :, c] = (img[:, :, c] * shadow).astype(np.uint8)
            noise = np.random.normal(0, 3, (h, w, 3)).astype(np.int16)
            img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        base64_str = encode_image(img)
        return {"image": base64_str}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Sample generation error: {str(e)}")

@app.post("/api/preprocess", response_model=PreprocessResponse)
def api_preprocess(request: PreprocessRequest):
    """Preprocesses an image and returns the processed base64 image without running OCR."""
    try:
        img = decode_image(request.image)
        processed, meta = preprocess_pipeline(img, request.config.model_dump())
        processed_base64 = encode_image(processed)
        return {
            "success": True,
            "processed_image": processed_base64,
            "metadata": meta
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Preprocessing error: {str(e)}")

@app.post("/api/ocr", response_model=OCRResponse)
async def api_ocr(request: OCRRequest):
    """
    Applies OpenCV preprocessing, runs OCR (local Tesseract or microservices), and parses structured output.
    """
    try:
        # 1. Decode base64 image
        img = decode_image(request.image)
        
        # 2. Apply preprocessing pipeline on the Gateway
        processed, meta = preprocess_pipeline(img, request.config.model_dump())
        processed_base64 = encode_image(processed)
        
        words = []
        preprocessed_image = None
        detected_tables = []
        gpu_active = False
        start_time = time.time()
        
        # 3. Route or execute OCR
        if request.engine == 'tesseract':
            # Run local Tesseract on the Gateway
            if not is_tesseract_available():
                raise HTTPException(status_code=500, detail="Tesseract binary is not installed on the Gateway.")
                
            tess_langs = []
            for l in request.languages:
                if l == 'vi': tess_langs.append('vie')
                elif l == 'en': tess_langs.append('eng')
                else: tess_langs.append(l)
            tess_lang_str = "+".join(tess_langs)
            
            data = pytesseract.image_to_data(processed, lang=tess_lang_str, output_type=pytesseract.Output.DICT)
            num_boxes = len(data["text"])
            
            for i in range(num_boxes):
                text = data["text"][i].strip()
                confidence = float(data["conf"][i])
                if confidence > 0 and text:
                    x = int(data["left"][i])
                    y = int(data["top"][i])
                    w = int(data["width"][i])
                    h = int(data["height"][i])
                    words.append({
                        "text": text,
                        "confidence": round(confidence, 2),
                        "box": {"x": x, "y": y, "w": w, "h": h}
                    })
        else:
            # Route to microservices
            pytorch_url = os.getenv("PYTORCH_SERVICE_URL", "http://ocr-pytorch:8002")
            paddle_url = os.getenv("PADDLE_SERVICE_URL", "http://ocr-paddle:8003")
            
            target_service_url = None
            if request.engine in ['easyocr', 'vietocr']:
                target_service_url = f"{pytorch_url}/api/ocr"
            elif request.engine in ['paddleocr', 'paddle_structure']:
                target_service_url = f"{paddle_url}/api/ocr"
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported OCR Engine: {request.engine}")
                
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
            
        elapsed = time.time() - start_time
        
        # If the backend microservice returned an internally unwarped image, overwrite ours
        if preprocessed_image:
            processed_base64 = preprocessed_image
            
        # 4. Perform box merging
        if request.merge_boxes:
            words = merge_adjacent_words(words)
            
        # 5. Extract structured data
        structured_data = extract_structured_data(words)
        
        return {
            "success": True,
            "preprocessed_image": processed_base64,
            "results": words,
            "metadata": {
                **meta,
                "words_count": len(words),
                "resolution": f"{img.shape[1]}x{img.shape[0]}",
                "detected_tables": detected_tables
            },
            "engine": request.engine,
            "execution_time_seconds": round(elapsed, 3),
            "gpu_accelerated": gpu_active,
            "structured_data": structured_data
        }
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"OCR Gateway execution failed: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
