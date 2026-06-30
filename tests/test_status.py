import asyncio
from types import SimpleNamespace

from routers.system import get_status


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class FakeClient:
    async def get(self, url):
        if "ocr-pytorch" in url:
            return FakeResponse(
                200,
                {
                    "gpu_acceleration": False,
                    "gpu_type": "None",
                    "pytorch_version": "2.2.0",
                    "device_allocated": "CPU",
                },
            )
        if "ocr-paddle" in url:
            return FakeResponse(
                200,
                {"paddleocr_installed": True, "paddle_structure_installed": True},
            )
        if "image-processor" in url:
            return FakeResponse(500)
        return FakeResponse(404)


def test_status_reports_degraded_when_one_dependency_is_down():
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(http_client=FakeClient())))

    status = asyncio.run(get_status(request))

    assert status["status"] == "degraded"
    assert status["paddleocr_installed"] is True
    assert status["vietocr_installed"] is True

