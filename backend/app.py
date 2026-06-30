from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from const import CORS_ORIGINS, STORAGE_REQUIRED
from services.supabase_service import is_storage_configured
from routers import system, ocr


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the lifecycle of shared resources.
    The shared httpx.AsyncClient is created once on startup and closed on shutdown,
    enabling connection pooling across all requests.
    """
    if STORAGE_REQUIRED and not is_storage_configured():
        raise RuntimeError("STORAGE_REQUIRED=true but Supabase storage is not configured")

    async with httpx.AsyncClient() as client:
        app.state.http_client = client
        yield
    # Client is automatically closed when the context manager exits


app = FastAPI(
    title="OCR Playground Orchestrator (BFF)",
    description="FastAPI orchestrator that routes requests to image processor and OCR microservices.",
    lifespan=lifespan,
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(ocr.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
