from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile
from decimal import Decimal

from engine.providers import CvmFundamentalsProvider


HEADER = "CNPJ_CIA;DT_REFER;VERSAO;DENOM_CIA;CD_CVM;GRUPO_DFP;MOEDA;ESCALA_MOEDA;ORDEM_EXERC;DT_FIM_EXERC;CD_CONTA;DS_CONTA;VL_CONTA;ST_CONTA_FIXA\n"


def row(code, value, order="ÚLTIMO"):
    return f"00.000.000/0001-00;2025-12-31;1;TESTE;1;DF;REAL;MIL;{order};2025-12-31;{code};Conta;{value};S\n"


class CvmFundamentalsProviderTests(unittest.TestCase):
    def test_builds_explainable_profile_from_official_account_codes(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "dfp.zip"
            with ZipFile(path, "w") as archive:
                archive.writestr("dfp_DRE_con.csv", (HEADER + row("3.01", 1000) + row("3.11", 120) + row("3.11", 100, "PENÚLTIMO")).encode("latin-1"))
                archive.writestr("dfp_BPA_con.csv", (HEADER + row("1", 2000)).encode("latin-1"))
                archive.writestr("dfp_BPP_con.csv", (HEADER + row("2.03", 800)).encode("latin-1"))
                archive.writestr("dfp_DFC_MI_con.csv", (HEADER + row("6.01", 180)).encode("latin-1"))
            profiles = CvmFundamentalsProvider(path, {"TEST3": {"cnpj": "00.000.000/0001-00", "model": "company"}}).fetch()
        profile = profiles["TEST3"]
        self.assertIsNotNone(profile.quality_score)
        self.assertGreaterEqual(profile.quality_score, Decimal("0.60"))
        self.assertEqual(profile.data_confidence, Decimal("1"))
        self.assertIn("Lucro líquido positivo", profile.positive_notes)

    def test_missing_essential_accounts_never_invents_score(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "dfp.zip"
            with ZipFile(path, "w") as archive:
                archive.writestr("dfp_DRE_con.csv", (HEADER + row("3.01", 1000)).encode("latin-1"))
                archive.writestr("dfp_BPA_con.csv", HEADER.encode("latin-1"))
                archive.writestr("dfp_BPP_con.csv", HEADER.encode("latin-1"))
                archive.writestr("dfp_DFC_MI_con.csv", HEADER.encode("latin-1"))
            profile = CvmFundamentalsProvider(path, {"TEST3": {"cnpj": "00.000.000/0001-00", "model": "company"}}).fetch()["TEST3"]
        self.assertIsNone(profile.quality_score)
        self.assertTrue(profile.warnings)
