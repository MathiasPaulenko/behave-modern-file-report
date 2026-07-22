"""Attachment helpers for Behave reports.

Provides internal helpers (``_find_formatter``, ``_make_attachment_from_*``)
plus the **public API** for use from ``environment.py``::

    from behave_modern_file_reports import attach_screenshot, log

    def after_step(context, step):
        if step.status == "failed":
            attach_screenshot(context)
            log(context, "failed here")

Supported sources for ``attach_screenshot``:
- Raw ``bytes`` (PNG data)
- File path (``str`` or ``pathlib.Path``)
- Selenium ``WebDriver`` (calls ``screenshot_as_png``)
- Playwright ``Page`` (calls ``screenshot``)
- PIL ``Image`` (saved to PNG bytes)
"""

from __future__ import annotations

import base64
import io
import json
import mimetypes
from pathlib import Path
from typing import Any

from behave_modern_file_reports.models import Attachment


def _find_formatter(context: Any) -> Any:
    """Find the active ``BaseFileFormatter`` from a Behave ``context``.

    Behave stores active formatters in ``context._runner.formatters``
    (a dict of name → formatter).  This helper scans the dict and
    returns the first ``BaseFileFormatter`` instance found.

    Args:
        context: A Behave ``Context`` object.

    Returns:
        The first ``BaseFileFormatter`` found, or ``None``.
    """
    runner = getattr(context, "_runner", None)
    if runner is None:
        return None
    formatters = getattr(runner, "formatters", None)
    if formatters is None:
        return None
    if isinstance(formatters, dict):
        for fmt in formatters.values():
            if _is_file_formatter(fmt):
                return fmt
    elif isinstance(formatters, list):
        for fmt in formatters:
            if _is_file_formatter(fmt):
                return fmt
    return None


def _is_file_formatter(obj: Any) -> bool:
    """Return ``True`` if *obj* looks like a ``BaseFileFormatter``."""
    return hasattr(obj, "attach") and hasattr(obj, "log") and hasattr(obj, "_collector")


def _guess_mime_type(name: str) -> str:
    """Guess a MIME type from a filename.

    Args:
        name: The filename to guess from.

    Returns:
        A MIME type string (defaults to ``application/octet-stream``).
    """
    guessed, _ = mimetypes.guess_type(name)
    return guessed or "application/octet-stream"


def _bytes_to_base64(data: bytes) -> str:
    """Encode raw bytes to a base64 string.

    Args:
        data: The raw bytes to encode.

    Returns:
        A base64-encoded string.
    """
    return base64.b64encode(data).decode("ascii")


def _make_attachment_from_bytes(
    data: bytes,
    name: str,
    mime_type: str | None = None,
) -> Attachment:
    """Build an :class:`Attachment` from raw bytes.

    Args:
        data: The raw attachment content.
        name: The attachment name (e.g. ``"screenshot.png"``).
        mime_type: Optional MIME type override.

    Returns:
        An :class:`Attachment` with base64-encoded data.
    """
    return Attachment(
        name=name,
        mime_type=mime_type or _guess_mime_type(name),
        data_base64=_bytes_to_base64(data),
    )


def _make_attachment_from_text(
    text: str,
    name: str,
    mime_type: str = "text/plain",
) -> Attachment:
    """Build an :class:`Attachment` from a text string.

    Args:
        text: The text content.
        name: The attachment name.
        mime_type: The MIME type (defaults to ``text/plain``).

    Returns:
        An :class:`Attachment` with text content.
    """
    return Attachment(
        name=name,
        mime_type=mime_type,
        text=text,
    )


def _make_attachment_from_file(path: str | Path, name: str | None = None) -> Attachment:
    """Build an :class:`Attachment` from a file on disk.

    Args:
        path: Path to the file.
        name: Optional name override (defaults to the filename).

    Returns:
        An :class:`Attachment` with base64-encoded data.
    """
    p = Path(path)
    file_name = name or p.name
    data = p.read_bytes()
    return _make_attachment_from_bytes(data, file_name)


# ---------------------------------------------------------------------------
# Size enforcement
# ---------------------------------------------------------------------------


def _check_size(data: bytes, max_size_kb: int) -> bytes:
    """Return *data* if within the size limit, otherwise empty bytes.

    Args:
        data: The raw attachment data.
        max_size_kb: Maximum allowed size in kilobytes.

    Returns:
        *data* if within limit, otherwise ``b""``.
    """
    if max_size_kb <= 0:
        return data
    if len(data) > max_size_kb * 1024:
        return b""
    return data


def _get_max_size_kb(formatter: Any) -> int:
    """Extract ``attachment_max_size_kb`` from a formatter's options."""
    options = getattr(formatter, "_options", None)
    if options is None:
        return 512
    return getattr(options, "attachment_max_size_kb", 512)


# ---------------------------------------------------------------------------
# Source detection for screenshots
# ---------------------------------------------------------------------------


def _is_selenium_driver(obj: Any) -> bool:
    """Return ``True`` if *obj* looks like a Selenium ``WebDriver``."""
    return hasattr(obj, "screenshot_as_png") and hasattr(obj, "save_screenshot")


