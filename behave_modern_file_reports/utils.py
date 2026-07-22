"""Pure utility helpers for behave-modern-file-reports.

Zero external dependencies. These helpers cover status normalization, safe
string conversions, timing, identifier generation, and parsing of
user-supplied configuration values.
"""

from __future__ import annotations

import math
import re
import time
import uuid
from datetime import UTC, datetime

# ---------------------------------------------------------------------------
# Status constants
# ---------------------------------------------------------------------------

STATUS_PASSED = "passed"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"
STATUS_UNDEFINED = "undefined"
STATUS_UNTESTED = "untested"

STATUS_ICONS: dict[str, str] = {
    STATUS_PASSED: "✓",
    STATUS_FAILED: "✗",
    STATUS_SKIPPED: "↷",
    STATUS_UNDEFINED: "?",
    STATUS_UNTESTED: "○",
}

STATUS_LABELS: dict[str, str] = {
    STATUS_PASSED: "PASSED",
    STATUS_FAILED: "FAILED",
    STATUS_SKIPPED: "SKIPPED",
    STATUS_UNDEFINED: "UNDEFINED",
    STATUS_UNTESTED: "UNTESTED",
}

STATUS_COLORS: dict[str, str] = {
    STATUS_PASSED: "#10B981",
    STATUS_FAILED: "#EF4444",
    STATUS_SKIPPED: "#F59E0B",
    STATUS_UNDEFINED: "#9CA3AF",
}


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    """Convert a ``#RRGGBB`` hex color to an RGB triple.

    Args:
        color: A ``#RRGGBB`` or ``RRGGBB`` color string.

    Returns:
        A tuple ``(r, g, b)`` with integer components in the range 0-255.
    """
    text = color.lstrip("#").lower()
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)


_MAX_STR_LENGTH = 500


# ---------------------------------------------------------------------------
# Safe conversions
# ---------------------------------------------------------------------------


def safe_str(value: object | None) -> str:
    """Convert a value to a stripped, truncated string.

    Args:
        value: Any value or ``None``.

    Returns:
        A stripped string representation of ``value``. If the result exceeds
        500 characters it is truncated to 500 and suffixed with ``"..."``.
        ``None`` returns an empty string.

    Examples:
        >>> safe_str(None)
        ''
        >>> safe_str("  hello  ")
        'hello'
        >>> safe_str(42)
        '42'
    """
    if value is None:
        return ""
    text = str(value).strip()
    if len(text) > _MAX_STR_LENGTH:
        return text[:_MAX_STR_LENGTH] + "..."
    return text


def safe_tags(value: object | None) -> list[str]:
    """Normalize tag-like input into a list of strings.

    Args:
        value: ``None``, a comma-separated string, a list of strings, or any
            other type.

    Returns:
        A list of tag strings. ``None`` returns ``[]``. A string is split by
        commas and each part is stripped. A list is copied with each item
        converted to a stripped string. Any other type returns ``[]``.

    Examples:
        >>> safe_tags(None)
        []
        >>> safe_tags("smoke, auth")
        ['smoke', 'auth']
        >>> safe_tags(["a", "b"])
        ['a', 'b']
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------


def monotonic_seconds(start: float) -> float:
    """Return elapsed seconds since ``start`` using a high-resolution monotonic clock.

    Args:
        start: A ``time.perf_counter()`` reference value.

    Returns:
        Elapsed seconds as a float.
    """
    return time.perf_counter() - start


def now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string.

    Returns:
        An ISO 8601 formatted timestamp with timezone information.
    """
    return datetime.now(UTC).isoformat()


def format_duration(
    seconds: float,
    precision: int = 3,
    zero_label: str = "0s",
) -> str:
    """Format a duration in seconds as a human-readable string.

    Args:
        seconds: Duration in seconds. Must be non-negative.
        precision: Decimal places for durations of one second or more.
        zero_label: Label used for durations smaller than one millisecond.

    Returns:
        A string like ``"1.234s"``, ``"12ms"`` or *zero_label*. Returns ``"N/A"``
        for negative, NaN, or infinite values.

    Examples:
        >>> format_duration(0)
        '0s'
        >>> format_duration(0.012)
        '12ms'
        >>> format_duration(1.234)
        '1.234s'
    """
    if seconds < 0 or math.isnan(seconds) or math.isinf(seconds):
        return "N/A"
    if seconds < 0.001:
        return zero_label
    if seconds < 1.0:
        return f"{int(seconds * 1000)}ms"
    return f"{seconds:.{precision}f}s"


# ---------------------------------------------------------------------------
# Status normalization
# ---------------------------------------------------------------------------


def normalize_status(behave_status: str | None) -> str:
    """Map a Behave status string to a canonical status constant.

    Behave's ``Status`` enum includes values beyond the basic four:
    ``xfailed`` (expected failure that failed) and ``xpassed`` (expected failure
    that passed) are treated as ``passed``; ``error``, ``hook_error``, and
    ``cleanup_error`` are treated as ``failed``; ``pending`` is treated as
    ``undefined``.

    Args:
        behave_status: A status string from Behave (e.g. ``"passed"``).

    Returns:
        One of ``STATUS_PASSED``, ``STATUS_FAILED``, ``STATUS_SKIPPED``,
        ``STATUS_UNDEFINED``, or ``STATUS_UNTESTED`` for unrecognized values.

    Examples:
        >>> normalize_status("passed")
        'passed'
        >>> normalize_status("xfailed")
        'passed'
        >>> normalize_status("error")
        'failed'
        >>> normalize_status("pending")
        'undefined'
    """
    if behave_status is None:
        return STATUS_UNTESTED
    status = behave_status.lower().strip()
    if status in (STATUS_PASSED, "xfailed", "xpassed"):
        return STATUS_PASSED
    if status in (STATUS_FAILED, "error", "hook_error", "cleanup_error"):
        return STATUS_FAILED
    if status == STATUS_SKIPPED:
        return STATUS_SKIPPED
    if status in (STATUS_UNDEFINED, "pending"):
        return STATUS_UNDEFINED
    return STATUS_UNTESTED


