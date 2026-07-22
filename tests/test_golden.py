"""Golden file regression tests for TXT and HTML output.

These tests generate output from a deterministic run summary, normalize
volatile values (timestamps, durations), and compare against golden files
stored in ``tests/golden/``.

To regenerate golden files run::

    python -m tests.golden._generate
"""

from __future__ import annotations

import io
import re
from pathlib import Path

from behave_modern_file_report.html_renderer import render_html
from behave_modern_file_report.models import (
    Environment,
    ErrorInfo,
    FeatureSummary,
    ReportOptions,
    RunSummary,
    ScenarioResult,
    Step,
)
from behave_modern_file_report.txt_writer import TXTWriter

_GOLDEN_DIR = Path(__file__).parent / "golden"


def _make_run() -> RunSummary:
    """Create a deterministic run summary matching the golden files."""
    step1 = Step(
        keyword="Given ",
        name="the user is on the login page",
        status="passed",
        duration=0.05,
        location="features/login.feature:7",
    )
    step2 = Step(
        keyword="When ",
        name="the user enters valid credentials",
        status="passed",
        duration=0.10,
        location="features/login.feature:8",
    )
    step3 = Step(
        keyword="Then ",
        name="the user should see the dashboard",
        status="passed",
        duration=0.03,
        location="features/login.feature:9",
    )
    scenario1 = ScenarioResult(
        name="Successful login",
        status="passed",
        duration=0.18,
        tags=["smoke"],
        location="features/login.feature:5",
        steps=[step1, step2, step3],
    )

    failed_step = Step(
        keyword="When ",
        name="the user enters invalid credentials",
        status="failed",
        duration=0.08,
        location="features/login.feature:15",
        error=ErrorInfo(
            message="Invalid credentials error",
            traceback=(
                "Traceback (most recent call last):\n"
                "  File features/login.feature:15\n"
                "AssertionError"
            ),
            exception_type="AssertionError",
        ),
    )
    scenario2 = ScenarioResult(
        name="Failed login",
        status="failed",
        duration=0.08,
        tags=["regression"],
        location="features/login.feature:13",
        steps=[step1, failed_step],
    )

    feature = FeatureSummary(
        name="Login",
        description="User authentication feature",
        status="failed",
        duration=0.26,
        tags=["auth"],
        location="features/login.feature:1",
        scenarios=[scenario1, scenario2],
    )

    return RunSummary(
        run_id="run-001",
        title="Test Report",
        project_name="My Project",
        start_time="2025-01-01T10:00:00+00:00",
        end_time="2025-01-01T10:00:05+00:00",
        duration=5.0,
        features=[feature],
        environment=Environment(
            python_version="3.12.0",
            platform="linux",
            hostname="test-host",
        ),
    )


def _normalize_txt(text: str) -> str:
    """Normalize volatile values in TXT output."""
    # Normalize timestamps
    text = re.sub(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}",
        "<TIMESTAMP>",
        text,
    )
    return text


def _normalize_html(text: str) -> str:
    """Normalize volatile values in HTML output."""
    # Normalize timestamps
    text = re.sub(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}",
        "<TIMESTAMP>",
        text,
    )
    return text


# ---------------------------------------------------------------------------
# TXT golden file
# ---------------------------------------------------------------------------


def test_txt_matches_golden() -> None:
    """TXT output matches the golden file."""
    run = _make_run()
    opts = ReportOptions(title="Test Report", project_name="My Project")
    writer = TXTWriter(opts)
    stream = io.StringIO()
    writer.write(run, stream)
    actual = _normalize_txt(stream.getvalue())

    golden_path = _GOLDEN_DIR / "report.txt"
    expected = _normalize_txt(golden_path.read_text(encoding="utf-8"))

    assert actual == expected, (
        f"TXT output does not match golden file.\n"
        f"To regenerate: python -m tests.golden._generate\n"
        f"--- Expected (first 500 chars) ---\n{expected[:500]}\n"
        f"--- Actual (first 500 chars) ---\n{actual[:500]}"
    )


# ---------------------------------------------------------------------------
# HTML golden file
# ---------------------------------------------------------------------------


def test_html_matches_golden() -> None:
    """HTML intermediate output matches the golden file."""
    run = _make_run()
    opts = ReportOptions(title="Test Report", project_name="My Project")
    actual = _normalize_html(render_html(run, opts))

    golden_path = _GOLDEN_DIR / "report.html"
    expected = _normalize_html(golden_path.read_text(encoding="utf-8"))

    assert actual == expected, (
        f"HTML output does not match golden file.\n"
        f"To regenerate: python -m tests.golden._generate\n"
        f"--- Expected (first 500 chars) ---\n{expected[:500]}\n"
        f"--- Actual (first 500 chars) ---\n{actual[:500]}"
    )


# ---------------------------------------------------------------------------
# Golden file detection
# ---------------------------------------------------------------------------


def test_golden_txt_file_exists() -> None:
    """Golden TXT file exists."""
    assert (_GOLDEN_DIR / "report.txt").is_file()


def test_golden_html_file_exists() -> None:
    """Golden HTML file exists."""
    assert (_GOLDEN_DIR / "report.html").is_file()
