"""Tests for behave_modern_file_reports.html_renderer."""

from __future__ import annotations

from pathlib import Path

from behave_modern_file_reports.html_renderer import render_html
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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_step(
    name: str = "step",
    keyword: str = "Given ",
    status: str = "passed",
    duration: float = 0.01,
    attachments: list[Attachment] | None = None,
    logs: list[str] | None = None,
) -> Step:
    return Step(
        keyword=keyword,
        name=name,
        status=status,
        duration=duration,
        attachments=attachments or [],
        logs=logs or [],
    )


def _make_scenario(
    name: str = "Scenario 1",
    status: str = "passed",
    duration: float = 0.05,
    steps: list[Step] | None = None,
    tags: list[str] | None = None,
    error: ErrorInfo | None = None,
    location: str = "features/test.feature:5",
    rule_name: str = "",
    is_outline: bool = False,
    background: Background | None = None,
) -> ScenarioResult:
    return ScenarioResult(
        name=name,
        status=status,
        duration=duration,
        steps=steps or [_make_step()],
        tags=tags or [],
        error=error,
        location=location,
        rule_name=rule_name,
        is_outline=is_outline,
        background=background,
    )


def _make_feature(
    name: str = "Feature 1",
    status: str = "passed",
    scenarios: list[ScenarioResult] | None = None,
    tags: list[str] | None = None,
    description: str = "",
    location: str = "features/test.feature:1",
    background: Background | None = None,
) -> FeatureSummary:
    feat = FeatureSummary(
        name=name,
        status=status,
        duration=0.1,
        scenarios=scenarios or [_make_scenario()],
        tags=tags or [],
        description=description,
        location=location,
        background=background,
    )
    return feat


def _make_run(
    features: list[FeatureSummary] | None = None,
    title: str = "Test Report",
    project_name: str = "Test Project",
) -> RunSummary:
    return RunSummary(
        run_id="r1",
        title=title,
        project_name=project_name,
        start_time="2025-01-01T00:00:00",
        end_time="2025-01-01T00:00:05",
        duration=5.0,
        features=features or [_make_feature()],
        environment=Environment(
            python_version="3.14",
            platform="linux",
            hostname="test-host",
        ),
    )


# ---------------------------------------------------------------------------
# Basic rendering
# ---------------------------------------------------------------------------


def test_render_html_returns_string() -> None:
    html = render_html(_make_run())
    assert isinstance(html, str)
    assert len(html) > 0


def test_render_html_contains_doctype() -> None:
    html = render_html(_make_run())
    assert "<!DOCTYPE html>" in html


def test_render_html_contains_title() -> None:
    html = render_html(_make_run(title="My Custom Title"))
    assert "My Custom Title" in html


def test_render_html_contains_project_name() -> None:
    html = render_html(_make_run(project_name="Awesome Project"))
    assert "Awesome Project" in html


# ---------------------------------------------------------------------------
# Cover page
# ---------------------------------------------------------------------------


def test_cover_metadata() -> None:
    html = render_html(_make_run())
    assert "2025-01-01" in html
    assert "5.00s" in html


def test_cover_progress_bar() -> None:
    html = render_html(_make_run())
    assert "cover-progress-bar" in html


def test_cover_without_project() -> None:
    run = _make_run()
    run.project_name = ""
    html = render_html(run)
    assert 'cover-subtitle">' not in html


def test_cover_with_logo() -> None:
    opts = ReportOptions(logo_b64="data:image/png;base64,iVBORw0KGgo=")
    html = render_html(_make_run(), opts)
    assert "cover-logo" in html
    assert "iVBORw0KGgo=" in html


# ---------------------------------------------------------------------------
# Executive summary
# ---------------------------------------------------------------------------


def test_summary_section() -> None:
    feat = _make_feature(
        scenarios=[_make_scenario(status="passed"), _make_scenario(status="failed")],
    )
    html = render_html(_make_run([feat]))
    assert "Executive summary" in html
    assert "Scenarios" in html
    assert "Passed" in html
    assert "Failed" in html


def test_summary_table_with_features() -> None:
    html = render_html(_make_run([_make_feature(name="Auth")]))
    assert "Auth" in html
    assert "Pass rate" in html


def test_summary_table_empty_features() -> None:
    run = _make_run(features=[])
    html = render_html(run)
    assert "Executive summary" in html
    assert "<table" not in html.split("Environment")[0].split("Executive summary")[1]


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------


def test_environment_section() -> None:
    html = render_html(_make_run())
    assert "Environment" in html
    assert "3.14" in html
    assert "linux" in html


def test_environment_user() -> None:
    run = _make_run()
    run.environment.user = "testuser"
    html = render_html(run)
    assert "testuser" in html


# ---------------------------------------------------------------------------
# Feature sections
# ---------------------------------------------------------------------------


