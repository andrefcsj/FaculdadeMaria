"""Public API for the FaculdadeMaria Decision Engine."""

from .asset import AssetQualityAssessment, AssetQualityPolicy, AssetQualityProfile, assess_asset_quality
from .core import OptionOpportunity
from .errors import DecisionEngineError
from .filters import SafetyFilterConfig, SafetyEvaluation, evaluate_put_safety
from .indicators import (
    BollingerBands,
    average_true_range,
    bollinger_bands,
    historical_volatility,
    moving_average_21,
    moving_average_200,
    relative_strength_index,
    simple_moving_average,
    strike_distance_in_atr,
    true_range,
)
from .metrics import PutMetricAssumptions, PutMetrics, calculate_put_metrics
from .strategy import PutStrategyConfig, PutStrategyEvaluation, evaluate_put_strategy
from .version import ENGINE_VERSION, get_engine_version

__all__ = [
    "AssetQualityAssessment",
    "AssetQualityPolicy",
    "AssetQualityProfile",
    "BollingerBands",
    "DecisionEngineError",
    "ENGINE_VERSION",
    "OptionOpportunity",
    "PutMetricAssumptions",
    "PutMetrics",
    "PutStrategyConfig",
    "PutStrategyEvaluation",
    "SafetyEvaluation",
    "SafetyFilterConfig",
    "assess_asset_quality",
    "average_true_range",
    "bollinger_bands",
    "calculate_put_metrics",
    "evaluate_put_safety",
    "evaluate_put_strategy",
    "get_engine_version",
    "historical_volatility",
    "moving_average_21",
    "moving_average_200",
    "relative_strength_index",
    "simple_moving_average",
    "strike_distance_in_atr",
    "true_range",
]
