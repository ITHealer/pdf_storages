import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

import aiofiles
from fastapi import HTTPException, UploadFile, status

from app.config import settings
from app.schemas.upload import FileListItem, UploadResponse

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 1024 * 1024  # 1 MB - balance between memory use and syscall count


class StorageService: 
    """
    Handles all local filesystem operations for PDF storage.
    
    Layout on disk:
    {storage_dir}/
        <sha256_hex>_<original_filename>
    """
    def __init__(self, storage_dir: Path = settings.storage_dir) -> None:
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    
    # Public interface

    async def save(self, file: UploadFile) -> UploadResponse:
        """
        Stream file to disk in 1 MB chunks while computing SHA-256 in one pass.
        If an identical file already exists (same checksum), skip writing and return the existing record with already_existed=True.
        """
        checksum, size = await self._compute_checksum_and_size(file)
        await file.seek(0)  # Rewind for potential re-read

        dest_path = self._build_path(checksum, file.filename)
        
        if dest_path.exists():
            logger.info("Duplicate detected - skipping write. file_id=%s", checksum)
            return UploadResponse(
                file_id=checksum,
                filename=file.filename,
                size_bytes=size,
                path=str(dest_path),
                uploaded_at=datetime.fromtimestamp(dest_path.stat().st_mtime, tz=timezone.utc),
                already_exists=True,
            )
        
        await self._stream_to_disk(file, dest_path)
        logger.info("Saved file. file_id=%s path=%s size=%d", checksum, dest_path, size)

        return UploadResponse(
            file_id=checksum,
            filename=file.filename,
            size_bytes=size,
            path=str(dest_path),
            uploaded_at=datetime.now(timezone.utc),
            already_exists=False,
        )
    

    def list_files(self) -> list[FileListItem]:
        """Return metadata for every stored PDF, newest first."""
        items = list[FileListItem] = []

        for path in sorted(self.storage_dir.glob("*.pdf"), key=lambda p: p.stat().st-mtime, reverse=True):
            stat = path.stat()
            file_id, _, original_name = path.stem.partition("_")
            items.append(
                FileListItem(
                    file_id=file_id,
                    filename=original_name,
                    size_bytes=stat.st_size,
                    path=str(path),
                    created_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                )
            )
        return items
    
    def delete(self, file_id: str) -> None:
        """Delete a stored file by its SHA-256 checksum (file_id)."""
        matches = list(self.storage_dir.glob(f"{file_id}_*.pdf"))

        if not matches:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No file found with id '{file_id}'.",
            )
        
        for path in matches:
            path.unlink()
            logger.info("Deleted file. file_id=%s path=%s", file_id, path)

    # Private helpers

    async def _compute_checksum_and_size(
        self, file: UploadFile
    ) -> tuple[str, int]:
        """Stream file once to get SHA-256 hex and total byte count."""
        sha256 = hashlib.sha256()
        total = 0
 
        while chunk := await file.read(_CHUNK_SIZE):
            sha256.update(chunk)
            total += len(chunk)
 
        return sha256.hexdigest(), total
 
    async def _stream_to_disk(self, file: UploadFile, dest: Path) -> None:
        """Write file to *dest* in chunks — never holds full content in memory."""
        tmp = dest.with_suffix(".tmp")
        try:
            async with aiofiles.open(tmp, "wb") as fp:
                while chunk := await file.read(_CHUNK_SIZE):
                    await fp.write(chunk)
            tmp.rename(dest)  # atomic on POSIX
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
 
    def _build_path(self, checksum: str, filename: str | None) -> Path:
        safe_name = Path(filename or "unnamed.pdf").name  # strip any path traversal
        return self.storage_dir / f"{checksum}_{safe_name}"
 
 
# Module-level singleton — injected via FastAPI Depends
storage_service = StorageService()