# behave-modern-file-report

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](#testing)
[![Coverage](https://img.shields.io/badge/coverage-enabled-brightgreen.svg)](#testing)

Document-style report formatters for **[Behave](https://github.com/behave/behave)** BDD framework.
Generate polished **PDF**, **DOCX**, and **TXT** reports from your Behave test runs — with
cover pages, executive summaries, environment metadata, attachments, and branding support.

---

## Table of contents

- [Features](#features)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Example project](#example-project)
- [CLI usage](#cli-usage)
- [Configuration options](#configuration-options)
- [Attachments API](#attachments-api)
- [Custom templates](#custom-templates)
- [Branding](#branding)
- [Extras](#extras)
- [Development](#development)
- [License](#license)

---

## Features

- **Three output formats**: PDF (via WeasyPrint or ReportLab), DOCX (python-docx), TXT
- **Cover page** with title, project name, logo, and run metadata
- **Executive summary** with scenario totals, pass rate, and per-feature breakdown
- **Environment metadata** (Python version, platform, hostname, Git info)
- **Attachments**: screenshots, files, text, and JSON — embedded inline in reports
- **Multi-source screenshots**: bytes, file path, Selenium WebDriver, Playwright Page, PIL Image
- **Custom Jinja2 templates** for PDF reports
- **Branding**: custom logo, primary color, title, and project name
- **Table of contents** (PDF/DOCX) with clickable links
- **Error blocks** with traceback, exception type, and message
- **Background steps** and **Rule** support
- **Scenario outlines** (each example row reported as its own scenario)
- **Regression tests** with golden files for TXT and HTML output

---

## Installation

```bash
# Install with all optional dependencies
pip install "behave-modern-file-report[all]"

# Or pick only what you need
pip install "behave-modern-file-report[behave,pdf]"
pip install "behave-modern-file-report[behave,docx]"
pip install "behave-modern-file-report[behave]"
```

---

## Quick start

1. Install the package with the formats you need:

   ```bash
   pip install "behave-modern-file-report[all]"
   ```

2. Register the formatters in your `behave.ini` (or `behave.cfg`, `setup.cfg`,
   `tox.ini`, `pyproject.toml` `[tool.behave.formatters]`):

   ```ini
   [behave.formatters]
   behave-modern-pdf = behave_modern_file_report.pdf_formatter:PDFFormatter
   behave-modern-docx = behave_modern_file_report.docx_formatter:DOCXFormatter
   behave-modern-txt = behave_modern_file_report.txt_formatter:TXTFormatter
   ```

   > **Note:** Behave does not load setuptools entry points for custom
   > formatters — you must either declare aliases like above or pass the
   > scoped class name directly to `-f` (see [CLI usage](#cli-usage)).

3. Run Behave with a formatter and output file:

   ```bash
   behave -f behave-modern-pdf -o report.pdf features/
   behave -f behave-modern-docx -o report.docx features/
   behave -f behave-modern-txt -o report.txt features/
   ```

4. Open the generated report file.

---

## Example project

A ready-to-run sample is in [`examples/behave_project`](examples/behave_project):

```bash
cd examples/behave_project
behave -f behave-modern-pdf -o report.pdf
behave -f behave-modern-docx -o report.docx
behave -f behave-modern-txt -o report.txt
```

The included `behave.ini` configures the formatters and sets `bmfr.title`,
`bmfr.project_name`, and `bmfr.pdf_engine = reportlab` so the PDF example works
without WeasyPrint system dependencies.

---

## CLI usage

Custom formatters are selected with `-f <formatter-name>`. Behave resolves
formatter names in two ways — pick whichever suits your project:

**Option A — aliases in `behave.ini` (recommended).** Declare the aliases once
under `[behave.formatters]` and use short names:

```ini
[behave.formatters]
behave-modern-pdf = behave_modern_file_report.pdf_formatter:PDFFormatter
behave-modern-docx = behave_modern_file_report.docx_formatter:DOCXFormatter
behave-modern-txt = behave_modern_file_report.txt_formatter:TXTFormatter
```

**Option B — scoped class names.** No config needed, pass `module:Class` to `-f`:

```bash
behave -f behave_modern_file_report.pdf_formatter:PDFFormatter -o report.pdf features/
```

Then run:

```bash
# PDF report (default engine: WeasyPrint)
behave -f behave-modern-pdf -o report.pdf features/

# DOCX report
behave -f behave-modern-docx -o report.docx features/

# TXT report
behave -f behave-modern-txt -o report.txt features/

# Multiple formatters at once
behave \
  -f behave-modern-pdf -o report.pdf \
  -f behave-modern-docx -o report.docx \
  -f behave-modern-txt -o report.txt \
  features/
```

> **Note:** `-o` is required for PDF and DOCX. Without it, the formatter
> writes `report.pdf` / `report.docx` to the current directory instead of
> failing. The TXT formatter writes to stdout when `-o` is omitted.

### PDF engine selection

By default, PDF reports are rendered with **WeasyPrint**. WeasyPrint produces the
richest output but needs system libraries (GTK/Pango). If it is not available,
switch to the self-contained **ReportLab** engine:

```bash
behave -f behave-modern-pdf -o report.pdf -D "bmfr.pdf_engine=reportlab" features/
```

---

## Configuration options

All options are passed via Behave's `-D` (userdata) flag with the `bmfr.` prefix.
Format-specific options (`bmfr.<format>.<key>`) take precedence over global options
(`bmfr.<key>`).

| Option | Default | Description |
|--------|---------|-------------|
| `bmfr.title` | `Behave Modern Report` | Report title shown on cover page |
| `bmfr.project_name` | _(empty)_ | Project name shown on cover page |
| `bmfr.logo` | _(empty)_ | Path to a logo image file (PNG, JPEG) |
| `bmfr.primary_color` | `#2563EB` | Primary hex color for branding |
| `bmfr.template` | _(empty)_ | Path to a custom Jinja2 template file, or a directory containing `default.html` (and optionally `default.css`) |
| `bmfr.only_failed` | `false` | Only include failed scenarios in the report |
| `bmfr.include_attachments` | `true` | Embed attachments in the report |
| `bmfr.attachment_max_size_kb` | `512` | Maximum attachment size in KB |
| `bmfr.max_traceback_lines` | `50` | Maximum traceback lines per error |
| `bmfr.txt_width` | `100` | TXT report line width |
| `bmfr.txt_ascii` | `false` | Use ASCII-only characters in TXT report |
| `bmfr.pdf_engine` | `weasyprint` | PDF engine: `weasyprint` or `reportlab` |

### Format-specific overrides

Any option can be scoped to a specific format:

```bash
# Different title for PDF vs DOCX
behave \
  -f behave-modern-pdf -o report.pdf \
  -f behave-modern-docx -o report.docx \
  -D "bmfr.pdf.title=PDF Report" \
  -D "bmfr.docx.title=DOCX Report" \
  features/
```

---

## Attachments API

The package provides a public API for attaching screenshots, files, text, and JSON
to your test steps. Attachments are embedded inline in the reports. Call these
helpers from `environment.py` hooks (e.g. `after_step`) or from step
implementations — when several formatters run at once, every report receives
the attachment.

### Screenshot

```python
from behave_modern_file_report import attach_screenshot


@when("I take a screenshot")
def step_impl(context):
    attach_screenshot(context, context.driver.get_screenshot_as_png(), "login_page.png")
```

Supports multiple source types:

```python
# From bytes
attach_screenshot(context, png_bytes, "page.png")

# From file path
attach_screenshot(context, "/tmp/screenshot.png", "page.png")

# From Selenium WebDriver
attach_screenshot(context, context.driver, "page.png")

# From Playwright Page
attach_screenshot(context, context.page, "page.png")

# From PIL Image
attach_screenshot(context, pil_image, "page.png")
```

### File, text, and JSON

```python
from behave_modern_file_report import attach_file, attach_text, attach_json, log

# Attach a file
attach_file(context, "/tmp/report.csv", "report.csv")

# Attach text content
attach_text(context, "Debug output here", "debug.txt")

# Attach JSON data
attach_json(context, {"key": "value"}, "response.json")

# Log a message
log(context, "Something happened")
```

---

## Custom templates

PDF reports are rendered from Jinja2 templates. You can provide your own template
file or directory:

```bash
behave -f behave-modern-pdf -o report.pdf \
  -D "bmfr.template=/path/to/my_template.html" \
  features/
```

The template receives these context variables:

| Variable | Type | Description |
|----------|------|-------------|
| `run` | `RunSummary` | Full run data with features, scenarios, steps |
| `options` | `ReportOptions` | Resolved options (title, logo, colors, etc.) |
| `css` | `str` | Inline CSS string from `default.css` |
| `logo_b64` | `str` | Base64-encoded logo data URI |

Custom Jinja2 filters are available:

| Filter | Description |
|--------|-------------|
| `format_duration` | Format seconds as `1.23s`, `456ms`, or `0ms` |
| `status_icon` | Return status icon character (`✓`, `✗`, `↷`, `?`, `○`) |

---

## Branding

Customize the look of your reports with logo, colors, title, and project name:

```bash
behave -f behave-modern-pdf -o report.pdf \
  -D "bmfr.logo=assets/logo.png" \
  -D "bmfr.primary_color=#1E90FF" \
  -D "bmfr.title=QA Report" \
  -D "bmfr.project_name=My Project" \
  features/
```

- **PDF**: Logo appears on the cover page, primary color is injected into CSS variables
- **DOCX**: Logo on cover page, primary color applied to headings, badges, and progress bar
- **TXT**: Title shown on cover page

---

## Extras

| Extra | Dependencies | Description |
|-------|-------------|-------------|
| `behave` | `behave>=1.3.0` | Behave framework integration |
| `pdf` | `Jinja2>=3.1`, `weasyprint>=63.0`, `reportlab>=4.0` | PDF report generation |
| `docx` | `python-docx>=1.1` | DOCX report generation |
| `all` | All of the above | Everything in one install |
| `dev` | `all` + `pytest`, `ruff`, `mypy`, `build`, `twine` | Development tools |

```bash
pip install "behave-modern-file-report[all]"
pip install "behave-modern-file-report[dev]"
```

---

## Development

```bash
# Install dev dependencies
make dev

# Run tests
make test

# Lint
make lint

# Type check
make typecheck

# Format
make format

# Build
make build

# Clean
make clean
```

### Testing

The project uses a comprehensive test suite with:

- Unit tests for all writers, formatters, models, and utilities
- Golden file regression tests for TXT and HTML output
- Integration tests with Behave (skipped if Behave is not installed)
- Type checking with mypy and linting with ruff

```bash
make test          # Run all tests
make lint          # Ruff linting
make typecheck     # Mypy type checking
```

---

## License

[MIT](LICENSE) © Mathias Paulenko
