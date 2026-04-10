"""
Integration tests — run with:  pytest tests/ -v
Uses HTTPX AsyncClient against the real app, tmp storage directory.
"""
import io
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app
from app.services.storage import StorageService

# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def tmp_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect all file writes to a temp directory per test."""
    monkeypatch.setattr(settings, "storage_dir", tmp_path)

    # Re-create the service singleton pointing at tmp_path
    import app.routers.upload as upload_module
    import app.services.storage as storage_module

    svc = StorageService(storage_dir=tmp_path)
    monkeypatch.setattr(storage_module, "storage_service", svc)
    monkeypatch.setattr(upload_module, "storage_service", svc)

    return tmp_path


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


def _make_pdf(content: bytes = b"hello") -> bytes:
    """Minimal valid-looking PDF bytes."""
    return b"%PDF-1.4\n" + content


# ── upload ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_valid_pdf(client: AsyncClient) -> None:
    resp = await client.post(
        "/files/upload",
        files={"file": ("report.pdf", _make_pdf(), "application/pdf")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["filename"] == "report.pdf"
    assert body["size_bytes"] > 0
    assert body["already_existed"] is False
    assert "file_id" in body


@pytest.mark.asyncio
async def test_upload_duplicate_returns_200(client: AsyncClient) -> None:
    payload = ("report.pdf", _make_pdf(), "application/pdf")
    await client.post("/files/upload", files={"file": payload})
    resp2 = await client.post("/files/upload", files={"file": payload})
    # Duplicate → 200 with already_existed flag in detail
    assert resp2.status_code == 200
    assert resp2.json()["already_existed"] is True


@pytest.mark.asyncio
async def test_upload_non_pdf_extension_rejected(client: AsyncClient) -> None:
    resp = await client.post(
        "/files/upload",
        files={"file": ("malware.exe", b"MZ\x90\x00", "application/octet-stream")},
    )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_upload_fake_pdf_extension_rejected(client: AsyncClient) -> None:
    """File named .pdf but magic bytes are wrong."""
    resp = await client.post(
        "/files/upload",
        files={"file": ("trick.pdf", b"NOTAPDF", "application/pdf")},
    )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_upload_oversized_file_rejected(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "max_file_size_mb", 0)  # 0 MB limit
    resp = await client.post(
        "/files/upload",
        files={"file": ("big.pdf", _make_pdf(b"x" * 1024), "application/pdf")},
    )
    assert resp.status_code == 413


# ── list ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_empty(client: AsyncClient) -> None:
    resp = await client.get("/files/")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_after_upload(client: AsyncClient) -> None:
    await client.post(
        "/files/upload",
        files={"file": ("a.pdf", _make_pdf(b"aaa"), "application/pdf")},
    )
    await client.post(
        "/files/upload",
        files={"file": ("b.pdf", _make_pdf(b"bbb"), "application/pdf")},
    )
    resp = await client.get("/files/")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ── delete ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_existing_file(client: AsyncClient) -> None:
    up = await client.post(
        "/files/upload",
        files={"file": ("del.pdf", _make_pdf(b"delete me"), "application/pdf")},
    )
    file_id = up.json()["file_id"]

    resp = await client.delete(f"/files/{file_id}")
    assert resp.status_code == 204

    listed = await client.get("/files/")
    assert listed.json() == []


@pytest.mark.asyncio
async def test_delete_nonexistent_returns_404(client: AsyncClient) -> None:
    resp = await client.delete("/files/deadbeef")
    assert resp.status_code == 404