import cv2
import numpy as np
import base64
import gc
import time
import torch
import easyocr
from PIL import Image
from fastapi import FastAPI, HTTPException
from threading import RLock
from vietocr.tool.predictor import Predictor
from vietocr.tool.config import Cfg

from shared.contracts import ModelSelectionRequest, ModelSelectionResponse, OCRServiceRequest, OCRServiceResponse
from shared.telemetry import init_telemetry, get_tracer
from const import (
    VIETOCR_WEIGHTS_PATH,
    VIETOCR_CONFIG_NAME
)

app = FastAPI(title="OCR PyTorch Microservice (EasyOCR & VietOCR)")
init_telemetry(app)
tracer = get_tracer("ocr_pytorch")

# Caches to avoid reloading weights/models on every request
_easyocr_readers_cache = {}
_vietocr_cache = {}
_model_lock = RLock()
_active_model = None


def release_torch_memory():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    if hasattr(torch, "mps") and hasattr(torch.mps, "empty_cache"):
        try:
            torch.mps.empty_cache()
        except Exception as exc:
            print(f"[PyTorch Service] Could not empty MPS cache: {exc}")


def loaded_models() -> list[str]:
    models = []
    if _easyocr_readers_cache:
        models.append("easyocr")
    if "predictor" in _vietocr_cache:
        models.append("vietocr")
    return models


def unload_easyocr_readers() -> list[str]:
    if not _easyocr_readers_cache:
        return []
    _easyocr_readers_cache.clear()
    release_torch_memory()
    print("[PyTorch Service] Unloaded EasyOCR readers")
    return ["easyocr"]


def unload_vietocr_predictor() -> list[str]:
    if "predictor" not in _vietocr_cache:
        return []
    _vietocr_cache.clear()
    release_torch_memory()
    print("[PyTorch Service] Unloaded VietOCR predictor")
    return ["vietocr"]


def select_model(engine: str, languages: list[str]) -> ModelSelectionResponse:
    global _active_model
    start_time = time.time()
    with _model_lock:
        unloaded = []
        warnings = []

        if engine == "easyocr":
            unloaded.extend(unload_vietocr_predictor())
            get_easyocr_reader(languages)
            _active_model = "easyocr"
        elif engine == "vietocr":
            unloaded.extend(unload_easyocr_readers())
            get_vietocr_predictor()
            _active_model = "vietocr"
        else:
            unloaded.extend(unload_easyocr_readers())
            unloaded.extend(unload_vietocr_predictor())
            _active_model = None
            warnings.append(f"No PyTorch model is required for engine '{engine}'.")

        elapsed = round(time.time() - start_time, 3)
        print(
            f"[PyTorch Service] Model selection engine={engine} "
            f"active={_active_model} loaded={loaded_models()} unloaded={unloaded} took={elapsed}s"
        )

        return ModelSelectionResponse(
            service="ocr-pytorch",
            requested_engine=engine,
            active_model=_active_model,
            loaded_models=loaded_models(),
            unloaded_models=unloaded,
            warnings=warnings,
        )

def get_easyocr_reader(langs: list[str]) -> easyocr.Reader:
    cache_key = tuple(sorted(langs))
    if cache_key not in _easyocr_readers_cache:
        use_gpu = torch.backends.mps.is_available() or torch.cuda.is_available()
        print(f"[PyTorch Service] Initializing EasyOCR Reader for {langs}. GPU acceleration: {use_gpu}")
        _easyocr_readers_cache[cache_key] = easyocr.Reader(langs, gpu=use_gpu)
    return _easyocr_readers_cache[cache_key]

def get_vietocr_predictor() -> Predictor:
    if "predictor" not in _vietocr_cache:
        print(f"[PyTorch Service] Initializing VietOCR ({VIETOCR_CONFIG_NAME})...")
        config = Cfg.load_config_from_name(VIETOCR_CONFIG_NAME)
        
        # Load local weights mapped into container to avoid downloading
        config['weights'] = VIETOCR_WEIGHTS_PATH
        
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

def require_easyocr_reader(langs: list[str]) -> easyocr.Reader:
    cache_key = tuple(sorted(langs))
    if cache_key not in _easyocr_readers_cache:
        raise HTTPException(
            status_code=409,
            detail=f"EasyOCR model for languages {list(cache_key)} is not loaded. Call /api/models/select before OCR.",
        )
    return _easyocr_readers_cache[cache_key]

def require_vietocr_predictor() -> Predictor:
    if "predictor" not in _vietocr_cache:
        raise HTTPException(
            status_code=409,
            detail="VietOCR model is not loaded. Call /api/models/select before OCR.",
        )
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
        "device_allocated": "GPU" if (mps_available or cuda_available) else "CPU",
        "active_model": _active_model,
        "loaded_models": loaded_models(),
    }

@app.on_event("startup")
def startup_event():
    print("[PyTorch Service] Starting without model warmup; models load on selection.")

@app.get("/health/live")
def live():
    return {"status": "healthy"}

@app.get("/health/ready")
def ready():
    return {
        "status": "ready",
        "details": {
            "service": "ocr-pytorch",
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
        with tracer.start_as_current_span("pytorch_ocr_request") as span:
            span.set_attribute("ocr.engine", request.engine)
            span.set_attribute("ocr.languages", str(request.languages))

            if request.engine == 'easyocr':
                # --- Run EasyOCR ---
                with tracer.start_as_current_span("decode_image"):
                    img = decode_image(request.image)
                reader = require_easyocr_reader(request.languages)
                with tracer.start_as_current_span("easyocr_inference"):
                    results = reader.readtext(img)

                word_results = []
                with tracer.start_as_current_span("format_results"):
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

                span.set_attribute("ocr.words_found", len(word_results))
                return OCRServiceResponse(
                    words=word_results,
                    gpu_accelerated=torch.backends.mps.is_available() or torch.cuda.is_available(),
                )

            elif request.engine == 'vietocr':
                if not request.layout_words:
                    raise HTTPException(
                        status_code=400,
                        detail="VietOCR requires layout_words supplied by the orchestrator",
                    )

                with tracer.start_as_current_span("decode_image"):
                    crop_src_img = decode_image(request.image)

                h_img, w_img = crop_src_img.shape[:2]
                predictor = require_vietocr_predictor()
                word_results = []

                # Crop each bounding box and run VietOCR
                with tracer.start_as_current_span("vietocr_inference") as viet_span:
                    viet_span.set_attribute("ocr.crops_count", len(request.layout_words))
                    for w_item in request.layout_words:
                        box = w_item.box
                        x, y, w, h = box.x, box.y, box.w, box.h

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
                                "confidence": w_item.confidence,
                                "box": {"x": x1, "y": y1, "w": crop_w, "h": crop_h}
                            })
                        except Exception as ex:
                            print(f"[VietOCR] Text recognition failed for crop {x1,y1,x2,y2}: {ex}")

                span.set_attribute("ocr.words_found", len(word_results))
                return OCRServiceResponse(
                    words=word_results,
                    gpu_accelerated=torch.backends.mps.is_available() or torch.cuda.is_available(),
                )

            else:
                raise HTTPException(status_code=400, detail=f"Unsupported engine in PyTorch microservice: {request.engine}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PyTorch OCR execution failed: {str(e)}")
