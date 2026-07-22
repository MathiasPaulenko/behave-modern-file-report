"""Generate golden files for regression tests.

Run with: python -m tests.golden._generate
"""

from __future__ import annotations

import io

from behave_modern_file_reports.html_renderer import render_html
from behave_modern_file_reports.models import (
    Environment,
    ErrorInfo,
    FeatureSummary,
    ReportOptions,
    RunSummary,
    ScenarioResult,
    Step,
)
from behave_modern_file_reports.txt_writer import TXTWriter


def _make_run() -> RunSummary:
    """Create a deterministic run summary for golden file generation."""
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


def _generate_txt() -> str:
    """Generate the TXT report output."""
    run = _make_run()
    opts = ReportOptions(title="Test Report", project_name="My Project")
    writer = TXTWriter(opts)
    stream = io.StringIO()
    writer.write(run, stream)
    return stream.getvalue()


def _generate_html() -> str:
    """Generate the HTML intermediate output."""
    run = _make_run()
    opts = ReportOptions(title="Test Report", project_name="My Project")
    return render_html(run, opts)


def main() -> None:
    """Write golden files to disk."""
    import pathlib

    golden_dir = pathlib.Path(__file__).parent

    txt_path = golden_dir / "report.txt"
    txt_path.write_text(_generate_txt(), encoding="utf-8")
    print(f"Wrote {txt_path}")

    html_path = golden_dir / "report.html"
    html_path.write_text(_generate_html(), encoding="utf-8")
    print(f"Wrote {html_path}")


if __name__ == "__main__":
    main()
