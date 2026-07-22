"""Tests for behave_modern_file_reports.collector."""

from __future__ import annotations

import time
from types import SimpleNamespace

from behave_modern_file_reports.collector import Collector


def _mock_feature(
    name: str = "Login",
    tags: list[str] | None = None,
    location: str = "features/login.feature:1",
    description: str | list[str] | None = None,
) -> SimpleNamespace:
    """Create a mock Behave feature."""
    return SimpleNamespace(
        name=name,
        tags=tags or [],
        location=location,
        description=description,
    )


def _mock_scenario(
    name: str = "Login succeeds",
    tags: list[str] | None = None,
    location: str = "features/login.feature:8",
    feature: SimpleNamespace | None = None,
    is_outline: bool = False,
    rule: SimpleNamespace | None = None,
    description: str | list[str] | None = None,
) -> SimpleNamespace:
    """Create a mock Behave scenario."""
    return SimpleNamespace(
        name=name,
        tags=tags or [],
        location=location,
        feature=feature,
        is_outline=is_outline,
        rule=rule,
        description=description,
    )


# ---------------------------------------------------------------------------
# start_feature / end_feature
# ---------------------------------------------------------------------------


def test_start_feature_creates_tracker() -> None:
    """start_feature creates a current feature tracker."""
    col = Collector()
    feat = _mock_feature(name="My Feature", tags=["smoke"])
    col.start_feature(feat)
    assert col._current_feature is not None
    assert col._current_feature.name == "My Feature"
    assert col._current_feature.tags == ["smoke"]


def test_end_feature_appends_to_run() -> None:
    """end_feature appends the feature to the run."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.end_feature()
    assert col._current_feature is None
    assert len(col._features) == 1
    assert col._features[0].name == "F1"


def test_end_feature_calculates_duration() -> None:
    """end_feature calculates the feature duration."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    time.sleep(0.05)
    col.end_feature()
    assert col._features[0].duration > 0.0


def test_end_feature_without_start_is_noop() -> None:
    """end_feature without a current feature is a no-op."""
    col = Collector()
    col.end_feature()
    assert len(col._features) == 0


def test_end_feature_derives_status_from_scenarios() -> None:
    """end_feature sets the feature status based on its scenarios."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="step 1", status="failed"))
    col.end_step(_mock_step(name="step 1", status="failed"))
    col.end_scenario()
    col.end_feature()
    assert col._features[0].status == "failed"


def test_start_feature_with_description_string() -> None:
    """start_feature stores a string description."""
    col = Collector()
    col.start_feature(_mock_feature(description="A feature description."))
    assert col._current_feature is not None
    assert col._current_feature.description == "A feature description."


def test_start_feature_with_description_list() -> None:
    """start_feature joins a list description."""
    col = Collector()
    col.start_feature(_mock_feature(description=["Line 1", "Line 2"]))
    assert col._current_feature is not None
    assert col._current_feature.description == "Line 1\nLine 2"


def test_start_feature_no_description() -> None:
    """start_feature handles missing description."""
    col = Collector()
    col.start_feature(_mock_feature(description=None))
    assert col._current_feature is not None
    assert col._current_feature.description == ""


# ---------------------------------------------------------------------------
# start_scenario / end_scenario
# ---------------------------------------------------------------------------


def test_start_scenario_creates_tracker() -> None:
    """start_scenario creates a current scenario tracker."""
    col = Collector()
    mock_feat = _mock_feature(name="Login")
    col.start_feature(mock_feat)
    col.start_scenario(_mock_scenario(name="My Scn", feature=mock_feat, tags=["auth"]))
    assert col._current_scenario is not None
    assert col._current_scenario.name == "My Scn"
    assert col._current_scenario.tags == ["auth"]
    assert col._current_scenario.feature_name == "Login"


def test_end_scenario_appends_to_feature() -> None:
    """end_scenario appends the scenario to the current feature."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.end_scenario()
    assert col._current_scenario is None
    assert len(col._features) == 0  # feature not ended yet
    assert col._current_feature is not None
    assert len(col._current_feature.scenarios) == 1
    assert col._current_feature.scenarios[0].name == "S1"


def test_end_scenario_calculates_duration() -> None:
    """end_scenario calculates the scenario duration."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    time.sleep(0.05)
    col.end_scenario()
    assert col._current_feature is not None
    assert col._current_feature.scenarios[0].duration > 0.0


def test_end_scenario_without_start_is_noop() -> None:
    """end_scenario without a current scenario is a no-op."""
    col = Collector()
    col.end_scenario()
    assert col._current_scenario is None


def test_start_scenario_outline() -> None:
    """start_scenario captures is_outline and outline_name."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="Outline 1", is_outline=True))
    assert col._current_scenario is not None
    assert col._current_scenario.is_outline is True
    assert col._current_scenario.outline_name == "Outline 1"


