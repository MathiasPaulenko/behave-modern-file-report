"""Sample step definitions for the example Behave project."""

from __future__ import annotations

from behave import given, then, when


@given("a passing step")
def step_passing(context):
    """A step that always passes."""
    pass


@when("I do something successfully")
def step_success(context):
    """A step that completes successfully."""
    pass


@when("I do something that fails")
def step_fail(context):
    """A step that raises an assertion error."""
    raise AssertionError("Intentional failure for demonstration")


@when("I do something that is skipped")
def step_skip(context):
    """A step that skips the rest of the scenario."""
    context.scenario.skip("Skipped for demonstration")


@then("I should see the result")
def step_result(context):
    """A step that verifies the result."""
    pass


@then("I should see an error")
def step_error(context):
    """A step that is never reached."""
    pass


@then("I should not reach this step")
def step_not_reached(context):
    """A step that is never reached."""
    pass
