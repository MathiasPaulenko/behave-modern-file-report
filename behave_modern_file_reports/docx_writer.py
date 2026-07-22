"""DOCX report writer for Behave.

Generates a Word document from a ``RunSummary`` tree using ``python-docx``.
The report structure mirrors the PDF output: cover page, TOC placeholder,
executive summary, environment metadata, and per-feature detail with
scenario headings, step tables, and error blocks.
"""

from __future__ import annotations

import base64
import io
from html import escape as _html_escape
from pathlib import Path
from typing import Any

from docx import Document
from docx.document import Document as DocxDocument
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsmap, qn
from docx.shared import Cm, Pt, RGBColor
from docx.table import Table
from docx.text.paragraph import Paragraph

from behave_modern_file_reports.models import (
    Background,
    Environment,
    FeatureSummary,
    ReportOptions,
    RunSummary,
    ScenarioResult,
    Step,
)
from behave_modern_file_reports.utils import (
    STATUS_FAILED,
    STATUS_PASSED,
    STATUS_SKIPPED,
    STATUS_UNDEFINED,
    format_duration,
)

# Status colors (RGB)
_STATUS_COLORS: dict[str, RGBColor] = {
    STATUS_PASSED: RGBColor(0x10, 0xB9, 0x81),
    STATUS_FAILED: RGBColor(0xEF, 0x44, 0x44),
    STATUS_SKIPPED: RGBColor(0xF5, 0x9E, 0x0B),
    STATUS_UNDEFINED: RGBColor(0x9C, 0xA3, 0xAF),
}

_STATUS_ICONS: dict[str, str] = {
    STATUS_PASSED: "\u2713",
    STATUS_FAILED: "\u2717",
    STATUS_SKIPPED: "\u2298",
    STATUS_UNDEFINED: "?",
}

_STATUS_LABELS: dict[str, str] = {
    STATUS_PASSED: "PASSED",
    STATUS_FAILED: "FAILED",
    STATUS_SKIPPED: "SKIPPED",
    STATUS_UNDEFINED: "UNDEFINED",
}

_DEFAULT_PRIMARY = RGBColor(0x25, 0x63, 0xEB)
_DEFAULT_PRIMARY_DARK = RGBColor(0x1E, 0x40, 0xAF)
_TEXT_MUTED = RGBColor(0x6B, 0x72, 0x80)
_ERROR_BG = "FEF2F2"
_ERROR_BORDER = "EF4444"
_SURFACE_BG = "F9FAFB"


def _hex_to_rgb(hex_color: str) -> RGBColor:
    """Convert a hex color string to ``RGBColor``.

    Args:
        hex_color: A ``#RRGGBB`` hex string.

    Returns:
        ``RGBColor`` instance.
    """
    h = hex_color.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _darken(hex_color: str, factor: float = 0.8) -> RGBColor:
    """Darken a hex color by a factor.

    Args:
        hex_color: A ``#RRGGBB`` hex string.
        factor: Darkening factor (0-1).

    Returns:
        Darkened ``RGBColor``.
    """
    h = hex_color.lstrip("#")
    r = int(int(h[0:2], 16) * factor)
    g = int(int(h[2:4], 16) * factor)
    b = int(int(h[4:6], 16) * factor)
    return RGBColor(r, g, b)


