"""Shared pytest fixtures and configuration."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from behave_modern_file_report.models import (
    Attachment,
    Background,
    Environment,
    ErrorInfo,
    FeatureSummary,
    ReportOptions,
    RunSummary,
    ScenarioResult,
    Step,
)
from behave_modern_file_report.utils import STATUS_PASSED


@pytest.fixture
def sample_step() -> Step:
    """Return a fully populated Step instance."""
    return Step(
        keyword="Given",
        name="the user is logged in",
        status=STATUS_PASSED,
        duration=0.045,
        location="features/login.feature:10",
        text=None,
        error=None,
        attachments=[
            Attachment(
                name="screenshot_01.png",
                mime_type="image/png",
                data_base64="iVBORw0KGgo=",
                step_name="the user is logged in",
                scenario_name="Login succeeds",
                feature_name="Login",
            ),
        ],
        logs=["Navigated to /login"],
    )


@pytest.fixture
def sample_failed_step() -> Step:
    """Return a failed Step with error info."""
    return Step(
        keyword="Then",
        name="the dashboard should be visible",
        status="failed",
        duration=1.234,
        location="features/login.feature:15",
        error=ErrorInfo(
            message="Element not found: #dashboard",
            traceback="Traceback (most recent call last):\n  ...",
            exception_type="AssertionError",
        ),
        attachments=[],
        logs=[],
    )


@pytest.fixture
def sample_scenario(sample_step: Step, sample_failed_step: Step) -> ScenarioResult:
    """Return a ScenarioResult with two steps (one passed, one failed)."""
    return ScenarioResult(
        name="Login succeeds",
        status="failed",
        duration=1.279,
        tags=["smoke", "auth"],
        location="features/login.feature:8",
        feature_name="Login",
        rule_name="",
        is_outline=False,
        outline_name="",
        steps=[sample_step, sample_failed_step],
        background=Background(
            name="Background",
            steps=[
                Step(keyword="Given", name="the app is running", status=STATUS_PASSED),
            ],
        ),
        description="A user logs in and sees the dashboard.",
        error=sample_failed_step.error,
    )


@pytest.fixture
def sample_passed_scenario() -> ScenarioResult:
    """Return a fully passed ScenarioResult."""
    return ScenarioResult(
        name="User can log out",
        status=STATUS_PASSED,
        duration=0.030,
        tags=["smoke"],
        location="features/login.feature:20",
        feature_name="Login",
        steps=[
            Step(keyword="Given", name="the user is logged in", status=STATUS_PASSED),
            Step(keyword="When", name="the user clicks logout", status=STATUS_PASSED),
            Step(keyword="Then", name="the login page is shown", status=STATUS_PASSED),
        ],
    )


@pytest.fixture
def sample_feature(
    sample_scenario: ScenarioResult,
    sample_passed_scenario: ScenarioResult,
) -> FeatureSummary:
    """Return a FeatureSummary with two scenarios."""
    return FeatureSummary(
        name="Login",
        description="Login and logout flows.",
        status="failed",
        duration=1.309,
        tags=["auth"],
        location="features/login.feature:1",
        scenarios=[sample_scenario, sample_passed_scenario],
        background=Background(
            name="Background",
            steps=[
                Step(keyword="Given", name="the app is running", status=STATUS_PASSED),
            ],
        ),
    )


@pytest.fixture
def sample_run(sample_feature: FeatureSummary) -> RunSummary:
    """Return a RunSummary with one feature."""
    return RunSummary(
        run_id="run_abc123def456",
        title="Behave Modern Report",
        project_name="My Project",
        start_time="2025-01-01T10:00:00+00:00",
        end_time="2025-01-01T10:00:05+00:00",
        duration=5.0,
        features=[sample_feature],
        environment=Environment(
            python_version="3.14.0",
            behave_version="1.2.6",
            platform="linux",
            hostname="ci-runner-01",
            cwd="/home/runner/project",
            command="behave -f behave-modern-pdf -o report.pdf",
            user="runner",
            cpu_count=4,
            git_branch="main",
            git_commit="abc1234",
        ),
    )


@pytest.fixture
def sample_options() -> ReportOptions:
    """Return a ReportOptions instance with default values."""
    return ReportOptions()


@pytest.fixture
def sample_options_custom() -> ReportOptions:
    """Return a ReportOptions instance with custom branding."""
    return ReportOptions(
        only_failed=True,
        primary_color="#1E90FF",
        title="QA Report",
        project_name="Custom Project",
        include_attachments=False,
        max_traceback_lines=20,
        txt_width=120,
        txt_ascii=True,
        pdf_engine="reportlab",
    )


@pytest.fixture
def sample_user_data() -> dict[str, str]:
    """Return a dict simulating Behave's config.userdata with bmfr.* keys."""
    return {
        "bmfr.only_failed": "true",
        "bmfr.title": "QA Report",
        "bmfr.primary_color": "#1E90FF",
        "bmfr.project_name": "Custom Project",
        "bmfr.include_attachments": "false",
        "bmfr.max_traceback_lines": "20",
        "bmfr.txt_width": "120",
        "bmfr.txt_ascii": "true",
        "bmfr.pdf_engine": "reportlab",
        "bmfr.pdf.title": "PDF Override Title",
        "bmfr.pdf.logo": "assets/pdf_logo.png",
    }


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> str:
    """Return a temporary directory path for report output tests."""
    return str(tmp_path)


