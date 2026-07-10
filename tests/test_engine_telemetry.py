import unittest
from engine.telemetry import TelemetryRecorder

class EngineTelemetryTests(unittest.TestCase):
    def test_records_event_metric_and_span(self):
        telemetry = TelemetryRecorder()
        telemetry.record_event('event')
        telemetry.record_metric('metric', 1)
        with telemetry.span('span'):
            pass
        summary = telemetry.summary()
        self.assertEqual(summary['events'], 1)
        self.assertEqual(summary['metrics'], 1)
        self.assertEqual(summary['spans'], 1)
