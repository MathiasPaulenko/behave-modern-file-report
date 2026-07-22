"""PDF report writers for Behave reports.

Provides two engines:

* **WeasyPrint** (default) — renders the Jinja2 HTML template to PDF.
* **ReportLab** (fallback) — builds the PDF directly using ReportLab's
  canvas API, reusing the same design tokens.

The engine is selected via ``ReportOptions.pdf_engine``
(``"weasyprint"`` or ``"reportlab"``).  Both engines are lazy-imported
so neither dependency is required at install time.

Usage::

    writer = PDFWriter(options)
    writer.write(run_summary, path)
"""

from __future__ import annotations

import functools
import html
from pathlib import Path
from typing import Any

from behave_modern_file_report.html_renderer import render_html
from behave_modern_file_report.models import (
    Background,
    ErrorInfo,
    FeatureSummary,
    ReportOptions,
    RunSummary,
    ScenarioResult,
    Step,
)
from behave_modern_file_report.utils import (
    STATUS_COLORS,
    STATUS_FAILED,
    STATUS_ICONS,
    STATUS_LABELS,
    format_duration,
    hex_to_rgb,
)

# ---------------------------------------------------------------------------
# Design tokens (shared with WeasyPrint CSS)
# ---------------------------------------------------------------------------

_PRIMARY = hex_to_rgb("#2563EB")
_PRIMARY_DARK = hex_to_rgb("#1E40AF")
_TEXT = hex_to_rgb("#1F2937")
_TEXT_MUTED = hex_to_rgb("#6B7280")
_BORDER = hex_to_rgb("#E5E7EB")
_SURFACE = hex_to_rgb("#F9FAFB")
_ERROR_BG = hex_to_rgb("#FEF2F2")

_STATUS_COLORS: dict[str, tuple[int, int, int]] = {
    k: hex_to_rgb(v) for k, v in STATUS_COLORS.items()
}


_format_duration = functools.partial(
    format_duration,
    precision=2,
    zero_label="0ms",
)


