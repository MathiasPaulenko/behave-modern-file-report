"""Jinja2-based HTML renderer for PDF report templates.

Renders the ``default.html`` template with ``RunSummary`` data and
custom Jinja2 filters for duration formatting and status icons.

Context variables:
    run: ``RunSummary`` instance with features, scenarios, and environment.
    options: ``ReportOptions`` with logo, title, and other settings.
    css: Inline CSS string read from ``default.css``.
"""

from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from behave_modern_file_report.models import ReportOptions, RunSummary
from behave_modern_file_report.utils import STATUS_ICONS, format_duration

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _format_duration(seconds: float) -> str:
    """Format a duration for HTML/PDF output.

    Args:
        seconds: Duration in seconds.

    Returns:
        Formatted string like ``"1.23s"``, ``"456ms"``, or ``"0ms"``.
    """
    return format_duration(seconds, precision=2, zero_label="0ms")


def _status_icon(status: str) -> str:
    """Return a single-character icon for a status.

    Args:
        status: Canonical status string.

    Returns:
        Icon character, or ``"?"`` for unknown statuses.
    """
    return STATUS_ICONS.get(status, "?")


def _create_env(template_dir: Path | None = None) -> Environment:
    """Create a Jinja2 environment with custom filters.

    Args:
        template_dir: Directory containing templates. Defaults to the
            built-in ``templates`` directory.

    Returns:
        Configured Jinja2 ``Environment``.
    """
    env = Environment(
        loader=FileSystemLoader(str(template_dir or _TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["format_duration"] = _format_duration
    env.filters["status_icon"] = _status_icon
    return env


def _resolve_template_path(
    options: ReportOptions,
    template_dir: Path | None,
) -> tuple[Path, str, str]:
    """Resolve the template directory, template name, and CSS name.

    If ``options.template`` is set and points to an existing file, the
    parent directory becomes the template directory and the filename
    becomes the template name.  Otherwise the built-in templates are used.

    Args:
        options: Resolved report options.
        template_dir: Explicit template directory override.

    Returns:
        A tuple of ``(template_dir, template_name, css_name)``.
    """
    if options.template:
        custom = Path(options.template)
        if custom.is_file():
            return custom.parent, custom.name, "default.css"
        # Could be a directory
        if custom.is_dir():
            return custom, "default.html", "default.css"
    return template_dir or _TEMPLATES_DIR, "default.html", "default.css"


def render_html(
    run_summary: RunSummary,
    options: ReportOptions | None = None,
    template_name: str = "default.html",
    css_name: str = "default.css",
    template_dir: Path | None = None,
) -> str:
    """Render the HTML report from a ``RunSummary``.

    If ``options.template`` is set and points to an existing file or
    directory, that template is used instead of the built-in one.

    Args:
        run_summary: The finalized run summary.
        options: Report options. If ``None``, default options are used.
        template_name: Name of the Jinja2 template file.
        css_name: Name of the CSS file to inline.
        template_dir: Directory containing templates. Defaults to the
            built-in ``templates`` directory.

    Returns:
        Rendered HTML string.
    """
    opts = options or ReportOptions()
    tdir, tname, cname = _resolve_template_path(opts, template_dir)
    # Allow explicit overrides when no custom template is set
    if not opts.template:
        tdir = template_dir or _TEMPLATES_DIR
        tname = template_name
        cname = css_name
    env = _create_env(tdir)

    css_path = tdir / cname
    if css_path.exists():
        css_content = css_path.read_text(encoding="utf-8", errors="replace")
    else:
        css_content = ""

    # Inject primary_color into CSS variables
    if opts.primary_color:
        css_content = re.sub(
            r"--color-primary:\s*[^;]+;",
            f"--color-primary: {opts.primary_color};",
            css_content,
        )

    template = env.get_template(tname)
    return template.render(
        run=run_summary,
        options=opts,
        css=css_content,
        logo_b64=opts.logo_b64,
    )


__all__ = ["render_html", "_resolve_template_path"]
