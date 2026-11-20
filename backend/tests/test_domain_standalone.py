"""Stdlib-only regression tests; runnable without Django installed."""
import sys
from pathlib import Path
import unittest
from decimal import Decimal
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apps.attempts.grading import mark_single_choice, percentage

class GradingContractTests(unittest.TestCase):
    def test_correct_choice_awards_all_marks(self):
        self.assertEqual(mark_single_choice(selected_option_id="abc", correct_option_id="abc", possible_marks=Decimal("2.50")), Decimal("2.50"))
    def test_wrong_or_missing_choice_awards_zero(self):
        for choice in ("wrong", None):
            self.assertEqual(mark_single_choice(selected_option_id=choice, correct_option_id="abc", possible_marks=Decimal("2.50")), Decimal("0"))
    def test_percentage_rounding(self):
        self.assertEqual(percentage(earned=Decimal("22"), possible=Decimal("30")), Decimal("73.33"))
    def test_invalid_percentages_rejected(self):
        with self.assertRaises(ValueError): percentage(earned=Decimal("20"), possible=Decimal("10"))

if __name__ == "__main__": unittest.main()