def _is_playwright_page(obj: Any) -> bool:
    """Return ``True`` if *obj* looks like a Playwright ``Page``."""
    return hasattr(obj, "screenshot") and not hasattr(obj, "screenshot_as_png")


def _is_pil_image(obj: Any) -> bool:
    """Return ``True`` if *obj* looks like a PIL ``Image``."""
    return hasattr(obj, "save") and hasattr(obj, "format") and hasattr(obj, "size")


def _capture_screenshot(source: Any) -> bytes:
    """Capture PNG bytes from various screenshot sources.

    Args:
        source: One of bytes, str/Path (file path), Selenium driver,
            Playwright page, or PIL Image.

    Returns:
        PNG image data as bytes.
    """
    if isinstance(source, bytes):
        return source

    if isinstance(source, str | Path):
        return Path(source).read_bytes()

    if _is_selenium_driver(source):
        return source.screenshot_as_png  # type: ignore[no-any-return]

    if _is_playwright_page(source):
        return source.screenshot()  # type: ignore[no-any-return]

    if _is_pil_image(source):
        buf = io.BytesIO()
        source.save(buf, format="PNG")
        return buf.getvalue()

    raise TypeError(
        f"Unsupported screenshot source type: {type(source).__name__}",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def attach_screenshot(
    context: Any,
    source: Any | None = None,
    name: str = "screenshot.png",
) -> None:
    """Attach a screenshot to the current step.

    Args:
        context: Behave ``context`` object.
        source: Screenshot source. Supports:
            - ``bytes``: raw PNG data.
            - ``str`` / ``Path``: path to a PNG file.
            - Selenium ``WebDriver``: uses ``screenshot_as_png``.
            - Playwright ``Page``: uses ``screenshot()``.
            - PIL ``Image``: saved to PNG bytes.
            If ``None``, attempts to use ``context.driver`` or ``context.page``.
        name: Attachment name (defaults to ``"screenshot.png"``).
    """
    fmt = _find_formatter(context)
    if fmt is None:
        return

    if source is None:
        source = getattr(context, "driver", None) or getattr(context, "page", None)
    if source is None:
        return

    data = _capture_screenshot(source)
    max_kb = _get_max_size_kb(fmt)
    data = _check_size(data, max_kb)
    if not data:
        return

    att = _make_attachment_from_bytes(data, name, "image/png")
    fmt.attach(att)


def attach_file(
    context: Any,
    path: str | Path,
    name: str | None = None,
) -> None:
    """Attach a file to the current step.

    Args:
        context: Behave ``context`` object.
        path: Path to the file to attach.
        name: Optional attachment name override.
    """
    fmt = _find_formatter(context)
    if fmt is None:
        return

    p = Path(path)
    file_name = name or p.name
    data = p.read_bytes()
    max_kb = _get_max_size_kb(fmt)
    data = _check_size(data, max_kb)
    if not data:
        return

    att = _make_attachment_from_bytes(data, file_name)
    fmt.attach(att)


def attach_text(
    context: Any,
    text: str,
    name: str = "log.txt",
) -> None:
    """Attach a text string to the current step.

    Args:
        context: Behave ``context`` object.
        text: The text content to attach.
        name: Attachment name (defaults to ``"log.txt"``).
    """
    fmt = _find_formatter(context)
    if fmt is None:
        return

    max_kb = _get_max_size_kb(fmt)
    encoded = text.encode("utf-8")
    if max_kb > 0 and len(encoded) > max_kb * 1024:
        encoded = encoded[: max_kb * 1024]
        text = encoded.decode("utf-8", errors="ignore")

    att = _make_attachment_from_text(text, name)
    fmt.attach(att)


def attach_json(
    context: Any,
    data: Any,
    name: str = "data.json",
) -> None:
    """Attach a JSON-serialisable value to the current step.

    Args:
        context: Behave ``context`` object.
        data: Any JSON-serialisable value (dict, list, etc.).
        name: Attachment name (defaults to ``"data.json"``).
    """
    fmt = _find_formatter(context)
    if fmt is None:
        return

    text = json.dumps(data, indent=2, default=str, ensure_ascii=False)
    max_kb = _get_max_size_kb(fmt)
    encoded = text.encode("utf-8")
    if max_kb > 0 and len(encoded) > max_kb * 1024:
        encoded = encoded[: max_kb * 1024]
        text = encoded.decode("utf-8", errors="ignore")

    att = _make_attachment_from_text(text, name, "application/json")
    fmt.attach(att)


def log(context: Any, message: str) -> None:
    """Add a log message to the current step.

    Args:
        context: Behave ``context`` object.
        message: The log message text.
    """
    fmt = _find_formatter(context)
    if fmt is None:
        return
    fmt.log(message)


__all__ = [
    # Public API
    "attach_screenshot",
    "attach_file",
    "attach_text",
    "attach_json",
    "log",
    # Internal helpers
    "_find_formatter",
    "_is_file_formatter",
    "_guess_mime_type",
    "_bytes_to_base64",
    "_make_attachment_from_bytes",
    "_make_attachment_from_text",
    "_make_attachment_from_file",
    "_check_size",
    "_get_max_size_kb",
    "_is_selenium_driver",
    "_is_playwright_page",
    "_is_pil_image",
    "_capture_screenshot",
]
