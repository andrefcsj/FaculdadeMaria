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
    attributes: dict = field(default_factory=dict