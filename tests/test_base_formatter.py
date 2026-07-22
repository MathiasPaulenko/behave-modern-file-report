"""Tests for behave_modern_file_report.base_formatter."""

from __future__ import annotations

import mimetypes
from types import SimpleNamespace
from typing import Any

import pytest

from behave_modern_file_report.base_formatter import BaseFileFormatter
from behave_modern_file_report.models import (
    Attachment,
    ReportOptions,
    RunSummary,
)

# ---------------------------------------------------------------------------
# Concrete subclass for testing
# ---------------------------------------------------------------------------


class TestFormatter(BaseFileFormatter):
    """Concrete formatter for testing."""

    __test__ = False
    name = "test-formatter"
    description = "Test formatter"
    _format_key = "pdf"
    _default_filename = "report.pdf"

    def __init__(
        self,
        stream_opener: Any | None = None,
        config: Any | None = None,
    ) -> None:
        super().__init__(stream_opener, config)
        self.write_calls: list[tuple[RunSummary, ReportOptions]] = []

    def _write_report(self, run_summary: RunSummary, options: ReportOptions) -> None:
        self.write_calls.append((run_summary, options))


class MockStreamOpener:
    """Mock stream opener with a name attribute."""

    def __init__(self, name: Any) -> None:
        self.name = name
        self.stream = None


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _mock_config(userdata: dict[str, str] | None = None) -> SimpleNamespace:
    """Create a mock Behave config with userdata."""
    return SimpleNamespace(userdata=userdata or {})


def _mock_feature(name: str = "F1") -> SimpleNamespace:
    return SimpleNamespace(
        name=name, tags=[], location="f:1", description=None,
    )


def _mock_scenario(name: str = "S1") -> SimpleNamespace:
    return SimpleNamespace(
        name=name, tags=[], location="f:5",
        feature=SimpleNamespace(name="F1", tags=[], location=""),
        is_outline=False, rule=None, description=None,
    )


def _mock_step(
    name: str = "step",
    status: str = "passed",
    duration: float = 0.01,
) -> SimpleNamespace:
    return SimpleNamespace(
        keyword="Given", name=name, status=status,
        location="f:10", duration=duration, text=None,
        error=None, exception=None, error_message=None,
    )


def _mock_background(name: str = "Background") -> SimpleNamespace:
    """Create a mock Behave background."""
    return SimpleNamespace(name=name, location="f:2")


# ---------------------------------------------------------------------------
# __init__ and option resolution
# ---------------------------------------------------------------------------


def test_init_with_no_config() -> None:
    """Formatter with no config uses default ReportOptions."""
    fmt = TestFormatter()
    assert fmt._options.only_failed is False
    assert fmt._options.title == "Behave Modern Report"
    assert fmt._closed is False


def test_init_with_config_resolves_options() -> None:
    """Formatter resolves bmfr.* keys from config.userdata."""
    config = _mock_config({
        "bmfr.title": "Custom Title",
        "bmfr.only_failed": "true",
    })
    fmt = TestFormatter(config=config)
    assert fmt._options.title == "Custom Title"
    assert fmt._options.only_failed is True


def test_init_format_specific_override() -> None:
    """bmfr.pdf.logo takes precedence over bmfr.logo for PDF formatter."""
    config = _mock_config({
        "bmfr.logo": "global_logo.png",
        "bmfr.pdf.logo": "pdf_logo.png",
    })
    fmt = TestFormatter(config=config)
    assert fmt._options.logo == "pdf_logo.png"


def test_init_format_specific_falls_back_to_global() -> None:
    """When no format-specific key, falls back to bmfr.<key>."""
    config = _mock_config({
        "bmfr.logo": "global_logo.png",
    })
    fmt = TestFormatter(config=config)
    assert fmt._options.logo == "global_logo.png"


def test_init_max_traceback_lines_passed_to_collector() -> None:
    """max_traceback_lines from options is passed to the Collector."""
    config = _mock_config({"bmfr.max_traceback_lines": "10"})
    fmt = TestFormatter(config=config)
    assert fmt._collector._max_traceback_lines == 10


def test_init_with_none_userdata() -> None:
    """Formatter handles config with None userdata."""
    config = SimpleNamespace(userdata=None)
    fmt = TestFormatter(config=config)
    assert fmt._options.title == "Behave Modern Report"


def test_init_with_stream_opener() -> None:
    """Formatter stores the stream opener."""
    opener = SimpleNamespace()
    fmt = TestFormatter(stream_opener=opener)
    assert fmt._stream_opener is opener


