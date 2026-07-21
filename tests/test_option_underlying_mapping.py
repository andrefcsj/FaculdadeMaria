import legacy_app


def test_existing_cple3_options_use_correct_underlying():
    assert legacy_app.infer_acao_from_option("CPLES15") == "CPLE3"
    assert legacy_app.infer_acao_from_option("CPLES129") == "CPLE3"


def test_every_cple_option_series_uses_cple3():
    for option_code in ("CPLEA101", "CPLEH150", "CPLES999", "CPLEX42"):
        assert legacy_app.infer_acao_from_option(option_code) == "CPLE3"
