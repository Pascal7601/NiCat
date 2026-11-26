import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("attempts", "__first__"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AIMarkingSuggestion",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("proposed_marks", models.DecimalField(decimal_places=2, max_digits=6)),
                ("breakdown", models.JSONField(default=list)),
                ("feedback", models.TextField()),
                ("model_name", models.CharField(max_length=100)),
                ("answer_sha256", models.CharField(max_length=64)),
                ("prompt_version", models.CharField(default="essay-review-v1", max_length=30)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("review_status", models.CharField(choices=[("pending", "Awaiting human marking"), ("accepted", "Reviewer chose same mark"), ("overridden", "Reviewer chose different mark")], default="pending", max_length=16)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("generated_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ai_suggestions_requested", to=settings.AUTH_USER_MODEL)),
                ("grade_item", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="ai_suggestion", to="attempts.gradeitem")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="ai_suggestions_reviewed", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "AI marking proposal (not a final grade)", "ordering": ["-created_at"]},
        ),
    ]
