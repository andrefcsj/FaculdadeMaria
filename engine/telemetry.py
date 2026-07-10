"""In-memory telemetry for the Decision Engine."""
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import perf_counter
from .errors import EngineTelemetryError

def _now():
    return datetime.now(timezone.utc).isoformat()

@dataclass
class TelemetryEvent:
    name: str
    timestamp: str
    attributes: dict = field(default_factory=dict)

@dataclass
class TelemetryMetric:
    name: str
    value: float
    timestamp: str
    attributes: dict = field(default_factory=dict)

@dataclass
class TelemetrySpan:
    name: str
    started_at: str
    attributes: dict = field(default_factory=dict)
    ended_at: object = None
    duration_ms: object = None
    _start: float = field(default_factory=perf_counter, repr=False)

    def finish(self):
        if self.ended_at is None:
            self.ended_at = _now()
            self.duration_ms = round((perf_counter() - self._start) * 1000, 3)
        return self

class TelemetryRecorder:
    def __init__(self):
        self.events, self.metrics, self.spans = [], [], []

    def record_event(self, name, attributes=None):
        if not name:
            raise EngineTelemetryError("Telemetry event name cannot be empty")
        item = TelemetryEvent(name, _now(), dict(attributes or {}))
        self.events.append(item)
        return item

    def record_metric(self, name, value, attributes=None):
        if not name or isinstance(value, bool) or not isinstance(value, (int, float)):
            raise EngineTelemetryError("Invalid telemetry metric")
        item = TelemetryMetric(name, float(value), _now(), dict(attributes or {}))
        self.metrics.append(item)
        return item

    @contextmanager
    def span(self, name, attributes=None):
        if not name:
            raise EngineTelemetryError("Telemetry span name cannot be empty")
        item = TelemetrySpan(name, _now(), dict(attributes or {}))
        self.spans.append(item)
        try:
            yield item
        finally:
            item.finish()

    def summary(self):
        return {
            "events": len(self.events),
            "metrics": len(self.metrics),
            "spans": len(self.spans),
            "duration_ms": round(sum(x.duration_ms or 0 for x in self.spans), 3),
        }
