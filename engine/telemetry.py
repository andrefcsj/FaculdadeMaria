"""In-memory telemetry for the Decision Engine."""

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import perf_counter
from typing import Optional

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
    ended_at: Optional[str] = None
    duration_ms: Optional[float] = None
    _start: float = field(default_factory=perf_counter, repr=False)

    def finish(self):
        if self.ended_at is None:
            self.ended_at = _now()
            self.duration_ms