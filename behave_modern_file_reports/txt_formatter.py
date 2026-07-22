"""Behave formatter that produces a plain-text report.

Registered as ``behave-modern-txt`` in Behave's formatter entry points.
"""

from __future__ import annotations

from typing import Any

from behave_modern_file_reports.base_formatter import BaseFileFormatter
from behave_modern_file_reports.models import ReportOptions, RunSummary
from behave_modern_file_reports.txt_writer import TXTWriter


class TXTFormatter(BaseFileFormatter):
    """Behave formatter producing a plain-text report file.

    Usage in Behave::

        behave -f behave-modern-txt -o report.txt features/
    """

    name = "behave-modern-txt"
    description = "Plain text report for Behave"
    _format_key = "txt"
    _default_filename = "report.txt"

    def _write_report(self, run_summary: RunSummary, options: ReportOptions) -> None:
        """Write the text report to the output stream.

        Args:
            run_summary: The finalized run summary.
            options: The resolved report options.
        """
        writer = TXTWriter(options)
        stream = self._open_stream()
        try:
            writer.write(run_summary, stream)
        finally:
            self._close_stream(stream)

    def _open_stream(self) -> Any:
        """Open the output stream in UTF-8 mode.

        Forces the Behave stream opener to use UTF-8 so Unicode status icons
        and arrows are written correctly on all platforms.
        """
        if self._stream_opener is not None:
            open_method = getattr(self._stream_opener, "open", None)
            if open_method is not None:
                encoding_attr = getattr(self._stream_opener, "encoding", None)
                if encoding_attr is not None:
                    self._stream_opener.encoding = "utf-8"
                return open_method()
        # Fallback: open default filename
        return open(self._default_filename, "w", encoding="utf-8")

    def _close_stream(self, stream: Any) -> None:
        """Close the output stream if it was opened by this formatter."""
        flush = getattr(stream, "flush", None)
        if flush is not None:
            flush()
        if self._stream_opener is None:
            stream.close()
        else:
            close_method = getattr(self._stream_opener, "close", None)
            if callable(close_method):
                close_method()


__all__ = ["TXTFormatter"]
