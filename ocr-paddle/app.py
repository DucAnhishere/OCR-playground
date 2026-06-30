import os
# Optimize PaddlePaddle memory allocation on CPU. A very low fraction causes
# Paddle to churn allocations during lazy init; keep enough headroom for warmup.
os.environ["FLAGS_fraction_of_cpu_memory_to_use"] = "0.25"
os.environ["FLAGS_allocator_strategy"] = "naive_best_fit"
os.environ["FLAGS_eager_delete_scope"] = "1"
os.environ["FLAGS_eager_delete_tensor_gb"] = "0.0"
os.environ["FLAGS_use_pinned_memory"] = "0"

import cv2
import numpy as np
import base64
import gc
import time
from fastapi import FastAPI, HTTPException
from threading import RLock
from paddleocr import PaddleOCR, PPStructureV3

from shared.contracts import ModelSelectionRequest, ModelSelectionResponse, OCRServiceRequest, OCRServiceResponse


app = FastAPI(title="OCR Paddle Microservice")

# Caches to avoid reloading models on every request
_paddle_ocr_cache = {}
_paddle_ocr_warmed = set()
_paddle_structure_cache = {}
_model_lock = RLock()
_active_model = None


def release_model_memory():
    gc.collect()


def loaded_models() -> list[str]:
    models = []
    if _paddle_ocr_cache:
        models.append("paddleocr")
    if "engine" in _paddle_structure_cache:
        models.append("paddle_structure")
    return models


def unload_paddle_ocr() -> list[str]:
    if not _paddle_ocr_cache:
        return []
    _paddle_ocr_cache.clear()
    _paddle_ocr_warmed.clear()
    release_model_memory()
    print("[OCR] Unloaded PaddleOCR models")
    return ["paddleocr"]


def unload_paddle_structure() -> list[str]:
    if "engine" not in _paddle_structure_cache:
        return []
    _paddle_structure_cache.clear()
    release_model_memory()
    print("[OCR] Unloaded PPStructureV3")
    return ["paddle_structure"]


def select_model(engine: str, languages: list[str]) -> ModelSelectionResponse:
    global _active_model
    start_time = time.time()
    with _model_lock:
        unloaded = []
        warnings = []

        if engine in {"paddleocr", "paddle_layout"}:
            unloaded.extend(unload_paddle_structure())
            lang = 'vi' if 'vi' in languages else ('en' if 'en' in languages else (languages[0] if languages else 'en'))
            warmup_paddle_ocr(lang)
            _active_model = engine
        elif engine == "paddle_structure":
            unloaded.extend(unload_paddle_ocr())
            warmup_paddle_structure()
            _active_model = "paddle_structure"
        else:
            unloaded.extend(unload_paddle_ocr())
            unloaded.extend(unload_paddle_structure())
            _active_model = None
            warnings.append(f"No Paddle model is required for engine '{engine}'.")

        elapsed = round(time.time() - start_time, 3)
        print(
            f"[OCR] Model selection engine={engine} "
            f"active={_active_model} loaded={loaded_models()} unloaded={unloaded} took={elapsed}s"
        )

        return ModelSelectionResponse(
            service="ocr-paddle",
            requested_engine=engine,
            active_model=_active_model,
            loaded_models=loaded_models(),
            unloaded_models=unloaded,
            warnings=warnings,
        )

def get_paddle_ocr(lang: str) -> PaddleOCR:
    if lang not in _paddle_ocr_cache:
        print(f"[OCR] Initializing PaddleOCR for language: {lang}")
        _paddle_ocr_cache[lang] = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            lang=lang,
            cpu_threads=2,
        )
    return _paddle_ocr_cache[lang]

def get_paddle_structure() -> PPStructureV3:
    if "engine" not in _paddle_structure_cache:
        print("[OCR] Initializing PPStructureV3 (Layout & Table Recognition)...")
        _paddle_structure_cache["engine"] = PPStructureV3(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            use_formula_recognition=False,
            use_chart_recognition=False,
            use_region_detection=False,
            use_seal_recognition=False,
            use_table_recognition=True,
            cpu_threads=2,
        )
    return _paddle_structure_cache["engine"]

def warmup_image() -> np.ndarray:
    img = np.ones((96, 320, 3), dtype=np.uint8) * 255
    cv2.putText(img, "warmup", (12, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2, cv2.LINE_AA)
    return img

def materialize_prediction(results):
    if results is None:
        return []
    if isinstance(results, list):
        return results
    return list(results)

def warmup_paddle_ocr(lang: str) -> PaddleOCR:
    ocr_instance = get_paddle_ocr(lang)
    if lang not in _paddle_ocr_warmed:
        print(f"[OCR] Warming PaddleOCR for language: {lang}")
        materialize_prediction(
            ocr_instance.predict(
                warmup_image(),
                use_doc_unwarping=False,
                use_doc_orientation_classify=False,
            )
        )
        _paddle_ocr_warmed.add(lang)
        print(f"[OCR] PaddleOCR warmup complete for language: {lang}")
    return ocr_instance

def warmup_paddle_structure() -> PPStructureV3:
    structure_instance = get_paddle_structure()
    if not _paddle_structure_cache.get("warmed"):
        print("[OCR] Warming PPStructureV3...")
        materialize_prediction(structure_instance.predict(warmup_image()))
        _paddle_structure_cache["warmed"] = True
        print("[OCR] PPStructureV3 warmup complete")
    return structure_instance

def require_paddle_ocr(lang: str) -> PaddleOCR:
    if lang not in _paddle_ocr_cache:
        raise HTTPException(
            status_code=409,
            detail=f"PaddleOCR model for language '{lang}' is not loaded. Call /api/models/select before OCR.",
        )
    return _paddle_ocr_cache[lang]

def require_paddle_structure() -> PPStructureV3:
    if "engine" not in _paddle_structure_cache:
        raise HTTPException(
            status_code=409,
            detail="PP-Structure model is not loaded. Call /api/models/select before OCR.",
        )
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
    print("[OCR] Starting without model warmup; models load on selection.")

@app.get("/api/status")
def status():
    # PaddleOCR runs on CPU inside standard Docker CPU environments
    return {
        "status": "online",
        "paddleocr_installed": True,
        "paddle_structure_installed": True,
        "active_model": _active_model,
        "loaded_models": loaded_models(),
    }

@app.get("/health/live")
def live():
    return {"status": "healthy"}

@app.get("/health/ready")
def ready():
    return {
        "status": "ready",
        "details": {
            "service": "ocr-paddle",
            "active_model": _active_model,
            "loaded_models": loaded_models(),
        },
    }


@app.post("/api/models/select", response_model=ModelSelectionResponse)
def select_runtime_model(request: ModelSelectionRequest):
    return select_model(request.engine, request.languages)

@app.post("/api/ocr")
def ocr(request: OCRServiceRequest):
    try:
        img = decode_image(request.image)
        
        # PaddleOCR strictly expects 3-channel BGR
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            
        word_results = []
        preprocessed_image_base64 = None
        detected_tables = []
        
        if request.engine in {'paddleocr', 'paddle_layout'}:
            lang = 'vi' if 'vi' in request.languages else ('en' if 'en' in request.languages else (request.languages[0] if request.languages else 'en'))
            ocr_instance = require_paddle_ocr(lang)
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
            structure_instance = require_paddle_structure()
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
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PaddleOCR execution failed: {str(e)}")
