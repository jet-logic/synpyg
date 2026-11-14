from typing import Any, ClassVar, TYPE_CHECKING, overload

from .tree.linked3 import Node
from .field import Field, iter_descriptors

if TYPE_CHECKING:
    from .animated import Animated
    from .value import Value


class Base(Node):
    pass


class WithXML:
    def to_xml_element(self, et: Any):
        raise NotImplementedError(f"{self.__class__.__name__}")


class Property(WithXML):
    """
    A Synfig param
    """

    name: str
    # None means "not set": such a property is skipped when serializing.
    value: "Value | Animated | None" = None

    def __init__(
        self,
        typed: "type[Value] | None" = None,
        name: str = "",
        value: "Value | Animated | None" = None,
    ):
        super().__init__()

        if typed is None:
            from .value import String

            typed = String

        self.typed = typed
        self.name = name
        self.value = value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value!r})"

    @property
    def has_value(self) -> bool:
        return self.value is not None

    def set_value(self, value: Any):
        from .animated import Animated

        if isinstance(value, Animated):
            if self.typed is not None and value._type is not self.typed:
                raise ValueError(
                    f"Animated type {value._type.__name__} does not match param type {self.typed.__name__}"
                )
            self.value = value
        # if isinstance(value, Animated) or (
        #     self.typed is not None and isinstance(value, self.typed)
        # ):
        #     self.value = value
        # elif type(value) is self.typed:
        #     self.value = value
        else:
            self.value = self.typed.coerce(value)  # type: ignore[union-attr]

    def as_animated(self, *, preserve: bool = True):
        from .animated import Animated

        if isinstance(self.value, Animated):
            return self.value

        old_value = self.value
        animated = self.typed.new_animated()  # type: ignore[union-attr]

        if preserve and old_value is not None:
            animated.add_waypoint(0, old_value)

        self.value = animated
        return animated

    def to_xml_element(self, et):
        if not self.name:
            raise ValueError("Property has no name")
        element = et.Element("param", {"name": self.name})
        if self.value is not None:
            element.append(self.value.to_xml_element(et))
        return element


# ---------------------------------------------------------------------------
# Declarative descriptors
# ---------------------------------------------------------------------------


class Param(Field):
    def __init__(self, typed: "type[Value]", name: str | None = None, **ctx):
        super().__init__(name=name, **ctx)
        self.typed = typed

    @overload
    def __get__(self, obj: None, owner: type) -> "Param": ...
    @overload
    def __get__(self, obj: object, owner: type) -> Property: ...
    def __get__(self, obj, owner=None):
        if obj is None:
            return self
        prop = obj.__dict__.get(self.attr)
        if prop is None:
            prop = obj.__dict__[self.attr] = Property(self.typed, self.name)
        return prop

    def __set__(self, obj, value: Any):
        self.__get__(obj, type(obj)).set_value(value)

    def __delete__(self, obj):
        obj.__dict__.pop(self.attr, None)

    def dumps(self, obj):
        raise TypeError("a Param serializes as a <param> element, not an attribute")

    dumpv = dumps


class _Declared:
    """Shared ``set_params`` for classes that declare descriptors of one kind."""

    _declared: ClassVar[dict[str, Any]] = {}

    def _assign(self, **kwargs):
        for k, v in kwargs.items():
            if k not in self._declared:
                raise TypeError(
                    f"{self.__class__.__name__} has no declared parameter {k!r}"
                )
            setattr(self, k, v)
        return self


class WithFields(_Declared):
    _fields: ClassVar[dict[str, Field]] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        found = dict(iter_descriptors(cls, order="parent-first"))
        for k, v in found.items():  # kind may not change on override
            old = cls._declared.get(k)
            if old is not None and isinstance(old, Param) != isinstance(v, Param):
                raise TypeError(
                    f"{cls.__name__}.{k} changes between Param and Field; ..."
                )
        cls._declared = found
        cls._params = {k: v for k, v in found.items() if isinstance(v, Param)}
        cls._fields = {k: v for k, v in found.items() if not isinstance(v, Param)}

    def __setattr__(self, key, value):
        # Dynamic (undeclared) params: name them after the attribute they're stored under.
        if isinstance(value, Property) and key not in self._params and not value.name:
            value.name = key.rstrip("_")  # same rule Field.__set_name__ uses
        super().__setattr__(key, value)

    def _enum_fields(self):
        """Yield (attr, Field, value) for every field that is set, in declaration order."""
        d = self.__dict__
        for k, f in self._fields.items():
            if k in d:
                yield k, f, d[k]

    def _enum_params(self):
        d = self.__dict__
        for k in self._params:
            if (p := d.get(k)) is not None:
                yield k, p
        for k, v in d.items():
            if k not in self._params and isinstance(v, Property):
                yield k, v

    def _xml_attrs(self) -> dict[str, str]:
        d = self.__dict__
        for k, f in self._fields.items():
            if f.ctx.get("required") and k not in d:
                raise ValueError(f"{self.__class__.__name__} has no {k}")
        return {f.name: f.dumpv(v) for _, f, v in self._enum_fields()}
