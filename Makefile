.DELETE_ON_ERROR:

all: install-hooks test

test:
	tox

venv:
	tox -evenv

install-hooks: venv
	pre-commit install -f --install-hooks

clean:
	rm -rf build/ dist/ .tox/ virtualenv_run/ *.egg-info/
	rm -f .coverage
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -delete

.PHONY: all test venv install-hooks clean
