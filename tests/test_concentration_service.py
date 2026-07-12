from decimal import Decimal

from services.concentration_service import build_portfolio_concentration, concentration_reading


def test_builds_only_open_put_concentration_and_projects_increment():
    portfolio = build_portfolio_concentration([
        {"Ativo": "PETRT123", "Tipo": "PUT", "Status": "Aberta", "Capital": "2000"},
        {"Ativo": "PETRA100", "Tipo": "PUT", "Status": "Encerrada", "Capital": "9000"},
        {"Ativo": "VALEC100", "Tipo": "CALL", "Status": "Aberta", "Capital": "5000"},
    ], "10000")

    assert portfolio.allocated_by_asset == {"PETR": Decimal("2000")}
    assert portfolio.projected_share("PETR", Decimal("1000")) == Decimal("0.3")
    assert portfolio.projected_share("VALE", Decimal("1000")) == Decimal("0.1")


def test_concentration_reading_uses_official_thresholds():
    assert concentration_reading(Decimal("0.20"))[0] == "balanced"
    assert concentration_reading(Decimal("0.30"))[0] == "attention"
    assert concentration_reading(Decimal("0.36"))[0] == "high"
