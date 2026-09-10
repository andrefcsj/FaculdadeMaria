"""Importação compartilhada de negociações de ativos à vista."""
from decimal import Decimal

from services.brokerage_note_service import (
    BrokerageNoteError, find_matching_provisional_note, imported_note_exists,
    replace_provisional_note, save_imported_note,
)
from services.equity_position_service import (
    portfolio, replace_equity_lot_from_note, save_equity_lot, sell_equity_asset,
)


def import_equity_trades(legacy, payload, equity_trades):
    """Registra as negociações à vista selecionadas, sem criar opções."""
    # Valida a nota inteira antes de alterar qualquer posição. Isso evita
    # importar parcialmente uma nota com mais de uma venda.
    available = {item["asset"]: int(item["available_quantity"]) for item in portfolio(legacy)}
    for trade in equity_trades:
        trade_payload = {**payload, "trade": trade}
        if imported_note_exists(legacy, trade_payload):
            raise BrokerageNoteError(f"A negociação de {trade['underlying_asset']} desta nota já foi importada.")
        if trade.get("event_type") == "equity_sale":
            ticker = str(trade["underlying_asset"]).upper()
            quantity = int(trade["quantity"])
            if quantity > available.get(ticker, 0):
                raise BrokerageNoteError(
                    f"A nota vende {quantity} ações {ticker}, mas a carteira possui somente "
                    f"{available.get(ticker, 0)} ações livres."
                )
            available[ticker] -= quantity

    imported = []
    sales = []
    for trade in equity_trades:
        trade_payload = {**payload, "trade": trade}
        provisional = find_matching_provisional_note(legacy, trade_payload)
        ticker = str(trade["underlying_asset"]).upper()

        if trade.get("event_type") == "equity_sale":
            operation_id = str(provisional.get("operation_id")) if provisional else f"equity-sale:{ticker}"
            if provisional:
                if not replace_provisional_note(legacy, str(provisional["key"]), trade_payload, operation_id):
                    raise BrokerageNoteError("Não foi possível substituir a nota prévia de venda pela definitiva.")
            elif not save_imported_note(legacy, trade_payload, operation_id):
                raise BrokerageNoteError(f"A venda de {ticker} desta nota já foi importada.")
            consumed_cost = sell_equity_asset(legacy, asset=ticker, quantity=int(trade["quantity"]))
            net_proceeds = (
                Decimal(str(trade["gross_value"]))
                - Decimal(str(trade["allocated_costs"]))
                - Decimal(str(trade["allocated_irrf"]))
            )
            sales.append({
                "asset": ticker, "quantity": int(trade["quantity"]),
                "net_proceeds": str(net_proceeds),
                "tax_cost": str(consumed_cost),
                "realized_result": str(net_proceeds - consumed_cost),
            })
            imported.append(ticker)
            continue

        lot_id = f"purchase:{payload['document_hash']}:{trade['trade_index']}"
        gross = Decimal(str(trade["gross_value"]))
        costs = Decimal(str(trade["allocated_costs"])) + Decimal(str(trade["allocated_irrf"]))
        quantity = int(trade["quantity"])
        lot = {
            "lot_id": lot_id, "asset": trade["underlying_asset"], "quantity": quantity,
            "available_quantity": quantity, "acquisition_date": payload["trade_date"],
            "exercise_price": str(trade["unit_price"]), "exercise_total": str(gross),
            "exercise_costs": str(costs), "cash_cost_total": str(gross + costs),
            "option_premium_gross": "0", "option_opening_costs": "0",
            "tax_cost_total": str(gross + costs),
            "tax_cost_per_share": str((gross + costs) / Decimal(quantity)),
            "source": "Compra de ações por nota", "source_operation_id": "",
            "source_option": "", "source_note_key": f"{payload['document_hash']}:{trade['trade_index']}",
            "note_pending": bool(payload.get("is_provisional", False)),
        }
        if provisional:
            operation_id = str(provisional.get("operation_id") or f"equity:{ticker}")
            if not replace_equity_lot_from_note(legacy, str(provisional["key"]), lot):
                raise BrokerageNoteError("O lote provisório correspondente não foi encontrado com segurança.")
            if not replace_provisional_note(legacy, str(provisional["key"]), trade_payload, operation_id):
                raise BrokerageNoteError("Não foi possível substituir a nota prévia pela definitiva.")
        else:
            if not save_imported_note(legacy, trade_payload, f"equity:{ticker}"):
                raise BrokerageNoteError(f"A compra de {ticker} desta nota já foi importada.")
            if not save_equity_lot(legacy, lot):
                raise BrokerageNoteError(f"O lote de {ticker} já foi cadastrado.")
        imported.append(ticker)
    return {
        "ok": True, "imported": imported, "sales": sales,
        "message": "Nota de compra/venda conciliada; posição, preço médio e caixa foram recalculados sem duplicidade.",
    }

