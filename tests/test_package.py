"""Smoke test that the package is importable and exposes a version."""

from __future__ import annotations

import behave_modern_file_reports


def test_version() -> None:
    """The package exposes a version string."""
    assert isinstance(behave_modern_file_reports.__version__, str)
    assert behave_modern_file_reports.__version__ == "1.0.0"
