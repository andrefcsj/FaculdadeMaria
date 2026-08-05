"""Geração de DARF no padrão visual do Sicalc Web (duas vias em A4)."""
from __future__ import annotations
import calendar
import unicodedata
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

MONTHS = ("janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro")

def _money(value): return f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
def _date(value): return value.strftime("%d/%m/%Y")
def _cpf(value):
    digits = "".join(ch for ch in str(value) if ch.isdigit()).zfill(11)
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
def _ascii_upper(value): return unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().upper()

def _fit(pdf, text, x, y, max_width, font="Helvetica", size=8):
    while size > 5 and stringWidth(text, font, size) > max_width: size -= .5
    pdf.setFont(font, size); pdf.drawString(x, y, text)

def _voucher(pdf, *, bottom, via, profile, assessment, due_date, amount, revenue_code, observations, crest):
    left, split, label_split, right = 31, 297, 430, 564
    top, fields_bottom, auth_bottom = bottom + 241, bottom + 16, bottom
    pdf.setStrokeColorRGB(0,0,0); pdf.setFillColorRGB(0,0,0); pdf.setLineWidth(.45)
    pdf.drawRightString(right, top+7, via)
    pdf.line(left, top, right, top); pdf.line(left, auth_bottom, left, top); pdf.line(split, auth_bottom, split, top); pdf.line(right, auth_bottom, right, top)
    # Cabeçalho e brasão.
    pdf.drawImage(crest, left+5, top-49, width=40, height=45, preserveAspectRatio=True, mask="auto")
    pdf.setFont("Helvetica-Bold", 12); pdf.drawString(left+47, top-16, "MINISTÉRIO DA FAZENDA")
    _fit(pdf, "SECRETARIA DA RECEITA FEDERAL DO BRASIL", left+47, top-31, split-left-51, "Helvetica-Bold", 9.6)
    pdf.setFont("Helvetica-Bold", 8.2); pdf.drawString(left+47, top-43, "Documento de Arrecadação de Receitas Federais")
    pdf.setFont("Helvetica-Bold", 17); pdf.drawString(left+47, top-65, "DARF")
    pdf.line(left+1, top-88, split-1, top-88)
    pdf.setFont("Helvetica-Bold", 13); pdf.drawString(left+2, top-102, "01")
    pdf.setFont("Helvetica", 6.5); pdf.drawString(left+21, top-99, "NOME / RAZÃO SOCIAL")
    _fit(pdf, _ascii_upper(profile["name"]), left+21, top-116, split-left-32, "Courier", 8)
    pdf.line(left+1, top-125, split-1, top-125)
    pdf.setFont("Helvetica", 8); pdf.drawString(left+5, top-146, "Data limite para acolhimento:")
    pdf.setFont("Helvetica-Bold", 8); pdf.drawString(left+125, top-146, _date(due_date))
    pdf.setFont("Helvetica", 8); pdf.drawString(left+5, top-164, "Observações:")
    pdf.setFont("Courier", 7.7)
    for index, line in enumerate(observations[:3]): pdf.drawString(left+5, top-181-index*12, line[:58])
    pdf.setFont("Helvetica", 5.8); pdf.drawString(left+3, auth_bottom+8, "SENDA (Versão:1.5.6)")
    pdf.drawRightString(split-3, auth_bottom+8, datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    # Campos 02 a 10.
    values = [
        ("02", "PERÍODO DE APURAÇÃO", _date(assessment)), ("03", "NÚMERO DO CPF OU CNPJ", _cpf(profile["cpf"])),
        ("04", "CÓDIGO DA RECEITA", revenue_code), ("05", "NÚMERO DE REFERÊNCIA", ""),
        ("06", "DATA DE VENCIMENTO", _date(due_date)), ("07", "VALOR DO PRINCIPAL", _money(amount)),
        ("08", "VALOR DA MULTA", ""), ("09", "VALOR DOS JUROS E / OU\nENCARGOS DL - 1.025/69", ""),
        ("10", "VALOR TOTAL", _money(amount)),
    ]
    row_height = 25
    for index, (number, label, value) in enumerate(values):
        y_top = top-index*row_height; y_bottom = y_top-row_height
        pdf.line(split, y_bottom, right, y_bottom); pdf.line(label_split, y_bottom, label_split, y_top)
        pdf.setFont("Helvetica-Bold", 12); pdf.drawString(split+2, y_top-13, number)
        pdf.setFont("Helvetica", 6.2)
        label_lines = label.split("\n")
        for li, line in enumerate(label_lines): pdf.drawString(split+21, y_top-10-li*7, line)
        pdf.setFont("Helvetica-Bold", 9); pdf.drawString(label_split-18, y_top-15, "->")
        pdf.setFont("Helvetica", 10); pdf.drawRightString(right-4, y_top-16, str(value))
    pdf.setFont("Helvetica-Bold", 13); pdf.drawString(split+2, fields_bottom-12, "11")
    pdf.setFont("Helvetica", 6.5); pdf.drawString(split+21, fields_bottom-9, "AUTENTICAÇÃO BANCÁRIA (Somente nas 1a. e 2a. vias)")

def generate_darf_pdf(*, profile, competence, due_date, amount, revenue_code="6015", payment_competences=()):
    year, month = map(int, competence.split("-")); assessment = date(year, month, calendar.monthrange(year, month)[1])
    months = list(payment_competences) or [competence]
    month_names = [MONTHS[int(item[5:7])-1] for item in months]
    period = month_names[0] if len(month_names)==1 else " e ".join((", ".join(month_names[:-1]), month_names[-1])).strip(" e")
    observations = [f"Venda de PUT no Mes de {period} de {year}", "Darf calculado pelo FaculdadeMaria", "Modelo visual do Sicalc Web"]
    stream=BytesIO(); pdf=canvas.Canvas(stream,pagesize=A4); crest=ImageReader(str(Path(__file__).resolve().parents[1]/"static"/"darf_brasao.png"))
    _voucher(pdf,bottom=553,via="1a. via",profile=profile,assessment=assessment,due_date=due_date,amount=amount,revenue_code=revenue_code,observations=observations,crest=crest)
    pdf.setDash(3,2); pdf.line(31,484,564,484); pdf.setDash()
    _voucher(pdf,bottom=202,via="2a. via",profile=profile,assessment=assessment,due_date=due_date,amount=amount,revenue_code=revenue_code,observations=observations,crest=crest)
    pdf.showPage(); pdf.save(); stream.seek(0); return stream
