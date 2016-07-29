.DELETE_ON_ERROR:

all: production

production:
	@true

test:
	tox

venv:
	tox -evenv

install-hooks:
	pre-commit install -f --install-hooks

clean:
	rm -rf build/ dist/ .tox/ virtualenv_run/ *.egg-info/
	rm -f .coverage
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -delete

.PHONY: all production test venv install-hooks clean
