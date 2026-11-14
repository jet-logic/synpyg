from __future__ import annotations
from typing import Any, overload
from synpyg.numfmt import fmt_num
from synpyg.timeutil import fmt_time, tosec
from synpyg.numeric import to_float, to_int, to_float_tuple


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
        if not isinstance(value, str):
            raise TypeError(f"{self.attr} must be a string, got {type(value).__name__}")
        super().__set__(obj, value)

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
        super().__set__(
            obj,
            to_float(value, name=self.attr),
        )

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
        super().__set__(
            obj,
            to_int(value, name=self.attr),
        )

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
            normalized = value.strip().lower()

            if normalized in ("1", "true", "yes", "on"):
                value = True
            elif normalized in ("0", "false", "no", "off"):
                value = False
            else:
                raise ValueError(
                    f"{self.attr}: expected a boolean string, got {value!r}"
                )
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
        # ``fps_attr`` names a sibling attribute holding the frame rate, so that
        # frame values such as "12f" can be resolved. It is read at assignment
        # time: the stored value is seconds and is not re-derived if fps changes.
        fps_attr = self.ctx.get("fps_attr")
        fps = getattr(obj, fps_attr, None) if fps_attr else None
        super().__set__(obj, tosec(value, fps))

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
        if isinstance(value, str):
            value = value.replace(",", " ").split()

        quad = to_float_tuple(value, name=self.attr, length=4)
        super().__set__(obj, quad)

    def dumps(self, obj):
        return self.dumpv(obj.__dict__[self.attr])

    def dumpv(self, obj: Any):
        return " ".join(fmt_num(v) for v in obj)


def iter_descriptors(cls: type, *, order: str = "child-first"):
    """
    Yield (name, Field) once per name.

    The most-derived definition wins. Non-Field attributes also
    shadow inherited Fields.
    """
    winners = {}

    # Determine the winning definition for each name.
    for klass in cls.__mro__:
        for name, value in vars(klass).items():
            if name not in winners:
                winners[name] = (klass, value)

    # Choose the order in which winning descriptors are emitted.
    if order == "child-first":
        classes = cls.__mro__
    elif order == "parent-first":
        classes = reversed(cls.__mro__)
    else:
        raise ValueError(f"Unknown descriptor order: {order!r}")

    for klass in classes:
        for name, value in vars(klass).items():
            owner, winning_value = winners[name]

            if owner is klass and isinstance(winning_value, Field):
                yield name, winning_value


def iter_fields(obj):
    yield from iter_descriptors(type(obj), order="child-first")


def iter_attrs(obj):
    for name, desc in iter_fields(obj):
        try:
            value = getattr(obj, name)
        except AttributeError:
            continue
        yield name, desc, value
