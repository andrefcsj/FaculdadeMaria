"""Cadastro Premium de novas operações sem sair da tela atual."""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from flask import jsonify, request

from engine.providers import B3CotahistProvider, ProviderError, download_cotahist_for_date
from services.market_import_service import load_market_import
from services.brokerage_note_service import imported_note_exists, save_imported_note
from services.operation_close_service import calculate_operation_close
from services.closed_operations_service import save_closure_metadata
from services.operation_preferences_service import normalize_exercise_interest, save_operation_metadata
from services.equity_position_service import create_put_assignment_lot, save_equity_lot, validate_covered_call


def _lookup_b3_option(code: str, underlying: str, trade_date: date, cache_dir):
    cache_path = cache_dir / "market" / f"cotahist_{trade_date.strftime('%Y%m%d')}.zip"
    if not cache_path.exists():
        download_cotahist_for_date(cache_path, trade_date)
    root = code[:4]
    opportunities = B3CotahistProvider(cache_path, {root: underlying}).fetch()
    return next((item for item in opportunities if item.option_code.upper() == code), None)


def _decimal(value, field: str, *, allow_zero: bool = True) -> Decimal:
    text = str(value or "").strip().replace("R$", "").replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        parsed = Decimal(text or "0")
    except InvalidOperation as exc:
        raise ValueError(f"{field} inválido.") from exc
    if parsed < 0 or (not allow_zero and parsed == 0):
        raise ValueError(f"{field} deve ser maior que zero.")
    return parsed


