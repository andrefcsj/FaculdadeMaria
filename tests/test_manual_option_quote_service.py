import tempfile
from pathlib import Path
from unittest.mock import patch

import legacy_app
from services.dashboard_market_service import load_option_quotes
from services.manual_option_quote_service import load_manual_option_quotes, save_manual_option_quote


def test_manual_profit_quote_is_persisted_with_time_and_has_priority():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        with patch.object(legacy_app, "DATA", root), patch.object(legacy_app, "USE_POSTGRES", False):
            saved = save_manual_option_quote(legacy_app, "CPLES15", "0,58", "2026-07-17T16:51")
            assert saved == {"price": "0.58", "quoted_at": "2026-07-17T16:51"}
            assert load_manual_option_quotes(legacy_app)["CPLES15"] == saved
            quotes = load_option_quotes(legacy_app)
            assert quotes["CPLES15"]["price"] == 0.58
            assert quotes["CPLES15"]["source"] == "ProfitPro • 17/07/2026 às 16:51"