def test_start_scenario_with_rule() -> None:
    """start_scenario captures the rule name."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    rule = SimpleNamespace(name="My Rule")
    col.start_scenario(_mock_scenario(name="S1", rule=rule))
    assert col._current_scenario is not None
    assert col._current_scenario.rule_name == "My Rule"


# ---------------------------------------------------------------------------
# finalize
# ---------------------------------------------------------------------------


def test_finalize_returns_run_summary() -> None:
    """finalize returns a RunSummary with all features."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.end_scenario()
    col.end_feature()
    run = col.finalize()
    assert run.run_id.startswith("run_")
    assert len(run.features) == 1
    assert run.features[0].name == "F1"
    assert run.features[0].scenarios[0].name == "S1"
    assert run.duration > 0.0
    assert run.start_time != ""
    assert run.end_time != ""


def test_finalize_empty_run() -> None:
    """finalize with no features returns an empty RunSummary."""
    col = Collector()
    run = col.finalize()
    assert len(run.features) == 0
    assert run.total_features == 0


def test_finalize_multiple_features() -> None:
    """finalize aggregates multiple features."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.end_scenario()
    col.end_feature()
    col.start_feature(_mock_feature(name="F2"))
    col.start_scenario(_mock_scenario(name="S2"))
    col.end_scenario()
    col.end_feature()
    run = col.finalize()
    assert len(run.features) == 2
    assert run.features[0].name == "F1"
    assert run.features[1].name == "F2"
    assert run.total_scenarios == 2


# ---------------------------------------------------------------------------
# start_step / end_step
# ---------------------------------------------------------------------------


def _mock_step(
    keyword: str = "Given",
    name: str = "a step",
    status: str = "passed",
    location: str = "features/test.feature:5",
    duration: float | None = 0.01,
    text: str | None = None,
) -> SimpleNamespace:
    """Create a mock Behave step."""
    return SimpleNamespace(
        keyword=keyword,
        name=name,
        status=status,
        location=location,
        duration=duration,
        text=text,
    )


def test_start_step_creates_tracker() -> None:
    """start_step queues a step tracker."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(keyword="When", name="click button"))
    assert len(col._step_queue) == 1
    assert col._step_queue[0].keyword == "When"
    assert col._step_queue[0].name == "click button"
    assert col._step_queue[0].status == "untested"


def test_peek_current_step() -> None:
    """peek_current_step returns the queued step without removing it."""
    col = Collector()
    assert col.peek_current_step() is None
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="step 1"))
    current = col.peek_current_step()
    assert current is not None
    assert current.name == "step 1"
    assert len(col._step_queue) == 1


def test_end_step_appends_to_scenario() -> None:
    """end_step appends the step to the current scenario."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="step 1"))
    col.end_step(_mock_step(name="step 1", status="passed"))
    assert len(col._step_queue) == 0
    assert col._current_scenario is not None
    assert len(col._current_scenario.steps) == 1
    assert col._current_scenario.steps[0].status == "passed"


def test_end_step_without_start_is_noop() -> None:
    """end_step without a queued step is a no-op."""
    col = Collector()
    col.end_step(_mock_step(status="passed"))
    assert len(col._step_queue) == 0


def test_end_step_without_scenario_or_background_is_noop() -> None:
    """end_step with a step but no scenario or background is a no-op."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_step(_mock_step(name="orphan step"))
    col.end_step(_mock_step(name="orphan step", status="passed"))
    assert len(col._step_queue) == 1  # step remains queued, not finalized


def test_end_step_in_background_without_background_object_falls_to_scenario() -> None:
    """end_step falls to scenario when in_background but no background object."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col._in_background = True
    col._current_background = None
    col.start_step(_mock_step(name="step 1"))
    col.end_step(_mock_step(name="step 1", status="passed"))
    assert col._current_scenario is not None
    assert len(col._current_scenario.steps) == 1
    col._in_background = False


def test_end_step_in_background_no_background_no_scenario_discards_step() -> None:
    """end_step in background mode with no background and no scenario does not finalize."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col._in_background = True
    col._current_background = None
    col.start_step(_mock_step(name="orphan step"))
    col.end_step(_mock_step(name="orphan step", status="passed"))
    assert len(col._step_queue) == 1  # step remains queued
    col._in_background = False


def test_end_step_in_background_with_background_no_scenario() -> None:
    """end_step in background mode with background but no scenario appends to background."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_background(_mock_background())
    col._in_background = True
    col.start_step(_mock_step(name="bg step"))
    col.end_step(_mock_step(name="bg step", status="passed"))
    assert col._current_background is not None
    assert len(col._current_background.steps) == 1
    assert col._current_background.steps[0].status == "passed"
    col._in_background = False


def test_end_step_calculates_duration_from_monotonic() -> None:
    """end_step uses 0.0 duration when not provided (queue-based, no per-step timer)."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="step 1"))
    col.end_step(SimpleNamespace(
        keyword="Given", name="step 1", status="passed",
        location="", duration=None, text=None,
    ))
    assert col._current_scenario is not None
    assert col._current_scenario.steps[0].duration == 0.0


def test_end_step_uses_provided_duration() -> None:
    """end_step uses the duration from the behave step when provided."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="step 1"))
    col.end_step(_mock_step(name="step 1", status="passed", duration=0.123))
    assert col._current_scenario is not None
    assert col._current_scenario.steps[0].duration == 0.123


def test_start_step_captures_text() -> None:
    """start_step captures docstring text."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="step 1", text="some docstring"))
    assert len(col._step_queue) == 1
    assert col._step_queue[0].text == "some docstring"


