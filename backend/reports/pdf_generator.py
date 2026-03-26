"""
reports/pdf_generator.py — Professional PDF report generator for ArchAI.

Uses WeasyPrint (HTML→PDF) + Jinja2 templates.
All templates live in reports/templates/.

Design decisions
----------------
- Jinja2 renders data → HTML; WeasyPrint converts to PDF using print CSS.
- The inline PDF_CSS is also exported so the FastAPI endpoint can override it
  without touching the template file.
- All monetary values are formatted as ₹ with thousand separators; all dicts
  that may be None are safely coerced to {} before template rendering.
- WeasyPrint is imported lazily (inside the function) so the module can be
  imported in environments that don't have the native libs installed —
  the endpoint will return a 503 instead of crashing at startup.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

_jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html"]),
)

# ─── Custom Jinja2 filters ────────────────────────────────────────────────────

def _inr(value: Any) -> str:
    """Format an integer as ₹1,23,456 (Indian numbering system)."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return str(value)
    # Indian number system: last 3 digits, then groups of 2
    s = str(abs(n))
    if len(s) <= 3:
        formatted = s
    else:
        last3    = s[-3:]
        rest     = s[:-3]
        groups   = []
        while rest:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        formatted = ",".join(groups) + "," + last3
    return f"₹{formatted}" if n >= 0 else f"-₹{formatted}"


def _humanize(s: str) -> str:
    return s.replace("_", " ").title() if s else ""


_jinja_env.filters["inr"]      = _inr
_jinja_env.filters["humanize"] = _humanize


# ─── PDF CSS ──────────────────────────────────────────────────────────────────

PDF_CSS = """
@page {
    size: A4;
    margin: 18mm 14mm 18mm 14mm;
    @top-left {
        content: "ArchAI";
        font-family: Helvetica Neue, Arial, sans-serif;
        font-size: 8pt; color: #aaa; font-weight: 600; letter-spacing: 1pt;
    }
    @top-center {
        content: "Architectural Design Report";
        font-family: Helvetica Neue, Arial, sans-serif;
        font-size: 8pt; color: #bbb;
    }
    @bottom-right {
        content: "Page " counter(page) " of " counter(pages);
        font-family: Helvetica Neue, Arial, sans-serif;
        font-size: 8pt; color: #bbb;
    }
}

/* ── Base ── */
*, *::before, *::after { box-sizing: border-box; }
body {
    font-family: 'Helvetica Neue', Arial, sans-serif;
    color: #2c2c2a;
    font-size: 10pt;
    line-height: 1.65;
    margin: 0;
}

/* ── Typography ── */
h1 { font-size: 24pt; font-weight: 300; color: #111; margin: 0 0 6pt; letter-spacing: -0.5pt; }
h2 {
    font-size: 13pt; font-weight: 500; color: #2c2c2a;
    border-bottom: 0.5pt solid #ddd;
    padding-bottom: 4pt;
    margin: 20pt 0 8pt;
    page-break-after: avoid;
}
h3 { font-size: 10.5pt; font-weight: 500; color: #555; margin: 10pt 0 4pt; page-break-after: avoid; }
p  { margin: 4pt 0; }

/* ── Cover page ── */
.cover { page-break-after: always; padding-top: 24pt; }
.cover-subtitle { color: #999; font-size: 11pt; margin: 4pt 0 28pt; }
.cover-accent {
    display: inline-block;
    background: #f0f0ec;
    border-left: 3pt solid #4a7c3f;
    padding: 6pt 10pt;
    font-size: 9pt;
    color: #555;
    margin: 16pt 0 0;
}

/* ── Metric grid ── */
.metric-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10pt; margin: 10pt 0; }
.metric {
    background: #f8f7f4;
    border-radius: 5pt;
    padding: 10pt 12pt;
    border-top: 2pt solid #e8e8e4;
}
.metric-label { font-size: 7.5pt; color: #999; text-transform: uppercase; letter-spacing: 0.6pt; }
.metric-value { font-size: 16pt; font-weight: 500; color: #1a1a18; line-height: 1.3; margin-top: 2pt; }
.metric-unit  { font-size: 8pt; color: #aaa; font-weight: 400; }

/* ── Tables ── */
.data-table { width: 100%; border-collapse: collapse; font-size: 9pt; margin: 6pt 0; }
.data-table th {
    background: #f0f0ec;
    padding: 5pt 8pt;
    text-align: left;
    font-weight: 500;
    font-size: 8pt;
    text-transform: uppercase;
    letter-spacing: 0.4pt;
    color: #666;
}
.data-table td { padding: 5pt 8pt; border-bottom: 0.5pt solid #eee; }
.data-table td.right { text-align: right; font-weight: 500; }
.data-table tr.total td { background: #f0f0ec; font-weight: 600; border-bottom: none; }
.data-table tr:last-child td { border-bottom: none; }

/* ── Compliance ── */
.compliance-row {
    display: flex; align-items: flex-start; gap: 8pt;
    padding: 5pt 0; border-bottom: 0.5pt solid #f0f0ec;
    font-size: 9pt;
}
.status-icon { font-size: 9pt; min-width: 14pt; }
.pass { color: #2d6a0a; font-weight: 600; }
.fail { color: #a01a1a; font-weight: 600; }
.warn { color: #8a5a00; font-weight: 600; }

/* ── Sustainability ── */
.green-badge {
    display: inline-block;
    background: #eaf4e0;
    border: 1pt solid #7ab84d;
    border-radius: 4pt;
    padding: 6pt 12pt;
    font-size: 28pt;
    font-weight: 300;
    color: #3b6d11;
    line-height: 1;
}
.green-label { font-size: 9pt; color: #7ab84d; font-weight: 500; margin-top: 2pt; }

.rec-list { margin: 4pt 0 0; padding: 0; list-style: none; }
.rec-list li { padding: 3pt 0; font-size: 9pt; color: #444; }
.rec-list li::before { content: "→ "; color: #4a7c3f; font-weight: 600; }

/* ── Floor plan ── */
.floor-plan-wrap { text-align: center; margin: 10pt 0; }
.floor-plan-wrap svg { max-width: 100%; height: auto; }
.floor-plan-caption { font-size: 8pt; color: #aaa; margin-top: 4pt; }

/* ── DNA pill tags ── */
.tag {
    display: inline-block;
    background: #f0f0ec;
    border: 0.5pt solid #ddd;
    border-radius: 3pt;
    padding: 1.5pt 6pt;
    font-size: 8pt;
    color: #555;
    margin: 1pt;
}

/* ── Section divider ── */
.divider { border: none; border-top: 0.5pt solid #eee; margin: 14pt 0; }

/* ── Page break helpers ── */
.page-break { page-break-before: always; }
.no-break    { page-break-inside: avoid; }
"""


