import unittest
from engine.errors import EngineProviderError
from engine.providers import ProviderError

class EngineProviderContractTests(unittest.TestCase):
    def test_provider_error_uses_engine_hierarchy(self):
        self.assertTrue(issubclass(ProviderError, EngineProviderError))