def test_end_step_normalizes_status() -> None:
    """end_step normalizes non-string status values."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="step 1"))
    col.end_step(SimpleNamespace(
        keyword="Given", name="step 1", status="passed",
        location="", duration=0.01, text=None,
    ))
    assert col._current_scenario is not None
    assert col._current_scenario.steps[0].status == "passed"


def test_end_step_normalizes_non_string_status() -> None:
    """end_step converts non-string status (e.g. Behave's Status enum) to string."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="step 1"))
    col.end_step(SimpleNamespace(
        keyword="Given", name="step 1", status=42,
        location="", duration=0.01, text=None,
    ))
    assert col._current_scenario is not None
    assert col._current_scenario.steps[0].status == "untested"


# ---------------------------------------------------------------------------
# Status derivation
# ---------------------------------------------------------------------------


def test_scenario_all_steps_passed() -> None:
    """A scenario with all passed steps derives passed status."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="s1"))
    col.end_step(_mock_step(name="s1", status="passed"))
    col.start_step(_mock_step(name="s2"))
    col.end_step(_mock_step(name="s2", status="passed"))
    col.end_scenario()
    assert col._current_feature is not None
    assert col._current_feature.scenarios[0].status == "passed"


def test_end_scenario_remaining_queued_steps_marked_skipped() -> None:
    """end_scenario marks remaining queued steps as skipped."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="s1"))
    col.start_step(_mock_step(name="s2"))
    col.start_step(_mock_step(name="s3"))
    col.end_step(_mock_step(name="s1", status="passed"))
    # s2 and s3 remain queued — simulating a failed step that stops execution
    col.end_scenario()
    assert col._current_feature is not None
    scenario = col._current_feature.scenarios[0]
    assert len(scenario.steps) == 3
    assert scenario.steps[0].status == "passed"
    assert scenario.steps[1].status == "skipped"
    assert scenario.steps[2].status == "skipped"


def test_end_scenario_clears_queue_when_no_scenario() -> None:
    """end_scenario clears the step queue even when no scenario is active."""
    col = Collector()
    col.start_step(_mock_step(name="orphan"))
    col.end_scenario()
    assert len(col._step_queue) == 0


def test_scenario_one_step_failed() -> None:
    """A scenario with one failed step derives failed status."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="s1"))
    col.end_step(_mock_step(name="s1", status="passed"))
    col.start_step(_mock_step(name="s2"))
    col.end_step(_mock_step(name="s2", status="failed"))
    col.end_scenario()
    assert col._current_feature is not None
    assert col._current_feature.scenarios[0].status == "failed"


def test_scenario_all_steps_skipped() -> None:
    """A scenario with all skipped steps derives skipped status."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="s1"))
    col.end_step(_mock_step(name="s1", status="skipped"))
    col.start_step(_mock_step(name="s2"))
    col.end_step(_mock_step(name="s2", status="skipped"))
    col.end_scenario()
    assert col._current_feature is not None
    assert col._current_feature.scenarios[0].status == "skipped"


def test_scenario_undefined_step() -> None:
    """A scenario with an undefined step derives undefined status."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="s1"))
    col.end_step(_mock_step(name="s1", status="passed"))
    col.start_step(_mock_step(name="s2"))
    col.end_step(_mock_step(name="s2", status="undefined"))
    col.end_scenario()
    assert col._current_feature is not None
    assert col._current_feature.scenarios[0].status == "undefined"


def test_scenario_no_steps_is_untested() -> None:
    """A scenario with no steps derives untested status."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.end_scenario()
    assert col._current_feature is not None
    assert col._current_feature.scenarios[0].status == "untested"


def test_scenario_untested_steps_derive_untested() -> None:
    """A scenario with only untested steps derives untested status."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="s1"))
    col.end_step(_mock_step(name="s1", status="untested"))
    col.end_scenario()
    assert col._current_feature is not None
    assert col._current_feature.scenarios[0].status == "untested"


def test_scenario_failed_takes_precedence_over_undefined() -> None:
    """Failed status takes precedence over undefined."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="s1"))
    col.end_step(_mock_step(name="s1", status="undefined"))
    col.start_step(_mock_step(name="s2"))
    col.end_step(_mock_step(name="s2", status="failed"))
    col.end_scenario()
    assert col._current_feature is not None
    assert col._current_feature.scenarios[0].status == "failed"


def test_scenario_mixed_passed_and_skipped_is_skipped() -> None:
    """A scenario with passed and skipped steps derives skipped status."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="s1"))
    col.end_step(_mock_step(name="s1", status="passed"))
    col.start_step(_mock_step(name="s2"))
    col.end_step(_mock_step(name="s2", status="skipped"))
    col.end_scenario()
    assert col._current_feature is not None
    assert col._current_feature.scenarios[0].status == "skipped"


def test_scenario_mixed_skipped_and_undefined_is_undefined() -> None:
    """A scenario with skipped and undefined steps derives undefined status."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="s1"))
    col.end_step(_mock_step(name="s1", status="skipped"))
    col.start_step(_mock_step(name="s2"))
    col.end_step(_mock_step(name="s2", status="undefined"))
    col.end_scenario()
    assert col._current_feature is not None
    assert col._current_feature.scenarios[0].status == "undefined"


# ---------------------------------------------------------------------------
# Full lifecycle with steps
# ---------------------------------------------------------------------------


def test_full_lifecycle_with_steps() -> None:
    """Full lifecycle: feature → scenario → steps → end → finalize."""
    col = Collector()
    col.start_feature(_mock_feature(name="Login", tags=["auth"]))
    col.start_scenario(_mock_scenario(name="Login succeeds", tags=["smoke"]))
    col.start_step(_mock_step(keyword="Given", name="user is on login page"))
    col.end_step(_mock_step(keyword="Given", name="user is on login page", status="passed"))
    col.start_step(_mock_step(keyword="When", name="user enters credentials"))
    col.end_step(_mock_step(keyword="When", name="user enters credentials", status="passed"))
    col.start_step(_mock_step(keyword="Then", name="dashboard is shown"))
    col.end_step(_mock_step(keyword="Then", name="dashboard is shown", status="passed"))
    col.end_scenario()
    col.end_feature()
    run = col.finalize()
    assert len(run.features) == 1
    feat = run.features[0]
    assert feat.name == "Login"
    assert len(feat.scenarios) == 1
    scn = feat.scenarios[0]
    assert scn.name == "Login succeeds"
    assert scn.status == "passed"
    assert len(scn.steps) == 3
    assert scn.steps[0].keyword == "Given"
    assert scn.steps[2].keyword == "Then"


# ---------------------------------------------------------------------------
# Error extraction
# ---------------------------------------------------------------------------


def _make_failing_step(
    name: str = "failing step",
    error_message: str | None = None,
) -> SimpleNamespace:
    """Create a mock Behave step that fails with an AssertionError."""
    try:
        raise AssertionError(error_message or "assertion failed") from None
    except AssertionError as exc:
        return SimpleNamespace(
            keyword="Then",
            name=name,
            status="failed",
            location="features/test.feature:10",
            duration=0.01,
            text=None,
            error=exc,
            error_message=None,
        )


def test_failed_step_extracts_error() -> None:
    """A failed step with an exception produces ErrorInfo on the Step."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="failing step"))
    col.end_step(_make_failing_step(name="failing step", error_message="boom"))
    assert col._current_scenario is not None
    step = col._current_scenario.steps[0]
    assert step.status == "failed"
    assert step.error is not None
    assert step.error.message == "boom"
    assert step.error.exception_type == "AssertionError"


def test_failed_step_extracts_traceback() -> None:
    """A failed step's ErrorInfo contains a traceback."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="failing step"))
    col.end_step(_make_failing_step(name="failing step"))
    assert col._current_scenario is not None
    step = col._current_scenario.steps[0]
    assert step.error is not None
    assert "Traceback" in step.error.traceback
    assert "AssertionError" in step.error.traceback


def test_failed_step_uses_error_message_attribute() -> None:
    """When behave_step has error_message, it is used as the traceback."""
    exc = AssertionError("original error")
    mock_step = SimpleNamespace(
        keyword="Then",
        name="step",
        status="failed",
        location="features/test.feature:10",
        duration=0.01,
        text=None,
        error=exc,
        error_message="Custom traceback line 1\nCustom traceback line 2",
    )
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="step"))
    col.end_step(mock_step)
    assert col._current_scenario is not None
    step = col._current_scenario.steps[0]
    assert step.error is not None
    assert "Custom traceback line 1" in step.error.traceback
    assert "Custom traceback line 2" in step.error.traceback


