"""Behave formatter that produces a PDF report.

Registered as ``behave-modern-pdf`` in Behave's formatter entry points.
"""

from __future__ import annotations

from behave_modern_file_reports.base_formatter import BaseFileFormatter
from behave_modern_file_reports.models import ReportOptions, RunSummary
from behave_modern_file_reports.pdf_writer import PDFWriter


class PDFFormatter(BaseFileFormatter):
    """Behave formatter producing a PDF report file.

    Usage in Behave::

        behave -f behave-modern-pdf -o report.pdf features/
    """

    name = "behave-modern-pdf"
    description = "PDF report for Behave"
    _format_key = "pdf"
    _default_filename = "report.pdf"

    def _write_report(  # pragma: no cover
        self, run_summary: RunSummary, options: ReportOptions,
    ) -> None:
        """Write the PDF report to the output path.

        Args:
            run_summary: The finalized run summary.
            options: The resolved report options.
        """
        writer = PDFWriter(options)
        path = self._resolve_path()
        writer.write(run_summary, path)


__all__ = ["PDFFormatter"]
