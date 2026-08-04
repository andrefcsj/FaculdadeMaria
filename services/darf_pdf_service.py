"""Geração do DARF simples, sem código de barras, para pagamento não vencido."""
from __future__ import annotations
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

def _brl(value): return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
def _date(value): return value.strftime("%d/%m/%Y")

def generate_darf_pdf(*, profile, competence, due_date, amount, revenue_code="6015"):
    year, month = map(int, competence.split("-"))
    import calendar
    assessment = __import__("datetime").date(year, month, calendar.monthrange(year, month)[1])
    stream = BytesIO(); page = landscape(A4); pdf = canvas.Canvas(stream, pagesize=page)
    width, height = page; left, bottom, right, top = 28, 55, width-28, height-35; split = left + (right-left)*.57
    pdf.setLineWidth(1.4); pdf.rect(left, bottom, right-left, top-bottom); pdf.line(split, bottom, split, top)
    for y in (top-185,): pdf.line(left, y, split, y)
    rows = [top, top-54, top-108, top-162, top-216, top-270, top-324, top-378, bottom]
    for y in rows[1:-1]: pdf.line(split, y, right, y)
    label_x, value_x = split+8, right-12
    labels = [("02 PERÍODO DE APURAÇÃO", _date(assessment)),("03 CPF", profile["cpf"]),("04 CÓDIGO DA RECEITA", revenue_code),("05 NÚMERO DE REFERÊNCIA", ""),("06 DATA DE VENCIMENTO", _date(due_date)),("07 VALOR DO PRINCIPAL", _brl(amount)),("08 VALOR DA MULTA", "R$ 0,00"),("09 JUROS / ENCARGOS", "R$ 0,00")]
    pdf.setFont("Helvetica", 10)
    for index,(label,value) in enumerate(labels):
        y=rows[index+1]+36; pdf.drawString(label_x,y,label); pdf.setFont("Helvetica-Bold",12); pdf.drawRightString(value_x,y,value); pdf.setFont("Helvetica",10)
    pdf.setFont("Helvetica-Bold",11); pdf.drawString(label_x,bottom+18,"10 VALOR TOTAL"); pdf.setFont("Helvetica-Bold",14); pdf.drawRightString(value_x,bottom+18,_brl(amount))
    pdf.setFont("Helvetica-Bold",20); pdf.drawString(left+18,top-38,"MINISTÉRIO DA FAZENDA")
    pdf.setFont("Helvetica-Bold",14); pdf.drawString(left+18,top-65,"SECRETARIA ESPECIAL DA RECEITA FEDERAL DO BRASIL")
    pdf.setFont("Helvetica",12); pdf.drawString(left+18,top-93,"Documento de Arrecadação de Receitas Federais")
    pdf.setFont("Helvetica-Bold",28); pdf.drawString(left+18,top-135,"DARF")
    pdf.setFont("Helvetica-Bold",11); pdf.drawString(left+12,top-207,"01 NOME / TELEFONE")
    pdf.setFont("Helvetica",12); pdf.drawString(left+25,top-235,f"{profile['name']}  {profile.get('phone','')}")
    pdf.setFont("Helvetica-Bold",13); pdf.drawString(left+18,top-295,"REF. OPERAÇÕES EM BOLSA DE VALORES")
    pdf.setFont("Helvetica",12); pdf.drawString(left+18,top-320,f"Competência {month:02d}/{year}")
    pdf.setFont("Helvetica-Bold",14); pdf.drawString(left+18,top-360,f"DARF válido para pagamento até {_date(due_date)}")
    pdf.setFont("Helvetica",11); pdf.drawString(left+18,top-388,f"Domicílio tributário: {profile['city']} - {profile['state']}")
    pdf.setFont("Helvetica-Bold",12); pdf.drawString(left+18,bottom+22,"PAGAMENTO SEM CÓDIGO DE BARRAS")
    pdf.setFont("Helvetica",8); pdf.drawRightString(right,bottom-18,"Documento gerado pelo FaculdadeMaria a partir da apuração informada pelo contribuinte.")
    pdf.showPage(); pdf.save(); stream.seek(0); return stream
