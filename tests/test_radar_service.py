from datetime import date, datetime, timezone
from decimal import Decimal

from engine import AssetQualityProfile, OptionOpportunity
from services.radar_service import build_demo_radar, build_radar, build_radar_from_market, build_radar_from_operations


def test_demo_radar_returns_ranked_cards():
    cards = build_demo_radar(date(2026, 7, 10))

    assert len(cards) == 3
    assert [card.position for card in cards] == [1, 2, 3]
    assert cards[0].asset == "BBAS3"
    assert cards[0].status == "eligible"
    assert "ROI" in cards[0].reason


def test_demo_radar_keeps_blocked_operation_explainable():
    cards = build_demo_radar(date(2026, 7, 10))
    discarded = [card for card in cards if card.status == "discarded"]

    assert discarded
    assert discarded[0].score is None
    assert "descartada" in discarded[0].headline.lower()
    assert "exercício" in discarded[0].reason.lower() or "ativo" in discarded[0].reason.lower()


def test_demo_radar_uses_four_percent_target_context():
    cards = build_demo_radar(date(2026, 7, 10))

    assert cards[0].gross_roi_pct == "4,07%"
    assert cards[1].gross_roi_pct == "4,00%"


def test_demo_radar_shows_option_premium_and_strike():
    cards = build_demo_radar(date(2026, 7, 10))

    assert cards[0].option_premium == "R$ 1,10"
    assert cards[0].strike == "R$ 27,00"
    assert cards[1].option_premium == "R$ 0,40"
    assert cards[1].strike == "R$ 10,00"
    assert cards[2].option_premium == "R$ 1,20"
    assert cards[2].strike == "R$ 15,00"


def test_demo_radar_shows_expiry_date_with_remaining_days():
    cards = build_demo_radar(date(2026, 7, 10))

    assert cards[0].expiry_date == "14/08/2026"
    assert cards[0].expiry_display == "14/08/2026 - 35 dias"
    assert cards[0].dte == 35


def test_demo_radar_translates_safety_attention_message():
    cards = build_demo_radar(date(2026, 7, 10))
    texts = " ".join(card.reason for card in cards)

    assert "Safety filters require attention" not in texts
    if "filtros de segurança" in texts.lower():
        assert "exigem atenção" in texts.lower()


def test_demo_radar_classifies_roi_above_three_percent_as_excellent():
    cards = build_demo_radar(date(2026, 7, 10))

    assert cards[0].roi_concept == "Excelente"
    assert cards[0].roi_concept_class == "excellent"
    assert cards[1].roi_concept == "Excelente"


def test_operation_like_rows_calculate_net_price_from_unit_premium():
    operations = [
        {
            "ID": "1",
            "Ativo": "BBASQ270",
            "ticker": "BBAS3",
            "Tipo": "PUT",
            "Status": "Aberta",
            "Contratos": "1",
            "Strike": "27.00",
            "Premio_opcao": "1.10",
            "Custos": "0",
            "IRRF": "0",
            "Vencimento": "2026-08-14",
            "Cotacao_atual": "28.50",
        }
    ]

    cards = build_radar_from_operations(operations, date(2026, 7, 10))

    assert len(cards) == 1
    assert cards[0].source == "real"
    assert cards[0].asset == "BBAS3"
    assert cards[0].option_code == "BBASQ270"
    assert cards[0].option_premium == "R$ 1,10"
    assert cards[0].strike == "R$ 27,00"
    assert cards[0].net_price == "R$ 25,90"
    assert cards[0].gross_roi_pct == "4,07%"
    assert cards[0].expiry_display == "14/08/2026 - 35 dias"
    assert cards[0].roi_concept == "Excelente"


def test_operation_like_row_roi_below_one_and_half_percent_is_bad_concept_only():
    operations = [
        {
            "ID": "2",
            "Ativo": "PETRQ200",
            "ticker": "PETR4",
            "Tipo": "PUT",
            "Status": "Aberta",
            "Contratos": "1",
            "Strike": "20.00",
            "Premio_opcao": "0.20",
            "Custos": "0",
            "IRRF": "0",
            "Vencimento": "2026-08-14",
            "Cotacao_atual": "22.00",
        }
    ]

    cards = build_radar_from_operations(operations, date(2026, 7, 10))

    assert len(cards) == 1
    assert cards[0].option_premium == "R$ 0,20"
    assert cards[0].gross_roi_pct == "1,00%"
    assert cards[0].roi_concept == "Ruim"
    assert cards[0].roi_concept_class == "bad"


def test_public_radar_does_not_turn_open_positions_into_market_opportunities():
    cards = build_radar(
        [
            {
                "Ativo": "BBDCT20",
                "ticker": "BBDC4",
                "Tipo": "PUT",
                "Status": "Aberta",
                "Contratos": "1",
                "Strike": "20.00",
                "Premio_opcao": "0.67",
                "Vencimento": "2026-08-20",
                "Cotacao_atual": "21.00",
            }
        ],
        date(2026, 7, 10),
    )

    assert len(cards) == 3
    assert {card.source for card in cards} == {"demo"}
    assert {card.asset for card in cards} == {"BBAS3", "ITSA4", "ALTO3"}


def test_radar_exposes_freshness_source_and_confidence_separately_from_score():
    opportunity = OptionOpportunity(
        asset="BBAS3", option_code="BBASQ270", option_type="PUT", expiry=date(2026, 8, 14),
        spot_price=Decimal("28.50"), strike=Decimal("27"), premium=Decimal("1.10"),
        bid=Decimal("1.05"), ask=Decimal("1.15"), liquidity=Decimal("32000"),
        timestamp=datetime(2026, 7, 11, tzinfo=timezone.utc), data_confidence=Decimal("0.80"),
        source="b3_cotahist_eod",
    )
    profile = AssetQualityProfile(
        asset="BBAS3", assignment_eligible=True, long_term_suitable=True,
        quality_score=Decimal("0.88"), data_confidence=Decimal("0.90"), source="cvm",
    )

    card = build_radar_from_market([opportunity], {"BBAS3": profile}, date(2026, 7, 12))[0]

    assert card.source_label == "B3 COTAHIST"
    assert card.data_mode == "Fechamento EOD"
    assert card.data_timestamp == "11/07/2026"
    assert card.data_age == "1 dia"
    assert card.freshness_status == "fresh"
    assert card.confidence_label == "Média"
    assert card.confidence_pct == "80%"


def test_radar_warns_when_reference_timestamp_is_unknown():
    card = build_demo_radar(date(2026, 7, 12))[0]
    assert card.freshness_status == "unknown"
    assert "Confirme o preço" in card.data_warning
