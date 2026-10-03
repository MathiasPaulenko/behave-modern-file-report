"""Tests for behave_modern_file_report.txt_writer."""

from __future__ import annotations

import io

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
from behave_modern_file_report.txt_writer import TXTWriter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_step(
    name: str = "step",
    keyword: str = "Given ",
    status: str = "passed",
    duration: float = 0.01,
    error: ErrorInfo | None = None,
    attachments: list[Attachment] | None = None,
    logs: list[str] | None = None,
) -> Step:
    return Step(
        keyword=keyword,
        name=name,
        status=status,
        duration=duration,
        location="features/test.feature:10",
        error=error,
        attachments=attachments or [],
        logs=logs or [],
    )


def _make_scenario(
    name: str = "Scenario 1",
    status: str = "passed",
    steps: list[Step] | None = None,
    error: ErrorInfo | None = None,
    tags: list[str] | None = None,
    is_outline: bool = False,
    background: Background | None = None,
) -> ScenarioResult:
    return ScenarioResult(
        name=name,
        status=status,
        duration=0.05,
        tags=tags or [],
        location="features/test.feature:5",
        feature_name="Test Feature",
        is_outline=is_outline,
        steps=steps or [],
        error=error,
        background=background,
    )


def _make_feature(
    name: str = "Test Feature",
    scenarios: list[ScenarioResult] | None = None,
    background: Background | None = None,
    tags: list[str] | None = None,
    description: str = "",
) -> FeatureSummary:
    return FeatureSummary(
        name=name,
        description=description,
        duration=0.1,
        tags=tags or [],
        location="features/test.feature:1",
        scenarios=scenarios or [],
        background=background,
    )


def _make_run(
    features: list[FeatureSummary] | None = None,
    title: str = "Test Report",
) -> RunSummary:
    return RunSummary(
        run_id="run_abc123",
        title=title,
        project_name="Test Project",
        start_time="2025-01-01T10:00:00+00:00",
        end_time="2025-01-01T10:00:05+00:00",
        duration=5.0,
        features=features or [],
        environment=Environment(
            python_version="3.14.0",
            platform="linux",
        ),
    )


def _write_report(
    run: RunSummary,
    options: ReportOptions | None = None,
) -> str:
    """Write a report to a string and return it."""
    if options is None:
        options = ReportOptions()
    writer = TXTWriter(options)
    stream = io.StringIO()
    writer.write(run, stream)
    return stream.getvalue()


# ---------------------------------------------------------------------------
# Cover
# ---------------------------------------------------------------------------


def test_cover_contains_title() -> None:
    """Report cover contains the title."""
    run = _make_run(title="My Report")
    output = _write_report(run)
    assert "My Report" in output


def test_cover_contains_project_name() -> None:
    """Report cover contains the project name."""
    run = _make_run()
    output = _write_report(run)
    assert "Test Project" in output


def test_cover_contains_run_metadata() -> None:
    """Report cover contains run ID, timestamps, and duration."""
    run = _make_run()
    output = _write_report(run)
    assert "run_abc123" in output
    assert "2025-01-01T10:00:00+00:00" in output
    assert "2025-01-01T10:00:05+00:00" in output


def test_cover_default_title() -> None:
    """Report with empty title uses default."""
    run = _make_run(title="")
    output = _write_report(run)
    assert "Behave Modern Report" in output


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def test_summary_contains_totals() -> None:
    """Summary section contains feature and scenario counts."""
    feat = _make_feature(
        scenarios=[
            _make_scenario(name="S1", status="passed"),
            _make_scenario(name="S2", status="failed"),
        ]
    )
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "Features:    1" in output
    assert "Scenarios:   2" in output
    assert "Passed:    1" in output
    assert "Failed:    1" in output


def test_summary_pass_rate() -> None:
    """Summary shows pass rate percentage."""
    feat = _make_feature(
        scenarios=[
            _make_scenario(name="S1", status="passed"),
            _make_scenario(name="S2", status="passed"),
            _make_scenario(name="S3", status="failed"),
        ]
    )
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "Pass rate:" in output
    assert "66.7%" in output


def test_summary_empty_run() -> None:
    """Summary for an empty run shows zeros."""
    run = _make_run(features=[])
    output = _write_report(run)
    assert "Features:    0" in output
    assert "Scenarios:   0" in output
    assert "Pass rate:   0.0%" in output


# ---------------------------------------------------------------------------
# Feature / Scenario / Step
# ---------------------------------------------------------------------------


def test_feature_name_in_output() -> None:
    """Feature name appears in the output."""
    feat = _make_feature(name="Login Feature")
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "Login Feature" in output


