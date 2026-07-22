"""Smoke test that the package is importable and exposes a version."""

from __future__ import annotations

import re

import behave_modern_file_reports


def test_version() -> None:
    """The package exposes a valid semantic version string."""
    assert isinstance(behave_modern_file_reports.__version__, str)
    assert re.match(r"^\d+\.\d+\.\d+$", behave_modern_file_reports.__version__)
