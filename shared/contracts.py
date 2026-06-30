from typing import Any, Literal

from pydantic import BaseModel, Field


EngineName = Literal["easyocr", "vietocr", "paddleocr", "paddle_structure", "paddle_layout"]
StorageStatus = Literal["uploaded", "failed", "disabled"]


class OCRWordBox(BaseModel):
    x: int = Field(..., description="Bounding box X coordinate (top-left)")
    y: int = Field(..., description="Bounding box Y coordinate (top-left)")
    w: int = Field(..., description="Bounding box width")
    h: int = Field(..., description="Bounding box height")


class OCRWordResult(BaseModel):
    text: str = Field(..., description="Extracted text")
    confidence: float = Field(..., description="Confidence score from 0 to 100")
    box: OCRWordBox = Field(..., description="Bounding box of the text region")


class DetectedTable(BaseModel):
    id: int = Field(..., description="Stable table id within the page")
    html: str = Field("", description="Recognized table HTML")


class OCRServiceRequest(BaseModel):
    image: str = Field(..., description="Base64 encoded image string")
    engine: EngineName = Field(..., description="OCR engine to run")
    languages: list[str] = Field(default_factory=lambda: ["vi", "en"])
    layout_words: list[OCRWordResult] | None = Field(
        default=None,
        description="Optional layout boxes supplied by the orchestrator for recognizers such as VietOCR",
    )


class OCRServiceResponse(BaseModel):
    words: list[OCRWordResult] = Field(default_factory=list)
    preprocessed_image: str | None = None
    detected_tables: list[DetectedTable] = Field(default_factory=list)
    gpu_accelerated: bool = False
    warnings: list[str] = Field(default_factory=list)


class ModelSelectionRequest(BaseModel):
    engine: EngineName = Field(..., description="Frontend-selected OCR workflow")
    languages: list[str] = Field(default_factory=lambda: ["vi", "en"])


class ModelSelectionResponse(BaseModel):
    service: str
    requested_engine: EngineName
    active_model: str | None = None
    loaded_models: list[str] = Field(default_factory=list)
    unloaded_models: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ServiceHealth(BaseModel):
    status: Literal["healthy", "unhealthy", "ready", "not_ready"]
    details: dict[str, Any] = Field(default_factory=dict)