def test_failed_step_no_exception_returns_none_error() -> None:
    """A failed step without an exception attribute has no ErrorInfo."""
    mock_step = SimpleNamespace(
        keyword="Then",
        name="step",
        status="failed",
        location="features/test.feature:10",
        duration=0.01,
        text=None,
        error=None,
        exception=None,
        error_message=None,
    )
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="step"))
    col.end_step(mock_step)
    assert col._current_scenario is not None
    step = col._current_scenario.steps[0]
    assert step.status == "failed"
    assert step.error is None


def test_failed_step_uses_exception_attribute() -> None:
    """When step.error is None, falls back to step.exception."""
    exc = ValueError("from exception attr")
    mock_step = SimpleNamespace(
        keyword="Then",
        name="step",
        status="failed",
        location="features/test.feature:10",
        duration=0.01,
        text=None,
        error=None,
        exception=exc,
        error_message=None,
    )
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="step"))
    col.end_step(mock_step)
    assert col._current_scenario is not None
    step = col._current_scenario.steps[0]
    assert step.error is not None
    assert step.error.exception_type == "ValueError"
    assert "from exception attr" in step.error.message


def test_failed_step_non_baseexception_no_traceback() -> None:
    """A non-BaseException error with no error_message has empty traceback."""
    mock_step = SimpleNamespace(
        keyword="Then",
        name="step",
        status="failed",
        location="features/test.feature:10",
        duration=0.01,
        text=None,
        error="some string error",
        exception=None,
        error_message=None,
    )
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="step"))
    col.end_step(mock_step)
    assert col._current_scenario is not None
    step = col._current_scenario.steps[0]
    assert step.error is not None
    assert step.error.message == "some string error"
    assert step.error.traceback == ""
    assert step.error.exception_type == "str"


