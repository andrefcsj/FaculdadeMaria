from dataclasses import dataclass, field
from ..telemetry import TelemetryRecorder

@dataclass
class DecisionContext:
    metadata: dict = field(default_factory=dict)
    traces: list = field(default_factory=list)
    telemetry: TelemetryRecorder = field(default_factory=TelemetryRecorder)

    def add_trace(self, stage, message, details=None):
        trace = {'stage': stage, 'message': message, 'details': dict(details or {})}
        self.traces.append(trace)
        self.telemetry.record_event('pipeline.trace', {'stage': stage})
        return trace