def test_scenario_name_in_output() -> None:
    """Scenario name appears in the output."""
    feat = _make_feature(scenarios=[_make_scenario(name="Login succeeds")])
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "Login succeeds" in output


def test_step_name_in_output() -> None:
    """Step keyword and name appear in the output."""
    step = _make_step(name="the user is logged in", keyword="Given ")
    feat = _make_feature(scenarios=[_make_scenario(steps=[step])])
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "Given" in output
    assert "the user is logged in" in output


def test_status_labels_in_output() -> None:
    """Status labels (PASSED, FAILED) appear in the output."""
    feat = _make_feature(
        scenarios=[
            _make_scenario(name="S1", status="passed"),
            _make_scenario(name="S2", status="failed"),
        ]
    )
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "PASSED" in output
    assert "FAILED" in output


def test_skipped_status_in_output() -> None:
    """Skipped status appears in the output."""
    feat = _make_feature(
        scenarios=[
            _make_scenario(name="S1", status="skipped"),
        ]
    )
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "SKIPPED" in output


def test_undefined_status_in_output() -> None:
    """Undefined status appears in the output."""
    feat = _make_feature(
        scenarios=[
            _make_scenario(name="S1", status="undefined"),
        ]
    )
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "UNDEFINED" in output


def test_feature_tags_in_output() -> None:
    """Feature tags appear in the output."""
    feat = _make_feature(tags=["auth", "smoke"])
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "auth" in output
    assert "smoke" in output


def test_scenario_tags_in_output() -> None:
    """Scenario tags appear in the output."""
    feat = _make_feature(
        scenarios=[
            _make_scenario(name="S1", tags=["fast"]),
        ]
    )
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "fast" in output


def test_feature_description_in_output() -> None:
    """Feature description appears in the output."""
    feat = _make_feature(description="This is a test feature.")
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "This is a test feature." in output


def test_outline_tag_in_output() -> None:
    """Scenario outline has [OUTLINE] tag in output."""
    feat = _make_feature(
        scenarios=[
            _make_scenario(name="Data driven", is_outline=True),
        ]
    )
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "[OUTLINE]" in output


def test_rule_name_in_output() -> None:
    """Rule name appears in the scenario output."""
    scn = _make_scenario(name="S1")
    scn.rule_name = "Auth rule"
    feat = _make_feature(scenarios=[scn])
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "Auth rule" in output


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------


def test_background_in_output() -> None:
    """Background steps appear in the output."""
    bg = Background(
        name="Common setup",
        steps=[
            _make_step(name="app is running", keyword="Given "),
        ],
    )
    feat = _make_feature(background=bg, scenarios=[_make_scenario(name="S1")])
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "Background" in output
    assert "Common setup" in output
    assert "app is running" in output


def test_scenario_background_in_output() -> None:
    """Scenario-level background appears in the output."""
    bg = Background(
        name="Scenario bg",
        steps=[
            _make_step(name="setup step", keyword="Given "),
        ],
    )
    feat = _make_feature(
        scenarios=[
            _make_scenario(name="S1", background=bg),
        ]
    )
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "Scenario bg" in output
    assert "setup step" in output


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


def test_error_message_in_output() -> None:
    """Error message appears in the output for failed scenarios."""
    error = ErrorInfo(
        message="Element not found",
        traceback="Traceback (most recent call last):\n  ...",
        exception_type="AssertionError",
    )
    feat = _make_feature(
        scenarios=[
            _make_scenario(name="S1", status="failed", error=error),
        ]
    )
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "ERROR" in output
    assert "Element not found" in output
    assert "AssertionError" in output


def test_error_traceback_in_output() -> None:
    """Error traceback appears in the output."""
    error = ErrorInfo(
        message="boom",
        traceback="Traceback:\n  File test.py:1\n    raise ValueError",
        exception_type="ValueError",
    )
    feat = _make_feature(
        scenarios=[
            _make_scenario(name="S1", status="failed", error=error),
        ]
    )
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "Traceback:" in output
    assert "File test.py:1" in output


def test_step_error_in_output() -> None:
    """Step-level error appears in the output."""
    error = ErrorInfo(
        message="step failed",
        traceback="",
        exception_type="RuntimeError",
    )
    step = _make_step(name="bad step", status="failed", error=error)
    feat = _make_feature(scenarios=[_make_scenario(steps=[step])])
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "step failed" in output
    assert "RuntimeError" in output


# ---------------------------------------------------------------------------
# Attachments and logs
# ---------------------------------------------------------------------------


def test_attachment_names_in_output() -> None:
    """Attachment names are listed in the output."""
    step = _make_step(
        name="step with screenshot",
        attachments=[
            Attachment(name="screenshot1.png", mime_type="image/png"),
            Attachment(name="screenshot2.png", mime_type="image/png"),
        ],
    )
    feat = _make_feature(scenarios=[_make_scenario(steps=[step])])
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "Attachments:" in output
    assert "screenshot1.png" in output
    assert "screenshot2.png" in output


