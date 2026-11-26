"""Deterministic structural checks only; semantic correctness requires a human."""
import hashlib
import re
from decimal import Decimal, InvalidOperation


def normalize(value):
    return re.sub(r"\s+", " ", (value or "").strip()).casefold()


def fingerprint(value):
    return hashlib.sha256(normalize(value).encode("utf-8")).hexdigest()


def validate_candidate(data, source_text):
    problems = []
    kind = data.get("kind")
    prompt = data.get("prompt")
    if kind not in ("mcq", "short", "essay"):
        problems.append("unsupported_type")
    if not isinstance(prompt, str) or not 15 <= len(prompt.strip()) <= 1600:
        problems.append("invalid_prompt")
    explanation = data.get("explanation")
    if not isinstance(explanation, str) or not 20 <= len(explanation.strip()) <= 4000:
        problems.append("invalid_explanation")
    quote = data.get("evidence_quote")
    if not isinstance(quote, str) or len(quote.strip()) < 15 or normalize(quote) not in normalize(source_text):
        problems.append("source_quote_not_found")
    options = data.get("options", [])
    idx = data.get("correct_index")
    if kind == "mcq":
        if not isinstance(options, list) or len(options) != 4 or any(not isinstance(v, str) or not 1 <= len(v.strip()) <= 350 for v in options):
            problems.append("invalid_options")
        elif len({normalize(v) for v in options}) != 4:
            problems.append("duplicate_options")
        if type(idx) is not int or idx not in range(4):
            problems.append("invalid_correct_index")
    elif options or idx is not None:
        problems.append("written_question_has_mcq_fields")
    rubric = data.get("rubric", [])
    if kind in ("short", "essay"):
        if not isinstance(rubric, list) or not 1 <= len(rubric) <= 8:
            problems.append("missing_rubric")
        else:
            total = Decimal("0")
            for item in rubric:
                if not isinstance(item, dict) or not 5 <= len(str(item.get("criterion", ""))) <= 300:
                    problems.append("invalid_rubric_criterion")
                    break
                try:
                    points = Decimal(str(item.get("marks")))
                    if not Decimal("0") < points <= Decimal("20"):
                        raise ValueError("marks range")
                    total += points
                except (InvalidOperation, ValueError, TypeError):
                    problems.append("invalid_rubric_marks")
                    break
            if total > 40:
                problems.append("rubric_total_too_large")
    elif rubric:
        problems.append("mcq_has_rubric")
    return sorted(set(problems))
