from shared.contracts import OCRServiceRequest, OCRServiceResponse


def test_ocr_service_response_contract_accepts_all_engine_shapes():
    response = OCRServiceResponse.model_validate(
        {
            "words": [
                {
                    "text": "hello",
                    "confidence": 98.2,
                    "box": {"x": 1, "y": 2, "w": 30, "h": 10},
                }
            ],
            "preprocessed_image": "data:image/jpeg;base64,abc",
            "detected_tables": [{"id": 1, "html": "<table></table>"}],
            "gpu_accelerated": False,
            "warnings": ["non-fatal warning"],
        }
    )

    assert response.words[0].text == "hello"
    assert response.detected_tables[0].id == 1
    assert response.warnings == ["non-fatal warning"]


def test_ocr_service_request_rejects_unknown_engine():
    try:
        OCRServiceRequest.model_validate(
            {"image": "data:image/jpeg;base64,abc", "engine": "unknown", "languages": ["en"]}
        )
    except Exception as exc:
        assert "engine" in str(exc)
    else:
        raise AssertionError("unknown engine should be rejected by the shared contract")

