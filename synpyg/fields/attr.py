from typing import Any, Generic, overload

from .base import Field
from .kind import Kind, T


class Attr(Field, Generic[T]):
    """A field whose coerced value is stored directly on the instance.

    The value type comes from its ``Kind``; ``Param`` is the same idea with a
    different storage strategy (a ``ParamValue``).
    """

    def __init__(self, kind: Kind[T], **ctx):
        super().__init__(**ctx)
        self.kind = kind

    @overload
    def __get__(self, obj: None, owner: type | None = None) -> "Attr[T]": ...
    @overload
    def __get__(self, obj: object, owner: type | None = None) -> T: ...

    def __get__(self, obj, owner=None):
        return super().__get__(obj, owner)

    def __set__(self, obj: object, value: Any):
        super().__set__(obj, self.kind.coerce(value, name=self.py_name, owner=obj))

    def dump_value(self, obj: T) -> str:
        return self.kind.dump(obj)
