import cv2
import numpy as np
import base64
from fastapi import FastAPI, HTTPException
from paddleocr import PaddleOCR, PPStructureV3

from shared.contracts import OCRServiceRequest, OCRServiceResponse


app = FastAPI(title="OCR Paddle Microservice")

# Caches to avoid reloading models on every request
_paddle_ocr_cache = {}
_paddle_structure_cache = {}

def get_paddle_ocr(lang: str) -> PaddleOCR:
    if lang not in _paddle_ocr_cache:
        print(f"[OCR] Initializing PaddleOCR for language: {lang}")
        _paddle_ocr_cache[lang] = PaddleOCR(use_textline_orientation=True, lang=lang)
    return _paddle_ocr_cache[lang]

def get_paddle_structure() -> PPStructureV3:
    if "engine" not in _paddle_structure_cache:
        print("[OCR] Initializing PPStructureV3 (Layout & Table Recognition)...")
        _paddle_structure_cache["engine"] = PPStructureV3()
    return _paddle_structure_cache["engine"]

def decode_image(base64_str: str) -> np.ndarray:
    if "," in base64_str:
        base64_str = base64_str.split(",")[1]
    img_data = base64.b64decode(base64_str)
    nparr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img

def encode_image(img: np.ndarray) -> str:
    _, buffer = cv2.imencode('.jpg', img)
    base64_str = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{base64_str}"

@app.on_event("startup")
def startup_event():
    print("[OCR] OCR Paddle Microservice starting up...")
    print("[OCR] Starting model warmup...")
    # Preload PaddleOCR for default languages
    get_paddle_ocr("vi")
    get_paddle_ocr("en")
    # Preload PPStructureV3
    get_paddle_structure()
    print("[OCR] Model warmup complete.")

@app.get("/api/status")
def status():
    # PaddleOCR runs on CPU inside standard Docker CPU environments
    return {
        "status": "online",
        "paddleocr_installed": True,
        "paddle_structure_installed": True
    }

@app.get("/health/live")
def live():
    return {"status": "healthy"}

@app.get("/health/ready")
def ready():
    paddle_ocr_loaded = "vi" in _paddle_ocr_cache and "en" in _paddle_ocr_cache
    structure_loaded = "engine" in _paddle_structure_cache
    if paddle_ocr_loaded and structure_loaded:
        return {"status": "ready", "details": {"service": "ocr-paddle"}}
    else:
        raise HTTPException(status_code=503, detail="Service warming up")

@app.post("/api/ocr")
async def ocr(request: OCRServiceRequest):
    try:
        img = decode_image(request.image)
        
        # PaddleOCR strictly expects 3-channel BGR
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            
        word_results = []
        preprocessed_image_base64 = None
        detected_tables = []
        
        if request.engine == 'paddleocr':
            lang = 'vi' if 'vi' in request.languages else ('en' if 'en' in request.languages else (request.languages[0] if request.languages else 'en'))
            ocr_instance = get_paddle_ocr(lang)
            results = ocr_instance.predict(img, use_doc_unwarping=False, use_doc_orientation_classify=False)
            
            if results and len(results) > 0:
                res_dict = results[0]
                rec_texts = res_dict.get('rec_texts', [])
                rec_scores = res_dict.get('rec_scores', [])
                rec_boxes = res_dict.get('rec_boxes', [])
                
                for text, score, box in zip(rec_texts, rec_scores, rec_boxes):
                    if len(box) >= 4:
                        xmin, ymin, xmax, ymax = box[:4]
                        x, y = int(xmin), int(ymin)
                        w, h = int(xmax - xmin), int(ymax - ymin)
                        text = text.strip()
                        if not text:
                            continue
                        word_results.append({
                            "text": text,
                            "confidence": round(float(score) * 100, 2),
                            "box": {"x": x, "y": y, "w": w, "h": h}
                        })
                        
        elif request.engine == 'paddle_structure':
            structure_instance = get_paddle_structure()
            results = structure_instance.predict(img)
            
            if results and len(results) > 0:
                page_res = results[0]
                
                # Extract text recognition results
                overall_ocr = page_res.get('overall_ocr_res', {})
                if overall_ocr:
                    rec_texts = overall_ocr.get('rec_texts', [])
                    rec_scores = overall_ocr.get('rec_scores', [])
                    rec_boxes = overall_ocr.get('rec_boxes', [])
                    
                    for text, score, box in zip(rec_texts, rec_scores, rec_boxes):
                        if len(box) >= 4:
                            xmin, ymin, xmax, ymax = box[:4]
                            x, y = int(xmin), int(ymin)
                            w, h = int(xmax - xmin), int(ymax - ymin)
                            text = text.strip()
                            if not text:
                                continue
                            word_results.append({
                                "text": text,
                                "confidence": round(float(score) * 100, 2),
                                "box": {"x": x, "y": y, "w": w, "h": h}
                            })
                
                # Extract preprocessed/unwarped image
                doc_prep = page_res.get('doc_preprocessor_res', {})
                if doc_prep and 'output_img' in doc_prep:
                    output_img = doc_prep['output_img']
                    if output_img is not None:
                        preprocessed_image_base64 = encode_image(output_img)
                        
                # Extract tables
                tables = page_res.get('table_res_list', [])
                if tables:
                    for idx, table in enumerate(tables):
                        html = table.get('pred_html', table.get('html', ''))
                        detected_tables.append({
                            "id": idx + 1,
                            "html": html
                        })
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported engine in Paddle microservice: {request.engine}")
            
        return OCRServiceResponse(
            words=word_results,
            preprocessed_image=preprocessed_image_base64,
            detected_tables=detected_tables,
            gpu_accelerated=False,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PaddleOCR execution failed: {str(e)}")
