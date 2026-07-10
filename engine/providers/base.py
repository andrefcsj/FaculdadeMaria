"""Provider contracts; no network integration in Sprint 1.1-R."""
from abc import ABC, abstractmethod
from ..errors import EngineProviderError

class ProviderError(EngineProviderError):
    pass

class MarketDataProvider(ABC):
    @property
    @abstractmethod
    def name(self):
        raise NotImplementedError

    @abstractmethod
    def fetch(self, request):
        raise NotImplementedError
