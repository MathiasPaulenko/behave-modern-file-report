"""Collector for gathering Behave execution events into a RunSummary.

The collector is the only module that interacts with Behave types. It accepts
``SimpleNamespace`` or any duck-typed object with the expected attributes, so
it can be tested without importing ``behave``.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Any

from behave_modern_file_reports.models import (
    Background,
    Environment,
    ErrorInfo,
    FeatureSummary,
    RunSummary,
    ScenarioResult,
    Step,
)
from behave_modern_file_reports.utils import (
    STATUS_FAILED,
    STATUS_PASSED,
    STATUS_SKIPPED,
    STATUS_UNDEFINED,
    generate_id,
    normalize_status,
    now_iso,
    safe_str,
)


class Collector:
    """Accumulates Behave events into a ``RunSummary`` tree.

    The collector follows the Behave formatter lifecycle:
    ``start_feature`` → ``start_scenario`` → ``end_scenario`` → ``end_feature``
    → ``finalize``.
    """

    def __init__(self, max_traceback_lines: int = 50) -> None:
        """Initialize an empty collector.

        Args:
            max_traceback_lines: Maximum number of traceback lines to retain
                when extracting errors from failed steps.
        """
        self._run_id: str = generate_id("run")
        self._start_time: str = now_iso()
        self._start_monotonic: float = time.monotonic()
        self._features: list[FeatureSummary] = []
        self._current_feature: FeatureSummary | None = None
        self._current_scenario: ScenarioResult | None = None
        self._step_queue: deque[Step] = deque()
        self._current_background: Background | None = None
        self._scenario_start: float = 0.0
        self._feature_start: float = 0.0
        self._max_traceback_lines: int = max_traceback_lines
        self._in_background: bool = False

    def start_feature(self, behave_feature: Any) -> None:
        """Begin tracking a feature.

        Args:
            behave_feature: A Behave ``Feature`` object (or mock) with
                ``name``, ``description``, ``tags``, and ``location``.
        """
        tags = list(getattr(behave_feature, "tags", []) or [])
        location = str(getattr(behave_feature, "location", ""))
        description = safe_description(behave_feature)

        self._current_feature = FeatureSummary(
            name=getattr(behave_feature, "name", "") or "",
            description=description,
            tags=tags,
            location=location,
        )
        self._feature_start = time.monotonic()

    def start_background(self, behave_background: Any) -> None:
        """Begin tracking a feature's background section.

        Args:
            behave_background: A Behave ``Background`` object (or mock) with
                ``name`` and optionally ``location``.
        """
        name = safe_str(getattr(behave_background, "name", "")) or "Background"
        self._current_background = Background(name=name)
        self._in_background = True

    def end_background(self) -> None:
        """Finalize the current background and attach it to the feature."""
        if self._current_background is not None and self._current_feature is not None:
            self._current_feature.background = self._current_background
        self._current_background = None
        self._in_background = False

    def start_scenario(self, behave_scenario: Any) -> None:
        """Begin tracking a scenario.

        Args:
            behave_scenario: A Behave ``Scenario`` object (or mock) with
                ``name``, ``tags``, ``location``, and ``feature``.
        """
        tags = list(getattr(behave_scenario, "tags", []) or [])
        location = str(getattr(behave_scenario, "location", ""))
        feature_name = ""
        feature = getattr(behave_scenario, "feature", None)
        if feature is not None:
            feature_name = getattr(feature, "name", "") or ""

        is_outline = bool(getattr(behave_scenario, "is_outline", False))
        outline_name = ""
        if is_outline:
            outline_name = getattr(behave_scenario, "name", "") or ""

        rule_name = ""
        rule = getattr(behave_scenario, "rule", None)
        if rule is not None:
            rule_name = getattr(rule, "name", "") or ""

        self._current_scenario = ScenarioResult(
            name=getattr(behave_scenario, "name", "") or "",
            tags=tags,
            location=location,
            feature_name=feature_name,
            rule_name=rule_name,
            is_outline=is_outline,
            outline_name=outline_name,
            description=safe_description(behave_scenario),
        )
        if self._current_feature is not None and self._current_feature.background is not None:
            self._current_scenario.background = self._current_feature.background
        self._scenario_start = time.monotonic()

    def start_step(self, behave_step: Any) -> None:
        """Queue a step for tracking within the current scenario.

        Behave announces all steps via ``step()`` before executing them
        via ``result()``, so steps are queued and matched in FIFO order.

        Args:
            behave_step: A Behave ``Step`` object (or mock) with ``keyword``,
                ``name``, and ``location``.
        """
        keyword = safe_str(getattr(behave_step, "keyword", ""))
        name = safe_str(getattr(behave_step, "name", ""))
        location = str(getattr(behave_step, "location", ""))

        text = getattr(behave_step, "text", None)
        if text is not None:
            text = safe_str(text)

        self._step_queue.append(
            Step(
                keyword=keyword,
                name=name,
                location=location,
                text=text,
            )
        )

    def end_step(self, behave_step: Any) -> None:
        """Finalize the next queued step and append it to the current scenario or background.

        Args:
            behave_step: A Behave ``Step`` object (or mock) with ``status``
                and optionally ``duration``.
        """
        if not self._step_queue:
            return
        if not self._in_background and self._current_scenario is None:
            return
        if (
            self._in_background
            and self._current_background is None
            and self._current_scenario is None
        ):
            return

        current_step = self._step_queue.popleft()

        raw_status = getattr(behave_step, "status", None)
        if raw_status is not None and not isinstance(raw_status, str):
            raw_status = getattr(raw_status, "name", str(raw_status))
        current_step.status = normalize_status(raw_status)

        duration = getattr(behave_step, "duration", None)
        if duration is not None:
            current_step.duration = float(duration)
        else:
            current_step.duration = 0.0

        if current_step.status == STATUS_FAILED:
            current_step.error = _extract_error(behave_step, self._max_traceback_lines)

        if self._in_background and self._current_background is not None:
            self._current_background.steps.append(current_step)
        elif self._current_scenario is not None:  # pragma: no cover: guarded above
            self._current_scenario.steps.append(current_step)

    def end_scenario(self) -> None:
        """Finalize the current scenario and append it to the current feature."""
        if self._current_scenario is None or self._current_feature is None:
            self._step_queue.clear()
            return

        # Finalize any remaining queued steps as skipped
        while self._step_queue:
            step = self._step_queue.popleft()
            step.status = STATUS_SKIPPED
            self._current_scenario.steps.append(step)

        self._current_scenario.duration = time.monotonic() - self._scenario_start
        self._current_scenario.status = _derive_scenario_status(self._current_scenario)
        if self._current_scenario.status == STATUS_FAILED:
            self._current_scenario.error = _first_failed_error(self._current_scenario)
        self._current_feature.scenarios.append(self._current_scenario)
        self._current_scenario = None

    def end_feature(self) -> None:
        """Finalize the current feature and append it to the run."""
        if self._current_feature is None:
            return

        self._current_feature.duration = time.monotonic() - self._feature_start
        self._features.append(self._current_feature)
        self._current_feature = None

    def finalize(self) -> RunSummary:
        """Finalize the run and return the complete ``RunSummary``.

        Returns:
            The fully populated ``RunSummary`` with all features, timing,
            and a generated run ID.
        """
        end_time = now_iso()
        duration = time.monotonic() - self._start_monotonic

        return RunSummary(
            run_id=self._run_id,
            start_time=self._start_time,
            end_time=end_time,
            duration=duration,
            features=list(self._features),
            environment=Environment.capture(),
        )


def _extract_error(behave_step: Any, max_traceback_lines: int) -> ErrorInfo | None:
    """Extract error information from a failed Behave step.

    Behave stores the exception in ``step.error`` or ``step.exception``.
    The traceback may be in ``step.error_message`` or derived from the
    exception itself.

    Args:
        behave_step: A Behave ``Step`` object (or mock) that failed.
        max_traceback_lines: Maximum number of traceback lines to retain.
            Lines beyond this limit are truncated with a marker.

    Returns:
        An ``ErrorInfo`` instance if error information is found, ``None`` otherwise.
    """
    exception = getattr(behave_step, "error", None)
    if exception is None:
        exception = getattr(behave_step, "exception", None)
    if exception is None:
        return None

    message = safe_str(exception)
    exception_type = type(exception).__name__

    traceback_str = ""
    error_message = getattr(behave_step, "error_message", None)
    if error_message is not None:
        traceback_str = safe_str(error_message)
    elif isinstance(exception, BaseException):
        tb_lines = _format_traceback(exception)
        traceback_str = "\n".join(tb_lines)

    if max_traceback_lines > 0:
        lines = traceback_str.splitlines()
        if len(lines) > max_traceback_lines:
            lines = lines[:max_traceback_lines]
            lines.append(f"... ({len(lines)} lines truncated)")
            traceback_str = "\n".join(lines)

    return ErrorInfo(
        message=message,
        traceback=traceback_str,
        exception_type=exception_type,
    )


def _format_traceback(exception: BaseException) -> list[str]:
    """Format an exception's traceback as a list of lines.

    Args:
        exception: The exception to format.

    Returns:
        A list of traceback lines.
    """
    import traceback as tb_module

    return tb_module.format_exception(type(exception), exception, exception.__traceback__)


def _first_failed_error(scenario: ScenarioResult) -> ErrorInfo | None:
    """Return the error from the first failed step in a scenario.

    Checks both background and scenario steps.

    Args:
        scenario: The scenario to search for a failed step.

    Returns:
        The ``ErrorInfo`` from the first failed step, or ``None``.
    """
    all_steps: list[Step] = []
    if scenario.background is not None:
        all_steps.extend(scenario.background.steps)
    all_steps.extend(scenario.steps)
    for step in all_steps:
        if step.status == STATUS_FAILED and step.error is not None:
            return step.error
    return None


def _derive_scenario_status(scenario: ScenarioResult) -> str:
    """Derive the scenario status from its steps (including background).

    Args:
        scenario: The scenario whose status should be derived.

    Returns:
        ``"failed"`` if any step failed, ``"undefined"`` if any step is
        undefined, ``"skipped"`` if any step is skipped (and none failed),
        ``"passed"`` if all steps passed, ``"untested"`` if no steps.
    """
    all_steps: list[Step] = []
    if scenario.background is not None:
        all_steps.extend(scenario.background.steps)
    all_steps.extend(scenario.steps)
    if not all_steps:
        return STATUS_UNDEFINED
    statuses = {s.status for s in all_steps}
    if STATUS_FAILED in statuses:
        return STATUS_FAILED
    if STATUS_UNDEFINED in statuses:
        return STATUS_UNDEFINED
    if STATUS_SKIPPED in statuses:
        return STATUS_SKIPPED
    return STATUS_PASSED


def safe_description(obj: Any) -> str:
    """Extract a description string from a Behave feature or scenario.

    Args:
        obj: An object with a ``description`` attribute (``str`` or ``list``).

    Returns:
        The description as a single string, or empty string if absent.
    """
    desc = getattr(obj, "description", None)
    if desc is None:
        return ""
    if isinstance(desc, list):
        return "\n".join(str(line) for line in desc)
    return str(desc)


__all__ = ["Collector"]
