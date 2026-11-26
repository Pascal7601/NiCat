"""Read-only release preflight; reports aggregate counts, never students' data.

Usage (development rehearsal): python backend/manage.py nicat_beta_audit --with-db
Usage (real beta): NICAT_BETA_ENV=production ... python backend/manage.py nicat_beta_audit --with-db --strict
The command does not modify database rows or deploy anything.
"""
from django.apps import apps
from django.conf import settings
from django.core.checks import Tags, run_checks
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


class Command(BaseCommand):
    help = "Read-only NiCat beta security, content, and migrations preflight."

    def add_arguments(self, parser):
        parser.add_argument("--with-db", action="store_true", help="Also check migrations and published study content.")
        parser.add_argument("--strict", action="store_true", help="Exit non-zero if there are blocking findings.")
        parser.add_argument("--min-coverage", type=float, default=90.0,
                            help="Minimum coverage for pilot exam questions (default: 90 percent).")

    def handle(self, *args, **options):
        if not 0 <= options["min_coverage"] <= 100:
            raise CommandError("--min-coverage must be between 0 and 100")
        findings = []

        def finding(level, label, message):
            findings.append((level, label, message))

        env = getattr(settings, "NICAT_BETA_ENV", "development")
        finding("INFO", "environment", f"NICAT_BETA_ENV={env}; DEBUG={settings.DEBUG}")
        if env != "production":
            finding("WARN", "release_mode", "Not evaluating production beta settings; use NICAT_BETA_ENV=production with production settings.")
        elif not options["with_db"]:
            finding("BLOCK", "database_skipped", "Run with --with-db for a complete production preflight.")

        for problem in run_checks(tags=[Tags.security], include_deployment_checks=True):
            level = "BLOCK" if problem.is_serious() else "WARN"
            finding(level, problem.id, problem.msg)

        if options["with_db"]:
            try:
                self._database_findings(finding, options["min_coverage"])
            except Exception as exc:
                # Fail closed. Never print exception details: URLs, SQL, database
                # credentials or connection strings can appear in driver errors.
                finding("BLOCK", "database_audit", f"Database audit could not complete ({type(exc).__name__}).")

        for level, label, message in findings:
            self.stdout.write(f"[{level}] {label}: {message}")
        blocks = sum(1 for level, _, _ in findings if level == "BLOCK")
        warnings = sum(1 for level, _, _ in findings if level == "WARN")
        self.stdout.write(f"TOTAL: {blocks} blocking finding(s), {warnings} warning(s).")
        if options["strict"] and (blocks or env != "production"):
            raise CommandError("NiCat beta release gate FAILED. Do not deploy.")
        if not blocks and env == "production" and options["with_db"]:
            self.stdout.write(self.style.SUCCESS("Automated preflight passed; manual QA and approvals are still mandatory."))

    def _database_findings(self, finding, minimum):
        if connection.vendor != "postgresql":
            finding("BLOCK", "postgres", "Beta requires PostgreSQL, not the SQLite development fallback.")
        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        pending = executor.migration_plan(targets)
        if pending:
            finding("BLOCK", "migrations", f"{len(pending)} unapplied migration(s) remain.")
            return  # Other queries may fail because the schema is incomplete.
        finding("INFO", "migrations", "All registered migrations are applied.")

        required = ("apps.exams", "apps.questions", "apps.study_tutor", "apps.study_coach")
        if not all(apps.is_installed(name) for name in required):
            finding("BLOCK", "apps", "Sprint 7 and 8 apps, exams and questions must be registered.")
            return

        from apps.exams.models import ExamQuestion
        from apps.questions.models import QuestionRevision
        from apps.study_tutor.models import TutorExplanation
        from apps.study_tutor.services import student_payload
        from apps.study_coach.models import TutorFollowUp

        revision_ids = set(ExamQuestion.objects.filter(
            version__is_published=True,
            version__show_explanations_after_submit=True,
        ).values_list("revision_id", flat=True).distinct())
        if not revision_ids:
            finding("BLOCK", "pilot_exams", "No eligible published exam questions found.")
            return
        # An explanation only counts if current publication, citations, rights
        # status and source fingerprint pass the actual student release service.
        valid = 0
        for revision in QuestionRevision.objects.filter(pk__in=revision_ids).select_related("question__topic"):
            if student_payload(revision=revision) is not None:
                valid += 1
        coverage = 100 * valid / len(revision_ids)
        finding("INFO", "explanations", f"{valid}/{len(revision_ids)} eligible pilot question revisions have release-valid explanations ({coverage:.1f}%).")
        if coverage < minimum:
            finding("BLOCK", "coverage", f"Coverage is under the {minimum:.1f}% pilot threshold.")

        # Both existing demo test data and generated mock placeholders must be
        # removed/reviewed before real students get access; only aggregate counts.
        mock_explanations = TutorExplanation.objects.filter(
            state=TutorExplanation.State.PUBLISHED,
            explanation__icontains="MOCK TEST DATA",
        ).count()
        mock_followups = TutorFollowUp.objects.filter(
            state=TutorFollowUp.State.PUBLISHED,
            published_answer__icontains="MOCK TEST DATA",
        ).count()
        if mock_explanations or mock_followups:
            finding("BLOCK", "mock_content", f"Published mock placeholders detected: {mock_explanations} explanation(s), {mock_followups} follow-up(s).")

        if not getattr(settings, "NICAT_AI_TUTOR_ENABLED", False):
            finding("WARN", "tutor_disabled", "Tutor delivery feature flag is disabled; approved explanations will not be visible.")
        if not getattr(settings, "NICAT_AI_RECOMMENDATIONS_ENABLED", False):
            finding("WARN", "revision_disabled", "Revision recommendations are disabled for the beta.")
