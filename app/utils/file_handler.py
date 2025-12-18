"""
Optimized file handling utilities for concurrent request support and streaming responses
"""
import os
import shutil
import asyncio
from pathlib import Path
from typing import Optional, Generator, AsyncGenerator
from tempfile import NamedTemporaryFile, TemporaryDirectory
from asyncio import Semaphore
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)

# Semaphore to limit concurrent file operations (max 5 concurrent conversions)
conversion_semaphore = Semaphore(5)

# Track temporary files for cleanup
_temp_files = set()
_temp_dirs = set()


async def acquire_conversion_slot():
    """Acquire a slot for a conversion operation"""
    await conversion_semaphore.acquire()


def release_conversion_slot():
    """Release a conversion slot"""
    conversion_semaphore.release()


@asynccontextmanager
async def conversion_lock():
    """Context manager for concurrent-safe conversion operations"""
    await acquire_conversion_slot()
    try:
        yield
    finally:
        release_conversion_slot()


def create_temp_file(suffix: str = ".tmp", delete: bool = False) -> Path:
    """Create a temporary file with automatic tracking for cleanup"""
    temp = NamedTemporaryFile(suffix=suffix, delete=delete)
    path = Path(temp.name)
    _temp_files.add(path)
    return path


def create_temp_dir() -> Path:
    """Create a temporary directory with automatic tracking for cleanup"""
    temp_dir = TemporaryDirectory()
    path = Path(temp_dir.name)
    _temp_dirs.add(path)
    return path


def cleanup_temp_file(path: Optional[Path]) -> None:
    """Safely cleanup a temporary file"""
    if path and path.exists():
        try:
            path.unlink()
            _temp_files.discard(path)
            logger.debug(f"Cleaned up temp file: {path}")
        except Exception as e:
            logger.error(f"Error cleaning up temp file {path}: {e}")


def cleanup_temp_dir(path: Optional[Path]) -> None:
    """Safely cleanup a temporary directory"""
    if path and path.exists():
        try:
            shutil.rmtree(path)
            _temp_dirs.discard(path)
            logger.debug(f"Cleaned up temp dir: {path}")
        except Exception as e:
            logger.error(f"Error cleaning up temp dir {path}: {e}")


def cleanup_all() -> None:
    """Cleanup all tracked temporary files and directories"""
    for file_path in list(_temp_files):
        cleanup_temp_file(file_path)
    
    for dir_path in list(_temp_dirs):
        cleanup_temp_dir(dir_path)


def stream_file_in_chunks(file_path: Path, chunk_size: int = 8192) -> Generator[bytes, None, None]:
    """Stream a file in chunks for memory-efficient delivery"""
    try:
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    except Exception as e:
        logger.error(f"Error streaming file {file_path}: {e}")
        raise


async def async_stream_file_in_chunks(
    file_path: Path, chunk_size: int = 8192
) -> AsyncGenerator[bytes, None]:
    """Async stream a file in chunks for memory-efficient delivery"""
    try:
        loop = asyncio.get_event_loop()
        with open(file_path, "rb") as f:
            while True:
                chunk = await loop.run_in_executor(None, f.read, chunk_size)
                if not chunk:
                    break
                yield chunk
    except Exception as e:
        logger.error(f"Error streaming file {file_path}: {e}")
        raise


def get_file_size(file_path: Path) -> int:
    """Get file size in bytes"""
    try:
        return file_path.stat().st_size
    except Exception as e:
        logger.error(f"Error getting file size {file_path}: {e}")
        return 0


def get_file_mime_type(file_path: Path) -> str:
    """Get MIME type for a file"""
    try:
        import magic
        mime = magic.Magic(mime=True)
        return mime.from_file(str(file_path))
    except Exception:
        # Fallback to basic detection
        suffix = file_path.suffix.lower()
        mime_types = {
            ".pdf": "application/pdf",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".mp4": "video/mp4",
            ".avi": "video/x-msvideo",
            ".csv": "text/csv",
            ".json": "application/json",
            ".xml": "application/xml",
            ".txt": "text/plain",
            ".zip": "application/zip",
            ".7z": "application/x-7z-compressed",
        }
        return mime_types.get(suffix, "application/octet-stream")


@asynccontextmanager
async def managed_temp_file(suffix: str = ".tmp"):
    """Context manager for temporary files with automatic cleanup"""
    temp_path = create_temp_file(suffix=suffix)
    try:
        yield temp_path
    finally:
        cleanup_temp_file(temp_path)


@asynccontextmanager
async def managed_temp_dir():
    """Context manager for temporary directories with automatic cleanup"""
    temp_dir = create_temp_dir()
    try:
        yield temp_dir
    finally:
        cleanup_temp_dir(temp_dir)


def copy_file_safe(src: Path, dst: Path, chunk_size: int = 1024 * 1024) -> None:
    """Safely copy a file using chunked reading (memory efficient)"""
    try:
        with open(src, "rb") as src_f:
            with open(dst, "wb") as dst_f:
                while True:
                    chunk = src_f.read(chunk_size)
                    if not chunk:
                        break
                    dst_f.write(chunk)
        logger.debug(f"Safely copied {src} to {dst}")
    except Exception as e:
        logger.error(f"Error copying file from {src} to {dst}: {e}")
        raise


async def run_subprocess_safe(
    cmd: list, timeout: int = 300, **kwargs
) -> tuple[int, str, str]:
    """Run subprocess safely with timeout and concurrent slot management"""
    async with conversion_lock():
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                **kwargs
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
                return (
                    process.returncode or 0,
                    stdout.decode(errors="ignore"),
                    stderr.decode(errors="ignore")
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                logger.error(f"Process timeout after {timeout}s: {' '.join(cmd)}")
                raise
        except Exception as e:
            logger.error(f"Error running subprocess {cmd}: {e}")
            raise
