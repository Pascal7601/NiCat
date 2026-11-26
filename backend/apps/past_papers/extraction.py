"""Conservative OCR boundary suggestions. NEVER claims correctness or page numbers.

Only anchored question headers cause a split; all suggestions require human visual
comparison with the original scan. OCR often drops question headers, so the
fallback is one unverified editable chunk, not a pretend full parse.
"""
import re

QUESTION_HEADER = re.compile(
    r"(?im)^(?=\S)\s*(?:QUESTION\s+\d{1,2}\b|Q\s*\.?\s*\d{1,2}\s*[:.)-]|\d{1,2}\s*[.)]\s+(?=[A-Z]))"
)


def suggest_question_chunks(text: str, *, max_questions: int = 40, max_chunk: int = 3000):
    text = (text or "").strip()
    if not text:
        return []
    indices = [m.start() for m in QUESTION_HEADER.finditer(text)]
    if not indices:
        return [(text[:max_chunk], ["manual_split_required", "page_unverified", "ocr_unverified"])]
    chunks = []
    for idx, pos in enumerate(indices[:max_questions]):
        end = indices[idx + 1] if idx + 1 < len(indices) else len(text)
        chunk = text[pos:end].strip()
        if len(chunk) < 15:
            continue
        flags = ["page_unverified", "ocr_unverified"]
        if len(chunk) > max_chunk:
            flags.append("possible_truncation")
        chunks.append((chunk[:max_chunk], flags))
    return chunks or [(text[:max_chunk], ["manual_split_required", "ocr_unverified", "page_unverified"])]
