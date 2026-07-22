"""Tests for behave_modern_file_reports.utils."""

from __future__ import annotations

import time
from datetime import UTC, datetime

import pytest

from behave_modern_file_reports import utils
from behave_modern_file_reports.utils import (
    STATUS_FAILED,
    STATUS_PASSED,
    STATUS_SKIPPED,
    STATUS_UNDEFINED,
    STATUS_UNTESTED,
    format_duration,
    generate_id,
    monotonic_seconds,
    normalize_status,
    now_iso,
    parse_bool,
    parse_color,
    parse_columns,
    parse_delimiter,
    parse_int,
    parse_pdf_engine,
    safe_str,
    safe_tags,
)


def test_safe_str_none() -> None:
    """safe_str returns an empty string for None."""
    assert safe_str(None) == ""


def test_safe_str_strips() -> None:
    """safe_str strips whitespace."""
    assert safe_str("  hello  ") == "hello"


def test_safe_str_converts() -> None:
    """safe_str converts non-string values."""
    assert safe_str(42) == "42"


def test_safe_str_truncates() -> None:
    """safe_str truncates long strings to 500 characters."""
    long_value = "x" * 600
    result = safe_str(long_value)
    assert len(result) == 503  # 500 chars + "..."
    assert result.endswith("...")


def test_safe_tags_none() -> None:
    """safe_tags returns an empty list for None."""
    assert safe_tags(None) == []


def test_safe_tags_string() -> None:
    """safe_tags splits a comma-separated string."""
    assert safe_tags("smoke, auth ") == ["smoke", "auth"]


def test_safe_tags_list() -> None:
    """safe_tags normalizes a list of values."""
    assert safe_tags(["a", " b ", 1]) == ["a", "b", "1"]


def test_safe_tags_other() -> None:
    """safe_tags returns an empty list for unsupported types."""
    assert safe_tags({"a": 1}) == []


def test_monotonic_seconds() -> None:
    """monotonic_seconds returns a positive elapsed time."""
    start = time.perf_counter()
    time.sleep(0.001)
    elapsed = monotonic_seconds(start)
    assert elapsed > 0.0


def test_now_iso() -> None:
    """now_iso returns a UTC ISO 8601 timestamp."""
    result = now_iso()
    parsed = datetime.fromisoformat(result)
    assert parsed.tzinfo == UTC


def test_format_duration_zero() -> None:
    """format_duration returns 0s for zero."""
    assert format_duration(0.0) == "0s"


def test_format_duration_milliseconds() -> None:
    """format_duration returns milliseconds for sub-second durations."""
    assert format_duration(0.012) == "12ms"


def test_format_duration_seconds() -> None:
    """format_duration returns seconds for durations >= 1s."""
    assert format_duration(1.234) == "1.234s"


def test_format_duration_invalid() -> None:
    """format_duration returns N/A for invalid durations."""
    assert format_duration(-1.0) == "N/A"
    assert format_duration(float("nan")) == "N/A"
    assert format_duration(float("inf")) == "N/A"


def test_format_duration_precision() -> None:
    """format_duration respects the precision parameter."""
    assert format_duration(1.234, precision=2) == "1.23s"
    assert format_duration(1.234, precision=1) == "1.2s"


def test_format_duration_zero_label() -> None:
    """format_duration uses the configured zero label."""
    assert format_duration(0.0, zero_label="0ms") == "0ms"


def test_normalize_status_passed() -> None:
    """normalize_status maps passed, xfailed and xpassed to passed."""
    assert normalize_status("passed") == STATUS_PASSED
    assert normalize_status("xfailed") == STATUS_PASSED
    assert normalize_status("xpassed") == STATUS_PASSED


def test_normalize_status_failed() -> None:
    """normalize_status maps failed variants to failed."""
    assert normalize_status("failed") == STATUS_FAILED
    assert normalize_status("error") == STATUS_FAILED
    assert normalize_status("hook_error") == STATUS_FAILED
    assert normalize_status("cleanup_error") == STATUS_FAILED


def test_normalize_status_skipped() -> None:
    """normalize_status maps skipped to skipped."""
    assert normalize_status("skipped") == STATUS_SKIPPED