class DOCXWriter:
    """Writes a DOCX report from a ``RunSummary``.

    The report follows the visual design system with cover page,
    TOC placeholder, executive summary, environment metadata, and
    per-feature detail sections.
    """

    def __init__(self, options: ReportOptions) -> None:
        """Initialize the writer with resolved options.

        Args:
            options: The resolved report options.
        """
        self._options = options
        self._primary = (
            _hex_to_rgb(options.primary_color)
            if options.primary_color
            else _DEFAULT_PRIMARY
        )
        self._primary_dark = (
            _darken(options.primary_color)
            if options.primary_color
            else _DEFAULT_PRIMARY_DARK
        )
        self._bookmark_id = 1

    def write(self, run_summary: RunSummary, path: str | Path) -> None:
        """Write the full DOCX report to the given path.

        Args:
            run_summary: The finalized run summary.
            path: Output file path for the ``.docx`` file.
        """
        doc = Document()
        self._bookmark_id = 1
        self._setup_styles(doc)
        self._write_cover(doc, run_summary)
        self._write_toc(doc, run_summary)
        self._write_summary(doc, run_summary)
        self._write_environment(doc, run_summary.environment)
        for f_idx, feature in enumerate(run_summary.features):
            self._write_feature(doc, feature, f_idx)
        doc.save(str(path))

    # ------------------------------------------------------------------
    # Styles
    # ------------------------------------------------------------------

    def _setup_styles(self, doc: DocxDocument) -> None:
        """Configure document styles."""
        style = doc.styles["Normal"]
        style.font.name = "Calibri"
        style.font.size = Pt(11)

        for heading_name, size, color in [
            ("Heading 1", 18, self._primary_dark),
            ("Heading 2", 14, self._primary_dark),
            ("Heading 3", 12, self._primary_dark),
        ]:
            heading_style = doc.styles[heading_name]
            heading_style.font.size = Pt(size)
            heading_style.font.color.rgb = color
            heading_style.font.name = "Calibri Light"

        # Ensure the Hyperlink character style exists for TOC entries
        if "Hyperlink" not in doc.styles:
            hyperlink_style = doc.styles.add_style(
                "Hyperlink", WD_STYLE_TYPE.CHARACTER
            )
            hyperlink_style.font.color.rgb = RGBColor(0x05, 0x63, 0xC1)
            hyperlink_style.font.underline = True

    # ------------------------------------------------------------------
    # Cover page
    # ------------------------------------------------------------------

    def _write_cover(self, doc: DocxDocument, run: RunSummary) -> None:
        """Write the cover page with title, project, and metadata."""
        # Logo
        if self._options.logo_b64:
            try:
                img_data = base64.b64decode(
                    self._options.logo_b64.split(",", 1)[1]
                    if "," in self._options.logo_b64
                    else self._options.logo_b64
                )
                img_stream = io.BytesIO(img_data)
                doc.add_picture(img_stream, width=Cm(4))
                last_para = doc.paragraphs[-1]
                last_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            except Exception:
                pass

        title_para = doc.add_paragraph()
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_para.paragraph_format.space_after = Pt(8)
        title_run = title_para.add_run(run.title or "Behave Modern Report")
        title_run.font.size = Pt(28)
        title_run.font.color.rgb = self._primary
        title_run.bold = True

        if run.project_name:
            subtitle_para = doc.add_paragraph()
            subtitle_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            subtitle_para.paragraph_format.space_after = Pt(16)
            sub_run = subtitle_para.add_run(run.project_name)
            sub_run.font.size = Pt(14)
            sub_run.font.color.rgb = _TEXT_MUTED

        # Metadata table (2 columns: label | value)
        meta_rows = [
            ("Started", run.start_time),
            ("Duration", format_duration(run.duration)),
            ("Scenarios", str(run.total_scenarios)),
            ("Passed", str(run.passed)),
            ("Failed", str(run.failed)),
            ("Skipped", str(run.skipped)),
            ("Pass rate", f"{run.pass_rate * 100:.1f}%"),
        ]
        meta_table = doc.add_table(rows=len(meta_rows), cols=2)
        meta_table.style = "Table Grid"
        self._set_table_widths(meta_table, [Cm(4.5), Cm(11)])
        for idx, (label, value) in enumerate(meta_rows):
            row = meta_table.rows[idx]
            label_cell = row.cells[0]
            value_cell = row.cells[1]
            label_para = label_cell.paragraphs[0]
            label_run = label_para.add_run(label)
            label_run.bold = True
            label_run.font.size = Pt(10)
            label_run.font.color.rgb = _TEXT_MUTED
            value_cell.paragraphs[0].add_run(value).font.size = Pt(10)

        # Progress bar
        doc.add_paragraph()
        self._add_progress_bar(doc, run.pass_rate)

        doc.add_page_break()  # type: ignore[no-untyped-call]

    def _add_progress_bar(self, doc: DocxDocument, pass_rate: float) -> None:
        """Add a visual progress bar as a shaded table cell."""
        pct = int(pass_rate * 100)
        bar_table = doc.add_table(rows=1, cols=2)
        bar_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        self._set_table_widths(
            bar_table,
            [Cm(15 * pass_rate), Cm(15 * (1 - pass_rate))],
        )
        filled_cell = bar_table.rows[0].cells[0]
        # Shade the filled cell
        self._shade_cell(filled_cell, self._primary)
        filled_para = filled_cell.paragraphs[0]
        filled_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        filled_run = filled_para.add_run(f"{pct}%")
        filled_run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        filled_run.bold = True
        filled_run.font.size = Pt(10)

    # ------------------------------------------------------------------
    # Table of contents
    # ------------------------------------------------------------------

    def _write_toc(self, doc: DocxDocument, run: RunSummary) -> None:
        """Insert a visible table of contents."""
        heading = doc.add_heading("Table of Contents", level=1)
        heading.style = doc.styles["Heading 1"]

        toc_entries: list[tuple[str, str, int]] = [
            ("Executive Summary", "executive-summary", 0),
            ("Environment", "environment", 0),
        ]
        for f_idx, feature in enumerate(run.features):
            toc_entries.append((feature.name, f"feature-{f_idx}", 0))
            for s_idx, scenario in enumerate(feature.scenarios):
                toc_entries.append(
                    (scenario.name, f"scenario-{f_idx}-{s_idx}", 1)
                )

        for text, bookmark_name, level in toc_entries:
            para = doc.add_paragraph()
            para.paragraph_format.left_indent = Cm(0.6 * level)
            para.paragraph_format.space_after = Pt(2)
            self._add_toc_link(
                para, text, bookmark_name, 11 if level == 0 else 10
            )

        doc.add_page_break()  # type: ignore[no-untyped-call]

    # ------------------------------------------------------------------
    # Executive summary
    # ------------------------------------------------------------------

    def _write_summary(self, doc: DocxDocument, run: RunSummary) -> None:
        """Write the executive summary section."""
        heading = doc.add_heading("Executive Summary", level=1)
        self._add_bookmark(heading, "executive-summary")

        # Totals table (1 row, 4 columns)
        totals = [
            (str(run.total_scenarios), "Scenarios"),
            (str(run.passed), "Passed"),
            (str(run.failed), "Failed"),
            (str(run.skipped), "Skipped"),
        ]
        totals_table = doc.add_table(rows=2, cols=4)
        totals_table.style = "Table Grid"
        totals_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        self._set_table_widths(totals_table, [Cm(3.8), Cm(3.8), Cm(3.8), Cm(3.8)])
        for idx, (number, label) in enumerate(totals):
            num_cell = totals_table.rows[0].cells[idx]
            num_para = num_cell.paragraphs[0]
            num_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            num_run = num_para.add_run(number)
            num_run.bold = True
            num_run.font.size = Pt(20)
            if label == "Passed":
                num_run.font.color.rgb = _STATUS_COLORS[STATUS_PASSED]
            elif label == "Failed":
                num_run.font.color.rgb = _STATUS_COLORS[STATUS_FAILED]
            elif label == "Skipped":
                num_run.font.color.rgb = _STATUS_COLORS[STATUS_SKIPPED]

            label_cell = totals_table.rows[1].cells[idx]
            label_para = label_cell.paragraphs[0]
            label_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            label_run = label_para.add_run(label)
            label_run.font.size = Pt(10)
            label_run.font.color.rgb = _TEXT_MUTED

        doc.add_paragraph()

        # Per-feature table
        if run.features:
            headers = [
                "Feature", "Scenarios", "Passed", "Failed",
                "Skipped", "Pass rate", "Duration",
            ]
            feat_table = doc.add_table(rows=1 + len(run.features), cols=len(headers))
            feat_table.style = "Table Grid"
            self._set_table_widths(
                feat_table,
                [Cm(4.0), Cm(2.2), Cm(1.8), Cm(1.7), Cm(1.9), Cm(2.0), Cm(1.9)],
            )
            # Header row
            for idx, header in enumerate(headers):
                cell = feat_table.rows[0].cells[idx]
                para = cell.paragraphs[0]
                text_run = para.add_run(header)
                text_run.bold = True
                text_run.font.size = Pt(10)
                self._shade_cell(cell, None, _SURFACE_BG)
            # Data rows
            for row_idx, feature in enumerate(run.features):
                row = feat_table.rows[row_idx + 1]
                row.cells[0].paragraphs[0].add_run(feature.name).font.size = Pt(10)
                row.cells[1].paragraphs[0].add_run(str(feature.total_scenarios)).font.size = Pt(10)
                row.cells[2].paragraphs[0].add_run(str(feature.passed)).font.size = Pt(10)
                row.cells[3].paragraphs[0].add_run(str(feature.failed)).font.size = Pt(10)
                row.cells[4].paragraphs[0].add_run(str(feature.skipped)).font.size = Pt(10)
                row.cells[5].paragraphs[0].add_run(
                    f"{feature.pass_rate * 100:.1f}%"
                ).font.size = Pt(10)
                row.cells[6].paragraphs[0].add_run(
                    format_duration(feature.duration)
                ).font.size = Pt(10)

        doc.add_page_break()  # type: ignore[no-untyped-call]

    # ------------------------------------------------------------------
    # Environment metadata
    # ------------------------------------------------------------------

    def _write_environment(self, doc: DocxDocument, env: Environment) -> None:
        """Write the environment metadata section."""
        heading = doc.add_heading("Environment", level=1)
        self._add_bookmark(heading, "environment")

        env_rows = [
            ("Python", env.python_version),
            ("Behave", env.behave_version),
            ("Platform", env.platform),
            ("Hostname", env.hostname),
            ("Working directory", env.cwd),
            ("Command", env.command),
            ("User", env.user),
            ("CPU count", str(env.cpu_count) if env.cpu_count else ""),
            ("Git branch", env.git_branch),
            ("Git commit", env.git_commit),
        ]
        env_table = doc.add_table(rows=len(env_rows), cols=2)
        env_table.style = "Table Grid"
        self._set_table_widths(env_table, [Cm(4.5), Cm(11)])
        for idx, (label, value) in enumerate(env_rows):
            row = env_table.rows[idx]
            label_cell = row.cells[0]
            value_cell = row.cells[1]
            label_run = label_cell.paragraphs[0].add_run(label)
            label_run.bold = True
            label_run.font.size = Pt(10)
            label_run.font.color.rgb = _TEXT_MUTED
            self._shade_cell(label_cell, None, _SURFACE_BG)
            value_cell.paragraphs[0].add_run(value).font.size = Pt(10)

        doc.add_page_break()  # type: ignore[no-untyped-call]

    # ------------------------------------------------------------------
    # Feature
    # ------------------------------------------------------------------

    def _write_feature(
        self,
        doc: DocxDocument,
        feature: FeatureSummary,
        feature_index: int,
    ) -> None:
        """Write a feature section with scenarios."""
        heading = doc.add_heading(feature.name, level=1)
        self._add_bookmark(heading, f"feature-{feature_index}")

        # Status badge
        status = feature.derive_status()
        self._add_status_badge(doc, status)

        # Location
        if feature.location:
            loc_para = doc.add_paragraph()
            loc_run = loc_para.add_run(f"Location: {feature.location}")
            loc_run.font.size = Pt(9)
            loc_run.font.color.rgb = _TEXT_MUTED

        # Tags
        if feature.tags:
            tags_para = doc.add_paragraph()
            tags_run = tags_para.add_run(
                f"Tags: {', '.join(f'@{t}' for t in feature.tags)}"
            )
            tags_run.font.size = Pt(9)
            tags_run.font.color.rgb = _TEXT_MUTED

        # Description
        if feature.description:
            doc.add_paragraph(feature.description)

        # Feature summary table
        self._add_feature_summary_table(doc, feature)

        # Background
        if feature.background is not None:
            self._write_background(doc, feature.background)

        # Scenarios
        for s_idx, scenario in enumerate(feature.scenarios):
            self._write_scenario(doc, scenario, feature_index, s_idx)

    def _add_feature_summary_table(
        self, doc: DocxDocument, feature: FeatureSummary
    ) -> None:
        """Add a mini summary table for a feature."""
        headers = ["Total", "Passed", "Failed", "Skipped", "Undefined", "Pass rate"]
        values = [
            str(feature.total_scenarios),
            str(feature.passed),
            str(feature.failed),
            str(feature.skipped),
            str(feature.undefined),
            f"{feature.pass_rate * 100:.1f}%",
        ]
        table = doc.add_table(rows=2, cols=len(headers))
        table.style = "Table Grid"
        self._set_table_widths(table, [Cm(2.6)] * len(headers))
        for idx, header in enumerate(headers):
            cell = table.rows[0].cells[idx]
            run = cell.paragraphs[0].add_run(header)
            run.bold = True
            run.font.size = Pt(9)
            self._shade_cell(cell, None, _SURFACE_BG)
        for idx, value in enumerate(values):
            table.rows[1].cells[idx].paragraphs[0].add_run(value).font.size = Pt(9)

    # ------------------------------------------------------------------
    # Background
    # ------------------------------------------------------------------

    def _write_background(self, doc: DocxDocument, background: Background) -> None:
        """Write a background section."""
        doc.add_heading(f"Background: {background.name}", level=3)
        self._write_step_table(doc, background.steps)

    # ------------------------------------------------------------------
    # Scenario
    # ------------------------------------------------------------------

    def _write_scenario(
        self,
        doc: DocxDocument,
        scenario: ScenarioResult,
        feature_index: int,
        scenario_index: int,
    ) -> None:
        """Write a scenario section with steps and errors."""
        heading_text = scenario.name
        if scenario.is_outline:
            heading_text = f"{heading_text} [OUTLINE]"
        heading = doc.add_heading(heading_text, level=2)
        self._add_bookmark(
            heading, f"scenario-{feature_index}-{scenario_index}"
        )

        # Status badge
        self._add_status_badge(doc, scenario.status)

        # Metadata
        if scenario.location:
            loc_para = doc.add_paragraph()
            loc_run = loc_para.add_run(f"Location: {scenario.location}")
            loc_run.font.size = Pt(9)
            loc_run.font.color.rgb = _TEXT_MUTED

        if scenario.rule_name:
            rule_para = doc.add_paragraph()
            rule_run = rule_para.add_run(f"Rule: {scenario.rule_name}")
            rule_run.font.size = Pt(9)
            rule_run.font.color.rgb = _TEXT_MUTED

        if scenario.tags:
            tags_para = doc.add_paragraph()
            tags_run = tags_para.add_run(
                f"Tags: {', '.join(f'@{t}' for t in scenario.tags)}"
            )
            tags_run.font.size = Pt(9)
            tags_run.font.color.rgb = _TEXT_MUTED

        dur_para = doc.add_paragraph()
        dur_run = dur_para.add_run(f"Duration: {format_duration(scenario.duration)}")
        dur_run.font.size = Pt(9)
        dur_run.font.color.rgb = _TEXT_MUTED

        # Scenario background
        if scenario.background is not None:
            self._write_background(doc, scenario.background)

        # Step table
        self._write_step_table(doc, scenario.steps, scenario.error)

        # Error block
        if scenario.error is not None:
            self._write_error_block(doc, scenario.error)

        # Attachments
        self._write_attachments(doc, scenario)

        doc.add_paragraph()

    # ------------------------------------------------------------------
    # Step table
    # ------------------------------------------------------------------

    def _write_step_table(
        self,
        doc: DocxDocument,
        steps: list[Step],
        scenario_error: object | None = None,
    ) -> None:
        """Write a table of steps."""
        if not steps:
            return

        headers = ["Status", "Step", "Duration"]
        table = doc.add_table(rows=1 + len(steps), cols=len(headers))
        table.style = "Table Grid"
        self._set_table_widths(table, [Cm(2.5), Cm(9.5), Cm(2.5)])
        for idx, header in enumerate(headers):
            cell = table.rows[0].cells[idx]
            run = cell.paragraphs[0].add_run(header)
            run.bold = True
            run.font.size = Pt(10)
            self._shade_cell(cell, None, _SURFACE_BG)

        for step_idx, step in enumerate(steps):
            row = table.rows[step_idx + 1]
            icon = _STATUS_ICONS.get(step.status, "?")
            status_cell = row.cells[0]
            status_para = status_cell.paragraphs[0]
            status_run = status_para.add_run(
                f"{icon} {_STATUS_LABELS.get(step.status, step.status)}"
            )
            status_run.font.size = Pt(10)
            color = _STATUS_COLORS.get(step.status)
            if color is not None:
                status_run.font.color.rgb = color

            step_cell = row.cells[1]
            step_para = step_cell.paragraphs[0]
            keyword_run = step_para.add_run(f"{step.keyword.rstrip()} ")
            keyword_run.bold = True
            keyword_run.font.size = Pt(10)
            step_para.add_run(step.name).font.size = Pt(10)

            dur_cell = row.cells[2]
            dur_para = dur_cell.paragraphs[0]
            dur_run = dur_para.add_run(format_duration(step.duration))
            dur_run.font.size = Pt(10)
            dur_run.font.color.rgb = _TEXT_MUTED

            # Step error (avoid duplicating the scenario-level error)
            if step.error is not None and step.error != scenario_error:
                self._write_error_block(doc, step.error)

            # Step attachments
            if step.attachments:
                att_para = doc.add_paragraph()
                att_run = att_para.add_run(
                    f"Attachments: {', '.join(a.name for a in step.attachments)}"
                )
                att_run.font.size = Pt(9)
                att_run.font.color.rgb = _TEXT_MUTED

            # Step logs
            if step.logs:
                for log_line in step.logs:
                    log_para = doc.add_paragraph()
                    log_run = log_para.add_run(f"> {log_line}")
                    log_run.font.size = Pt(9)
                    log_run.font.color.rgb = _TEXT_MUTED

    # ------------------------------------------------------------------
    # Error block
    # ------------------------------------------------------------------

    def _write_error_block(self, doc: DocxDocument, error: object) -> None:
        """Write an error block with red background and traceback."""
        message = getattr(error, "message", str(error))
        exception_type = getattr(error, "exception_type", "")
        traceback_str = getattr(error, "traceback", "")

        table = doc.add_table(rows=1, cols=1)
        table.style = "Table Grid"
        cell = table.rows[0].cells[0]
        self._shade_cell(cell, None, _ERROR_BG)

        # Title
        title_para = cell.paragraphs[0]
        title_run = title_para.add_run("Failure")
        title_run.bold = True
        title_run.font.size = Pt(11)
        title_run.font.color.rgb = RGBColor(0xEF, 0x44, 0x44)

        # Error type
        if exception_type:
            type_para = cell.add_paragraph()
            type_run = type_para.add_run(f"Error type: {exception_type}")
            type_run.font.size = Pt(10)

        # Message
        msg_para = cell.add_paragraph()
        msg_run = msg_para.add_run(f"Message: {message}")
        msg_run.font.size = Pt(10)

        # Traceback
        if traceback_str:
            tb_para = cell.add_paragraph()
            tb_run = tb_para.add_run(f"Traceback:\n{traceback_str}")
            tb_run.font.size = Pt(9)
            tb_run.font.name = "Consolas"

    # ------------------------------------------------------------------
    # Attachments
    # ------------------------------------------------------------------

    def _write_attachments(self, doc: DocxDocument, scenario: ScenarioResult) -> None:
        """Write attachments for a scenario.

        Images are inserted inline with a max width of 16cm.
        Text/JSON attachments are shown in monospace font with a light background.
        Binary files are listed by name only.
        """
        all_attachments: list[Any] = []
        for step in scenario.steps:
            for att in step.attachments:
                all_attachments.append(att)
        if not all_attachments:
            return

        heading = doc.add_paragraph()
        heading_run = heading.add_run("Attachments")
        heading_run.font.size = Pt(11)
        heading_run.font.bold = True
        heading_run.font.color.rgb = self._primary_dark

        for att in all_attachments:
            if att.is_image and self._options.include_attachments and att.data_base64:
                self._insert_image_inline(doc, att)
            elif att.text is not None:
                self._insert_text_attachment(doc, att)
            else:
                name_para = doc.add_paragraph()
                name_run = name_para.add_run(f"  - {att.name}")
                name_run.font.size = Pt(9)
                name_run.font.color.rgb = _TEXT_MUTED

    def _insert_image_inline(self, doc: DocxDocument, att: Any) -> None:
        """Insert an image attachment inline with max width."""
        try:
            img_data = base64.b64decode(att.data_base64)
            img_stream = io.BytesIO(img_data)
            doc.add_picture(img_stream, width=Cm(16))
        except Exception:
            name_para = doc.add_paragraph()
            name_run = name_para.add_run(f"  - {att.name} (image, could not display)")
            name_run.font.size = Pt(9)
            name_run.font.color.rgb = _TEXT_MUTED

    def _insert_text_attachment(self, doc: DocxDocument, att: Any) -> None:
        """Insert a text attachment in monospace font."""
        name_para = doc.add_paragraph()
        name_run = name_para.add_run(f"  - {att.name}")
        name_run.font.size = Pt(9)
        name_run.font.color.rgb = _TEXT_MUTED

        if att.text:
            text_para = doc.add_paragraph()
            text_run = text_para.add_run(att.text)
            text_run.font.size = Pt(8)
            text_run.font.name = "Consolas"
            text_run.font.color.rgb = _TEXT_MUTED

    # ------------------------------------------------------------------
    # Status badge
    # ------------------------------------------------------------------

    def _add_status_badge(self, doc: DocxDocument, status: str) -> None:
        """Add a status badge as a shaded table cell."""
        table = doc.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        self._set_table_widths(table, [Cm(3)])
        cell = table.rows[0].cells[0]
        color = _STATUS_COLORS.get(status)
        if color is not None:
            self._shade_cell(cell, color)
        para = cell.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = para.add_run(_STATUS_LABELS.get(status, status.upper()))
        run.bold = True
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _add_bookmark(self, paragraph: Paragraph, name: str) -> None:
        """Add a bookmark covering the entire paragraph."""
        w_ns = nsmap["w"]
        bid = self._bookmark_id
        self._bookmark_id += 1
        start = parse_xml(
            f'<w:bookmarkStart w:id="{bid}" w:name="{name}" '
            f'xmlns:w="{w_ns}" />'
        )
        end = parse_xml(f'<w:bookmarkEnd w:id="{bid}" xmlns:w="{w_ns}" />')
        p = paragraph._p
        pPr = p.find(qn("w:pPr"))
        if pPr is not None:
            pPr.addnext(start)
        else:
            p.insert(0, start)
        p.append(end)

    def _add_toc_link(
        self,
        paragraph: Paragraph,
        text: str,
        bookmark_name: str,
        font_size: int,
    ) -> None:
        """Add a hyperlink to a bookmark in the given paragraph."""
        w_ns = nsmap["w"]
        escaped = _html_escape(text, quote=True)
        half_pts = font_size * 2
        hyperlink = parse_xml(
            f'<w:hyperlink w:anchor="{bookmark_name}" w:history="1" '
            f'xmlns:w="{w_ns}"><w:r><w:rPr>'
            f'<w:rStyle w:val="Hyperlink"/>'
            f'<w:sz w:val="{half_pts}"/>'
            f'<w:szCs w:val="{half_pts}"/>'
            f'</w:rPr><w:t>{escaped}</w:t></w:r></w:hyperlink>'
        )
        paragraph._p.append(hyperlink)

    def _set_table_widths(self, table: Table, widths: list[Any]) -> None:
        """Set fixed column widths for a table."""
        table.autofit = False
        for idx, width in enumerate(widths):
            table.columns[idx].width = width

    def _shade_cell(
        self,
        cell: object,
        color: RGBColor | None = None,
        bg_hex: str | None = None,
    ) -> None:
        """Apply background shading to a table cell.

        Args:
            cell: The table cell to shade.
            color: If provided, convert to hex and use as background.
            bg_hex: Background color as a hex string without ``#``.
        """
        if bg_hex is None and color is not None:
            bg_hex = f"{color[0]:02X}{color[1]:02X}{color[2]:02X}"
        if bg_hex is None:
            return  # pragma: no cover
        w_ns = nsmap["w"]
        shading = parse_xml(
            f'<w:shd w:fill="{bg_hex}" w:val="clear" '
            f'xmlns:w="{w_ns}" />'
        )
        cell._tc.append(shading)  # type: ignore[attr-defined]


__all__ = ["DOCXWriter"]
