from decimal import Decimal

from services.premium_totals_service import calculate_premium_totals


def operation(identifier, *, status="Aberta", premium="100", result="0", strategy="Venda"):
    return {
        "ID": str(identifier), "Tipo": "PUT", "Estratégia": strategy,
        "Status": status, "Contratos": "1", "Premio_liquido": premium,
        "Resultado_realizado": result,
    }


def test_open_and_expired_premiums_are_fully_retained():
    received, retained = calculate_premium_totals(
        [operation(1), operation(2, status="Encerrada")],
        {"2": {"method": "virou_po"}},
    )
    assert received == Decimal("200")
    assert retained == Decimal("200")


def test_repurchase_is_subtracted_from_retained_but_not_received_total():
    received, retained = calculate_premium_totals(
        [operation(1, status="Encerrada")],
        {"1": {"method": "recompra", "repurchase_value": "0.30"}},
    )
    assert received == Decimal("100")
    assert retained == Decimal("70.00")


def test_loss_making_repurchase_reduces_accumulated_retained_premium():
    _, retained = calculate_premium_totals(
        [operation(1, status="Encerrada")],
        {"1": {"method": "recompra", "repurchase_value": "1.30"}},
    )
    assert retained == Decimal("-30.00")


def test_covered_call_exercise_keeps_only_option_premium_not_share_sale_result():
    covered = operation(1, status="Encerrada", premium="80", result="1250")
    covered.update({"Tipo": "CALL", "Estratégia": "Venda coberta"})
    received, retained = calculate_premium_totals(
        [covered], {"1": {"method": "exercida"}},
    )
    assert received == Decimal("80")
    assert retained == Decimal("80")
