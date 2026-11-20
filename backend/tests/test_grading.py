from decimal import Decimal
import pytest
from apps.attempts.grading import mark_single_choice, percentage


def test_single_choice_exact_marks_and_zero():
    assert mark_single_choice(selected_option_id="b", correct_option_id="b", possible_marks=Decimal("2.50")) == Decimal("2.50")
    assert mark_single_choice(selected_option_id="a", correct_option_id="b", possible_marks=Decimal("2.50")) == 0
    assert mark_single_choice(selected_option_id=None, correct_option_id="b", possible_marks=Decimal("2.50")) == 0


def test_percentage_rounds_conventionally():
    assert percentage(earned=Decimal("22"), possible=Decimal("30")) == Decimal("73.33")


def test_invalid_grade_fails_closed():
    with pytest.raises(ValueError):
        percentage(earned=Decimal("12"), possible=Decimal("10"))