# ---------------------------------------------------------------------------
# Identifiers
# ---------------------------------------------------------------------------


def generate_id(prefix: str = "run") -> str:
    """Generate a unique identifier with a prefix.

    Args:
        prefix: A prefix prepended to the hex identifier.

    Returns:
        A string like ``"run_a1b2c3d4e5f6"``.
    """
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# Configuration parsing
# ---------------------------------------------------------------------------


def parse_bool(raw: str | bool | None) -> bool:
    """Parse a boolean value from a string.

    Args:
        raw: One of ``"true"``, ``"1"``, ``"yes"``, ``"false"``, ``"0``,
            ``"no"`` (case-insensitive), or a bool.

    Returns:
        ``True`` for truthy values, ``False`` otherwise.

    Examples:
        >>> parse_bool("true")
        True
        >>> parse_bool("0")
        False
    """
    if isinstance(raw, bool):
        return raw
    if raw is None:
        return False
    value = str(raw).lower().strip()
    return value in ("true", "1", "yes", "on")


def parse_int(raw: str | int | None, default: int) -> int:
    """Parse an integer from user input.

    Args:
        raw: A string or integer value, or ``None``.
        default: Value returned when ``raw`` is ``None`` or empty.

    Returns:
        An integer. Raises ``ValueError`` when ``raw`` is provided but not
        a valid integer.
    """
    if raw is None:
        return default
    if isinstance(raw, int):
        return raw
    text = str(raw).strip()
    if text == "":
        return default
    try:
        return int(text)
    except ValueError as exc:
        raise ValueError(f"Invalid integer value: {raw!r}") from exc


def parse_color(raw: str | None, default: str = "#2563EB") -> str:
    """Parse and normalize a hex color string.

    Args:
        raw: A hex color such as ``"#1E90FF"`` or ``"1E90FF"``.
        default: Value returned when ``raw`` is ``None`` or empty.

    Returns:
        A lowercased ``#RRGGBB`` color. Raises ``ValueError`` when ``raw`` is
        provided but not a valid color.
    """
    if raw is None:
        return default
    text = str(raw).strip()
    if text == "":
        return default
    if not text.startswith("#"):
        text = f"#{text}"
    match = re.fullmatch(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$", text)
    if not match:
        raise ValueError(f"Invalid color value: {raw!r}")
    hex_value = match.group(1)
    if len(hex_value) == 3:
        hex_value = "".join(c * 2 for c in hex_value)
    return f"#{hex_value.lower()}"


def parse_pdf_engine(raw: str | None, default: str = "weasyprint") -> str:
    """Parse the PDF engine option.

    Args:
        raw: ``"weasyprint"`` or ``"reportlab`` (case-insensitive).
        default: Value returned when ``raw`` is ``None`` or empty.

    Returns:
        A normalized engine name. Raises ``ValueError`` when ``raw`` is
        provided but not a valid engine.
    """
    if raw is None:
        return default
    text = str(raw).lower().strip()
    if text == "":
        return default
    if text in ("weasyprint", "reportlab"):
        return text
    raise ValueError(f"Invalid PDF engine: {raw!r}")


def parse_delimiter(raw: str | None, default: str = ",") -> str:
    """Parse a delimiter name into the actual delimiter character.

    Args:
        raw: One of ``"comma"``, ``"semicolon"``, ``"tab`` (case-insensitive).
        default: Value returned when ``raw`` is ``None`` or empty.

    Returns:
        The delimiter character. Raises ``ValueError`` when ``raw`` is provided
        but not a valid delimiter name.
    """
    if raw is None:
        return default
    text = str(raw).lower().strip()
    if text == "":
        return default
    mapping = {
        "comma": ",",
        "semicolon": ";",
        "tab": "\t",
    }
    if text in mapping:
        return mapping[text]
    raise ValueError(f"Invalid delimiter: {raw!r}")


def parse_columns(raw: str | None) -> list[str]:
    """Parse a comma-separated list of column names.

    Args:
        raw: A comma-separated string or ``None``.

    Returns:
        A list of stripped, non-empty column names. Returns ``[]`` when
        ``raw`` is ``None`` or empty.
    """
    if raw is None:
        return []
    text = str(raw).strip()
    if text == "":
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


__all__ = [
    "STATUS_FAILED",
    "STATUS_PASSED",
    "STATUS_SKIPPED",
    "STATUS_UNDEFINED",
    "STATUS_UNTESTED",
    "format_duration",
    "generate_id",
    "monotonic_seconds",
    "normalize_status",
    "now_iso",
    "parse_bool",
    "parse_color",
    "parse_columns",
    "parse_delimiter",
    "parse_int",
    "parse_pdf_engine",
    "safe_str",
    "safe_tags",
]
