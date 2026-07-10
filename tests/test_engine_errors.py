import unittest
from engine import DecisionEngineError

class EngineErrorTests(unittest.TestCase):
    def test_structured_error(self):
        error = DecisionEngineError('boom')
        self.assertEqual(error.to_dict()['code'], 'decision_engine_error')
        self.assertEqual(error.to_dict()['message'], 'boom')
