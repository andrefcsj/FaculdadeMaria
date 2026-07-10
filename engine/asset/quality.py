"""Asset quality checks for systematic PUT selling.

This module does not fetch fundamentals or market data. It evaluates only data
explicitly provided by callers so premium/ROI cannot hide an unsuitable asset.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from ..errors import EngineContractError

PASSED = "passed"
ATTENTION = "attention"
FAILED = "failed"
INSUFFICIENT_DATA = "insufficient_data"


def _as_tuple_of_str(values: tuple[str, ...] | list[str] | None, *, field: str) -> tuple[str, ...]:
    if values is None:
        return tuple()
    if not isinstance(values, (tuple, list)):
        raise EngineContractError(f"{field} must be a tuple/list of strings", details={"field": field})
    normalized: list[str] = []
    for item in values:
        if not isinstance(item, str) or not item.strip():
            raise EngineContractError(f"{field} must contain non-empty strings", details={"field": field})
        normalized.append(item.strip())
    return tuple(normalized)


def _validate_ratio(value: Decimal | None, *, field: str) -> Decimal | None:
    if value is None:
        return None
    if not isinstance(value, Decimal):
        raise EngineContractError(f"{field} must be Decimal or None", details={"field": field, "value": repr(value)})
    if not value.is_finite():
        raise EngineContractError(f"{field} must be finite", details={"field": field})
    if value < 0 or value > 1:
        raise EngineContractError(f"{field} must be between 0 and 1", details={"field": field, "value": repr(value)})
    return value


def _validate_bool(value: bool | None, *, field: str) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise EngineContractError(f"{field} must be bool or None", details={"field": field, "value": repr(value)})
    return value


@dataclass(frozen=True, slots=True)
class AssetQualityProfile:
    """Caller-supplied asset quality profile.

    The profile is intentionally explicit: no quality, eligibility, event, or
    concentration information is inferred by the engine.
    """

    asset: str
    assignment_eligible: bool | None = None
    long_term_suitable: bool | None = None
    quality_score: Decimal | None = None
    data_confidence: Decimal | None = None
    concentration_pct: Decimal | None = None
    blocking_events: tuple[str, ...] = tuple()
    warnings: tuple[str, ...] = tuple()
    positive_notes: tuple[str, ...] = tuple()
    source: str | None = None

    def __post_init__(self) -> None:
        asset = self.asset.strip() if isinstance(self.asset, str) else self.asset
        source = self.source.strip() if isinstance(self.source, str) else self.source

        if not isinstance(asset, str) or not asset:
            raise EngineContractError("asset must be a non-empty string", details={"field": "asset"})
        if source is not None and not source:
            raise EngineContractError("source cannot be blank", details={"field": "source"})

        object.__setattr__(self, "asset", asset)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "assignment_eligible", _validate_bool(self.assignment_eligible, field="assignment_eligible"))
        object.__setattr__(self, "long_term_suitable", _validate_bool(self.long_term_suitable, field="long_term_suitable"))
        object.__setattr__(self, "quality_score", _validate_ratio(self.quality_score, field="quality_score"))
        object.__setattr__(self, "data_confidence", _validate_ratio(self.data_confidence, field="data_confidence"))
        object.__setattr__(self, "concentration_pct", _validate_ratio(self.concentration_pct, field="concentration_pct"))
        object.__setattr__(self, "blocking_events", _as_tuple_of_str(self.blocking_events, field="blocking_events"))
        object.__setattr__(self, "warnings", _as_tuple_of_str(self.warnings, field="warnings"))
        object.__setattr__(self, "positive_notes", _as_tuple_of_str(self.positive_notes, field="positive_notes"))


@dataclass(frozen=True, slots=True)
class AssetQualityPolicy:
    min_quality_score: Decimal = Decimal("0.60")
    attention_quality_score: Decimal = Decimal("0.75")
    min_data_confidence: Decimal | None = Decimal("0.50")
    max_concentration_pct: Decimal | None = None
    require_assignment_eligible: bool = True
    require_long_term_suitable: bool = True

    def __post_init__(self) -> None:
        min_quality = _validate_ratio(self.min_quality_score, field="min_quality_score")
        attention = _validate_ratio(self.attention_quality_score, field="attention_quality_score")
        min_conf = _validate_ratio(self.min_data_confidence, field="min_data_confidence")
        max_conc = _validate_ratio(self.max_concentration_pct, field="max_concentration_pct")
        assert min_quality is not None and attention is not None

        if attention < min_quality:
            raise EngineContractError("attention_quality_score cannot be lower than min_quality_score")
        object.__setattr__(self, "min_quality_score", min_quality)
        object.__setattr__(self, "attention_quality_score", attention)
        object.__setattr__(self, "min_data_confidence", min_conf)
        object.__setattr__(self, "max_concentration_pct", max_conc)


@dataclass(frozen=True, slots=True)
class AssetQualityCheck:
    code: str
    status: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AssetQualityAssessment:
    asset: str
    status: str
    checks: tuple[AssetQualityCheck, ...]
    positive_factors: tuple[str, ...]
    warnings: tuple[str, ...]
    blockers: tuple[str, ...]
    quality_score: Decimal | None
    data_confidence: Decimal | None

    @property
    def passed(self) -> bool:
        return self.status == PASSED


def _status_from_checks(checks: list[AssetQualityCheck]) -> str:
    if any(check.status == FAILED for check in checks):
        return FAILED
    if any(check.status == INSUFFICIENT_DATA for check in checks):
        return INSUFFICIENT_DATA
    if any(check.status == ATTENTION for check in checks):
        return ATTENTION
    return PASSED


def assess_asset_quality(
    profile: AssetQualityProfile,
    policy: AssetQualityPolicy | None = None,
) -> AssetQualityAssessment:
    """Assess whether an asset is acceptable for assignment-focused PUT selling."""

    if not isinstance(profile, AssetQualityProfile):
        raise EngineContractError("profile must be AssetQualityProfile")
    policy = policy or AssetQualityPolicy()
    if not isinstance(policy, AssetQualityPolicy):
        raise EngineContractError("policy must be AssetQualityPolicy")

    checks: list[AssetQualityCheck] = []
    positive: list[str] = list(profile.positive_notes)
    warnings: list[str] = list(profile.warnings)
    blockers: list[str] = list(profile.blocking_events)

    if profile.blocking_events:
        checks.append(
            AssetQualityCheck(
                code="asset_blocking_events",
                status=FAILED,
                message="Asset has explicit blocking events",
                details={"events": list(profile.blocking_events)},
            )
        )

    if policy.require_assignment_eligible:
        if profile.assignment_eligible is None:
            checks.append(
                AssetQualityCheck(
                    code="assignment_eligibility_missing",
                    status=INSUFFICIENT_DATA,
                    message="Assignment eligibility was not supplied",
                )
            )
        elif not profile.assignment_eligible:
            checks.append(
                AssetQualityCheck(
                    code="asset_not_assignment_eligible",
                    status=FAILED,
                    message="Asset is not eligible for assignment under the current policy",
                )
            )
            blockers.append("Asset not accepted for assignment")
        else:
            checks.append(
                AssetQualityCheck(
                    code="assignment_eligible",
                    status=PASSED,
                    message="Asset is eligible for assignment under the current policy",
                )
            )
            positive.append("Asset accepted for assignment")

    if policy.require_long_term_suitable:
        if profile.long_term_suitable is None:
            checks.append(
                AssetQualityCheck(
                    code="long_term_suitability_missing",
                    status=INSUFFICIENT_DATA,
                    message="Long-term suitability was not supplied",
                )
            )
        elif not profile.long_term_suitable:
            checks.append(
                AssetQualityCheck(
                    code="not_long_term_suitable",
                    status=FAILED,
                    message="Asset is not suitable for the long-term profile",
                )
            )
            blockers.append("Asset not suitable for long-term holding")
        else:
            checks.append(
                AssetQualityCheck(
                    code="long_term_suitable",
                    status=PASSED,
                    message="Asset is suitable for the long-term profile",
                )
            )
            positive.append("Long-term suitability confirmed")

    if profile.quality_score is None:
        checks.append(
            AssetQualityCheck(
                code="quality_score_missing",
                status=INSUFFICIENT_DATA,
                message="Asset quality score was not supplied",
            )
        )
    elif profile.quality_score < policy.min_quality_score:
        checks.append(
            AssetQualityCheck(
                code="quality_score_below_minimum",
                status=FAILED,
                message="Asset quality score is below the configured minimum",
                details={"quality_score": str(profile.quality_score), "minimum": str(policy.min_quality_score)},
            )
        )
        blockers.append("Asset quality below minimum")
    elif profile.quality_score < policy.attention_quality_score:
        checks.append(
            AssetQualityCheck(
                code="quality_score_attention",
                status=ATTENTION,
                message="Asset quality score passes the minimum but deserves attention",
                details={"quality_score": str(profile.quality_score), "attention": str(policy.attention_quality_score)},
            )
        )
        warnings.append("Asset quality is acceptable but not strong")
    else:
        checks.append(
            AssetQualityCheck(
                code="quality_score_strong",
                status=PASSED,
                message="Asset quality score meets the preferred threshold",
                details={"quality_score": str(profile.quality_score)},
            )
        )
        positive.append("Asset quality score is strong")

    if policy.min_data_confidence is not None:
        if profile.data_confidence is None:
            checks.append(
                AssetQualityCheck(
                    code="asset_confidence_missing",
                    status=ATTENTION,
                    message="Asset data confidence was not supplied",
                )
            )
            warnings.append("Asset confidence data missing")
        elif profile.data_confidence < policy.min_data_confidence:
            checks.append(
                AssetQualityCheck(
                    code="asset_confidence_below_minimum",
                    status=ATTENTION,
                    message="Asset data confidence is below the configured minimum",
                    details={"data_confidence": str(profile.data_confidence), "minimum": str(policy.min_data_confidence)},
                )
            )
            warnings.append("Asset confidence below preferred minimum")
        else:
            checks.append(
                AssetQualityCheck(
                    code="asset_confidence_minimum",
                    status=PASSED,
                    message="Asset data confidence meets the configured minimum",
                    details={"data_confidence": str(profile.data_confidence)},
                )
            )

    if policy.max_concentration_pct is not None:
        if profile.concentration_pct is None:
            checks.append(
                AssetQualityCheck(
                    code="concentration_missing",
                    status=ATTENTION,
                    message="Concentration data was not supplied",
                )
            )
            warnings.append("Concentration data missing")
        elif profile.concentration_pct > policy.max_concentration_pct:
            checks.append(
                AssetQualityCheck(
                    code="concentration_above_maximum",
                    status=FAILED,
                    message="Asset concentration is above the configured maximum",
                    details={
                        "concentration_pct": str(profile.concentration_pct),
                        "maximum": str(policy.max_concentration_pct),
                    },
                )
            )
            blockers.append("Asset concentration above maximum")
        else:
            checks.append(
                AssetQualityCheck(
                    code="concentration_within_limit",
                    status=PASSED,
                    message="Asset concentration is within the configured maximum",
                    details={"concentration_pct": str(profile.concentration_pct)},
                )
            )

    status = _status_from_checks(checks)
    return AssetQualityAssessment(
        asset=profile.asset,
        status=status,
        checks=tuple(checks),
        positive_factors=tuple(dict.fromkeys(positive)),
        warnings=tuple(dict.fromkeys(warnings)),
        blockers=tuple(dict.fromkeys(blockers)),
        quality_score=profile.quality_score,
        data_confidence=profile.data_confidence,
    )
