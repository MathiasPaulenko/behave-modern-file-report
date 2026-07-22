"""Base Behave formatter protocol for file-based report generation.

This module provides ``BaseFileFormatter``, an abstract Behave formatter that
collects execution events via a ``Collector`` and delegates report writing to
subclasses through ``_write_report``.

The formatter reads Behave's ``config.userdata`` and resolves options using
``ReportOptions.from_dict`` with format-specific overrides (``bmfr.<format>.*``).
"""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any

from behave.formatter.base import Formatter

from behave_modern_file_reports.collector import Collector
from behave_modern_file_reports.models import (
    Attachment,
    ReportOptions,
    RunSummary,
)


class BaseFileFormatter(Formatter):  # type: ignore[misc]
    """Abstract Behave formatter that collects events and writes a report.

    Subclasses must set ``_format_key`` and implement ``_write_report``.
    """

    name: str = "file-reports"
    description: str = "Base file report formatter for Behave"
    _format_key: str = ""
    _default_filename: str = "report.txt"

    def __init__(
        self,
        stream_opener: Any | None = None,
        config: Any | None = None,
    ) -> None:
        """Initialize the formatter with a stream opener and config.

        Args:
            stream_opener: Behave's stream opener (or mock) for output.
            config: Behave's config object (or mock) with ``userdata``.
        """
        if stream_opener is not None and config is not None:
            # Behave's Formatter.__init__ expects stream_opener.stream
            if not hasattr(stream_opener, "stream"):
                stream_opener.stream = None
            super().__init__(stream_opener, config)
        else:
            self.stream_opener = stream_opener
            self.stream = getattr(stream_opener, "stream", None) if stream_opener else None
            self.config = config

        self._stream_opener = stream_opener
        self._config = config

        userdata: dict[str, str] = {}
        if config is not None:
            raw_userdata = getattr(config, "userdata", None)
            if raw_userdata is not None:
                userdata = dict(raw_userdata)

        self._options = ReportOptions.from_dict(userdata, self._format_key)
        self._collector = Collector(
            max_traceback_lines=self._options.max_traceback_lines,
        )
        self._closed = False
        self._attachment_buffer: list[Attachment] = []
        self._log_buffer: list[str] = []

    # ------------------------------------------------------------------
    # Behave formatter protocol
    # ------------------------------------------------------------------

    def uri(self, uri: str) -> None:
        """Handle a feature URI notification (no-op for file reports)."""

    def feature(self, feature: Any) -> None:
        """Begin tracking a feature.

        Finalizes the previous feature if one is still open.

        Args:
            feature: A Behave ``Feature`` object.
        """
        self._collector.end_scenario()
        self._collector.end_feature()
        self._collector.start_feature(feature)

    def background(self, background: Any) -> None:
        """Begin tracking a background section.

        Args:
            background: A Behave ``Background`` object.
        """
        self._collector.start_background(background)

    def rule(self, rule: Any) -> None:
        """Handle a rule notification.

        The rule name is captured per-scenario via ``start_scenario``, so
        this method is a no-op at the formatter level.

        Args:
            rule: A Behave ``Rule`` object.
        """

    def scenario(self, scenario: Any) -> None:
        """Begin tracking a scenario.

        Finalizes the previous scenario if one is still open.

        Args:
            scenario: A Behave ``Scenario`` object.
        """
        self._collector.end_scenario()
        self._collector.start_scenario(scenario)

    def step(self, step: Any) -> None:
        """Begin tracking a step.

        Args:
            step: A Behave ``Step`` object.
        """
        self._collector.start_step(step)

    def result(self, step: Any) -> None:
        """Finalize a step with its result.

        Flushes any buffered attachments and logs to the step before
        finalizing it in the collector.

        Args:
            step: A Behave ``Step`` object with status and duration.
        """
        if self._collector._step_queue:
            current_step = self._collector._step_queue[0]
            for attachment in self._attachment_buffer:
                current_step.attachments.append(attachment)
            for message in self._log_buffer:
                current_step.logs.append(message)
        self._attachment_buffer.clear()
        self._log_buffer.clear()

        self._collector.end_step(step)

    def eof(self) -> None:
        """Handle end-of-file notification (finalizes current feature/scenario)."""
        self._collector.end_scenario()
        self._collector.end_feature()

    def close(self) -> None:
        """Finalize the run and write the report exactly once."""
        if self._closed:
            return
        self._closed = True
        self._resolve_logo()
        run_summary = self._collector.finalize()
        run_summary.title = self._options.title
        if self._options.project_name:
            run_summary.project_name = self._options.project_name
        self._write_report(run_summary, self._options)

    # ------------------------------------------------------------------
    # Branding helpers
    # ------------------------------------------------------------------

    def _resolve_logo(self) -> None:
        """Resolve the logo file path to a base64 data URI.

        If ``self._options.logo`` is set and points to an existing file,
        the file is read and encoded as a base64 data URI in
        ``self._options.logo_b64``.
        """
        if self._options.logo_b64:
            return
        if not self._options.logo:
            return
        logo_path = Path(self._options.logo)
        if not logo_path.is_file():
            return
        mime, _ = mimetypes.guess_type(str(logo_path))
        if mime is None or not mime.startswith("image/"):
            mime = "image/png"
        data = logo_path.read_bytes()
        encoded = base64.b64encode(data).decode("ascii")
        self._options.logo_b64 = f"data:{mime};base64,{encoded}"

    # ------------------------------------------------------------------
    # Attachment and log API
    # ------------------------------------------------------------------

    def attach(self, attachment: Attachment) -> None:
        """Buffer an attachment to be added to the current step.

        Args:
            attachment: The attachment to add.
        """
        self._attachment_buffer.append(attachment)

    def log(self, message: str) -> None:
        """Buffer a log message to be added to the current step.

        Args:
            message: The log message text.
        """
        self._log_buffer.append(message)

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    def _write_report(self, run_summary: RunSummary, options: ReportOptions) -> None:
        """Write the report to the output stream.

        Subclasses must implement this method.

        Args:
            run_summary: The finalized run summary.
            options: The resolved report options.
        """
        raise NotImplementedError


__all__ = ["BaseFileFormatter"]