def test_logs_in_output() -> None:
    """Step logs appear in the output."""
    step = _make_step(name="step with logs", logs=["navigated to /login", "clicked button"])
    feat = _make_feature(scenarios=[_make_scenario(steps=[step])])
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "navigated to /login" in output
    assert "clicked button" in output


# ---------------------------------------------------------------------------
# Width and ASCII options
# ---------------------------------------------------------------------------


def test_width_affects_separator_length() -> None:
    """Separator lines respect txt_width."""
    run = _make_run()
    output = _write_report(run, ReportOptions(txt_width=60))
    lines = output.splitlines()
    sep_lines = [ln for ln in lines if ln.startswith("=") and len(ln) > 10]
    assert all(len(ln) == 60 for ln in sep_lines)


def test_ascii_mode_uses_ascii_icons() -> None:
    """ASCII mode uses [PASS]/[FAIL] instead of unicode symbols."""
    feat = _make_feature(
        scenarios=[
            _make_scenario(name="S1", status="passed"),
            _make_scenario(name="S2", status="failed"),
        ]
    )
    run = _make_run(features=[feat])
    output = _write_report(run, ReportOptions(txt_ascii=True))
    assert "[PASS]" in output
    assert "[FAIL]" in output


def test_unicode_mode_uses_unicode_icons() -> None:
    """Unicode mode uses checkmark/cross symbols."""
    feat = _make_feature(
        scenarios=[
            _make_scenario(name="S1", status="passed"),
            _make_scenario(name="S2", status="failed"),
        ]
    )
    run = _make_run(features=[feat])
    output = _write_report(run, ReportOptions(txt_ascii=False))
    assert "\u2713" in output
    assert "\u2717" in output


def test_width_wraps_long_text() -> None:
    """Long step names are wrapped to the configured width."""
    long_name = (
        "This is a very long step name that should be wrapped "
        "because it exceeds the configured line width and needs "
        "to be split across multiple lines for readability"
    )
    step = _make_step(name=long_name)
    feat = _make_feature(scenarios=[_make_scenario(steps=[step])])
    run = _make_run(features=[feat])
    output = _write_report(run, ReportOptions(txt_width=60))
    lines = output.splitlines()
    step_lines = [ln for ln in lines if "This is a very long" in ln]
    assert len(step_lines) >= 1
    # At least one continuation line should exist
    all_step_lines = [ln for ln in lines if "long step name" in ln or "wrapped" in ln]
    assert len(all_step_lines) >= 2


def test_minimum_width_enforced() -> None:
    """Width below 40 is clamped to 40."""
    run = _make_run()
    output = _write_report(run, ReportOptions(txt_width=10))
    lines = output.splitlines()
    sep_lines = [ln for ln in lines if ln.startswith("=") and len(ln) > 5]
    assert all(len(ln) >= 40 for ln in sep_lines)


# ---------------------------------------------------------------------------
# Multiple features
# ---------------------------------------------------------------------------


def test_multiple_features_in_output() -> None:
    """Multiple features all appear in the output."""
    feat1 = _make_feature(name="Feature A", scenarios=[_make_scenario(name="S1")])
    feat2 = _make_feature(name="Feature B", scenarios=[_make_scenario(name="S2")])
    run = _make_run(features=[feat1, feat2])
    output = _write_report(run)
    assert "Feature A" in output
    assert "Feature B" in output
    assert "S1" in output
    assert "S2" in output


# ---------------------------------------------------------------------------
# Duration
# ---------------------------------------------------------------------------


def test_duration_in_output() -> None:
    """Step duration appears in the output."""
    step = _make_step(name="timed step", duration=1.234)
    feat = _make_feature(scenarios=[_make_scenario(steps=[step])])
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "1.23" in output or "1.234" in output


def test_scenario_duration_in_output() -> None:
    """Scenario duration appears in the output."""
    feat = _make_feature(scenarios=[_make_scenario(name="S1", status="passed")])
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "Duration:" in output


# ---------------------------------------------------------------------------
# Edge cases for branch coverage
# ---------------------------------------------------------------------------


def test_cover_without_project_name() -> None:
    """Cover without project name does not include it."""
    run = _make_run()
    run.project_name = ""
    output = _write_report(run)
    assert "Test Project" not in output


def test_feature_without_location() -> None:
    """Feature with empty location omits the Location line."""
    feat = _make_feature(name="NoLoc")
    feat.location = ""
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "NoLoc" in output


