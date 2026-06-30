import asyncio

from services.orchestrator_service import model_selection_targets, run_ocr_workflow, select_ocr_models


def test_easyocr_selection_loads_pytorch_and_unloads_paddle():
    targets = model_selection_targets("easyocr")

    assert targets[0][1] == "easyocr"
    assert targets[1][1] == "easyocr"


def test_vietocr_selection_loads_paddle_layout_and_vietocr_recognizer():
    targets = model_selection_targets("vietocr")

    assert targets[0][1] == "paddle_layout"
    assert targets[1][1] == "vietocr"


def test_paddleocr_selection_loads_paddle_and_unloads_pytorch():
    targets = model_selection_targets("paddleocr")

    assert targets[0][1] == "paddleocr"
    assert targets[1][1] == "paddleocr"


class FakeResponse:
    status_code = 200
    text = ""

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class FakeClient:
    async def post(self, url, json, timeout):
        return FakeResponse(
            {
                "service": "ocr-pytorch" if "ocr-pytorch" in url else "ocr-paddle",
                "requested_engine": json["engine"],
                "active_model": json["engine"] if json["engine"] in {"easyocr", "vietocr", "paddleocr", "paddle_structure", "paddle_layout"} else None,
                "loaded_models": [json["engine"]] if json["engine"] in {"easyocr", "vietocr", "paddleocr", "paddle_structure", "paddle_layout"} else [],
                "unloaded_models": [],
                "warnings": [],
            }
        )


def test_select_ocr_models_returns_valid_service_responses():
    result = asyncio.run(select_ocr_models(FakeClient(), "vietocr", ["vi", "en"]))

    assert result["success"] is True
    assert result["engine"] == "vietocr"
    assert [service["requested_engine"] for service in result["services"]] == ["paddle_layout", "vietocr"]


class FakeLayoutOnlyClient:
    def __init__(self):
        self.calls = []

    async def post(self, url, json, timeout):
        self.calls.append(json["engine"])
        return FakeResponse(
            {
                "words": [],
                "preprocessed_image": None,
                "detected_tables": [],
                "gpu_accelerated": False,
                "warnings": [],
            }
        )


def test_vietocr_workflow_skips_recognition_when_layout_is_empty():
    client = FakeLayoutOnlyClient()
    result = asyncio.run(run_ocr_workflow(client, "vietocr", "data:image/jpeg;base64,", ["vi", "en"]))

    assert result.words == []
    assert client.calls == ["paddle_layout"]
    assert "VietOCR recognition was skipped" in result.warnings[0]
