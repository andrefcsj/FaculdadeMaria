"""Livro-caixa da corretora e saldo contábil calculado."""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from services.brokerage_note_service import load_imported_notes
from services.closed_operations_service import load_closure_metadata


def money(value: Any) -> Decimal:
    text=str(value or "0").strip().replace("R$","").replace(" ","")
    if "," in text and "." in text:text=text.replace(".","").replace(",",".")
    elif "," in text:text=text.replace(",",".")
    try:return Decimal(text or "0")
    except InvalidOperation as exc:raise ValueError("Valor monetário inválido.") from exc


def _path(legacy)->Path:return legacy.DATA/"cash_ledger.json"


def load_cash_events(legacy)->list[dict[str,Any]]:
    if getattr(legacy,"USE_POSTGRES",False):
        conn=legacy.get_pg_conn()
        try:
            cur=conn.cursor();cur.execute("""CREATE TABLE IF NOT EXISTS cash_ledger (
                event_id TEXT PRIMARY KEY,payload JSONB NOT NULL,event_date DATE NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""");conn.commit();cur.execute("SELECT payload FROM cash_ledger ORDER BY event_date,created_at")
            return [row[0] if isinstance(row[0],dict) else json.loads(row[0]) for row in cur.fetchall()]
        finally:conn.close()
    path=_path(legacy)
    if not path.exists():return []
    try:
        data=json.loads(path.read_text(encoding="utf-8"));return data if isinstance(data,list) else []
    except Exception:return []


def save_cash_event(legacy,*,kind:str,amount:Decimal,event_date:date,description:str)->dict[str,Any]:
    if kind not in {"aporte","retirada","ajuste_credito","ajuste_debito"}:raise ValueError("Tipo de movimentação inválido.")
    if amount<=0:raise ValueError("O valor deve ser maior que zero.")
    record={"id":uuid.uuid4().hex,"kind":kind,"amount":str(amount),"date":event_date.isoformat(),"description":str(description or "").strip()[:180],"created_at":datetime.now().isoformat(timespec="seconds")}
    if getattr(legacy,"USE_POSTGRES",False):
        conn=legacy.get_pg_conn()
        try:
            cur=conn.cursor();cur.execute("""CREATE TABLE IF NOT EXISTS cash_ledger (
                event_id TEXT PRIMARY KEY,payload JSONB NOT NULL,event_date DATE NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""");cur.execute("INSERT INTO cash_ledger(event_id,payload,event_date) VALUES(%s,%s::jsonb,%s)",(record["id"],json.dumps(record,ensure_ascii=False),record["date"]));conn.commit();return record
        finally:conn.close()
    rows=load_cash_events(legacy);rows.append(record);path=_path(legacy);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(".tmp");tmp.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8");tmp.replace(path);return record


def delete_cash_event(legacy,event_id:str)->bool:
    if getattr(legacy,"USE_POSTGRES",False):
        conn=legacy.get_pg_conn()
        try:
            cur=conn.cursor();cur.execute("DELETE FROM cash_ledger WHERE event_id=%s",(event_id,));deleted=cur.rowcount>0;conn.commit();return deleted
        finally:conn.close()
    rows=load_cash_events(legacy);kept=[row for row in rows if row.get("id")!=event_id]
    if len(kept)==len(rows):return False
    path=_path(legacy);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(kept,ensure_ascii=False,indent=2),encoding="utf-8");return True


def _unique_notes(notes:list[dict[str,Any]])->list[dict[str,Any]]:
    unique:dict[str,dict[str,Any]]={}
    for note in notes:
        trade=note.get("trade",{}) if isinstance(note.get("trade"),dict) else {}
        identity=str(note.get("key") or f"{note.get('document_hash','')}:{trade.get('trade_index',0)}:{trade.get('option_code','')}")
        if identity not in unique:unique[identity]=note
    return list(unique.values())


def _note_links(notes:list[dict[str,Any]])->tuple[set[str],set[str]]:
    ids={str(note.get("operation_id")) for note in notes if note.get("operation_id") not in (None,"")}
    codes={str(note.get("trade",{}).get("option_code","")).upper() for note in notes if isinstance(note.get("trade"),dict)}
    return ids,{code for code in codes if code}


def _operation_has_note(operation:dict[str,Any],linked_ids:set[str],linked_codes:set[str])->bool:
    return str(operation.get("ID")) in linked_ids or str(operation.get("Ativo","")).upper() in linked_codes