# ─── Main generator ───────────────────────────────────────────────────────────

def generate_project_pdf(
    project:           dict[str, Any],
    geo_data:          dict[str, Any],
    design_variant:    dict[str, Any],
    layout_data:       dict[str, Any],
    cost_data:         dict[str, Any],
    compliance_data:   dict[str, Any],
    sustainability_data: dict[str, Any],
    floor_plan_svg:    str = "",
) -> bytes:
    """
    Render the Jinja2 HTML template and convert to PDF with WeasyPrint.

    All dict arguments are safely defaulted to {} if None.
    Returns raw PDF bytes.
    """
    try:
        from weasyprint import HTML, CSS  # lazy import
    except ImportError as exc:
        raise RuntimeError(
            "WeasyPrint is not installed. Run: pip install weasyprint"
        ) from exc

    # Safe defaults
    geo_data           = geo_data           or {}
    design_variant     = design_variant     or {}
    layout_data        = layout_data        or {}
    cost_data          = cost_data          or {}
    compliance_data    = compliance_data    or {}
    sustainability_data= sustainability_data or {}

    dna: dict[str, Any] = design_variant.get("dna") or {}

    # Flatten compliance setback sub-dict for easy template access
    setback = compliance_data.get("setback_compliance") or {}
    compliance_flat = {
        **compliance_data,
        "setback_front_m":          setback.get("front",  3.0),
        "setback_front_required_m": setback.get("front_required", 3.0),
        "setback_sides_m":          setback.get("sides",  1.5),
        "height_ok":                compliance_data.get("height_compliance", True),
        "max_height_m":             float(dna.get("floor_height", 3.0)) * int(project.get("floors", 2)),
        "fsi_used":                 round(float(compliance_data.get("fsi_used") or 0), 2),
        "fsi_allowed":              round(float(compliance_data.get("fsi_allowed") or 1.5), 2),
        "fsi_ok": (
            float(compliance_data.get("fsi_used") or 0)
            <= float(compliance_data.get("fsi_allowed") or 1.5)
        ),
        "issues":   compliance_data.get("issues")   or [],
        "warnings": compliance_data.get("warnings") or [],
        "passed":   compliance_data.get("passed", True),
    }

    template = _jinja_env.get_template("report.html")
    html_content = template.render(
        project          = project,
        geo              = geo_data,
        dna              = dna,
        variant          = design_variant,
        layout           = layout_data,
        cost             = cost_data,
        compliance       = compliance_flat,
        sustainability   = sustainability_data,
        floor_plan_svg   = floor_plan_svg or "",
        generated_at     = datetime.now().strftime("%B %d, %Y"),
        score            = float(design_variant.get("score") or 0),
    )

    logger.info("pdf_generator: rendering PDF for project %s", project.get("id", "?"))
    pdf_bytes: bytes = HTML(string=html_content).write_pdf(
        stylesheets=[CSS(string=PDF_CSS)]
    )
    logger.info("pdf_generator: PDF generated (%d bytes)", len(pdf_bytes))
    return pdf_bytes
