from pydantic import BaseModel, Field
from typing import List, Dict, Any

# --- Request/Input Schemas ---

class PreprocessConfig(BaseModel):
    auto_flatten: bool = Field(False, description="Automatically detect sheet contours and apply perspective transform")
    grayscale: bool = Field(False, description="Convert image to grayscale")
    contrast: float = Field(1.0, description="Contrast scaling factor (1.0 = normal)")
    brightness: int = Field(0, description="Brightness offset (-100 to 100)")
    deskew: bool = Field(False, description="Automatically deskew text orientation")
    threshold_method: str = Field("none", description="Thresholding method: 'none', 'binary', 'otsu', 'adaptive'")
    threshold_val: int = Field(127, description="Threshold value for 'binary' method")
    adaptive_block_size: int = Field(11, description="Block size for 'adaptive' method (must be odd)")
    adaptive_c: int = Field(2, description="C constant for 'adaptive' method")
    morphology_op: str = Field("none", description="Morphology operator: 'none', 'dilation', 'erosion'")
    morphology_kernel: int = Field(3, description="Kernel size for morphology (must be odd)")
    morphology_iterations: int = Field(1, description="Number of iterations for morphology operator")

class OCRRequest(BaseModel):
    image: str = Field(..., description="Base64 encoded image string")
    config: PreprocessConfig = Field(..., description="Configuration for preprocessing pipeline")
    engine: str = Field("easyocr", description="OCR Engine to use: 'easyocr', 'vietocr', 'paddleocr', 'paddle_structure'")
    languages: List[str] = Field(["vi", "en"], description="Languages to load for OCR engines")
    merge_boxes: bool = Field(True, description="Merge horizontally aligned and adjacent word bounding boxes")

class PreprocessRequest(BaseModel):
    image: str = Field(..., description="Base64 encoded image string")
    config: PreprocessConfig = Field(..., description="Configuration for preprocessing pipeline")


# --- Response/Output Schemas ---

class StatusResponse(BaseModel):
    status: str = Field(..., description="Backend system status (e.g. 'online')")
    gpu_acceleration: bool = Field(..., description="True if PyTorch has CUDA or MPS acceleration active")
    gpu_type: str = Field(..., description="GPU Type ('Apple Silicon (MPS)', 'NVIDIA (CUDA)', 'None')")
    paddleocr_installed: bool = Field(..., description="True if PaddleOCR is installed and available")
    paddle_structure_installed: bool = Field(..., description="True if PaddleOCR Structure is installed and available")
    vietocr_installed: bool = Field(..., description="True if VietOCR is installed and available")
    pytorch_version: str = Field(..., description="Installed PyTorch library version")
    device_allocated: str = Field(..., description="Device used ('GPU' or 'CPU')")


class PreprocessResponse(BaseModel):
    success: bool = Field(True, description="True if processing succeeded")
    processed_image: str = Field(..., description="Base64 encoded processed image")
    metadata: Dict[str, Any] = Field(..., description="Metadata after preprocessing (e.g., deskew angle)")

class OCRWordBox(BaseModel):
    x: int = Field(..., description="Bounding box X coordinate (top-left)")
    y: int = Field(..., description="Bounding box Y coordinate (top-left)")
    w: int = Field(..., description="Bounding box width")
    h: int = Field(..., description="Bounding box height")

class OCRWordResult(BaseModel):
    text: str = Field(..., description="Extracted word text")
    confidence: float = Field(..., description="Confidence score from 0 to 100")
    box: OCRWordBox = Field(..., description="Bounding box of the word")

class OCRResponse(BaseModel):
    success: bool = Field(True, description="True if OCR operation succeeded")
    preprocessed_image: str = Field(..., description="Base64 encoded preprocessed image")
    results: List[OCRWordResult] = Field(..., description="List of recognized word bounding boxes")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata about execution")
    engine: str = Field(..., description="OCR Engine used ('easyocr', 'vietocr', 'paddleocr', 'paddle_structure')")
    execution_time_seconds: float = Field(..., description="Duration of OCR execution in seconds")
    gpu_accelerated: bool = Field(..., description="True if GPU acceleration was active during OCR")
