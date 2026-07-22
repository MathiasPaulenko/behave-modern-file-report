"""Tests for behave_modern_file_reports.pdf_writer."""

from __future__ import annotations

from pathlib import Path

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
from behave_modern_file_reports.pdf_writer import PDFWriter, ReportLabWriter, _format_duration, _rl

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
    return FeatureSummary(
        name=name,
        status=status,
        duration=0.1,
        scenarios=scenarios or [_make_scenario()],
        tags=tags or [],
        description=description,
        location=location,
        background=background,
    )


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
        environment=Environment(python_version="3.14", platform="linux"),
    )


def _weasyprint_available() -> bool:
    try:
        import weasyprint  # noqa: F401
    except (ImportError, OSError):
        return False
    return True


_weasyprint_skip = pytest.mark.skipif(
    not _weasyprint_available(),
    reason="WeasyPrint not installed",
)


# ---------------------------------------------------------------------------
# render_html_string (intermediate HTML, no WeasyPrint needed)
# ---------------------------------------------------------------------------


def test_rl_converts_0_255_rgb_to_0_1_range() -> None:
    """_rl converts a 0-255 RGB tuple to 0-1 range for ReportLab."""
    assert _rl((0, 0, 0)) == (0.0, 0.0, 0.0)
    assert _rl((255, 255, 255)) == (1.0, 1.0, 1.0)
    assert _rl((0x25, 0x63, 0xEB)) == (0x25 / 255, 0x63 / 255, 0xEB / 255)


def test_render_html_string_returns_html() -> None:
    writer = PDFWriter()
    html = writer.render_html_string(_make_run())
    assert isinstance(html, str)
    assert "<!DOCTYPE html>" in html


def test_render_html_string_contains_title() -> None:
    writer = PDFWriter()
    html = writer.render_html_string(_make_run(title="My PDF Report"))
    assert "My PDF Report" in html


def test_render_html_string_contains_features() -> None:
    writer = PDFWriter()
    html = writer.render_html_string(_make_run([_make_feature(name="Login")]))
    assert "Login" in html


def test_render_html_string_contains_scenarios() -> None:
    writer = PDFWriter()
    html = writer.render_html_string(
        _make_run([_make_feature(scenarios=[_make_scenario(name="Login ok")])]),
    )
    assert "Login ok" in html


def test_render_html_string_contains_status() -> None:
    writer = PDFWriter()
    html = writer.render_html_string(
        _make_run([_make_feature(scenarios=[_make_scenario(status="failed")])]),
    )
    assert "failed" in html


def test_render_html_string_contains_steps() -> None:
    writer = PDFWriter()
    step = _make_step(name="user on page")
    html = writer.render_html_string(
        _make_run([_make_feature(scenarios=[_make_scenario(steps=[step])])]),
    )
    assert "user on page" in html


def test_render_html_string_contains_error_block() -> None:
    writer = PDFWriter()
    err = ErrorInfo(message="boom", traceback="tb", exception_type="ValueError")
    html = writer.render_html_string(
        _make_run(
            [_make_feature(scenarios=[_make_scenario(status="failed", error=err)])],
        ),
    )
    assert "Failure" in html
    assert "ValueError" in html
    assert "boom" in html


def test_render_html_string_contains_environment() -> None:
    writer = PDFWriter()
    html = writer.render_html_string(_make_run())
    assert "Environment" in html
    assert "3.14" in html


def test_render_html_string_contains_toc() -> None:
    writer = PDFWriter()
    html = writer.render_html_string(_make_run([_make_feature(name="Auth")]))
    assert "Table of contents" in html


def test_render_html_string_contains_cover() -> None:
    writer = PDFWriter()
    html = writer.render_html_string(_make_run())
    assert "cover" in html.lower()
    assert "Test Project" in html


def test_render_html_string_with_options() -> None:
    opts = ReportOptions(title="Custom Title")
    writer = PDFWriter(opts)
    run = _make_run()
    run.title = "Custom Title"
    html = writer.render_html_string(run)
    assert "Custom Title" in html


def test_render_html_string_empty_run() -> None:
    writer = PDFWriter()
    html = writer.render_html_string(_make_run(features=[]))
    assert "Executive summary" in html


