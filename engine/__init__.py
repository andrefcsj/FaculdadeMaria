"""Public API for the FaculdadeMaria Decision Engine."""

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
from .version import ENGINE_VERSION, get_engine_version

__all__ = [
    "BollingerBands",
    "DecisionEngineError",
    "ENGINE_VERSION",
    "OptionOpportunity",
    "PutMetricAssumptions",
    "PutMetrics",
    "SafetyEvaluation",
    "SafetyFilterConfig",
    "average_true_range",
    "bollinger_bands",
    "calculate_put_metrics",
    "evaluate_put_safety",
    "get_engine_version",
    "historical_volatility",
    "moving_average_21",
    "moving_average_200",
    "relative_strength_index",
    "simple_moving_average",
    "strike_distance_in_atr",
    "true_range",
]
