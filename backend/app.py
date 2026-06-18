from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import system, ocr

app = FastAPI(
    title="OCR Playground Orchestrator (BFF)",
    description="FastAPI orchestrator that routes requests to image processor and OCR microservices."
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(ocr.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