def test_traceback_truncation() -> None:
    """Traceback is truncated to max_traceback_lines."""
    long_tb = "\n".join(f"line {i}" for i in range(100))
    exc = AssertionError("error")
    mock_step = SimpleNamespace(
        keyword="Then",
        name="step",
        status="failed",
        location="features/test.feature:10",
        duration=0.01,
        text=None,
        error=exc,
        error_message=long_tb,
    )
    col = Collector(max_traceback_lines=10)
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="step"))
    col.end_step(mock_step)
    assert col._current_scenario is not None
    step = col._current_scenario.steps[0]
    assert step.error is not None
    lines = step.error.traceback.splitlines()
    assert len(lines) == 11  # 10 lines + truncation marker
    assert "truncated" in lines[-1]
    assert "90 lines truncated" in lines[-1]


def test_traceback_no_truncation_when_within_limit() -> None:
    """Traceback is not truncated when within the limit."""
    short_tb = "line 1\nline 2\nline 3"
    exc = AssertionError("error")
    mock_step = SimpleNamespace(
        keyword="Then",
        name="step",
        status="failed",
        location="features/test.feature:10",
        duration=0.01,
        text=None,
        error=exc,
        error_message=short_tb,
    )
    col = Collector(max_traceback_lines=50)
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="step"))
    col.end_step(mock_step)
    assert col._current_scenario is not None
    step = col._current_scenario.steps[0]
    assert step.error is not None
    assert step.error.traceback == "line 1\nline 2\nline 3"


def test_traceback_no_truncation_when_limit_zero() -> None:
    """When max_traceback_lines is 0, traceback is not truncated."""
    tb = "line 1\nline 2"
    exc = AssertionError("error")
    mock_step = SimpleNamespace(
        keyword="Then",
        name="step",
        status="failed",
        location="features/test.feature:10",
        duration=0.01,
        text=None,
        error=exc,
        error_message=tb,
    )
    col = Collector(max_traceback_lines=0)
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="step"))
    col.end_step(mock_step)
    assert col._current_scenario is not None
    step = col._current_scenario.steps[0]
    assert step.error is not None
    assert step.error.traceback == "line 1\nline 2"


def test_traceback_not_truncated_by_safe_str() -> None:
    """Long error_message strings are only truncated by max_traceback_lines, not safe_str."""
    long_line = "x" * 1000
    tb = f"{long_line}\nline 2"
    exc = AssertionError("error")
    mock_step = SimpleNamespace(
        keyword="Then",
        name="step",
        status="failed",
        location="f:1",
        duration=0.01,
        text=None,
        error=exc,
        error_message=tb,
    )
    col = Collector(max_traceback_lines=0)
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="step"))
    col.end_step(mock_step)
    assert col._current_scenario is not None
    step = col._current_scenario.steps[0]
    assert step.error is not None
    assert long_line in step.error.traceback
    assert "line 2" in step.error.traceback


def test_scenario_error_populated_from_first_failed_step() -> None:
    """ScenarioResult.error is populated from the first failed step."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="s1"))
    col.end_step(_mock_step(name="s1", status="passed"))
    col.start_step(_mock_step(name="s2"))
    col.end_step(_make_failing_step(name="s2", error_message="first failure"))
    col.start_step(_mock_step(name="s3"))
    col.end_step(_make_failing_step(name="s3", error_message="second failure"))
    col.end_scenario()
    assert col._current_feature is not None
    scn = col._current_feature.scenarios[0]
    assert scn.status == "failed"
    assert scn.error is not None
    assert "first failure" in scn.error.message


def test_passed_step_has_no_error() -> None:
    """A passed step does not have ErrorInfo."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="s1"))
    col.end_step(_mock_step(name="s1", status="passed"))
    assert col._current_scenario is not None
    step = col._current_scenario.steps[0]
    assert step.error is None


def test_scenario_no_failed_step_has_no_error() -> None:
    """A scenario with no failed steps has no error."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(name="s1"))
    col.end_step(_mock_step(name="s1", status="passed"))
    col.end_scenario()
    assert col._current_feature is not None
    scn = col._current_feature.scenarios[0]
    assert scn.status == "passed"
    assert scn.error is None


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------


def _mock_background(name: str = "Background") -> SimpleNamespace:
    """Create a mock Behave background."""
    return SimpleNamespace(name=name, location="features/test.feature:3")


def test_start_background_creates_tracker() -> None:
    """start_background creates a current background tracker."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_background(_mock_background())
    assert col._current_background is not None
    assert col._current_background.name == "Background"
    assert col._in_background is True


