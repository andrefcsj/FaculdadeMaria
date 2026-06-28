from __future__ import annotations

import csv
import math
import json
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Tuple

from flask import Flask, redirect, request, url_for, jsonify

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
OPERACOES = DATA / "operacoes.csv"
FECHADAS = DATA / "fechadas.csv"
CONFIG = DATA / "config.csv"

app = Flask(__name__)

MESES = ["jan/26", "fev/26", "mar/26", "abr/26", "mai/26", "jun/26", "jul/26", "ago/26", "set/26", "out/26", "nov/26", "dez/26"]
MONTH_NAMES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


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
        nota = "★★★★★" if roi >= 2 else "★★★★☆" if roi >= 1.5 else "★★★☆☆" if roi >= 1 else "★★☆☆☆"
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
    lucro_mes = 0.0
    for f in fechadas:
        if f.get("Mes") == "mai/26":
            lucro_mes += fnum(f.get("Lucro_tributavel"))
    darf = lucro_mes * cfg.get("Aliquota IR opcoes", 0.15)
    roi_mes = lucro_mes / capital_total * 100 if capital_total else 0
    roi_abertas = premios_ativos / capital_comp * 100 if capital_comp else 0
    roi_medio_abertas = (sum(float(o.get("ROI", 0)) for o in abertas) / len(abertas)) if abertas else 0
    return {"capital_total": capital_total, "capital_comp": capital_comp, "caixa": max(capital_total - capital_comp, 0), "premios_ativos": premios_ativos, "lucro_mes": lucro_mes, "darf": darf, "roi_mes": roi_mes, "roi_abertas": roi_abertas, "roi_medio_abertas": roi_medio_abertas, "abertas": len(abertas), "encerradas": len(ops) - len(abertas)}


def monthly(ops: List[Dict[str, object]], fechadas: List[Dict[str, str]], cfg: Dict[str, float]) -> List[Dict[str, float | str]]:
    base = []
    patrimonio = cfg.get("Capital total inicial", 4000.0)
    for m in MESES:
        lucro = sum(fnum(f.get("Lucro_tributavel")) for f in fechadas if f.get("Mes") == m)
        premios = sum(float(o["Premio_liquido"]) for o in ops if o.get("Mes_abertura") == m)
        darf = lucro * cfg.get("Aliquota IR opcoes", 0.15)
        patrimonio += lucro + premios * 0.15
        roi = lucro / cfg.get("Capital total inicial", 4000.0) * 100 if cfg.get("Capital total inicial", 0) else 0
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


def gauge(value: float) -> str:
    angle = -135 + min(max(value, 0), 5) / 5 * 270
    return f'''<div class="gauge"><svg viewBox="0 0 260 160"><path d="M35 130 A95 95 0 0 1 225 130" fill="none" stroke="#1d2a3b" stroke-width="22"/><path d="M35 130 A95 95 0 0 1 75 50" fill="none" stroke="#f04b3d" stroke-width="18"/><path d="M75 50 A95 95 0 0 1 130 35" fill="none" stroke="#f2df34" stroke-width="18"/><path d="M130 35 A95 95 0 0 1 185 50" fill="none" stroke="#b8ec35" stroke-width="18"/><path d="M185 50 A95 95 0 0 1 225 130" fill="none" stroke="#23b64a" stroke-width="18"/><line x1="130" y1="130" x2="130" y2="55" stroke="#dce6f2" stroke-width="6" transform="rotate({angle:.1f} 130 130)"/><circle cx="130" cy="130" r="8" fill="#dce6f2"/><text x="130" y="42" fill="#e7f0ff" text-anchor="middle" font-size="13">2%</text><text x="40" y="128" fill="#e7f0ff" text-anchor="middle" font-size="13">0%</text><text x="220" y="128" fill="#e7f0ff" text-anchor="middle" font-size="13">5%</text></svg><div class="gauge-num">{pct(value)}</div><div class="badge">ÓTIMO</div><small>Meta: &gt; 1,00%</small></div>'''


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
        body.append(f"""<tr><td>{o.get('Ativo')}</td><td>{o.get('Tipo')}</td><td>{int(float(o.get('Contratos_n',0)))}</td><td>{brl(float(o.get('Strike_n',0)))}</td><td>{brl(float(o.get('Premio_liquido',0)))}</td><td>{brl(float(o.get('Capital',0)))}</td><td>{o.get('Vencimento_fmt','')}</td><td>{int(float(o.get('Dias',0)))}</td><td>{pct(float(o.get('ROI',0)))}</td><td>{o.get('Nota')}</td><td class="{alert_cls}">{o.get('Alerta')}</td><td class="actions"><a title="Editar operação" href="/editar/{oid}">✏️</a><a title="Fechar operação" href="/fechar/{oid}" onclick="return confirm('Fechar esta operação?')">✅</a><a title="Excluir operação" href="/excluir/{oid}" onclick="return confirm('Excluir esta operação definitivamente?')">🗑️</a></td></tr>""")
    return "".join(body)


