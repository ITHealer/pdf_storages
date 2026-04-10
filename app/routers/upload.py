import logging

from fastapi import APIRouter, Depends, Response, UploadFile, status

from app.schemas.upload import ErrorResponse, FileListItem, UploadResponse
from app.services.storage import StorageService, storage_service
from app.utils.validators import validate_pdf_upload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["files"])


def get_storage() -> StorageService:
    """Dependency — swap with a test double in unit tests."""
    return storage_service


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF file",
    responses={
        200: {"model": UploadResponse, "description": "File already exists (duplicate)"},
        400: {"model": ErrorResponse, "description": "Missing or invalid filename"},
        413: {"model": ErrorResponse, "description": "File too large"},
        415: {"model": ErrorResponse, "description": "Not a PDF"},
    },
)
async def upload_pdf(
    file: UploadFile,
    response: Response,
    service: StorageService = Depends(get_storage),
) -> UploadResponse:
    """
    Upload a PDF (up to MAX_FILE_SIZE_MB).

    - Validates extension and PDF magic bytes before writing.
    - Streams to disk in 1 MB chunks — no full-file RAM spike.
    - Deduplicates by SHA-256: uploading the same file twice returns the
      existing record with `already_existed=True` and HTTP 200.
    """
    await validate_pdf_upload(file)
    result = await service.save(file)

    # Idempotent: duplicate upload → downgrade to 200
    if result.already_existed:
        response.status_code = status.HTTP_200_OK

    return result


@router.get(
    "/",
    response_model=list[FileListItem],
    summary="List all stored PDFs",
)
def list_files(
    service: StorageService = Depends(get_storage),
) -> list[FileListItem]:
    """Return metadata for every stored PDF, newest first."""
    return service.list_files()


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a PDF by file_id",
    responses={
        404: {"model": ErrorResponse, "description": "File not found"},
    },
)
def delete_file(
    file_id: str,
    service: StorageService = Depends(get_storage),
) -> None:
    """Delete a stored PDF by its SHA-256 file_id."""
    service.delete(file_id)