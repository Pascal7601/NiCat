"""Concurrent submissions need real PostgreSQL row locks, not SQLite semantics."""
import concurrent.futures
from decimal import Decimal
import pytest
from django.db import connection, close_old_connections
from apps.accounts.models import User
from apps.academics.models import Topic, Unit
from apps.attempts.models import Attempt, Grade, GradingEvent
from apps.attempts.services import start_attempt, submit_attempt
from apps.exams.models import ExamQuestion, ExamTemplate, ExamVersion
from apps.questions.models import ChoiceOption, Question, QuestionRevision


@pytest.mark.django_db(transaction=True)
def test_two_submissions_cannot_duplicate_grade():
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL-only concurrency guarantee")
    student = User.objects.create_user("concurrent@example.test", "ExamplePass!9912")
    reviewer = User.objects.create_superuser("concurrent-reviewer@example.test", "ExamplePass!9912")
    unit = Unit.objects.create(title="Concurrency Fixture", slug="concurrency-pg-test")
    topic = Topic.objects.create(unit=unit, title="Stacks")
    q = Question.objects.create(topic=topic)
    rev = QuestionRevision.objects.create(question=q, number=1,
        kind="single_choice", provenance="original_practice", prompt="Select a valid stack operation",
        max_marks=Decimal("1.00"))
    ChoiceOption.objects.create(revision=rev, position=1, text="pop", is_correct=True)
    ChoiceOption.objects.create(revision=rev, position=2, text="enqueue", is_correct=False)
    rev.reviewed_by = reviewer
    rev.status = QuestionRevision.Status.PUBLISHED
    rev.save()
    template = ExamTemplate.objects.create(unit=unit, title="Concurrency")
    version = ExamVersion.objects.create(template=template, number=1, duration_seconds=600)
    ExamQuestion.objects.create(version=version, revision=rev, position=1)
    version.is_published = True
    version.save()
    attempt = start_attempt(exam=version, student=student)

    def submit():
        close_old_connections()
        try:
            result = submit_attempt(attempt_id=attempt.id, student=student)
            return result.pk
        finally:
            connection.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        result_ids = list(pool.map(lambda _: submit(), (1, 2)))
    assert result_ids == [attempt.pk, attempt.pk]
    assert Grade.objects.filter(attempt=attempt).count() == 1
    assert GradingEvent.objects.filter(grade__attempt=attempt, details__type="submission").count() == 1
    attempt.refresh_from_db()
    assert attempt.state == Attempt.State.GRADED_FINAL