def _rl(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    """Convert a 0-255 RGB tuple to 0-1 range for ReportLab."""
    return (rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)


def _escape(text: str) -> str:
    """Escape text for ReportLab Paragraph HTML content."""
    return html.escape(str(text), quote=True)


def _step_paragraph(step: Step, style: Any) -> Any:
    """Return a ReportLab Paragraph for a step description."""
    from reportlab.platypus import Paragraph

    keyword = _escape(step.keyword.rstrip())
    name = _escape(step.name)
    return Paragraph(f"<b>{keyword}</b> {name}", style)


# ---------------------------------------------------------------------------
# PDFWriter — engine dispatcher
# ---------------------------------------------------------------------------


class PDFWriter:
    """Generate a PDF report from a :class:`RunSummary`.

    The engine is selected via ``options.pdf_engine``:

    * ``"weasyprint"`` (default) — HTML → PDF via WeasyPrint.
    * ``"reportlab"`` — direct PDF via ReportLab.

    Args:
        options: Resolved report options.
    """

    def __init__(self, options: ReportOptions | None = None) -> None:
        self._options = options or ReportOptions()

    def write(self, run_summary: RunSummary, path: str | Path) -> None:
        """Write the PDF report to ``path``.

        Args:
            run_summary: The finalized run summary.
            path: Output file path for the PDF.

        Raises:
            ImportError: If the selected PDF engine is not installed.
        """
        if self._options.pdf_engine == "reportlab":  # pragma: no cover
            writer = ReportLabWriter(self._options)
            writer.write(run_summary, path)
        else:
            html = render_html(run_summary, self._options)
            self._render_weasyprint(html, path)

    def render_html_string(self, run_summary: RunSummary) -> str:
        """Return the intermediate HTML string without writing a PDF.

        Args:
            run_summary: The finalized run summary.

        Returns:
            Rendered HTML string.
        """
        return render_html(run_summary, self._options)

    def _render_weasyprint(self, html: str, path: str | Path) -> None:
        """Render HTML to PDF using WeasyPrint.

        Args:
            html: HTML string to render.
            path: Output file path.

        Raises:
            ImportError: If WeasyPrint is not installed.
        """
        try:
            from weasyprint import HTML
        except (ImportError, OSError) as exc:
            raise ImportError(
                "WeasyPrint is required for PDF generation. "
                "Install it with: pip install weasyprint"
            ) from exc

        output_path = str(path)  # pragma: no cover
        HTML(string=html).write_pdf(output_path)  # pragma: no cover


# ---------------------------------------------------------------------------
# ReportLabWriter — fallback engine
# ---------------------------------------------------------------------------


class ReportLabWriter:
    """Generate a basic PDF report using ReportLab.

    Reuses the same design tokens as the WeasyPrint output but with
    fewer styling options (no CSS, no HTML templates).

    Args:
        options: Resolved report options.
    """

    def __init__(self, options: ReportOptions | None = None) -> None:
        self._options = options or ReportOptions()

    def write(self, run_summary: RunSummary, path: str | Path) -> None:  # pragma: no cover
        """Write the PDF report to ``path``.

        Args:
            run_summary: The finalized run summary.
            path: Output file path for the PDF.

        Raises:
            ImportError: If ReportLab is not installed.
        """
        try:
            from reportlab.lib.enums import TA_CENTER, TA_RIGHT
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import mm
            from reportlab.platypus import (
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )
        except ImportError as exc:
            raise ImportError(
                "ReportLab is required for PDF generation. "
                "Install it with: pip install reportlab"
            ) from exc

        output_path = str(path)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=25 * mm,
            bottomMargin=25 * mm,
        )

        styles = getSampleStyleSheet()
        style_title = ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontSize=28,
            textColor=_rl(_PRIMARY),
            spaceAfter=20,
        )
        style_subtitle = ParagraphStyle(
            "ReportSubtitle",
            parent=styles["Normal"],
            fontSize=14,
            textColor=_rl(_TEXT_MUTED),
            spaceAfter=24,
        )
        style_h1 = ParagraphStyle(
            "ReportH1",
            parent=styles["Heading1"],
            fontSize=18,
            textColor=_rl(_PRIMARY_DARK),
            spaceBefore=20,
            spaceAfter=10,
        )
        style_h2 = ParagraphStyle(
            "ReportH2",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=_rl(_TEXT),
            spaceBefore=14,
            spaceAfter=8,
        )
        style_h3 = ParagraphStyle(
            "ReportH3",
            parent=styles["Heading3"],
            fontSize=11,
            textColor=_rl(_TEXT_MUTED),
            spaceBefore=10,
            spaceAfter=6,
        )
        style_normal = ParagraphStyle(
            "ReportNormal",
            parent=styles["Normal"],
            fontSize=10.5,
            textColor=_rl(_TEXT),
            spaceAfter=4,
        )
        style_muted = ParagraphStyle(
            "ReportMuted",
            parent=styles["Normal"],
            fontSize=9,
            textColor=_rl(_TEXT_MUTED),
            spaceAfter=4,
        )
        style_mono = ParagraphStyle(
            "ReportMono",
            parent=styles["Code"],
            fontSize=9,
            textColor=_rl(_TEXT),
            spaceAfter=4,
            splitLongWords=True,
        )
        style_cell = ParagraphStyle(
            "ReportCell",
            parent=style_normal,
            fontSize=9,
            leading=11,
            spaceAfter=0,
            splitLongWords=True,
        )
        style_cell_center = ParagraphStyle(
            "ReportCellCenter",
            parent=style_cell,
            alignment=TA_CENTER,
        )
        style_cell_right = ParagraphStyle(
            "ReportCellRight",
            parent=style_cell,
            alignment=TA_RIGHT,
        )
        style_cell_muted = ParagraphStyle(
            "ReportCellMuted",
            parent=style_muted,
            fontSize=9,
            leading=11,
            spaceAfter=0,
        )
        style_cell_header = ParagraphStyle(
            "ReportCellHeader",
            parent=style_cell,
            fontName="Helvetica-Bold",
            textColor=_rl(_PRIMARY_DARK),
            alignment=TA_CENTER,
        )

        story: list[Any] = []

        # -- Cover page --
        story.append(Paragraph(
            _escape(run_summary.title or "Behave Modern Report"),
            style_title,
        ))
        if run_summary.project_name:
            story.append(Paragraph(_escape(run_summary.project_name), style_subtitle))

        pct = run_summary.pass_rate * 100
        cover_rows = [
            [Paragraph("Started:", style_cell_muted),
             Paragraph(_escape(run_summary.start_time), style_cell)],
            [Paragraph("Duration:", style_cell_muted),
             Paragraph(_format_duration(run_summary.duration), style_cell)],
            [Paragraph("Scenarios:", style_cell_muted),
             Paragraph(str(run_summary.total_scenarios), style_cell)],
            [Paragraph("Passed:", style_cell_muted),
             Paragraph(str(run_summary.passed), style_cell)],
            [Paragraph("Failed:", style_cell_muted),
             Paragraph(str(run_summary.failed), style_cell)],
            [Paragraph("Skipped:", style_cell_muted),
             Paragraph(str(run_summary.skipped), style_cell)],
            [Paragraph("Pass rate:", style_cell_muted),
             Paragraph(f"{pct:.1f}%", style_cell)],
        ]
        cover_table = Table(cover_rows, colWidths=[50 * mm, 120 * mm])
        cover_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, _rl(_BORDER)),
            ("BACKGROUND", (0, 0), (0, -1), _rl(_SURFACE)),
            ("TEXTCOLOR", (0, 0), (0, -1), _rl(_TEXT_MUTED)),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(cover_table)
        story.append(Spacer(1, 30))

        # -- Executive summary --
        story.append(Paragraph("Executive Summary", style_h1))
        totals_data = [
            [Paragraph("Scenarios", style_cell_header), Paragraph("Passed", style_cell_header),
             Paragraph("Failed", style_cell_header), Paragraph("Skipped", style_cell_header)],
            [Paragraph(str(run_summary.total_scenarios), style_cell_center),
             Paragraph(str(run_summary.passed), style_cell_center),
             Paragraph(str(run_summary.failed), style_cell_center),
             Paragraph(str(run_summary.skipped), style_cell_center)],
        ]
        totals_table = Table(totals_data, colWidths=[42.5 * mm] * 4)
        totals_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _rl(_SURFACE)),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.5, _rl(_BORDER)),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(totals_table)
        story.append(Spacer(1, 16))

        # Feature summary table
        if run_summary.features:
            feat_headers = [
                "Feature", "Scenarios", "Passed", "Failed",
                "Skipped", "Pass rate", "Duration",
            ]
            feat_rows = [[Paragraph(h, style_cell_header) for h in feat_headers]]
            for feat in run_summary.features:
                feat_rows.append([
                    Paragraph(_escape(feat.name), style_cell),
                    Paragraph(str(feat.total_scenarios), style_cell_center),
                    Paragraph(str(feat.passed), style_cell_center),
                    Paragraph(str(feat.failed), style_cell_center),
                    Paragraph(str(feat.skipped), style_cell_center),
                    Paragraph(f"{feat.pass_rate * 100:.1f}%", style_cell_right),
                    Paragraph(_format_duration(feat.duration), style_cell_right),
                ])
            feat_table = Table(
                feat_rows,
                colWidths=[50 * mm, 22 * mm, 16 * mm, 16 * mm, 18 * mm, 20 * mm, 18 * mm],
            )
            feat_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), _rl(_SURFACE)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 1), (6, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, _rl(_BORDER)),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(feat_table)
        story.append(Spacer(1, 20))

        # -- Environment --
        story.append(Paragraph("Environment", style_h1))
        env = run_summary.environment
        env_rows = [
            [
                Paragraph("Python", style_cell_muted),
                Paragraph(_escape(env.python_version), style_cell),
            ],
            [
                Paragraph("Behave", style_cell_muted),
                Paragraph(_escape(env.behave_version), style_cell),
            ],
            [
                Paragraph("Platform", style_cell_muted),
                Paragraph(_escape(env.platform), style_cell),
            ],
            [
                Paragraph("Hostname", style_cell_muted),
                Paragraph(_escape(env.hostname), style_cell),
            ],
            [
                Paragraph("Working directory", style_cell_muted),
                Paragraph(_escape(env.cwd), style_cell),
            ],
            [
                Paragraph("Command", style_cell_muted),
                Paragraph(_escape(env.command), style_cell),
            ],
            [
                Paragraph("User", style_cell_muted),
                Paragraph(_escape(env.user), style_cell),
            ],
            [
                Paragraph("Git branch", style_cell_muted),
                Paragraph(_escape(env.git_branch), style_cell),
            ],
            [
                Paragraph("Git commit", style_cell_muted),
                Paragraph(_escape(env.git_commit), style_cell),
            ],
        ]
        env_table = Table(env_rows, colWidths=[50 * mm, 120 * mm])
        env_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, _rl(_BORDER)),
            ("BACKGROUND", (0, 0), (0, -1), _rl(_SURFACE)),
            ("TEXTCOLOR", (0, 0), (0, -1), _rl(_TEXT_MUTED)),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(env_table)
        story.append(Spacer(1, 20))

        # -- Per-feature sections --
        cell_styles = {
            "cell": style_cell,
            "center": style_cell_center,
            "right": style_cell_right,
            "muted": style_cell_muted,
            "header": style_cell_header,
        }
        for feature in run_summary.features:
            self._write_feature(
                feature, story, style_h1, style_h2, style_h3,
                style_normal, style_muted, style_mono, cell_styles,
            )

        doc.build(story)

    def _write_feature(  # pragma: no cover
        self,
        feature: FeatureSummary,
        story: list[Any],
        style_h1: Any,
        style_h2: Any,
        style_h3: Any,
        style_normal: Any,
        style_muted: Any,
        style_mono: Any,
        cell_styles: dict[str, Any],
    ) -> None:
        """Write a feature section to the story."""
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

        story.append(Paragraph(_escape(feature.name), style_h1))
        feature_status = feature.derive_status()
        status_label = STATUS_LABELS.get(feature_status, feature_status.upper())
        status_color = _STATUS_COLORS.get(feature_status, _TEXT_MUTED)
        story.append(Paragraph(
            f'<font color="#{status_color[0]:02X}{status_color[1]:02X}{status_color[2]:02X}">'
            f"{_escape(status_label)}</font>",
            style_muted,
        ))
        if feature.location:
            story.append(Paragraph(_escape(feature.location), style_muted))
        if feature.description:
            story.append(Paragraph(_escape(feature.description), style_normal))
        if feature.tags:
            story.append(Paragraph(
                "Tags: " + " ".join(f"@{_escape(t)}" for t in feature.tags),
                style_muted,
            ))

        # Feature summary table
        headers = ["Total", "Passed", "Failed", "Skipped", "Undefined", "Pass rate"]
        summary_data = [[Paragraph(h, cell_styles["header"]) for h in headers]]
        summary_data.append([
            Paragraph(str(feature.total_scenarios), cell_styles["center"]),
            Paragraph(str(feature.passed), cell_styles["center"]),
            Paragraph(str(feature.failed), cell_styles["center"]),
            Paragraph(str(feature.skipped), cell_styles["center"]),
            Paragraph(str(feature.undefined), cell_styles["center"]),
            Paragraph(f"{feature.pass_rate * 100:.1f}%", cell_styles["right"]),
        ])
        summary_table = Table(summary_data, colWidths=[28 * mm] * 6)
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _rl(_SURFACE)),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, _rl(_BORDER)),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 12))

        # Background
        if feature.background:
            self._write_background(
                feature.background, story, style_h3,
                style_normal, style_muted, style_mono, cell_styles,
            )

        # Scenarios
        for scenario in feature.scenarios:
            self._write_scenario(
                scenario, story, style_h2, style_h3,
                style_normal, style_muted, style_mono, cell_styles,
            )

    def _write_scenario(  # pragma: no cover
        self,
        scenario: ScenarioResult,
        story: list[Any],
        style_h2: Any,
        style_h3: Any,
        style_normal: Any,
        style_muted: Any,
        style_mono: Any,
        cell_styles: dict[str, Any],
    ) -> None:
        """Write a scenario section to the story."""
        from reportlab.platypus import Paragraph, Spacer

        name = _escape(scenario.name)
        if scenario.is_outline:
            name += " [OUTLINE]"
        story.append(Paragraph(name, style_h2))

        status_label = STATUS_LABELS.get(scenario.status, scenario.status.upper())
        status_color = _STATUS_COLORS.get(scenario.status, _TEXT_MUTED)
        story.append(Paragraph(
            f'<font color="#{status_color[0]:02X}{status_color[1]:02X}{status_color[2]:02X}">'
            f"{_escape(status_label)}</font>",
            style_muted,
        ))

        meta_parts: list[str] = []
        if scenario.location:
            meta_parts.append(f"Location: {_escape(scenario.location)}")
        if scenario.rule_name:
            meta_parts.append(f"Rule: {_escape(scenario.rule_name)}")
        meta_parts.append(f"Duration: {_format_duration(scenario.duration)}")
        story.append(Paragraph("  |  ".join(meta_parts), style_muted))

        if scenario.tags:
            story.append(Paragraph(
                "Tags: " + " ".join(f"@{_escape(t)}" for t in scenario.tags),
                style_muted,
            ))

        # Background
        if scenario.background:
            self._write_background(
                scenario.background, story, style_h3,
                style_normal, style_muted, style_mono, cell_styles,
            )

        # Step table
        self._write_step_table(scenario.steps, story, cell_styles)

        # Error block
        if scenario.error:
            self._write_error_block(scenario.error, story, style_h3, style_mono)

        # Attachments
        attachments: list[Any] = []
        for step in scenario.steps:
            attachments.extend(step.attachments)
        if attachments:
            story.append(Paragraph("Attachments", style_h3))
            for att in attachments:
                story.append(Paragraph(f"- {_escape(att.name)}", style_muted))
                if att.text:
                    story.append(Paragraph(_escape(att.text), style_mono))

        # Logs
        logs: list[str] = []
        for step in scenario.steps:
            logs.extend(step.logs)
        if logs:
            story.append(Paragraph("Logs", style_h3))
            for line in logs:
                story.append(Paragraph(_escape(line), style_mono))

        story.append(Spacer(1, 16))

    def _write_background(  # pragma: no cover
        self,
        background: Background,
        story: list[Any],
        style_h3: Any,
        style_normal: Any,
        style_muted: Any,
        style_mono: Any,
        cell_styles: dict[str, Any],
    ) -> None:
        """Write a background section to the story."""
        from reportlab.platypus import Paragraph

        story.append(Paragraph(f"Background: {_escape(background.name)}", style_h3))
        self._write_step_table(background.steps, story, cell_styles)

    def _write_step_table(  # pragma: no cover
        self,
        steps: list[Step],
        story: list[Any],
        cell_styles: dict[str, Any],
    ) -> None:
        """Write a step table to the story."""
        if not steps:
            return
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

        data = [
            [Paragraph("Status", cell_styles["header"]),
             Paragraph("Step", cell_styles["header"]),
             Paragraph("Duration", cell_styles["header"])],
        ]
        for step in steps:
            icon = STATUS_ICONS.get(step.status, "?")
            label = STATUS_LABELS.get(step.status, step.status.upper())
            data.append([
                Paragraph(f"{_escape(icon)} {_escape(label)}", cell_styles["muted"]),
                _step_paragraph(step, cell_styles["cell"]),
                Paragraph(_format_duration(step.duration), cell_styles["right"]),
            ])
        table = Table(data, colWidths=[25 * mm, 115 * mm, 30 * mm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _rl(_SURFACE)),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 1), (0, -1), "CENTER"),
            ("ALIGN", (2, 1), (2, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, _rl(_BORDER)),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(table)
        story.append(Spacer(1, 8))

    def _write_error_block(  # pragma: no cover
        self,
        error: ErrorInfo,
        story: list[Any],
        style_h3: Any,
        style_mono: Any,
    ) -> None:
        """Write an error block to the story."""
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

        story.append(Paragraph("Failure", style_h3))
        lines: list[str] = []
        if error.exception_type:
            lines.append(f"Type: {_escape(error.exception_type)}")
        lines.append(f"Message: {_escape(error.message)}")
        if error.traceback:
            lines.append("Traceback:")
            for tb_line in error.traceback.splitlines():
                lines.append(_escape(tb_line))
        error_text = "<br/>".join(lines)
        error_table = Table([[Paragraph(error_text, style_mono)]], colWidths=[170 * mm])
        error_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), _rl(_ERROR_BG)),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LINEBEFORE", (0, 0), (0, -1), 3, _rl(_STATUS_COLORS[STATUS_FAILED])),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(error_table)
        story.append(Spacer(1, 8))


__all__ = ["PDFWriter", "ReportLabWriter"]