# ---------------------------------------------------------------------------
# Behave mock fixtures (SimpleNamespace-based, no behave import required)
# ---------------------------------------------------------------------------


@pytest.fixture
def behave_feature() -> SimpleNamespace:
    """Return a mock Behave Feature object."""
    return SimpleNamespace(
        name="Login",
        tags=["auth", "smoke"],
        location="features/login.feature:1",
        description="Login and logout flows.",
    )


@pytest.fixture
def behave_background() -> SimpleNamespace:
    """Return a mock Behave Background object."""
    return SimpleNamespace(
        name="Background",
        location="features/login.feature:3",
    )


@pytest.fixture
def behave_scenario() -> SimpleNamespace:
    """Return a mock Behave Scenario object."""
    return SimpleNamespace(
        name="Login succeeds",
        tags=["smoke"],
        location="features/login.feature:8",
        feature=SimpleNamespace(name="Login", tags=["auth"], location=""),
        is_outline=False,
        rule=None,
        description="A user logs in and sees the dashboard.",
    )


@pytest.fixture
def behave_outline_scenario() -> SimpleNamespace:
    """Return a mock Behave Scenario Outline object."""
    return SimpleNamespace(
        name="Login with <user>",
        tags=["data-driven"],
        location="features/login.feature:30",
        feature=SimpleNamespace(name="Login", tags=["auth"], location=""),
        is_outline=True,
        rule=None,
        description=None,
    )


@pytest.fixture
def behave_passed_step() -> SimpleNamespace:
    """Return a mock Behave Step with passed status."""
    return SimpleNamespace(
        keyword="Given",
        name="the user is on the login page",
        status="passed",
        location="features/login.feature:10",
        duration=0.045,
        text=None,
        error=None,
        exception=None,
        error_message=None,
    )


@pytest.fixture
def behave_failed_step() -> SimpleNamespace:
    """Return a mock Behave Step with failed status and an exception."""
    try:
        raise AssertionError("Dashboard element not found") from None
    except AssertionError as exc:
        return SimpleNamespace(
            keyword="Then",
            name="the dashboard should be visible",
            status="failed",
            location="features/login.feature:15",
            duration=1.234,
            text=None,
            error=exc,
            exception=None,
            error_message=None,
        )


@pytest.fixture
def behave_skipped_step() -> SimpleNamespace:
    """Return a mock Behave Step with skipped status."""
    return SimpleNamespace(
        keyword="Then",
        name="a welcome message is shown",
        status="skipped",
        location="features/login.feature:18",
        duration=0.0,
        text=None,
        error=None,
        exception=None,
        error_message=None,
    )


@pytest.fixture
def behave_undefined_step() -> SimpleNamespace:
    """Return a mock Behave Step with undefined status."""
    return SimpleNamespace(
        keyword="Then",
        name="an undefined step",
        status="undefined",
        location="features/login.feature:20",
        duration=0.0,
        text=None,
        error=None,
        exception=None,
        error_message=None,
    )

