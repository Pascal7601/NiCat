"""Focused OCR unit/smoke tests. Test documents contain only synthetic text."""
import os
import shutil
from pathlib import Path

import pytest

from apps.document_intake.ocr import OCRExtractionError, ocr_pdf


def make_image_only_pdf(path):
    """Make a scanned-looking PDF without a text layer using pypdfium2 + Pillow."""
    from PIL import Image, ImageDraw, ImageFont
    # Use reportlab for constructing a PDF with image-only contents.
    from reportlab.pdfgen.canvas import Canvas

    image = Image.new("RGB", (1240, 1754), "white")
    draw = ImageDraw.Draw(image)
    lines = [
        "CLOUD COMPUTING UNIVERSITY PRACTICE EXAMINATION",
        "QUESTION ONE: Explain three key benefits of virtualization.",
        "QUESTION TWO: Compare public and private cloud deployment models.",
        "QUESTION THREE: Describe access controls and data protection.",
    ]
    font = _test_font(ImageFont)
    for index, line in enumerate(lines):
        draw.text((60, 80 + index * 100), line, fill="black", font=font)
    image.save(path.with_suffix(".png"))
    pdf = Canvas(str(path), pagesize=(620, 877))
    pdf.drawImage(str(path.with_suffix(".png")), 0, 0, width=620, height=877)
    pdf.save()
    return path


def _test_font(ImageFont):
    for name in ("DejaVuSans.ttf", "arial.ttf", "C:/Windows/Fonts/arial.ttf"):
        try:
            return ImageFont.truetype(name, 30)
        except OSError:
            continue
    return ImageFont.load_default(size=30)


def test_missing_tesseract_fails_closed(tmp_path):
    path = make_image_only_pdf(tmp_path / "scanned.pdf")
    with pytest.raises(OCRExtractionError, match="Tesseract executable was not found"):
        ocr_pdf(path, tesseract_cmd="there-is-no-tesseract-4567")


def test_image_only_pdf_can_be_ocr_extracted(tmp_path):
    tesseract_cmd = os.getenv("NICAT_TESSERACT_CMD", "tesseract")
    if not shutil.which(tesseract_cmd) and not Path(tesseract_cmd).is_file():
        pytest.skip("Tesseract executable not installed")
    path = make_image_only_pdf(tmp_path / "scanned.pdf")
    text, pages = ocr_pdf(path, tesseract_cmd=tesseract_cmd)
    assert pages == 1
    assert "CLOUD COMPUTING" in text
    assert "virtualization" in text.lower()
    assert len(text) >= 100


def test_max_pdf_pages_is_enforced(tmp_path):
    path = make_image_only_pdf(tmp_path / "scanned.pdf")
    with pytest.raises(OCRExtractionError, match="1 to 0 pages"):
        ocr_pdf(path, max_pages=0)
