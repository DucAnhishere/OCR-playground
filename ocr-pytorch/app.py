import os
import cv2
import numpy as np
import base64
import torch
import easyocr
import httpx
from PIL import Image
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from vietocr.tool.predictor import Predictor
from vietocr.tool.config import Cfg

app = FastAPI(title="OCR PyTorch Microservice (EasyOCR & VietOCR)")

class OCRRequest(BaseModel):
    image: str  # Base64 string
    engine: str  # 'easyocr' or 'vietocr'
    languages: list[str] = ["en", "vi"]

# Caches to avoid reloading weights/models on every request
_easyocr_readers_cache = {}
_vietocr_cache = {}

def get_easyocr_reader(langs: list[str]) -> easyocr.Reader:
    cache_key = tuple(sorted(langs))
    if cache_key not in _easyocr_readers_cache:
        use_gpu = torch.backends.mps.is_available() or torch.cuda.is_available()
        print(f"[PyTorch Service] Initializing EasyOCR Reader for {langs}. GPU acceleration: {use_gpu}")
        _easyocr_readers_cache[cache_key] = easyocr.Reader(langs, gpu=use_gpu)
    return _easyocr_readers_cache[cache_key]

def get_vietocr_predictor() -> Predictor:
    if "predictor" not in _vietocr_cache:
        print("[PyTorch Service] Initializing VietOCR (VGG + Transformer)...")
        config = Cfg.load_config_from_name('vgg_transformer')
        
        # Load local weights mapped into container to avoid downloading
        config['weights'] = '/root/.vietocr/vgg_transformer.pth'
        
        if torch.backends.mps.is_available():
            config['device'] = 'mps'
            print("[PyTorch Service] VietOCR GPU Acceleration enabled (Apple Silicon MPS)")
        elif torch.cuda.is_available():
            config['device'] = 'cuda'
            print("[PyTorch Service] VietOCR GPU Acceleration enabled (NVIDIA CUDA)")
        else:
            config['device'] = 'cpu'
            print("[PyTorch Service] VietOCR running on CPU")
            
        _vietocr_cache["predictor"] = Predictor(config)
    return _vietocr_cache["predictor"]

def decode_image(base64_str: str) -> np.ndarray:
    if "," in base64_str:
        base64_str = base64_str.split(",")[1]
    img_data = base64.b64decode(base64_str)
    nparr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img

@app.get("/api/status")
def status():
    mps_available = torch.backends.mps.is_available()
    cuda_available = torch.cuda.is_available()
    gpu_type = "None"
    if mps_available:
        gpu_type = "Apple Silicon (MPS)"
    elif cuda_available:
        gpu_type = "NVIDIA (CUDA)"
        
    return {
        "status": "online",
        "gpu_acceleration": mps_available or cuda_available,
        "gpu_type": gpu_type,
        "pytorch_version": torch.__version__,
        "device_allocated": "GPU" if (mps_available or cuda_available) else "CPU"
    }

@app.post("/api/ocr")
async def ocr(request: OCRRequest):
    try:
        if request.engine == 'easyocr':
            # --- Run EasyOCR ---
            img = decode_image(request.image)
            reader = get_easyocr_reader(request.languages)
            results = reader.readtext(img)
            
            word_results = []
            for box, text, confidence in results:
                x_coords = [p[0] for p in box]
                y_coords = [p[1] for p in box]
                
                x = int(min(x_coords))
                y = int(min(y_coords))
                w = int(max(x_coords) - x)
                h = int(max(y_coords) - y)
                
                text = text.strip()
                if not text:
                    continue
                    
                word_results.append({
                    "text": text,
                    "confidence": round(float(confidence) * 100, 2),
                    "box": {"x": x, "y": y, "w": w, "h": h}
                })
                
            return {"words": word_results}
            
        elif request.engine == 'vietocr':
            # --- Run VietOCR ---
            paddle_service_url = os.getenv("PADDLE_SERVICE_URL", "http://ocr-paddle:8003")
            
            # 1. Query ocr-paddle service for PP-Structure bounding boxes and unwarping
            try:
                async with httpx.AsyncClient(timeout=120) as client:
                    paddle_resp = await client.post(
                        f"{paddle_service_url}/api/ocr",
                        json={
                            "image": request.image,
                            "engine": "paddle_structure",
                            "languages": request.languages
                        }
                    )
                    
                    if paddle_resp.status_code != 200:
                        raise HTTPException(
                            status_code=500,
                            detail=f"Paddle service returned status code {paddle_resp.status_code}: {paddle_resp.text}"
                        )
                        
                    paddle_data = paddle_resp.json()
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to communicate with Paddle layout detection service: {str(e)}"
                )
                
            paddle_words = paddle_data.get("words", [])
            preprocessed_image_base64 = paddle_data.get("preprocessed_image")
            detected_tables = paddle_data.get("detected_tables", [])
            
            # Decode the source image for cropping (either unwarped or original)
            if preprocessed_image_base64:
                crop_src_img = decode_image(preprocessed_image_base64)
            else:
                crop_src_img = decode_image(request.image)
                
            h_img, w_img = crop_src_img.shape[:2]
            predictor = get_vietocr_predictor()
            word_results = []
            
            # Crop each bounding box and run VietOCR
            for w_item in paddle_words:
                box = w_item["box"]
                x, y, w, h = box["x"], box["y"], box["w"], box["h"]
                
                pad = 2
                x1 = max(0, x - pad)
                y1 = max(0, y - pad)
                x2 = min(w_img, x + w + pad)
                y2 = min(h_img, y + h + pad)
                
                crop_w = x2 - x1
                crop_h = y2 - y1
                
                if crop_w <= 0 or crop_h <= 0:
                    continue
                    
                cropped_bgr = crop_src_img[y1:y2, x1:x2]
                cropped_rgb = cv2.cvtColor(cropped_bgr, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(cropped_rgb)
                
                try:
                    recognized_text = predictor.predict(pil_img)
                    recognized_text = recognized_text.strip()
                    
                    if not recognized_text:
                        continue
                        
                    word_results.append({
                        "text": recognized_text,
                        "confidence": w_item["confidence"],
                        "box": {"x": x1, "y": y1, "w": crop_w, "h": crop_h}
                    })
                except Exception as ex:
                    print(f"[VietOCR] Text recognition failed for crop {x1,y1,x2,y2}: {ex}")
                    
            return {
                "words": word_results,
                "preprocessed_image": preprocessed_image_base64,
                "detected_tables": detected_tables
            }
            
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported engine in PyTorch microservice: {request.engine}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PyTorch OCR execution failed: {str(e)}")
