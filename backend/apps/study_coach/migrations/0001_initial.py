# NiCat Sprint 8 — additive initial schema, no changes to existing apps.
import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("attempts", "0001_initial"),
        ("study_tutor", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="TutorDailyBudget",
            fields=[
                ("day", models.DateField(primary_key=True, serialize=False)),
                ("requests", models.PositiveIntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name="TutorFollowUp",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("question", models.CharField(max_length=500)),
                ("draft_answer", models.TextField(blank=True)),
                ("published_answer", models.TextField(blank=True)),
                ("state", models.CharField(choices=[
                    ("draft", "Awaiting academic review"),
                    ("published", "Reviewer-approved"),
                    ("rejected", "Rejected"),
                    ("withdrawn", "Withdrawn"),
                ], default="draft", max_length=12)),
                ("quota_day", models.DateField(db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("attempt_question", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="study_followups", to="attempts.attemptquestion",
                )),
                ("explanation", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="followups", to="study_tutor.tutorexplanation",
                )),
                ("student", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="study_followups", to=settings.AUTH_USER_MODEL,
                )),
                ("reviewed_by", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="reviewed_study_followups", to=settings.AUTH_USER_MODEL,
                )),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("citations", models.ManyToManyField(
                    blank=True, related_name="study_followups", to="study_tutor.sourceexcerpt",
                )),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="tutorfollowup",
            index=models.Index(fields=["student", "quota_day"], name="coach_student_day_idx"),
        ),
    ]
