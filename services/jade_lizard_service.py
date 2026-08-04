"""Motor do Radar Jade Lizard, independente da origem da cadeia de opções."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
from math import erf, exp, log, sqrt
from typing import Callable, Iterable


@dataclass(frozen=True)
class JadeConfig:
    min_dte: int = 15
    max_dte: int = 45
    min_liquidity: int = 1000
    min_open_interest: int = 500
    max_spread_pct: float = 15.0
    min_score: float = 80.0
    min_retention_pct: float = 95.0


@dataclass(frozen=True)
class JadeOpportunity:
    ticker: str
    logo_url: str
    spot: float
    days: int
    expiry: str
    put_code: str
    short_call_code: str
    long_call_code: str
    put_strike: float
    short_call_strike: float
    long_call_strike: float
    put_credit: float
    put_roi_on_strike: float
    short_call_credit: float
    long_call_debit: float
    net_credit: float
    jade_roi_on_strike: float
    spread_width: float
    break_even: float
    effective_cost: float
    max_profit: float
    max_loss: float
    capital_required: float
    roi: float
    probability_profit: float
    retention_pct: float
    score: float
    put_delta: float
    iv: float
    hv: float
    liquidity: int
    open_interest: int
    spread_pct: float
    data_mode: str = "estimado"

    def to_dict(self) -> dict:
        return asdict(self)


def _cdf(value: float) -> float:
    return 0.5 * (1.0 + erf(value / sqrt(2.0)))


def _bs(spot: float, strike: float, years: float, rate: float, iv: float, kind: str) -> tuple[float, float]:
    d1 = (log(spot / strike) + (rate + iv * iv / 2) * years) / (iv * sqrt(years))
    d2 = d1 - iv * sqrt(years)
    if kind == "call":
        return spot * _cdf(d1) - strike * exp(-rate * years) * _cdf(d2), _cdf(d1)
    return strike * exp(-rate * years) * _cdf(-d2) - spot * _cdf(-d1), _cdf(d1) - 1


def _round_strike(value: float, step: float = .5) -> float:
    return round(round(value / step) * step, 2)


CALL_MONTH_CODES = "ABCDEFGHIJKL"
PUT_MONTH_CODES = "MNOPQRSTUVWX"


def build_estimated_option_code(ticker: str, kind: str, strike: float, expiry: date) -> str:
    """Monta código projetado respeitando tipo e mês definidos pela B3.

    O sufixo numérico continua sendo apenas uma referência de strike enquanto não
    houver uma cadeia oficial; a letra, porém, nunca pode contradizer o vencimento.
    """
    normalized_ticker = str(ticker).strip().upper()
    root = normalized_ticker[:-1] if normalized_ticker[-1:].isdigit() else normalized_ticker
    month_codes = PUT_MONTH_CODES if kind.lower() == "put" else CALL_MONTH_CODES
    month_code = month_codes[expiry.month - 1]
    return f"{root}{month_code}{int(round(strike * 100)):04d}"


def is_dte_allowed(days: int, config: JadeConfig | None = None) -> bool:
    """Regra central: oportunidades fora da janela nunca chegam ao ranking."""
    cfg = config or JadeConfig()
    return cfg.min_dte <= int(days) <= cfg.max_dte


def scan_estimated_chain(
    tickers: Iterable[str],
    spot_loader: Callable[[str], float | None],
    config: JadeConfig | None = None,
    target_expiry: date | None = None,
) -> list[JadeOpportunity]:
    """Cria uma cadeia estimada e passa todas as combinações pelo mesmo motor do feed real."""
    cfg = config or JadeConfig()
    results: list[JadeOpportunity] = []
    expiry_date = target_expiry or (date.today() + timedelta(days=30))
    days = (expiry_date - date.today()).days
    if not is_dte_allowed(days, cfg):
        return []
    years = days / 365
    expiry = expiry_date.isoformat()
    for ticker in tickers:
        spot = float(spot_loader(ticker) or 0)
        if spot <= 0:
            continue
        hv, iv = .27, .33
        put_candidates = [_round_strike(spot * ratio) for ratio in (.88, .90, .92, .94)]
        call_candidates = [_round_strike(spot * ratio) for ratio in (1.04, 1.06, 1.08, 1.10)]
        best: JadeOpportunity | None = None
        for put_strike in sorted(set(put_candidates)):
            put_credit, put_delta = _bs(spot, put_strike, years, .11, iv, "put")
            if not -.30 <= put_delta <= -.15 or put_credit <= 0:
                continue
            for short_strike in sorted(set(call_candidates)):
                short_credit, _ = _bs(spot, short_strike, years, .11, iv, "call")
                for width in (.5, 1.0, 2.0):
                    long_strike = _round_strike(short_strike + width)
                    if long_strike <= short_strike:
                        continue
                    long_debit, _ = _bs(spot, long_strike, years, .11, iv, "call")
                    width = long_strike - short_strike
                    net = put_credit + short_credit - long_debit
                    retention = net / put_credit * 100
                    if retention < cfg.min_retention_pct:
                        continue
                    # Uma Jade Lizard sem risco na alta exige que todo o crédito
                    # recebido cubra a largura máxima da trava de CALL no vencimento.
                    # A retenção de 95% protege o prêmio da PUT, mas não substitui
                    # esta identidade financeira.
                    if net + 1e-9 < width:
                        continue
                    downside = max(put_strike - net, 0)
                    upside = max(width - net, 0)
                    max_loss = max(downside, upside)
                    capital = max_loss * 100
                    roi = (net * 100 / capital * 100) if capital else 0
                    spread_pct = 7.5
                    liquidity, oi = 5000, 2500
                    put_quality = min(100, 82 + max(0, (iv / hv - 1) * 40))
                    liquidity_score = 95
                    relation_score = min(100, (net / width) * 90) if width else 0
                    delta_score = max(0, 100 - abs(abs(put_delta) - .225) * 600)
                    iv_score = 100 if iv > hv else 50
                    distance_score = min(100, max(0, (spot - put_strike) / spot * 900))
                    score = (.30 * put_quality + .20 * liquidity_score + .20 * relation_score +
                             .10 * delta_score + .10 * iv_score + .10 * distance_score)
                    if score < cfg.min_score:
                        continue
                    displayed_put_credit = round(put_credit, 2)
                    displayed_net_credit = round(net, 2)
                    displayed_max_loss = round(max(
                        max(put_strike - displayed_net_credit, 0),
                        max(width - displayed_net_credit, 0),
                    ) * 100, 2)
                    displayed_roi = (displayed_net_credit * 100 / displayed_max_loss * 100) if displayed_max_loss else 0
                    candidate = JadeOpportunity(
                        ticker=ticker,
                        logo_url=f"https://raw.githubusercontent.com/thefintz/icones-b3/main/icones/{ticker}.png",
                        spot=round(spot, 2), days=days, expiry=expiry,
                        put_code=build_estimated_option_code(ticker, "put", put_strike, expiry_date),
                        short_call_code=build_estimated_option_code(ticker, "call", short_strike, expiry_date),
                        long_call_code=build_estimated_option_code(ticker, "call", long_strike, expiry_date),
                        put_strike=put_strike, short_call_strike=short_strike, long_call_strike=long_strike,
                        put_credit=displayed_put_credit, put_roi_on_strike=round(displayed_put_credit / put_strike * 100, 2),
                        short_call_credit=round(short_credit, 2), long_call_debit=round(long_debit, 2),
                        net_credit=displayed_net_credit, jade_roi_on_strike=round(displayed_net_credit / put_strike * 100, 2),
                        spread_width=round(width, 2), break_even=round(put_strike - displayed_net_credit, 2),
                        effective_cost=round(put_strike - displayed_net_credit, 2), max_profit=round(displayed_net_credit * 100, 2),
                        max_loss=displayed_max_loss, capital_required=displayed_max_loss,
                        roi=round(displayed_roi, 2), probability_profit=round((1 + put_delta) * 100, 1),
                        retention_pct=round(retention, 1), score=round(score, 1), put_delta=round(put_delta, 3),
                        iv=iv, hv=hv, liquidity=liquidity, open_interest=oi, spread_pct=spread_pct,
                    )
                    if best is None or (candidate.score, candidate.net_credit, -candidate.max_loss) > (best.score, best.net_credit, -best.max_loss):
                        best = candidate
        if best:
            results.append(best)
    return sorted(results, key=lambda row: (row.score, row.roi), reverse=True)
