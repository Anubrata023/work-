"""
Automated PDF Report Generator using ReportLab
Generates enforcement reports for BTP.
"""
import io
import pandas as pd
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

PROJECT_ROOT = Path(__file__).parent.parent


def generate_enforcement_report(ccis_df, hotspots, date_str=None):
    """
    Generate a PDF enforcement report.

    Parameters:
    - ccis_df: DataFrame with CCIS data
    - hotspots: DataFrame of top hotspots (already filtered by hour)
    - date_str: string, date for the report header

    Returns:
    - bytes: PDF content as bytes
    """
    if date_str is None:
        date_str = datetime.now().strftime("%B %d, %Y")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.darkblue,
        alignment=0
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.darkblue
    )

    story = []

    # Title
    story.append(Paragraph("VECTOR GRID", title_style))
    story.append(Paragraph(f"Enforcement Report - {date_str}", styles['Heading2']))
    story.append(Spacer(1, 0.25 * inch))

    # Summary
    story.append(Paragraph(f"Report Generated: {datetime.now().strftime('%H:%M %p')}", styles['Normal']))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(f"Active Hotspots: {len(hotspots)}", styles['Normal']))
    story.append(Paragraph(f"Total CCIS Impact: {hotspots['ccis'].sum():.1f}", styles['Normal']))
    story.append(Spacer(1, 0.25 * inch))

    # Hotspot Table
    story.append(Paragraph("Top 10 Priority Hotspots", heading_style))
    story.append(Spacer(1, 0.1 * inch))

    # Prepare table data
    table_data = [["Rank", "Zone ID", "CCIS Score", "Status"]]

    for idx, (_, row) in enumerate(hotspots.head(10).iterrows(), 1):
        status = "Critical" if row['ccis'] >= 6 else "Monitor" if row['ccis'] >= 3 else "Clear"
        table_data.append([
            str(idx),
            row['h3_cell'],
            f"{row['ccis']:.1f}",
            status
        ])

    table = Table(table_data, colWidths=[0.5 * inch, 1.8 * inch, 0.8 * inch, 0.8 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.25 * inch))

    # Recommendations
    story.append(Paragraph("Recommended Enforcement Schedule", heading_style))
    story.append(Spacer(1, 0.1 * inch))

    for idx, (_, row) in enumerate(hotspots.head(5).iterrows(), 1):
        story.append(Paragraph(
            f"{idx}. Zone {row['h3_cell']}: CCIS {row['ccis']:.1f} - Dispatch 2 officers",
            styles['Normal']
        ))
    story.append(Spacer(1, 0.25 * inch))

    # Footer
    story.append(Paragraph("--- End of Report ---", styles['Normal']))
    story.append(Paragraph("VECTOR GRID © 2026 | Data sourced from BTP", styles['Normal']))

    doc.build(story)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes


if __name__ == "__main__":
    # Test the report generator
    ccis_path = PROJECT_ROOT / "data" / "processed" / "ccis_scores.csv"
    if ccis_path.exists():
        ccis_df = pd.read_csv(ccis_path)
        hotspots = ccis_df.nlargest(10, 'ccis')
        pdf_bytes = generate_enforcement_report(ccis_df, hotspots)
        print(f"PDF generated: {len(pdf_bytes):,} bytes")

        # Save test PDF
        with open("test_report.pdf", "wb") as f:
            f.write(pdf_bytes)
        print("Test PDF saved as test_report.pdf")
    else:
        print("CCIS data not found.")