def test_feature_heading() -> None:
    html = render_html(_make_run([_make_feature(name="Login")]))
    assert "Login" in html
    assert 'id="feature-1"' in html


def test_feature_status_badge() -> None:
    html = render_html(_make_run([_make_feature(status="failed")]))
    assert "badge-failed" in html
    assert "failed" in html


def test_feature_description() -> None:
    html = render_html(
        _make_run([_make_feature(description="A test feature for auth.")]),
    )
    assert "A test feature for auth." in html


def test_feature_tags() -> None:
    html = render_html(
        _make_run([_make_feature(tags=["smoke", "critical"])]),
    )
    assert "smoke" in html
    assert "critical" in html


def test_feature_location() -> None:
    html = render_html(_make_run([_make_feature(location="features/auth.feature:1")]))
    assert "features/auth.feature:1" in html


def test_feature_summary_table() -> None:
    feat = _make_feature(
        scenarios=[_make_scenario(status="passed"), _make_scenario(status="failed")],
    )
    html = render_html(_make_run([feat]))
    assert "Total" in html
    assert "Undefined" in html


# ---------------------------------------------------------------------------
# Scenario sections
# ---------------------------------------------------------------------------


def test_scenario_heading() -> None:
    html = render_html(
        _make_run([_make_feature(scenarios=[_make_scenario(name="Login works")])]),
    )
    assert "Login works" in html


def test_scenario_status_badge() -> None:
    html = render_html(
        _make_run([_make_feature(scenarios=[_make_scenario(status="skipped")])]),
    )
    assert "badge-skipped" in html


def test_scenario_tags() -> None:
    html = render_html(
        _make_run([_make_feature(scenarios=[_make_scenario(tags=["regression"])])]),
    )
    assert "regression" in html


def test_scenario_location() -> None:
    html = render_html(
        _make_run(
            [_make_feature(scenarios=[_make_scenario(location="f:10")])],
        ),
    )
    assert "f:10" in html


def test_scenario_rule_name() -> None:
    html = render_html(
        _make_run(
            [_make_feature(scenarios=[_make_scenario(rule_name="Slow tests")])],
        ),
    )
    assert "Slow tests" in html


def test_scenario_outline() -> None:
    html = render_html(
        _make_run(
            [_make_feature(scenarios=[_make_scenario(is_outline=True)])],
        ),
    )
    assert "OUTLINE" in html


def test_scenario_duration() -> None:
    html = render_html(
        _make_run([_make_feature(scenarios=[_make_scenario(duration=2.5)])]),
    )
    assert "2.50s" in html


# ---------------------------------------------------------------------------
# Step table
# ---------------------------------------------------------------------------


def test_step_in_table() -> None:
    step = _make_step(name="user on page")
    html = render_html(
        _make_run([_make_feature(scenarios=[_make_scenario(steps=[step])])]),
    )
    assert "user on page" in html
    assert "Given" in html
    assert "Status" in html


def test_step_status_icon() -> None:
    step = _make_step(status="passed")
    html = render_html(
        _make_run([_make_feature(scenarios=[_make_scenario(steps=[step])])]),
    )
    assert "✓" in html


def test_step_failed_icon() -> None:
    step = _make_step(status="failed")
    html = render_html(
        _make_run([_make_feature(scenarios=[_make_scenario(steps=[step])])]),
    )
    assert "✗" in html


def test_step_skipped_icon() -> None:
    step = _make_step(status="skipped")
    html = render_html(
        _make_run([_make_feature(scenarios=[_make_scenario(steps=[step])])]),
    )
    assert "↷" in html


def test_step_duration() -> None:
    step = _make_step(duration=0.005)
    html = render_html(
        _make_run([_make_feature(scenarios=[_make_scenario(steps=[step])])]),
    )
    assert "5ms" in html


# ---------------------------------------------------------------------------
# Error block
# ---------------------------------------------------------------------------


def test_error_block() -> None:
    err = ErrorInfo(
        message="boom",
        traceback="Traceback:\n  File x",
        exception_type="ValueError",
    )
    html = render_html(
        _make_run(
            [_make_feature(scenarios=[_make_scenario(status="failed", error=err)])],
        ),
    )
    assert "Failure" in html
    assert "ValueError" in html
    assert "boom" in html
    assert "Traceback" in html


def test_error_without_traceback() -> None:
    err = ErrorInfo(message="no tb")
    html = render_html(
        _make_run(
            [_make_feature(scenarios=[_make_scenario(status="failed", error=err)])],
        ),
    )
    assert "no tb" in html
    assert "Traceback" not in html


def test_error_without_exception_type() -> None:
    err = ErrorInfo(message="no type", traceback="tb line")
    html = render_html(
        _make_run(
            [_make_feature(scenarios=[_make_scenario(status="failed", error=err)])],
        ),
    )
    assert "no type" in html
    assert "Type:" not in html


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------


