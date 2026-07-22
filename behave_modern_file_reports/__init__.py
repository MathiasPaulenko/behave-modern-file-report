"""Document-style report formatters for Behave BDD."""

from behave_modern_file_reports.attachments import (
    attach_file,
    attach_json,
    attach_screenshot,
    attach_text,
    log,
)

__version__ = "1.1.1"

__all__ = [
    "__version__",
    "attach_file",
    "attach_json",
    "attach_screenshot",
    "attach_text",
    "log",
]
