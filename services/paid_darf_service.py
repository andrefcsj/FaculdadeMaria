"""Histórico de DARFs pagos com cadastro manual e PDF opcional."""
from __future__ import annotations
import hashlib,json,uuid
from datetime import date,datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from services.cash_ledger_service import money

MAX_PDF_SIZE=5*1024*1024
def _path(legacy)->Path:return legacy.DATA/"paid_darfs.json"
def load_paid_darfs(legacy)->list[dict[str,Any]]:
    if getattr(legacy,"USE_POSTGRES",False):
        conn=legacy.get_pg_conn()
        try:
            cur=conn.cursor();cur.execute("""CREATE TABLE IF NOT EXISTS paid_darfs (
                darf_id TEXT PRIMARY KEY,payload JSONB NOT NULL,competence TEXT NOT NULL,payment_date DATE NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""");conn.commit();cur.execute("SELECT payload FROM paid_darfs ORDER BY payment_date DESC,created_at DESC");return [row[0] if isinstance(row[0],dict) else json.loads(row[0]) for row in cur.fetchall()]
        finally:conn.close()
    path=_path(legacy)
    if not path.exists():return []
    try:
        rows=json.loads(path.read_text(encoding="utf-8"));return rows if isinstance(rows,list) else []
    except Exception:return []
def save_paid_darf(legacy,*,competence:str,payment_date:date,due_date:date|None,revenue_code:str,amount:Decimal,description:str,pdf:bytes|None)->dict[str,Any]:
    if len(competence)!=7 or competence[4]!="-":raise ValueError("Competência inválida.")
    if amount<=0:raise ValueError("O valor pago deve ser maior que zero.")
    digest=""
    if pdf:
        if len(pdf)>MAX_PDF_SIZE:raise ValueError("O PDF deve ter no máximo 5 MB.")
        if not pdf.startswith(b"%PDF"):raise ValueError("O arquivo enviado não é um PDF válido.")
        digest=hashlib.sha256(pdf).hexdigest()
    rows=load_paid_darfs(legacy)
    if digest and any(row.get("document_hash")==digest for row in rows):raise ValueError("Este PDF de DARF já foi cadastrado.")
    record={"id":uuid.uuid4().hex,"competence":competence,"payment_date":payment_date.isoformat(),"due_date":due_date.isoformat() if due_date else "","revenue_code":str(revenue_code or "6015")[:12],"amount":str(amount),"description":str(description or "").strip()[:180],"document_hash":digest,"pdf_stored":False,"created_at":datetime.now().isoformat(timespec="seconds")}
    if getattr(legacy,"USE_POSTGRES",False):
        conn=legacy.get_pg_conn()
        try:
            cur=conn.cursor();cur.execute("""CREATE TABLE IF NOT EXISTS paid_darfs (
                darf_id TEXT PRIMARY KEY,payload JSONB NOT NULL,competence TEXT NOT NULL,payment_date DATE NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""");cur.execute("INSERT INTO paid_darfs(darf_id,payload,competence,payment_date) VALUES(%s,%s::jsonb,%s,%s)",(record["id"],json.dumps(record,ensure_ascii=False),competence,record["payment_date"]));conn.commit();return record
        finally:conn.close()
    rows.append(record);path=_path(legacy);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(".tmp");tmp.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8");tmp.replace(path);return record
def delete_paid_darf(legacy,darf_id:str)->bool:
    if getattr(legacy,"USE_POSTGRES",False):
        conn=legacy.get_pg_conn()
        try:cur=conn.cursor();cur.execute("DELETE FROM paid_darfs WHERE darf_id=%s",(darf_id,));deleted=cur.rowcount>0;conn.commit();return deleted
        finally:conn.close()
    rows=load_paid_darfs(legacy);kept=[row for row in rows if row.get("id")!=darf_id]
    if len(kept)==len(rows):return False
    _path(legacy).write_text(json.dumps(kept,ensure_ascii=False,indent=2),encoding="utf-8");return True
def build_darf_dashboard(legacy,*,scope:str,month:str,year:str)->dict[str,Any]:
    all_rows=load_paid_darfs(legacy)
    if scope=="month" and month:filtered=[row for row in all_rows if row.get("competence")==month]
    elif scope=="year" and year:filtered=[row for row in all_rows if str(row.get("competence","")).startswith(year)]
    else:filtered=all_rows
    current_month=date.today().strftime("%Y-%m");current_year=str(date.today().year)
    total_month=sum((money(row["amount"]) for row in all_rows if row.get("competence")==current_month),Decimal("0"));total_year=sum((money(row["amount"]) for row in all_rows if str(row.get("competence","")).startswith(current_year)),Decimal("0"));total_all=sum((money(row["amount"]) for row in all_rows),Decimal("0"))
    grouped={}
    for row in all_rows:grouped[row["competence"]]=grouped.get(row["competence"],Decimal("0"))+money(row["amount"])
    months=sorted(grouped)[-18:]
    return {"rows":filtered,"count":len(filtered),"total_month":total_month,"total_year":total_year,"total_all":total_all,"months":months,"series":[float(grouped[key]) for key in months],"scope":scope,"month":month or current_month,"year":year or current_year}
