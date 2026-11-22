"""Shorthand attribute descriptors: ``FloatAttr()`` is ``Attr(Number)``, etc."""

from .fields import Attr
from .kinds import (
    Boolean,
    EnumKind,
    Integer,
    Number,
    PositiveInteger,
    PositiveNumber,
    QuadFloat,
    String,
    TimeKind,
)

VALID_INTERPOLATIONS = (
    "auto",
    "clamped",
    "constant",
    "ease",
    "halt",
    "linear",
    "manual",
)

# Shared by every interpolation attribute descriptor.
_INTERPOLATION_KIND = EnumKind(VALID_INTERPOLATIONS)


class StringAttr(Attr[str]):
    def __init__(self, name: str | None = None, **ctx):
        super().__init__(String, name, **ctx)


class FloatAttr(Attr[float]):
    def __init__(self, name: str | None = None, **ctx):
        super().__init__(Number, name, **ctx)


class PositiveFloatAttr(Attr[float]):
    def __init__(self, name: str | None = None, **ctx):
        super().__init__(PositiveNumber, name, **ctx)


class IntAttr(Attr[int]):
    def __init__(self, name: str | None = None, **ctx):
        super().__init__(Integer, name, **ctx)


class PositiveIntAttr(Attr[int]):
    def __init__(self, name: str | None = None, **ctx):
        super().__init__(PositiveInteger, name, **ctx)


class BoolAttr(Attr[bool]):
    def __init__(self, name: str | None = None, **ctx):
        super().__init__(Boolean, name, **ctx)


class TimeAttr(Attr[float]):
    def __init__(self, name: str | None = None, *, fps_attr: str | None = None, **ctx):
        super().__init__(TimeKind(fps_attr), name, **ctx)


class StringEnumAttr(Attr[str]):
    def __init__(self, choices, name: str | None = None, **ctx):
        super().__init__(EnumKind(choices), name, **ctx)


class InterpolationAttr(Attr[str]):
    def __init__(self, name: str | None = None, **ctx):
        super().__init__(_INTERPOLATION_KIND, name, **ctx)


class QuadFloatAttr(Attr[tuple[float, ...]]):
    def __init__(self, name: str | None = None, **ctx):
        super().__init__(QuadFloat, name, **ctx)
