"""Pure deterministic grading functions. Never grade written answers automatically."""
from decimal import Decimal, ROUND_HALF_UP


def mark_single_choice(*, selected_option_id: str | None, correct_option_id: str,
                       possible_marks: Decimal) -> Decimal:
    if possible_marks <= 0:
        raise ValueError("Possible marks must be positive")
    return possible_marks if selected_option_id == correct_option_id else Decimal("0.00")


def percentage(*, earned: Decimal, possible: Decimal) -> Decimal:
    if possible <= 0 or earned < 0 or earned > possible:
        raise ValueError("Invalid grade totals")
    return (earned * Decimal("100") / possible).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
