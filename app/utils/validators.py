from fastapi import HTTPException, UploadFile, status

from app.config import settings

# PDF magic bytes (first 4 bytes = %PDF)
_PDF_MAGIC = b"%PDF"
_PEEK_SIZE = 4


async def validate_pdf_upload(file: UploadFile) -> None:
    """
    Run all validations on an incoming upload.
    Raises HTTPException on the first failing check.
    Order: extension -> magic bytes -> size (streamed, no full load).
    """
    _validate_extension(file.filename)
    await _validate_magic_bytes(file)
    await _validate_file_size(file)


# Private helpers

def _suffix(filename: str) -> str:
    dot = filename.rfind(".")
    return filename[dot + 1 :].lower() if dot != -1 else ""


def _validate_extension(filename: str | None) -> None:
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is missing.",
        )
    suffix = _suffix(filename)
    if suffix not in settings.allowed_extensions_set:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{suffix}' is not allowed. Accepted: {settings.allowed_extensions}",
        )
    

async def _validate_magic_bytes(file: UploadFile) -> None:
    """Read the first 4 bytes, verify PDF magic, then rewind."""
    header = await file.read(_PEEK_SIZE)
    await file.seek(0)  # Rewind for later processing

    if header[:_PEEK_SIZE] != _PDF_MAGIC:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File content does not match PDF format.",
        )
    

async def _validate_file_size(file: UploadFile) -> None:
    """
    Stream through the file to count bytes without loading it into memory.
    Rewinds to position 0 afterward so the caller can read normally.
    """
    total = 0
    chunk_size = 1024 * 1024  # 1 MB
 
    while chunk := await file.read(chunk_size):
        total += len(chunk)
        if total > settings.max_file_size_bytes:
            await file.seek(0)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"File exceeds the maximum allowed size of "
                    f"{settings.max_file_size_mb} MB."
                ),
            )
 
    await file.seek(0)


