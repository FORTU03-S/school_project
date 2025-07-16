# school_project/profiles/utils.py (ou school_project/utils.py)

import os
from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.lib import colors
from datetime import datetime
from decimal import Decimal
from django.db.models import Sum # Important pour les agrégations

# Assurez-vous d'importer vos modèles
from profiles.models import Payment, Student, TuitionFee, School, AcademicPeriod

# --- DÉFINITION DES STYLES REPORTLAB (GLOBALEMENT DANS CE FICHIER) ---
# Ceci est la correction pour le "KeyError: Style 'Heading2' already defined"
reportlab_styles = getSampleStyleSheet()
reportlab_styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
reportlab_styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT))
reportlab_styles.add(ParagraphStyle(name='BoldTitle', fontSize=18, fontName='Helvetica-Bold', alignment=TA_CENTER))
reportlab_styles.add(ParagraphStyle(name='Heading2', fontSize=14, fontName='Helvetica-Bold', spaceAfter=10))
reportlab_styles.add(ParagraphStyle(name='Normal', fontSize=10, fontName='Helvetica'))
reportlab_styles.add(ParagraphStyle(name='Small', fontSize=8, fontName='Helvetica'))
reportlab_styles.add(ParagraphStyle(name='DetailLabel', fontSize=10, fontName='Helvetica-Bold'))
reportlab_styles.add(ParagraphStyle(name='DetailValue', fontSize=10, fontName='Helvetica'))

# --- DÉFINITION DE LA FONCTION GENERATE_RECEIPT_PDF ---
def generate_receipt_pdf(payment_instance):
    temp_receipts_root = os.path.join(settings.BASE_DIR, 'temp_receipts')
    os.makedirs(temp_receipts_root, exist_ok=True)

    filename = f"receipt_REC-{payment_instance.receipt_number}.pdf"
    pdf_path = os.path.join(temp_receipts_root, filename)

    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    story = []

    # Utilisez la variable de styles globale 'reportlab_styles'
    styles = reportlab_styles 

    # --- EN-TÊTE DE L'ÉCOLE ---
    school = payment_instance.student.school
    story.append(Paragraph(school.name.upper(), styles['BoldTitle']))
    story.append(Spacer(1, 0.2 * 10))
    story.append(Paragraph("REÇU DE PAIEMENT", styles['Heading2']))
    story.append(Spacer(1, 0.2 * 10))

    # --- INFOS GÉNÉRALES DU REÇU ---
    story.append(Paragraph(f"<font name='Helvetica-Bold'>Numéro de Reçu:</font> {payment_instance.receipt_number}", styles['Normal']))
    story.append(Paragraph(f"<font name='Helvetica-Bold'>Date du Paiement:</font> {payment_instance.payment_date.strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 0.2 * 10))

    # --- INFOS DE L'ÉLÈVE ---
    student = payment_instance.student
    story.append(Paragraph(f"<font name='Helvetica-Bold'>Payeur:</font> Parent de {student.full_name}", styles['Normal']))
    story.append(Paragraph(f"<font name='Helvetica-Bold'>Élève:</font> {student.full_name}", styles['Normal']))
    story.append(Paragraph(f"<font name='Helvetica-Bold'>Classe:</font> {student.current_classe.name}", styles['Normal']))
    story.append(Paragraph(f"<font name='Helvetica-Bold'>Période Académique:</font> {payment_instance.academic_period.name}", styles['Normal']))
    story.append(Spacer(1, 0.2 * 10))

    # --- DÉTAILS DU PAIEMENT SOUS FORME DE TABLEAU ---
    data = [
        ['Description', 'Type de Frais', 'Montant Dû', 'Montant Payé', 'Solde Restant']
    ]

    fees_due_for_student = TuitionFee.objects.filter(
        academic_period=payment_instance.academic_period,
        classe=student.current_classe,
        fee_type__school=school
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)

    amount_paid_by_student_total = Payment.objects.filter(
        academic_period=payment_instance.academic_period,
        student=student
    ).aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal(0)

    remaining_balance_overall = fees_due_for_student - amount_paid_by_student_total

    data.append([
        payment_instance.description or "Paiement de frais",
        payment_instance.fee_type.name if payment_instance.fee_type else "Non spécifié",
        f"{fees_due_for_student:.2f}$",
        f"{payment_instance.amount_paid:.2f}$",
        f"{remaining_balance_overall:.2f}$"
    ])

    table = Table(data, colWidths=[2*10, 1.5*10, 1.5*10, 1.5*10, 1.5*10])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.4 * 10))

    # --- RÉSUMÉ DES MONTANTS ---
    story.append(Paragraph(f"Montant Payé pour cette transaction: <font name='Helvetica-Bold'>{payment_instance.amount_paid:.2f}$</font>", styles['Right']))
    story.append(Paragraph(f"Solde Total Dû par l'élève: <font name='Helvetica-Bold'>{remaining_balance_overall:.2f}$</font>", styles['Right']))
    story.append(Spacer(1, 0.4 * 10))

    # --- PIED DE PAGE ---
    story.append(Paragraph(f"Enregistré par: {payment_instance.recorded_by.full_name}", styles['Normal']))
    story.append(Paragraph(f"Méthode de paiement: {payment_instance.payment_method}", styles['Normal']))
    story.append(Spacer(1, 0.5 * 10))
    story.append(Paragraph("Merci pour votre paiement!", styles['Center']))
    story.append(Paragraph(f"Généré le: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Small']))

    doc.build(story)
    return pdf_path