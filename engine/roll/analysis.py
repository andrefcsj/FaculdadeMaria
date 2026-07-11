"""Cálculos puros e explicáveis para comparar manter, fechar ou rolar uma PUT."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from engine.errors import DecisionEngineError


@dataclass(frozen=True, slots=True)
class RollInput:
    option_code: str
    current_strike: Decimal
    original_premium: Decimal
    current_expiry: date
    buyback_price: Decimal
    new_option_code: str
    new_strike: Decimal
    new_premium: Decimal
    new_expiry: date
    spot_price: Decimal
    contract_size: int = 100
    costs_total: Decimal = Decimal("0")
    target_roi: Decimal = Decimal("0.04")


@dataclass(frozen=True, slots=True)
class RollAnalysis:
    recommendation: str
    recommendation_label: str
    captured_profit_per_unit: Decimal
    captured_profit_total: Decimal
    captured_pct: Decimal
    remaining_premium_per_unit: Decimal
    roll_credit_per_unit: Decimal
    roll_credit_total: Decimal
    current_net_price: Decimal
    new_net_price: Decimal
    current_roi: Decimal
    new_cumulative_roi: Decimal
    strike_change: Decimal
    extra_days: int
    positive_factors: tuple[str, ...]
    attention_points: tuple[str, ...]
    explanation: str


def _q(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _validate(data: RollInput) -> None:
    values = {
        "strike atual": data.current_strike,
        "prêmio original": data.original_premium,
        "preço de recompra": data.buyback_price,
        "novo strike": data.new_strike,
        "novo prêmio": data.new_premium,
        "cotação do ativo": data.spot_price,
        "custos": data.costs_total,
    }
    for label, value in values.items():
        if value < 0:
            raise DecisionEngineError(f"{label} não pode ser negativo")
    if data.current_strike <= 0 or data.new_strike <= 0 or data.spot_price <= 0:
        raise DecisionEngineError("strikes e cotação devem ser maiores que zero")
    if data.contract_size <= 0:
        raise DecisionEngineError("tamanho do contrato deve ser maior que zero")
    if data.new_expiry <= data.current_expiry:
        raise DecisionEngineError("o novo vencimento deve ser posterior ao vencimento atual")


def analyze_put_roll(data: RollInput) -> RollAnalysis:
    """Compara a PUT atual com uma nova PUT candidata sem inventar dados."""

    _validate(data)
    size = Decimal(data.contract_size)
    captured_unit = data.original_premium - data.buyback_price
    captured_total = captured_unit * size
    captured_pct = captured_unit / data.original_premium if data.original_premium > 0 else Decimal("0")
    remaining = data.buyback_price
    roll_credit_total = (data.new_premium - data.buyback_price) * size - data.costs_total
    roll_credit_unit = roll_credit_total / size
    current_net = data.current_strike - data.original_premium
    cumulative_premium = data.original_premium + roll_credit_unit
    new_net = data.new_strike - cumulative_premium
    current_roi = data.original_premium / data.current_strike
    new_roi = cumulative_premium / data.new_strike
    strike_change = data.new_strike - data.current_strike
    extra_days = (data.new_expiry - data.current_expiry).days

    positives: list[str] = []
    attention: list[str] = []

    if roll_credit_total >= 0:
        positives.append("A rolagem gera crédito líquido.")
    else:
        attention.append("A rolagem exige débito líquido.")
    if new_net < current_net:
        positives.append("O novo preço líquido de aquisição é menor.")
    elif new_net > current_net:
        attention.append("O novo preço líquido de aquisição aumenta.")
    if data.new_strike < data.current_strike:
        positives.append("O novo strike reduz o risco de exercício.")
    elif data.new_strike > data.current_strike:
        attention.append("O novo strike aumenta a exposição ao exercício.")
    if new_roi >= data.target_roi:
        positives.append("O ROI acumulado alcança ou supera a meta de 4%.")
    else:
        attention.append("O ROI acumulado permanece abaixo da meta de 4%.")
    if captured_pct >= Decimal("0.80"):
        positives.append("Ao menos 80% do prêmio original já foi capturado.")
    if data.spot_price < data.current_strike:
        attention.append("A PUT atual está dentro do dinheiro pela cotação informada.")

    improves_net = new_net <= current_net
    improves_strike = data.new_strike < data.current_strike
    acceptable_return = new_roi >= data.target_roi
    credit_roll = roll_credit_total >= 0

    if credit_roll and (improves_net or improves_strike) and acceptable_return:
        recommendation = "roll"
        label = "ROLAR"
        explanation = (
            f"Rolar para {data.new_option_code} é tecnicamente superior: "
            f"crédito líquido de R$ {_q(roll_credit_total)}, preço líquido de R$ {_q(new_net)} "
            f"e ROI acumulado de {_q(new_roi * Decimal('100'))}%."
        )
    elif captured_pct >= Decimal("0.80") and not (improves_net or improves_strike):
        recommendation = "close"
        label = "FECHAR E REAVALIAR"
        explanation = (
            f"A operação já capturou {_q(captured_pct * Decimal('100'))}% do prêmio, "
            "mas a nova alternativa não melhora o preço líquido nem o strike."
        )
    else:
        recommendation = "maintain"
        label = "MANTER"
        explanation = (
            "A rolagem informada ainda não apresenta melhoria objetiva suficiente em crédito, "
            "strike, preço líquido e retorno para justificar a troca."
        )

    return RollAnalysis(
        recommendation=recommendation,
        recommendation_label=label,
        captured_profit_per_unit=_q(captured_unit),
        captured_profit_total=_q(captured_total),
        captured_pct=_q(captured_pct * Decimal("100")),
        remaining_premium_per_unit=_q(remaining),
        roll_credit_per_unit=_q(roll_credit_unit),
        roll_credit_total=_q(roll_credit_total),
        current_net_price=_q(current_net),
        new_net_price=_q(new_net),
        current_roi=_q(current_roi * Decimal("100")),
        new_cumulative_roi=_q(new_roi * Decimal("100")),
        strike_change=_q(strike_change),
        extra_days=extra_days,
        positive_factors=tuple(positives),
        attention_points=tuple(attention),
        explanation=explanation,
    )
