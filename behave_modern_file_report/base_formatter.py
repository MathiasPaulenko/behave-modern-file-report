"""Base Behave formatter protocol for file-based report generation.

This module provides ``BaseFileFormatter``, an abstract Behave formatter that
collects execution events via a ``Collector`` and delegates report writing to
subclasses through ``_write_report``.

The formatter reads Behave's ``config.userdata`` and resolves options using
``ReportOptions.from_dict`` with format-specific overrides (``bmfr.<format>.*``).
"""

from __future__ import annotations

import base64
import contextlib
import mimetypes
from pathlib import Path
from typing import Any

from behave.formatter.base import Formatter

from behave_modern_file_report.collector import Collector
from behave_modern_file_report.models import (
    Attachment,
    FeatureSummary,
    ReportOptions,
    RunSummary,
)
from behave_modern_file_report.utils import STATUS_FAILED, clean_xml_text


def _filter_failed_scenarios(run_summary: RunSummary) -> None:
    """Reduce a run summary to failed scenarios only.

    Mutates ``run_summary.features`` so that each feature contains only its
    failed scenarios. Features with no failed scenarios are removed.
    """
    filtered_features: list[FeatureSummary] = []
    for feature in run_summary.features:
        failed_scenarios = [
            scenario for scenario in feature.scenarios if scenario.status == STATUS_FAILED
        ]
        if not failed_scenarios:
            # A feature can be failed by a hook without any failed scenario;
            # keep it (with full context) rather than dropping the failure.
            if feature.status != STATUS_FAILED:
                continue
            failed_scenarios = list(feature.scenarios)
        filtered_features.append(
            FeatureSummary(
                name=feature.name,
                description=feature.description,
                status=feature.status,
                duration=feature.duration,
                tags=feature.tags,
                location=feature.location,
                scenarios=failed_scenarios,
                background=feature.background,
            )
        )
    run_summary.features = filtered_features


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
                with contextlib.suppress(TypeError, ValueError):
                    userdata = dict(raw_userdata)

        self._options = ReportOptions.from_dict(userdata, self._format_key)
        self._collector = Collector(
            max_traceback_lines=self._options.max_traceback_lines,
        )
        self._closed = False
        self._attachment_buffer: list[Attachment] = []
        self._log_buffer: list[str] = []
        self._embed_count = 0

    # ------------------------------------------------------------------
    # Behave formatter protocol
    # ------------------------------------------------------------------

    def uri(self, uri: str) -> None:
        """Handle a feature URI notification (no-op for file reports)."""

    def embedding(self, mime_type: str, data: Any) -> None:
        """Support Behave's ``context.attach(mime_type, data)`` API.

        Behave forwards attachments to every formatter defining
        ``embedding(mime_type, data)``. The data is raw bytes; it is
        buffered like any other attachment and flushed to the step that
        is running when the call happens.

        Args:
            mime_type: MIME type of the data (e.g. ``"image/png"``).
            data: Raw attachment data (``bytes``, ``str`` or bytes-like).
        """
        mime = mime_type if isinstance(mime_type, str) and mime_type else "application/octet-stream"
        if isinstance(data, str):
            raw = data.encode("utf-8")
        else:
            try:
                raw = bytes(data)
            except (TypeError, ValueError):
                raw = str(data).encode("utf-8")
        ext = mimetypes.guess_extension(mime.split(";", 1)[0].strip()) or ".bin"
        self._embed_count += 1
        attachment = Attachment(
            name=f"embed-{self._embed_count}{ext}",
            mime_type=mime,
            data_base64=base64.b64encode(raw).decode("ascii"),
        )
        if mime.startswith("text/") or mime in ("application/json", "application/xml"):
            attachment.text = clean_xml_text(raw.decode("utf-8", errors="replace"))
        self.attach(attachment)

    def feature(self, feature: Any) -> None:
        """Begin tracking a feature.

        Finalizes the previous feature if one is still open.

        Args:
            feature: A Behave ``Feature`` object.
        """
        self._collector.end_background()
        self._flush_orphan_buffers()
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

        Finalizes the previous scenario if one is still open. The background
        section is also finalized here because Behave does not emit an explicit
        ``end_background`` event.

        Args:
            scenario: A Behave ``Scenario`` object.
        """
        self._collector.end_background()
        self._flush_orphan_buffers()
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
        current_step = self._collector.peek_current_step()
        if current_step is not None:
            for attachment in self._attachment_buffer:
                current_step.attachments.append(attachment)
            for message in self._log_buffer:
                current_step.logs.append(message)
            self._attachment_buffer.clear()
            self._log_buffer.clear()

        self._collector.end_step(step)

    def rule_finished(self) -> None:
        """Handle the end of a Rule block (finalizes the current scenario).

        Behave emits ``rule_finished`` instead of ``eof`` when a Rule
        container ends; the enclosing feature remains open.
        """
        self._collector.end_background()
        self._flush_orphan_buffers()
        self._collector.end_scenario()

    def eof(self) -> None:
        """Handle end-of-file notification (finalizes current feature/scenario)."""
        self._collector.end_background()
        self._flush_orphan_buffers()
        self._collector.end_scenario()
        self._collector.end_feature()

    def close(self) -> None:
        """Finalize the run and write the report exactly once."""
        if self._closed:
            return
        # Finalize anything still open (e.g. an aborted run) and flush
        # attachments/logs buffered after the last step result.
        self.eof()
        self._resolve_logo()
        run_summary = self._collector.finalize()
        run_summary.title = clean_xml_text(self._options.title)
        if self._options.project_name:
            run_summary.project_name = clean_xml_text(self._options.project_name)
        if self._options.only_failed:
            _filter_failed_scenarios(run_summary)
        self._write_report(run_summary, self._options)
        # Only mark closed after a successful write so a failed report can be
        # retried instead of being permanently swallowed.
        self._closed = True

    # ------------------------------------------------------------------
    # Branding helpers
    # ------------------------------------------------------------------

    def _resolve_path(self) -> str:
        """Resolve the output path from the stream opener or default filename.

        Binary writers (PDF/DOCX) never open the Behave stream, so the
        stream opener's own ``ensure_dir_exists`` never runs. The parent
        directory is created here instead.

        Returns:
            The stream opener's ``name`` attribute, or ``self._default_filename``.
        """
        path = str(getattr(self, "_default_filename", ""))
        if self._stream_opener is not None:
            name = getattr(self._stream_opener, "name", None)
            if name is not None:
                path = str(name)
        try:
            parent = Path(path).parent
            if str(parent) not in ("", "."):
                parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        return path

    def _resolve_logo(self) -> None:
        """Resolve the logo file path to a base64 data URI.

        If ``self._options.logo`` is set and points to an existing file,
        the file is read and encoded as a base64 data URI in
        ``self._options.logo_b64``.
        """
        _MAX_LOGO_SIZE_KB = 5 * 1024

        if self._options.logo_b64:
            return
        if not self._options.logo:
            return
        logo_path = Path(self._options.logo).expanduser()
        if not logo_path.is_file():
            return
        mime, _ = mimetypes.guess_type(str(logo_path))
        if mime is None:
            mime = "image/png"
        elif not mime.startswith("image/"):
            return
        try:
            if logo_path.stat().st_size > _MAX_LOGO_SIZE_KB * 1024:
                return
            data = logo_path.read_bytes()
        except OSError:
            return
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
        self._log_buffer.append(
            clean_xml_text(message if isinstance(message, str) else str(message))
        )

    def _flush_orphan_buffers(self) -> None:
        """Flush attachment/log buffers to the last step of the current scenario.

        Attachments and logs emitted outside of a step result (for example in
        ``after_scenario`` hooks) are buffered without a matching queued step.
        Attach them to the most recent step so they are not silently dropped.

        When there is no step to attach to yet (for example attachments
        emitted from ``before_scenario`` of a step-less scenario), the
        buffers are kept so the next step result or boundary picks them up
        instead of being silently discarded.
        """
        if not self._attachment_buffer and not self._log_buffer:
            return
        scenario = self._collector._current_scenario
        if scenario is None:
            return
        candidates = scenario.steps
        if not candidates and scenario.background is not None:
            candidates = scenario.background.steps
        if not candidates:
            return
        target_step = candidates[-1]
        target_step.attachments.extend(self._attachment_buffer)
        target_step.logs.extend(self._log_buffer)
        self._attachment_buffer.clear()
        self._log_buffer.clear()

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
