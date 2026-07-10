import unittest
from engine.core import DecisionContext

class EngineContextTests(unittest.TestCase):
    def test_trace_also_records_telemetry(self):
        context = DecisionContext()
        trace = context.add_trace('pipeline', 'pass_through')
        self.assertEqual(trace['stage'], 'pipeline')
        self.assertEqual(len(context.traces), 1)
        self.assertEqual(context.telemetry.summary()['events'], 1)