# ---------------------------------------------------------------------------
# Behave protocol methods
# ---------------------------------------------------------------------------


def test_uri_is_noop() -> None:
    """uri() does not raise."""
    fmt = TestFormatter()
    fmt.uri("features/test.feature")


def test_feature_starts_collector_feature() -> None:
    """feature() starts a feature in the collector."""
    fmt = TestFormatter()
    fmt.feature(_mock_feature(name="MyFeature"))
    assert fmt._collector._current_feature is not None
    assert fmt._collector._current_feature.name == "MyFeature"


def test_background_starts_collector_background() -> None:
    """background() starts a background in the collector."""
    fmt = TestFormatter()
    fmt.feature(_mock_feature())
    fmt.background(SimpleNamespace(name="Background", location="f:3"))
    assert fmt._collector._current_background is not None
    assert fmt._collector._in_background is True


def test_rule_is_noop() -> None:
    """rule() does not raise."""
    fmt = TestFormatter()
    fmt.rule(SimpleNamespace(name="My Rule"))


def test_scenario_starts_collector_scenario() -> None:
    """scenario() starts a scenario in the collector."""
    fmt = TestFormatter()
    fmt.feature(_mock_feature())
    fmt.scenario(_mock_scenario(name="MyScenario"))
    assert fmt._collector._current_scenario is not None
    assert fmt._collector._current_scenario.name == "MyScenario"


def test_step_starts_collector_step() -> None:
    """step() queues a step in the collector."""
    fmt = TestFormatter()
    fmt.feature(_mock_feature())
    fmt.scenario(_mock_scenario())
    fmt.step(_mock_step(name="my step"))
    assert len(fmt._collector._step_queue) == 1
    assert fmt._collector._step_queue[0].name == "my step"


def test_result_finalizes_step() -> None:
    """result() finalizes the step with status and duration."""
    fmt = TestFormatter()
    fmt.feature(_mock_feature())
    fmt.scenario(_mock_scenario())
    fmt.step(_mock_step(name="step 1"))
    fmt.result(_mock_step(name="step 1", status="passed", duration=0.05))
    assert len(fmt._collector._step_queue) == 0
    assert fmt._collector._current_scenario is not None
    assert len(fmt._collector._current_scenario.steps) == 1
    assert fmt._collector._current_scenario.steps[0].status == "passed"


def test_background_steps_are_attached_to_feature_and_scenarios() -> None:
    """Background steps are captured and attached to the feature/scenarios."""
    fmt = TestFormatter()
    fmt.feature(_mock_feature(name="F1"))
    fmt.background(_mock_background(name="BG"))
    fmt.step(_mock_step(name="bg step"))
    fmt.result(_mock_step(name="bg step", status="passed"))
    fmt.scenario(_mock_scenario(name="S1"))
    fmt.step(_mock_step(name="sc step"))
    fmt.result(_mock_step(name="sc step", status="passed"))
    fmt.eof()
    fmt.close()

    run = fmt.write_calls[0][0]
    assert len(run.features) == 1
    feature = run.features[0]
    assert feature.background is not None
    assert [s.name for s in feature.background.steps] == ["bg step"]
    assert len(feature.scenarios) == 1
    scenario = feature.scenarios[0]
    assert [s.name for s in scenario.steps] == ["sc step"]
    assert scenario.background is feature.background


def test_eof_finalizes_scenario_and_feature() -> None:
    """eof() finalizes the current scenario and feature."""
    fmt = TestFormatter()
    fmt.feature(_mock_feature())
    fmt.scenario(_mock_scenario())
    fmt.step(_mock_step())
    fmt.result(_mock_step(status="passed"))
    fmt.eof()
    assert fmt._collector._current_scenario is None
    assert fmt._collector._current_feature is None
    assert len(fmt._collector._features) == 1


# ---------------------------------------------------------------------------
# close()
# ---------------------------------------------------------------------------


def test_close_calls_write_report_once() -> None:
    """close() calls _write_report exactly once."""
    fmt = TestFormatter()
    fmt.feature(_mock_feature())
    fmt.scenario(_mock_scenario())
    fmt.step(_mock_step())
    fmt.result(_mock_step(status="passed"))
    fmt.eof()
    fmt.close()
    assert len(fmt.write_calls) == 1
    run, opts = fmt.write_calls[0]
    assert isinstance(run, RunSummary)
    assert isinstance(opts, ReportOptions)
    assert len(run.features) == 1