@app.route("/", methods=["GET"])
def index():
    ops, fechadas, cfg = load_all()
    ind = metrics(ops, fechadas, cfg)
    hist = monthly(ops, fechadas, cfg)
    abertas = [o for o in ops if str(o.get("Status", "")).lower() == "aberta"]
    top = sorted(abertas, key=lambda x: float(x["Premio_liquido"]), reverse=True)[:5]
    hist_nonzero = [r for r in hist if float(r["lucro"]) or float(r["premios"] or 0)]
    historico_table = "".join([f'<tr><td>{r["mes"]}</td><td>{brl(float(r["lucro"]))}</td><td>{brl(float(r["darf"]))}</td><td>{brl(float(r["premios"]))}</td><td>{pct(float(r["roi"]))} ↑</td></tr>' for r in reversed(hist_nonzero[-5:])])
    top_table = "".join([f'<tr><td>{o.get("Ativo")}</td><td>{o.get("Tipo")}</td><td>{brl(float(o["Strike_n"]))}</td><td>{brl(float(o["Premio_liquido"]))}</td><td>{pct(float(o["ROI"]))}</td></tr>' for o in top])
    html = f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Cortex Invest PRO</title><style>{CSS}</style></head><body>
    <aside><div class="logo"><div class="brain">✺</div><div class="brand">CORTEX<br><span>INVEST</span></div></div><div class="strategy">WHEEL STRATEGY</div><div class="side-block">📅<div><b>DATA ATUALIZAÇÃO</b><br>30/05/2026<br>12:45:28</div></div><label>MÊS SELECIONADO</label><select><option>mai/26</option></select><nav><a class="active">▦ VISÃO GERAL</a><a>▧ OPERAÇÕES ABERTAS</a><a>▣ HISTÓRICO MENSAL</a><a>⌁ DESEMPENHO</a><a>⚙ ATIVOS</a><a>▤ RELATÓRIOS</a><a>⚙ CONFIGURAÇÕES</a></nav><div class="quote">“A consistência é o que transforma estratégia em patrimônio.”<br><small>– CORTEX INVEST</small></div><div class="version">VERSÃO 1.0</div></aside>
    <main><header><h1>DASHBOARD <span>WHEEL</span></h1><p>Painel automático com prêmios mensais, ROI abertas e histórico por mês</p></header>
    <section class="metrics">
    {metric_card('🏦','CAPITAL TOTAL',brl(float(ind['capital_total'])),'','blue')}{metric_card('🔒','CAPITAL COMPROMETIDO',brl(float(ind['capital_comp'])),'','green')}{metric_card('💼','CAIXA LIVRE',brl(float(ind['caixa'])),'','cyan')}{metric_card('🎁','PRÊMIOS ATIVOS',brl(float(ind['premios_ativos'])),'Total em aberto','purple')}{metric_card('📈','LUCRO DO MÊS',brl(float(ind['lucro_mes'])),'mai/26','orange')}{metric_card('🏛️','DARF DO MÊS',brl(float(ind['darf'])),'mai/26','red')}{metric_card('%','ROI MÊS',pct(float(ind['roi_mes'])),'mai/26','cyan')}{metric_card('🎯','ROI ABERTAS',pct(float(ind['roi_abertas'])),'sobre capital comp.','green')}
    </section>
    <section class="grid two"><div class="panel"><h2>EVOLUÇÃO DO LUCRO (R$)</h2>{line_chart(hist,'lucro')}</div><div class="panel"><h2>PRÊMIOS RECEBIDOS POR MÊS (R$)</h2>{bar_chart(hist,'premios')}</div></section>
    <section class="grid three"><div class="panel wide"><h2>EVOLUÇÃO DO PATRIMÔNIO (R$)</h2>{line_chart(hist,'patrimonio','#a85cff')}</div><div class="panel"><h2>DISTRIBUIÇÃO DOS PRÊMIOS ATIVOS</h2>{donut_chart(abertas)}</div><div class="panel"><h2>VELOCÍMETRO ROI MÉDIO (ABERTAS)</h2>{gauge(float(ind['roi_medio_abertas']))}</div></section>
    <section class="grid four"><div class="panel"><h2>HISTÓRICO MENSAL</h2><table><thead><tr><th>Mês</th><th>Lucro</th><th>DARF</th><th>Prêmios</th><th>ROI</th></tr></thead><tbody>{historico_table}</tbody></table></div><div class="panel"><h2>TOP 5 OPERAÇÕES (PRÊMIO ATIVO)</h2><table><thead><tr><th>Ativo</th><th>Tipo</th><th>Strike</th><th>Prêmio</th><th>ROI</th></tr></thead><tbody>{top_table}</tbody></table><a href="#ops" class="button">VER TODAS AS OPERAÇÕES →</a></div><div class="panel"><h2>STATUS DAS OPERAÇÕES</h2><div class="status-donut">{donut_chart([{'Ativo':'Abertas','Premio_liquido':float(ind['abertas'])},{'Ativo':'Encerradas','Premio_liquido':float(ind['encerradas'])}])}</div></div><div class="panel summary"><h2>RESUMO GERAL</h2><p>▣ Total de Operações <b>{len(ops)}</b></p><p>▧ Operações Abertas <b>{ind['abertas']}</b></p><p>⊗ Operações Encerradas <b>{ind['encerradas']}</b></p><p>◴ Dias em Média (Abertas) <b>{(sum(float(o['Dias']) for o in abertas)/len(abertas)) if abertas else 0:.1f}</b></p><p>✪ Prêmio Médio por Operação <b>{brl((sum(float(o['Premio_liquido']) for o in abertas)/len(abertas)) if abertas else 0)}</b></p></div></section>
    <section class="panel" id="ops"><h2>OPERAÇÕES ABERTAS</h2><table class="ops"><thead><tr><th>Ativo</th><th>Tipo</th><th>Contratos</th><th>Strike</th><th>Prêmio líquido</th><th>Capital</th><th>Vencimento</th><th>Dias</th><th>ROI</th><th>Nota</th><th>Alerta</th><th>Ações</th></tr></thead><tbody>{rows_html(abertas)}</tbody></table></section>
    <section class="panel"><h2>CADASTRAR NOVA OPERAÇÃO</h2><form method="post" action="/nova" class="form labeled">
      <div><span>Código da opção</span><input id="ativo" name="Ativo" placeholder="Ex: BBDCS167" required onblur="buscarCotacao()"></div>
      <div><span>Tipo</span><select name="Tipo"><option>PUT</option><option>CALL</option></select></div>
      <div><span>Estratégia</span><select name="Estrategia"><option>Wheel</option><option>Pozinho</option></select></div>
      <div><span>Status</span><select name="Status"><option>Aberta</option><option>Encerrada</option></select></div>
      <div><span>Vencimento da opção</span><input type="date" name="Vencimento" required></div>
      <div><span>Contratos</span><input name="Contratos" type="number" min="1" value="1"></div>
      <div><span>Strike real</span><input name="Strike" type="number" step="0.01" placeholder="Ex: 16,89"></div>
      <div><span>Prêmio por opção</span><input name="Premio_opcao" type="number" step="0.01" placeholder="Ex: 0,33"></div>
      <div><span>Custos</span><input name="Custos" type="number" step="0.01" value="1.07"></div>
      <div><span>IRRF</span><input name="IRRF" type="number" step="0.01" value="0.04"></div>
      <div><span>Cotação atual da ação</span><input id="cotacao" name="Cotacao_atual" type="number" step="0.01" placeholder="Busca automática"></div>
      <button>Salvar operação</button>
    </form><small class="hint">A cotação tenta buscar automaticamente pela ação originária. Se não encontrar, você pode preencher manualmente.</small></section>
    <script>
    async function buscarCotacao(){{
      const ativo=document.getElementById('ativo').value.trim();
      const campo=document.getElementById('cotacao');
      if(!ativo) return;
      campo.placeholder='Buscando...';
      try{{
        const r=await fetch('/cotacao?codigo='+encodeURIComponent(ativo));
        const d=await r.json();
        if(d.cotacao){{ campo.value=Number(d.cotacao).toFixed(2); campo.placeholder='Cotação atual'; }}
        else {{ campo.placeholder='Não encontrada. Digite manualmente'; }}
      }}catch(e){{ campo.placeholder='Digite manualmente'; }}
    }}
    </script>
    </main><footer>🛡️ Dashboard protegido contra edição. Os dados são atualizados automaticamente. &nbsp; CORTEX INVEST v1.0 • WHEEL STRATEGY • DISCIPLINA, GESTÃO E CONSISTÊNCIA</footer></body></html>'''
    return html


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
    rows.append(row)
    write_csv(OPERACOES, rows, ["ID", "Data abertura", "Ativo", "Tipo", "Estratégia", "Status", "Contratos", "Strike", "Premio_opcao", "Custos", "IRRF", "Vencimento", "Cotacao_atual", "Resultado_realizado"])
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
    <div><span>Cotação atual da ação</span><input type="number" step="0.01" name="Cotacao_atual" value="{r.get('Cotacao_atual','')}"></div>
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


CSS = r'''
:root{--bg:#050b13;--panel:#101a27;--panel2:#0b1420;--line:#24364c;--txt:#f4f7ff;--muted:#91a4bb;--blue:#1478ff;--green:#21c35b;--purple:#8d45ff;--orange:#ffae22;--red:#ff6381;--cyan:#25d7de}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 45% 0%,#132035 0%,#07111e 45%,#03070d 100%);color:var(--txt);font-family:Inter,Segoe UI,Arial,sans-serif}aside{position:fixed;left:0;top:0;bottom:0;width:236px;background:linear-gradient(180deg,#081323,#03070d);border-right:1px solid #273a52;padding:22px 10px}main{margin-left:236px;padding:18px 18px 44px}.logo{display:flex;align-items:center;gap:12px}.brain{width:54px;height:54px;border:2px solid #4d8cff;border-radius:16px;display:grid;place-items:center;font-size:35px;color:#4d8cff;box-shadow:0 0 18px #1749b1}.brand{font-size:28px;font-weight:900;line-height:.95;letter-spacing:1px}.brand span,h1 span{color:#4d8cff}.strategy,label{display:block;margin:19px 0 9px;color:#4d8cff;font-size:12px;font-weight:900;letter-spacing:1.2px}.side-block{display:flex;gap:11px;align-items:center;color:#dfeaff;line-height:1.45}.side-block b{color:#4d8cff;font-size:11px}select,input{width:100%;background:#07111d;color:#fff;border:1px solid #24364c;border-radius:7px;padding:11px 12px}nav{margin-top:20px}nav a{display:block;padding:13px 15px;margin:6px 0;border-radius:9px;font-weight:800;color:#dce8fb;text-decoration:none}nav a.active{background:linear-gradient(180deg,#0871df,#06499c);box-shadow:inset 0 0 18px rgba(65,151,255,.35),0 0 16px rgba(29,128,255,.22)}.quote{border:1px solid #263d5a;border-radius:10px;padding:20px 15px;margin-top:25px;color:#4199ff;background:#091521;font-size:18px;line-height:1.35}.quote small{color:#899ab0}.version{color:#8955ff;font-weight:900;text-align:center;margin-top:26px}h1{font-size:33px;line-height:1;margin:0;font-weight:950}header p{color:#c7d5e8;margin:4px 0 14px}.metrics{display:grid;grid-template-columns:repeat(8,1fr);gap:8px}.metric{min-height:92px;background:linear-gradient(180deg,rgba(17,29,43,.96),rgba(8,17,29,.96));border:1px solid var(--line);border-radius:10px;padding:14px 10px;display:flex;align-items:center;gap:9px;box-shadow:0 0 18px rgba(0,0,0,.22)}.mi{font-size:28px}.mlabel{font-size:11px;font-weight:900;text-transform:uppercase}.mvalue{font-size:21px;font-weight:950;margin-top:8px}.msub{font-size:12px;color:#b6c3d4}.blue{border-color:#125da4;box-shadow:0 0 16px rgba(20,120,255,.18)}.green{border-color:#126d39;box-shadow:0 0 16px rgba(33,195,91,.14)}.cyan{border-color:#177a83;box-shadow:0 0 16px rgba(37,215,222,.14)}.purple{border-color:#6330aa;box-shadow:0 0 16px rgba(141,69,255,.16)}.orange{border-color:#8f6512;box-shadow:0 0 16px rgba(255,174,34,.15)}.red{border-color:#874052;box-shadow:0 0 16px rgba(255,99,129,.14)}.grid{display:grid;gap:8px;margin-top:8px}.two{grid-template-columns:1fr 1fr}.three{grid-template-columns:1.35fr .8fr .7fr}.four{grid-template-columns:1.1fr 1.1fr .8fr .9fr}.panel{background:linear-gradient(180deg,rgba(17,29,43,.96),rgba(8,17,29,.96));border:1px solid #26384f;border-radius:10px;padding:14px;box-shadow:0 0 18px rgba(0,0,0,.22);overflow:hidden}h2{font-size:16px;margin:0 0 10px;text-transform:uppercase}.chart{width:100%;height:220px}.donut-wrap{display:flex;align-items:center;gap:8px}.donut{width:46%;min-width:165px}.legend{flex:1}.legend div{margin:8px 0;font-size:12px}.legend span{display:inline-block;width:11px;height:11px;margin-right:6px;border-radius:2px}.legend em{float:right;font-style:normal;color:#fff}.legend small{display:block;color:#9fb0c5;margin-left:21px}.gauge{text-align:center}.gauge svg{width:100%;max-height:150px}.gauge-num{font-size:30px;font-weight:900;margin-top:-22px}.badge{display:inline-block;background:#169c3a;border-radius:5px;padding:5px 22px;font-weight:800;margin:4px}table{width:100%;border-collapse:collapse;font-size:13px}th{background:#192434;color:#dce8fb;text-align:left;padding:8px}td{border-bottom:1px solid #1c2b3f;padding:7px;color:#edf4ff}.ops th,.ops td{white-space:nowrap}.warn{color:#ff6d6d;font-weight:800}.ok{color:#7df097}.button{display:block;margin:10px auto 0;text-align:center;max-width:245px;padding:8px 12px;background:#0b4c98;border:1px solid #2589ff;border-radius:7px;color:#fff;text-decoration:none;font-weight:800}.summary p{border-bottom:1px solid #1f2d40;padding:9px 0;margin:0}.summary b{float:right}.form{display:grid;grid-template-columns:repeat(6,1fr);gap:8px}.labeled div span{display:block;color:#9fb8d8;font-size:11px;font-weight:900;text-transform:uppercase;margin:0 0 5px}.hint{display:block;color:#9fb0c5;margin-top:10px}.actions a{display:inline-block;text-decoration:none;margin-right:8px;font-size:16px}.danger{background:#7a1522!important;border-color:#ff6381!important}.edit-page{margin-left:0;max-width:1180px;margin-right:auto}.form button{background:linear-gradient(180deg,#0871df,#06499c);border:1px solid #278fff;color:white;font-weight:900;border-radius:8px;padding:11px}footer{position:fixed;left:0;right:0;bottom:0;background:#07111d;border-top:1px solid #26384f;color:#6d7d91;text-align:center;padding:8px;font-size:12px}@media(max-width:1100px){aside{position:relative;width:100%;height:auto}main{margin-left:0}.metrics,.two,.three,.four,.form{grid-template-columns:1fr}.donut-wrap{display:block}.donut{width:100%}footer{position:static}}'''

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
