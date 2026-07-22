"""Tests for behave_modern_file_reports.txt_formatter."""

from __future__ import annotations

import io
from types import SimpleNamespace
from typing import Any, cast

import pytest

from behave_modern_file_reports.models import (
    FeatureSummary,
    RunSummary,
    ScenarioResult,
    Step,
)
from behave_modern_file_reports.txt_formatter import TXTFormatter

# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


class MockStreamOpener:
    """Mock stream opener that returns a StringIO."""

    def __init__(self) -> None:
        self.stream = io.StringIO()
        self.opened = False

    def open(self) -> io.StringIO:
        self.opened = True
        return self.stream


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


# ---------------------------------------------------------------------------
# Class attributes
# ---------------------------------------------------------------------------


def test_name_is_behave_modern_txt() -> None:
    """TXTFormatter.name is 'behave-modern-txt'."""
    assert TXTFormatter.name == "behave-modern-txt"


def test_format_key_is_txt() -> None:
    """TXTFormatter._format_key is 'txt'."""
    assert TXTFormatter._format_key == "txt"


def test_default_filename_is_report_txt() -> None:
    """TXTFormatter._default_filename is 'report.txt'."""
    assert TXTFormatter._default_filename == "report.txt"


def test_description_set() -> None:
    """TXTFormatter has a description."""
    assert "text" in TXTFormatter.description.lower()


# ---------------------------------------------------------------------------
# Option resolution
# ---------------------------------------------------------------------------


def test_resolves_txt_specific_options() -> None:
    """bmfr.txt.* keys are resolved by the formatter."""
    config = _mock_config({
        "bmfr.txt_width": "120",
        "bmfr.txt_ascii": "true",
    })
    fmt = TXTFormatter(config=config)
    assert fmt._options.txt_width == 120
    assert fmt._options.txt_ascii is True


def test_txt_specific_overrides_global() -> None:
    """bmfr.txt.title takes precedence over bmfr.title."""
    config = _mock_config({
        "bmfr.title": "Global Title",
        "bmfr.txt.title": "TXT Title",
    })
    fmt = TXTFormatter(config=config)
    assert fmt._options.title == "TXT Title"


def test_global_falls_back_for_txt() -> None:
    """When no txt-specific key, falls back to bmfr.<key>."""
    config = _mock_config({"bmfr.title": "Global Title"})
    fmt = TXTFormatter(config=config)
    assert fmt._options.title == "Global Title"


# ---------------------------------------------------------------------------
# _write_report with stream opener
# ---------------------------------------------------------------------------


def test_write_report_uses_stream_opener() -> None:
    """_write_report writes to the stream from the stream opener."""
    opener = MockStreamOpener()
    fmt = TXTFormatter(stream_opener=opener)
    run = _make_simple_run()
    fmt._write_report(run, fmt._options)
    assert opener.opened
    content = opener.stream.getvalue()
    assert "Test Report" in content
    assert "Test feature" in content
    assert "Test scenario" in content


def test_open_stream_uses_utf8_encoding() -> None:
    """TXTFormatter forces the stream opener to use UTF-8 encoding."""
    opener = SimpleNamespace(
        name="report.txt",
        encoding="cp1252",
        stream=None,
        open=SimpleNamespace,
    )
    called: dict[str, Any] = {}

    def fake_open() -> io.StringIO:
        called["encoding"] = opener.encoding
        opener.stream = io.StringIO()
        return cast(io.StringIO, opener.stream)

    opener.open = fake_open
    fmt = TXTFormatter(stream_opener=opener)
    stream = fmt._open_stream()
    assert called["encoding"] == "utf-8"
    assert stream is opener.stream


def test_close_writes_report_via_stream_opener() -> None:
    """close() calls _write_report which uses the stream opener."""
    opener = MockStreamOpener()
    fmt = TXTFormatter(stream_opener=opener)
    # Simulate a full lifecycle
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
    content = opener.stream.getvalue()
    assert "F1" in content
    assert "S1" in content
    assert "step" in content


def test_close_is_idempotent() -> None:
    """close() called twice only writes once."""
    opener = MockStreamOpener()
    fmt = TXTFormatter(stream_opener=opener)
    fmt.close()
    fmt.close()
    content = opener.stream.getvalue()
    # Should have content from only one write
    assert content.count("SUMMARY") == 1


# ---------------------------------------------------------------------------
# _write_report without stream opener (file fallback)
# ---------------------------------------------------------------------------