def test_close_is_idempotent() -> None:
    """close() called twice only writes once."""
    fmt = TestFormatter()
    fmt.close()
    fmt.close()
    assert len(fmt.write_calls) == 1


def test_close_with_empty_run() -> None:
    """close() with no events produces an empty run."""
    fmt = TestFormatter()
    fmt.close()
    assert len(fmt.write_calls) == 1
    run, _ = fmt.write_calls[0]
    assert len(run.features) == 0


def test_close_passes_options_to_write_report() -> None:
    """close() passes the resolved options to _write_report."""
    config = _mock_config({"bmfr.title": "My Report"})
    fmt = TestFormatter(config=config)
    fmt.close()
    _, opts = fmt.write_calls[0]
    assert opts.title == "My Report"


def test_close_only_failed_filters_to_failed_scenarios() -> None:
    """close() filters the run summary to failed scenarios when only_failed is set."""
    config = _mock_config({"bmfr.only_failed": "true"})
    fmt = TestFormatter(config=config)
    fmt.feature(_mock_feature(name="mixed"))
    fmt.scenario(_mock_scenario(name="passing"))
    fmt.step(_mock_step(name="ok"))
    fmt.result(_mock_step(name="ok", status="passed"))
    fmt.scenario(_mock_scenario(name="failing"))
    fmt.step(_mock_step(name="bad"))
    fmt.result(_mock_step(name="bad", status="failed"))
    fmt.feature(_mock_feature(name="all_pass"))
    fmt.scenario(_mock_scenario(name="another"))
    fmt.step(_mock_step(name="ok2"))
    fmt.result(_mock_step(name="ok2", status="passed"))
    fmt.eof()
    fmt.close()
    run = fmt.write_calls[0][0]
    assert len(run.features) == 1
    assert run.features[0].name == "mixed"
    assert len(run.features[0].scenarios) == 1
    assert run.features[0].scenarios[0].name == "failing"


# ---------------------------------------------------------------------------
# Attachments and logs
# ---------------------------------------------------------------------------


def test_attach_buffers_attachment() -> None:
    """attach() buffers an attachment for the current step."""
    fmt = TestFormatter()
    attachment = Attachment(name="screenshot.png", mime_type="image/png")
    fmt.attach(attachment)
    assert len(fmt._attachment_buffer) == 1
    assert fmt._attachment_buffer[0].name == "screenshot.png"


def test_log_buffers_message() -> None:
    """log() buffers a log message for the current step."""
    fmt = TestFormatter()
    fmt.log("something happened")
    assert len(fmt._log_buffer) == 1
    assert fmt._log_buffer[0] == "something happened"


def test_result_flushes_attachments_to_step() -> None:
    """result() flushes buffered attachments to the current step."""
    fmt = TestFormatter()
    fmt.feature(_mock_feature())
    fmt.scenario(_mock_scenario())
    fmt.step(_mock_step(name="step 1"))
    fmt.attach(Attachment(name="screenshot.png", mime_type="image/png"))
    fmt.result(_mock_step(name="step 1", status="passed"))
    assert fmt._collector._current_scenario is not None
    step = fmt._collector._current_scenario.steps[0]
    assert len(step.attachments) == 1
    assert step.attachments[0].name == "screenshot.png"
    assert len(fmt._attachment_buffer) == 0


def test_result_flushes_logs_to_step() -> None:
    """result() flushes buffered logs to the current step."""
    fmt = TestFormatter()
    fmt.feature(_mock_feature())
    fmt.scenario(_mock_scenario())
    fmt.step(_mock_step(name="step 1"))
    fmt.log("navigated to /login")
    fmt.log("clicked submit")
    fmt.result(_mock_step(name="step 1", status="passed"))
    assert fmt._collector._current_scenario is not None
    step = fmt._collector._current_scenario.steps[0]
    assert len(step.logs) == 2
    assert step.logs[0] == "navigated to /login"
    assert step.logs[1] == "clicked submit"
    assert len(fmt._log_buffer) == 0


def test_result_without_current_step_clears_buffers() -> None:
    """result() without a current step still clears buffers."""
    fmt = TestFormatter()
    fmt.attach(Attachment(name="orphan.png", mime_type="image/png"))
    fmt.log("orphan log")
    fmt.result(_mock_step(status="passed"))
    assert len(fmt._attachment_buffer) == 0
    assert len(fmt._log_buffer) == 0


