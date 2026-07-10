from datetime import date

from services.radar_service import build_demo_radar


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
