"""Concrete value kinds for synpyg (numbers, booleans, times, ...).

The abstract ``Kind`` lives in the vendored, reusable ``synpyg.fields``
package; this module holds the kinds that depend on synpyg's own numeric/time
helpers.
"""

from typing import Any

from .fields import Kind, unwrap
from .numeric import to_float, to_float_tuple, to_int
from .numfmt import fmt_num
from .timeutil import fmt_time, tosec


class StringKind(Kind[str]):
    def coerce(
        self, value: Any, *, name: str = "value", owner: object | None = None
    ) -> str:
        if not isinstance(value, str):
            raise ValueError(f"{name} must be a string, got {type(value).__name__}")
        return value

    def interpolate(self, start: str, end: str, amount: float) -> str:
        # Synfig treats strings as discrete values: hold the old value until
        # the next waypoint is reached.
        return end if amount >= 1.0 else start


class FloatKind(Kind[float]):
    def coerce(
        self, value: Any, *, name: str = "value", owner: object | None = None
    ) -> float:
        return to_float(value, name=name)

    def dump(self, value: float) -> str:
        return fmt_num(value)

    def interpolate(self, start: float, end: float, amount: float) -> float:
        return start + (end - start) * amount


class AngleKind(FloatKind):
    """Interpolate angles along Synfig's shortest angular distance.

    Angle values in SIF are expressed in degrees.
    """

    def interpolate(self, start: float, end: float, amount: float) -> float:
        delta = (end - start + 180.0) % 360.0 - 180.0
        return start + delta * amount


class PositiveFloatKind(FloatKind):
    def coerce(
        self, value: Any, *, name: str = "value", owner: object | None = None
    ) -> float:
        value = super().coerce(value, name=name, owner=owner)
        if value <= 0:
            raise ValueError(f"{name} must be positive, got {value!r}")
        return value


class IntKind(Kind[int]):
    def coerce(
        self, value: Any, *, name: str = "value", owner: object | None = None
    ) -> int:
        return to_int(value, name=name)

    def interpolate(self, start: int, end: int, amount: float) -> int:
        if amount == 0.0:
            return start
        if amount == 1.0:
            return end
        # Synfig's integer Hermite interpolator uses fixed-point premultiply /
        # demultiply with a half-unit rounding offset.
        return int(start + (end - start) * amount + 0.5)


class PositiveIntKind(IntKind):
    def coerce(
        self, value: Any, *, name: str = "value", owner: object | None = None
    ) -> int:
        value = super().coerce(value, name=name, owner=owner)
        if value <= 0:
            raise ValueError(f"{name} must be positive, got {value!r}")
        return value


class BoolKind(Kind[bool]):
    def __init__(self, parse_str: bool = True) -> None:
        self.parse_str = parse_str

    def coerce(
        self, value: Any, *, name: str = "value", owner: object | None = None
    ) -> bool:
        if isinstance(value, str) and self.parse_str:
            normalized = value.strip().lower()
            if normalized in ("1", "true", "yes", "on"):
                return True
            if normalized in ("0", "false", "no", "off"):
                return False
            raise ValueError(f"{name}: expected a boolean string, got {value!r}")
        if not isinstance(value, bool):
            raise ValueError(f"{name}: expected bool, got {type(value).__name__}")
        return value

    def dump(self, value: bool) -> str:
        return "true" if value else "false"

    def interpolate(self, start: bool, end: bool, amount: float) -> bool:
        return end if amount >= 1.0 else start


class TimeKind(Kind[float]):
    """Seconds, parsed from "1s", "500ms", "1:30", "12f", ...

    ``fps_attr`` names a sibling attribute holding the frame rate, so that
    frame values such as "12f" can be resolved. It is read from ``owner`` at
    assignment time: the stored value is seconds and is not re-derived if fps
    changes. Without an ``owner`` (e.g. ``ParamValue.set_value`` called
    directly) frame values cannot be resolved.
    """

    def __init__(self, fps_attr: str | None = None) -> None:
        self.fps_attr = fps_attr

    def coerce(
        self, value: Any, *, name: str = "value", owner: object | None = None
    ) -> float:
        fps = None
        if self.fps_attr and owner is not None:
            fps = unwrap(getattr(owner, self.fps_attr, None))
        return tosec(value, fps)

    def dump(self, value: float) -> str:
        return fmt_time(value)

    def interpolate(self, start: float, end: float, amount: float) -> float:
        return start + (end - start) * amount


class EnumKind(Kind[str]):
    def __init__(self, choices) -> None:
        if isinstance(choices, (str, bytes, bytearray)):
            raise TypeError("choices must be an iterable of strings, not a string")
        choices = tuple(choices)
        if not choices or not all(isinstance(c, str) for c in choices):
            raise ValueError(
                f"choices must be a non-empty sequence of str, got {choices!r}"
            )
        self.choices = choices

    def coerce(
        self, value: Any, *, name: str = "value", owner: object | None = None
    ) -> str:
        if not isinstance(value, str):
            raise ValueError(f"{name} must be a string, got {type(value).__name__}")
        if value not in self.choices:
            raise ValueError(f"{name}: expected one of {self.choices!r}, got {value!r}")
        return value

    def interpolate(self, start: str, end: str, amount: float) -> str:
        return end if amount >= 1.0 else start


class FloatTupleKind(Kind[tuple[float, ...]]):
    def __init__(self, n=2, parse_str: bool = True) -> None:
        super().__init__()
        self._length = n
        self.parse_str = parse_str

    def coerce(
        self, value: Any, *, name: str = "value", owner: object | None = None
    ) -> tuple[float, ...]:
        if isinstance(value, str) and self.parse_str:
            # SVG list syntax: "0 0 10 10", "0,0,10,10" or "0, 0, 10, 10".
            value = value.replace(",", " ").split()
        elif isinstance(value, (str, bytes, bytearray)):
            raise ValueError(f"{name}: unexpected value {value!r}")
        try:
            value = tuple(value)
        except TypeError:
            raise ValueError(f"{name}: unexpected value {value!r}") from None

        if len(value) != self._length:
            raise ValueError(
                f"{name} needs exactly {self._length} " f"components, got {len(value)}"
            )

        return to_float_tuple(value, name=name)

    def dump(self, value: tuple[float, ...]) -> str:
        return " ".join(fmt_num(v) for v in value)

    def interpolate(
        self, start: tuple[float, ...], end: tuple[float, ...], amount: float
    ) -> tuple[float, ...]:
        if len(start) != self._length or len(end) != self._length:
            raise ValueError(f"both values must have {self._length} components")
        return tuple(a + (b - a) * amount for a, b in zip(start, end))


String = StringKind()
Number = FloatKind()
PositiveNumber = PositiveFloatKind()
Integer = IntKind()
PositiveInteger = PositiveIntKind()
Boolean = BoolKind()
QuadFloat = FloatTupleKind(4)

# Strict variants for Synfig values: no string parsing.
StrictBoolean = BoolKind(parse_str=False)
Vec2 = FloatTupleKind(2, parse_str=False)
Vec4 = FloatTupleKind(4, parse_str=False)
