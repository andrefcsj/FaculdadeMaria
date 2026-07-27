from services.open_operations_extension import effective_exercise_price


def test_short_put_effective_acquisition_price_subtracts_net_premium():
    operation = {
        "Tipo": "PUT", "Estratégia": "Venda", "Contratos_n": 1,
        "Strike_n": 15.28, "Premio_liquido": 43.90,
    }
    assert round(effective_exercise_price(operation, 100), 2) == 14.84


def test_covered_call_effective_sale_price_adds_net_premium():
    operation = {
        "Tipo": "CALL", "Estratégia": "Venda Coberta", "Contratos_n": 1,
        "Strike_n": 16, "Premio_liquido": 29,
    }
    assert round(effective_exercise_price(operation, 100), 2) == 16.29


def test_purchased_option_has_no_exercise_sale_or_acquisition_price():
    operation = {
        "Tipo": "PUT", "Estratégia": "Compra", "Contratos_n": 1,
        "Strike_n": 15, "Premio_liquido": -30,
    }
    assert effective_exercise_price(operation, 100) is None