def test_feature_background() -> None:
    bg = Background(name="Common", steps=[_make_step(name="app running")])
    html = render_html(_make_run([_make_feature(background=bg)]))
    assert "Background" in html
    assert "Common" in html
    assert "app running" in html


def test_scenario_background() -> None:
    bg = Background(name="Setup", steps=[_make_step(name="db ready")])
    html = render_html(
        _make_run([_make_feature(scenarios=[_make_scenario(background=bg)])]),
    )
    assert "Background" in html
    assert "Setup" in html
    assert "db ready" in html


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------


def test_text_attachment() -> None:
    att = Attachment(name="log.txt", mime_type="text/plain", text="line1\nline2")
    step = _make_step(name="step", attachments=[att])
    html = render_html(
        _make_run([_make_feature(scenarios=[_make_scenario(steps=[step])])]),
    )
    assert "log.txt" in html
    assert "line1" in html


def test_image_attachment() -> None:
    att = Attachment(
        name="screenshot.png",
        mime_type="image/png",
        data_base64="iVBORw0KGgo=",
    )
    step = _make_step(name="step", attachments=[att])
    html = render_html(
        _make_run([_make_feature(scenarios=[_make_scenario(steps=[step])])]),
    )
    assert "screenshot.png" in html
    assert "data:image/png;base64,iVBORw0KGgo=" in html


def test_image_attachment_excluded_when_disabled() -> None:
    att = Attachment(
        name="screenshot.png",
        mime_type="image/png",
        data_base64="iVBORw0KGgo=",
    )
    step = _make_step(name="step", attachments=[att])
    opts = ReportOptions(include_attachments=False)
    html = render_html(
        _make_run([_make_feature(scenarios=[_make_scenario(steps=[step])])]),
        opts,
    )
    assert "screenshot.png" in html
    assert "data:image/png;base64," not in html


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------


def test_step_logs() -> None:
    step = _make_step(name="step", logs=["> log line 1", "> log line 2"])
    html = render_html(
        _make_run([_make_feature(scenarios=[_make_scenario(steps=[step])])]),
    )
    assert "log line 1" in html
    assert "log line 2" in html


# ---------------------------------------------------------------------------
# TOC
# ---------------------------------------------------------------------------


def test_toc_placeholder() -> None:
    html = render_html(_make_run([_make_feature(name="Auth")]))
    assert "Table of contents" in html
    assert "#feature-1" in html


def test_toc_links_to_scenarios() -> None:
    html = render_html(
        _make_run(
            [_make_feature(scenarios=[_make_scenario(name="Login")])],
        ),
    )
    assert "#scenario-" in html
    assert "Login" in html


# ---------------------------------------------------------------------------
# Multiple features
# ---------------------------------------------------------------------------


def test_multiple_features() -> None:
    html = render_html(
        _make_run([_make_feature(name="Auth"), _make_feature(name="Payment")]),
    )
    assert "Auth" in html
    assert "Payment" in html
    assert 'id="feature-1"' in html
    assert 'id="feature-2"' in html


# ---------------------------------------------------------------------------
# Empty run
# ---------------------------------------------------------------------------


def test_empty_run() -> None:
    run = _make_run(features=[])
    html = render_html(run)
    assert "Executive summary" in html
    assert "Environment" in html


# ---------------------------------------------------------------------------
# CSS inlining
# ---------------------------------------------------------------------------


def test_css_inlined() -> None:
    html = render_html(_make_run())
    assert "<style>" in html
    assert "--color-primary" in html


# ---------------------------------------------------------------------------
# Custom template
# ---------------------------------------------------------------------------


def test_custom_template_dir(tmp_path: Path) -> None:
    template = tmp_path / "custom.html"
    template.write_text("<html><body>{{ run.title }}<style>{{ css }}</style></body></html>")
    css = tmp_path / "custom.css"
    css.write_text("body { color: red; }")
    html = render_html(
        _make_run(title="Custom"),
        template_name="custom.html",
        css_name="custom.css",
        template_dir=tmp_path,
    )
    assert "Custom" in html
    assert "color: red" in html


def test_custom_template_via_options(tmp_path: Path) -> None:
    """Custom template loaded via options.template (file path)."""
    template = tmp_path / "my_report.html"
    template.write_text(
        "<html><body>CUSTOM: {{ run.title }}"
        "<style>{{ css }}</style></body></html>",
    )
    opts = ReportOptions(template=str(template))
    html = render_html(_make_run(title="ViaOptions"), opts)
    assert "CUSTOM: ViaOptions" in html


