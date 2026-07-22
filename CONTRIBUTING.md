# Contributing to behave-modern-file-report

Thank you for your interest in contributing! This document covers everything you need to get started.

## Prerequisites

- Python 3.11 or higher
- Git
- A GitHub account

## Quick Start

```bash
git clone https://github.com/MathiasPaulenko/behave-modern-file-report.git
cd behave-modern-file-report
pip install -e ".[dev,pdf,docx]"
pre-commit install
```

## Development Workflow

### 1. Create a branch

```bash
git checkout -b feat/my-feature
```

Use conventional branch prefixes:

- `feat/` — new features
- `fix/` — bug fixes
- `docs/` — documentation only
- `refactor/` — code restructuring without behavior change
- `test/` — test additions or fixes
- `chore/` — tooling, CI, dependencies

### 2. Make your changes

Follow the existing code style:

- **Linter**: `ruff check` and `ruff format`
- **Type checker**: `mypy --strict`
- **Line length**: 100 characters
- **Type hints**: required on all function signatures
- **Docstrings**: Google style for all public functions, classes, and modules

### 3. Run checks locally

```bash
make lint          # ruff check + format check
make typecheck     # mypy --strict
make test          # pytest with verbose output
```

Or run everything at once:

```bash
ruff check . && ruff format --check . && mypy behave_modern_file_report tests && python -m pytest tests/ -v --cov=behave_modern_file_report --cov-fail-under=100
```

### 4. Commit your changes

We use [Conventional Commits](https://www.conventionalcommits.org/):

```text
feat: add PDF attachment inline rendering
fix: handle empty scenario name in TXT writer
docs: update installation instructions
```

Pre-commit hooks will run automatically on commit. If they modify files, stage and commit again.

### 5. Push and open a Pull Request

```bash
git push origin feat/my-feature
```

Open a PR against `main` and fill in the pull request template.

## Code Style

- **Python**: PEP 8, enforced by ruff
- **Imports**: `isort`-compatible ordering (handled by ruff)
- **Typing**: strict mypy with no `Any` in public APIs (use `Any` only for Behave objects in the collector)
- **Testing**: 100% coverage required — every new line of code must be tested
- **Docstrings**: Google style

### Example docstring

```python
def format_duration(seconds: float) -> str:
    """Format a duration in seconds as a human-readable string.

    Args:
        seconds: Duration in seconds.

    Returns:
        A string like ``"1.23s"`` or ``"456ms"``.
    """
```

## Testing

Tests live in `tests/` and use `pytest`. Run the full suite with:

```bash
make test
```

For coverage details:

```bash
python -m pytest tests/ -v --cov=behave_modern_file_report --cov-report=term-missing
```

Coverage must stay at 100%. If you add code, add tests.

## Project Structure

```text
behave_modern_file_report/
    __init__.py          # Public API exports
    collector.py         # Behave event -> RunSummary
    models.py            # Pure dataclasses (no external deps)
    base_formatter.py    # BaseFileFormatter (Behave Formatter subclass)
    txt_formatter.py     # Behave formatter for TXT
    txt_writer.py        # TXT serialization
    docx_formatter.py    # Behave formatter for DOCX
    docx_writer.py       # DOCX serialization (python-docx)
    pdf_formatter.py     # Behave formatter for PDF
    pdf_writer.py        # PDF serialization (WeasyPrint/ReportLab)
    html_renderer.py     # Jinja2 HTML rendering for PDF
    attachments.py       # Public attachment API
    utils.py             # Shared helpers
    templates/           # Default Jinja2 templates (HTML + CSS)
tests/
    test_collector.py
    test_models.py
    test_txt_writer.py
    ...
examples/
    behave_project/      # Example project with sample feature
```

## Reporting Issues

- **Bugs**: Use the bug report issue template. Include Python version, OS, Behave version, and a minimal reproduction.
- **Features**: Use the feature request issue template. Describe the use case and expected behavior.

## Release Process

Releases are automated. To cut a new release:

1. Bump the version in `behave_modern_file_report/__init__.py`
2. Update `CHANGELOG.md` with the new version and changes
3. Commit and push to `main`
4. The release workflow handles tagging, PyPI publishing, and GitHub Release creation automatically

## Questions?

Feel free to open a [Discussion](https://github.com/MathiasPaulenko/behave-modern-file-report/discussions) or an issue.
