from typing import Any, Callable, ClassVar, TYPE_CHECKING, overload

from .tree.linked3 import Node

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

    typed: "type[Value] | None"
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

    def as_animated(self):
        from .animated import Animated

        if isinstance(self.value, Animated):
            return self.value
        # TODO: preserve existing constant as a waypoint at 0:
        v = self.value = self.typed.new_animated()  # type: ignore[union-attr]
        return v

    def to_xml_element(self, et):
        element = et.Element("param", {"name": self.name})
        if self.value is not None:
            element.append(self.value.to_xml_element(et))
        return element


# ---------------------------------------------------------------------------
# Declarative descriptors
# ---------------------------------------------------------------------------


class Param:
    """
    Declares a Synfig ``<param>`` on a class::

        class CircleLayer(Layer):
            radius = Param(Real)                  # <param name="radius">
            from_ = Param(Real)                   # <param name="from"> (trailing "_" dropped)
            z_depth = Param(Real, "z-depth")      # explicit name

    Reading ``layer.radius`` returns that instance's :class:`Property`, creating it
    on first access. Writing ``layer.radius = 1.2`` validates the value through
    the param's type. ``del layer.radius`` unsets it. Properties without a value
    are never serialized.
    """

    def __init__(self, typed: "type[Value]", name: str | None = None):
        self.typed = typed
        self.name = name
        self.attr = ""

    def __set_name__(self, owner: type, attr: str):
        self.attr = attr
        if self.name is None:
            self.name = attr.rstrip("_")

    @overload
    def __get__(self, obj: None, owner: type) -> "Param": ...
    @overload
    def __get__(self, obj: object, owner: type) -> Property: ...
    def __get__(self, obj, owner=None):
        if obj is None:
            return self
        prop = obj.__dict__.get(self.attr)
        if prop is None:
            prop = obj.__dict__[self.attr] = Property(self.typed, self.name or "")
        return prop

    def __set__(self, obj, value: Any):
        self.__get__(obj, type(obj)).set_value(value)

    def __delete__(self, obj):
        obj.__dict__.pop(self.attr, None)


def _collect(cls: type, kind: type) -> dict[str, Any]:
    """Descriptors of ``kind`` on ``cls`` and its bases: parents first, in declaration order."""
    found: dict[str, Any] = {}
    for klass in reversed(cls.__mro__):
        for key, val in vars(klass).items():
            if isinstance(val, kind):
                found[key] = val
    return found


class _Declared:
    """Shared ``set_params`` for classes that declare descriptors of one kind."""

    _declared: ClassVar[dict[str, Any]] = {}

    def set_params(self, **kwargs):
        for k, v in kwargs.items():
            if k not in self._declared:
                raise TypeError(
                    f"{self.__class__.__name__} has no declared parameter {k!r}"
                )
            setattr(self, k, v)
        return self


class WithParams(_Declared):
    """Mixin for classes declaring :class:`Param` descriptors."""

    _params: ClassVar[dict[str, Param]] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._params = _collect(cls, Param)
        cls._declared = {**cls._declared, **cls._params}

    def _enum_params(self):
        """
        Yield ``(attr, Property)`` for every property that exists on this instance:
        declared params in declaration order, then ad-hoc ``Property`` attributes.
        Properties without a value are included here; serialization skips them.
        """
        d = self.__dict__
        for k in self._params:
            if (p := d.get(k)) is not None:
                yield k, p
        for k, v in d.items():
            if k not in self._params and isinstance(v, Property):
                yield k, v


from .field import Field  # field.py only imports timeutil, so no cycle


class WithFields(_Declared):
    _fields: ClassVar[dict[str, Field]] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._fields = _collect(cls, Field)
        cls._declared = {**cls._declared, **cls._fields}

    def _enum_fields(self):
        """Yield (attr, Field, value) for every field that is set, in declaration order."""
        d = self.__dict__
        for k, f in self._fields.items():
            if k in d:
                yield k, f, d[k]

    def _xml_attrs(self) -> dict[str, str]:
        d = self.__dict__
        for k, f in self._fields.items():
            if f.ctx.get("required") and k not in d:
                raise ValueError(f"{self.__class__.__name__} has no {k}")
        return {f.name: f.dumpv(v) for _, f, v in self._enum_fields()}
