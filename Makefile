.PHONY: install dev test lint typecheck format format-check build clean report

PYTHON := python

install:
	$(PYTHON) -m pip install -e ".[dev]"

dev:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest

lint:
	ruff check .

typecheck:
	mypy behave_modern_file_reports tests

format:
	ruff check --fix .
	ruff format .

format-check:
	ruff format --check .

build:
	$(PYTHON) -m build

twine-check:
	twine check dist/*

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache .coverage coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

report:
	cd examples/behave_project && \
	python -m behave -f behave-modern-txt -o report.txt && \
	python -m behave -f behave-modern-docx -o report.docx && \
	python -m behave -f behave-modern-pdf -o report.pdf
