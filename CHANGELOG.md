# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- `BaseFileFormatter` now finalizes the background section at feature/scenario/eof boundaries so background steps are captured and attached to the correct feature.
- `FeatureSummary.status` is now derived from its scenarios in `Collector.end_feature`, ensuring report badges reflect the real feature outcome.
- `ReportOptions.only_failed` is now respected; non-failing scenarios are filtered out before the report is written.
- `Environment.capture` no longer crashes when `os.getcwd()` or `getpass.getuser()` fail.
- `Collector._extract_error` no longer prematurely truncates long error messages/tracebacks with `safe_str`; only `max_traceback_lines` controls traceback length.
- `attach_text` and `attach_json` no longer truncate content when `attachment_max_size_kb` is zero or negative.
- `BaseFileFormatter._resolve_logo` now rejects non-image files instead of forcing `image/png` on them.
- `DOCXWriter` bookmarks and TOC links now escape bookmark names/anchors to avoid invalid XML.
- `PDFWriter` and the HTML template now derive the feature status with `FeatureSummary.derive_status()` instead of relying on a manually-set `status` field.
- `Collector._extract_error` now reports the correct number of truncated traceback lines.
- `Collector`/`FeatureSummary`/`RunSummary` status derivation now correctly handles `untested` status in addition to passed/failed/undefined/skipped.
- `Environment.capture` now performs a single git command to retrieve branch and commit, reducing blocking time.
- `BaseFileFormatter._resolve_logo` now skips oversized logo files and tolerates read errors.
- `attach_file` and `attach_screenshot` now check file size before reading and skip missing or oversized files without crashing.
- `TXTWriter` now tolerates invalid base64 attachment data.
- `html_renderer` now tolerates CSS files with invalid UTF-8 sequences.
- `BaseFileFormatter` now exposes `_resolve_path` and `_resolve_logo`, removing duplicated path resolution in `DOCXFormatter` and `PDFFormatter`.
- `Collector` now exposes `peek_current_step` so `BaseFileFormatter` no longer accesses the private `_step_queue` directly.
- Duration formatting is now unified through `utils.format_duration` with configurable precision, eliminating duplicated implementations in HTML/PDF/TXT.
- Status icons, labels, and colors are now centralized in `utils` and reused by DOCX, PDF, HTML, and TXT writers.
- `TXTFormatter` now forces UTF-8 output encoding, preventing `UnicodeEncodeError` when writing Unicode status icons on Windows.
- `TXTFormatter` now closes the Behave stream opener after writing, ensuring the output file is flushed and closed.
- WeasyPrint rendering now also catches `OSError` caused by missing system libraries and reports a clear `ImportError`.

## [1.0.0] - 2026-07-22

### Added

#### Core (Fases 1-3)

- **Three report formatters**: PDF (WeasyPrint/ReportLab), DOCX (python-docx), TXT
- **ReportOptions** model with format-specific overrides (`bmfr.<format>.<key>` over `bmfr.<key>`)
- **Collector** that listens to Behave events and builds `RunSummary` / `FeatureSummary` / `ScenarioResult` / `Step`
- **BaseFileFormatter** inheriting from `behave.formatter.base.Formatter` for full Behave compatibility
- **Cover page** with title, project name, run metadata, and progress bar
- **Executive summary** with scenario totals, pass rate, and per-feature breakdown
- **Environment metadata** (Python version, platform, hostname, Git info)
- **Error blocks** with traceback, exception type, and message
- **Background steps** and **Rule** support
- **Scenario outlines** with example tables
- **Table of contents** with clickable links (PDF/DOCX)

#### TXT Writer (Fase 4)

- Plain-text report with cover, summary, and per-feature detail sections
- Configurable line width (`bmfr.txt_width`)
- ASCII-only mode (`bmfr.txt_ascii`)
- Status icons (checkmark, cross, arrow, question mark)
- Duration formatting (ms/s)

#### DOCX Writer (Fase 5)

- Cover page with title, project name, and metadata
- Executive summary table with progress bar
- Per-feature sections with scenario detail
- Inline attachment rendering (images, text, file listings)
- Configurable heading styles and colors

#### PDF Writer (Fase 6)

- HTML intermediate via Jinja2 templates
- WeasyPrint and ReportLab engine support (`bmfr.pdf_engine`)
- CSS-based styling with print page setup
- Inline attachments as data URIs
- Table of contents with bookmarks

#### Attachments API (Fase 7a)

- `attach_screenshot` — multi-source: bytes, file path, Selenium WebDriver, Playwright Page, PIL Image
- `attach_file` — attach arbitrary files
- `attach_text` — attach text content
- `attach_json` — attach JSON data
- `log` — log messages
- Attachment size enforcement via `bmfr.attachment_max_size_kb`
- Attachment rendering in all three formats

#### Branding (Fase 7b)

- Custom logo (`bmfr.logo`) — resolved to base64 data URI, rendered on cover page (PDF/DOCX)
- Custom primary color (`bmfr.primary_color`) — injected into CSS variables (PDF) and applied to headings, badges, progress bar (DOCX)
- Custom title (`bmfr.title`) and project name (`bmfr.project_name`) on all formats

#### Custom Templates (Fase 7a)

- Custom Jinja2 template support via `bmfr.template` (file or directory path)
- Template context: `run`, `options`, `css`, `logo_b64`
- Custom filters: `format_duration`, `status_icon`

#### Golden File Tests (Fase 7c)

- `tests/golden/report.txt` and `tests/golden/report.html` for regression testing
- Timestamp normalization in comparisons
- `tests/golden/_generate.py` script for regenerating golden files

#### Example Project (Fase 8b)

- `examples/behave_project/` with `behave.ini`, `environment.py`, sample feature, and step definitions
- Demonstrates `attach_screenshot`, `attach_text`, and `log` API usage
- `make report` target generates TXT and DOCX reports

#### Documentation (Fase 8a)

- `README.md` with badges, installation, quick start, CLI usage, configuration options, attachments API, custom templates, branding, extras, and development sections
- `CHANGELOG.md` following Keep a Changelog format
- `LICENSE` MIT

### Changed

- `BaseFileFormatter` now inherits from `behave.formatter.base.Formatter` for Behave 1.3.3 compatibility
- TXT formatter `_close_stream` now flushes before closing to ensure data is written
- `README.md` updated with an example project section, PDF engine notes, and corrected testing claims

### Fixed

- WeasyPrint availability check now catches `OSError` in addition to `ImportError` (missing system libraries)
- PDF report tables now fit within page margins and long text wraps correctly in ReportLab and WeasyPrint
- Tags in PDF reports now render with a leading `@` on each tag
- Status icons and summary cards are now better aligned in WeasyPrint output
- Environment metadata is now captured automatically (Python/Behave version, platform, cwd, command, git, etc.)
- ReportLab cover page now shows run metadata in a table and no longer displays the "Generated by..." footer
- DOCX reports now render correctly with `python-docx>=1.1` (fixed `parse_xml` import)
- DOCX cover page uses a cleaner metadata table, fixed title/subtitle spacing, removed "Generated by..." footer
- DOCX tags now render with a leading `@` and step text now has correct spacing between keyword and name
- DOCX tables now use fixed column widths to prevent squished layouts
- DOCX Table of Contents is now a visible list with clickable links to each section and scenario

### Dependencies

- `behave>=1.3.0` (optional, via `[behave]` extra)
- `Jinja2>=3.1`, `weasyprint>=63.0`, `reportlab>=4.0` (optional, via `[pdf]` extra)
- `python-docx>=1.1` (optional, via `[docx]` extra)
