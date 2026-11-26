import uuid
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("academics", "__first__"),
        ("questions", "__first__"),
        ("resources", "__first__"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SourceExcerpt",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, serialize=False, editable=False)),
                ("text", models.TextField(help_text="Short reviewed excerpt, not an entire copyrighted document")),
                ("state", models.CharField(max_length=12, default="draft", choices=[
                    ("draft", "Awaiting source review"), ("approved", "Approved for tutor use"),
                    ("withdrawn", "Withdrawn")])),
                ("approved_at", models.DateTimeField(null=True, blank=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("reference", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                    related_name="tutor_excerpts", to="resources.sourcereference")),
                ("topic", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                    related_name="tutor_excerpts", to="academics.topic")),
                ("approved_by", models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="approved_tutor_excerpts", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["topic_id", "created_at"],
                "permissions": [("approve_tutor_content", "May approve tutor sources and explanations")],
                "indexes": [models.Index(fields=["topic", "state"], name="tutor_topic_state_idx")],
            },
        ),
        migrations.CreateModel(
            name="TutorExplanation",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, serialize=False, editable=False)),
                ("explanation", models.TextField()),
                ("common_mistake", models.TextField()),
                ("practice_tip", models.TextField()),
                ("state", models.CharField(max_length=12, default="draft", choices=[
                    ("draft", "Academic review required"), ("published", "Reviewer-approved"),
                    ("withdrawn", "Withdrawn")])),
                ("version", models.PositiveIntegerField(default=1)),
                ("prompt_version", models.CharField(max_length=32, default="grounded-explanation-v1")),
                ("model_name", models.CharField(max_length=100)),
                ("source_fingerprint", models.CharField(max_length=64)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("revision", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                    related_name="tutor_explanations", to="questions.questionrevision")),
                ("citations", models.ManyToManyField(related_name="tutor_explanations",
                    to="study_tutor.sourceexcerpt")),
                ("generated_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                    related_name="drafted_tutor_explanations", to=settings.AUTH_USER_MODEL)),
                ("approved_by", models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="published_tutor_explanations", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="tutorexplanation",
            constraint=models.UniqueConstraint(fields=["revision"], condition=Q(state="published"),
                name="unique_published_tutor_explanation_per_revision"),
        ),
        migrations.AddConstraint(
            model_name="tutorexplanation",
            constraint=models.UniqueConstraint(fields=["revision", "version"],
                name="unique_tutor_explanation_version"),
        ),
    ]
