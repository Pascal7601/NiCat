"""Sprint 15 contract tests. Run inside NiCat's existing Django pytest environment."""
import hashlib
import uuid
import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import override_settings
from rest_framework.test import APIClient

from apps.academics.models import Topic
from apps.document_intake.models import DocumentSubmission
from apps.past_papers.models import PaperQuestionDraft, PaperVariationJob, PaperVariationCandidate
from apps.past_papers.services import (
    PaperConflict, is_eligible_paper, extract_question_drafts, update_question,
    review_question, queue_variations, process_variation_job, review_variation,
)
from .test_document_intake import intake


def grant(user, codename, app="past_papers"):
    user.user_permissions.add(Permission.objects.get(content_type__app_label=app, codename=codename))
    user = get_user_model().objects.get(pk=user.pk)
    return user


@pytest.fixture
def paper_setup(intake):
    owner, outsider, rights, academic, programme, unit, data, root = intake
    User = get_user_model()
    extractor = User.objects.create_user(email="paper-extractor@example.test", password="TestPassword!44", is_staff=True)
    verifier = User.objects.create_user(email="paper-verifier@example.test", password="TestPassword!44", is_staff=True)
    requester = User.objects.create_user(email="paper-requester@example.test", password="TestPassword!44", is_staff=True)
    candidate_reviewer = User.objects.create_user(email="paper-candidate-reviewer@example.test", password="TestPassword!44", is_staff=True)
    extractor = grant(extractor, "extract_paper_questions")
    verifier = grant(verifier, "verify_paper_questions")
    requester = grant(requester, "request_paper_variations")
    candidate_reviewer = grant(candidate_reviewer, "review_paper_variations")
    topic = Topic.objects.create(unit=unit, title="Cloud concepts")
    transcript = (
        "QUESTION 1\nExplain cloud deployment models and their impact on business continuity. (5 marks)\n"
        "QUESTION 2\nList cloud service models and describe their common uses. (6 marks)\n"
    )
    doc = DocumentSubmission.objects.create(
        student=owner, programme=programme, unit=unit, title="Academic cloud paper",
        document_type="licensed_paper", rights_basis="permission", rights_evidence="Permission was verified by an authorized independent reviewer.",
        author_or_owner="University", permit_question_generation=True,
        original_filename="cloud.pdf", stored_key=f"{uuid.uuid4().hex}.pdf", file_type="pdf",
        size_bytes=1234, sha256="e" * 64, scan_state="clean", extraction_state="done",
        extracted_text=transcript, page_count=2, state=DocumentSubmission.State.APPROVED,
        rights_reviewed_by=rights, academic_reviewed_by=academic,
    )
    return dict(doc=doc, owner=owner, outsider=outsider, rights=rights, academic=academic,
                extractor=extractor, verifier=verifier, requester=requester,
                candidate_reviewer=candidate_reviewer, topic=topic)


@pytest.mark.django_db
def test_only_approved_papers_qualify_and_no_auto_publication(paper_setup):
    a = paper_setup
    assert is_eligible_paper(a["doc"])
    assert PaperQuestionDraft.objects.count() == 0
    a["doc"].document_type = "original_notes"
    assert not is_eligible_paper(a["doc"])
    a["doc"].document_type = "licensed_paper"
    a["doc"].state = a["doc"].State.WITHDRAWN
    assert not is_eligible_paper(a["doc"])


@pytest.mark.django_db
def test_staff_extract_correction_and_independent_visual_verification(paper_setup):
    a = paper_setup
    doc = a["doc"]
    assert extract_question_drafts(document_id=doc.pk, actor=a["extractor"]) == 2
    questions = list(PaperQuestionDraft.objects.filter(document=doc))
    assert all(q.state == q.State.DRAFT and q.page_number is None for q in questions)
    from apps.questions.models import Question
    assert not Question.objects.filter(topic=a["topic"]).exists()
    q = questions[0]
    with pytest.raises(PaperConflict, match="separate"):
        review_question(question_id=q.pk, actor=a["extractor"], action="verify",
                        rationale="I checked the original page very carefully.")
    q = update_question(question_id=q.pk, actor=a["extractor"],
        corrected_text="Explain three cloud deployment models and their uses. (5 marks)",
        page_number=1, marks=5, topic_id=a["topic"].pk,
        verified_answer_context="The public, private, and hybrid cloud deployment models differ in ownership, hosting, and access controls for organizations.",
        rationale="The original first question and marks have been checked and transcribed.")
    with pytest.raises(PaperConflict, match="separate"):
        review_question(question_id=q.pk, actor=a["extractor"], action="verify",
                        rationale="I checked page one visually and verified question wording.")
    verified = review_question(question_id=q.pk, actor=a["verifier"], action="verify",
                               rationale="Compared source page one to text, marks and academic topic.")
    assert verified.state == q.State.VERIFIED
    assert verified.events.filter(action="question_verify").exists()
    assert not Question.objects.filter(topic=a["topic"]).exists()
    with pytest.raises(PaperConflict, match="immutable"):
        update_question(question_id=q.pk, actor=a["extractor"], corrected_text=q.corrected_text,
                        page_number=1, marks=5, topic_id=a["topic"].pk,
                        verified_answer_context=q.verified_answer_context,
                        rationale="Attempting to rewrite an already verified original question.")


