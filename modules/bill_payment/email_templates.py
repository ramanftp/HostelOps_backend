from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)


def generate_bill_pdf(bill, tenant, hostel):
    """
    Premium modern hostel bill PDF template
    Returns BytesIO object
    """

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18,
        leftMargin=18,
        topMargin=18,
        bottomMargin=18
    )

    styles = getSampleStyleSheet()

    # Custom Styles
    title_style = ParagraphStyle(
        name="TitleStyle",
        parent=styles["Normal"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1d4ed8"),
        spaceAfter=10,
        alignment=1
    )

    section_title = ParagraphStyle(
        name="SectionTitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#111827"),
        spaceAfter=6
    )

    normal = ParagraphStyle(
        name="NormalText",
        parent=styles["Normal"],
        fontSize=10,
        leading=14
    )

    total_style = ParagraphStyle(
        name="TotalStyle",
        parent=styles["Normal"],
        fontSize=16,
        textColor=colors.HexColor("#059669"),
        alignment=2
    )

    elements = []

    # =========================
    # HEADER
    # =========================
    elements.append(Paragraph("HOSTEL RENT INVOICE", title_style))
    elements.append(
        Paragraph(
            f"<b>{hostel.name}</b><br/>{hostel.address or '-'}",
            normal
        )
    )

    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    elements.append(Spacer(1, 12))

    # =========================
    # BILL + TENANT INFO
    # =========================
    info_data = [
        [
            Paragraph(
                f"<b>Invoice No:</b> {bill.bill_number}<br/>"
                f"<b>Bill Date:</b> {bill.created_at.strftime('%d-%m-%Y')}<br/>"
                f"<b>Due Date:</b> {bill.due_date.strftime('%d-%m-%Y')}",
                normal
            ),
            Paragraph(
                f"<b>Tenant:</b> {tenant.name}<br/>"
                f"<b>Room:</b> {tenant.room.room_number if tenant.room else '-'}<br/>"
                f"<b>Status:</b> {bill.status.title()}",
                normal
            )
        ]
    ]

    info_table = Table(info_data, colWidths=[260, 260])

    info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.lightgrey),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    elements.append(info_table)
    elements.append(Spacer(1, 18))

    # =========================
    # CHARGES TABLE
    # =========================
    charges = [
        ["Description", "Amount (₹)"],
        [bill.description or "Monthly Rent", f"{bill.amount:.2f}"],
    ]

    charges_table = Table(charges, colWidths=[390, 130])

    charges_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),

        ("GRID", (0, 0), (-1, -1), 0.6, colors.grey),

        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),

        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    elements.append(charges_table)
    elements.append(Spacer(1, 18))

    # =========================
    # TOTAL
    # =========================
    elements.append(
        Paragraph(
            f"Total Payable: ₹ {bill.amount:.2f}",
            total_style
        )
    )

    elements.append(Spacer(1, 25))
    elements.append(HRFlowable(width="100%", thickness=0.6, color=colors.grey))
    elements.append(Spacer(1, 10))

    # =========================
    # FOOTER
    # =========================
    elements.append(
        Paragraph(
            "Thank you for staying with us.<br/>"
            "Please pay before due date to avoid late charges.",
            normal
        )
    )

    doc.build(elements)

    buffer.seek(0)
    return buffer