def test_scenario_without_location() -> None:
    """Scenario with empty location omits the Location line."""
    scn = _make_scenario(name="NoLoc")
    scn.location = ""
    feat = _make_feature(scenarios=[scn])
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "NoLoc" in output


def test_step_with_zero_duration_omits_parens() -> None:
    """Step with zero duration does not show duration in parens."""
    step = _make_step(name="instant step", duration=0.0)
    feat = _make_feature(scenarios=[_make_scenario(steps=[step])])
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "instant step" in output
    assert "(0.00s)" not in output


def test_error_without_exception_type() -> None:
    """Error without exception_type still shows the message."""
    error = ErrorInfo(message="unknown error", traceback="", exception_type="")
    feat = _make_feature(
        scenarios=[
            _make_scenario(name="S1", status="failed", error=error),
        ]
    )
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "ERROR" in output
    assert "unknown error" in output


def test_error_without_traceback() -> None:
    """Error with empty traceback only shows the header."""
    error = ErrorInfo(message="no tb", traceback="", exception_type="ValueError")
    feat = _make_feature(
        scenarios=[
            _make_scenario(name="S1", status="failed", error=error),
        ]
    )
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "no tb" in output
    assert "ValueError" in output


def test_wrap_empty_paragraph() -> None:
    """Description with empty paragraphs handles them correctly."""
    feat = _make_feature(description="Line 1\n\nLine 2")
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "Line 1" in output
    assert "Line 2" in output


def test_wrap_whitespace_only_text() -> None:
    """Description with whitespace-only paragraph handles gracefully."""
    feat = _make_feature(description="Line 1\n   \nLine 2")
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "Line 1" in output
    assert "Line 2" in output


def test_feature_without_tags_or_description() -> None:
    """Feature with no tags and no description renders correctly."""
    feat = _make_feature(name="Minimal", tags=[], description="")
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "Minimal" in output


def test_scenario_without_tags_rule_or_background() -> None:
    """Scenario with no tags, rule, or background renders correctly."""
    scn = _make_scenario(name="Minimal", tags=[])
    scn.rule_name = ""
    scn.background = None
    feat = _make_feature(scenarios=[scn])
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "Minimal" in output


# ---------------------------------------------------------------------------
# Attachment rendering
# ---------------------------------------------------------------------------


def test_attachment_with_image_shows_name_and_type() -> None:
    """Image attachment shows name, mime type, and byte size."""
    import base64

    img_data = base64.b64encode(b"\x89PNG\r\n\x1a\n\x00\x01").decode("ascii")
    att = Attachment(
        name="screenshot.png",
        mime_type="image/png",
        data_base64=img_data,
    )
    step = _make_step(attachments=[att])
    scn = _make_scenario(steps=[step])
    feat = _make_feature(scenarios=[scn])
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "screenshot.png" in output
    assert "image/png" in output
    assert "bytes" in output


def test_attachment_with_invalid_base64_shows_placeholder() -> None:
    """Attachment with invalid base64 data does not crash the report."""
    att = Attachment(
        name="corrupt.png",
        mime_type="image/png",
        data_base64="not-valid-base64!!!",
    )
    step = _make_step(attachments=[att])
    scn = _make_scenario(steps=[step])
    feat = _make_feature(scenarios=[scn])
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "corrupt.png" in output
    assert "invalid base64" in output


def test_attachment_with_text_shows_content() -> None:
    """Text attachment shows name, mime type, and text content."""
    att = Attachment(
        name="log.txt",
        mime_type="text/plain",
        text="line1\nline2",
    )
    step = _make_step(attachments=[att])
    scn = _make_scenario(steps=[step])
    feat = _make_feature(scenarios=[scn])
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "log.txt" in output
    assert "text/plain" in output
    assert "line1" in output
    assert "line2" in output


def test_attachment_no_data_shows_name_only() -> None:
    """Attachment with no data_base64 and no text shows name and type only."""
    att = Attachment(name="empty.bin", mime_type="application/octet-stream")
    step = _make_step(attachments=[att])
    scn = _make_scenario(steps=[step])
    feat = _make_feature(scenarios=[scn])
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "empty.bin" in output
    assert "application/octet-stream" in output


def test_multiple_attachments_all_listed() -> None:
    """Multiple attachments are all listed."""
    att1 = Attachment(name="a.txt", mime_type="text/plain", text="aaa")
    att2 = Attachment(name="b.png", mime_type="image/png", data_base64="AAAA")
    step = _make_step(attachments=[att1, att2])
    scn = _make_scenario(steps=[step])
    feat = _make_feature(scenarios=[scn])
    run = _make_run(features=[feat])
    output = _write_report(run)
    assert "a.txt" in output
    assert "b.png" in output
