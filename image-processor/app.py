from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import image_filters

app = FastAPI(title="Image Processor Service")

class ProcessRequest(BaseModel):
    image: str # Base64 encoded image
    config: dict

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/api/process")
async def process_image(request: ProcessRequest):
    try:
        img = image_filters.decode_image(request.image)
        processed, meta = image_filters.preprocess_pipeline(img, request.config)
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
