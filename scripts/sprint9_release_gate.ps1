# NiCat Sprint 9 local non-destructive test gate.
# Run from repo root in an activated Python virtual environment.
# Does NOT deploy, change DB rows, set real keys or perform migrations.
$ErrorActionPreference = "Stop"

function Invoke-Checked($name, [scriptblock]$command) {
    Write-Host "`n=== $name ===" -ForegroundColor Cyan
    & $command
    if ($LASTEXITCODE -ne 0) {
        throw "$name failed with exit code $LASTEXITCODE"
    }
}

if (-not (Test-Path "backend/manage.py")) {
    throw "Run this script from the NiCat repository root."
}
Invoke-Checked "Sprint 9 backend guard tests" {
    python -m pytest -q backend/tests/test_beta_guard.py
}
Invoke-Checked "Sprint 6-8 backend regression tests" {
    python -m pytest -q backend/tests/test_study_coach.py backend/tests/test_study_tutor.py backend/tests/test_ai_marking.py backend/tests/test_reviewer_workflow.py
}
Invoke-Checked "Django system checks" {
    python backend/manage.py check
}
Invoke-Checked "Migration drift (read-only)" {
    python backend/manage.py makemigrations --check --dry-run
}
Push-Location frontend
try {
    Invoke-Checked "Frontend security route policy" {
        node --test tests/sprint9-security-route-policy.test.mjs
    }
    Invoke-Checked "Frontend TypeScript" {
        npx tsc --noEmit
    }
    Invoke-Checked "Frontend build" {
        npm run build
    }
} finally {
    Pop-Location
}
Write-Host "`nLocal automated gate passed. Production checks and manual beta approvals remain required." -ForegroundColor Green