def test_render_html_string_multiple_features() -> None:
    writer = PDFWriter()
    html = writer.render_html_string(
        _make_run([_make_feature(name="Auth"), _make_feature(name="Payment")]),
    )
    assert "Auth" in html
    assert "Payment" in html


# ---------------------------------------------------------------------------
# PDFWriter construction
# ---------------------------------------------------------------------------


def test_writer_with_default_options() -> None:
    writer = PDFWriter()
    assert writer._options.title == "Behave Modern Report"


def test_writer_with_custom_options() -> None:
    opts = ReportOptions(title="Custom")
    writer = PDFWriter(opts)
    assert writer._options.title == "Custom"


# ---------------------------------------------------------------------------
# write() — PDF generation (requires WeasyPrint)
# ---------------------------------------------------------------------------


@_weasyprint_skip
@pytest.mark.slow
def test_write_produces_pdf_file(tmp_path: Path) -> None:
    writer = PDFWriter()
    path = tmp_path / "report.pdf"
    writer.write(_make_run(), path)
    assert path.exists()
    assert path.stat().st_size > 0


@_weasyprint_skip
@pytest.mark.slow
def test_write_pdf_starts_with_pdf_magic(tmp_path: Path) -> None:
    writer = PDFWriter()
    path = tmp_path / "report.pdf"
    writer.write(_make_run(), path)
    with open(path, "rb") as f:
        header = f.read(5)
    assert header == b"%PDF-"


@_weasyprint_skip
@pytest.mark.slow
def test_write_pdf_with_multiple_features(tmp_path: Path) -> None:
    writer = PDFWriter()
    path = tmp_path / "report.pdf"
    run = _make_run([_make_feature(name="Auth"), _make_feature(name="Payment")])
    writer.write(run, path)
    assert path.exists()
    assert path.stat().st_size > 1000


@_weasyprint_skip
@pytest.mark.slow
def test_write_pdf_with_failed_scenario(tmp_path: Path) -> None:
    writer = PDFWriter()
    path = tmp_path / "report.pdf"
    err = ErrorInfo(message="assertion failed", traceback="tb line")
    run = _make_run(
        [_make_feature(scenarios=[_make_scenario(status="failed", error=err)])],
    )
    writer.write(run, path)
    assert path.exists()


@_weasyprint_skip
@pytest.mark.slow
def test_write_pdf_empty_run(tmp_path: Path) -> None:
    writer = PDFWriter()
    path = tmp_path / "report.pdf"
    run = _make_run(features=[])
    writer.write(run, path)
    assert path.exists()


@_weasyprint_skip
@pytest.mark.slow
def test_write_pdf_with_custom_title(tmp_path: Path) -> None:
    opts = ReportOptions(title="Custom PDF Title")
    writer = PDFWriter(opts)
    path = tmp_path / "report.pdf"
    writer.write(_make_run(), path)
    assert path.exists()


@_weasyprint_skip
@pytest.mark.slow
def test_write_pdf_with_string_path(tmp_path: Path) -> None:
    writer = PDFWriter()
    path = str(tmp_path / "report.pdf")
    writer.write(_make_run(), path)
    assert Path(path).exists()


# ---------------------------------------------------------------------------
# WeasyPrint not installed
# ---------------------------------------------------------------------------


def test_write_raises_import_error_without_weasyprint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "weasyprint" or name.startswith("weasyprint."):
            raise ImportError("No module named 'weasyprint'")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", fake_import)
    writer = PDFWriter()
    with pytest.raises(ImportError, match="WeasyPrint is required"):
        writer.write(_make_run(), tmp_path / "report.pdf")


# ---------------------------------------------------------------------------
# ReportLab fallback
# ---------------------------------------------------------------------------


def _reportlab_available() -> bool:
    try:
        import reportlab  # noqa: F401
    except ImportError:
        return False
    return True


_reportlab_skip = pytest.mark.skipif(
    not _reportlab_available(),
    reason="ReportLab not installed",
)


# ---------------------------------------------------------------------------
# PDFWriter with pdf_engine="reportlab"
# ---------------------------------------------------------------------------


@_reportlab_skip
@pytest.mark.slow
def test_reportlab_engine_produces_pdf(tmp_path: Path) -> None:
    opts = ReportOptions(pdf_engine="reportlab")
    writer = PDFWriter(opts)
    path = tmp_path / "report.pdf"
    writer.write(_make_run(), path)
    assert path.exists()
    assert path.stat().st_size > 0


