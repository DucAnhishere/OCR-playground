import asyncio

from services import orchestrator_service


def test_upload_best_effort_returns_disabled_when_storage_is_not_configured(monkeypatch):
    monkeypatch.setattr(orchestrator_service, "is_storage_configured", lambda: False)
    warnings = []

    url, status = asyncio.run(
        orchestrator_service.upload_best_effort(
            client=None,
            file_bytes=b"image",
            filename="file.jpg",
            content_type="image/jpeg",
            warnings=warnings,
        )
    )

    assert url is None
    assert status == "disabled"
    assert warnings


def test_upload_best_effort_returns_failed_when_upload_raises(monkeypatch):
    async def failing_upload(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(orchestrator_service, "is_storage_configured", lambda: True)
    monkeypatch.setattr(orchestrator_service, "upload_to_supabase", failing_upload)
    warnings = []

    url, status = asyncio.run(
        orchestrator_service.upload_best_effort(
            client=None,
            file_bytes=b"image",
            filename="file.jpg",
            content_type="image/jpeg",
            warnings=warnings,
        )
    )

    assert url is None
    assert status == "failed"
    assert warnings

