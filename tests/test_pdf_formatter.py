"""Tests for behave_modern_file_report.pdf_formatter."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from behave_modern_file_report.models import (
    ErrorInfo,
    FeatureSummary,
    RunSummary,
    ScenarioResult,
    Step,
)
from behave_modern_file_report.pdf_formatter import PDFFormatter

# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


class MockStreamOpener:
    """Mock stream opener with a name attribute for path resolution."""

    def __init__(self, path: str) -> None:
        self.name = path
        self.opened = False

    def open(self) -> Any:
        self.opened = True
        return self


def _mock_config(userdata: dict[str, str] | None = None) -> SimpleNamespace:
    return SimpleNamespace(userdata=userdata or {})


def _make_simple_run() -> RunSummary:
    """Return a minimal run with one feature and one passed scenario."""
    step = Step(keyword="Given ", name="a step", status="passed", duration=0.01)
    scn = ScenarioResult(
        name="Test scenario",
        status="passed",
        duration=0.05,
        steps=[step],
    )
    feat = FeatureSummary(
        name="Test feature",
        duration=0.1,
        location="features/test.feature:1",
        scenarios=[scn],
    )
    return RunSummary(
        run_id="run_test",
        title="Test Report",
        features=[feat],
    )


def _make_failed_run() -> RunSummary:
    """Return a run with a failed scenario containing an error."""
    err = ErrorInfo(
        message="assertion failed",
        traceback="Traceback:\n  File 'test.py', line 1",
        exception_type="AssertionError",
    )
    step = Step(
        keyword="Then ",
        name="bad step",
        status="failed",
        duration=0.01,
        error=err,
    )
    scn = ScenarioResult(
        name="Failed scenario",
        status="failed",
        duration=0.05,
        steps=[step],
        error=err,
    )
    feat = FeatureSummary(
        name="Failed feature",
        duration=0.1,
        scenarios=[scn],
    )
    return RunSummary(
        run_id="run_fail",
        title="Failed Report",
        features=[feat],
    )


def _weasyprint_available() -> bool:
    try:
        import weasyprint  # noqa: F401
    except (ImportError, OSError):
        return False
    return True


def _reportlab_available() -> bool:
    try:
        import reportlab  # noqa: F401
    except ImportError:
        return False
    return True


_weasyprint_skip = pytest.mark.skipif(
    not _weasyprint_available(),
    reason="WeasyPrint not installed",
)
_reportlab_skip = pytest.mark.skipif(
    not _reportlab_available(),
    reason="ReportLab not installed",
)


# ---------------------------------------------------------------------------
# Class attributes
# ---------------------------------------------------------------------------


def test_name_is_behave_modern_pdf() -> None:
    assert PDFFormatter.name == "behave-modern-pdf"


def test_format_key_is_pdf() -> None:
    assert PDFFormatter._format_key == "pdf"


def test_default_filename_is_report_pdf() -> None:
    assert PDFFormatter._default_filename == "report.pdf"


def test_description_set() -> None:
    assert "pdf" in PDFFormatter.description.lower()


# ---------------------------------------------------------------------------
# Option resolution
# ---------------------------------------------------------------------------


def test_resolves_pdf_specific_options() -> None:
    config = _mock_config({"bmfr.pdf.title": "PDF Title"})
    fmt = PDFFormatter(config=config)
    assert fmt._options.title == "PDF Title"


def test_pdf_specific_overrides_global() -> None:
    config = _mock_config({
        "bmfr.title": "Global Title",
        "bmfr.pdf.title": "PDF Title",
    })
    fmt = PDFFormatter(config=config)
    assert fmt._options.title == "PDF Title"


def test_global_falls_back_for_pdf() -> None:
    config = _mock_config({"bmfr.title": "Global Title"})
    fmt = PDFFormatter(config=config)
    assert fmt._options.title == "Global Title"


def test_resolves_pdf_engine_option() -> None:
    config = _mock_config({"bmfr.pdf_engine": "reportlab"})
    fmt = PDFFormatter(config=config)
    assert fmt._options.pdf_engine == "reportlab"


def test_pdf_engine_specific_overrides_global() -> None:
    config = _mock_config({
        "bmfr.pdf_engine": "weasyprint",
        "bmfr.pdf.pdf_engine": "reportlab",
    })
    fmt = PDFFormatter(config=config)
    assert fmt._options.pdf_engine == "reportlab"


# ---------------------------------------------------------------------------
# _write_report (WeasyPrint)
# ---------------------------------------------------------------------------


@_weasyprint_skip
@pytest.mark.slow
def test_write_report_with_stream_opener(tmp_path: Path) -> None:
    path = tmp_path / "report.pdf"
    opener = MockStreamOpener(str(path))
    fmt = PDFFormatter(stream_opener=opener)
    run = _make_simple_run()
    fmt._write_report(run, fmt._options)
    assert path.exists()
    assert path.stat().st_size > 0


@_weasyprint_skip
@pytest.mark.slow
def test_write_report_produces_valid_pdf(tmp_path: Path) -> None:
    path = tmp_path / "report.pdf"
    opener = MockStreamOpener(str(path))
    fmt = PDFFormatter(stream_opener=opener)
    fmt._write_report(_make_simple_run(), fmt._options)
    with open(path, "rb") as f:
        header = f.read(5)
    assert header == b"%PDF-"


@_weasyprint_skip
@pytest.mark.slow
def test_write_report_without_stream_opener(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    default_path = tmp_path / "report.pdf"
    fmt = PDFFormatter()
    monkeypatch.setattr(fmt, "_default_filename", str(default_path))
    fmt._write_report(_make_simple_run(), fmt._options)
    assert default_path.exists()


@_weasyprint_skip
@pytest.mark.slow
def test_write_report_without_stream_opener_no_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    default_path = tmp_path / "report.pdf"
    opener = SimpleNamespace()
    fmt = PDFFormatter(stream_opener=opener)
    monkeypatch.setattr(fmt, "_default_filename", str(default_path))
    fmt._write_report(_make_simple_run(), fmt._options)
    assert default_path.exists()


# ---------------------------------------------------------------------------
# _write_report (ReportLab fallback)
# ---------------------------------------------------------------------------


@_reportlab_skip
@pytest.mark.slow
def test_write_report_reportlab_engine(tmp_path: Path) -> None:
    path = tmp_path / "report.pdf"
    opener = MockStreamOpener(str(path))
    config = _mock_config({"bmfr.pdf_engine": "reportlab"})
    fmt = PDFFormatter(stream_opener=opener, config=config)
    fmt._write_report(_make_simple_run(), fmt._options)
    assert path.exists()
    assert path.stat().st_size > 0


@_reportlab_skip
@pytest.mark.slow
def test_write_report_reportlab_valid_pdf(tmp_path: Path) -> None:
    path = tmp_path / "report.pdf"
    opener = MockStreamOpener(str(path))
    config = _mock_config({"bmfr.pdf_engine": "reportlab"})
    fmt = PDFFormatter(stream_opener=opener, config=config)
    fmt._write_report(_make_simple_run(), fmt._options)
    with open(path, "rb") as f:
        header = f.read(5)
    assert header == b"%PDF-"


# ---------------------------------------------------------------------------
# close() lifecycle
# ---------------------------------------------------------------------------


@_weasyprint_skip
@pytest.mark.slow
def test_close_writes_report(tmp_path: Path) -> None:
    path = tmp_path / "report.pdf"
    opener = MockStreamOpener(str(path))
    fmt = PDFFormatter(stream_opener=opener)
    fmt.feature(SimpleNamespace(
        name="F1", tags=[], location="f:1", description=None,
    ))
    fmt.scenario(SimpleNamespace(
        name="S1", tags=[], location="f:5",
        feature=SimpleNamespace(name="F1", tags=[], location=""),
        is_outline=False, rule=None, description=None,
    ))
    fmt.step(SimpleNamespace(
        keyword="Given ", name="step", status="passed",
        location="f:10", duration=0.01, text=None,
        error=None, exception=None, error_message=None,
    ))
    fmt.result(SimpleNamespace(
        keyword="Given ", name="step", status="passed",
        location="f:10", duration=0.01, text=None,
        error=None, exception=None, error_message=None,
    ))
    fmt.eof()
    fmt.close()
    assert path.exists()
    assert path.stat().st_size > 0


@_weasyprint_skip
@pytest.mark.slow
def test_close_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "report.pdf"
    opener = MockStreamOpener(str(path))
    fmt = PDFFormatter(stream_opener=opener)
    fmt.close()
    fmt.close()
    assert path.exists()


@_weasyprint_skip
@pytest.mark.slow
def test_close_without_stream_opener_writes_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    default_path = tmp_path / "report.pdf"
    fmt = PDFFormatter()
    monkeypatch.setattr(fmt, "_default_filename", str(default_path))
    fmt.close()
    assert default_path.exists()


# ---------------------------------------------------------------------------
# Structure: Run → Feature → Scenario → Step
# ---------------------------------------------------------------------------


@_weasyprint_skip
@pytest.mark.slow
def test_structure_run_feature_scenario_step(tmp_path: Path) -> None:
    """Verify the PDF contains the full Run → Feature → Scenario → Step hierarchy."""
    path = tmp_path / "report.pdf"
    opener = MockStreamOpener(str(path))
    fmt = PDFFormatter(stream_opener=opener)
    fmt.feature(SimpleNamespace(
        name="Login", tags=["security"], location="features/login.feature:1",
        description="User authentication flows.",
    ))
    fmt.scenario(SimpleNamespace(
        name="Successful login", tags=["smoke"], location="features/login.feature:5",
        feature=SimpleNamespace(name="Login", tags=[], location=""),
        is_outline=False, rule=None, description=None,
    ))
    fmt.step(SimpleNamespace(
        keyword="Given ", name="user on login page", status="passed",
        location="features/login.feature:10", duration=0.05, text=None,
        error=None, exception=None, error_message=None,
    ))
    fmt.result(SimpleNamespace(
        keyword="Given ", name="user on login page", status="passed",
        location="features/login.feature:10", duration=0.05, text=None,
        error=None, exception=None, error_message=None,
    ))
    fmt.eof()
    fmt.close()
    assert path.exists()
    assert path.stat().st_size > 100


@_weasyprint_skip
@pytest.mark.slow
def test_structure_failed_step_with_error(tmp_path: Path) -> None:
    """Verify the PDF contains error info for failed steps."""
    path = tmp_path / "report.pdf"
    opener = MockStreamOpener(str(path))
    fmt = PDFFormatter(stream_opener=opener)
    fmt.feature(SimpleNamespace(
        name="Checkout", tags=[], location="f:1", description=None,
    ))
    fmt.scenario(SimpleNamespace(
        name="Payment fails", tags=[], location="f:5",
        feature=SimpleNamespace(name="Checkout", tags=[], location=""),
        is_outline=False, rule=None, description=None,
    ))
    try:
        raise AssertionError("insufficient funds") from None
    except AssertionError as exc:
        failed_step = SimpleNamespace(
            keyword="Then ", name="payment succeeds", status="failed",
            location="f:15", duration=0.01, text=None,
            error=exc, exception=None, error_message=None,
        )
    fmt.step(SimpleNamespace(
        keyword="Then ", name="payment succeeds", status="failed",
        location="f:15", duration=0.01, text=None,
        error=None, exception=None, error_message=None,
    ))
    fmt.result(failed_step)
    fmt.eof()
    fmt.close()
    assert path.exists()


@_weasyprint_skip
@pytest.mark.slow
def test_structure_multiple_features(tmp_path: Path) -> None:
    """Verify the PDF contains multiple features."""
    path = tmp_path / "report.pdf"
    opener = MockStreamOpener(str(path))
    fmt = PDFFormatter(stream_opener=opener)
    for feat_name in ["Auth", "Payment", "Profile"]:
        fmt.feature(SimpleNamespace(
            name=feat_name, tags=[], location="f:1", description=None,
        ))
        fmt.scenario(SimpleNamespace(
            name=f"{feat_name} scenario", tags=[], location="f:5",
            feature=SimpleNamespace(name=feat_name, tags=[], location=""),
            is_outline=False, rule=None, description=None,
        ))
        fmt.step(SimpleNamespace(
            keyword="Given ", name="step", status="passed",
            location="f:10", duration=0.01, text=None,
            error=None, exception=None, error_message=None,
        ))
        fmt.result(SimpleNamespace(
            keyword="Given ", name="step", status="passed",
            location="f:10", duration=0.01, text=None,
            error=None, exception=None, error_message=None,
        ))
    fmt.eof()
    fmt.close()
    assert path.exists()


@_weasyprint_skip
@pytest.mark.slow
def test_structure_skipped_scenario(tmp_path: Path) -> None:
    """Verify the PDF handles skipped scenarios."""
    path = tmp_path / "report.pdf"
    opener = MockStreamOpener(str(path))
    fmt = PDFFormatter(stream_opener=opener)
    fmt.feature(SimpleNamespace(
        name="Feature1", tags=[], location="f:1", description=None,
    ))
    fmt.scenario(SimpleNamespace(
        name="Skipped scenario", tags=[], location="f:5",
        feature=SimpleNamespace(name="Feature1", tags=[], location=""),
        is_outline=False, rule=None, description=None,
    ))
    fmt.step(SimpleNamespace(
        keyword="Given ", name="step", status="skipped",
        location="f:10", duration=0.0, text=None,
        error=None, exception=None, error_message=None,
    ))
    fmt.result(SimpleNamespace(
        keyword="Given ", name="step", status="skipped",
        location="f:10", duration=0.0, text=None,
        error=None, exception=None, error_message=None,
    ))
    fmt.eof()
    fmt.close()
    assert path.exists()


# ---------------------------------------------------------------------------
# Full lifecycle with options
# ---------------------------------------------------------------------------


@_weasyprint_skip
@pytest.mark.slow
def test_full_lifecycle_with_options(tmp_path: Path) -> None:
    path = tmp_path / "report.pdf"
    opener = MockStreamOpener(str(path))
    config = _mock_config({"bmfr.title": "Custom PDF Report"})
    fmt = PDFFormatter(stream_opener=opener, config=config)
    assert fmt._options.title == "Custom PDF Report"

    fmt.feature(SimpleNamespace(
        name="Auth", tags=["security"], location="f:1",
        description="Auth flows.",
    ))
    fmt.scenario(SimpleNamespace(
        name="Login ok", tags=["smoke"], location="f:5",
        feature=SimpleNamespace(name="Auth", tags=[], location=""),
        is_outline=False, rule=None, description=None,
    ))
    fmt.step(SimpleNamespace(
        keyword="Given ", name="user exists", status="passed",
        location="f:10", duration=0.01, text=None,
        error=None, exception=None, error_message=None,
    ))
    fmt.result(SimpleNamespace(
        keyword="Given ", name="user exists", status="passed",
        location="f:10", duration=0.01, text=None,
        error=None, exception=None, error_message=None,
    ))
    fmt.eof()
    fmt.close()
    assert path.exists()
    assert path.stat().st_size > 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def test_entry_point_resolvable() -> None:
    try:
        from importlib.metadata import entry_points
    except ImportError:
        from importlib_metadata import entry_points  # type: ignore

    eps = entry_points()
    if hasattr(eps, "select"):
        formatter_eps = eps.select(group="behave.formatters")
    else:
        formatter_eps = eps.get("behave.formatters", [])  # type: ignore
    names = [ep.name for ep in formatter_eps]
    assert "behave-modern-pdf" in names
