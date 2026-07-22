"""Domain models for behave-modern-file-reports.

Pure dataclasses with ``slots=True`` and zero external dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from behave_modern_file_reports.utils import (
    STATUS_FAILED,
    STATUS_PASSED,
    STATUS_SKIPPED,
    STATUS_UNDEFINED,
    parse_bool,
    parse_color,
    parse_int,
    parse_pdf_engine,
)

# ---------------------------------------------------------------------------
# ErrorInfo
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ErrorInfo:
    """Information about an error that occurred during a step.

    Attributes:
        message: The error message.
        traceback: The full traceback as a string.
        exception_type: The exception class name (e.g. ``"AssertionError"``).
    """

    message: str = ""
    traceback: str = ""
    exception_type: str = ""


# ---------------------------------------------------------------------------
# Attachment
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Attachment:
    """A file or blob attached to a step or scenario.

    Attributes:
        name: A short label for the attachment.
        mime_type: MIME type (e.g. ``"image/png"``).
        data_base64: Binary content encoded as base64.
        text: Text content for text-based attachments (JSON, logs).
        step_name: Name of the step that owns the attachment.
        scenario_name: Name of the scenario that owns the attachment.
        feature_name: Name of the feature that owns the attachment.
    """

    name: str = ""
    mime_type: str = "application/octet-stream"
    data_base64: str = ""
    text: str | None = None
    step_name: str = ""
    scenario_name: str = ""
    feature_name: str = ""

    @property
    def is_image(self) -> bool:
        """Return ``True`` if the MIME type indicates an image."""
        return self.mime_type.startswith("image/")

    @property
    def is_text(self) -> bool:
        """Return ``True`` if the MIME type indicates text or text content is set."""
        return self.mime_type.startswith("text/") or self.text is not None

    @property
    def is_screenshot(self) -> bool:
        """Return ``True`` if the attachment is a PNG image named as a screenshot."""
        return self.is_image and "screenshot" in self.name.lower()


# ---------------------------------------------------------------------------
# Step
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Step:
    """A single Gherkin step within a scenario.

    Attributes:
        keyword: The step keyword (``"Given"``, ``"When"``, etc.).
        name: The step text.
        status: Canonical status (``"passed"``, ``"failed"``, etc.).
        duration: Execution time in seconds.
        location: Source location (e.g. ``"features/foo.feature:12"``).
        text: Docstring content, if any.
        error: Error information, if the step failed.
        attachments: List of attachments for this step.
        logs: List of log lines for this step.
    """

    keyword: str = ""
    name: str = ""
    status: str = "untested"
    duration: float = 0.0
    location: str = ""
    text: str | None = None
    error: ErrorInfo | None = None
    attachments: list[Attachment] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Background:
    """A Gherkin background section shared by all scenarios in a feature.

    Attributes:
        name: The background label (usually ``"Background"``).
        steps: The background steps.
    """

    name: str = ""
    steps: list[Step] = field(default_factory=list)


# ---------------------------------------------------------------------------
# ScenarioResult
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ScenarioResult:
    """A scenario or scenario-outline example.

    Attributes:
        name: The scenario name.
        status: Canonical status.
        duration: Execution time in seconds.
        tags: Scenario tags.
        location: Source location.
        feature_name: Name of the parent feature.
        rule_name: Name of the Rule the scenario belongs to, if any.
        is_outline: Whether this is a scenario outline example.
        outline_name: The outline name, if applicable.
        steps: The scenario steps.
        background: Shared background steps, if any.
        description: Scenario description text.
        error: Error information, if the scenario failed.
    """

    name: str = ""
    status: str = "untested"
    duration: float = 0.0
    tags: list[str] = field(default_factory=list)
    location: str = ""
    feature_name: str = ""
    rule_name: str = ""
    is_outline: bool = False
    outline_name: str = ""
    steps: list[Step] = field(default_factory=list)
    background: Background | None = None
    description: str = ""
    error: ErrorInfo | None = None


# ---------------------------------------------------------------------------
# FeatureSummary
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class FeatureSummary:
    """A Gherkin feature and its scenarios.

    Attributes:
        name: The feature name.
        description: Feature description text.
        status: Derived status (worst of all scenarios).
        duration: Total execution time in seconds.
        tags: Feature tags.
        location: Source location.
        scenarios: Scenarios belonging to this feature.
        background: Shared background, if any.
    """

    name: str = ""
    description: str = ""
    status: str = "untested"
    duration: float = 0.0
    tags: list[str] = field(default_factory=list)
    location: str = ""
    scenarios: list[ScenarioResult] = field(default_factory=list)
    background: Background | None = None

    @property
    def total_scenarios(self) -> int:
        """Return the total number of scenarios."""
        return len(self.scenarios)

    @property
    def passed(self) -> int:
        """Return the number of passed scenarios."""
        return sum(1 for s in self.scenarios if s.status == STATUS_PASSED)

    @property
    def failed(self) -> int:
        """Return the number of failed scenarios."""
        return sum(1 for s in self.scenarios if s.status == STATUS_FAILED)

    @property
    def skipped(self) -> int:
        """Return the number of skipped scenarios."""
        return sum(1 for s in self.scenarios if s.status == STATUS_SKIPPED)

    @property
    def undefined(self) -> int:
        """Return the number of undefined scenarios."""
        return sum(1 for s in self.scenarios if s.status == STATUS_UNDEFINED)

    @property
    def pass_rate(self) -> float:
        """Return the pass rate as a fraction in ``[0, 1]``."""
        total = self.total_scenarios
        if total == 0:
            return 0.0
        return self.passed / total

    def derive_status(self) -> str:
        """Derive the feature status from its scenarios.

        Returns:
            ``"failed"`` if any scenario failed, ``"undefined"`` if any is
            undefined (but none failed), ``"skipped"`` if any is skipped
            (and none failed/undefined), ``"passed"`` if all passed,
            ``"untested"`` if no scenarios.
        """
        if not self.scenarios:
            return "untested"
        statuses = {s.status for s in self.scenarios}
        if STATUS_FAILED in statuses:
            return STATUS_FAILED
        if STATUS_UNDEFINED in statuses:
            return STATUS_UNDEFINED
        if STATUS_SKIPPED in statuses:
            return STATUS_SKIPPED
        return STATUS_PASSED


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Environment:
    """Host and runtime metadata.

    Attributes:
        python_version: Python interpreter version.
        behave_version: Behave version, if available.
        platform: Operating system platform.
        hostname: Machine hostname.
        cwd: Current working directory.
        command: The command line that launched the run.
        user: The user executing the run.
        cpu_count: Number of CPU cores.
        git_branch: Current Git branch, if any.
        git_commit: Current Git commit hash, if any.
    """

    python_version: str = ""
    behave_version: str = ""
    platform: str = ""
    hostname: str = ""
    cwd: str = ""
    command: str = ""
    user: str = ""
    cpu_count: int = 0
    git_branch: str = ""
    git_commit: str = ""

    @classmethod
    def capture(cls) -> Environment:
        """Capture the current runtime environment information."""
        import getpass
        import os
        import platform
        import subprocess
        import sys

        behave_version = ""
        try:
            from importlib.metadata import version

            behave_version = version("behave")
        except Exception:
            pass

        git_branch = ""
        git_commit = ""
        try:
            branch = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
                timeout=2,
            )
            git_branch = branch.stdout.strip()
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
                timeout=2,
            )
            git_commit = commit.stdout.strip()
        except Exception:
            pass

        return cls(
            python_version=platform.python_version(),
            behave_version=behave_version,
            platform=platform.platform(),
            hostname=platform.node(),
            cwd=os.getcwd(),
            command=" ".join(sys.argv),
            user=getpass.getuser(),
            cpu_count=os.cpu_count() or 0,
            git_branch=git_branch,
            git_commit=git_commit,
        )


# ---------------------------------------------------------------------------
# RunSummary
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class RunSummary:
    """Root of the report tree representing a full Behave run.

    Attributes:
        run_id: Unique identifier for the run.
        title: Report title.
        project_name: Project name.
        start_time: ISO 8601 start timestamp.
        end_time: ISO 8601 end timestamp.
        duration: Total execution time in seconds.
        features: Features in this run.
        environment: Runtime environment metadata.
    """

    run_id: str = ""
    title: str = "Behave Modern Report"
    project_name: str = ""
    start_time: str = ""
    end_time: str = ""
    duration: float = 0.0
    features: list[FeatureSummary] = field(default_factory=list)
    environment: Environment = field(default_factory=Environment)

    @property
    def total_features(self) -> int:
        """Return the total number of features."""
        return len(self.features)

    @property
    def total_scenarios(self) -> int:
        """Return the total number of scenarios across all features."""
        return sum(f.total_scenarios for f in self.features)

    @property
    def passed(self) -> int:
        """Return the total number of passed scenarios."""
        return sum(f.passed for f in self.features)

    @property
    def failed(self) -> int:
        """Return the total number of failed scenarios."""
        return sum(f.failed for f in self.features)

    @property
    def skipped(self) -> int:
        """Return the total number of skipped scenarios."""
        return sum(f.skipped for f in self.features)

    @property
    def undefined(self) -> int:
        """Return the total number of undefined scenarios."""
        return sum(f.undefined for f in self.features)

    @property
    def pass_rate(self) -> float:
        """Return the overall pass rate as a fraction in ``[0, 1]``."""
        total = self.total_scenarios
        if total == 0:
            return 0.0
        return self.passed / total

    @property
    def status(self) -> str:
        """Return the overall run status.

        Returns:
            ``"failed"`` if any scenario failed, ``"undefined"`` if any is
            undefined, ``"skipped"`` if all skipped, ``"passed"`` if all
            passed, ``"untested"`` if no scenarios.
        """
        if not self.features:
            return "untested"
        statuses = {f.derive_status() for f in self.features}
        if STATUS_FAILED in statuses:
            return STATUS_FAILED
        if STATUS_UNDEFINED in statuses:
            return STATUS_UNDEFINED
        if statuses == {STATUS_SKIPPED}:
            return STATUS_SKIPPED
        return STATUS_PASSED


# ---------------------------------------------------------------------------
# ReportOptions
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ReportOptions:
    """Resolved formatter options.

    Loaded from Behave ``userdata`` using the ``bmfr.*`` prefix and optional
    ``bmfr.<format>.*`` overrides. Each option resolves in order:
    ``bmfr.<format>.<key>`` → ``bmfr.<key>`` → default.

    Attributes:
        only_failed: If True, only include failed scenarios in the report.
        template: Path to a custom Jinja2 template.
        logo: Path to a logo image file.
        logo_b64: Base64-encoded logo data (resolved at runtime).
        primary_color: Hex color string for branding.
        title: Report title.
        project_name: Project name.
        include_attachments: Whether to embed attachments in the report.
        max_traceback_lines: Maximum number of traceback lines to show.
        attachment_max_size_kb: Max attachment size in KB.
        txt_width: Line width for TXT reports.
        txt_ascii: If True, use ASCII-only characters in TXT output.
        pdf_engine: PDF rendering engine (``"weasyprint"`` or ``"reportlab"``).
    """

    only_failed: bool = False
    template: str = ""
    logo: str = ""
    logo_b64: str = ""
    primary_color: str = "#2563EB"
    title: str = "Behave Modern Report"
    project_name: str = ""
    include_attachments: bool = True
    max_traceback_lines: int = 50
    attachment_max_size_kb: int = 512
    txt_width: int = 100
    txt_ascii: bool = False
    pdf_engine: str = "weasyprint"

    @classmethod
    def from_dict(
        cls,
        data: dict[str, str],
        format_key: str = "",
    ) -> ReportOptions:
        """Build ``ReportOptions`` from a flat dictionary of user options.

        The dictionary keys are expected to use the ``bmfr.*`` prefix.
        Format-specific overrides (``bmfr.<format>.<key>``) take precedence
        over global keys (``bmfr.<key>``).

        Args:
            data: A flat dict such as Behave's ``config.userdata``.
            format_key: Optional format name (``"pdf"``, ``"docx"``, ``"txt"``)
                for per-format overrides.

        Returns:
            A populated ``ReportOptions`` instance.
        """
        prefix = "bmfr."
        fmt_prefix = f"bmfr.{format_key}." if format_key else ""

        def resolve(key: str) -> str | None:
            if fmt_prefix:
                fmt_val = data.get(f"{fmt_prefix}{key}")
                if fmt_val is not None:
                    return fmt_val
            return data.get(f"{prefix}{key}")

        return cls(
            only_failed=parse_bool(resolve("only_failed")),
            template=resolve("template") or "",
            logo=resolve("logo") or "",
            primary_color=parse_color(resolve("primary_color")),
            title=resolve("title") or "Behave Modern Report",
            project_name=resolve("project_name") or "",
            include_attachments=parse_bool(resolve("include_attachments")),
            max_traceback_lines=parse_int(resolve("max_traceback_lines"), 50),
            attachment_max_size_kb=parse_int(resolve("attachment_max_size_kb"), 512),
            txt_width=parse_int(resolve("txt_width"), 100),
            txt_ascii=parse_bool(resolve("txt_ascii")),
            pdf_engine=parse_pdf_engine(resolve("pdf_engine")),
        )


__all__ = [
    "Attachment",
    "Background",
    "Environment",
    "ErrorInfo",
    "FeatureSummary",
    "ReportOptions",
    "RunSummary",
    "ScenarioResult",
    "Step",
]