def test_write_report_without_stream_opener_opens_file(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_write_report without stream_opener writes to a default file."""
    default_file = tmp_path / "report.txt"
    fmt = TXTFormatter()
    monkeypatch.setattr(fmt, "_default_filename", str(default_file))
    run = _make_simple_run()
    fmt._write_report(run, fmt._options)
    content = default_file.read_text(encoding="utf-8")
    assert "Test Report" in content
    assert "Test feature" in content


def test_close_without_stream_opener_writes_file(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """close() without stream_opener writes to a file."""
    default_file = tmp_path / "report.txt"
    fmt = TXTFormatter()
    monkeypatch.setattr(fmt, "_default_filename", str(default_file))
    fmt.close()
    content = default_file.read_text(encoding="utf-8")
    assert "Behave Modern Report" in content


# ---------------------------------------------------------------------------
# Full lifecycle integration
# ---------------------------------------------------------------------------


def test_full_lifecycle_with_options() -> None:
    """Full lifecycle with custom options produces expected output."""
    config = _mock_config({
        "bmfr.txt_width": "80",
        "bmfr.txt_ascii": "true",
        "bmfr.title": "Integration TXT Report",
    })
    opener = MockStreamOpener()
    fmt = TXTFormatter(stream_opener=opener, config=config)
    assert fmt._options.txt_width == 80
    assert fmt._options.txt_ascii is True
    assert fmt._options.title == "Integration TXT Report"

    fmt.feature(SimpleNamespace(
        name="Login", tags=["auth"], location="f:1",
        description="Login flows.",
    ))
    fmt.scenario(SimpleNamespace(
        name="Login succeeds", tags=["smoke"], location="f:5",
        feature=SimpleNamespace(name="Login", tags=[], location=""),
        is_outline=False, rule=None, description=None,
    ))
    fmt.step(SimpleNamespace(
        keyword="Given ", name="user on page", status="passed",
        location="f:10", duration=0.01, text=None,
        error=None, exception=None, error_message=None,
    ))
    fmt.result(SimpleNamespace(
        keyword="Given ", name="user on page", status="passed",
        location="f:10", duration=0.01, text=None,
        error=None, exception=None, error_message=None,
    ))
    fmt.eof()
    fmt.close()

    content = opener.stream.getvalue()
    assert "Integration TXT Report" in content
    assert "Login" in content
    assert "Login succeeds" in content
    assert "user on page" in content
    assert "[PASS]" in content
    assert "auth" in content
    assert "smoke" in content


def test_write_report_with_failed_scenario() -> None:
    """Report includes error info for failed scenarios."""
    opener = MockStreamOpener()
    fmt = TXTFormatter(stream_opener=opener)

    try:
        raise AssertionError("something went wrong") from None
    except AssertionError as exc:
        failed_step = SimpleNamespace(
            keyword="Then ", name="bad step", status="failed",
            location="f:15", duration=0.01, text=None,
            error=exc, exception=None, error_message=None,
        )

    fmt.feature(SimpleNamespace(
        name="F1", tags=[], location="f:1", description=None,
    ))
    fmt.scenario(SimpleNamespace(
        name="S1", tags=[], location="f:5",
        feature=SimpleNamespace(name="F1", tags=[], location=""),
        is_outline=False, rule=None, description=None,
    ))
    fmt.step(SimpleNamespace(
        keyword="Then ", name="bad step", status="failed",
        location="f:15", duration=0.01, text=None,
        error=None, exception=None, error_message=None,
    ))
    fmt.result(failed_step)
    fmt.eof()
    fmt.close()

    content = opener.stream.getvalue()
    assert "FAILED" in content
    assert "something went wrong" in content
    assert "AssertionError" in content


# ---------------------------------------------------------------------------
# Entry point verification
# ---------------------------------------------------------------------------


def test_entry_point_resolvable() -> None:
    """The behave-modern-txt entry point can be resolved."""
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
    assert "behave-modern-txt" in names


def test_close_without_title_or_project_uses_defaults() -> None:
    """close() without title/project options uses RunSummary defaults."""
    opener = MockStreamOpener()
    fmt = TXTFormatter(stream_opener=opener)
    fmt.close()
    content = opener.stream.getvalue()
    assert "Behave Modern Report" in content


def test_close_with_title_but_no_project_name() -> None:
    """close() with title but no project_name only applies title."""
    config = _mock_config({"bmfr.title": "Custom Title"})
    opener = MockStreamOpener()
    fmt = TXTFormatter(stream_opener=opener, config=config)
    fmt.close()
    content = opener.stream.getvalue()
    assert "Custom Title" in content


def test_close_with_project_name_in_output() -> None:
    """close() with project_name option shows it in the report."""
    config = _mock_config({"bmfr.project_name": "My Project"})
    opener = MockStreamOpener()
    fmt = TXTFormatter(stream_opener=opener, config=config)
    fmt.close()
    content = opener.stream.getvalue()
    assert "My Project" in content


def test_write_report_stream_opener_without_open_method(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_write_report with stream_opener lacking open() falls back to file."""
    default_file = tmp_path / "report.txt"
    opener = SimpleNamespace()  # No open method
    fmt = TXTFormatter(stream_opener=opener)
    monkeypatch.setattr(fmt, "_default_filename", str(default_file))
    run = _make_simple_run()
    fmt._write_report(run, fmt._options)
    content = default_file.read_text(encoding="utf-8")
    assert "Test Report" in content


def test_close_stream_without_flush() -> None:
    """_close_stream handles streams without a flush method."""
    opener = MockStreamOpener()
    fmt = TXTFormatter(stream_opener=opener)
    stream = SimpleNamespace(write=lambda s: None, close=lambda: None)
    fmt._close_stream(stream)  # Should not raise
