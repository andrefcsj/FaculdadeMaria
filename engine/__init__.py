"""Public foundation API for the FaculdadeMaria Decision Engine."""

from .errors import DecisionEngineError
from .version import ENGINE_VERSION, get_engine_version

__all__ = ['DecisionEngineError', 'ENGINE_VERSION', 'get_engine_version']
