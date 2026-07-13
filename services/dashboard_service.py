"""Adaptador de apresentação do Dashboard Executivo.

Este módulo não cria regras financeiras. Ele apenas organiza métricas já
calculadas pela aplicação em um view model estável para a interface.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Mapping, Sequence
from services.concentration_service import ATTENTION_ASSET_CONCENTRATION, MAX_ASSET_CONCENTRATION


def _number(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _asset_from_option(option_code: object) -> str:
    letters = "".join(character for character in str(option_code or "").upper() if character.isalpha())
    return letters[:4] if letters else "N/D"


def _attention_item(option_code: object, categories: list[dict[str, str]]) -> dict[str, object]:
    rank = {"info": 0, "medium": 1, "high": 2, "critical": 3}
    severity = max((category["severity"] for category in categories), key=lambda value: rank[value])
    labels = {"critical": "Crítico", "high": "Acompanhar", "medium": "Observar", "info": "Informação"}
    return {"option_code": option_code, "categories": tuple(categories), "message": " • ".join(category["message"] for category in categories), "severity": severity, "label": labels[severity]}


@dataclass(frozen=True)
class DashboardViewModel:
    premiums_month: float
    premiums_total: float
    average_roi: float
    allocated_capital: float
    open_puts: int
    next_expiry: Mapping[str, object] | None
    projected_roi: float
    broker_cash_balance: float
    ai_summary: str
    ai_tone: str
    portfolio: tuple[Mapping[str, object], ...]
    roll_candidates: tuple[Mapping[str, object], ...]
    attention_items: tuple[Mapping[str, object], ...]
    today_scenario: tuple[Mapping[str, object], ...]
    upcoming_expiries: tuple[Mapping[str, object], ...]
    goals: tuple[Mapping[str, object], ...]
    stats: tuple[Mapping[str, object], ...]
    chart_labels: tuple[str, ...]
    chart_premiums: tuple[float, ...]


def build_dashboard_view_model(
    operations: Sequence[Mapping[str, object]],
    closed_operations: Sequence[Mapping[str, object]],
    indicators: Mapping[str, object],
    history: Sequence[Mapping[str, object]],
    config: Mapping[str, object],
    option_quotes: Mapping[str, Mapping[str, object]] | None = None,
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
    expiries = sorted(
        (operation for operation in open_puts if operation.get("Vencimento_fmt")),
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
            "reason": "Vencimento próximo" if _number(operation.get("Dias")) <= 15 else str(operation.get("Alerta", "Revisar posição")),
        }
        for operation in expiries
        if _number(operation.get("Dias")) <= 30 or str(operation.get("Alerta", "OK")) != "OK"
    )[:5]

    attention = []
    for operation in open_options:
        categories: list[dict[str, str]] = []
        days = _number(operation.get("Dias"), 9999)
        spot = _number(operation.get("Cotacao_n"))
        strike = _number(operation.get("Strike_n"))
        option_type = str(operation.get("Tipo", "PUT")).upper()
        if spot > 0 and strike > 0:
            distance = (spot - strike) / spot * 100
            in_the_money = (option_type == "PUT" and spot <= strike) or (option_type == "CALL" and spot >= strike)
            if in_the_money and days <= 10:
                categories.append({"kind": "Exercício", "message": f"{option_type} dentro do dinheiro e vence em {int(days)} dia(s) — avaliar exercício ou rolagem", "severity": "critical"})
            elif option_type == "PUT" and spot > strike and distance <= 2:
                categories.append({"kind": "Exercício", "message": f"Cotação {distance:.1f}% acima do strike — risco elevado se houver queda", "severity": "high"})
            elif option_type == "PUT" and spot > strike and distance <= 5:
                categories.append({"kind": "Exercício", "message": f"Cotação {distance:.1f}% acima do strike — PUT ainda fora do dinheiro", "severity": "medium"})
        if days <= 7:
            categories.append({"kind": "Vencimento", "message": f"Vence em {int(days)} dia(s) — acompanhar de perto", "severity": "high"})
        elif days <= 15:
            categories.append({"kind": "Vencimento", "message": f"Vence em {int(days)} dias — planejar manutenção, fechamento ou rolagem", "severity": "medium"})
        if spot <= 0:
            categories.append({"kind": "Dados", "message": "Cotação não informada — atualize antes de avaliar exercício", "severity": "medium"})
        if categories:
            attention.append(_attention_item(operation.get("Ativo", "N/D"), categories))

    target_roi = _number(config.get("Meta ROI mensal"), 0.04) * 100
    average_roi = _number(indicators.get("roi_medio_abertas"))
    capital_total = _number(indicators.get("capital_total"))
    capital_free = _number(indicators.get("caixa_livre"))
    projected_roi = _number(indicators.get("roi_abertas"))
    premiums_month = _number(indicators.get("lucro_mes"))
    premiums_total = sum(
        _number(operation.get("Premio_liquido"))
        for operation in operations
        if str(operation.get("Estratégia", "Venda")).lower() == "venda"
    )

    if not open_puts:
        summary = "Não há PUTs abertas. O capital está livre para aguardar oportunidades que atendam aos critérios do Radar Premium."
        tone = "neutral"
    elif average_roi >= target_roi:
        summary = f"A carteira possui {len(open_puts)} PUT(s) aberta(s) e ROI médio de {average_roi:.2f}%, acima da meta oficial de {target_roi:.2f}%. Revise risco, liquidez e vencimentos antes de ampliar exposição."
        tone = "positive"
    else:
        summary = f"A carteira possui {len(open_puts)} PUT(s) aberta(s) e ROI médio de {average_roi:.2f}%, abaixo da meta oficial de {target_roi:.2f}%. Não aumente risco apenas para buscar retorno."
        tone = "attention"
    quotes = option_quotes or {}
    today_scenario = []
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
        today_scenario.append({
            "option_code": code,
            "days": int(_number(operation.get("Dias"))),
            "own_value": _number(operation.get("Premio_opcao_n", operation.get("Premio_opcao"))),
            "current_value": _number(quote.get("price")) if quote.get("price") is not None else None,
            "quote_source": quote.get("source", "Cotação não disponível"),
            "situation": situation,
            "situation_class": situation_class,
        })

    goal_progress = min(max(average_roi / target_roi * 100, 0), 100) if target_roi else 0
    capital_usage = min(max(_number(indicators.get("capital_comp")) / capital_total * 100, 0), 100) if capital_total else 0

    return DashboardViewModel(
        premiums_month=premiums_month,
        premiums_total=premiums_total,
        average_roi=average_roi,
        allocated_capital=_number(indicators.get("capital_comp")),
        open_puts=len(open_puts),
        next_expiry=({
            "option_code": expiries[0].get("Ativo", "N/D"),
            "date": expiries[0].get("Vencimento_fmt", ""),
            "days": int(_number(expiries[0].get("Dias"))),
        } if expiries else None),
        projected_roi=projected_roi,
        broker_cash_balance=_number(indicators.get("broker_cash_balance")),
        ai_summary=summary,
        ai_tone=tone,
        portfolio=portfolio,
        roll_candidates=roll_candidates,
        attention_items=tuple(attention[:6]),
        today_scenario=tuple(today_scenario),
        upcoming_expiries=tuple({
            "option_code": operation.get("Ativo", "N/D"),
            "date": operation.get("Vencimento_fmt", ""),
            "days": int(_number(operation.get("Dias"))),
        } for operation in expiries[:6]),
        goals=(
            {"label": "ROI médio", "value": average_roi, "target": target_roi, "progress": goal_progress, "unit": "%"},
            {"label": "Capital utilizado", "value": _number(indicators.get("capital_comp")), "target": capital_total, "progress": capital_usage, "unit": "R$"},
        ),
        stats=(
            {"label": "Capital total", "value": capital_total, "kind": "money"},
            {"label": "Disponível", "value": capital_free, "kind": "money"},
            {"label": "Operações fechadas", "value": len(closed_operations), "kind": "number"},
            {"label": "Itens de atenção", "value": len(attention), "kind": "number"},
        ),
        chart_labels=tuple(str(row.get("mes", "")) for row in history),
        chart_premiums=tuple(_number(row.get("premios")) for row in history),
    )