def test_end_background_attaches_to_feature() -> None:
    """end_background attaches the background to the current feature."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_background(_mock_background(name="Common setup"))
    col.end_background()
    assert col._current_background is None
    assert col._in_background is False
    assert col._current_feature is not None
    assert col._current_feature.background is not None
    assert col._current_feature.background.name == "Common setup"


def test_end_background_without_start_is_noop() -> None:
    """end_background without a current background is a no-op."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.end_background()
    assert col._current_feature is not None
    assert col._current_feature.background is None


def test_background_steps_routed_to_background() -> None:
    """Steps during background mode are appended to the background, not the scenario."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_background(_mock_background())
    col.start_step(_mock_step(keyword="Given", name="bg step 1"))
    col.end_step(_mock_step(keyword="Given", name="bg step 1", status="passed"))
    col.end_background()
    assert col._current_feature is not None
    assert col._current_feature.background is not None
    assert len(col._current_feature.background.steps) == 1
    assert col._current_feature.background.steps[0].name == "bg step 1"


def test_background_attached_to_scenario() -> None:
    """Background is attached to scenarios when they start."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_background(_mock_background())
    col.start_step(_mock_step(keyword="Given", name="bg step"))
    col.end_step(_mock_step(keyword="Given", name="bg step", status="passed"))
    col.end_background()
    col.start_scenario(_mock_scenario(name="S1"))
    assert col._current_scenario is not None
    assert col._current_scenario.background is not None
    assert col._current_scenario.background.name == "Background"
    assert len(col._current_scenario.background.steps) == 1


def test_background_no_feature_is_noop() -> None:
    """end_background without a feature is a no-op."""
    col = Collector()
    col.start_background(_mock_background())
    col.end_background()
    assert col._current_background is None
    assert col._in_background is False


def test_background_failed_step_derives_scenario_failed() -> None:
    """A failed background step causes the scenario to derive failed status."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_background(_mock_background())
    col.start_step(_mock_step(keyword="Given", name="bg step"))
    col.end_step(_mock_step(keyword="Given", name="bg step", status="failed"))
    col.end_background()
    col.start_scenario(_mock_scenario(name="S1"))
    col.start_step(_mock_step(keyword="When", name="scn step"))
    col.end_step(_mock_step(keyword="When", name="scn step", status="passed"))
    col.end_scenario()
    assert col._current_feature is not None
    scn = col._current_feature.scenarios[0]
    assert scn.status == "failed"


def test_background_only_scenario_is_undefined_if_no_scenario_steps() -> None:
    """A scenario with only background steps and no scenario steps derives from all."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_background(_mock_background())
    col.start_step(_mock_step(keyword="Given", name="bg step"))
    col.end_step(_mock_step(keyword="Given", name="bg step", status="passed"))
    col.end_background()
    col.start_scenario(_mock_scenario(name="S1"))
    col.end_scenario()
    assert col._current_feature is not None
    scn = col._current_feature.scenarios[0]
    assert scn.status == "passed"


def test_background_default_name() -> None:
    """start_background with empty name defaults to 'Background'."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_background(SimpleNamespace(name="", location=""))
    assert col._current_background is not None
    assert col._current_background.name == "Background"


def test_full_lifecycle_with_background() -> None:
    """Full lifecycle with background: feature → background → scenario → steps → end."""
    col = Collector()
    col.start_feature(_mock_feature(name="Login", tags=["auth"]))
    col.start_background(_mock_background(name="Common setup"))
    col.start_step(_mock_step(keyword="Given", name="user is logged in"))
    col.end_step(_mock_step(keyword="Given", name="user is logged in", status="passed"))
    col.end_background()
    col.start_scenario(_mock_scenario(name="Logout"))
    col.start_step(_mock_step(keyword="When", name="user clicks logout"))
    col.end_step(_mock_step(keyword="When", name="user clicks logout", status="passed"))
    col.end_scenario()
    col.end_feature()
    run = col.finalize()
    feat = run.features[0]
    assert feat.background is not None
    assert feat.background.name == "Common setup"
    assert len(feat.background.steps) == 1
    scn = feat.scenarios[0]
    assert scn.background is not None
    assert len(scn.background.steps) == 1
    assert len(scn.steps) == 1
    assert scn.status == "passed"


# ---------------------------------------------------------------------------
# Rule
# ---------------------------------------------------------------------------


def test_rule_name_captured() -> None:
    """start_scenario captures the rule name from the scenario's rule attribute."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    rule = SimpleNamespace(name="My Rule")
    col.start_scenario(_mock_scenario(name="S1", rule=rule))
    assert col._current_scenario is not None
    assert col._current_scenario.rule_name == "My Rule"


def test_rule_name_empty_when_no_rule() -> None:
    """start_scenario with no rule has empty rule_name."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="S1", rule=None))
    assert col._current_scenario is not None
    assert col._current_scenario.rule_name == ""


def test_rule_with_background_and_scenario() -> None:
    """A rule with background and scenario steps works end-to-end."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_background(_mock_background(name="Rule bg"))
    col.start_step(_mock_step(keyword="Given", name="rule bg step"))
    col.end_step(_mock_step(keyword="Given", name="rule bg step", status="passed"))
    col.end_background()
    rule = SimpleNamespace(name="Auth rule")
    col.start_scenario(_mock_scenario(name="Login", rule=rule))
    assert col._current_scenario is not None
    assert col._current_scenario.rule_name == "Auth rule"
    assert col._current_scenario.background is not None
    col.start_step(_mock_step(keyword="When", name="login"))
    col.end_step(_mock_step(keyword="When", name="login", status="passed"))
    col.end_scenario()
    col.end_feature()
    run = col.finalize()
    scn = run.features[0].scenarios[0]
    assert scn.rule_name == "Auth rule"
    assert scn.status == "passed"


