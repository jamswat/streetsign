.PHONY: migrate backup

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
