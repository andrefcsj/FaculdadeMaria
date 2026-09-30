from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "cloudflare" / "pilot" / "tools" / "export_local_data.py"
SPEC = importlib.util.spec_from_file_location("cloudflare_export", MODULE_PATH)
assert SPEC and SPEC.loader
cloudflare_export = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cloudflare_export)


def test_build_sql_preserves_csv_records_and_escapes_quotes(tmp_path):
    (tmp_path / "operacoes.csv").write_text(
        "Data abertura,Ativo,Tipo,Estratégia,Status,Contratos,Strike,Premio_opcao,Custos,IRRF,Vencimento,Cotacao_atual,Resultado_realizado\n"
        "2026-01-10,PETR4,PUT,Venda,aberta,1,30,1.2,0,0,2026-02-20,29,\n",
        encoding="utf-8",
    )
    (tmp_path / "config.csv").write_text(
        "Parametro,Valor\nCapital d'água,4000\n", encoding="utf-8"
    )
    (tmp_path / "fechadas.csv").write_text(
        "Ativo,Data fechamento,Resultado_final\nVALE3,2026-01-20,120.50\n",
        encoding="utf-8",
    )

    sql = cloudflare_export.build_sql(tmp_path)

    assert "INSERT INTO operacoes" in sql
    assert "'PETR4'" in sql
    assert "Capital d''água" in sql
    assert "INSERT INTO closed_operations" in sql
    assert "BEGIN TRANSACTION;" in sql
    assert sql.rstrip().endswith("COMMIT;")
