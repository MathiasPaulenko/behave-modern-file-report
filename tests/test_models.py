"""Tests for behave_modern_file_reports.models."""

from __future__ import annotations

from typing import Any

import pytest

from behave_modern_file_reports.models import (
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


def test_error_info_defaults() -> None:
    """ErrorInfo can be created with defaults."""
    info = ErrorInfo()
    assert info.message == ""
    assert info.traceback == ""
    assert info.exception_type == ""


def test_error_info_values() -> None:
    """ErrorInfo stores provided values."""
    info = ErrorInfo(message="boom", traceback="trace", exception_type="ValueError")
    assert info.message == "boom"
    assert info.traceback == "trace"
    assert info.exception_type == "ValueError"


def test_attachment_defaults() -> None:
    """Attachment has sensible defaults."""
    att = Attachment(name="file.txt")
    assert att.name == "file.txt"
    assert att.mime_type == "application/octet-stream"
    assert att.data_base64 == ""
    assert att.text is None
    assert att.step_name == ""
    assert att.scenario_name == ""
    assert att.feature_name == ""


def test_attachment_is_image() -> None:
    """is_image returns True for image MIME types."""
    att = Attachment(name="logo.png", mime_type="image/png", data_base64="abc")
    assert att.is_image is True
    assert att.is_text is False


def test_attachment_is_text() -> None:
    """is_text returns True for text MIME types or when text content is set."""
    att = Attachment(name="log.txt", mime_type="text/plain", text="hello")
    assert att.is_text is True
    assert att.is_image is False

    att2 = Attachment(name="data.json", mime_type="application/json", text='{"k": 1}')
    assert att2.is_text is True


def test_attachment_is_screenshot() -> None:
    """is_screenshot returns True for images named as screenshots."""
    att = Attachment(name="screenshot_01.png", mime_type="image/png", data_base64="abc")
    assert att.is_screenshot is True

    att2 = Attachment(name="logo.png", mime_type="image/png", data_base64="abc")
    assert att2.is_screenshot is False


def test_attachment_is_screenshot_not_image() -> None:
    """is_screenshot returns False for non-images even if name contains screenshot."""
    att = Attachment(name="screenshot.txt", mime_type="text/plain", text="hello")
    assert att.is_screenshot is False


def test_step_defaults() -> None:
    """Step has sensible defaults."""
    step = Step(keyword="Given", name="a step")
    assert step.keyword == "Given"
    assert step.name == "a step"
    assert step.status == "untested"
    assert step.duration == 0.0
    assert step.location == ""
    assert step.text is None
    assert step.error is None
    assert step.attachments == []
    assert step.logs == []


def test_step_with_error_and_attachments() -> None:
    """Step stores error and attachments correctly."""
    error = ErrorInfo(message="fail", exception_type="AssertionError")
    att = Attachment(name="screenshot.png", mime_type="image/png")
    step = Step(
        keyword="Then",
        name="it should work",
        status="failed",
        duration=1.5,
        location="features/test.feature:10",
        error=error,
        attachments=[att],
        logs=["line 1", "line 2"],
    )
    assert step.status == "failed"
    assert step.error is not None
    assert step.error.message == "fail"
    assert len(step.attachments) == 1
    assert step.attachments[0].name == "screenshot.png"
    assert step.logs == ["line 1", "line 2"]


def test_step_attachments_independent() -> None:
    """Each Step instance has its own attachments list."""
    step1 = Step(keyword="Given", name="a")
    step2 = Step(keyword="Given", name="b")
    step1.attachments.append(Attachment(name="x"))
    assert len(step2.attachments) == 0


def test_step_logs_independent() -> None:
    """Each Step instance has its own logs list."""
    step1 = Step(keyword="Given", name="a")
    step2 = Step(keyword="Given", name="b")
    step1.logs.append("entry")
    assert len(step2.logs) == 0


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------


def test_background_defaults() -> None:
    """Background has sensible defaults."""
    bg = Background()
    assert bg.name == ""
    assert bg.steps == []


def test_background_with_steps() -> None:
    """Background stores steps."""
    step = Step(keyword="Given", name="a precondition")
    bg = Background(name="Background", steps=[step])
    assert bg.name == "Background"
    assert len(bg.steps) == 1


# ---------------------------------------------------------------------------
# ScenarioResult
# ---------------------------------------------------------------------------


def test_scenario_result_defaults() -> None:
    """ScenarioResult has sensible defaults."""
    scenario = ScenarioResult(name="My scenario")
    assert scenario.name == "My scenario"
    assert scenario.status == "untested"
    assert scenario.duration == 0.0
    assert scenario.tags == []
    assert scenario.steps == []
    assert scenario.background is None
    assert scenario.is_outline is False
    assert scenario.error is None


def test_scenario_result_with_steps() -> None:
    """ScenarioResult stores steps and tags."""
    step = Step(keyword="Given", name="a step", status="passed")
    scenario = ScenarioResult(
        name="Login",
        status="passed",
        tags=["smoke"],
        steps=[step],
    )
    assert len(scenario.steps) == 1
    assert scenario.tags == ["smoke"]


def test_scenario_result_independent_lists() -> None:
    """Each ScenarioResult has its own lists."""
    s1 = ScenarioResult(name="a")
    s2 = ScenarioResult(name="b")
    s1.steps.append(Step(name="x"))
    s1.tags.append("t")
    assert len(s2.steps) == 0
    assert len(s2.tags) == 0


# ---------------------------------------------------------------------------
# FeatureSummary
# ---------------------------------------------------------------------------


def _make_scenario(status: str) -> ScenarioResult:
    return ScenarioResult(name=f"scn-{status}", status=status)


def test_feature_summary_no_scenarios() -> None:
    """FeatureSummary with no scenarios has zero pass_rate and untested status."""
    feat = FeatureSummary(name="Empty")
    assert feat.total_scenarios == 0
    assert feat.passed == 0
    assert feat.failed == 0
    assert feat.pass_rate == 0.0
    assert feat.derive_status() == "untested"


def test_feature_summary_all_passed() -> None:
    """FeatureSummary derives passed status when all scenarios pass."""
    feat = FeatureSummary(
        name="F",
        scenarios=[_make_scenario("passed"), _make_scenario("passed")],
    )
    assert feat.passed == 2
    assert feat.pass_rate == 1.0
    assert feat.derive_status() == "passed"


def test_feature_summary_with_failure() -> None:
    """FeatureSummary derives failed status when any scenario fails."""
    feat = FeatureSummary(
        name="F",
        scenarios=[_make_scenario("passed"), _make_scenario("failed")],
    )
    assert feat.failed == 1
    assert feat.derive_status() == "failed"


def test_feature_summary_undefined() -> None:
    """FeatureSummary derives undefined when any scenario is undefined."""
    feat = FeatureSummary(
        name="F",
        scenarios=[_make_scenario("passed"), _make_scenario("undefined")],
    )
    assert feat.undefined == 1
    assert feat.derive_status() == "undefined"


def test_feature_summary_all_skipped() -> None:
    """FeatureSummary derives skipped when all scenarios are skipped."""
    feat = FeatureSummary(
        name="F",
        scenarios=[_make_scenario("skipped"), _make_scenario("skipped")],
    )
    assert feat.skipped == 2
    assert feat.derive_status() == "skipped"


def test_feature_summary_mixed_not_all_skipped() -> None:
    """FeatureSummary with passed+skipped derives skipped."""
    feat = FeatureSummary(
        name="F",
        scenarios=[_make_scenario("passed"), _make_scenario("skipped")],
    )
    assert feat.derive_status() == "skipped"


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------


def test_environment_defaults() -> None:
    """Environment has sensible defaults."""
    env = Environment()
    assert env.python_version == ""
    assert env.cpu_count == 0
    assert env.git_branch == ""


def test_environment_with_values() -> None:
    """Environment stores provided values."""
    env = Environment(
        python_version="3.14.0",
        platform="win32",
        hostname="myhost",
        git_branch="main",
        git_commit="abc123",
    )
    assert env.python_version == "3.14.0"
    assert env.git_branch == "main"


def test_environment_capture_handles_missing_user_and_cwd(monkeypatch: pytest.MonkeyPatch) -> None:
    """Environment.capture tolerates failures from os.getcwd and getpass.getuser."""
    monkeypatch.setattr("os.getcwd", lambda: (_ for _ in ()).throw(OSError("no cwd")))
    monkeypatch.setattr("getpass.getuser", lambda: (_ for _ in ()).throw(KeyError("no user")))
    env = Environment.capture()
    assert env.cwd == ""
    assert env.user == ""


def test_environment_capture_handles_missing_behave_and_git(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Environment.capture tolerates missing behave package and git commands."""
    def _raise(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("not available")

    monkeypatch.setattr("importlib.metadata.version", _raise)
    monkeypatch.setattr("subprocess.run", _raise)
    env = Environment.capture()
    assert env.behave_version == ""
    assert env.git_branch == ""
    assert env.git_commit == ""


# ---------------------------------------------------------------------------
# RunSummary
# ---------------------------------------------------------------------------


def test_run_summary_no_features() -> None:
    """RunSummary with no features has zero counts and untested status."""
    run = RunSummary(run_id="r1")
    assert run.total_features == 0
    assert run.total_scenarios == 0
    assert run.pass_rate == 0.0
    assert run.status == "untested"


def test_run_summary_all_passed() -> None:
    """RunSummary aggregates counts correctly when all pass."""
    feat = FeatureSummary(
        name="F",
        scenarios=[_make_scenario("passed"), _make_scenario("passed")],
    )
    run = RunSummary(features=[feat])
    assert run.total_scenarios == 2
    assert run.passed == 2
    assert run.pass_rate == 1.0
    assert run.status == "passed"


def test_run_summary_with_failure() -> None:
    """RunSummary derives failed status when any scenario fails."""
    feat = FeatureSummary(
        name="F",
        scenarios=[_make_scenario("passed"), _make_scenario("failed")],
    )
    run = RunSummary(features=[feat])
    assert run.failed == 1
    assert run.status == "failed"


def test_run_summary_multiple_features() -> None:
    """RunSummary aggregates across multiple features."""
    f1 = FeatureSummary(name="F1", scenarios=[_make_scenario("passed")])
    f2 = FeatureSummary(
        name="F2",
        scenarios=[_make_scenario("failed"), _make_scenario("skipped")],
    )
    run = RunSummary(features=[f1, f2])
    assert run.total_features == 2
    assert run.total_scenarios == 3
    assert run.passed == 1
    assert run.failed == 1
    assert run.skipped == 1
    assert run.status == "failed"


def test_run_summary_undefined() -> None:
    """RunSummary derives undefined status when any scenario is undefined."""
    feat = FeatureSummary(
        name="F",
        scenarios=[_make_scenario("passed"), _make_scenario("undefined")],
    )
    run = RunSummary(features=[feat])
    assert run.undefined == 1
    assert run.status == "undefined"


def test_run_summary_all_skipped() -> None:
    """RunSummary derives skipped status when all scenarios are skipped."""
    feat = FeatureSummary(
        name="F",
        scenarios=[_make_scenario("skipped"), _make_scenario("skipped")],
    )
    run = RunSummary(features=[feat])
    assert run.skipped == 2
    assert run.status == "skipped"


def test_feature_summary_untested() -> None:
    """FeatureSummary derives untested status when any scenario is untested."""
    feat = FeatureSummary(
        name="F",
        scenarios=[_make_scenario("passed"), _make_scenario("untested")],
    )
    assert feat.derive_status() == "untested"


def test_run_summary_untested() -> None:
    """RunSummary derives untested status when any feature is untested."""
    feat = FeatureSummary(
        name="F",
        scenarios=[_make_scenario("passed"), _make_scenario("untested")],
    )
    run = RunSummary(features=[feat])
    assert run.status == "untested"


# ---------------------------------------------------------------------------
# ReportOptions
# ---------------------------------------------------------------------------


def test_report_options_defaults() -> None:
    """ReportOptions has sensible defaults."""
    opts = ReportOptions()
    assert opts.only_failed is False
    assert opts.template == ""
    assert opts.primary_color == "#2563EB"
    assert opts.title == "Behave Modern Report"
    assert opts.include_attachments is True
    assert opts.max_traceback_lines == 50
    assert opts.txt_width == 100
    assert opts.txt_ascii is False
    assert opts.pdf_engine == "weasyprint"


def test_report_options_from_dict_empty() -> None:
    """from_dict with empty dict returns defaults."""
    opts = ReportOptions.from_dict({})
    assert opts.only_failed is False
    assert opts.title == "Behave Modern Report"


def test_report_options_from_dict_global() -> None:
    """from_dict resolves global bmfr.* keys."""
    opts = ReportOptions.from_dict({
        "bmfr.only_failed": "true",
        "bmfr.title": "QA Report",
        "bmfr.primary_color": "#1E90FF",
        "bmfr.txt_width": "120",
        "bmfr.pdf_engine": "reportlab",
    })
    assert opts.only_failed is True
    assert opts.title == "QA Report"
    assert opts.primary_color == "#1e90ff"
    assert opts.txt_width == 120
    assert opts.pdf_engine == "reportlab"


def test_report_options_from_dict_invalid_color_falls_back() -> None:
    """from_dict falls back to the default color when primary_color is invalid."""
    opts = ReportOptions.from_dict({"bmfr.primary_color": "not-a-color"})
    assert opts.primary_color == "#2563EB"


def test_report_options_from_dict_format_override() -> None:
    """from_dict resolves format-specific overrides over global keys."""
    opts = ReportOptions.from_dict(
        {
            "bmfr.title": "Global Title",
            "bmfr.pdf.title": "PDF Title",
            "bmfr.logo": "global.png",
            "bmfr.pdf.logo": "pdf.png",
        },
        format_key="pdf",
    )
    assert opts.title == "PDF Title"
    assert opts.logo == "pdf.png"


def test_report_options_from_dict_no_format_override() -> None:
    """from_dict without format_key uses only global keys."""
    opts = ReportOptions.from_dict({
        "bmfr.title": "Global Title",
        "bmfr.pdf.title": "PDF Title",
    })
    assert opts.title == "Global Title"


def test_report_options_from_dict_format_fallback() -> None:
    """from_dict falls back to global when format-specific key is absent."""
    opts = ReportOptions.from_dict(
        {
            "bmfr.title": "Global Title",
            "bmfr.pdf.logo": "pdf.png",
        },
        format_key="pdf",
    )
    assert opts.title == "Global Title"
    assert opts.logo == "pdf.png"
