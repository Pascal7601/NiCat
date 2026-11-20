.PHONY: install db run check migrations migrate test schema lint
install:
	python -m pip install -r requirements-dev.txt
db:
	docker compose up -d db
run:
	cd backend && python manage.py runserver
check:
	cd backend && python manage.py check
# First bootstrap: migrations are deliberately not claimed generated/reviewed in this offline environment.
migrations:
	bash scripts/bootstrap-migrations.sh
migrate:
	cd backend && python manage.py migrate
test:
	pytest -q
schema:
	cd backend && python manage.py spectacular --file ../docs/openapi.generated.yaml --validate
lint:
	ruff check backend

.PHONY: verify seed-dsa
verify:
	bash scripts/verify-backend.sh
seed-dsa:
	cd backend && python manage.py seed_dsa_pilot
