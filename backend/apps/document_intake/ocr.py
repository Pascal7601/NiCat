"""Bounded OCR fallback for already malware-scanned private PDF uploads.

This module performs *extraction only*. The caller is responsible for ensuring
that ClamAV has marked the original file clean before invoking it.

PDFium (via pypdfium2) renders each page into a temporary grayscale PNG;
Tesseract then reads that PNG locally. No document is sent to a cloud service.
The temporary images are removed automatically.

Production: execute in a restricted, resource-limited worker/container. Python
timeouts bound the Tesseract child processes, but cannot stop a stalled PDFium
native rendering call by themselves.
"""

from __future__ import annotations

import math
import re
import subprocess
import tempfile
import time
from pathlib import Path


class OCRExtractionError(RuntimeError):
    """A predictable OCR failure. This is never evidence of a clean extraction."""


_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_LANGUAGE = re.compile(r"^[A-Za-z0-9_+]{1,50}$")


def ocr_pdf(
    path: str | Path,
    *,
    tesseract_cmd: str = "tesseract",
    language: str = "eng",
    dpi: int = 180,
    max_pages: int = 80,
    min_chars: int = 100,
    max_chars: int = 100_000,
    max_pixels: int = 9_000_000,
    max_file_bytes: int = 8 * 1024 * 1024,
    per_page_timeout: int = 25,
    total_timeout: int = 240,
) -> tuple[str, int]:
    """Return (recognized_text, PDF_page_count), or raise OCRExtractionError.

    The output is an extraction *candidate*, not verified academic content.
    The 100-character threshold only checks minimum quantity; a human still
    needs to check OCR quality, formulas, MCQ options, and correct page order.
    """
    path = Path(path)
    if not path.is_file() or path.stat().st_size > max_file_bytes:
        raise OCRExtractionError("Private PDF is missing or exceeds the intake size limit")
    if not _LANGUAGE.fullmatch(language):
        raise OCRExtractionError("Invalid OCR language configuration")
    if not 72 <= dpi <= 300:
        raise OCRExtractionError("OCR DPI must be between 72 and 300")
    if not tesseract_cmd or not str(tesseract_cmd).strip():
        raise OCRExtractionError("Tesseract executable is not configured")

    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise OCRExtractionError("pypdfium2 is not installed") from exc

    deadline = time.monotonic() + total_timeout
    pdf = None
    try:
        try:
            pdf = pdfium.PdfDocument(str(path))
            page_count = len(pdf)
        except Exception as exc:
            raise OCRExtractionError("PDF renderer could not open the PDF") from exc

        if not 1 <= page_count <= max_pages:
            raise OCRExtractionError(f"PDF must contain 1 to {max_pages} pages")

        recognized_parts: list[str] = []
        recognized_chars = 0
        with tempfile.TemporaryDirectory(prefix="nicat-ocr-") as directory:
            image_path = Path(directory) / "page.png"
            for index in range(page_count):
                if time.monotonic() >= deadline:
                    raise OCRExtractionError("OCR job exceeded its total time limit")

                page = None
                bitmap = None
                picture = None
                try:
                    page = pdf[index]
                    width, height = page.get_size()
                    pixel_width = math.ceil(width * dpi / 72)
                    pixel_height = math.ceil(height * dpi / 72)
                    if (
                        pixel_width <= 0 or pixel_height <= 0
                        or pixel_width * pixel_height > max_pixels
                    ):
                        raise OCRExtractionError("A PDF page exceeds OCR image size limits")

                    bitmap = page.render(scale=dpi / 72, grayscale=True)
                    picture = bitmap.to_pil()
                    picture.save(image_path, format="PNG")
                except OCRExtractionError:
                    raise
                except Exception as exc:
                    raise OCRExtractionError(f"Could not render PDF page {index + 1}") from exc
                finally:
                    # Close the PIL view before the native PDFium buffer.
                    if picture is not None:
                        picture.close()
                    if bitmap is not None:
                        bitmap.close()
                    if page is not None:
                        page.close()

                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise OCRExtractionError("OCR job exceeded its total time limit")
                timeout = min(per_page_timeout, remaining)
                try:
                    result = subprocess.run(
                        [str(tesseract_cmd), str(image_path), "stdout", "-l", language, "--psm", "3"],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=timeout,
                        check=False,
                    )
                except FileNotFoundError as exc:
                    raise OCRExtractionError("Tesseract executable was not found") from exc
                except subprocess.TimeoutExpired as exc:
                    raise OCRExtractionError(f"Tesseract timed out on page {index + 1}") from exc
                except OSError as exc:
                    raise OCRExtractionError("Could not start Tesseract") from exc
                finally:
                    image_path.unlink(missing_ok=True)

                if result.returncode != 0:
                    # Do not expose original paths or Tesseract stderr to the UI.
                    raise OCRExtractionError(f"Tesseract failed on page {index + 1}")

                page_text = _CONTROL_CHARS.sub("", result.stdout).strip()
                recognized_chars += len(page_text)
                if page_text:
                    recognized_parts.append(f"[Page {index + 1}]\n{page_text}")
                if sum(map(len, recognized_parts)) >= max_chars:
                    break

        if recognized_chars < min_chars:
            raise OCRExtractionError("OCR produced too little readable text; manual transcription may be needed")
        return "\n\n".join(recognized_parts)[:max_chars], page_count
    finally:
        if pdf is not None:
            pdf.close()
