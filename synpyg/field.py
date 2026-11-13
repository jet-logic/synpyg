from __future__ import annotations

from typing import Any, overload

from synpyg.numfmt import fmt_num
from synpyg.timeutil import fmt_time, tosec


class Field:
    def __init__(self, **kwargs):
        self.ctx = kwargs
        self.attr: str = ""
        self.name: str = kwargs.get("name") or ""

    def __set_name__(self, owner, attr):
        self.attr = attr
        self.name = self.ctx.get("name") or attr.rstrip("_")

    def __get__(self, obj: object | None, owner: type | None = None):
        if obj is None:
            return self
        try:
            return obj.__dict__[self.attr]
        except KeyError:
            raise AttributeError(
                f"{type(obj).__name__!r} object has no attribute {self.attr!r}"
            ) from None

    def __set__(self, obj: object, value: Any):
        obj.__dict__[self.attr] = value

    def dumps(self, obj: object) -> str:
        raise NotImplementedError(f"{type(self).__name__}.dumps(...)")

    def __delete__(self, obj: object):
        try:
            del obj.__dict__[self.attr]
        except KeyError:
            raise AttributeError(self.attr) from None

    def dumpv(self, obj: object) -> str:
        return str(obj)


class StringAttr(Field):
    @overload
    def __get__(self, obj: None, owner: type | None = None) -> StringAttr: ...
    @overload
    def __get__(self, obj: object, owner: type | None = None) -> str: ...

    def __get__(self, obj, owner=None):
        return super().__get__(obj, owner)

    def __set__(self, obj: object, value: str):
        super().__set__(obj, str(value))

    def dumps(self, obj: object) -> str:
        return str(obj.__dict__[self.attr])

    def dumpv(self, obj: object) -> str:
        return str(obj)


class FloatAttr(Field):
    @overload
    def __get__(self, obj: None, owner: type | None = None) -> FloatAttr: ...
    @overload
    def __get__(self, obj: object, owner: type | None = None) -> float: ...

    def __get__(self, obj, owner=None):
        return super().__get__(obj, owner)

    def __set__(self, obj: object, value: float):
        super().__set__(obj, float(value))

    def dumps(self, obj):
        return self.dumpv(obj.__dict__[self.attr])

    def dumpv(self, obj: Any):
        return fmt_num(obj)


class IntAttr(Field):
    @overload
    def __get__(self, obj: None, owner: type | None = None) -> IntAttr: ...
    @overload
    def __get__(self, obj: object, owner: type | None = None) -> int: ...

    def __get__(self, obj, owner=None):
        return super().__get__(obj, owner)

    def __set__(self, obj: object, value: int):
        super().__set__(obj, int(value))

    def dumps(self, obj: object) -> str:
        return str(obj.__dict__[self.attr])


class BoolAttr(Field):
    @overload
    def __get__(self, obj: None, owner: type | None = None) -> BoolAttr: ...
    @overload
    def __get__(self, obj: object, owner: type | None = None) -> bool: ...

    def __get__(self, obj, owner=None):
        return super().__get__(obj, owner)

    def __set__(self, obj: object, value: bool):
        if isinstance(value, str):
            value = value.strip().lower() in ("1", "true", "yes", "on")
        else:
            value = bool(value)
        super().__set__(obj, value)

    def dumps(self, obj: object) -> str:
        return "true" if obj.__dict__[self.attr] else "false"

    def dumpv(self, obj: object) -> str:
        return "true" if obj else "false"


class TimeAttr(Field):
    @overload
    def __get__(self, obj: None, owner: type | None = None) -> TimeAttr: ...
    @overload
    def __get__(self, obj: object, owner: type | None = None) -> float: ...

    def __get__(self, obj, owner=None):
        return super().__get__(obj, owner)

    def __set__(self, obj: object, value: str | float | int):
        super().__set__(obj, tosec(value))

    def dumps(self, obj):
        return fmt_time(obj.__dict__[self.attr])

    def dumpv(self, obj):
        return fmt_time(obj)  # type: ignore


class StringEnumAttr(Field):

    @overload
    def __get__(self, obj: None, owner: type | None = None) -> StringEnumAttr: ...
    @overload
    def __get__(self, obj: object, owner: type | None = None) -> str: ...

    def __get__(self, obj, owner=None):
        return super().__get__(obj, owner)

    def __set__(self, obj: object, value: str):
        value = str(value)
        choices = self.ctx.get("choices")
        assert isinstance(choices, (list, tuple))
        if value not in choices:
            raise ValueError(f"{self.attr}: expected one of {choices!r}, got {value!r}")
        super().__set__(obj, value)

    def dumps(self, obj: object) -> str:
        return str(obj.__dict__[self.attr])


import math


class QuadFloatAttr(Field):
    @overload
    def __get__(self, obj: None, owner: type | None = None) -> QuadFloatAttr: ...
    @overload
    def __get__(
        self, obj: object, owner: type | None = None
    ) -> tuple[float, float, float, float]: ...

    def __get__(self, obj, owner=None):
        return super().__get__(obj, owner)

    def __set__(self, obj: object, value):
        if isinstance(value, str):  # "x1 y1 x2 y2" (commas allowed)
            value = value.replace(",", " ").split()
        quad = tuple(float(v) for v in value)
        if len(quad) != 4:
            raise ValueError(f"{self.attr}: expected 4 components, got {len(quad)}")
        if not all(math.isfinite(v) for v in quad):
            raise ValueError(f"{self.attr}: components must be finite, got {quad!r}")
        super().__set__(obj, quad)

    def dumps(self, obj):
        return self.dumpv(obj.__dict__[self.attr])

    def dumpv(self, obj: Any):
        return " ".join(fmt_num(v) for v in obj)


# # Keep timep intentionally short/compact -- terseness is a design goal.
# def tosec(value: str | float | int, fps: float | None = None) -> float:
#     """Convert a time representation to seconds.

#     A string ending in ``"f"`` is interpreted as frames and requires ``fps``.
#     """
#     if isinstance(value, bool):
#         raise ValueError(f"Invalid time {value!r}")
#     if isinstance(value, (int, float)):
#         return float(value)
#     if not isinstance(value, str):
#         raise ValueError(f"Invalid time {value!r}")

#     value = value.strip()
#     if value.endswith("ms"):
#         return float(value[:-2]) / 1000
#     if value.endswith("s"):
#         return float(value[:-1])
#     if value.endswith("f"):
#         if fps is None:
#             raise ValueError(f"Frames require fps: {value!r}")
#         return float(value[:-1]) / fps
#     if ":" in value and value.count(":") <= 2:
#         parts = [float(p) for p in value.split(":")]
#         return sum(p * 60**i for i, p in enumerate(reversed(parts)))
#     return float(value)


def _iter_descriptors(obj):
    """Yield (name, Field) once per name; the most-derived definition wins."""
    seen: set[str] = set()
    for klass in type(obj).__mro__:
        for name, value in vars(klass).items():
            if name in seen:
                continue
            seen.add(name)  # mark even non-Field values, so they shadow base Fields
            if isinstance(value, Field):
                yield name, value


def iter_fields(obj):
    """Iterate over Field descriptors declared on obj's class and its bases."""
    yield from _iter_descriptors(obj)


def iter_attrs(obj):
    """Iterate over (name, Field, value) for every Field that is set on obj."""
    for name, desc in _iter_descriptors(obj):
        try:
            value = getattr(obj, name)
        except AttributeError:  # unset
            continue
        yield name, desc, value