def test_multiple_attachments_and_logs_on_same_step() -> None:
    """Multiple attachments and logs are flushed to the same step."""
    fmt = TestFormatter()
    fmt.feature(_mock_feature())
    fmt.scenario(_mock_scenario())
    fmt.step(_mock_step(name="step 1"))
    fmt.attach(Attachment(name="screenshot1.png", mime_type="image/png"))
    fmt.attach(Attachment(name="screenshot2.png", mime_type="image/png"))
    fmt.log("log 1")
    fmt.log("log 2")
    fmt.log("log 3")
    fmt.result(_mock_step(name="step 1", status="passed"))
    assert fmt._collector._current_scenario is not None
    step = fmt._collector._current_scenario.steps[0]
    assert len(step.attachments) == 2
    assert len(step.logs) == 3


def test_orphan_attachments_flushed_to_last_step_on_scenario_end() -> None:
    """Attachments/logs emitted after the last result are flushed to the last step."""
    fmt = TestFormatter()
    fmt.feature(_mock_feature())
    fmt.scenario(_mock_scenario())
    fmt.step(_mock_step(name="step 1"))
    fmt.result(_mock_step(name="step 1", status="passed"))
    fmt.attach(Attachment(name="post_step.png", mime_type="image/png"))
    fmt.log("after step log")
    fmt.eof()
    fmt.close()
    scenario = fmt.write_calls[0][0].features[0].scenarios[0]
    assert len(scenario.steps) == 1
    assert len(scenario.steps[0].attachments) == 1
    assert scenario.steps[0].attachments[0].name == "post_step.png"
    assert scenario.steps[0].logs == ["after step log"]


def test_orphan_attachments_discarded_when_no_scenario() -> None:
    """Orphan attachments/logs are discarded when there is no current scenario."""
    fmt = TestFormatter()
    fmt.attach(Attachment(name="orphan.png", mime_type="image/png"))
    fmt.log("orphan log")
    fmt.eof()
    fmt.close()
    assert len(fmt._attachment_buffer) == 0
    assert len(fmt._log_buffer) == 0


# ---------------------------------------------------------------------------
# Full lifecycle integration
# ---------------------------------------------------------------------------


def test_full_lifecycle() -> None:
    """Full formatter lifecycle: feature → scenario → step → result → eof → close."""
    config = _mock_config({
        "bmfr.title": "Integration Report",
        "bmfr.pdf.title": "PDF Integration Report",
    })
    fmt = TestFormatter(config=config)
    assert fmt._options.title == "PDF Integration Report"

    fmt.feature(_mock_feature(name="Login"))
    fmt.scenario(_mock_scenario(name="Login succeeds"))
    fmt.step(_mock_step(name="user on login page"))
    fmt.attach(Attachment(name="page.png", mime_type="image/png"))
    fmt.log("loaded page")
    fmt.result(_mock_step(name="user on login page", status="passed"))
    fmt.step(_mock_step(name="user clicks login"))
    fmt.result(_mock_step(name="user clicks login", status="passed"))
    fmt.eof()
    fmt.close()

    assert len(fmt.write_calls) == 1
    run, opts = fmt.write_calls[0]
    assert opts.title == "PDF Integration Report"
    assert len(run.features) == 1
    feat = run.features[0]
    assert feat.name == "Login"
    assert len(feat.scenarios) == 1
    scn = feat.scenarios[0]
    assert scn.name == "Login succeeds"
    assert scn.status == "passed"
    assert len(scn.steps) == 2
    assert len(scn.steps[0].attachments) == 1
    assert len(scn.steps[0].logs) == 1
    assert len(scn.steps[1].attachments) == 0


def test_write_report_not_implemented_in_base() -> None:
    """BaseFileFormatter._write_report raises NotImplementedError."""
    fmt = BaseFileFormatter()
    with pytest.raises(NotImplementedError):
        fmt._write_report(RunSummary(), ReportOptions())


def test_stream_opener_stored_and_open_callable() -> None:
    """StreamOpener with open() method is stored correctly."""
    class FakeOpener:
        def open(self) -> str:
            return "stream"

    opener = FakeOpener()
    fmt = TestFormatter(stream_opener=opener)
    assert fmt._stream_opener is opener
    assert opener.open() == "stream"


# ---------------------------------------------------------------------------
# Logo resolution
# ---------------------------------------------------------------------------