def test_custom_template_via_options_directory(tmp_path: Path) -> None:
    """Custom template loaded via options.template (directory path)."""
    template = tmp_path / "default.html"
    template.write_text(
        "<html><body>DIR: {{ run.title }}"
        "<style>{{ css }}</style></body></html>",
    )
    opts = ReportOptions(template=str(tmp_path))
    html = render_html(_make_run(title="ViaDir"), opts)
    assert "DIR: ViaDir" in html


def test_custom_template_falls_back_when_not_found() -> None:
    """If options.template points to a non-existent path, falls back to default."""
    opts = ReportOptions(template="/nonexistent/path/template.html")
    html = render_html(_make_run(title="Fallback"), opts)
    assert "Fallback" in html
    assert "<!DOCTYPE html>" in html


def test_custom_template_with_logo_b64(tmp_path: Path) -> None:
    """Custom template receives logo_b64 context variable."""
    template = tmp_path / "logo_test.html"
    template.write_text(
        "<html><body>LOGO: {{ logo_b64 }}"
        "<style>{{ css }}</style></body></html>",
    )
    opts = ReportOptions(
        template=str(template),
        logo_b64="data:image/png;base64,ABC123",
    )
    html = render_html(_make_run(), opts)
    assert "LOGO: data:image/png;base64,ABC123" in html


def test_logo_b64_empty_by_default(tmp_path: Path) -> None:
    """logo_b64 is empty string by default."""
    template = tmp_path / "logo_check.html"
    template.write_text(
        "<html><body>LOGO=[{{ logo_b64 }}]"
        "<style>{{ css }}</style></body></html>",
    )
    opts = ReportOptions(template=str(template))
    html = render_html(_make_run(), opts)
    assert "LOGO=[]" in html


def test_resolve_template_path_custom_file(tmp_path: Path) -> None:
    """_resolve_template_path returns custom file location."""
    from behave_modern_file_reports.html_renderer import _resolve_template_path
    template = tmp_path / "custom.html"
    template.write_text("<html></html>")
    opts = ReportOptions(template=str(template))
    tdir, tname, cname = _resolve_template_path(opts, None)
    assert tdir == tmp_path
    assert tname == "custom.html"
    assert cname == "default.css"


def test_resolve_template_path_custom_dir(tmp_path: Path) -> None:
    """_resolve_template_path returns custom directory location."""
    from behave_modern_file_reports.html_renderer import _resolve_template_path
    opts = ReportOptions(template=str(tmp_path))
    tdir, tname, cname = _resolve_template_path(opts, None)
    assert tdir == tmp_path
    assert tname == "default.html"
    assert cname == "default.css"


def test_resolve_template_path_nonexistent() -> None:
    """_resolve_template_path falls back for non-existent path."""
    from behave_modern_file_reports.html_renderer import _resolve_template_path
    opts = ReportOptions(template="/nonexistent/template.html")
    tdir, tname, cname = _resolve_template_path(opts, None)
    assert tname == "default.html"


def test_resolve_template_path_empty() -> None:
    """_resolve_template_path returns defaults when template is empty."""
    from behave_modern_file_reports.html_renderer import _resolve_template_path
    opts = ReportOptions()
    tdir, tname, cname = _resolve_template_path(opts, None)
    assert tname == "default.html"
    assert cname == "default.css"


# ---------------------------------------------------------------------------
# Branding: primary_color injection
# ---------------------------------------------------------------------------


def test_primary_color_injected_into_css() -> None:
    """Custom primary_color replaces the CSS variable."""
    opts = ReportOptions(primary_color="#1E90FF")
    html = render_html(_make_run(), opts)
    assert "--color-primary: #1E90FF;" in html
    assert "--color-primary: #2563EB;" not in html


def test_default_primary_color_in_css() -> None:
    """Default primary_color is used when not specified."""
    html = render_html(_make_run())
    assert "--color-primary: #2563EB;" in html


def test_empty_primary_color_skips_injection() -> None:
    """Empty primary_color does not inject into CSS."""
    opts = ReportOptions(primary_color="")
    html = render_html(_make_run(), opts)
    assert "--color-primary: #2563EB;" in html


# ---------------------------------------------------------------------------
# Default options
# ---------------------------------------------------------------------------


def test_default_options_when_none() -> None:
    html = render_html(_make_run())
    assert "Behave Modern Report" in html or "Test Report" in html


# ---------------------------------------------------------------------------
# Duration filter
# ---------------------------------------------------------------------------


def test_format_duration_seconds() -> None:
    step = _make_step(duration=3.5)
    html = render_html(
        _make_run([_make_feature(scenarios=[_make_scenario(steps=[step])])]),
    )
    assert "3.50s" in html


def test_format_duration_zero() -> None:
    step = _make_step(duration=0.0)
    html = render_html(
        _make_run([_make_feature(scenarios=[_make_scenario(steps=[step])])]),
    )
    assert "0ms" in html