@_reportlab_skip
@pytest.mark.slow
def test_reportlab_engine_pdf_magic(tmp_path: Path) -> None:
    opts = ReportOptions(pdf_engine="reportlab")
    writer = PDFWriter(opts)
    path = tmp_path / "report.pdf"
    writer.write(_make_run(), path)
    with open(path, "rb") as f:
        header = f.read(5)
    assert header == b"%PDF-"


@_reportlab_skip
@pytest.mark.slow
def test_reportlab_engine_multiple_features(tmp_path: Path) -> None:
    opts = ReportOptions(pdf_engine="reportlab")
    writer = PDFWriter(opts)
    path = tmp_path / "report.pdf"
    run = _make_run([_make_feature(name="Auth"), _make_feature(name="Payment")])
    writer.write(run, path)
    assert path.exists()
    assert path.stat().st_size > 1000


@_reportlab_skip
@pytest.mark.slow
def test_reportlab_engine_failed_scenario(tmp_path: Path) -> None:
    opts = ReportOptions(pdf_engine="reportlab")
    writer = PDFWriter(opts)
    path = tmp_path / "report.pdf"
    err = ErrorInfo(message="assertion failed", traceback="tb line")
    run = _make_run(
        [_make_feature(scenarios=[_make_scenario(status="failed", error=err)])],
    )
    writer.write(run, path)
    assert path.exists()


@_reportlab_skip
@pytest.mark.slow
def test_reportlab_engine_empty_run(tmp_path: Path) -> None:
    opts = ReportOptions(pdf_engine="reportlab")
    writer = PDFWriter(opts)
    path = tmp_path / "report.pdf"
    run = _make_run(features=[])
    writer.write(run, path)
    assert path.exists()


@_reportlab_skip
@pytest.mark.slow
def test_reportlab_engine_with_string_path(tmp_path: Path) -> None:
    opts = ReportOptions(pdf_engine="reportlab")
    writer = PDFWriter(opts)
    path = str(tmp_path / "report.pdf")
    writer.write(_make_run(), path)
    assert Path(path).exists()


@_reportlab_skip
@pytest.mark.slow
def test_reportlab_engine_with_tags_and_description(tmp_path: Path) -> None:
    opts = ReportOptions(pdf_engine="reportlab")
    writer = PDFWriter(opts)
    path = tmp_path / "report.pdf"
    feat = _make_feature(
        name="Tagged Feature",
        description="A feature with tags",
        tags=["smoke", "critical"],
        scenarios=[_make_scenario(name="Tagged scenario", tags=["regression"])],
    )
    writer.write(_make_run([feat]), path)
    assert path.exists()


@_reportlab_skip
@pytest.mark.slow
def test_reportlab_engine_with_background(tmp_path: Path) -> None:
    opts = ReportOptions(pdf_engine="reportlab")
    writer = PDFWriter(opts)
    path = tmp_path / "report.pdf"
    bg = Background(name="Common", steps=[_make_step(name="app running")])
    feat = _make_feature(background=bg)
    writer.write(_make_run([feat]), path)
    assert path.exists()


@_reportlab_skip
@pytest.mark.slow
def test_reportlab_engine_with_attachments(tmp_path: Path) -> None:
    opts = ReportOptions(pdf_engine="reportlab")
    writer = PDFWriter(opts)
    path = tmp_path / "report.pdf"
    att = Attachment(name="log.txt", mime_type="text/plain", text="line1")
    step = _make_step(name="step", attachments=[att])
    feat = _make_feature(scenarios=[_make_scenario(steps=[step])])
    writer.write(_make_run([feat]), path)
    assert path.exists()


@_reportlab_skip
@pytest.mark.slow
def test_reportlab_engine_with_logs(tmp_path: Path) -> None:
    opts = ReportOptions(pdf_engine="reportlab")
    writer = PDFWriter(opts)
    path = tmp_path / "report.pdf"
    step = _make_step(name="step", logs=["> log line 1", "> log line 2"])
    feat = _make_feature(scenarios=[_make_scenario(steps=[step])])
    writer.write(_make_run([feat]), path)
    assert path.exists()


@_reportlab_skip
@pytest.mark.slow
def test_reportlab_engine_with_outline(tmp_path: Path) -> None:
    opts = ReportOptions(pdf_engine="reportlab")
    writer = PDFWriter(opts)
    path = tmp_path / "report.pdf"
    feat = _make_feature(scenarios=[_make_scenario(is_outline=True)])
    writer.write(_make_run([feat]), path)
    assert path.exists()


