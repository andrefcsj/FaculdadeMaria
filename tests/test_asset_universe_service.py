from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from services.asset_universe_service import load_personal_asset_universe


class PersonalAssetUniverseTests(unittest.TestCase):
    def test_empty_registry_approves_nothing(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "assets.csv"
            path.write_text(
                "option_root,ticker,assignment_eligible,long_term_suitable,quality_score,data_confidence,notes\n",
                encoding="utf-8",
            )
            roots, profiles = load_personal_asset_universe(path)
        self.assertEqual(roots, {})
        self.assertEqual(profiles, {})

    def test_explicit_personal_approval_builds_engine_profile(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "assets.csv"
            path.write_text(
                "option_root,ticker,assignment_eligible,long_term_suitable,quality_score,data_confidence,notes\n"
                "TEST,TEST3,sim,sim,0.82,0.90,Aprovado pelo titular para eventual exercício\n",
                encoding="utf-8",
            )
            roots, profiles = load_personal_asset_universe(path)
        self.assertEqual(roots, {"TEST": "TEST3"})
        self.assertTrue(profiles["TEST3"].assignment_eligible)
        self.assertEqual(str(profiles["TEST3"].quality_score), "0.82")

    def test_non_approved_asset_is_blocked(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "assets.csv"
            path.write_text(
                "option_root,ticker,assignment_eligible,long_term_suitable,quality_score,data_confidence,notes\n"
                "TEST,TEST3,nao,nao,0.40,0.80,Não aprovado\n",
                encoding="utf-8",
            )
            _, profiles = load_personal_asset_universe(path)
        self.assertFalse(profiles["TEST3"].assignment_eligible)
        self.assertTrue(profiles["TEST3"].blocking_events)
