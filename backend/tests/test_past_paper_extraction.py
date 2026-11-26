"""Pure extraction tests; runnable without Django by loading the standalone parser."""
from pathlib import Path
import importlib.util

FILE = Path(__file__).resolve().parents[1] / 'apps' / 'past_papers' / 'extraction.py'
spec = importlib.util.spec_from_file_location('nicat_paper_extraction', FILE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_numbered_questions_become_unverified_drafts():
    data = 'QUESTION 1\nDescribe three cloud models.\nQUESTION 2\nExplain SaaS, PaaS and IaaS.'
    chunks = module.suggest_question_chunks(data)
    assert len(chunks) == 2
    assert 'QUESTION 1' in chunks[0][0]
    assert 'QUESTION 2' in chunks[1][0]
    assert all('page_unverified' in flags for _, flags in chunks)


def test_unstructured_ocr_requires_manual_split():
    chunks = module.suggest_question_chunks('Cloud paper text without useful question numbering. ' * 5)
    assert len(chunks) == 1
    assert 'manual_split_required' in chunks[0][1]


def test_empty_ocr_produces_no_questions():
    assert module.suggest_question_chunks('  ') == []


def test_never_marks_questions_verified():
    data = '1. Explain cloud security in detail.\n2. Discuss private and public networks.'
    chunks = module.suggest_question_chunks(data)
    assert chunks
    assert all('ocr_unverified' in flags for _, flags in chunks)
