import legacy_app


def test_existing_cple3_options_use_correct_underlying():
    assert legacy_app.infer_acao_from_option("CPLES15") == "CPLE3"
    assert legacy_app.infer_acao_from_option("CPLES129") == "CPLE3"
