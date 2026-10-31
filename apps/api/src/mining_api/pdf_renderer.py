"""Deterministic local PDF renderer from the serialized Python snapshot."""

from functools import partial
from pathlib import Path
from xml.sax.saxutils import escape

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

TITLE = "Laporan Rekap Anggaran dan Biaya Operasional"
FONT = "ReportVera"
BOLD_FONT = "ReportVeraBold"
# ReportLab distributes these licensed fonts; embed them without network assets.
FONT_DIRECTORY = Path(reportlab.__file__).parent / "fonts"
pdfmetrics.registerFont(TTFont(FONT, str(FONT_DIRECTORY / "Vera.ttf")))
pdfmetrics.registerFont(TTFont(BOLD_FONT, str(FONT_DIRECTORY / "VeraBd.ttf")))
pdfmetrics.registerFontFamily(FONT, normal=FONT, bold=BOLD_FONT)


def render_pdf(report: dict, destination: Path) -> None:
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportBody", fontName=FONT, fontSize=9, leading=13,
                              alignment=TA_LEFT, spaceAfter=7))
    styles["Title"].fontName = BOLD_FONT
    styles["Title"].alignment = TA_LEFT
    styles["Title"].fontSize = 18
    styles["Title"].leading = 23
    styles["Heading2"].fontName = BOLD_FONT
    styles.add(ParagraphStyle(name="Cell", fontName=FONT, fontSize=7, leading=10, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name="CellNumber", parent=styles["Cell"], alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name="CellHead", parent=styles["Cell"], fontName=BOLD_FONT, textColor=colors.white))
    story = []

    def paragraph(text, style="ReportBody"):
        # All dynamic text escaped before ReportLab markup interpretation.
        return Paragraph(escape(str(text)), styles[style])

    def table(rows, widths, header=True):
        data = [[paragraph(cell, "CellHead" if index == 0 and header else "Cell" if column == 0 else "CellNumber")
                 for column, cell in enumerate(row)]
                for index, row in enumerate(rows)]
        result = LongTable(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
        commands = [("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#d4e0e0"))]
        if header:
            commands.extend([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#163d3b")),
                             ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f6f5")])])
        result.setStyle(TableStyle(commands))
        return result

    story.append(paragraph(TITLE, "Title"))
    summary = report["summary"]
    story.append(paragraph(summary["synthetic_data_disclaimer"]))
    metadata = report["metadata"]
    story.append(paragraph(f"Periode: {metadata['period_start']} sampai {metadata['period_end']} | Mata uang: IDR | Sumber ringkasan: offline"))
    story.append(paragraph("Variance positif = over-budget; negatif = under-budget; nol = on-budget."))
    kpis = report["kpis"]
    rows = [["KPI", "Nilai"]]
    for label, key in [("Total Anggaran", "total_budget"), ("Total Realisasi", "total_actual_cost"),
                       ("Variance", "variance"), ("Variance %", "variance_pct"),
                       ("Total Transaksi", "transaction_count"), ("Over-budget", "over_budget_count"),
                       ("Under-budget", "under_budget_count"), ("On-budget", "on_budget_count")]:
        value = kpis[key]
        rows.append([label, value["display_value"] if isinstance(value, dict) else value])
    story.extend([table(rows, [245, 270]), Spacer(1, 12)])
    for heading, section, label in [("Ringkasan Departemen", "department_summary", "department"),
                                     ("Ringkasan Kategori", "category_summary", "category")]:
        story.append(paragraph(heading, "Heading2"))
        rows = [["Nama", "Anggaran", "Realisasi", "Variance", "Variance %", "Jumlah"]]
        for row in report[section]:
            rows.append([row[label], *[row[key]["display_value"] for key in ("budget", "actual_cost", "variance", "variance_pct")], row["transaction_count"]])
        story.extend([table(rows, [120, 90, 90, 90, 72, 53]), Spacer(1, 12)])
    for heading, texts in [
        ("Ringkasan Eksekutif", [summary["executive_summary"]]), ("Temuan Utama", summary["key_findings"]),
        ("Potensi Risiko", [f"{risk['evidence_level']}: {risk['statement']}" for risk in summary["potential_risks"]]),
        ("Rekomendasi Tindakan", summary["actionable_recommendations"]),
    ]:
        story.append(paragraph(heading, "Heading2"))
        for text in texts:
            story.append(paragraph(text))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(FONT, 8)
        canvas.setFillColor(colors.HexColor("#526765"))
        canvas.drawString(34, 20, "Data sintetis | KPI dari Python/Pandas | Interpretasi offline")
        canvas.drawRightString(A4[0] - 34, 20, f"Halaman {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(str(destination), pagesize=A4, rightMargin=34, leftMargin=34,
                            topMargin=32, bottomMargin=38, title=TITLE,
                            author="Synthetic Demo", subject="Synthetic operational expense report")
    doc.build(story, onFirstPage=footer, onLaterPages=footer, canvasmaker=partial(Canvas, invariant=1))