def test_normalize_status_undefined() -> None:
    """normalize_status maps undefined and pending to undefined."""
    assert normalize_status("undefined") == STATUS_UNDEFINED
    assert normalize_status("pending") == STATUS_UNDEFINED


def test_normalize_status_untested() -> None:
    """normalize_status returns untested for None and unknown values."""
    assert normalize_status(None) == STATUS_UNTESTED
    assert normalize_status("unknown") == STATUS_UNTESTED


def test_generate_id() -> None:
    """generate_id returns a prefixed identifier."""
    result = generate_id()
    assert result.startswith("run_")
    assert len(result) == 16  # "run_" + 12 hex chars


def test_generate_id_custom_prefix() -> None:
    """generate_id uses the provided prefix."""
    result = generate_id("feat")
    assert result.startswith("feat_")


def test_generate_id_unique() -> None:
    """generate_id produces unique values."""
    result1 = generate_id()
    result2 = generate_id()
    assert result1 != result2


def test_parse_bool_true_values() -> None:
    """parse_bool returns True for truthy strings."""
    assert parse_bool("true") is True
    assert parse_bool("True") is True
    assert parse_bool("1") is True
    assert parse_bool("yes") is True
    assert parse_bool("on") is True
    assert parse_bool(True) is True


def test_parse_bool_false_values() -> None:
    """parse_bool returns False for falsy strings and None."""
    assert parse_bool("false") is False
    assert parse_bool("False") is False
    assert parse_bool("0") is False
    assert parse_bool("no") is False
    assert parse_bool("off") is False
    assert parse_bool(None) is False
    assert parse_bool(False) is False
    assert parse_bool("anything else") is False


def test_parse_int() -> None:
    """parse_int returns an integer or the default."""
    assert parse_int("42", 0) == 42
    assert parse_int(7, 0) == 7
    assert parse_int(None, 10) == 10
    assert parse_int("", 10) == 10


def test_parse_int_invalid() -> None:
    """parse_int raises ValueError for invalid input."""
    with pytest.raises(ValueError):
        parse_int("abc", 0)


def test_parse_color() -> None:
    """parse_color normalizes hex colors."""
    assert parse_color("#1E90FF") == "#1e90ff"
    assert parse_color("1E90FF") == "#1e90ff"
    assert parse_color("#abc") == "#aabbcc"
    assert parse_color(None, "#000000") == "#000000"
    assert parse_color("", "#000000") == "#000000"


def test_parse_color_invalid() -> None:
    """parse_color raises ValueError for invalid colors."""
    with pytest.raises(ValueError):
        parse_color("not-a-color")
    with pytest.raises(ValueError):
        parse_color("#GGGGGG")


def test_parse_pdf_engine() -> None:
    """parse_pdf_engine normalizes and validates the engine."""
    assert parse_pdf_engine("weasyprint") == "weasyprint"
    assert parse_pdf_engine("ReportLab") == "reportlab"
    assert parse_pdf_engine(None) == "weasyprint"
    assert parse_pdf_engine("", "reportlab") == "reportlab"


def test_parse_pdf_engine_invalid() -> None:
    """parse_pdf_engine raises ValueError for invalid engines."""
    with pytest.raises(ValueError):
        parse_pdf_engine("wkhtmltopdf")


def test_parse_delimiter() -> None:
    """parse_delimiter maps names to characters."""
    assert parse_delimiter("comma") == ","
    assert parse_delimiter("semicolon") == ";"
    assert parse_delimiter("tab") == "\t"
    assert parse_delimiter(None) == ","
    assert parse_delimiter("", ";") == ";"


def test_parse_delimiter_invalid() -> None:
    """parse_delimiter raises ValueError for unknown delimiters."""
    with pytest.raises(ValueError):
        parse_delimiter("pipe")


def test_parse_columns() -> None:
    """parse_columns splits and trims a comma-separated string."""
    assert parse_columns("a, b, c") == ["a", "b", "c"]
    assert parse_columns(None) == []
    assert parse_columns("  ") == []


__all__ = ["utils"]
