from __future__ import annotations
from typing import Any


class Wrapped:
    """Mixin for objects that hold a plain value, e.g. ``ParamValue``."""

    def unwrap(self) -> Any:
        """Return the plain value this object holds."""
        raise NotImplementedError


def unwrap(value: Any) -> Any:
    """Return the plain value behind a ``Wrapped`` object, else ``value`` itself."""
    return value.unwrap() if isinstance(value, Wrapped) else value


class Field:
    def __init__(self, **kwargs):
        self.ctx = kwargs
        self.py_name: str = ""

    def __set_name__(self, owner, attr):
        if self.py_name and self.py_name != attr:
            raise TypeError(
                f"{type(self).__name__} already bound to {self.py_name!r}; "
                f"create a separate instance for {attr!r}"
            )
        self.py_name = attr

    def __get__(self, obj: object | None, owner: type | None = None):
        if obj is None:
            return self
        try:
            return obj.__dict__[self.py_name]
        except KeyError:
            raise AttributeError(
                f"{type(obj).__name__!r} object has no attribute {self.py_name!r}"
            ) from None

    def __set__(self, obj: object, value: Any):
        obj.__dict__[self.py_name] = value

    def __delete__(self, obj: object):
        try:
            del obj.__dict__[self.py_name]
        except KeyError:
            raise AttributeError(self.py_name) from None

    def dump_value(self, obj: Any) -> str:
        return str(obj)


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
