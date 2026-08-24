"""Página da Calculadora de ROI para venda de CALL e PUT."""
from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

from flask import render_template, request

from services.equity_position_service import portfolio
from services.roi_calculator_service import build_roi_option_rows
from services.sldx_market_service import SldxMarketError, fetch_option_chain, fetch_stock_price


def register(app, legacy):
    @app.get("/calculadora-roi")
    def roi_calculator():
        ticker = str(request.args.get("ativo", "")).strip().upper().removesuffix(".SA")
        option_type = str(request.args.get("tipo", "PUT")).strip().upper()
        if option_type not in {"PUT", "CALL"}:
            option_type = "PUT"
        operations = legacy.read_operacoes()
        suggestions = {
            str(item.get("asset", "")).upper() for item in portfolio(legacy, operations)
        }
        suggestions.update(
            str(operation.get("Ativo_subjacente") or legacy.infer_acao_from_option(str(operation.get("Ativo", "")))).upper()
            for operation in operations
        )
        rows = ()
        error = ""
        if ticker:
            try:
                opportunities = fetch_option_chain(
                    ticker, option_types=(option_type,), force_refresh=True,
                )
                current_spot = Decimal(str(fetch_stock_price(ticker)))
                opportunities = tuple(
                    replace(opportunity, spot_price=current_spot)
                    for opportunity in opportunities
                )
                rows = build_roi_option_rows(opportunities, option_type=option_type)
                if not rows:
                    error = f"Nenhuma {option_type} com prêmio e vencimento em até 60 dias úteis foi encontrada."
            except (SldxMarketError, ValueError) as exc:
                error = str(exc)
        return render_template(
            "calculadora_roi.html", ticker=ticker, option_type=option_type,
            rows=rows, error=error, suggestions=sorted(value for value in suggestions if value),
            today=date.today(),
        )
