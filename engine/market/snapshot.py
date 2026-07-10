"""Normalized market snapshot structures."""
from __future__ import annotations

from dataclasses import dataclass

from ..core.contracts import OptionOpportunity


@dataclass(frozen=True, slots=True)
class NormalizedMarketSnapshot:
    """A normalized opportunity plus explicit missing-field metadata."""

    opportunity: OptionOpportunity
    missing_fields: tuple[str, ...]

    @classmethod
    def from_opportunity(cls, opportunity: OptionOpportunity) -> "NormalizedMarketSnapshot":
        return cls(opportunity=opportunity, missing_fields=opportunity.missing_fields())