def test_resolve_logo_from_file(tmp_path: Any) -> None:
    """Logo file path is resolved to base64 data URI."""
    import base64

    logo_data = b"\x89PNG\r\n\x1a\n\x00\x00"
    logo_file = tmp_path / "logo.png"
    logo_file.write_bytes(logo_data)

    fmt = TestFormatter(config=_mock_config({"bmfr.logo": str(logo_file)}))
    fmt._resolve_logo()

    assert fmt._options.logo_b64.startswith("data:image/png;base64,")
    encoded = fmt._options.logo_b64.split(",", 1)[1]
    assert base64.b64decode(encoded) == logo_data


def test_resolve_logo_skipped_when_already_set() -> None:
    """Logo resolution is skipped when logo_b64 is already set."""
    fmt = TestFormatter(config=_mock_config({"bmfr.logo": "/some/path.png"}))
    fmt._options.logo_b64 = "data:image/png;base64,EXISTING"
    fmt._resolve_logo()
    assert fmt._options.logo_b64 == "data:image/png;base64,EXISTING"


def test_resolve_logo_skipped_when_no_logo() -> None:
    """Logo resolution is skipped when logo is not set."""
    fmt = TestFormatter(config=_mock_config({}))
    fmt._resolve_logo()
    assert fmt._options.logo_b64 == ""


def test_resolve_logo_skipped_when_file_not_found() -> None:
    """Logo resolution is skipped when file does not exist."""
    fmt = TestFormatter(config=_mock_config({"bmfr.logo": "/nonexistent/logo.png"}))
    fmt._resolve_logo()
    assert fmt._options.logo_b64 == ""


def test_resolve_path_from_stream_opener() -> None:
    """_resolve_path returns the stream opener name when available."""
    fmt = TestFormatter(stream_opener=MockStreamOpener("custom_report.txt"))
    assert fmt._resolve_path() == "custom_report.txt"


def test_resolve_path_fallback_to_default() -> None:
    """_resolve_path falls back to the formatter's default filename."""
    fmt = TestFormatter(stream_opener=MockStreamOpener(None))
    assert fmt._resolve_path() == TestFormatter._default_filename


def test_resolve_logo_jpeg_mime(tmp_path: Any) -> None:
    """Logo resolution detects JPEG MIME type."""
    logo_data = b"\xff\xd8\xff\xe0"
    logo_file = tmp_path / "logo.jpg"
    logo_file.write_bytes(logo_data)

    fmt = TestFormatter(config=_mock_config({"bmfr.logo": str(logo_file)}))
    fmt._resolve_logo()

    assert fmt._options.logo_b64.startswith("data:image/jpeg;base64,")


def test_close_resolves_logo() -> None:
    """close() calls _resolve_logo before writing report."""
    fmt = TestFormatter(config=_mock_config({}))
    fmt.close()
    assert len(fmt.write_calls) == 1
    # logo_b64 should be empty (no logo set)
    assert fmt.write_calls[0][1].logo_b64 == ""


def test_resolve_logo_unknown_extension(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Logo with unknown extension defaults to image/png MIME."""
    logo_data = b"\x00\x01\x02\x03"
    logo_file = tmp_path / "logo.xyz"
    logo_file.write_bytes(logo_data)

    # Force the MIME guess to return None so the code falls back to image/png.
    monkeypatch.setattr(mimetypes, "guess_type", lambda _path: (None, None))

    fmt = TestFormatter(config=_mock_config({"bmfr.logo": str(logo_file)}))
    fmt._resolve_logo()

    assert fmt._options.logo_b64.startswith("data:image/png;base64,")


def test_resolve_logo_skipped_for_non_image(tmp_path: Any) -> None:
    """Logo resolution is skipped when the file is not an image."""
    logo_file = tmp_path / "logo.txt"
    logo_file.write_text("not an image")

    fmt = TestFormatter(config=_mock_config({"bmfr.logo": str(logo_file)}))
    fmt._resolve_logo()

    assert fmt._options.logo_b64 == ""


def test_resolve_logo_skips_oversized_files(tmp_path: Any) -> None:
    """Logo resolution skips files larger than the 5 MB limit."""
    logo_file = tmp_path / "logo.png"
    logo_file.write_bytes(b"\x89PNG" + b"x" * (5 * 1024 * 1024))

    fmt = TestFormatter(config=_mock_config({"bmfr.logo": str(logo_file)}))
    fmt._resolve_logo()

    assert fmt._options.logo_b64 == ""
