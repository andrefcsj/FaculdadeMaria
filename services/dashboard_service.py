"""Adaptador de apresentação do Dashboard Executivo.

Este módulo não cria regras financeiras. Ele apenas organiza métricas já
calculadas pela aplicação em um view model estável para a interface.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Mapping, Sequence
from services.concentration_service import ATTENTION_ASSET_CONCENTRATION, MAX_ASSET_CONCENTRATION
from services.exercise_probability_service import estimate_operation_exercise_probability
from services.option_cycle_service import build_cycle_groups, classify_option_cycle


def _number(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _operation_expiry(value: object) -> date | None:
    text = str(value or "").strip()
    for parser in (date.fromisoformat, lambda raw: date(int(raw[6:]), int(raw[3:5]), int(raw[:2]))):
        try:
            return parser(text)
        except (TypeError, ValueError):
            continue
    return None


def _asset_from_option(option_code: object) -> str:
    letters = "".join(character for character in str(option_code or "").upper() if character.isalpha())
    return letters[:4] if letters else "N/D"


def _underlying_asset(operation: Mapping[str, object]) -> str:
    explicit = str(operation.get("Ativo_subjacente") or "").strip().upper()
    if explicit:
        return explicit
    root = _asset_from_option(operation.get("Ativo"))
    return {
        "BBDC": "BBDC4", "ITSA": "ITSA4", "GOAU": "GOAU4",
        "CPLE": "CPLE3", "PETR": "PETR4", "VALE": "VALE3",
        "BBAS": "BBAS3", "ABEV": "ABEV3",
    }.get(root, root)


def _has_exercise_interest(operation: Mapping[str, object]) -> bool:
    value = operation.get("Interesse_exercicio", False)
    return value if isinstance(value, bool) else str(value or "").strip().lower() in {"1", "true", "sim", "yes", "s"}


def _is_in_the_money(operation: Mapping[str, object]) -> bool:
    spot = _number(operation.get("Cotacao_n"))
    strike = _number(operation.get("Strike_n"))
    option_type = str(operation.get("Tipo", "PUT")).upper()
    return bool(spot > 0 and strike > 0 and ((option_type == "PUT" and spot <= strike) or (option_type == "CALL" and spot >= strike)))


def _attention_item(option_code: object, categories: list[dict[str, str]]) -> dict[str, object]:
    rank = {"info": 0, "medium": 1, "high": 2, "critical": 3}
    severity = max((category["severity"] for category in categories), key=lambda value: rank[value])
    labels = {"critical": "Crítico", "high": "Acompanhar", "medium": "Observar", "info": "Informação"}
    return {"option_code": option_code, "categories": tuple(categories), "message": " • ".join(category["message"] for category in categories), "severity": severity, "label": labels[severity]}


@dataclass(frozen=True)
class DashboardViewModel:
    patrimony: float
    equities_value: float
    current_month_filter: str
    premiums_month: float
    premiums_total: float
    premiums_retained: float
    average_roi: float
    monthly_roi: float
    weekly_roi: float
    monthly_target_roi: float
    weekly_target_roi: float
    allocated_capital: float
    commitment_items: tuple[Mapping[str, object], ...]
    available_to_trade: float
    open_puts: int
    open_operations: int
    next_expiry: Mapping[str, object] | None
    projected_roi: float
    broker_cash_balance: float
    ai_summary: str
    ai_tone: str
    portfolio: tuple[Mapping[str, object], ...]
    roll_candidates: tuple[Mapping[str, object], ...]
    attention_items: tuple[Mapping[str, object], ...]
    today_scenario: tuple[Mapping[str, object], ...]
    open_positions: tuple[Mapping[str, object], ...]
    upcoming_expiries: tuple[Mapping[str, object], ...]
    goals: tuple[Mapping[str, object], ...]
    stats: tuple[Mapping[str, object], ...]
    chart_labels: tuple[str, ...]
    chart_premiums: tuple[float, ...]
    darf_alert: Mapping[str, object]


def _estimated_darf_due_date(competence: str) -> str:
    """Último dia útil (segunda a sexta) do mês seguinte, como estimativa."""
    try:
        year, month = (int(part) for part in competence.split("-"))
        next_month = date(year + (month == 12), 1 if month == 12 else month + 1, 1)
        following = date(next_month.year + (next_month.month == 12), 1 if next_month.month == 12 else next_month.month + 1, 1)
        due = following - timedelta(days=1)
        while due.weekday() >= 5:
            due -= timedelta(days=1)
        return due.isoformat()
    except (TypeError, ValueError):
        return ""


def build_dashboard_view_model(
    operations: Sequence[Mapping[str, object]],
    closed_operations: Sequence[Mapping[str, object]],
    indicators: Mapping[str, object],
    history: Sequence[Mapping[str, object]],
    config: Mapping[str, object],
    option_quotes: Mapping[str, Mapping[str, object]] | None = None,
    darf_projection: Mapping[str, object] | None = None,
    equity_holdings: Sequence[Mapping[str, object]] = (),
) -> DashboardViewModel:
    """Organiza dados existentes para o Dashboard sem recalcular o domínio."""
    open_operations = [
        operation for operation in operations
        if str(operation.get("Status", "")).lower() == "aberta"
    ]
    open_options = [
        operation for operation in open_operations
        if str(operation.get("Tipo", "PUT")).upper() in {"PUT", "CALL"}
    ]
    open_puts = [
        operation for operation in open_operations
        if str(operation.get("Tipo", "PUT")).upper() == "PUT"
    ]
    contract_size = _number(config.get("Tamanho contrato opcoes"), 100)
    commitment_items = []
    for operation in open_puts:
        strategy = str(operation.get("Estratégia", "Venda")).strip().lower()
        if strategy == "compra":
            continue
        quantity = int(_number(operation.get("Contratos_n", operation.get("Contratos")), 1) * contract_size)
        commitment_items.append({
            "kind": "put",
            "asset": _underlying_asset(operation),
            "option_code": str(operation.get("Ativo", "N/D")).upper(),
            "quantity": quantity,
            "total": _number(operation.get("Capital_nominal", operation.get("Capital"))),
            "expiry": operation.get("Vencimento_fmt", ""),
            "days": int(_number(operation.get("Dias"))),
            "logo_url": f"https://raw.githubusercontent.com/thefintz/icones-b3/main/icones/{_underlying_asset(operation)}.png",
        })

    holding_by_asset = {
        str(holding.get("asset", "")).upper(): holding
        for holding in equity_holdings
        if str(holding.get("asset", "")).upper() != "LFTB11"
    }
    for operation in open_options:
        strategy = str(operation.get("Estratégia", "")).strip().lower()
        if str(operation.get("Tipo", "")).upper() != "CALL" or strategy not in {"venda coberta", "call coberta"}:
            continue
        asset = _underlying_asset(operation)
        holding = holding_by_asset.get(asset, {})
        quantity = int(_number(operation.get("Contratos_n", operation.get("Contratos")), 1) * contract_size)
        covered_quantity = min(quantity, int(_number(holding.get("quantity"))))
        unit_cost = _number(holding.get("cash_cost_per_share"))
        commitment_items.append({
            "kind": "shares",
            "asset": asset,
            "option_code": str(operation.get("Ativo", "N/D")).upper(),
            "quantity": covered_quantity,
            "total": covered_quantity * unit_cost,
            "expiry": operation.get("Vencimento_fmt", ""),
            "days": int(_number(operation.get("Dias"))),
            "logo_url": f"https://raw.githubusercontent.com/thefintz/icones-b3/main/icones/{asset}.png",
        })
    commitment_items.sort(key=lambda item: (str(item["asset"]), str(item["option_code"])))
    expiries = sorted(
        (operation for operation in open_options if operation.get("Vencimento_fmt")),
        key=lambda operation: _number(operation.get("Dias"), 999999),
    )

    allocated_by_asset: dict[str, float] = defaultdict(float)
    for operation in open_puts:
        allocated_by_asset[_asset_from_option(operation.get("Ativo"))] += _number(operation.get("Capital"))
    allocated_total = sum(allocated_by_asset.values())
    portfolio = tuple(
        {
            "asset": asset,
            "capital": capital,
            "share": capital / allocated_total * 100 if allocated_total else 0.0,
            "capital_share": capital / _number(indicators.get("capital_total")) * 100 if _number(indicators.get("capital_total")) else 0.0,
            "risk": "high" if _number(indicators.get("capital_total")) and capital / _number(indicators.get("capital_total")) > float(MAX_ASSET_CONCENTRATION) else ("attention" if _number(indicators.get("capital_total")) and capital / _number(indicators.get("capital_total")) >= float(ATTENTION_ASSET_CONCENTRATION) else "balanced"),
        }
        for asset, capital in sorted(allocated_by_asset.items(), key=lambda item: item[1], reverse=True)
    )

    roll_candidates = tuple(
        {
            "option_code": operation.get("Ativo", "N/D"),
            "asset": _asset_from_option(operation.get("Ativo")),
            "days": int(_number(operation.get("Dias"))),
            "roi": _number(operation.get("ROI")),
            "reason": f"Risco de exercício em {int(_number(operation.get('Dias')))} dia(s) — avaliar rolagem",
        }
        for operation in expiries
        if _number(operation.get("Dias")) <= 10 and _is_in_the_money(operation) and not _has_exercise_interest(operation)
    )[:5]

    attention = []
    for operation in open_options:
        categories: list[dict[str, str]] = []
        days = _number(operation.get("Dias"), 9999)
        spot = _number(operation.get("Cotacao_n"))
        strike = _number(operation.get("Strike_n"))
        option_type = str(operation.get("Tipo", "PUT")).upper()
        if spot > 0 and strike > 0:
            in_the_money = (option_type == "PUT" and spot <= strike) or (option_type == "CALL" and spot >= strike)
            if in_the_money and days <= 10:
                distance = abs(spot - strike) / strike * 100
                if _has_exercise_interest(operation):
                    categories.append({"kind": "Exercício", "message": f"{option_type} dentro do dinheiro ({distance:.1f}% além do strike) e vence em {int(days)} dia(s) — possível exercício conforme sua preferência", "severity": "high"})
                else:
                    categories.append({"kind": "Rolagem", "message": f"{option_type} dentro do dinheiro ({distance:.1f}% além do strike) e vence em {int(days)} dia(s) — avaliar rolagem para evitar exercício", "severity": "critical"})
        if spot <= 0 and days <= 10:
            categories.append({"kind": "Dados", "message": "Cotação não informada — atualize para confirmar o risco de exercício", "severity": "medium"})
        if categories:
            attention.append(_attention_item(operation.get("Ativo", "N/D"), categories))

    monthly_target_roi = _number(config.get("Meta ROI mensal"), 0.02) * 100
    weekly_target_roi = _number(config.get("Meta ROI semanal"), 0.01) * 100
    cycle_operations = []
    for operation in open_options:
        enriched = dict(operation)
        enriched.update(classify_option_cycle(operation.get("Ativo")))
        cycle_operations.append(enriched)
    cycle_groups = {
        group["cycle"]: group
        for group in build_cycle_groups(cycle_operations, result_key="Premio_liquido", capital_key="Capital")
    }
    monthly_roi = _number(cycle_groups["monthly"]["roi"])
    weekly_roi = _number(cycle_groups["weekly"]["roi"])
    average_roi = _number(indicators.get("roi_medio_abertas"))
    capital_total = _number(indicators.get("capital_total"))
    capital_free = _number(indicators.get("caixa_livre"))
    broker_cash = _number(indicators.get("broker_cash_balance"))
    projected_roi = _number(indicators.get("roi_abertas"))
    premiums_month = _number(indicators.get("lucro_mes"))
    premiums_total = _number(indicators.get("premios_total")) if "premios_total" in indicators else sum(
        _number(operation.get("Premio_liquido"))
        for operation in operations
        if str(operation.get("Estratégia", "Venda")).strip().lower() != "compra"
    )
    premiums_retained = _number(indicators.get("premios_retidos"), premiums_total)

    if not open_puts:
        summary = "Não há PUTs abertas. O capital está livre para aguardar oportunidades que atendam aos critérios do Radar Premium."
        tone = "neutral"
    elif all(
        _number(group["roi"]) >= (weekly_target_roi if cycle == "weekly" else monthly_target_roi)
        for cycle, group in cycle_groups.items() if group["count"]
    ):
        summary = f"A carteira possui {len(open_puts)} PUT(s) aberta(s). ROI mensal: {monthly_roi:.2f}% (meta {monthly_target_roi:.2f}%) e semanal: {weekly_roi:.2f}% (meta {weekly_target_roi:.2f}%). Revise risco, liquidez e vencimentos antes de ampliar exposição."
        tone = "positive"
    else:
        summary = f"A carteira possui {len(open_puts)} PUT(s) aberta(s). ROI mensal: {monthly_roi:.2f}% (meta {monthly_target_roi:.2f}%) e semanal: {weekly_roi:.2f}% (meta {weekly_target_roi:.2f}%). Não aumente risco apenas para buscar retorno."
        tone = "attention"
    quotes = option_quotes or {}
    today_scenario = []
    probability_by_code: dict[str, object] = {}
    for operation in open_options:
        code = str(operation.get("Ativo", "N/D")).upper()
        probability_by_code[code] = estimate_operation_exercise_probability(
            ticker=_underlying_asset(operation),
            option_type=str(operation.get("Tipo", "PUT")).upper(),
            strike=Decimal(str(_number(operation.get("Strike_n", operation.get("Strike"))) or 0)),
            expiry=_operation_expiry(operation.get("Vencimento")),
        )

    for operation in sorted(open_options, key=lambda item: _number(item.get("Dias"), 999999))[:5]:
        code = str(operation.get("Ativo", "N/D")).upper()
        spot, strike = _number(operation.get("Cotacao_n")), _number(operation.get("Strike_n"))
        option_type = str(operation.get("Tipo", "PUT")).upper()
        if spot <= 0 or strike <= 0:
            situation, situation_class = "Não calculada", "unknown"
        else:
            exercised = (option_type == "PUT" and spot <= strike) or (option_type == "CALL" and spot >= strike)
            situation, situation_class = ("Seria exercida", "exercised") if exercised else ("Não seria exercida", "safe")
        quote = quotes.get(code, {})
        estimate = probability_by_code[code]
        today_scenario.append({
            "option_code": code,
            "days": int(_number(operation.get("Dias"))),
            "own_value": _number(operation.get("Premio_opcao_n", operation.get("Premio_opcao"))),
            "current_value": _number(quote.get("price")) if quote.get("price") is not None else None,
            "quote_source": quote.get("source", "Cotação não disponível"),
            "situation": situation,
            "situation_class": situation_class,
            "exercise_probability": estimate.percentage,
            "exercise_probability_label": estimate.label,
        })

    open_positions = tuple({
        "option_code": str(operation.get("Ativo", "N/D")).upper(),
        "asset": _underlying_asset(operation),
        "logo_url": f"https://raw.githubusercontent.com/thefintz/icones-b3/main/icones/{_underlying_asset(operation)}.png",
        "type": str(operation.get("Tipo", "PUT")).upper(),
        "strategy": str(operation.get("Estratégia", "Venda")),
        "strike": _number(operation.get("Strike_n", operation.get("Strike"))),
        "premium": _number(operation.get("Premio_liquido")),
        "capital": _number(operation.get("Capital")),
        "expiry": operation.get("Vencimento_fmt", ""),
        "days": int(_number(operation.get("Dias"))),
        "roi": _number(operation.get("ROI")),
        "spot": _number(operation.get("Cotacao_n")) or None,
        "probability": probability_by_code[str(operation.get("Ativo", "")).upper()].percentage,
        "probability_label": probability_by_code[str(operation.get("Ativo", "")).upper()].label,
        "probability_class": (
            "high" if probability_by_code[str(operation.get("Ativo", "")).upper()].probability is not None
            and probability_by_code[str(operation.get("Ativo", "")).upper()].probability >= Decimal("0.65")
            else "mid" if probability_by_code[str(operation.get("Ativo", "")).upper()].probability is not None
            and probability_by_code[str(operation.get("Ativo", "")).upper()].probability >= Decimal("0.35")
            else "low" if probability_by_code[str(operation.get("Ativo", "")).upper()].probability is not None
            else "unavailable"
        ),
    } for operation in sorted(open_options, key=lambda item: _number(item.get("Dias"), 999999)))

    monthly_goal_progress = min(max(monthly_roi / monthly_target_roi * 100, 0), 100) if monthly_target_roi else 0
    weekly_goal_progress = min(max(weekly_roi / weekly_target_roi * 100, 0), 100) if weekly_target_roi else 0
    capital_usage = min(max(_number(indicators.get("capital_comp")) / capital_total * 100, 0), 100) if capital_total else 0
    projection_rows = tuple((darf_projection or {}).get("rows", ()))
    paid_by_competence = (darf_projection or {}).get("paid_by_competence", {})
    pending_rows = [row for row in projection_rows if _number(row.get("estimated_darf")) > _number(paid_by_competence.get(str(row.get("competence"))))]
    insufficient_rows = [row for row in projection_rows if _number(row.get("estimated_darf")) == 0 and _number(row.get("tax_carry")) > 0]
    current_tax = pending_rows[-1] if pending_rows else (insufficient_rows[-1] if insufficient_rows else next((row for row in reversed(projection_rows) if _number(row.get("estimated_darf")) > 0), {}))
    current_competence = str(current_tax.get("competence", (darf_projection or {}).get("current_month", "")))
    estimated_darf = _number(current_tax.get("estimated_darf"))
    paid_amount = _number(paid_by_competence.get(current_competence))
    pending_amount = max(estimated_darf - paid_amount, 0)
    insufficient_amount = _number(current_tax.get("tax_carry")) if estimated_darf == 0 else 0
    darf_alert = {
        "competence": current_competence,
        "premium_base": _number(current_tax.get("net_result")),
        "taxable_base": _number(current_tax.get("taxable_base")),
        "estimated_darf": estimated_darf,
        "paid_amount": paid_amount,
        "pending_amount": pending_amount,
        "insufficient_amount": insufficient_amount,
        "is_insufficient": insufficient_amount > 0,
        "due_date": _estimated_darf_due_date(current_competence),
        "has_due": pending_amount > 0,
        "review_count": int(_number(current_tax.get("review_count"))),
    }

    return DashboardViewModel(
        patrimony=_number(indicators.get("patrimonio_atual")),
        equities_value=_number(indicators.get("capital_acoes")),
        current_month_filter=date.today().strftime("%Y-%m"),
        premiums_month=premiums_month,
        premiums_total=premiums_total,
        premiums_retained=premiums_retained,
        average_roi=average_roi,
        monthly_roi=monthly_roi,
        weekly_roi=weekly_roi,
        monthly_target_roi=monthly_target_roi,
        weekly_target_roi=weekly_target_roi,
        allocated_capital=_number(indicators.get("capital_comp")),
        commitment_items=tuple(commitment_items),
        available_to_trade=(
            broker_cash
            + _number(indicators.get("margem_lftb11"))
            - _number(indicators.get("capital_opcoes", indicators.get("capital_comp")))
        ),
        open_puts=len(open_puts),
        open_operations=len(open_operations),
        next_expiry=({
            "option_code": expiries[0].get("Ativo", "N/D"),
            "date": expiries[0].get("Vencimento_fmt", ""),
            "days": int(_number(expiries[0].get("Dias"))),
        } if expiries else None),
        projected_roi=projected_roi,
        broker_cash_balance=broker_cash,
        ai_summary=summary,
        ai_tone=tone,
        portfolio=portfolio,
        roll_candidates=roll_candidates,
        attention_items=tuple(attention[:6]),
        today_scenario=tuple(today_scenario),
        open_positions=open_positions,
        upcoming_expiries=tuple({
            "option_code": operation.get("Ativo", "N/D"),
            "date": operation.get("Vencimento_fmt", ""),
            "days": int(_number(operation.get("Dias"))),
        } for operation in expiries[:6]),
        goals=(
            {"label": "ROI mensal", "value": monthly_roi, "target": monthly_target_roi, "progress": monthly_goal_progress, "unit": "%"},
            {"label": "Capital utilizado", "value": _number(indicators.get("capital_comp")), "target": capital_total, "progress": capital_usage, "unit": "R$"},
            {"label": "ROI semanal", "value": weekly_roi, "target": weekly_target_roi, "progress": weekly_goal_progress, "unit": "%"},
        ),
        stats=(
            {"label": "Capital total", "value": capital_total, "kind": "money"},
            {"label": "Disponível", "value": capital_free, "kind": "money"},
            {"label": "Operações fechadas", "value": len(closed_operations), "kind": "number"},
            {"label": "Itens de atenção", "value": len(attention), "kind": "number"},
        ),
        chart_labels=tuple(str(row.get("mes", "")) for row in history),
        chart_premiums=tuple(_number(row.get("patrimonio")) for row in history),
        darf_alert=darf_alert,
    )