@_reportlab_skip
@pytest.mark.slow
def test_reportlab_engine_with_rule_name(tmp_path: Path) -> None:
    opts = ReportOptions(pdf_engine="reportlab")
    writer = PDFWriter(opts)
    path = tmp_path / "report.pdf"
    feat = _make_feature(scenarios=[_make_scenario(rule_name="Slow tests")])
    writer.write(_make_run([feat]), path)
    assert path.exists()


@_reportlab_skip
@pytest.mark.slow
def test_reportlab_engine_skipped_status(tmp_path: Path) -> None:
    opts = ReportOptions(pdf_engine="reportlab")
    writer = PDFWriter(opts)
    path = tmp_path / "report.pdf"
    feat = _make_feature(
        status="skipped",
        scenarios=[_make_scenario(status="skipped")],
    )
    writer.write(_make_run([feat]), path)
    assert path.exists()


@_reportlab_skip
@pytest.mark.slow
def test_reportlab_engine_error_without_traceback(tmp_path: Path) -> None:
    opts = ReportOptions(pdf_engine="reportlab")
    writer = PDFWriter(opts)
    path = tmp_path / "report.pdf"
    err = ErrorInfo(message="no tb")
    feat = _make_feature(scenarios=[_make_scenario(status="failed", error=err)])
    writer.write(_make_run([feat]), path)
    assert path.exists()


@_reportlab_skip
@pytest.mark.slow
def test_reportlab_engine_error_without_exception_type(tmp_path: Path) -> None:
    opts = ReportOptions(pdf_engine="reportlab")
    writer = PDFWriter(opts)
    path = tmp_path / "report.pdf"
    err = ErrorInfo(message="no type", traceback="tb line")
    feat = _make_feature(scenarios=[_make_scenario(status="failed", error=err)])
    writer.write(_make_run([feat]), path)
    assert path.exists()


# ---------------------------------------------------------------------------
# ReportLabWriter direct usage
# ---------------------------------------------------------------------------


@_reportlab_skip
@pytest.mark.slow
def test_reportlab_writer_direct(tmp_path: Path) -> None:
    writer = ReportLabWriter()
    path = tmp_path / "report.pdf"
    writer.write(_make_run(), path)
    assert path.exists()
    assert path.stat().st_size > 0


@_reportlab_skip
@pytest.mark.slow
def test_reportlab_writer_with_options(tmp_path: Path) -> None:
    opts = ReportOptions(title="Custom RL Title")
    writer = ReportLabWriter(opts)
    path = tmp_path / "report.pdf"
    run = _make_run()
    run.title = "Custom RL Title"
    writer.write(run, path)
    assert path.exists()


# ---------------------------------------------------------------------------
# ReportLab not installed
# ---------------------------------------------------------------------------


def test_reportlab_writer_raises_import_error_without_reportlab(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "reportlab" or name.startswith("reportlab."):
            raise ImportError("No module named 'reportlab'")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", fake_import)
    writer = ReportLabWriter()
    with pytest.raises(ImportError, match="ReportLab is required"):
        writer.write(_make_run(), tmp_path / "report.pdf")


def test_pdf_writer_reportlab_engine_raises_import_error_without_reportlab(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "reportlab" or name.startswith("reportlab."):
            raise ImportError("No module named 'reportlab'")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", fake_import)
    opts = ReportOptions(pdf_engine="reportlab")
    writer = PDFWriter(opts)
    with pytest.raises(ImportError, match="ReportLab is required"):
        writer.write(_make_run(), tmp_path / "report.pdf")


# ---------------------------------------------------------------------------
# _format_duration helper
# ---------------------------------------------------------------------------


def test_format_duration_seconds() -> None:
    assert _format_duration(3.5) == "3.50s"


def test_format_duration_milliseconds() -> None:
    assert _format_duration(0.005) == "5ms"


def test_format_duration_zero() -> None:
    assert _format_duration(0.0) == "0ms"


def test_format_duration_sub_millisecond() -> None:
    assert _format_duration(0.0001) == "0ms"


def test_format_duration_exact_one_second() -> None:
    assert _format_duration(1.0) == "1.00s"
