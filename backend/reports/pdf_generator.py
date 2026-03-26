"""
reports/pdf_generator.py — Professional PDF report generator for ArchAI.

Uses ReportLab (cross-platform PDF library) instead of WeasyPrint for Windows compatibility.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any
from io import BytesIO

logger = logging.getLogger(__name__)

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
    Generate a PDF report using ReportLab (Windows-compatible).
    Returns raw PDF bytes.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    except ImportError:
        # Fallback to a simple text-based PDF if ReportLab isn't available
        return _generate_simple_pdf(project, cost_data, compliance_data)

    # Safe defaults
    geo_data           = geo_data           or {}
    design_variant     = design_variant     or {}
    layout_data        = layout_data        or {}
    cost_data          = cost_data          or {}
    compliance_data    = compliance_data    or {}
    sustainability_data= sustainability_data or {}

    # Create PDF buffer
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch, bottomMargin=1*inch)
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#2c2c2a')
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        spaceBefore=20,
        textColor=colors.HexColor('#2c2c2a')
    )
    
    # Build content
    story = []
    
    # Title
    story.append(Paragraph("ArchAI Architectural Design Report", title_style))
    story.append(Spacer(1, 20))
    
    # Project Info
    story.append(Paragraph("Project Overview", heading_style))
    project_info = [
        ['Project Name:', project.get('name', 'Untitled Project')],
        ['Location:', f"{project.get('latitude', 0):.4f}, {project.get('longitude', 0):.4f}"],
        ['Plot Area:', f"{project.get('plot_area_sqm', 0):,.0f} sqm"],
        ['Floors:', str(project.get('floors', 2))],
        ['Budget:', f"₹{project.get('budget_inr', 0):,}"],
        ['Status:', project.get('status', 'Unknown').title()],
        ['Generated:', datetime.now().strftime("%B %d, %Y")]
    ]
    
    project_table = Table(project_info, colWidths=[2*inch, 4*inch])
    project_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(project_table)
    story.append(Spacer(1, 20))
    
    # Cost Analysis
    if cost_data:
        story.append(Paragraph("Cost Analysis", heading_style))
        total_cost = cost_data.get('total_cost_inr', 0)
        cost_per_sqft = cost_data.get('cost_per_sqft', 0)
        
        cost_info = [
            ['Total Construction Cost:', f"₹{total_cost:,}"],
            ['Cost per Sq Ft:', f"₹{cost_per_sqft:,.0f}"],
        ]
        
        # Add breakdown if available
        breakdown = cost_data.get('breakdown', {})
        if breakdown:
            for category, amount in breakdown.items():
                if isinstance(amount, (int, float)) and amount > 0:
                    cost_info.append([f"{category.replace('_', ' ').title()}:", f"₹{amount:,}"])
        
        cost_table = Table(cost_info, colWidths=[3*inch, 2*inch])
        cost_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(cost_table)
        story.append(Spacer(1, 20))
    
    # Compliance Check
    if compliance_data:
        story.append(Paragraph("Building Code Compliance", heading_style))
        
        passed = compliance_data.get('passed', False)
        fsi_used = compliance_data.get('fsi_used', 0)
        fsi_allowed = compliance_data.get('fsi_allowed', 1.5)
        issues = compliance_data.get('issues', [])
        
        compliance_info = [
            ['Overall Status:', '✓ COMPLIANT' if passed else '✗ NON-COMPLIANT'],
            ['FSI Used:', f"{fsi_used:.2f}"],
            ['FSI Allowed:', f"{fsi_allowed:.2f}"],
            ['FSI Compliance:', '✓ Pass' if fsi_used <= fsi_allowed else '✗ Fail'],
        ]
        
        if issues:
            compliance_info.append(['Issues Found:', f"{len(issues)} issue(s)"])
            for i, issue in enumerate(issues[:5], 1):  # Show max 5 issues
                compliance_info.append([f"Issue {i}:", str(issue)])
        
        compliance_table = Table(compliance_info, colWidths=[2.5*inch, 3*inch])
        compliance_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('TEXTCOLOR', (1, 0), (1, 0), colors.green if passed else colors.red),
        ]))
        story.append(compliance_table)
        story.append(Spacer(1, 20))
    
    # Sustainability
    if sustainability_data:
        story.append(Paragraph("Sustainability Analysis", heading_style))
        
        green_score = sustainability_data.get('green_score', 0)
        green_rating = sustainability_data.get('green_rating', 'Not Rated')
        
        sustainability_info = [
            ['Green Rating:', green_rating],
            ['Green Score:', f"{green_score}/100"],
            ['Solar Potential:', sustainability_data.get('solar_potential', 'Good')],
            ['Energy Efficiency:', sustainability_data.get('energy_efficiency', 'Standard')],
        ]
        
        sustainability_table = Table(sustainability_info, colWidths=[2.5*inch, 3*inch])
        sustainability_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(sustainability_table)
        story.append(Spacer(1, 20))
    
    # Design DNA
    dna = design_variant.get('dna', {})
    if dna:
        story.append(Paragraph("Design DNA", heading_style))
        
        dna_info = []
        for key, value in dna.items():
            if isinstance(value, (str, int, float)) and key not in ['layout_data', 'user_edited_rooms']:
                display_key = key.replace('_', ' ').title()
                dna_info.append([display_key + ':', str(value)])
        
        if dna_info:
            dna_table = Table(dna_info[:10], colWidths=[2.5*inch, 3*inch])  # Show max 10 items
            dna_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(dna_table)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    logger.info("pdf_generator: PDF generated using ReportLab (%d bytes)", len(pdf_bytes))
    return pdf_bytes


def _generate_simple_pdf(project: dict, cost_data: dict, compliance_data: dict) -> bytes:
    """
    Fallback: Generate a very simple PDF using just text if no PDF library is available.
    """
    try:
        from fpdf import FPDF
    except ImportError:
        # Ultimate fallback - return a simple text response as bytes
        content = f"""
ArchAI Project Report
====================

Project: {project.get('name', 'Untitled')}
Location: {project.get('latitude', 0):.4f}, {project.get('longitude', 0):.4f}
Plot Area: {project.get('plot_area_sqm', 0):,} sqm
Budget: ₹{project.get('budget_inr', 0):,}

Total Cost: ₹{cost_data.get('total_cost_inr', 0):,}
Compliance: {'PASS' if compliance_data.get('passed', False) else 'FAIL'}

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()
        return content.encode('utf-8')
    
    # Use FPDF as fallback
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'ArchAI Project Report', 0, 1, 'C')
    
    pdf.set_font('Arial', '', 12)
    pdf.ln(10)
    
    lines = [
        f"Project: {project.get('name', 'Untitled')}",
        f"Location: {project.get('latitude', 0):.4f}, {project.get('longitude', 0):.4f}",
        f"Plot Area: {project.get('plot_area_sqm', 0):,} sqm",
        f"Budget: ₹{project.get('budget_inr', 0):,}",
        "",
        f"Total Cost: ₹{cost_data.get('total_cost_inr', 0):,}",
        f"Compliance: {'PASS' if compliance_data.get('passed', False) else 'FAIL'}",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    ]
    
    for line in lines:
        pdf.cell(0, 8, line, 0, 1)
    
    return pdf.output(dest='S').encode('latin1')
