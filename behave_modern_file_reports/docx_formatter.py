"""Behave formatter that produces a DOCX report.

Registered as ``behave-modern-docx`` in Behave's formatter entry points.
"""

from __future__ import annotations

from behave_modern_file_reports.base_formatter import BaseFileFormatter
from behave_modern_file_reports.docx_writer import DOCXWriter
from behave_modern_file_reports.models import ReportOptions, RunSummary


class DOCXFormatter(BaseFileFormatter):
    """Behave formatter producing a DOCX report file.

    Usage in Behave::

        behave -f behave-modern-docx -o report.docx features/
    """

    name = "behave-modern-docx"
    description = "DOCX report for Behave"
    _format_key = "docx"
    _default_filename = "report.docx"

    def _write_report(self, run_summary: RunSummary, options: ReportOptions) -> None:
        """Write the DOCX report to the output path.

        Args:
            run_summary: The finalized run summary.
            options: The resolved report options.
        """
        writer = DOCXWriter(options)
        path = self._resolve_path()
        writer.write(run_summary, path)


__all__ = ["DOCXFormatter"]
