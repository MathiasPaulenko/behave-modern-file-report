"""Plain-text report writer for Behave.

Generates a human-readable text report from a ``RunSummary`` tree.
Supports configurable line width and ASCII-only mode.
"""

from __future__ import annotations

import base64
import binascii
import textwrap
from typing import TextIO

from behave_modern_file_reports.models import (
    Background,
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

# Status icons (Unicode and ASCII variants)
_STATUS_ICONS_UNICODE: dict[str, str] = {
    STATUS_PASSED: "\u2713",
    STATUS_FAILED: "\u2717",
    STATUS_SKIPPED: "\u25cb",
    STATUS_UNDEFINED: "?",
}

_STATUS_ICONS_ASCII: dict[str, str] = {
    STATUS_PASSED: "[PASS]",
    STATUS_FAILED: "[FAIL]",
    STATUS_SKIPPED: "[SKIP]",
    STATUS_UNDEFINED: "[????]",
}

_STATUS_LABELS: dict[str, str] = {
    STATUS_PASSED: "PASSED",
    STATUS_FAILED: "FAILED",
    STATUS_SKIPPED: "SKIPPED",
    STATUS_UNDEFINED: "UNDEFINED",
}


class TXTWriter:
    """Writes a plain-text report from a ``RunSummary``.

    The report structure is:
    1. Cover (title, project, run metadata)
    2. Executive summary (totals, pass rate)
    3. Per-feature detail (scenarios, steps, errors)
    """

    def __init__(self, options: ReportOptions) -> None:
        """Initialize the writer with resolved options.

        Args:
            options: The resolved report options.
        """
        self._width: int = max(40, options.txt_width)
        self._ascii: bool = options.txt_ascii
        self._icons: dict[str, str] = (
            _STATUS_ICONS_ASCII if self._ascii else _STATUS_ICONS_UNICODE
        )

    def write(self, run_summary: RunSummary, stream: TextIO) -> None:
        """Write the full report to the given stream.

        Args:
            run_summary: The finalized run summary.
            stream: A writable text stream.
        """
        self._write_cover(run_summary, stream)
        self._write_summary(run_summary, stream)
        for feature in run_summary.features:
            self._write_feature(feature, stream)

    # ------------------------------------------------------------------
    # Cover
    # ------------------------------------------------------------------

    def _write_cover(self, run: RunSummary, stream: TextIO) -> None:
        """Write the cover section."""
        stream.write(self._separator("="))
        stream.write("\n")
        stream.write(self._center(run.title or "Behave Modern Report"))
        stream.write("\n")
        if run.project_name:
            stream.write(self._center(run.project_name))
            stream.write("\n")
        stream.write(self._separator("="))
        stream.write("\n\n")

        meta_lines = [
            f"Run ID:     {run.run_id}",
            f"Start:      {run.start_time}",
            f"End:        {run.end_time}",
            f"Duration:   {format_duration(run.duration)}",
            f"Status:     {_STATUS_LABELS.get(run.status, run.status.upper())}",
        ]
        for line in meta_lines:
            stream.write(line)
            stream.write("\n")
        stream.write("\n")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def _write_summary(self, run: RunSummary, stream: TextIO) -> None:
        """Write the executive summary section."""
        stream.write(self._separator("-"))
        stream.write("\n")
        stream.write("SUMMARY")
        stream.write("\n")
        stream.write(self._separator("-"))
        stream.write("\n\n")

        total = run.total_scenarios
        passed = run.passed
        failed = run.failed
        skipped = run.skipped
        undefined = run.undefined
        pass_rate = run.pass_rate * 100

        lines = [
            f"Features:    {run.total_features}",
            f"Scenarios:   {total}",
            f"  Passed:    {passed}",
            f"  Failed:    {failed}",
            f"  Skipped:    {skipped}",
            f"  Undefined:  {undefined}",
            f"Pass rate:   {pass_rate:.1f}%",
        ]
        for line in lines:
            stream.write(line)
            stream.write("\n")
        stream.write("\n")

    # ------------------------------------------------------------------
    # Feature
    # ------------------------------------------------------------------

    def _write_feature(self, feature: FeatureSummary, stream: TextIO) -> None:
        """Write a feature section with its scenarios."""
        icon = self._icons.get(feature.derive_status(), "?")
        stream.write(self._separator("-"))
        stream.write("\n")
        stream.write(f"{icon} FEATURE: {feature.name}")
        stream.write("\n")
        if feature.location:
            stream.write(f"   Location: {feature.location}")
            stream.write("\n")
        if feature.tags:
            stream.write(f"   Tags: {', '.join(feature.tags)}")
            stream.write("\n")
        if feature.description:
            for line in self._wrap(feature.description, indent="   "):
                stream.write(line)
                stream.write("\n")
        stream.write(self._separator("-"))
        stream.write("\n\n")

        if feature.background is not None:
            self._write_background(feature.background, stream)

        for scenario in feature.scenarios:
            self._write_scenario(scenario, stream)

        stream.write("\n")

    # ------------------------------------------------------------------
    # Background
    # ------------------------------------------------------------------

    def _write_background(self, background: Background, stream: TextIO) -> None:
        """Write a background section."""
        stream.write(f"   Background: {background.name}")
        stream.write("\n")
        for step in background.steps:
            self._write_step(step, stream, indent="      ")
        stream.write("\n")

    # ------------------------------------------------------------------
    # Scenario
    # ------------------------------------------------------------------

    def _write_scenario(self, scenario: ScenarioResult, stream: TextIO) -> None:
        """Write a scenario section with its steps."""
        icon = self._icons.get(scenario.status, "?")
        label = _STATUS_LABELS.get(scenario.status, scenario.status.upper())

        outline_tag = ""
        if scenario.is_outline:
            outline_tag = " [OUTLINE]"

        stream.write(f"   {icon} {label}{outline_tag}: {scenario.name}")
        stream.write("\n")
        if scenario.location:
            stream.write(f"      Location: {scenario.location}")
            stream.write("\n")
        if scenario.rule_name:
            stream.write(f"      Rule: {scenario.rule_name}")
            stream.write("\n")
        if scenario.tags:
            stream.write(f"      Tags: {', '.join(scenario.tags)}")
            stream.write("\n")
        stream.write(
            f"      Duration: {format_duration(scenario.duration)}"
        )
        stream.write("\n\n")

        if scenario.background is not None:
            self._write_background(scenario.background, stream)

        for step in scenario.steps:
            self._write_step(step, stream, indent="      ")

        if scenario.error is not None:
            self._write_error(scenario.error, stream)

        stream.write("\n")

    # ------------------------------------------------------------------
    # Step
    # ------------------------------------------------------------------

    def _write_step(self, step: Step, stream: TextIO, indent: str) -> None:
        """Write a single step line."""
        icon = self._icons.get(step.status, "?")
        duration_str = format_duration(step.duration)
        keyword = step.keyword
        if keyword and not keyword.endswith(" "):
            keyword = f"{keyword} "
        line = f"{icon} {keyword}{step.name}"
        if step.duration > 0:
            line = f"{line} ({duration_str})"

        wrapped = self._wrap(line, indent=indent)
        for wl in wrapped:
            stream.write(wl)
            stream.write("\n")

        if step.error is not None:
            self._write_error(step.error, stream, indent=indent + "   ")

        if step.attachments:
            stream.write(f"{indent}Attachments:\n")
            for att in step.attachments:
                size_info = ""
                if att.data_base64:
                    try:
                        raw_len = len(base64.b64decode(att.data_base64))
                        size_info = f" ({raw_len} bytes)"
                    except (binascii.Error, ValueError):
                        size_info = " (invalid base64)"
                stream.write(f"{indent}  - {att.name} [{att.mime_type}]{size_info}")
                stream.write("\n")
                if att.text:
                    for text_line in att.text.splitlines():
                        stream.write(f"{indent}    {text_line}")
                        stream.write("\n")

        if step.logs:
            for log_line in step.logs:
                stream.write(f"{indent}  > {log_line}")
                stream.write("\n")

    # ------------------------------------------------------------------
    # Error
    # ------------------------------------------------------------------

    def _write_error(
        self,
        error: object,
        stream: TextIO,
        indent: str = "      ",
    ) -> None:
        """Write an error block with traceback."""
        message = getattr(error, "message", str(error))
        exception_type = getattr(error, "exception_type", "")
        traceback_str = getattr(error, "traceback", "")

        header = f"{indent}ERROR"
        if exception_type:
            header = f"{header} ({exception_type})"
        header = f"{header}: {message}"
        stream.write(header)
        stream.write("\n")

        if traceback_str:
            for tb_line in traceback_str.splitlines():
                stream.write(f"{indent}  {tb_line}")
                stream.write("\n")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _separator(self, char: str) -> str:
        """Return a separator line of the configured width."""
        return char * self._width

    def _center(self, text: str) -> str:
        """Center text within the configured width."""
        return text.center(self._width)

    def _wrap(self, text: str, indent: str = "") -> list[str]:
        """Wrap text to the configured width with indentation.

        Args:
            text: The text to wrap.
            indent: The indentation prefix for continuation lines.

        Returns:
            A list of wrapped lines.
        """
        effective_width = max(20, self._width - len(indent))
        lines: list[str] = []
        for paragraph in text.splitlines():
            if not paragraph:
                lines.append("")
                continue
            wrapped = textwrap.wrap(paragraph, width=effective_width)
            if not wrapped:
                lines.append("")
                continue
            lines.append(f"{indent}{wrapped[0]}")
            for wl in wrapped[1:]:
                lines.append(f"{indent}{wl}")
        return lines


__all__ = ["TXTWriter"]
