.PHONY: migrate

_INSTRUCTIONS:
	echo 'make all, or make clean.'

clean:
	rm -rf .virtualenv/ database.db config.py

all: .virtualenv config.py database.db migrate

.virtualenv:
	python3 -m venv .virtualenv
	./.virtualenv/bin/pip install -r requirements.txt

config.py:
	python3 .setup/make_initial_config_file.py > config.py

database.db:
	echo 'make()' | ./.virtualenv/bin/python3 -i db.py

migrate:
	echo 'run_migrations()' | ./.virtualenv/bin/python3 -i db.py 
