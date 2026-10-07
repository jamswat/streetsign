.PHONY: all clean migrate backup run test lint audit check

_INSTRUCTIONS:
	echo 'make all, or make clean.'

clean:
	rm -rf .venv database.db config.py

all: .venv .githooks config.py database.db migrate

.venv:
	uv sync --extra dev

.githooks:
	cp .setup/hooks/pre-commit .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit

config.py:
	python3 .setup/make_initial_config_file.py > config.py

database.db:
	echo 'make()' | ./.venv/bin/python3 -i db.py

migrate:
	echo 'run_migrations()' | ./.venv/bin/python3 -i db.py

backup:
	./.venv/bin/python3 scripts/backup_db.py

run:
	./.venv/bin/python3 run.py

test:
	./.venv/bin/python3 -m pytest

lint:
	./.venv/bin/python3 -m pylint --fail-under=9.0 streetsign_server/

audit:
	uv export --no-dev --no-emit-project -o /tmp/requirements.txt
	./.venv/bin/python3 -m pip_audit -r /tmp/requirements.txt

check: lint test audit