def register(app, legacy, market_path):
    def close_from_note(operation_id: str, note_payload: dict, option_code: str):
        trade = note_payload.get("trade", {})
        if str(trade.get("side", "")).lower() != "compra":
            raise ValueError("A nota não representa uma recompra.")
        is_assignment = str(trade.get("event_type", "")) == "exercise_put_assignment"
        rows = legacy.read_csv(legacy.OPERACOES)
        operation = legacy.get_operacao_pg(operation_id) if legacy.USE_POSTGRES else legacy.find_row(rows, operation_id)
        if not operation or str(operation.get("Status", "")).lower() != "aberta":
            raise ValueError("A operação aberta para encerramento não foi encontrada.")
        if str(operation.get("Ativo", "")).upper() != option_code or str(operation.get("Estratégia", "")).lower() not in {"venda", "wheel"}:
            raise ValueError("A negociação não corresponde à operação aberta.")
        if is_assignment and str(operation.get("Tipo", "PUT")).upper() != "PUT":
            raise ValueError("A nota de exercício não corresponde a uma PUT vendida.")
        config = legacy.load_config()
        contracts = Decimal(str(legacy.fnum(operation.get("Contratos"), 0)))
        contract_size = Decimal(str(config.get("Tamanho contrato opcoes", 100)))
        open_quantity = int(contracts * contract_size)
        if int(trade.get("quantity", 0)) != open_quantity:
            raise ValueError("Encerramento parcial ou quantidade incompatível exige conferência manual.")
        close_date = legacy.parse_date(str(note_payload.get("trade_date", ""))) or date.today()
        repurchase = Decimal("0") if is_assignment else _decimal(trade.get("unit_price"), "Valor de recompra")
        premium_total = Decimal(str(legacy.fnum(operation.get("Premio_opcao")))) * contracts * contract_size - Decimal(str(legacy.fnum(operation.get("Custos")))) - Decimal(str(legacy.fnum(operation.get("IRRF"))) )
        method = "exercida" if is_assignment else "recompra"
        closure = calculate_operation_close(method=method, close_date=close_date, expiry=legacy.parse_date(str(operation.get("Vencimento", ""))), premium_received=premium_total, repurchase_per_unit=repurchase, contracts=contracts, contract_size=contract_size)
        closing_costs = _decimal(trade.get("allocated_costs"), "Custos") + _decimal(trade.get("allocated_irrf"), "IRRF")
        # No exercício da PUT o prêmio passa a compor o custo fiscal das ações;
        # os custos da nota pertencem à aquisição, não a uma recompra da opção.
        realized = closure.result if is_assignment else closure.result - closing_costs
        if not save_imported_note(legacy, note_payload, operation_id):
            raise ValueError("Esta negociação da nota já foi importada.")
        lot = None
        if is_assignment:
            lot = create_put_assignment_lot(legacy, operation, note_payload)
            if not save_equity_lot(legacy, lot):
                raise ValueError("O lote de ações deste exercício já foi registrado.")
        if legacy.USE_POSTGRES:
            conn = legacy.get_pg_conn()
            try:
                cur = conn.cursor();cur.execute("UPDATE operacoes SET status=%s, resultado_realizado=%s WHERE id=%s", ("Encerrada", str(realized), operation_id));conn.commit()
            finally:conn.close()
        else:
            operation["Status"] = "Encerrada";operation["Resultado_realizado"] = str(realized)
            legacy.write_csv(legacy.OPERACOES, rows, list(rows[0].keys()))
        save_closure_metadata(legacy, operation_id, close_date=close_date, method=method, repurchase_value=repurchase, result=realized)
        message = "Exercício registrado: PUT encerrada e 100 ações incluídas na carteira." if is_assignment else "Recompra identificada e operação encerrada."
        return jsonify({"ok": True, "operation_id": operation_id, "note_saved": True, "closed": True, "equity_lot": lot, "redirect": "/carteira-acoes" if is_assignment else "/operacoes-abertas", "message": message})

    @app.get("/api/opcoes/<option_code>")
    def lookup_option(option_code: str):
        code = str(option_code or "").strip().upper()
        if not code:
            return jsonify({"ok": False, "error": "Informe o código da opção."}), 400
        underlying = legacy.infer_acao_from_option(code)
        result = {
            "ok": True,
            "option_code": code,
            "asset": underlying,
            "strike": None,
            "expiry": None,
            "premium": None,
            "spot_price": None,
            "source": "inferência do código",
        }
        trade_date = legacy.parse_date(str(request.args.get("trade_date", "")))
        if trade_date and underlying:
            try:
                item = _lookup_b3_option(code, underlying, trade_date, legacy.DATA)
                if item:
                    result.update({
                        "asset": item.asset,
                        "strike": str(item.strike),
                        "expiry": item.expiry.isoformat(),
                        "premium": str(item.premium),
                        "spot_price": str(item.spot_price),
                        "source": f"B3 COTAHIST de {trade_date.strftime('%d/%m/%Y')}",
                    })
                    return jsonify(result)
            except (ProviderError, OSError, ValueError):
                pass
        imported = load_market_import(market_path)
        if imported:
            item = next((o for o in imported.opportunities if o.option_code.upper() == code), None)
            if item:
                result.update({
                    "asset": item.asset,
                    "strike": str(item.strike),
                    "expiry": item.expiry.isoformat(),
                    "premium": str(item.premium),
                    "spot_price": str(item.spot_price),
                    "source": "mercado importado",
                })
                return jsonify(result)
        for row in legacy.read_operacoes():
            if str(row.get("Ativo", "")).upper() == code:
                result.update({
                    "asset": legacy.infer_acao_from_option(code),
                    "strike": str(row.get("Strike", "") or "") or None,
                    "expiry": str(row.get("Vencimento", "") or "") or None,
                    "premium": str(row.get("Premio_opcao", "") or "") or None,
                    "spot_price": str(row.get("Cotacao_atual", "") or "") or None,
                    "source": "operação já cadastrada",
                })
                return jsonify(result)
        quote = legacy.cotacao_yahoo(underlying) if underlying else None
        if quote:
            result["spot_price"] = str(quote)
        return jsonify(result)

    @app.post("/api/operacoes")
    def create_operation():
        payload = request.get_json(silent=True) or {}
        try:
            option_code = str(payload.get("Ativo", "")).strip().upper()
            if not option_code:
                raise ValueError("Código da opção é obrigatório.")
            note_payload = payload.get("Nota_corretagem") if isinstance(payload.get("Nota_corretagem"), dict) else None
            if note_payload and imported_note_exists(legacy, note_payload):
                raise ValueError("Esta negociação da nota já foi importada.")
            if payload.get("Encerrar_operacao_id"):
                if not note_payload:
                    raise ValueError("A nota de recompra é obrigatória para o encerramento automático.")
                return close_from_note(str(payload["Encerrar_operacao_id"]), note_payload, option_code)
            option_type = str(payload.get("Tipo", "PUT")).upper()
            if option_type not in {"PUT", "CALL"}:
                raise ValueError("Tipo de opção inválido.")
            raw_strategy = str(payload.get("Estrategia", "Venda")).strip().lower()
            strategy = {"venda": "Venda", "compra": "Compra", "venda coberta": "Venda Coberta", "call coberta": "Venda Coberta"}.get(raw_strategy, "")
            if strategy not in {"Venda", "Compra", "Venda Coberta"}:
                raise ValueError("Operação inválida.")
            expiry_text = str(payload.get("Vencimento", "")).strip()
            expiry = legacy.parse_date(expiry_text)
            if expiry is None:
                raise ValueError("Vencimento inválido.")
            contracts = _decimal(payload.get("Contratos"), "Quantidade", allow_zero=False)
            strike = _decimal(payload.get("Strike"), "Strike", allow_zero=False)
            premium = _decimal(payload.get("Premio_opcao"), "Prêmio", allow_zero=False)
            costs = _decimal(payload.get("Custos"), "Custos")
            irrf = _decimal(payload.get("IRRF"), "IRRF")
            spot = _decimal(payload.get("Cotacao_atual"), "Cotação atual")
            underlying = str(payload.get("Ativo_subjacente") or legacy.infer_acao_from_option(option_code)).strip().upper()
            if strategy in {"Venda", "Venda Coberta"} and option_type == "CALL":
                validate_covered_call(legacy, underlying, contracts)
                strategy = "Venda Coberta"
            rows = legacy.read_csv(legacy.OPERACOES)
            next_id = max([int(legacy.fnum(row.get("ID"))) for row in rows] + [0]) + 1
            row = {
                "ID": str(next_id),
                "Data abertura": (legacy.parse_date(str(payload.get("Data_abertura", ""))) or date.today()).isoformat(),
                "Ativo": option_code,
                "Tipo": option_type,
                "Estratégia": strategy,
                "Status": "Aberta",
                "Contratos": str(contracts),
                "Strike": str(strike),
                "Premio_opcao": str(premium),
                "Custos": str(costs),
                "IRRF": str(irrf),
                "Vencimento": expiry.isoformat(),
                "Cotacao_atual": str(spot),
                "Resultado_realizado": "0",
            }
            if legacy.USE_POSTGRES:
                row["ID"] = str(legacy.salvar_operacao_pg(row))
            else:
                rows.append(row)
                legacy.write_csv(legacy.OPERACOES, rows, [
                    "ID", "Data abertura", "Ativo", "Tipo", "Estratégia", "Status",
                    "Contratos", "Strike", "Premio_opcao", "Custos", "IRRF",
                    "Vencimento", "Cotacao_atual", "Resultado_realizado",
                ])
            save_operation_metadata(
                legacy, row["ID"],
                interested=normalize_exercise_interest(payload.get("Interesse_exercicio", False)),
                underlying_asset=underlying,
            )
            note_saved = False
            if isinstance(payload.get("Nota_corretagem"), dict):
                note_saved = save_imported_note(legacy, payload["Nota_corretagem"], row["ID"])
            return jsonify({"ok": True, "operation_id": row["ID"], "note_saved": note_saved, "message": "Operação cadastrada com sucesso."})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
