# Initial migration for NiCat v1.2 Sprint 11; generated for the supplied model schema.
import uuid
import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("academics", "__first__"),
    ]
    operations = [
        migrations.CreateModel(
            name="Contribution",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("title", models.CharField(max_length=160)),
                ("body", models.TextField(validators=[django.core.validators.MinLengthValidator(100), django.core.validators.MaxLengthValidator(6000)])),
                ("author_declaration", models.BooleanField(default=False)),
                ("allow_display", models.BooleanField(default=False)),
                ("allow_ai_use", models.BooleanField(default=False)),
                ("content_sha256", models.CharField(max_length=64, db_index=True)),
                ("possible_duplicate", models.BooleanField(default=False)),
                ("state", models.CharField(max_length=24, default="pending_review", db_index=True, choices=[("pending_review", "Pending review"), ("rights_hold", "Rights hold"), ("approved", "Approved for later publication"), ("rejected", "Rejected"), ("withdrawn", "Withdrawn")])),
                ("rights_review_note", models.TextField(blank=True)),
                ("academic_review_note", models.TextField(blank=True)),
                ("rights_reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("academic_reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="contributions", to=settings.AUTH_USER_MODEL)),
                ("unit", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="student_contributions", to="academics.unit")),
                ("rights_reviewed_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="rights_reviewed_contributions", to=settings.AUTH_USER_MODEL, null=True, blank=True)),
                ("academic_reviewed_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="academically_reviewed_contributions", to=settings.AUTH_USER_MODEL, null=True, blank=True)),
            ],
            options={
                "ordering": ["-created_at"],
                "permissions": [("review_contribution_rights", "Can verify student contribution rights"), ("review_contribution_content", "Can approve student contribution academic content")],
            },
        ),
        migrations.CreateModel(
            name="ContributionDecision",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("action", models.CharField(max_length=30, choices=[("rights_cleared", "Rights cleared"), ("rights_hold", "Rights hold"), ("approved", "Academic approval"), ("rejected", "Rejected"), ("withdrawn", "Withdrawn")])),
                ("rationale", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="contribution_decisions", to=settings.AUTH_USER_MODEL)),
                ("contribution", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="decisions", to="contributions.contribution")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="contribution",
            index=models.Index(fields=["student", "created_at"], name="contrib_student_created_idx"),
        ),
    ]
