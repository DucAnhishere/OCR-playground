from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import image_filters

from shared.telemetry import init_telemetry, get_tracer

app = FastAPI(title="Image Processor Service")
init_telemetry(app)
tracer = get_tracer("image_processor")

class ProcessRequest(BaseModel):
    image: str # Base64 encoded image
    config: dict

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/health/live")
def live():
    return {"status": "healthy"}

@app.get("/health/ready")
def ready():
    return {"status": "ready", "details": {"service": "image-processor"}}

@app.post("/api/process")
async def process_image(request: ProcessRequest):
    try:
        with tracer.start_as_current_span("image_preprocess_pipeline") as span:
            with tracer.start_as_current_span("decode_image"):
                img = image_filters.decode_image(request.image)

            span.set_attribute("image.height", img.shape[0])
            span.set_attribute("image.width", img.shape[1])

            with tracer.start_as_current_span("preprocess_pipeline"):
                processed, meta = image_filters.preprocess_pipeline(img, request.config)

            with tracer.start_as_current_span("encode_image"):
                processed_base64 = image_filters.encode_image(processed)

            return {
                "image": processed_base64,
                "meta": meta
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8004)
