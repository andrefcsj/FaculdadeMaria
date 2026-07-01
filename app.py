from __future__ import annotations

import csv
import math
import json
import sqlite3
import os
import psycopg2
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Tuple

from flask import Flask, redirect, request, url_for, jsonify

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
OPERACOES = DATA / "operacoes.csv"
FECHADAS = DATA / "fechadas.csv"
CONFIG = DATA / "config.csv"
DB = DATA / "cortex.db"

app = Flask(__name__)
DATABASE_URL = os.getenv("DATABASE_URL")
USE_POSTGRES = bool(DATABASE_URL)

def get_pg_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL não configurada.")
    return psycopg2.connect(DATABASE_URL)


def init_db():
    if USE_POSTGRES:
        conn = get_pg_conn()
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS operacoes (
            id SERIAL PRIMARY KEY,
            data_abertura TEXT,
            ativo TEXT,
            tipo TEXT,
            estrategia TEXT,
            status TEXT,
            contratos TEXT,
            strike TEXT,
            premio_opcao TEXT,
            custos TEXT,
            irrf TEXT,
            vencimento TEXT,
            cotacao_atual TEXT,
            resultado_realizado TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS config (
            parametro TEXT PRIMARY KEY,
            valor TEXT
        )
        """)

        conn.commit()
        conn.close()
        print("✅ Tabelas criadas no Neon.")
        return

    # fallback para SQLite
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS operacoes (
            id INTEGER PRIMARY KEY,
            data_abertura TEXT,
            ativo TEXT,
            tipo TEXT,
            estrategia TEXT,
            status TEXT,
            contratos TEXT,
            strike TEXT,
            premio_opcao TEXT,
            custos TEXT,
            irrf TEXT,
            vencimento TEXT,
            cotacao_atual TEXT,
            resultado_realizado TEXT
        )
    ''')

    conn.commit()
    conn.close()


init_db()


MONTH_NAMES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

def current_month_label() -> str:
    d = date.today()
    return f"{MONTH_NAMES[d.month - 1]}/{str(d.year)[-2:]}"

def rolling_months(start: date | None = None, count: int = 12) -> List[str]:
    d = start or date.today()
    labels = []
    y, m = d.year, d.month
    for _ in range(count):
        labels.append(f"{MONTH_NAMES[m - 1]}/{str(y)[-2:]}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return labels


def brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(value: float) -> str:
    return f"{value:.2f}%".replace(".", ",")


def fnum(value: str | float | int | None, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        if isinstance(value, (int, float)):
            return float(value)
        txt = str(value).replace("R$", "").replace("%", "").strip().replace(" ", "")
        if "," in txt and "." in txt:
            txt = txt.replace(".", "").replace(",", ".")
        elif "," in txt:
            txt = txt.replace(",", ".")
        elif "." in txt:
            left, right = txt.rsplit(".", 1)
            if len(right) > 2:
                txt = txt.replace(".", "")
        return float(txt)
    except Exception:
        return default


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_config() -> Dict[str, float]:
    cfg = {"Capital total inicial": 4000.0, "Aliquota IR opcoes": 0.15, "Meta ROI mensal": 0.01, "Tamanho contrato opcoes": 100.0}
    for row in read_csv(CONFIG):
        cfg[row.get("Parametro", "")] = fnum(row.get("Valor"), cfg.get(row.get("Parametro", ""), 0))
    return cfg


def parse_date(s: str) -> date | None:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        try:
            return datetime.strptime(s, "%d/%m/%Y").date()
        except Exception:
            return None


def mes_label(d: date | None) -> str:
    if not d:
        return ""
    return f"{MONTH_NAMES[d.month - 1]}/{str(d.year)[-2:]}"


def enrich_ops(rows: List[Dict[str, str]], cfg: Dict[str, float]) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    tamanho = cfg.get("Tamanho contrato opcoes", 100.0)
    today = date.today()
    for r in rows:
        contratos = fnum(r.get("Contratos"), 1)
        strike = fnum(r.get("Strike"))
        premio_opcao = fnum(r.get("Premio_opcao"))
        custos = fnum(r.get("Custos"))
        irrf = fnum(r.get("IRRF"))
        cotacao = fnum(r.get("Cotacao_atual"))
        capital = contratos * strike * tamanho
        premio_bruto = contratos * premio_opcao * tamanho
        premio_liq = premio_bruto - custos - irrf
        roi = (premio_liq / capital * 100) if capital else 0
        venc = parse_date(str(r.get("Vencimento", "")))
        dias = max((venc - today).days, 0) if venc else 0
        tipo = str(r.get("Tipo", "PUT")).upper()
        alerta = "OK"
        if tipo == "PUT" and cotacao and cotacao < strike:
            alerta = "PUT dentro do dinheiro"
        if tipo == "CALL" and cotacao and cotacao > strike:
            alerta = "CALL dentro do dinheiro"
        # Nota provisória baseada no ROI líquido da operação.
        # 0 a 1,50% = baixo; 1,51% a 2,99% = regular; 3%+ = excelente.
        if roi >= 3:
            nota = "★★★★★"
        elif roi >= 2.5:
            nota = "★★★★☆"
        elif roi >= 1.51:
            nota = "★★★☆☆"
        elif roi > 0:
            nota = "★★☆☆☆"
        else:
            nota = "★☆☆☆☆"
        item = dict(r)
        item.update({
            "Contratos_n": contratos, "Strike_n": strike, "Premio_opcao_n": premio_opcao,
            "Custos_n": custos, "IRRF_n": irrf, "Cotacao_n": cotacao,
            "Capital": capital, "Premio_bruto": premio_bruto, "Premio_liquido": premio_liq,
            "ROI": roi, "Dias": dias, "Nota": nota, "Alerta": alerta,
            "Vencimento_fmt": venc.strftime("%d/%m/%Y") if venc else "",
            "Data_abertura_fmt": parse_date(str(r.get("Data abertura", ""))).strftime("%d/%m/%Y") if parse_date(str(r.get("Data abertura", ""))) else "",
            "Mes_abertura": mes_label(parse_date(str(r.get("Data abertura", ""))))
        })
        out.append(item)
    return out


def load_all() -> Tuple[List[Dict[str, object]], List[Dict[str, str]], Dict[str, float]]:
    cfg = load_config()
    return enrich_ops(read_csv(OPERACOES), cfg), read_csv(FECHADAS), cfg


def metrics(ops: List[Dict[str, object]], fechadas: List[Dict[str, str]], cfg: Dict[str, float]) -> Dict[str, float | str | int]:
    abertas = [o for o in ops if str(o.get("Status", "")).lower() == "aberta"]
    capital_total = cfg.get("Capital total inicial", 4000.0)
    capital_comp = sum(float(o["Capital"]) for o in abertas)
    premios_ativos = sum(float(o["Premio_liquido"]) for o in abertas)
    mes_atual = current_month_label()
    # DARF e lucro do mês vêm apenas das operações fechadas.
    # Preferimos Premio_liquido; se não existir, usamos Lucro_tributavel/Resultado_final como fallback.
    lucro_mes = 0.0
    for f in fechadas:
        if f.get("Mes") == mes_atual:
            base_f = fnum(f.get("Premio_liquido"), 0)
            if not base_f:
                base_f = fnum(f.get("Lucro_tributavel"), fnum(f.get("Resultado_final"), 0))
            lucro_mes += base_f
    darf = lucro_mes * cfg.get("Aliquota IR opcoes", 0.15)
    roi_mes = lucro_mes / capital_total * 100 if capital_total else 0
    roi_abertas = premios_ativos / capital_comp * 100 if capital_comp else 0
    roi_medio_abertas = (sum(float(o.get("ROI", 0)) for o in abertas) / len(abertas)) if abertas else 0
    rois_fechadas = []
    for f in fechadas:
        capital_f = fnum(f.get("Contratos"), 1) * fnum(f.get("Strike"), 0) * cfg.get("Tamanho contrato opcoes", 100.0)
        lucro_f = fnum(f.get("Lucro_tributavel"), fnum(f.get("Resultado_final"), 0))
        if capital_f:
            rois_fechadas.append(lucro_f / capital_f * 100)
    roi_medio_fechadas = (sum(rois_fechadas) / len(rois_fechadas)) if rois_fechadas else 0
    premios_fechados_total = 0.0
    for f in fechadas:
        base_f = fnum(f.get("Premio_liquido"), 0)
        if not base_f:
            base_f = fnum(f.get("Lucro_tributavel"), fnum(f.get("Resultado_final"), 0))
        premios_fechados_total += base_f
    premios_total = premios_ativos + premios_fechados_total
    caixa_livre = max(capital_total - capital_comp, 0)
    patrimonio_atual = capital_comp + premios_total
    return {"capital_total": capital_total, "capital_comp": capital_comp, "caixa": caixa_livre, "caixa_livre": caixa_livre, "premios_ativos": premios_ativos, "premios_total": premios_total, "patrimonio_atual": patrimonio_atual, "lucro_mes": lucro_mes, "darf": darf, "roi_mes": roi_mes, "roi_abertas": roi_abertas, "roi_medio_abertas": roi_medio_abertas, "roi_medio_fechadas": roi_medio_fechadas, "mes_atual": mes_atual, "abertas": len(abertas), "encerradas": len(ops) - len(abertas)}


def monthly(ops: List[Dict[str, object]], fechadas: List[Dict[str, str]], cfg: Dict[str, float]) -> List[Dict[str, float | str]]:
    base = []
    acumulado_premios = 0.0
    acumulado_capital = 0.0
    for m in rolling_months():
        premio_fechado_mes = 0.0
        for f in fechadas:
            if f.get("Mes") == m:
                base_f = fnum(f.get("Premio_liquido"), 0)
                if not base_f:
                    base_f = fnum(f.get("Lucro_tributavel"), fnum(f.get("Resultado_final"), 0))
                premio_fechado_mes += base_f
        premio_aberto_mes = sum(float(o["Premio_liquido"]) for o in ops if o.get("Mes_abertura") == m)
        capital_mes = sum(float(o["Capital"]) for o in ops if o.get("Mes_abertura") == m)
        lucro = premio_aberto_mes + premio_fechado_mes
        premios = lucro
        acumulado_premios += premios
        acumulado_capital += capital_mes
        darf = premio_fechado_mes * cfg.get("Aliquota IR opcoes", 0.15)
        patrimonio = acumulado_capital + acumulado_premios
        roi = lucro / acumulado_capital * 100 if acumulado_capital else 0
        base.append({"mes": m, "lucro": lucro, "premios": premios, "darf": darf, "roi": roi, "patrimonio": patrimonio})
    return base


def points(values: List[float], width: int = 620, height: int = 190, pad: int = 35) -> str:
    max_v = max(values + [1])
    min_v = min(values + [0])
    span = max(max_v - min_v, 1)
    step = (width - 2 * pad) / max(len(values) - 1, 1)
    pts = []
    for i, v in enumerate(values):
        x = pad + i * step
        y = height - pad - ((v - min_v) / span) * (height - 2 * pad)
        pts.append(f"{x:.1f},{y:.1f}")
    return " ".join(pts)


def line_chart(rows: List[Dict[str, object]], key: str, color: str = "#2a8cff") -> str:
    values = [float(r[key]) for r in rows]
    labels = "".join([f'<text x="{35+i*((620-70)/11):.0f}" y="184" font-size="10" fill="#b8c6d8" text-anchor="middle">{r["mes"]}</text>' for i, r in enumerate(rows)])
    circles = "".join([f'<circle cx="{p.split(",")[0]}" cy="{p.split(",")[1]}" r="4" fill="{color}" stroke="#bfe0ff"/><text x="{p.split(",")[0]}" y="{float(p.split(",")[1])-12:.1f}" font-size="10" fill="#fff" text-anchor="middle">{values[i]:.0f}</text>' for i, p in enumerate(points(values).split()) if values[i] > 0 or i < 5])
    grid = "".join([f'<line x1="30" y1="{y}" x2="610" y2="{y}" stroke="#1d2a3b"/>' for y in [35,65,95,125,155]])
    return f'<svg viewBox="0 0 620 190" class="chart">{grid}<polyline points="{points(values)}" fill="none" stroke="{color}" stroke-width="3"/>{circles}{labels}</svg>'


def bar_chart(rows: List[Dict[str, object]], key: str) -> str:
    values = [float(r[key]) for r in rows]
    max_v = max(values + [1])
    bars = []
    for i, r in enumerate(rows):
        x = 28 + i * 49
        h = (float(r[key]) / max_v) * 120 if max_v else 0
        y = 155 - h
        bars.append(f'<rect x="{x}" y="{y:.1f}" width="24" height="{h:.1f}" rx="4" fill="url(#barGrad)"/><text x="{x+12}" y="{max(20,y-8):.1f}" font-size="10" fill="#fff" text-anchor="middle">{float(r[key]):.0f}</text><text x="{x+12}" y="184" font-size="10" fill="#b8c6d8" text-anchor="middle">{r["mes"]}</text>')
    grid = "".join([f'<line x1="25" y1="{y}" x2="610" y2="{y}" stroke="#1d2a3b"/>' for y in [35,65,95,125,155]])
    return f'<svg viewBox="0 0 620 190" class="chart"><defs><linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#4ffc5d"/><stop offset="1" stop-color="#0b8e31"/></linearGradient></defs>{grid}{"".join(bars)}</svg>'


def donut_chart(ops: List[Dict[str, object]]) -> str:
    vals = [float(o["Premio_liquido"]) for o in ops]
    total = sum(vals) or 1
    colors = ["#2979ff", "#26c247", "#ff9d1e", "#7b35ff", "#ef4435"]
    start = 0
    segs = []
    legend = []
    for i, (o, v) in enumerate(zip(ops, vals)):
        frac = v / total
        end = start + frac * 360
        r = 65; cx = 95; cy = 88
        def xy(a):
            rad = math.radians(a - 90)
            return cx + r * math.cos(rad), cy + r * math.sin(rad)
        x1, y1 = xy(start); x2, y2 = xy(end)
        large = 1 if end - start > 180 else 0
        segs.append(f'<path d="M {cx} {cy} L {x1:.1f} {y1:.1f} A {r} {r} 0 {large} 1 {x2:.1f} {y2:.1f} Z" fill="{colors[i%len(colors)]}"/>')
        legend.append(f'<div><span style="background:{colors[i%len(colors)]}"></span><b>{o.get("Ativo")}</b> <em>{v/total*100:.1f}%</em><small>{brl(v)}</small></div>')
        start = end
    return f'<div class="donut-wrap"><svg viewBox="0 0 190 176" class="donut">{"".join(segs)}<circle cx="95" cy="88" r="42" fill="#0b1420"/><text x="95" y="84" text-anchor="middle" fill="#fff" font-size="16">{brl(total)}</text><text x="95" y="104" text-anchor="middle" fill="#b9c6d8" font-size="12">Total</text></svg><div class="legend">{"".join(legend)}</div></div>'


def gauge(value: float, titulo: str = "ROI") -> str:
    v = min(max(value, 0), 5)
    # Velocímetro v1.9: mais compacto, sem deformação, com numeração correta acima do arco.
    def polar(cx: float, cy: float, r: float, deg: float) -> tuple[float, float]:
        rad = math.radians(deg)
        return cx + r * math.cos(rad), cy - r * math.sin(rad)

    def arc_path(start_deg: float, end_deg: float, r: float = 88, cx: float = 130, cy: float = 126) -> str:
        x1, y1 = polar(cx, cy, r, start_deg)
        x2, y2 = polar(cx, cy, r, end_deg)
        large = 1 if abs(end_deg - start_deg) > 180 else 0
        return f'M {x1:.1f} {y1:.1f} A {r} {r} 0 {large} 0 {x2:.1f} {y2:.1f}'

    colors = [
        '#e51b12','#f03316','#fb4c18','#ff6a16','#ff8614',
        '#ffaa13','#ffc918','#ffe51a','#fff21a','#f4f31a',
        '#d6ee1b','#afe51b','#82d91d','#58cb22','#31b92b','#18a934'
    ]
    segs = []
    n = len(colors)
    gap = 1.9
    for i, c in enumerate(colors):
        start = 180 - (i * 180 / n) - gap/2
        end = 180 - ((i + 1) * 180 / n) + gap/2
        segs.append(f'<path d="{arc_path(start, end)}" class="gauge-seg" stroke="{c}"/>')

    angle = 180 - (v / 5 * 180)
    tip_x, tip_y = polar(130, 126, 74, angle)
    base_lx, base_ly = polar(130, 126, 9, angle + 96)
    base_rx, base_ry = polar(130, 126, 9, angle - 96)
    needle = f'<polygon points="{tip_x:.1f},{tip_y:.1f} {base_lx:.1f},{base_ly:.1f} {base_rx:.1f},{base_ry:.1f}" fill="url(#needleGrad)" stroke="#f4f6fb" stroke-width="1.1"/>'

    if value < 1:
        badge, cls = "RUIM", "low"
    elif value < 2.5:
        badge, cls = "REGULAR", "mid"
    elif value < 4:
        badge, cls = "BOM", "mid"
    elif value < 5:
        badge, cls = "ÓTIMO", "high"
    else:
        badge, cls = "EXCELENTE", "high"

    label_parts = []
    for pct_label in range(0, 6):
        deg = 180 - (pct_label / 5 * 180)
        x, y = polar(130, 126, 112, deg)
        # Pequeno ajuste nos extremos para manter o texto dentro do quadro.
        if pct_label == 0:
            x += 8
        elif pct_label == 5:
            x -= 8
        label_parts.append(f'<text x="{x:.1f}" y="{y:.1f}" class="g-label">{pct_label}%</text>')

    return f"""<div class="gauge gauge-v19">
    <svg viewBox="0 0 260 192" aria-label="{titulo}">
      <defs>
        <linearGradient id="needleGrad" x1="0" x2="1" y1="0" y2="1">
          <stop stop-color="#ffffff"/><stop offset=".55" stop-color="#b8c0ca"/><stop offset="1" stop-color="#6d7580"/>
        </linearGradient>
      </defs>
      <path d="{arc_path(180, 0, 92)}" class="gauge-back"/>
      {''.join(segs)}
      <path d="{arc_path(180, 0, 96)}" class="gauge-rim"/>
      {''.join(label_parts)}
      {needle}
      <circle cx="130" cy="126" r="6.5" fill="#091320" stroke="#9facbd" stroke-width="1.8"/>
      <text x="130" y="164" class="g-value">{pct(value)}</text>
    </svg>
    <div class="badge {cls}">{badge}</div>
    </div>"""

def metric_card(icon: str, label: str, value: str, sub: str, color: str) -> str:
    return f'<div class="metric {color}"><div class="mi">{icon}</div><div><div class="mlabel">{label}</div><div class="mvalue">{value}</div><div class="msub">{sub}</div></div></div>'


def infer_acao_from_option(codigo: str) -> str:
    codigo = (codigo or "").upper().strip()
    letters = "".join(ch for ch in codigo if ch.isalpha())
    base = letters[:4] if len(letters) >= 4 else letters
    mapa = {"BBDC": "BBDC4", "ITSA": "ITSA4", "GOAU": "GOAU4", "CPLE": "CPLE6", "PETR": "PETR4", "VALE": "VALE3", "BBAS": "BBAS3", "ABEV": "ABEV3"}
    return mapa.get(base, f"{base}4" if base else "")

def cotacao_yahoo(acao: str) -> float | None:
    try:
        import urllib.request
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{acao}.SA?range=1d&interval=1m"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        result = data.get("chart", {}).get("result", [])
        if not result:
            return None
        price = result[0].get("meta", {}).get("regularMarketPrice")
        return float(price) if price else None
    except Exception:
        return None


def rows_html(rows: List[Dict[str, object]], limit: int | None = None) -> str:
    body = []
    for o in rows[:limit]:
        alert_cls = "warn" if "dentro" in str(o.get("Alerta")) else "ok"
        oid = o.get("ID", "")
        opcao = str(o.get("Ativo", "")).upper()
        acao = infer_acao_from_option(opcao)
        contratos_acoes = int(float(o.get("Contratos_n", 0)) * 100)
        body.append(f"""<tr><td>{acao}</td><td>{opcao}</td><td>{o.get('Tipo')}</td><td>{contratos_acoes}</td><td>{brl(float(o.get('Strike_n',0)))}</td><td>{brl(float(o.get('Premio_liquido',0)))}</td><td>{brl(float(o.get('Capital',0)))}</td><td>{o.get('Vencimento_fmt','')}</td><td>{int(float(o.get('Dias',0)))}</td><td>{pct(float(o.get('ROI',0)))}</td><td>{o.get('Nota')}</td><td class="{alert_cls}">{o.get('Alerta')}</td><td class="actions"><a title="Editar operação" href="/editar/{oid}">✎</a><a title="Fechar operação" href="/fechar/{oid}" onclick="return confirm('Fechar esta operação?')">✓</a><a title="Excluir operação" href="/excluir/{oid}" onclick="return confirm('Excluir esta operação definitivamente?')">×</a></td></tr>""")
    return "".join(body)


@app.route("/", methods=["GET"])
def index():
    ops, fechadas, cfg = load_all()
    ind = metrics(ops, fechadas, cfg)
    hist = monthly(ops, fechadas, cfg)
    abertas = [o for o in ops if str(o.get("Status", "")).lower() == "aberta"]
    top = sorted(abertas, key=lambda x: float(x["Premio_liquido"]), reverse=True)[:5]
    prox = sorted([o for o in abertas if o.get('Vencimento_fmt')], key=lambda x: float(x.get('Dias', 9999)))
    if prox:
        prox_venc = f"{int(float(prox[0].get('Dias',0)))} dias"
        prox_sub = f"{infer_acao_from_option(str(prox[0].get('Ativo','')))} • {prox[0].get('Vencimento_fmt','')}"
    else:
        prox_venc = "--"
        prox_sub = "Sem operação aberta"
    notas_map = {'★☆☆☆☆':1, '★★☆☆☆':2, '★★★☆☆':3, '★★★★☆':4, '★★★★★':5}
    nota_media = (sum(notas_map.get(str(o.get('Nota','')),0) for o in abertas) / len(abertas)) if abertas else 0
    nota_cortex = f"{nota_media:.1f} ★".replace('.', ',') if abertas else "--"
    hist_nonzero = [r for r in hist if float(r["lucro"]) or float(r["premios"] or 0)]
    historico_table = "".join([f'<tr><td>{r["mes"]}</td><td>{brl(float(r["lucro"]))}</td><td>{brl(float(r["darf"]))}</td><td>{brl(float(r["premios"]))}</td><td>{pct(float(r["roi"]))} ↑</td></tr>' for r in reversed(hist_nonzero[-5:])])
    top_table = "".join([f'<tr><td>{o.get("Ativo")}</td><td>{o.get("Tipo")}</td><td>{brl(float(o["Strike_n"]))}</td><td>{brl(float(o["Premio_liquido"]))}</td><td>{pct(float(o["ROI"]))}</td></tr>' for o in top])
    html = f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Cortex Invest PRO v3.2.3</title><style>{CSS}</style></head><body>
    <aside><div class="logo"><div class="brain">✺</div><div class="brand">CORTEX<br><span>INVEST</span></div></div><div class="strategy">WHEEL STRATEGY</div><div class="side-block">📅<div><b>DATA ATUALIZAÇÃO</b><br>{datetime.now().strftime("%d/%m/%Y<br>%H:%M:%S")}</div></div><label>MÊS SELECIONADO</label><select><option>{ind["mes_atual"]}</option></select><nav><a class="active">▦ Dashboard</a><a>▧ Operações Abertas</a><a href='/op-fechadas'>Operações Fechadas</a><a>◫ Op. Fechadas</a><a>▣ Histórico</a><a>⌁ Desempenho</a><a>⚙ Ativos</a><a>▤ Relatórios</a><a>⚙ Configurações</a></nav><div class="quote">“A consistência é o que transforma estratégia em patrimônio.”<br><small>– CORTEX INVEST</small></div><div class="version">VERSÃO 3.2.3</div></aside>
    <main><header><h1>DASHBOARD <span>WHEEL</span></h1><p>Painel automático com prêmios mensais, ROI abertas e histórico por mês</p></header>
    <section class="metrics">
    {metric_card('🎁','PRÊMIOS ACUMULADOS',brl(float(ind['premios_total'])),'Abertas + fechadas','purple')}{metric_card('🎯','ROI ABERTAS',pct(float(ind['roi_medio_abertas'])),'Média das abertas','green')}{metric_card('🔒','CAPITAL COMPROMETIDO',brl(float(ind['capital_comp'])),'Em operações abertas','green')}{metric_card('💼','CAIXA DISPONÍVEL',brl(float(ind['caixa_livre'])),'Para novas operações','blue')}{metric_card('📅','PRÓXIMO VENCIMENTO',prox_venc,prox_sub,'orange')}{metric_card('⭐','NOTA CORTEX',nota_cortex,'Média das abertas','cyan')}{metric_card('🏛️','DARF DO MÊS',brl(float(ind['darf'])),str(ind['mes_atual']),'red')}{metric_card('📈','LUCRO DO MÊS',brl(float(ind['lucro_mes'])),str(ind['mes_atual']),'orange')}
    </section>
    <section class="grid two"><div class="panel"><h2>EVOLUÇÃO DO LUCRO (R$)</h2>{line_chart(hist,'lucro')}</div><div class="panel"><h2>PRÊMIOS RECEBIDOS POR MÊS (R$)</h2>{bar_chart(hist,'premios')}</div></section>
    <section class="grid three"><div class="panel wide"><h2>EVOLUÇÃO DO PATRIMÔNIO (R$)</h2>{line_chart(hist,'patrimonio','#a85cff')}</div><div class="panel"><h2>VELOCÍMETRO ROI MÉDIO (FECHADAS)</h2>{gauge(float(ind['roi_medio_fechadas']), 'ROI fechadas')}</div><div class="panel"><h2>VELOCÍMETRO ROI MÉDIO (ABERTAS)</h2>{gauge(float(ind['roi_medio_abertas']), 'ROI abertas')}</div></section>
    <section class="grid four no-summary"><div class="panel"><h2>Histórico</h2><table><thead><tr><th>Mês</th><th>Lucro</th><th>DARF</th><th>Prêmios</th><th>ROI</th></tr></thead><tbody>{historico_table}</tbody></table></div><div class="panel"><h2>TOP 5 Operações Abertas</h2><table><thead><tr><th>Ativo</th><th>Tipo</th><th>Strike</th><th>Prêmio</th><th>ROI</th></tr></thead><tbody>{top_table}</tbody></table><a href="#ops" class="button">VER TODAS AS OPERAÇÕES →</a></div><div class="panel"><h2>DISTRIBUIÇÃO DOS PRÊMIOS Ativos</h2>{donut_chart(abertas)}</div></section>
    <section class="panel" id="ops"><h2>{ind['abertas']} Operações Abertas</h2><table class="ops"><thead><tr><th>Ação</th><th>Opção</th><th>Tipo</th><th>Contratos</th><th>Strike</th><th>Prêmio líquido</th><th>Capital</th><th>Vencimento</th><th>Dias</th><th>ROI</th><th>Nota</th><th>Alerta</th><th>Ações</th></tr></thead><tbody>{rows_html(abertas)}</tbody></table></section>
    <section class="panel"><h2>CADASTRAR NOVA OPERAÇÃO</h2><form method="post" action="/nova" class="form labeled">
      <div><span>Código da opção</span><input id="ativo" name="Ativo" placeholder="Ex: BBDCS167" required onblur="buscarCotacao()"></div>
      <div><span>Strike real</span><input name="Strike" type="number" step="0.01" placeholder="Ex: 16,89"></div>
      <div><span>Tipo</span><select name="Tipo"><option>PUT</option><option>CALL</option></select></div>
      <div><span>Estratégia</span><select name="Estrategia"><option>Wheel</option><option>Pozinho</option></select></div>
      <div><span>Status</span><select name="Status"><option>Aberta</option><option>Encerrada</option></select></div>
      <div><span>Vencimento da opção</span><input type="date" name="Vencimento" required></div>
      <div><span>Contratos</span><input name="Contratos" type="number" min="1" value="1"></div>
      <div><span>Prêmio por opção</span><input name="Premio_opcao" type="number" step="0.01" placeholder="Ex: 0,33"></div>
      <div><span>Custos</span><input name="Custos" type="number" step="0.01" value="1.07"></div>
      <div><span>IRRF</span><input name="IRRF" type="number" step="0.01" value="0.04"></div>
      <input id="cotacao" name="Cotacao_atual" type="hidden" value="0">
      <button>Salvar operação</button>
    </form><small class="hint">A cotação da ação originária é buscada automaticamente pelo código da opção.</small></section>
    <script>
    async function buscarCotacao(){{
      const ativo=document.getElementById('ativo').value.trim();
      const campo=document.getElementById('cotacao');
      if(!ativo) return;
      // cotação buscada em segundo plano
      try{{
        const r=await fetch('/cotacao?codigo='+encodeURIComponent(ativo));
        const d=await r.json();
        if(d.cotacao){{ campo.value=Number(d.cotacao).toFixed(2); }}
      }}catch(e){{ /* mantém zero se não encontrar */ }}
    }}
    </script>
    </main><footer>🛡️ Dashboard protegido contra edição. Os dados são atualizados automaticamente. &nbsp; CORTEX INVEST v2.9 • WHEEL STRATEGY • DISCIPLINA, GESTÃO E CONSISTÊNCIA</footer></body></html>'''
    return html

def salvar_operacao_pg(row):
    conn = get_pg_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO operacoes (
            data_abertura,
            ativo,
            tipo,
            estrategia,
            status,
            contratos,
            strike,
            premio_opcao,
            custos,
            irrf,
            vencimento,
            cotacao_atual,
            resultado_realizado
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        row["Data abertura"],
        row["Ativo"],
        row["Tipo"],
        row["Estratégia"],
        row["Status"],
        row["Contratos"],
        row["Strike"],
        row["Premio_opcao"],
        row["Custos"],
        row["IRRF"],
        row["Vencimento"],
        row["Cotacao_atual"],
        row["Resultado_realizado"]
    ))

    conn.commit()
    conn.close()

@app.route("/nova", methods=["POST"])
def nova():
    rows = read_csv(OPERACOES)
    next_id = max([int(fnum(r.get("ID"))) for r in rows] + [0]) + 1

    row = {
        "ID": str(next_id),
        "Data abertura": request.form.get("Data_abertura", str(date.today())),
        "Ativo": request.form.get("Ativo", "").upper(),
        "Tipo": request.form.get("Tipo", "PUT"),
        "Estratégia": request.form.get("Estrategia", "Wheel"),
        "Status": request.form.get("Status", "Aberta"),
        "Contratos": request.form.get("Contratos", "1"),
        "Strike": request.form.get("Strike", "0"),
        "Premio_opcao": request.form.get("Premio_opcao", "0"),
        "Custos": request.form.get("Custos", "0"),
        "IRRF": request.form.get("IRRF", "0"),
        "Vencimento": request.form.get("Vencimento", str(date.today())),
        "Cotacao_atual": request.form.get("Cotacao_atual", "0"),
        "Resultado_realizado": "0",
    }

    if not fnum(row.get("Cotacao_atual")):
        acao = infer_acao_from_option(row.get("Ativo", ""))
        valor = cotacao_yahoo(acao) if acao else None

        if valor:
            row["Cotacao_atual"] = f"{valor:.2f}"

    if USE_POSTGRES:
        salvar_operacao_pg(row)
        return redirect(url_for("index"))

    rows.append(row)
    write_csv(
        OPERACOES,
        rows,
        [
            "ID",
            "Data abertura",
            "Ativo",
            "Tipo",
            "Estratégia",
            "Status",
            "Contratos",
            "Strike",
            "Premio_opcao",
            "Custos",
            "IRRF",
            "Vencimento",
            "Cotacao_atual",
            "Resultado_realizado",
        ],
    )

    return redirect(url_for("index"))


@app.route('/cotacao')
def cotacao():
    codigo = request.args.get('codigo', '')
    acao = infer_acao_from_option(codigo)
    valor = cotacao_yahoo(acao) if acao else None
    return jsonify({'codigo_opcao': codigo.upper(), 'acao': acao, 'cotacao': valor})


def find_row(rows: List[Dict[str, str]], oid: str) -> Dict[str, str] | None:
    for r in rows:
        if str(r.get('ID')) == str(oid):
            return r
    return None


@app.route('/editar/<oid>', methods=['GET', 'POST'])
def editar(oid: str):
    rows = read_csv(OPERACOES)
    r = find_row(rows, oid)
    if not r:
        return redirect(url_for('index'))
    fields = ['ID', 'Data abertura', 'Ativo', 'Tipo', 'Estratégia', 'Status', 'Contratos', 'Strike', 'Premio_opcao', 'Custos', 'IRRF', 'Vencimento', 'Cotacao_atual', 'Resultado_realizado']
    if request.method == 'POST':
        for campo in ['Ativo', 'Tipo', 'Status', 'Contratos', 'Strike', 'Premio_opcao', 'Custos', 'IRRF', 'Vencimento', 'Cotacao_atual']:
            r[campo] = request.form.get(campo, r.get(campo, ''))
        r['Estratégia'] = request.form.get('Estrategia', r.get('Estratégia', 'Wheel'))
        write_csv(OPERACOES, rows, fields)
        return redirect(url_for('index'))
    html = f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Editar operação</title><style>{CSS}</style></head><body><main class="edit-page"><section class="panel"><h2>EDITAR OPERAÇÃO</h2><form method="post" class="form labeled">
    <div><span>Código da opção</span><input name="Ativo" value="{r.get('Ativo','')}"></div>
    <div><span>Tipo</span><select name="Tipo"><option {'selected' if r.get('Tipo')=='PUT' else ''}>PUT</option><option {'selected' if r.get('Tipo')=='CALL' else ''}>CALL</option></select></div>
    <div><span>Status</span><select name="Status"><option {'selected' if r.get('Status')=='Aberta' else ''}>Aberta</option><option {'selected' if r.get('Status')=='Encerrada' else ''}>Encerrada</option></select></div>
    <div><span>Estratégia</span><input name="Estrategia" value="{r.get('Estratégia','Wheel')}"></div>
    <div><span>Vencimento da opção</span><input type="date" name="Vencimento" value="{r.get('Vencimento','')}"></div>
    <div><span>Contratos</span><input type="number" name="Contratos" value="{r.get('Contratos','1')}"></div>
    <div><span>Strike real</span><input type="number" step="0.01" name="Strike" value="{r.get('Strike','')}"></div>
    <div><span>Prêmio por opção</span><input type="number" step="0.01" name="Premio_opcao" value="{r.get('Premio_opcao','')}"></div>
    <div><span>Custos</span><input type="number" step="0.01" name="Custos" value="{r.get('Custos','')}"></div>
    <div><span>IRRF</span><input type="number" step="0.01" name="IRRF" value="{r.get('IRRF','')}"></div>
    <input type="hidden" name="Cotacao_atual" value="{r.get('Cotacao_atual','')}">
    <button>Salvar alterações</button><a class="button danger" href="/excluir/{oid}" onclick="return confirm('Excluir esta operação definitivamente?')">Excluir operação</a><a class="button" href="/">Voltar</a></form></section></main></body></html>'''
    return html


@app.route('/fechar/<oid>')
def fechar(oid: str):
    rows = read_csv(OPERACOES)
    r = find_row(rows, oid)
    if r:
        r['Status'] = 'Encerrada'
        write_csv(OPERACOES, rows, ['ID', 'Data abertura', 'Ativo', 'Tipo', 'Estratégia', 'Status', 'Contratos', 'Strike', 'Premio_opcao', 'Custos', 'IRRF', 'Vencimento', 'Cotacao_atual', 'Resultado_realizado'])
    return redirect(url_for('index'))


@app.route('/excluir/<oid>')
def excluir(oid: str):
    rows = read_csv(OPERACOES)
    rows = [r for r in rows if str(r.get('ID')) != str(oid)]
    write_csv(OPERACOES, rows, ['ID', 'Data abertura', 'Ativo', 'Tipo', 'Estratégia', 'Status', 'Contratos', 'Strike', 'Premio_opcao', 'Custos', 'IRRF', 'Vencimento', 'Cotacao_atual', 'Resultado_realizado'])
    return redirect(url_for('index'))



@app.route('/reabrir/<oid>')
def reabrir(oid):
    rows = read_csv(OPERACOES)
    r = find_row(rows, oid)
    if r:
        r['Status'] = 'Aberta'
        write_csv(OPERACOES, rows, ['ID', 'Data abertura', 'Ativo', 'Tipo', 'Estratégia', 'Status', 'Contratos', 'Strike', 'Premio_opcao', 'Custos', 'IRRF', 'Vencimento', 'Cotacao_atual', 'Resultado_realizado'])
    return redirect(url_for('op_fechadas'))


CSS = r'''
:root{--bg:#050b13;--panel:#101a27;--panel2:#0b1420;--line:#24364c;--txt:#f4f7ff;--muted:#91a4bb;--blue:#1478ff;--green:#21c35b;--purple:#8d45ff;--orange:#ffae22;--red:#ff6381;--cyan:#25d7de}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 45% 0%,#132035 0%,#07111e 45%,#03070d 100%);color:var(--txt);font-family:Inter,Segoe UI,Arial,sans-serif}aside{position:fixed;left:0;top:0;bottom:0;width:236px;background:linear-gradient(180deg,#081323,#03070d);border-right:1px solid #273a52;padding:22px 10px}main{margin-left:236px;padding:18px 18px 44px}.logo{display:flex;align-items:center;gap:12px}.brain{width:54px;height:54px;border:2px solid #4d8cff;border-radius:16px;display:grid;place-items:center;font-size:35px;color:#4d8cff;box-shadow:0 0 18px #1749b1}.brand{font-size:28px;font-weight:900;line-height:.95;letter-spacing:1px}.brand span,h1 span{color:#4d8cff}.strategy,label{display:block;margin:19px 0 9px;color:#4d8cff;font-size:12px;font-weight:900;letter-spacing:1.2px}.side-block{display:flex;gap:11px;align-items:center;color:#dfeaff;line-height:1.45}.side-block b{color:#4d8cff;font-size:11px}select,input{width:100%;background:#07111d;color:#fff;border:1px solid #24364c;border-radius:7px;padding:11px 12px}nav{margin-top:20px}nav a{display:block;padding:13px 15px;margin:6px 0;border-radius:9px;font-weight:800;color:#dce8fb;text-decoration:none}nav a.active{background:linear-gradient(180deg,#0871df,#06499c);box-shadow:inset 0 0 18px rgba(65,151,255,.35),0 0 16px rgba(29,128,255,.22)}.quote{border:1px solid #263d5a;border-radius:10px;padding:20px 15px;margin-top:25px;color:#4199ff;background:#091521;font-size:18px;line-height:1.35}.quote small{color:#899ab0}.version{color:#8955ff;font-weight:900;text-align:center;margin-top:26px}h1{font-size:33px;line-height:1;margin:0;font-weight:950}header p{color:#c7d5e8;margin:4px 0 14px}.metrics{display:grid;grid-template-columns:repeat(8,1fr);gap:8px}.metric{min-height:92px;background:linear-gradient(180deg,rgba(17,29,43,.96),rgba(8,17,29,.96));border:1px solid var(--line);border-radius:10px;padding:14px 10px;display:flex;align-items:center;gap:9px;box-shadow:0 0 18px rgba(0,0,0,.22)}.mi{font-size:28px}.mlabel{font-size:11px;font-weight:900;text-transform:uppercase}.mvalue{font-size:21px;font-weight:950;margin-top:8px}.msub{font-size:12px;color:#b6c3d4}.blue{border-color:#125da4;box-shadow:0 0 16px rgba(20,120,255,.18)}.green{border-color:#126d39;box-shadow:0 0 16px rgba(33,195,91,.14)}.cyan{border-color:#177a83;box-shadow:0 0 16px rgba(37,215,222,.14)}.purple{border-color:#6330aa;box-shadow:0 0 16px rgba(141,69,255,.16)}.orange{border-color:#8f6512;box-shadow:0 0 16px rgba(255,174,34,.15)}.red{border-color:#874052;box-shadow:0 0 16px rgba(255,99,129,.14)}.grid{display:grid;gap:8px;margin-top:8px}.two{grid-template-columns:1fr 1fr}.three{grid-template-columns:1.35fr .8fr .7fr}.four{grid-template-columns:1.1fr 1.1fr .8fr .9fr}.panel{background:linear-gradient(180deg,rgba(17,29,43,.96),rgba(8,17,29,.96));border:1px solid #26384f;border-radius:10px;padding:14px;box-shadow:0 0 18px rgba(0,0,0,.22);overflow:auto}h2{font-size:16px;margin:0 0 10px;text-transform:uppercase}.chart{width:100%;height:220px}.donut-wrap{display:flex;align-items:center;gap:8px}.donut{width:46%;min-width:165px}.legend{flex:1}.legend div{margin:8px 0;font-size:12px}.legend span{display:inline-block;width:11px;height:11px;margin-right:6px;border-radius:2px}.legend em{float:right;font-style:normal;color:#fff}.legend small{display:block;color:#9fb0c5;margin-left:21px}.gauge{text-align:center}.gauge svg{width:100%;max-height:165px}.gauge-num{font-size:30px;font-weight:900;margin:0 0 4px;position:relative;z-index:2}.badge{display:inline-block;background:#169c3a;border-radius:5px;padding:5px 22px;font-weight:800;margin:4px}.gauge-legend{display:flex;justify-content:center;gap:8px;margin:8px auto 5px;max-width:360px}.gauge-legend span{flex:1;border:1px solid #26384f;border-radius:6px;padding:5px 4px;font-size:11px;color:#dce8fb;text-align:center}.gauge-legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px}.lg-low{background:#f04b3d}.lg-mid{background:#ffcc21}.lg-high{background:#23b64a}table{width:100%;border-collapse:collapse;font-size:13px}th{background:#192434;color:#dce8fb;text-align:left;padding:8px}td{border-bottom:1px solid #1c2b3f;padding:7px;color:#edf4ff}.ops{min-width:1120px}.ops th,.ops td{white-space:nowrap}.ops th:last-child,.ops td.actions{position:sticky;right:0;background:#101a27;z-index:3;box-shadow:-8px 0 10px rgba(0,0,0,.25)}.warn{color:#ff6d6d;font-weight:800}.ok{color:#7df097}.button{display:block;margin:10px auto 0;text-align:center;max-width:245px;padding:8px 12px;background:#0b4c98;border:1px solid #2589ff;border-radius:7px;color:#fff;text-decoration:none;font-weight:800}.summary p{border-bottom:1px solid #1f2d40;padding:9px 0;margin:0}.summary b{float:right}.form{display:grid;grid-template-columns:repeat(7,1fr);gap:8px}.labeled div span{display:block;color:#9fb8d8;font-size:11px;font-weight:900;text-transform:uppercase;margin:0 0 5px}.hint{display:block;color:#9fb0c5;margin-top:10px}.actions a{display:inline-grid;place-items:center;text-decoration:none;margin-right:8px;font-size:17px;color:#fff;border:1px solid #34506f;border-radius:6px;width:28px;height:28px;background:#111f31;font-weight:900}.actions a:hover{background:#1d3554}.badge.low{background:#b63131}.badge.mid{background:#b99a18;color:#101010}.badge.high{background:#169c3a}.danger{background:#7a1522!important;border-color:#ff6381!important}.edit-page{margin-left:0;max-width:1180px;margin-right:auto}.form button{background:linear-gradient(180deg,#0871df,#06499c);border:1px solid #278fff;color:white;font-weight:900;border-radius:8px;padding:11px}footer{position:fixed;left:0;right:0;bottom:0;background:#07111d;border-top:1px solid #26384f;color:#6d7d91;text-align:center;padding:8px;font-size:12px}@media(max-width:1350px){.metrics{grid-template-columns:repeat(4,1fr)}}@media(max-width:1100px){aside{position:relative;width:100%;height:auto}main{margin-left:0}.two,.three,.four,.form{grid-template-columns:1fr}.metrics{grid-template-columns:repeat(2,1fr)}.donut-wrap{display:block}.donut{width:100%}footer{position:static}}@media(max-width:640px){.metrics{grid-template-columns:1fr}.actions a{width:34px;height:34px;font-size:20px}.ops{min-width:1180px}}
/* v1.8 - velocímetro premium */
.no-summary{grid-template-columns:1.1fr 1.1fr .9fr}.gauge-v19{position:relative;padding-top:0}.gauge-v19 svg{width:100%;max-height:205px;filter:drop-shadow(0 0 10px rgba(10,115,255,.15))}.gauge-v19 .gauge-back{fill:none;stroke:#07101b;stroke-width:30;stroke-linecap:butt}.gauge-v19 .gauge-rim{fill:none;stroke:#43566d;stroke-width:2.2;opacity:.9}.gauge-v19 .gauge-seg{fill:none;stroke-width:17.5;stroke-linecap:butt;filter:drop-shadow(0 0 5px rgba(255,220,30,.18))}.gauge-v19 .g-label{fill:#f4f7ff;font-size:13px;font-weight:900;text-anchor:middle;paint-order:stroke;stroke:#07101b;stroke-width:3px}.gauge-v19 .g-value{fill:#f8fbff;font-size:31px;font-weight:950;text-anchor:middle;letter-spacing:.5px;paint-order:stroke;stroke:#07101b;stroke-width:3px}.gauge-v19 .badge{min-width:118px;border:1px solid #69ff35;background:linear-gradient(180deg,rgba(9,35,28,.98),rgba(6,18,20,.98));color:#78ff25;border-radius:9px;padding:5px 24px;font-size:18px;box-shadow:inset 0 0 18px rgba(61,255,30,.08),0 0 14px rgba(79,255,30,.12)}.gauge-v19 .badge.low{border-color:#ff3b2f;color:#ff584d;background:rgba(35,12,13,.96)}.gauge-v19 .badge.mid{border-color:#82ff2e;color:#82ff2e;background:rgba(8,30,22,.96)}.gauge-v19 .badge.high{border-color:#38ff6c;color:#38ff6c;background:rgba(6,38,22,.96)}.panel:has(.gauge-v19){border-color:#245886;box-shadow:inset 0 0 38px rgba(18,94,170,.08),0 0 20px rgba(0,0,0,.28)}


/* ===== DASHBOARD WHEEL v2.7 ===== */
body{
 background:#0b1220;
 background-image:radial-gradient(circle at top,#16243b 0%,#0b1220 45%,#050811 100%);
}
aside{
 background:#0d1526;
 border-right:1px solid #1f2c45;
 box-shadow:0 0 40px rgba(0,0,0,.45);
}
.panel,.metric{
 background:linear-gradient(180deg,#111b2f,#0c1525);
 border:1px solid #23314b;
 border-radius:22px;
 box-shadow:0 12px 30px rgba(0,0,0,.35);
}
.metric{
 padding:18px;
}
.metric .mvalue{
 font-size:1.6rem;
 font-weight:800;
}
h1,h2{
 letter-spacing:.5px;
}
table{
 border-radius:18px;
 overflow:hidden;
}
button,.button{
 border-radius:14px;
 background:#1e88ff;
}
'''





@app.route('/op-fechadas')
def op_fechadas():
    ops, fechadas_csv, cfg = load_all()
    fechadas = [o for o in ops if str(o.get('Status','')).lower() == 'encerrada']

    total_lucro = sum(float(o.get('Premio_liquido',0)) for o in fechadas)
    lucro_mes = sum(float(o.get('Premio_liquido',0))
                    for o in fechadas
                    if o.get('Mes_abertura') == current_month_label())
    roi_medio = (sum(float(o.get('ROI',0)) for o in fechadas) / len(fechadas)) if fechadas else 0

    linhas = []
    for o in fechadas:
        oid = o.get('ID','')
        linhas.append(
            f"<tr><td>{infer_acao_from_option(str(o.get('Ativo','')))}</td>"
            f"<td>{o.get('Ativo','')}</td>"
            f"<td>{o.get('Tipo','')}</td>"
            f"<td>{brl(float(o.get('Premio_liquido',0)))}</td>"
            f"<td>{o.get('Mes_abertura','')}</td>"
            f"<td class='actions'>"
            f"<a href='/editar/{oid}' title='Editar'>✎</a>"
            f"<a href='/excluir/{oid}' title='Excluir'>×</a>"
            f"<a href='/reabrir/{oid}' title='Reabrir'>↩</a>"
            f"</td></tr>"
        )

    tabela = ''.join(linhas) if linhas else "<tr><td colspan='6'>Nenhuma operação fechada.</td></tr>"

    return f'''<!doctype html>
    <html lang="pt-BR"><head><meta charset="utf-8">
    <title>Cortex Invest PRO v3.2.3 - Operações Fechadas</title>
    <style>{CSS}</style></head>
    <body>
    <main style="margin-left:0;padding:25px">
      <h1>Operações <span>Fechadas</span></h1>

      <section class="metrics">
        {metric_card('💰','LUCRO DO MÊS',brl(lucro_mes),current_month_label(),'green')}
        {metric_card('🏦','LUCRO ACUMULADO',brl(total_lucro),'Todas as operações','purple')}
        {metric_card('🎯','ROI MÉDIO',pct(roi_medio),'Operações fechadas','cyan')}
        {metric_card('📁','TOTAL FECHADAS',str(len(fechadas)),'Operações encerradas','blue')}
      </section>

      <section class="grid three">
        <div class="panel">
          <h2>VELOCÍMETRO ROI MÉDIO</h2>
          {gauge(roi_medio)}
        </div>
        <div class="panel">
          <h2>DISTRIBUIÇÃO DOS PRÊMIOS</h2>
          {donut_chart(fechadas[:5]) if fechadas else '<p>Sem dados.</p>'}
        </div>
        <div class="panel">
          <h2>RESUMO</h2>
          <p><b>Lucro do mês:</b> {brl(lucro_mes)}</p>
          <p><b>Lucro acumulado:</b> {brl(total_lucro)}</p>
          <p><b>Operações:</b> {len(fechadas)}</p>
        </div>
      </section>

      <section class="panel" style="margin-top:15px">
        <h2>Operações Fechadas</h2>
        <table class="ops">
        <thead><tr><th>Ação</th><th>Opção</th><th>Tipo</th><th>Lucro</th><th>Mês</th><th>Ações</th></tr></thead>
        <tbody>{tabela}</tbody>
        </table>
      </section>

      <p style="margin-top:20px"><a class="button" href="/">Voltar ao Dashboard</a></p>
    </main>
    </body></html>'''


# ===== Backup SQLite v3.2 =====
@app.route('/backup-db')
def backup_db():
    from flask import send_file
    if DB.exists():
        return send_file(DB, as_attachment=True, download_name='cortex_backup.db')
    return "Banco de dados não encontrado.", 404

@app.route('/restaurar-db')
def restaurar_db_info():
    return '''
    <h2>Restaurar Backup</h2>
    <p>No Render Free, envie manualmente o arquivo cortex.db para a pasta data/ antes do deploy.</p>
    <p>Próxima versão: upload direto pelo navegador.</p>
    <p><a href="/">Voltar</a></p>
    '''
# ===== fim Backup SQLite =====


@app.route('/backup')
def backup_center():
    return '''
    <html><head><title>Cortex Invest PRO v3.2.3 - Backup</title></head>
    <body style="font-family:Arial;background:#07111d;color:white;padding:30px">
    <h1>💾 Central de Backup</h1>
    <p>Proteja suas operações reais baixando o banco regularmente.</p>
    <p><a href="/backup-db">⬇️ Baixar Backup do Banco (cortex.db)</a></p>
    <p><a href="/">← Voltar ao Dashboard</a></p>
    </body></html>
    '''

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

# TODO v2.7: página Op. Fechadas e velocímetro meta 5%


# v2.9 - arquitetura simplificada
# Operações fechadas são obtidas de operacoes.csv usando Status='Encerrada'

# v2.9.1 OP_FECHADAS_TEMPLATE
# return render_template('op_fechadas_v291.html') na rota /op-fechadas


# MENU_V323
# Novo item sugerido para a barra lateral:
# 💾 Backup -> /backup
# Estilo recomendado:
# Dashboard | Op. Abertas | Op. Fechadas | Histórico | Backup | Configurações
