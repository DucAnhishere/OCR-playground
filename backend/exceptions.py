"""
Domain-level exceptions for the OCR Playground BFF.

These exceptions are raised by the service layer and should be caught
by the router (controller) layer, which converts them into HTTP responses.
This keeps the service layer decoupled from FastAPI.
"""


class SupabaseUploadError(Exception):
    """Raised when uploading a file to Supabase Storage fails."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Supabase upload failed [{status_code}]: {detail}")


class ImageProcessorError(Exception):
    """Raised when the Image Processor microservice returns a non-200 response."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Image Processor failed [{status_code}]: {detail}")


class OCRServiceError(Exception):
    """Raised when an OCR microservice returns a non-200 response."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"OCR Service failed [{status_code}]: {detail}")


class UnsupportedEngineError(Exception):
    """Raised when an unsupported OCR engine name is requested."""

    def __init__(self, engine: str):
        self.engine = engine
        super().__init__(f"Unsupported OCR Engine: '{engine}'")
