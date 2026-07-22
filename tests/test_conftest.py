"""Tests for shared conftest fixtures."""

from __future__ import annotations

from behave_modern_file_reports.models import (
    FeatureSummary,
    ReportOptions,
    RunSummary,
    ScenarioResult,
    Step,
)


def test_sample_step(sample_step: Step) -> None:
    """sample_step fixture provides a fully populated Step."""
    assert sample_step.keyword == "Given"
    assert sample_step.status == "passed"
    assert len(sample_step.attachments) == 1
    assert sample_step.attachments[0].is_image is True
    assert sample_step.logs == ["Navigated to /login"]


def test_sample_failed_step(sample_failed_step: Step) -> None:
    """sample_failed_step fixture provides a failed Step with error."""
    assert sample_failed_step.status == "failed"
    assert sample_failed_step.error is not None
    assert sample_failed_step.error.exception_type == "AssertionError"


def test_sample_scenario(sample_scenario: ScenarioResult) -> None:
    """sample_scenario fixture provides a ScenarioResult with steps and background."""
    assert sample_scenario.name == "Login succeeds"
    assert sample_scenario.status == "failed"
    assert len(sample_scenario.steps) == 2
    assert sample_scenario.background is not None
    assert len(sample_scenario.background.steps) == 1
    assert sample_scenario.tags == ["smoke", "auth"]


def test_sample_passed_scenario(sample_passed_scenario: ScenarioResult) -> None:
    """sample_passed_scenario fixture provides a fully passed scenario."""
    assert sample_passed_scenario.status == "passed"
    assert len(sample_passed_scenario.steps) == 3
    assert all(s.status == "passed" for s in sample_passed_scenario.steps)


def test_sample_feature(sample_feature: FeatureSummary) -> None:
    """sample_feature fixture provides a FeatureSummary with two scenarios."""
    assert sample_feature.name == "Login"
    assert len(sample_feature.scenarios) == 2
    assert sample_feature.failed == 1
    assert sample_feature.passed == 1
    assert sample_feature.derive_status() == "failed"


def test_sample_run(sample_run: RunSummary) -> None:
    """sample_run fixture provides a RunSummary with environment metadata."""
    assert sample_run.run_id == "run_abc123def456"
    assert len(sample_run.features) == 1
    assert sample_run.total_scenarios == 2
    assert sample_run.environment.python_version == "3.14.0"
    assert sample_run.environment.git_branch == "main"
    assert sample_run.status == "failed"


def test_sample_options(sample_options: ReportOptions) -> None:
    """sample_options fixture provides default ReportOptions."""
    assert sample_options.only_failed is False
    assert sample_options.title == "Behave Modern Report"
    assert sample_options.pdf_engine == "weasyprint"


def test_sample_options_custom(sample_options_custom: ReportOptions) -> None:
    """sample_options_custom fixture provides customized ReportOptions."""
    assert sample_options_custom.only_failed is True
    assert sample_options_custom.title == "QA Report"
    assert sample_options_custom.pdf_engine == "reportlab"
    assert sample_options_custom.txt_ascii is True


def test_sample_user_data(sample_user_data: dict[str, str]) -> None:
    """sample_user_data fixture provides bmfr.* keys."""
    assert "bmfr.only_failed" in sample_user_data
    assert sample_user_data["bmfr.only_failed"] == "true"
    assert "bmfr.pdf.title" in sample_user_data


def test_sample_user_data_resolves_options(sample_user_data: dict[str, str]) -> None:
    """ReportOptions.from_dict resolves sample_user_data correctly."""
    opts = ReportOptions.from_dict(sample_user_data, format_key="pdf")
    assert opts.only_failed is True
    assert opts.title == "PDF Override Title"
    assert opts.logo == "assets/pdf_logo.png"
    assert opts.pdf_engine == "reportlab"
