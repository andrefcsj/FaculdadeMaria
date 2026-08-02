from app import app
import legacy_app


def test_jade_page_and_mount_plan(monkeypatch):
    monkeypatch.setattr(legacy_app, "cotacao_yahoo", lambda _ticker: 37.0)
    client = app.test_client()

    page = client.get("/estrategias/jade-lizard")
    assert page.status_code == 200
    assert b"Radar Jade Lizard" in page.data
    assert b"Modo de proje" in page.data

    plan = client.post("/api/estrategias/jade-lizard/montar", json={
        "ticker": "PETR4", "put_code": "PETRP3500",
        "short_call_code": "PETRC3900", "long_call_code": "PETRC4000",
    })
    assert plan.status_code == 200
    assert plan.get_json()["status"] == "plano_pronto"
    assert len(plan.get_json()["legs"]) == 3