# ---------------------------------------------------------------------------
# Scenario Outline
# ---------------------------------------------------------------------------


def test_scenario_outline_is_outline_true() -> None:
    """A scenario outline sets is_outline=True and outline_name."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="Login with <user>", is_outline=True))
    assert col._current_scenario is not None
    assert col._current_scenario.is_outline is True
    assert col._current_scenario.outline_name == "Login with <user>"


def test_scenario_outline_not_outline() -> None:
    """A regular scenario has is_outline=False and empty outline_name."""
    col = Collector()
    col.start_feature(_mock_feature(name="F1"))
    col.start_scenario(_mock_scenario(name="Regular", is_outline=False))
    assert col._current_scenario is not None
    assert col._current_scenario.is_outline is False
    assert col._current_scenario.outline_name == ""


def test_scenario_outline_full_lifecycle() -> None:
    """A scenario outline with steps works end-to-end."""
    col = Collector()
    col.start_feature(_mock_feature(name="Data Driven"))
    col.start_scenario(_mock_scenario(name="Examples: <a>, <b>", is_outline=True))
    col.start_step(_mock_step(keyword="Given", name="input <a>"))
    col.end_step(_mock_step(keyword="Given", name="input <a>", status="passed"))
    col.start_step(_mock_step(keyword="Then", name="result is <b>"))
    col.end_step(_mock_step(keyword="Then", name="result is <b>", status="passed"))
    col.end_scenario()
    col.end_feature()
    run = col.finalize()
    scn = run.features[0].scenarios[0]
    assert scn.is_outline is True
    assert scn.outline_name == "Examples: <a>, <b>"
    assert len(scn.steps) == 2
    assert scn.status == "passed"


# ---------------------------------------------------------------------------
# Integration tests (using conftest behave_* fixtures)
# ---------------------------------------------------------------------------


def test_integration_mixed_status_run(
    behave_feature: SimpleNamespace,
    behave_background: SimpleNamespace,
    behave_scenario: SimpleNamespace,
    behave_passed_step: SimpleNamespace,
    behave_failed_step: SimpleNamespace,
    behave_skipped_step: SimpleNamespace,
    behave_undefined_step: SimpleNamespace,
) -> None:
    """Full run with passed, failed, skipped, and undefined statuses."""
    col = Collector()

    # Feature 1: Login — background + scenario with passed/failed/skipped
    col.start_feature(behave_feature)
    col.start_background(behave_background)
    col.start_step(behave_passed_step)
    col.end_step(behave_passed_step)
    col.end_background()

    col.start_scenario(behave_scenario)
    col.start_step(behave_passed_step)
    col.end_step(behave_passed_step)
    col.start_step(behave_failed_step)
    col.end_step(behave_failed_step)
    col.start_step(behave_skipped_step)
    col.end_step(behave_skipped_step)
    col.end_scenario()
    col.end_feature()

    # Feature 2: Search — scenario with undefined steps
    search_feature = SimpleNamespace(
        name="Search",
        tags=[],
        location="features/search.feature:1",
        description=None,
    )
    search_scenario = SimpleNamespace(
        name="Search works",
        tags=[],
        location="features/search.feature:5",
        feature=search_feature,
        is_outline=False,
        rule=None,
        description=None,
    )
    col.start_feature(search_feature)
    col.start_scenario(search_scenario)
    col.start_step(behave_undefined_step)
    col.end_step(behave_undefined_step)
    col.end_scenario()
    col.end_feature()

    run = col.finalize()

    # Run-level checks
    assert len(run.features) == 2
    assert run.duration > 0.0
    assert run.run_id.startswith("run_")

    # Feature 1: Login
    feat1 = run.features[0]
    assert feat1.name == "Login"
    assert feat1.background is not None
    assert len(feat1.background.steps) == 1
    assert len(feat1.scenarios) == 1
    scn1 = feat1.scenarios[0]
    assert scn1.name == "Login succeeds"
    assert scn1.status == "failed"
    assert scn1.error is not None
    assert "Dashboard element not found" in scn1.error.message
    assert len(scn1.steps) == 3
    assert scn1.steps[0].status == "passed"
    assert scn1.steps[1].status == "failed"
    assert scn1.steps[2].status == "skipped"
    assert scn1.background is not None
    assert len(scn1.background.steps) == 1

    # Feature 2: Search
    feat2 = run.features[1]
    assert feat2.name == "Search"
    assert feat2.background is None
    assert len(feat2.scenarios) == 1
    scn2 = feat2.scenarios[0]
    assert scn2.status == "undefined"
    assert scn2.error is None
    assert len(scn2.steps) == 1
    assert scn2.steps[0].status == "undefined"


def test_integration_all_passed_run(
    behave_feature: SimpleNamespace,
    behave_scenario: SimpleNamespace,
    behave_passed_step: SimpleNamespace,
) -> None:
    """A run where all steps pass produces a clean RunSummary."""
    col = Collector()
    col.start_feature(behave_feature)
    col.start_scenario(behave_scenario)
    col.start_step(behave_passed_step)
    col.end_step(behave_passed_step)
    col.start_step(behave_passed_step)
    col.end_step(behave_passed_step)
    col.end_scenario()
    col.end_feature()
    run = col.finalize()
    assert len(run.features) == 1
    scn = run.features[0].scenarios[0]
    assert scn.status == "passed"
    assert scn.error is None
    assert len(scn.steps) == 2


def test_integration_outline_with_background(
    behave_feature: SimpleNamespace,
    behave_background: SimpleNamespace,
    behave_outline_scenario: SimpleNamespace,
    behave_passed_step: SimpleNamespace,
) -> None:
    """A scenario outline with background works end-to-end."""
    col = Collector()
    col.start_feature(behave_feature)
    col.start_background(behave_background)
    col.start_step(behave_passed_step)
    col.end_step(behave_passed_step)
    col.end_background()
    col.start_scenario(behave_outline_scenario)
    assert col._current_scenario is not None
    assert col._current_scenario.is_outline is True
    assert col._current_scenario.outline_name == "Login with <user>"
    assert col._current_scenario.background is not None
    col.start_step(behave_passed_step)
    col.end_step(behave_passed_step)
    col.end_scenario()
    col.end_feature()
    run = col.finalize()
    scn = run.features[0].scenarios[0]
    assert scn.is_outline is True
    assert scn.background is not None
    assert len(scn.background.steps) == 1
    assert scn.status == "passed"


def test_integration_multiple_features_mixed_statuses(
    behave_passed_step: SimpleNamespace,
    behave_failed_step: SimpleNamespace,
    behave_skipped_step: SimpleNamespace,
) -> None:
    """Multiple features with different scenario statuses aggregate correctly."""
    col = Collector()

    # Feature 1: all passed
    f1 = SimpleNamespace(name="F1", tags=[], location="f1:1", description=None)
    s1 = SimpleNamespace(
        name="S1", tags=[], location="f1:5",
        feature=f1, is_outline=False, rule=None, description=None,
    )
    col.start_feature(f1)
    col.start_scenario(s1)
    col.start_step(behave_passed_step)
    col.end_step(behave_passed_step)
    col.end_scenario()
    col.end_feature()

    # Feature 2: failed
    f2 = SimpleNamespace(name="F2", tags=[], location="f2:1", description=None)
    s2 = SimpleNamespace(
        name="S2", tags=[], location="f2:5",
        feature=f2, is_outline=False, rule=None, description=None,
    )
    col.start_feature(f2)
    col.start_scenario(s2)
    col.start_step(behave_passed_step)
    col.end_step(behave_passed_step)
    col.start_step(behave_failed_step)
    col.end_step(behave_failed_step)
    col.end_scenario()
    col.end_feature()

    # Feature 3: all skipped
    f3 = SimpleNamespace(name="F3", tags=[], location="f3:1", description=None)
    s3 = SimpleNamespace(
        name="S3", tags=[], location="f3:5",
        feature=f3, is_outline=False, rule=None, description=None,
    )
    col.start_feature(f3)
    col.start_scenario(s3)
    col.start_step(behave_skipped_step)
    col.end_step(behave_skipped_step)
    col.end_scenario()
    col.end_feature()

    run = col.finalize()
    assert len(run.features) == 3
    assert run.features[0].scenarios[0].status == "passed"
    assert run.features[1].scenarios[0].status == "failed"
    assert run.features[2].scenarios[0].status == "skipped"


def test_integration_empty_run() -> None:
    """An empty run produces an empty RunSummary."""
    col = Collector()
    run = col.finalize()
    assert len(run.features) == 0
    assert run.total_features == 0
    assert run.total_scenarios == 0
    assert run.duration >= 0.0


def test_integration_conftest_fixtures_are_valid(
    behave_feature: SimpleNamespace,
    behave_background: SimpleNamespace,
    behave_scenario: SimpleNamespace,
    behave_outline_scenario: SimpleNamespace,
    behave_passed_step: SimpleNamespace,
    behave_failed_step: SimpleNamespace,
    behave_skipped_step: SimpleNamespace,
    behave_undefined_step: SimpleNamespace,
) -> None:
    """Verify that conftest behave_* fixtures have expected attributes."""
    assert behave_feature.name == "Login"
    assert "auth" in behave_feature.tags

    assert behave_background.name == "Background"

    assert behave_scenario.name == "Login succeeds"
    assert behave_scenario.feature.name == "Login"
    assert behave_scenario.is_outline is False

    assert behave_outline_scenario.is_outline is True
    assert behave_outline_scenario.name == "Login with <user>"

    assert behave_passed_step.status == "passed"
    assert behave_failed_step.status == "failed"
    assert behave_failed_step.error is not None
    assert behave_skipped_step.status == "skipped"
    assert behave_undefined_step.status == "undefined"