@pytest.mark.django_db
def test_mock_variation_never_approved_and_source_revocation_blocks(paper_setup):
    a = paper_setup
    q = PaperQuestionDraft.objects.create(
        document=a["doc"], position=1, source_sha256=a["doc"].sha256,
        extracted_sha256=hashlib.sha256(a["doc"].extracted_text.encode()).hexdigest(),
        original_ocr_text="Question 1", corrected_text="Explain the advantages of private and public cloud hosting.",
        page_number=1, topic=a["topic"], marks=5,
        verified_answer_context="Private hosting controls resource sharing, while public hosting uses provider infrastructure and broader shared services for scalability.",
        state=PaperQuestionDraft.State.VERIFIED, extracted_by=a["extractor"], verified_by=a["verifier"])
    with override_settings(NICAT_QUESTION_AI_PROVIDER="mock", NICAT_QUESTION_AI_REMOTE_ENABLED=False):
        job = queue_variations(question_id=q.pk, actor=a["requester"],count=2,kind="mcq",difficulty="easy")
        assert process_variation_job(job.pk) == "complete"
        candidate = PaperVariationCandidate.objects.filter(job=job).first()
        assert "mock_test_data" in candidate.validation_errors
        with pytest.raises(PaperConflict, match="Mock"):
            review_variation(candidate_id=candidate.pk, actor=a["candidate_reviewer"],action="approve",
                             note="This mock test content is not an actual academic question.")
        doc = a["doc"]
        doc.state = doc.State.WITHDRAWN
        doc.save(update_fields=["state"])
        with pytest.raises(PaperConflict):
            queue_variations(question_id=q.pk, actor=a["requester"],count=1,kind="mcq",difficulty="easy")


@pytest.mark.django_db
def test_staff_preview_requires_authentication(paper_setup):
    doc = paper_setup["doc"]
    url = f"/api/v1/past-papers/{doc.pk}/page/1/"
    anonymous = APIClient()
    with override_settings(NICAT_PAST_PAPERS_ENABLED=True):
        assert anonymous.get(url).status_code in (401, 403)
        client = APIClient()
        client.force_authenticate(user=paper_setup["outsider"])
        assert client.get(url).status_code == 403


@pytest.mark.django_db
def test_notes_only_existing_generator_when_policy_enabled(paper_setup):
    """Becomes green after the documented one-line Sprint 14 source filter."""
    from apps.question_generation.services import valid_source
    doc = paper_setup["doc"]
    assert not valid_source(doc), "Sprint 14 must exclude licensed_paper from notes generator"

@pytest.mark.django_db
def test_remote_variations_require_independent_vendor_authorization(paper_setup):
    a = paper_setup
    q = PaperQuestionDraft.objects.create(
        document=a["doc"], position=1, source_sha256=a["doc"].sha256,
        extracted_sha256=hashlib.sha256(a["doc"].extracted_text.encode()).hexdigest(),
        corrected_text="Explain private cloud versus public cloud hosting and security.",
        original_ocr_text="Q1: cloud hosting?", page_number=1, topic=a["topic"],
        verified_answer_context="Private clouds give dedicated organizational resources; public clouds use shared provider resources with separate security controls.",
        state=PaperQuestionDraft.State.VERIFIED, extracted_by=a["extractor"], verified_by=a["verifier"])
    with override_settings(NICAT_QUESTION_AI_PROVIDER="openai", NICAT_QUESTION_AI_REMOTE_ENABLED=True):
        with pytest.raises(PaperConflict, match="authorization"):
            queue_variations(question_id=q.pk, actor=a["requester"], count=1, kind="mcq", difficulty="easy")


@pytest.mark.django_db
def test_original_uploader_cannot_extract_ocr_questions(paper_setup):
    a = paper_setup
    owner = grant(a["owner"], "extract_paper_questions")
    owner.is_staff = True
    owner.save(update_fields=["is_staff"])
    with pytest.raises(PaperConflict, match="uploader"):
        extract_question_drafts(document_id=a["doc"].pk, actor=owner)
