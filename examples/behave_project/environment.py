"""Behave environment with screenshot and attachment hooks.

This file is loaded by Behave before running features. It demonstrates how to
use the public attachment API from ``behave_modern_file_reports``.
"""

from __future__ import annotations

from behave_modern_file_reports import attach_screenshot, attach_text, log


def before_scenario(context, scenario):
    """Set up context before each scenario."""
    context.screenshot_counter = 0


def after_step(context, step):
    """Attach a screenshot and log line after each step.

    In a real project you would capture a real browser screenshot here.
    For this example we generate a small placeholder PNG.
    """
    context.screenshot_counter += 1

    # Generate a minimal 1x1 red PNG as a placeholder screenshot
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01"
        b"\x5c\xcd\xff\x69\x1e\x9b"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    name = f"step_{context.screenshot_counter}.png"
    attach_screenshot(context, png_bytes, name)

    # Log a message
    log(context, f"Completed step: {step.name}")


def after_scenario(context, scenario):
    """Attach a text summary after each scenario."""
    summary = f"Scenario '{scenario.name}' finished with status: {scenario.status}"
    attach_text(context, summary, "scenario_summary.txt")
