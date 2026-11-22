from typing import Any, Generic, TypeVar

T = TypeVar("T")


class Kind(Generic[T]):
    """A value type: how to coerce raw input and how to dump it for output.

    One ``Kind`` serves both storage strategies: ``Attr`` stores the coerced
    value directly, ``Param`` keeps it in a ``ParamValue``.
    """

    def coerce(
        self, value: Any, *, name: str = "value", owner: object | None = None
    ) -> T:
        """Convert ``value`` or raise.

        ``name`` labels the field in error messages. ``owner`` is the object
        being assigned to, for kinds that read a sibling attribute.
        """
        raise NotImplementedError()

    def dump(self, value: T) -> str:
        """Serialize an already-coerced value."""
        return str(value)

    def interpolate(self, start: T, end: T, amount: float) -> T:
        """Interpolate between two coerced values, when supported by this Kind."""
        raise TypeError(f"{type(self).__name__} does not support interpolation")

    def add(self, a: T, b: T) -> T:
        raise NotImplementedError()
