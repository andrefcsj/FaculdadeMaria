"""Automatic, explainable asset-quality profiles from CVM open DFP data."""
from __future__ import annotations

from csv import DictReader
import io
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Mapping
from urllib.request import Request, urlopen
from zipfile import ZipFile

from ..asset.quality import AssetQualityProfile
from .base import ProviderError


def download_latest_dfp(destination: str | Path, *, reference: date | None = None) -> Path:
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    year = (reference or date.today()).year - 1
    url = f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{year}.zip"
    try:
        request = Request(url, headers={"User-Agent": "FaculdadeMaria/1.0 (+dados-abertos-CVM)"})
        with urlopen(request, timeout=45) as response:
            payload = response.read()
        temporary = target.with_suffix(".tmp")
        temporary.write_bytes(payload)
        with ZipFile(temporary) as archive:
            if not any("DRE_con" in name for name in archive.namelist()):
                raise ValueError("DFP sem demonstrações consolidadas")
        temporary.replace(target)
        return target
    except Exception as exc:
        raise ProviderError("Não foi possível atualizar os dados DFP da CVM", details={"url": url, "error": str(exc)}) from exc


def _ratio(value: Decimal, low: Decimal, high: Decimal) -> Decimal:
    if high <= low:
        return Decimal("0")
    return max(Decimal("0"), min(Decimal("1"), (value - low) / (high - low)))


class CvmFundamentalsProvider:
    """Build quality profiles without hiding missing data or sector assumptions."""

    name = "cvm_dfp_open_data"

    def __init__(self, source: str | Path, issuers: Mapping[str, Mapping[str, str]]):
        self.source = Path(source)
        self.issuers = issuers

    def _accounts(self) -> dict[str, dict[str, dict[str, Decimal]]]:
        if not self.source.exists():
            raise ProviderError("Arquivo DFP não encontrado")
        wanted_cnpjs = {str(config["cnpj"]) for config in self.issuers.values()}
        output = {cnpj: {"current": {}, "previous": {}} for cnpj in wanted_cnpjs}
        with ZipFile(self.source) as archive:
            names = [name for name in archive.namelist() if any(key in name for key in ("DRE_con", "BPA_con", "BPP_con", "DFC_MI_con"))]
            for name in names:
                text = io.TextIOWrapper(archive.open(name), encoding="latin-1", newline="")
                for row in DictReader(text, delimiter=";"):
                    cnpj = row.get("CNPJ_CIA", "")
                    if cnpj not in wanted_cnpjs:
                        continue
                    period = "current" if row.get("ORDEM_EXERC") == "ÚLTIMO" else "previous"
                    code = row.get("CD_CONTA", "")
                    try:
                        value = Decimal(row.get("VL_CONTA", "0"))
                    except InvalidOperation:
                        continue
                    output[cnpj][period][code] = value
        return output

    @staticmethod
    def _get(accounts: dict[str, Decimal], *codes: str) -> Decimal | None:
        for code in codes:
            if code in accounts:
                return accounts[code]
        return None

    def _score_company(self, current: dict[str, Decimal], previous: dict[str, Decimal]) -> tuple[Decimal | None, Decimal, list[str], list[str]]:
        revenue = self._get(current, "3.01")
        profit = self._get(current, "3.11")
        previous_profit = self._get(previous, "3.11")
        assets = self._get(current, "1")
        equity = self._get(current, "2.03")
        cfo = self._get(current, "6.01")
        values = (revenue, profit, previous_profit, assets, equity, cfo)
        confidence = Decimal(sum(value is not None for value in values)) / Decimal(len(values))
        if profit is None or assets is None or equity is None or equity <= 0:
            return None, confidence, [], ["Dados fundamentais essenciais ausentes"]
        positives, warnings = [], []
        score = Decimal("0")
        if profit > 0:
            score += Decimal("0.25"); positives.append("Lucro líquido positivo")
        else:
            warnings.append("Prejuízo no último exercício")
        roe = profit / equity
        score += _ratio(roe, Decimal("0"), Decimal("0.20")) * Decimal("0.25")
        if roe >= Decimal("0.12"): positives.append("ROE consistente")
        elif roe < Decimal("0.06"): warnings.append("ROE baixo")
        if cfo is not None and cfo > 0:
            score += Decimal("0.20"); positives.append("Geração operacional de caixa positiva")
        else:
            warnings.append("Caixa operacional ausente ou negativo")
        if previous_profit is not None and previous_profit > 0 and profit > 0:
            score += Decimal("0.15"); positives.append("Lucro positivo em dois exercícios")
        equity_ratio = equity / assets if assets > 0 else Decimal("0")
        score += _ratio(equity_ratio, Decimal("0.10"), Decimal("0.50")) * Decimal("0.15")
        return min(score, Decimal("1")), confidence, positives, warnings

    def _score_financial(self, current: dict[str, Decimal], previous: dict[str, Decimal]) -> tuple[Decimal | None, Decimal, list[str], list[str]]:
        profit = self._get(current, "3.11", "3.09")
        previous_profit = self._get(previous, "3.11", "3.09")
        equity = self._get(current, "2.08", "2.07", "2.03")
        previous_equity = self._get(previous, "2.08", "2.07", "2.03")
        values = (profit, previous_profit, equity, previous_equity)
        confidence = Decimal(sum(value is not None for value in values)) / Decimal(len(values))
        if profit is None or equity is None or equity <= 0:
            return None, confidence, [], ["Dados financeiros essenciais ausentes"]
        positives, warnings = [], []
        score = Decimal("0")
        if profit > 0:
            score += Decimal("0.30"); positives.append("Lucro líquido positivo")
        else:
            warnings.append("Prejuízo no último exercício")
        roe = profit / equity
        score += _ratio(roe, Decimal("0"), Decimal("0.20")) * Decimal("0.30")
        if previous_profit is not None and previous_profit > 0 and profit > 0:
            score += Decimal("0.20"); positives.append("Lucro positivo em dois exercícios")
        if previous_equity is not None and previous_equity > 0 and equity >= previous_equity:
            score += Decimal("0.20"); positives.append("Patrimônio estável ou crescente")
        elif previous_equity is not None:
            warnings.append("Patrimônio recuou")
        return min(score, Decimal("1")), confidence, positives, warnings

    def fetch(self) -> dict[str, AssetQualityProfile]:
        accounts = self._accounts()
        profiles = {}
        for ticker, config in self.issuers.items():
            company = accounts.get(str(config["cnpj"]), {"current": {}, "previous": {}})
            model = str(config.get("model", "company"))
            scorer = self._score_financial if model == "financial" else self._score_company
            score, confidence, positives, warnings = scorer(company["current"], company["previous"])
            profiles[ticker] = AssetQualityProfile(
                asset=ticker,
                assignment_eligible=True,
                long_term_suitable=True,
                quality_score=score,
                data_confidence=confidence,
                warnings=tuple(warnings),
                positive_notes=tuple(positives),
                source=f"{self.name}:{model}",
            )
        return profiles
