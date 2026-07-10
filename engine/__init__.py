"""Public API for the FaculdadeMaria Decision Engine."""

from .core import OptionOpportunity
from .errors import DecisionEngineError
from .metrics import PutMetricAssumptions, PutMetrics, calculate_put_metrics
from .version import ENGINE_VERSION, get_engine_version

__all__ = [
    "DecisionEngineError",
    "ENGINE_VERSION",
    "OptionOpportunity",
    "PutMetricAssumptions",
    "PutMetrics",
    "calculate_put_metrics",
    "get_engine_version",
]
