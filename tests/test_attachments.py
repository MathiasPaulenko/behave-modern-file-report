"""Tests for behave_modern_file_report.attachments and attachment buffer."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from behave_modern_file_report.attachments import (
    _bytes_to_base64,
    _capture_screenshot,
    _check_size,
    _find_formatter,
    _find_formatters,
    _get_max_size_kb,
    _guess_mime_type,
    _is_file_formatter,
    _is_pil_image,
    _is_playwright_page,
    _is_selenium_driver,
    _make_attachment_from_bytes,
    _make_attachment_from_file,
    _make_attachment_from_text,
    attach_file,
    attach_json,
    attach_screenshot,
    attach_text,
)
from behave_modern_file_report.attachments import (
    log as attach_log,
)
from behave_modern_file_report.base_formatter import BaseFileFormatter
from behave_modern_file_report.models import Attachment
from behave_modern_file_report.pdf_formatter import PDFFormatter
from behave_modern_file_report.txt_formatter import TXTFormatter

# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


class MockStreamOpener:
    """Mock stream opener with a name attribute."""

    def __init__(self, path: str) -> None:
        self.name = path


def _mock_config(userdata: dict[str, str] | None = None) -> SimpleNamespace:
    return SimpleNamespace(userdata=userdata or {})


def _make_formatter() -> BaseFileFormatter:
    return TXTFormatter(stream_opener=MockStreamOpener("report.txt"))


def _mock_context(formatter: Any | None = None) -> SimpleNamespace:
    """Build a mock Behave context with a runner containing formatters."""
    if formatter is None:
        formatter = _make_formatter()
    runner = SimpleNamespace(formatters={"txt": formatter})
    return SimpleNamespace(_runner=runner)


# ---------------------------------------------------------------------------
# _find_formatter
# ---------------------------------------------------------------------------


def test_find_formatter_returns_formatter() -> None:
    fmt = _make_formatter()
    ctx = _mock_context(fmt)
    assert _find_formatter(ctx) is fmt


def test_find_formatter_no_runner() -> None:
    ctx = SimpleNamespace()
    assert _find_formatter(ctx) is None


def test_find_formatter_no_formatters_attr() -> None:
    ctx = SimpleNamespace(_runner=SimpleNamespace())
    assert _find_formatter(ctx) is None


def test_find_formatter_empty_formatters() -> None:
    ctx = SimpleNamespace(_runner=SimpleNamespace(formatters={}))
    assert _find_formatter(ctx) is None


def test_find_formatter_no_file_formatter() -> None:
    other = SimpleNamespace()
    ctx = SimpleNamespace(_runner=SimpleNamespace(formatters={"other": other}))
    assert _find_formatter(ctx) is None


def test_find_formatter_formatters_not_dict_or_list() -> None:
    ctx = SimpleNamespace(_runner=SimpleNamespace(formatters="not a dict"))
    assert _find_formatter(ctx) is None


def test_find_formatter_list_formatters() -> None:
    fmt = _make_formatter()
    other = SimpleNamespace()
    ctx = SimpleNamespace(_runner=SimpleNamespace(formatters=[other, fmt]))
    assert _find_formatter(ctx) is fmt


def test_find_formatter_list_no_file_formatter() -> None:
    other = SimpleNamespace()
    ctx = SimpleNamespace(_runner=SimpleNamespace(formatters=[other]))
    assert _find_formatter(ctx) is None


def test_find_formatter_empty_list() -> None:
    ctx = SimpleNamespace(_runner=SimpleNamespace(formatters=[]))
    assert _find_formatter(ctx) is None


def test_find_formatter_first_match_wins() -> None:
    fmt1 = _make_formatter()
    fmt2 = PDFFormatter(stream_opener=MockStreamOpener("report.pdf"))
    ctx = SimpleNamespace(_runner=SimpleNamespace(formatters={"a": fmt1, "b": fmt2}))
    assert _find_formatter(ctx) is fmt1


def test_find_formatter_pdf_formatter() -> None:
    fmt = PDFFormatter(stream_opener=MockStreamOpener("report.pdf"))
    ctx = _mock_context(fmt)
    assert _find_formatter(ctx) is fmt


def test_find_formatters_returns_all_matches() -> None:
    """_find_formatters returns every active file formatter."""
    fmt1 = _make_formatter()
    fmt2 = PDFFormatter(stream_opener=MockStreamOpener("report.pdf"))
    ctx = SimpleNamespace(_runner=SimpleNamespace(formatters=[fmt1, fmt2]))
    found = _find_formatters(ctx)
    assert found == [fmt1, fmt2]


def test_attach_reaches_all_formatters() -> None:
    """attach_text delivers the attachment to every file formatter."""
    fmt1 = _make_formatter()
    fmt2 = _make_formatter()
    ctx = SimpleNamespace(_runner=SimpleNamespace(formatters=[fmt1, fmt2]))
    attach_text(ctx, "hello", "note.txt")
    assert len(fmt1._attachment_buffer) == 1
    assert len(fmt2._attachment_buffer) == 1


def test_log_reaches_all_formatters() -> None:
    """log delivers the message to every file formatter."""
    fmt1 = _make_formatter()
    fmt2 = _make_formatter()
    ctx = SimpleNamespace(_runner=SimpleNamespace(formatters=[fmt1, fmt2]))
    attach_log(ctx, "msg")
    assert fmt1._log_buffer == ["msg"]
    assert fmt2._log_buffer == ["msg"]


# ---------------------------------------------------------------------------
# _is_file_formatter
# ---------------------------------------------------------------------------


def test_is_file_formatter_true_for_txt() -> None:
    assert _is_file_formatter(_make_formatter()) is True


def test_is_file_formatter_true_for_pdf() -> None:
    fmt = PDFFormatter(stream_opener=MockStreamOpener("report.pdf"))
    assert _is_file_formatter(fmt) is True


def test_is_file_formatter_false_for_plain_object() -> None:
    assert _is_file_formatter(SimpleNamespace()) is False


def test_is_file_formatter_false_for_none() -> None:
    assert _is_file_formatter(None) is False


# ---------------------------------------------------------------------------
# _guess_mime_type
# ---------------------------------------------------------------------------


def test_guess_mime_type_png() -> None:
    assert _guess_mime_type("screenshot.png") == "image/png"


def test_guess_mime_type_jpg() -> None:
    assert _guess_mime_type("photo.jpg") == "image/jpeg"


def test_guess_mime_type_txt() -> None:
    assert _guess_mime_type("log.txt") == "text/plain"


def test_guess_mime_type_json() -> None:
    assert _guess_mime_type("data.json") == "application/json"


def test_guess_mime_type_unknown() -> None:
    assert _guess_mime_type("file.unknownext") == "application/octet-stream"


def test_guess_mime_type_no_extension() -> None:
    assert _guess_mime_type("README") == "application/octet-stream"


# ---------------------------------------------------------------------------
# _bytes_to_base64
# ---------------------------------------------------------------------------


def test_bytes_to_base64_simple() -> None:
    assert _bytes_to_base64(b"hello") == "aGVsbG8="


def test_bytes_to_base64_empty() -> None:
    assert _bytes_to_base64(b"") == ""


def test_bytes_to_base64_binary() -> None:
    data = bytes(range(256))
    result = _bytes_to_base64(data)
    import base64

    assert result == base64.b64encode(data).decode("ascii")


# ---------------------------------------------------------------------------
# _make_attachment_from_bytes
# ---------------------------------------------------------------------------


def test_make_attachment_from_bytes_basic() -> None:
    att = _make_attachment_from_bytes(b"hello", "test.txt")
    assert att.name == "test.txt"
    assert att.mime_type == "text/plain"
    assert att.data_base64 == "aGVsbG8="
    assert att.text is None


def test_make_attachment_from_bytes_png() -> None:
    att = _make_attachment_from_bytes(b"\x89PNG\r\n\x1a\n", "screenshot.png")
    assert att.name == "screenshot.png"
    assert att.mime_type == "image/png"
    assert att.is_image is True


def test_make_attachment_from_bytes_with_mime_override() -> None:
    att = _make_attachment_from_bytes(b"data", "file.bin", "application/custom")
    assert att.mime_type == "application/custom"


def test_make_attachment_from_bytes_empty() -> None:
    att = _make_attachment_from_bytes(b"", "empty.txt")
    assert att.data_base64 == ""


def test_make_attachment_from_bytes_unknown_ext() -> None:
    att = _make_attachment_from_bytes(b"data", "file.unknownext")
    assert att.mime_type == "application/octet-stream"


# ---------------------------------------------------------------------------
# _make_attachment_from_text
# ---------------------------------------------------------------------------


def test_make_attachment_from_text_basic() -> None:
    att = _make_attachment_from_text("hello world", "log.txt")
    assert att.name == "log.txt"
    assert att.mime_type == "text/plain"
    assert att.text == "hello world"
    assert att.data_base64 == ""
    assert att.is_text is True


def test_make_attachment_from_text_custom_mime() -> None:
    att = _make_attachment_from_text("{}", "data.json", "application/json")
    assert att.mime_type == "application/json"
    assert att.text == "{}"


def test_make_attachment_from_text_empty() -> None:
    att = _make_attachment_from_text("", "empty.txt")
    assert att.text == ""


def test_make_attachment_from_text_multiline() -> None:
    text = "line1\nline2\nline3"
    att = _make_attachment_from_text(text, "log.txt")
    assert att.text == text


# ---------------------------------------------------------------------------
# _make_attachment_from_file
# ---------------------------------------------------------------------------


def test_make_attachment_from_file_text(tmp_path: Path) -> None:
    p = tmp_path / "log.txt"
    p.write_text("hello file", encoding="utf-8")
    att = _make_attachment_from_file(p)
    assert att.name == "log.txt"
    assert att.mime_type == "text/plain"
    assert att.data_base64 == _bytes_to_base64(b"hello file")


def test_make_attachment_from_file_binary(tmp_path: Path) -> None:
    p = tmp_path / "data.bin"
    p.write_bytes(b"\x00\x01\x02\x03")
    att = _make_attachment_from_file(p)
    assert att.name == "data.bin"
    assert att.mime_type == "application/octet-stream"
    assert att.data_base64 == _bytes_to_base64(b"\x00\x01\x02\x03")


def test_make_attachment_from_file_with_name_override(tmp_path: Path) -> None:
    p = tmp_path / "original.txt"
    p.write_text("content", encoding="utf-8")
    att = _make_attachment_from_file(p, name="custom.txt")
    assert att.name == "custom.txt"


def test_make_attachment_from_file_png(tmp_path: Path) -> None:
    p = tmp_path / "screenshot.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n")
    att = _make_attachment_from_file(p)
    assert att.name == "screenshot.png"
    assert att.mime_type == "image/png"
    assert att.is_image is True


# ---------------------------------------------------------------------------
# Attachment buffer in BaseFileFormatter
# ---------------------------------------------------------------------------


def test_attach_adds_to_buffer() -> None:
    fmt = _make_formatter()
    att = Attachment(name="test.txt", mime_type="text/plain", text="hello")
    fmt.attach(att)
    assert len(fmt._attachment_buffer) == 1
    assert fmt._attachment_buffer[0] is att


def test_log_adds_to_buffer() -> None:
    fmt = _make_formatter()
    fmt.log("log message")
    assert len(fmt._log_buffer) == 1
    assert fmt._log_buffer[0] == "log message"


def test_attach_multiple() -> None:
    fmt = _make_formatter()
    fmt.attach(Attachment(name="a.txt", text="a"))
    fmt.attach(Attachment(name="b.txt", text="b"))
    assert len(fmt._attachment_buffer) == 2


def test_log_multiple() -> None:
    fmt = _make_formatter()
    fmt.log("msg1")
    fmt.log("msg2")
    fmt.log("msg3")
    assert len(fmt._log_buffer) == 3


def test_attach_and_log_combined() -> None:
    fmt = _make_formatter()
    fmt.attach(Attachment(name="screenshot.png", mime_type="image/png"))
    fmt.log("captured screenshot")
    assert len(fmt._attachment_buffer) == 1
    assert len(fmt._log_buffer) == 1


def test_result_flushes_buffers_to_step() -> None:
    fmt = _make_formatter()
    fmt.feature(
        SimpleNamespace(
            name="F1",
            tags=[],
            location="f:1",
            description=None,
        )
    )
    fmt.scenario(
        SimpleNamespace(
            name="S1",
            tags=[],
            location="f:5",
            feature=SimpleNamespace(name="F1", tags=[], location=""),
            is_outline=False,
            rule=None,
            description=None,
        )
    )
    fmt.step(
        SimpleNamespace(
            keyword="Given ",
            name="step",
            status="passed",
            location="f:10",
            duration=0.01,
            text=None,
            error=None,
            exception=None,
            error_message=None,
        )
    )
    att = Attachment(name="log.txt", text="hello")
    fmt.attach(att)
    fmt.log("log line")
    fmt.result(
        SimpleNamespace(
            keyword="Given ",
            name="step",
            status="passed",
            location="f:10",
            duration=0.01,
            text=None,
            error=None,
            exception=None,
            error_message=None,
        )
    )
    assert len(fmt._attachment_buffer) == 0
    assert len(fmt._log_buffer) == 0
    # After result, step is finalized — check via collector's scenario
    scenario = fmt._collector._current_scenario
    assert scenario is not None
    assert len(scenario.steps) == 1
    assert len(scenario.steps[0].attachments) == 1
    assert scenario.steps[0].attachments[0].name == "log.txt"
    assert len(scenario.steps[0].logs) == 1
    assert scenario.steps[0].logs[0] == "log line"


def test_result_clears_buffers_even_without_step() -> None:
    fmt = _make_formatter()
    fmt.attach(Attachment(name="orphan.txt", text="orphan"))
    fmt.log("orphan log")
    fmt.result(
        SimpleNamespace(
            keyword="Given ",
            name="step",
            status="passed",
            location="f:10",
            duration=0.01,
            text=None,
            error=None,
            exception=None,
            error_message=None,
        )
    )
    assert len(fmt._attachment_buffer) == 0
    assert len(fmt._log_buffer) == 0


def test_buffers_empty_after_init() -> None:
    fmt = _make_formatter()
    assert fmt._attachment_buffer == []
    assert fmt._log_buffer == []


def test_attach_then_result_then_attach_again() -> None:
    fmt = _make_formatter()
    fmt.feature(
        SimpleNamespace(
            name="F1",
            tags=[],
            location="f:1",
            description=None,
        )
    )
    fmt.scenario(
        SimpleNamespace(
            name="S1",
            tags=[],
            location="f:5",
            feature=SimpleNamespace(name="F1", tags=[], location=""),
            is_outline=False,
            rule=None,
            description=None,
        )
    )
    # First step
    fmt.step(
        SimpleNamespace(
            keyword="Given ",
            name="step1",
            status="passed",
            location="f:10",
            duration=0.01,
            text=None,
            error=None,
            exception=None,
            error_message=None,
        )
    )
    fmt.attach(Attachment(name="att1.txt", text="a1"))
    fmt.result(
        SimpleNamespace(
            keyword="Given ",
            name="step1",
            status="passed",
            location="f:10",
            duration=0.01,
            text=None,
            error=None,
            exception=None,
            error_message=None,
        )
    )
    # Second step
    fmt.step(
        SimpleNamespace(
            keyword="When ",
            name="step2",
            status="passed",
            location="f:15",
            duration=0.01,
            text=None,
            error=None,
            exception=None,
            error_message=None,
        )
    )
    fmt.attach(Attachment(name="att2.txt", text="a2"))
    fmt.log("log2")
    fmt.result(
        SimpleNamespace(
            keyword="When ",
            name="step2",
            status="passed",
            location="f:15",
            duration=0.01,
            text=None,
            error=None,
            exception=None,
            error_message=None,
        )
    )
    scenario = fmt._collector._current_scenario
    assert scenario is not None
    assert len(scenario.steps) == 2
    assert len(scenario.steps[0].attachments) == 1
    assert scenario.steps[0].attachments[0].name == "att1.txt"
    assert len(scenario.steps[0].logs) == 0
    assert len(scenario.steps[1].attachments) == 1
    assert scenario.steps[1].attachments[0].name == "att2.txt"
    assert len(scenario.steps[1].logs) == 1
    assert scenario.steps[1].logs[0] == "log2"


# ---------------------------------------------------------------------------
# Integration: _find_formatter + attach
# ---------------------------------------------------------------------------


def test_find_formatter_then_attach() -> None:
    fmt = _make_formatter()
    ctx = _mock_context(fmt)
    found = _find_formatter(ctx)
    assert found is fmt
    att = _make_attachment_from_text("hello", "test.txt")
    found.attach(att)
    assert len(fmt._attachment_buffer) == 1
    assert fmt._attachment_buffer[0].name == "test.txt"


def test_find_formatter_then_log() -> None:
    fmt = _make_formatter()
    ctx = _mock_context(fmt)
    found = _find_formatter(ctx)
    assert found is fmt
    found.log("test log")
    assert len(fmt._log_buffer) == 1
    assert fmt._log_buffer[0] == "test log"


# ---------------------------------------------------------------------------
# _check_size
# ---------------------------------------------------------------------------


def test_check_size_within_limit() -> None:
    assert _check_size(b"hello", 1) == b"hello"


def test_check_size_exceeds_limit() -> None:
    data = b"x" * 2048
    assert _check_size(data, 1) == b""


def test_check_size_zero_limit_allows_all() -> None:
    data = b"x" * 10000
    assert _check_size(data, 0) == data


def test_check_size_exact_boundary() -> None:
    data = b"x" * 1024
    assert _check_size(data, 1) == data


def test_check_size_one_byte_over() -> None:
    data = b"x" * 1025
    assert _check_size(data, 1) == b""


# ---------------------------------------------------------------------------
# _get_max_size_kb
# ---------------------------------------------------------------------------


def test_get_max_size_kb_from_formatter() -> None:
    fmt = _make_formatter()
    assert _get_max_size_kb(fmt) == fmt._options.attachment_max_size_kb


def test_get_max_size_kb_no_options() -> None:
    obj = SimpleNamespace()
    assert _get_max_size_kb(obj) == 512


def test_get_max_size_kb_no_options_attr() -> None:
    obj = SimpleNamespace(_options=None)
    assert _get_max_size_kb(obj) == 512


# ---------------------------------------------------------------------------
# Source detection
# ---------------------------------------------------------------------------


def test_is_selenium_driver_true() -> None:
    obj = SimpleNamespace(screenshot_as_png=b"", save_screenshot=lambda path: None)
    assert _is_selenium_driver(obj) is True


def test_is_selenium_driver_false() -> None:
    assert _is_selenium_driver(SimpleNamespace()) is False


def test_is_playwright_page_true() -> None:
    obj = SimpleNamespace(screenshot=lambda: b"")
    assert _is_playwright_page(obj) is True


def test_is_playwright_page_false() -> None:
    assert _is_playwright_page(SimpleNamespace()) is False


def test_is_playwright_page_false_for_selenium() -> None:
    obj = SimpleNamespace(screenshot_as_png=b"", save_screenshot=lambda p: None)
    assert _is_playwright_page(obj) is False


def test_is_pil_image_true() -> None:
    obj = SimpleNamespace(save=lambda *a, **kw: None, format="PNG", size=(100, 100))
    assert _is_pil_image(obj) is True


def test_is_pil_image_false() -> None:
    assert _is_pil_image(SimpleNamespace()) is False


# ---------------------------------------------------------------------------
# _capture_screenshot
# ---------------------------------------------------------------------------


def test_capture_screenshot_from_bytes() -> None:
    data = b"\x89PNG\r\n\x1a\n"
    assert _capture_screenshot(data) == data


def test_capture_screenshot_from_path(tmp_path: Path) -> None:
    p = tmp_path / "shot.png"
    p.write_bytes(b"\x89PNG data")
    assert _capture_screenshot(str(p)) == b"\x89PNG data"


def test_capture_screenshot_from_pathlib(tmp_path: Path) -> None:
    p = tmp_path / "shot.png"
    p.write_bytes(b"PNG bytes")
    assert _capture_screenshot(p) == b"PNG bytes"


def test_capture_screenshot_from_selenium() -> None:
    png_data = b"\x89PNG selenium"
    driver = SimpleNamespace(
        screenshot_as_png=png_data,
        save_screenshot=lambda path: None,
    )
    assert _capture_screenshot(driver) == png_data


def test_capture_screenshot_from_playwright() -> None:
    png_data = b"\x89PNG playwright"
    page = SimpleNamespace(screenshot=lambda: png_data)
    assert _capture_screenshot(page) == png_data


def test_capture_screenshot_from_pil() -> None:
    png_data = b"\x89PNG pil image"

    class FakePILImage:
        format = "PNG"
        size = (100, 100)

        def save(self, buf: Any, format: str = "PNG") -> None:
            buf.write(png_data)

    img = FakePILImage()
    assert _capture_screenshot(img) == png_data


def test_capture_screenshot_unsupported_type() -> None:
    with pytest.raises(TypeError, match="Unsupported screenshot source"):
        _capture_screenshot(42)


# ---------------------------------------------------------------------------
# Public API: attach_screenshot
# ---------------------------------------------------------------------------


def test_attach_screenshot_from_bytes() -> None:
    fmt = _make_formatter()
    ctx = _mock_context(fmt)
    png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\x00"
    attach_screenshot(ctx, png)
    assert len(fmt._attachment_buffer) == 1
    att = fmt._attachment_buffer[0]
    assert att.name == "screenshot.png"
    assert att.mime_type == "image/png"
    assert att.is_image is True


def test_attach_screenshot_from_path(tmp_path: Path) -> None:
    fmt = _make_formatter()
    ctx = _mock_context(fmt)
    p = tmp_path / "shot.png"
    p.write_bytes(b"\x89PNG data")
    attach_screenshot(ctx, str(p), name="shot.png")
    assert len(fmt._attachment_buffer) == 1
    assert fmt._attachment_buffer[0].name == "shot.png"


def test_attach_screenshot_custom_name() -> None:
    fmt = _make_formatter()
    ctx = _mock_context(fmt)
    attach_screenshot(ctx, b"\x89PNG", name="failure.png")
    assert fmt._attachment_buffer[0].name == "failure.png"


def test_attach_screenshot_from_selenium() -> None:
    fmt = _make_formatter()
    ctx = _mock_context(fmt)
    driver = SimpleNamespace(
        screenshot_as_png=b"\x89PNG selenium",
        save_screenshot=lambda path: None,
    )
    attach_screenshot(ctx, driver)
    assert len(fmt._attachment_buffer) == 1
    assert fmt._attachment_buffer[0].mime_type == "image/png"


def test_attach_screenshot_from_playwright() -> None:
    fmt = _make_formatter()
    ctx = _mock_context(fmt)
    page = SimpleNamespace(screenshot=lambda: b"\x89PNG playwright")
    attach_screenshot(ctx, page)
    assert len(fmt._attachment_buffer) == 1
    assert fmt._attachment_buffer[0].mime_type == "image/png"


def test_attach_screenshot_from_pil() -> None:
    fmt = _make_formatter()
    ctx = _mock_context(fmt)
    png_data = b"\x89PNG pil"

    class FakePILImage:
        format = "PNG"
        size = (100, 100)

        def save(self, buf: Any, format: str = "PNG") -> None:
            buf.write(png_data)

    attach_screenshot(ctx, FakePILImage())
    assert len(fmt._attachment_buffer) == 1
    assert fmt._attachment_buffer[0].mime_type == "image/png"


def test_attach_screenshot_from_context_driver() -> None:
    fmt = _make_formatter()
    ctx = _mock_context(fmt)
    ctx.driver = SimpleNamespace(
        screenshot_as_png=b"\x89PNG auto",
        save_screenshot=lambda path: None,
    )
    attach_screenshot(ctx)
    assert len(fmt._attachment_buffer) == 1


def test_attach_screenshot_from_context_page() -> None:
    fmt = _make_formatter()
    ctx = _mock_context(fmt)
    ctx.page = SimpleNamespace(screenshot=lambda: b"\x89PNG auto")
    attach_screenshot(ctx)
    assert len(fmt._attachment_buffer) == 1


def test_attach_screenshot_no_source_no_context_attr() -> None:
    fmt = _make_formatter()
    ctx = _mock_context(fmt)
    attach_screenshot(ctx)
    assert len(fmt._attachment_buffer) == 0


def test_attach_screenshot_no_formatter() -> None:
    ctx = SimpleNamespace()
    attach_screenshot(ctx, b"\x89PNG")
    # Should not raise


def test_attach_screenshot_oversized_skipped() -> None:
    fmt = _make_formatter()
    fmt._options.attachment_max_size_kb = 1
    ctx = _mock_context(fmt)
    big_data = b"\x89PNG" + b"x" * 2048
    attach_screenshot(ctx, big_data)
    assert len(fmt._attachment_buffer) == 0


# ---------------------------------------------------------------------------
# Public API: attach_file
# ---------------------------------------------------------------------------


def test_attach_file_basic(tmp_path: Path) -> None:
    fmt = _make_formatter()
    ctx = _mock_context(fmt)
    p = tmp_path / "report.txt"
    p.write_text("hello file", encoding="utf-8")
    attach_file(ctx, str(p))
    assert len(fmt._attachment_buffer) == 1
    att = fmt._attachment_buffer[0]
    assert att.name == "report.txt"
    assert att.data_base64 == _bytes_to_base64(b"hello file")


def test_attach_file_with_name_override(tmp_path: Path) -> None:
    fmt = _make_formatter()
    ctx = _mock_context(fmt)
    p = tmp_path / "original.txt"
    p.write_text("content", encoding="utf-8")
    attach_file(ctx, p, name="custom.txt")
    assert fmt._attachment_buffer[0].name == "custom.txt"


def test_attach_file_binary(tmp_path: Path) -> None:
    fmt = _make_formatter()
    ctx = _mock_context(fmt)
    p = tmp_path / "data.bin"
    p.write_bytes(b"\x00\x01\x02\x03")
    attach_file(ctx, p)
    assert fmt._attachment_buffer[0].mime_type == "application/octet-stream"


def test_attach_file_no_formatter(tmp_path: Path) -> None:
    p = tmp_path / "test.txt"
    p.write_text("data", encoding="utf-8")
    ctx = SimpleNamespace()
    attach_file(ctx, str(p))
    # Should not raise


def test_attach_file_oversized_skipped(tmp_path: Path) -> None:
    fmt = _make_formatter()
    fmt._options.attachment_max_size_kb = 1
    ctx = _mock_context(fmt)
    p = tmp_path / "big.bin"
    p.write_bytes(b"x" * 2048)
    attach_file(ctx, p)
    assert len(fmt._attachment_buffer) == 0


def test_attach_file_missing_path() -> None:
    """attach_file skips missing files without raising."""
    fmt = _make_formatter()
    ctx = _mock_context(fmt)
    attach_file(ctx, "/nonexistent/path/file.txt")
    assert len(fmt._attachment_buffer) == 0


def test_attach_screenshot_file_path_missing() -> None:
    """attach_screenshot skips missing file paths without raising."""
    fmt = _make_formatter()
    ctx = _mock_context(fmt)
    attach_screenshot(ctx, "/nonexistent/path/screenshot.png")
    assert len(fmt._attachment_buffer) == 0


# ---------------------------------------------------------------------------
# Public API: attach_text
# ---------------------------------------------------------------------------


def test_attach_text_basic() -> None:
    fmt = _make_formatter()
    ctx = _mock_context(fmt)
    attach_text(ctx, "hello world")
    assert len(fmt._attachment_buffer) == 1
    att = fmt._attachment_buffer[0]
    assert att.name == "log.txt"
    assert att.text == "hello world"
    assert att.mime_type == "text/plain"


def test_attach_text_custom_name() -> None:
    fmt = _make_formatter()
    ctx = _mock_context(fmt)
    attach_text(ctx, "data", name="output.txt")
    assert fmt._attachment_buffer[0].name == "output.txt"


def test_attach_text_no_formatter() -> None:
    ctx = SimpleNamespace()
    attach_text(ctx, "hello")
    # Should not raise


def test_attach_text_truncated() -> None:
    fmt = _make_formatter()
    fmt._options.attachment_max_size_kb = 1
    ctx = _mock_context(fmt)
    long_text = "x" * 2048
    attach_text(ctx, long_text)
    assert len(fmt._attachment_buffer) == 1
    att = fmt._attachment_buffer[0]
    assert att.text is not None
    assert len(att.text.encode("utf-8")) <= 1024


def test_attach_text_non_positive_max_size_no_truncation() -> None:
    """A non-positive attachment_max_size_kb disables text truncation."""
    fmt = _make_formatter()
    fmt._options.attachment_max_size_kb = -1
    ctx = _mock_context(fmt)
    long_text = "x" * 2048
    attach_text(ctx, long_text)
    att = fmt._attachment_buffer[0]
    assert att.text == long_text


# ---------------------------------------------------------------------------
# Public API: attach_json
# ---------------------------------------------------------------------------


def test_attach_json_basic() -> None:
    fmt = _make_formatter()
    ctx = _mock_context(fmt)
    attach_json(ctx, {"key": "value"})
    assert len(fmt._attachment_buffer) == 1
    att = fmt._attachment_buffer[0]
    assert att.name == "data.json"
    assert att.mime_type == "application/json"
    import json

    parsed = json.loads(att.text or "")
    assert parsed == {"key": "value"}


def test_attach_json_list() -> None:
    fmt = _make_formatter()
    ctx = _mock_context(fmt)
    attach_json(ctx, [1, 2, 3])
    att = fmt._attachment_buffer[0]
    import json

    assert json.loads(att.text or "") == [1, 2, 3]


def test_attach_json_custom_name() -> None:
    fmt = _make_formatter()
    ctx = _mock_context(fmt)
    attach_json(ctx, {"a": 1}, name="config.json")
    assert fmt._attachment_buffer[0].name == "config.json"


def test_attach_json_nested() -> None:
    fmt = _make_formatter()
    ctx = _mock_context(fmt)
    data = {"a": {"b": {"c": [1, 2, {"d": "e"}]}}}
    attach_json(ctx, data)
    att = fmt._attachment_buffer[0]
    import json

    assert json.loads(att.text or "") == data


def test_attach_json_no_formatter() -> None:
    ctx = SimpleNamespace()
    attach_json(ctx, {"a": 1})
    # Should not raise


def test_attach_json_truncated() -> None:
    fmt = _make_formatter()
    fmt._options.attachment_max_size_kb = 1
    ctx = _mock_context(fmt)
    big_data = {str(i): i for i in range(500)}
    attach_json(ctx, big_data)
    assert len(fmt._attachment_buffer) == 1
    att = fmt._attachment_buffer[0]
    assert len((att.text or "").encode("utf-8")) <= 1024


def test_attach_json_non_positive_max_size_no_truncation() -> None:
    """A non-positive attachment_max_size_kb disables JSON truncation."""
    fmt = _make_formatter()
    fmt._options.attachment_max_size_kb = 0
    ctx = _mock_context(fmt)
    big_data = {str(i): i for i in range(500)}
    attach_json(ctx, big_data)
    att = fmt._attachment_buffer[0]
    assert att.text is not None
    import json

    assert json.loads(att.text) == big_data


# ---------------------------------------------------------------------------
# Public API: log
# ---------------------------------------------------------------------------


def test_log_public_api() -> None:
    fmt = _make_formatter()
    ctx = _mock_context(fmt)
    attach_log(ctx, "failed here")
    assert len(fmt._log_buffer) == 1
    assert fmt._log_buffer[0] == "failed here"


def test_log_no_formatter() -> None:
    ctx = SimpleNamespace()
    attach_log(ctx, "message")
    # Should not raise


def test_log_multiple_messages() -> None:
    fmt = _make_formatter()
    ctx = _mock_context(fmt)
    attach_log(ctx, "msg1")
    attach_log(ctx, "msg2")
    attach_log(ctx, "msg3")
    assert len(fmt._log_buffer) == 3


# ---------------------------------------------------------------------------
# Package exports
# ---------------------------------------------------------------------------


def test_package_exports_attach_screenshot() -> None:
    import behave_modern_file_report as pkg

    assert hasattr(pkg, "attach_screenshot")


def test_package_exports_attach_file() -> None:
    import behave_modern_file_report as pkg

    assert hasattr(pkg, "attach_file")


def test_package_exports_attach_text() -> None:
    import behave_modern_file_report as pkg

    assert hasattr(pkg, "attach_text")


def test_package_exports_attach_json() -> None:
    import behave_modern_file_report as pkg

    assert hasattr(pkg, "attach_json")


def test_package_exports_log() -> None:
    import behave_modern_file_report as pkg

    assert hasattr(pkg, "log")


def test_package_all_contains_public_api() -> None:
    import behave_modern_file_report as pkg

    assert "attach_screenshot" in pkg.__all__
    assert "attach_file" in pkg.__all__
    assert "attach_text" in pkg.__all__
    assert "attach_json" in pkg.__all__
    assert "log" in pkg.__all__
