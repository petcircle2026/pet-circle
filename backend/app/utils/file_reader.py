"""
PetCircle Phase 1 - File Reader Utility

Reads uploaded file content for GPT extraction:
    - Images (JPEG/PNG): Base64-encodes for GPT vision API.
    - PDFs: Extracts text using PyPDF2; renders scanned pages as images via PyMuPDF.

Rules:
    - No file content is stored in memory beyond the extraction call.
    - PDF text extraction is best-effort - scanned PDFs yield empty text.
    - Scanned PDFs are rendered to JPEG images for GPT vision fallback.
    - All errors are logged but never crash the caller.

Bulkhead:
    - CPU-bound rendering (PyMuPDF page rasterisation, Pillow resize/compress)
      runs in a dedicated ThreadPoolExecutor (_RENDER_POOL) so it cannot block
      the asyncio event loop used by webhook handlers.
    - Pool size is capped at FILE_READER_MAX_WORKERS (default 4) to bound
      memory and CPU usage under concurrent extraction bursts.
    - Async wrappers (async_encode_image_base64, async_render_pdf_pages_as_images,
      async_extract_pdf_text) let callers await without blocking.
"""

import asyncio
import base64
import concurrent.futures
import io
import logging
import os

logger = logging.getLogger(__name__)

# Max threads for CPU-bound PDF/image work. Defaults to min(4, cpu_count).
# Keeps extraction bursts from starving the event loop while still allowing
# parallelism across multiple concurrent documents.
FILE_READER_MAX_WORKERS: int = min(4, (os.cpu_count() or 2))

# Module-level pool - created once, shared across all extraction tasks.
# Shutdown is handled by the Python interpreter at process exit.
_RENDER_POOL: concurrent.futures.ThreadPoolExecutor = (
    concurrent.futures.ThreadPoolExecutor(
        max_workers=FILE_READER_MAX_WORKERS,
        thread_name_prefix="file_reader",
    )
)

_MAX_IMAGE_DIMENSION = 7900  # Anthropic API hard limit is 8000px per dimension
_MAX_BASE64_BYTES = 4_800_000  # Anthropic API hard limit is 5MB base64; use 4.8MB headroom


def encode_image_base64(file_bytes: bytes, mime_type: str) -> str:
    """
    Base64-encode image bytes for the Anthropic vision API.

    Enforces two Anthropic API limits:
      1. Max 8000px per dimension  -> resizes down proportionally.
      2. Max 5MB base64 payload    -> reduces JPEG quality in steps until within limit.

    Args:
        file_bytes: Raw image bytes.
        mime_type: MIME type (image/jpeg or image/png).

    Returns:
        Data URI string: data:{mime_type};base64,{encoded_data}
    """
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(file_bytes))
        orig_w, orig_h = img.size

        # Step 1: pixel-dimension cap.
        if orig_w > _MAX_IMAGE_DIMENSION or orig_h > _MAX_IMAGE_DIMENSION:
            scale = _MAX_IMAGE_DIMENSION / max(orig_w, orig_h)
            img = img.resize((int(orig_w * scale), int(orig_h * scale)), Image.LANCZOS)
            logger.debug(
                "Resized image from %dx%d to %dx%d for Anthropic API pixel limit",
                orig_w, orig_h, img.width, img.height,
            )

        # Step 2: base64 size cap - reduce JPEG quality until under limit.
        fmt = "JPEG" if mime_type == "image/jpeg" else "PNG"
        quality = 92
        while True:
            buf = io.BytesIO()
            save_kwargs = {"format": fmt, "quality": quality} if fmt == "JPEG" else {"format": fmt}
            img.save(buf, **save_kwargs)
            file_bytes = buf.getvalue()
            encoded_len = (len(file_bytes) * 4 + 2) // 3  # base64 output length
            if encoded_len <= _MAX_BASE64_BYTES or fmt != "JPEG":
                break
            if quality > 60:
                quality -= 10
            else:
                # Quality reduction alone isn't enough - halve dimensions.
                img = img.resize((img.width // 2, img.height // 2), Image.LANCZOS)
                quality = 85
                logger.debug(
                    "Further resized image to %dx%d to meet 5MB base64 limit",
                    img.width, img.height,
                )

    except Exception as e:
        logger.warning("Image resize/compress skipped (PIL unavailable or error): %s", e)

    encoded = base64.b64encode(file_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def extract_pdf_text(file_bytes: bytes) -> str:
    """
    Extract text content from a PDF file using PyPDF2.

    For text-based PDFs, returns the full text content.
    For scanned PDFs (image-only), returns empty string.

    Args:
        file_bytes: Raw PDF bytes.

    Returns:
        Extracted text from all pages, or empty string if no text found.
    """
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(file_bytes))
        text_parts = []

        for page_num, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text.strip())
            except Exception as e:
                logger.warning(
                    "Failed to extract text from PDF page %d: %s",
                    page_num, str(e),
                )

        return "\n\n".join(text_parts)

    except Exception as e:
        logger.error("PDF text extraction failed: %s", str(e))
        return ""


def render_pdf_pages_as_images(file_bytes: bytes, max_pages: int = 3) -> list[str]:
    """
    Render PDF pages as JPEG base64 data URIs for GPT vision API.

    Uses PyMuPDF (fitz) to render each page at 200 DPI.
    This is the fallback for scanned PDFs where text extraction yields nothing.

    Args:
        file_bytes: Raw PDF bytes.
        max_pages: Maximum number of pages to render (default 3).

    Returns:
        List of data URI strings (data:image/jpeg;base64,...), one per page.
        Returns empty list if rendering fails or PyMuPDF is not installed.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error(
            "PyMuPDF (fitz) is not installed - cannot render scanned PDF pages. "
            "Install with: pip install PyMuPDF"
        )
        return []

    data_uris = []
    try:
        pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
        page_count = min(len(pdf_doc), max_pages)

        for page_num in range(page_count):
            try:
                page = pdf_doc[page_num]
                # Render at 200 DPI (default is 72; matrix scales by 200/72).
                zoom = 200 / 72
                matrix = fitz.Matrix(zoom, zoom)
                pixmap = page.get_pixmap(matrix=matrix)
                img_bytes = pixmap.tobytes("jpeg")
                # Apply the same dimension and base64-size caps as encode_image_base64
                # so that large scanned films (USG, X-ray) don't exceed the API limits.
                data_uri = encode_image_base64(img_bytes, "image/jpeg")
                data_uris.append(data_uri)
            except Exception as e:
                logger.warning(
                    "Failed to render PDF page %d as image: %s",
                    page_num, str(e),
                )

        pdf_doc.close()
    except Exception as e:
        logger.error("PDF page rendering failed: %s", str(e))

    return data_uris


# ---------------------------------------------------------------------------
# Async bulkhead wrappers
# ---------------------------------------------------------------------------

async def async_encode_image_base64(file_bytes: bytes, mime_type: str) -> str:
    """Non-blocking wrapper - runs Pillow resize/compress in _RENDER_POOL."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_RENDER_POOL, encode_image_base64, file_bytes, mime_type)


async def async_extract_pdf_text(file_bytes: bytes) -> str:
    """Non-blocking wrapper - runs PyPDF2 parsing in _RENDER_POOL."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_RENDER_POOL, extract_pdf_text, file_bytes)


async def async_render_pdf_pages_as_images(
    file_bytes: bytes, max_pages: int = 3
) -> list[str]:
    """Non-blocking wrapper - runs PyMuPDF rasterisation in _RENDER_POOL."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _RENDER_POOL, render_pdf_pages_as_images, file_bytes, max_pages
    )
