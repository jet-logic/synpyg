from dataclasses import dataclass, field
from typing import Any

from .valuenode import ValueNode


@dataclass
class Waypoint:
    time: str
    value: Any

    before: str | None = None
    after: str | None = None

    tension: float | None = None
    temporal_tension: float | None = None
    continuity: float | None = None
    bias: float | None = None


@dataclass
class Animated(ValueNode):
    value_type: str
    waypoints: list[Waypoint] = field(default_factory=list)

    interpolation: str | None = None
    node_id: str | None = None

    def add_waypoint(self, time, value, **kwargs):
        self.waypoints.append(Waypoint(time, value, **kwargs))
        return self