def calculate_broker_balance(legacy)->dict[str,Any]:
    events=load_cash_events(legacy);notes=_unique_notes(load_imported_notes(legacy));linked_ids,linked_codes=_note_links(notes);closures=load_closure_metadata(legacy);operations=legacy.read_operacoes();size=money(legacy.load_config().get("Tamanho contrato opcoes",100))
    contributions=sum((money(row["amount"]) for row in events if row.get("kind") in {"aporte","ajuste_credito"}),Decimal("0"))
    withdrawals=sum((money(row["amount"]) for row in events if row.get("kind") in {"retirada","ajuste_debito"}),Decimal("0"))
    note_cash=sum((money(note.get("net_cash"))*(Decimal("1") if str(note.get("cash_direction","C")).upper()=="C" else Decimal("-1")) for note in notes),Decimal("0"))
    manual_cash=Decimal("0")
    for op in operations:
        oid=str(op.get("ID"));
        contracts=money(op.get("Contratos",1));premium=money(op.get("Premio_opcao"));costs=money(op.get("Custos"))+money(op.get("IRRF"));side=str(op.get("Estratégia","Venda")).lower()
        if not _operation_has_note(op,linked_ids,linked_codes):manual_cash+=(premium*contracts*size-costs)*(Decimal("1") if side=="venda" else Decimal("-1"))
        meta=closures.get(oid,{})
        if str(op.get("Status","")).lower()=="encerrada":
            method=str(meta.get("method",""));buyback=money(meta.get("repurchase_value"))
            if method=="recompra":manual_cash-=buyback*contracts*size
            elif method=="exercida" and str(op.get("Tipo","PUT")).upper()=="PUT":manual_cash-=money(op.get("Strike"))*contracts*size
    balance=contributions-withdrawals+note_cash+manual_cash
    return {"balance":balance,"contributions":contributions,"withdrawals":withdrawals,"brokerage_cash":note_cash,"manual_operations_cash":manual_cash,"events":events}


def build_cash_dashboard(legacy)->dict[str,Any]:
    summary=calculate_broker_balance(legacy);running=Decimal("0");entries=[]
    labels={"aporte":"Aporte","retirada":"Retirada","ajuste_credito":"Crédito manual","ajuste_debito":"Débito manual"}
    for event in summary["events"]:
        amount=money(event["amount"]);signed=amount if event["kind"] in {"aporte","ajuste_credito"} else -amount;entries.append({**event,"label":labels[event["kind"]],"source":"Movimentação manual","signed":signed,"deletable":True})
    notes=_unique_notes(load_imported_notes(legacy));linked_ids,linked_codes=_note_links(notes)
    for note in notes:
        signed=money(note.get("net_cash"))*(Decimal("1") if str(note.get("cash_direction","C")).upper()=="C" else Decimal("-1"));entries.append({"id":"note-"+str(note.get("key","")),"date":str(note.get("trade_date","")),"label":"Crédito de nota" if signed>=0 else "Débito de nota","description":f"Nota {note.get('note_number','')} • {note.get('trade',{}).get('option_code','')}","source":"BTG/Necton","signed":signed,"deletable":False})
    closures=load_closure_metadata(legacy);size=money(legacy.load_config().get("Tamanho contrato opcoes",100))
    for op in legacy.read_operacoes():
        oid=str(op.get("ID"));
        contracts=money(op.get("Contratos",1));premium=money(op.get("Premio_opcao"));costs=money(op.get("Custos"))+money(op.get("IRRF"));signed=(premium*contracts*size-costs)*(Decimal("1") if str(op.get("Estratégia","Venda")).lower()=="venda" else Decimal("-1"))
        if not _operation_has_note(op,linked_ids,linked_codes):entries.append({"id":"op-"+oid,"date":str(op.get("Data abertura","")),"label":"Prêmio de operação" if signed>=0 else "Compra de opção","description":str(op.get("Ativo","")),"source":"Operação cadastrada","signed":signed,"deletable":False})
        meta=closures.get(oid,{})
        if str(op.get("Status","")).lower()=="encerrada" and meta:
            method=str(meta.get("method",""));debit=Decimal("0")
            if method=="recompra":debit=money(meta.get("repurchase_value"))*contracts*size
            elif method=="exercida" and str(op.get("Tipo","PUT")).upper()=="PUT":debit=money(op.get("Strike"))*contracts*size
            if debit:entries.append({"id":"close-"+oid,"date":str(meta.get("close_date","")),"label":"Recompra" if method=="recompra" else "Exercício de PUT","description":str(op.get("Ativo","")),"source":"Encerramento","signed":-debit,"deletable":False})
    rows=[]
    for entry in sorted(entries,key=lambda row:(row.get("date",""),row.get("created_at",""),row.get("id",""))):running+=entry["signed"];rows.append({**entry,"running":running})
    summary["ledger_rows"]=list(reversed(rows));summary["chart_labels"]=[row.get("date","") for row in rows];summary["chart_values"]=[float(row["running"]) for row in rows];return summary
