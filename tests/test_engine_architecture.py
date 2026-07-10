import unittest
from engine import ENGINE_VERSION, get_engine_version
from engine.core import run_pipeline

class EngineArchitectureTests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(ENGINE_VERSION, get_engine_version())

    def test_pipeline_pass_through(self):
        data = [{'id': 1}]
        result = run_pipeline(data)
        self.assertEqual(result['candidates'], data)
        self.assertIn('telemetry', result['metadata'])
