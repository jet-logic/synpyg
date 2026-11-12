from typing import Any, Callable, ClassVar, TYPE_CHECKING, overload
from .valuenode import WithXML
from .value import Value
from .tree.linked3 import Node

if TYPE_CHECKING:
    from .animated import Animated


class Base(Node):
    pass


class Property(WithXML):
    """
    A Synfig param
    """

    typed: type[Value] | None
    name: str
    # None means "not set": such a property is skipped when serializing.
    value: "Value | Animated | None" = None

    def __init__(
        self,
        typed: type[Value] | None = None,
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

        if isinstance(value, Animated) or (
            self.typed is not None and isinstance(value, self.typed)
        ):
            self.value = value
        else:
            self.value = self.typed.check_value(value)  # type: ignore[union-attr]

    def as_animated(self):
        from .animated import Animated

        if isinstance(self.value, Animated):
            return self.value
        v = self.value = self.typed.new_animated()  # type: ignore[union-attr]
        return v

    def to_xml_element(self):
        element = self._etree.Element("param", {"name": self.name})
        if self.value is not None:
            element.append(self.value.to_xml_element())
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

    def __init__(self, typed: type[Value], name: str | None = None):
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


class Attr:
    """
    Declares an XML attribute on a class, e.g. ``time`` on ``<waypoint time="4s">``.

    ``name`` is the XML attribute name (defaults to the Python name), ``strf``
    formats the value. Unlike :class:`Param`, reading an unset attribute raises
    ``AttributeError``, and unset attributes are omitted from the XML.
    """

    def __init__(self, name: str | None = None, strf: Callable[[Any], str] = str):
        self.name = name
        self.strf = strf
        self.attr = ""

    def __set_name__(self, owner: type, attr: str):
        self.attr = attr
        if self.name is None:
            self.name = attr

    def __get__(self, obj, owner=None):
        if obj is None:
            return self
        try:
            return obj.__dict__[self.attr]
        except KeyError:
            raise AttributeError(
                f"{type(obj).__name__!r} object has no attribute {self.attr!r}"
            ) from None

    def __set__(self, obj, value: Any):
        obj.__dict__[self.attr] = value

    def __delete__(self, obj):
        try:
            del obj.__dict__[self.attr]
        except KeyError:
            raise AttributeError(self.attr) from None


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
        cls._params = cls._declared = _collect(cls, Param)

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


class WithAttrs(_Declared):
    """Mixin for classes declaring :class:`Attr` descriptors."""

    _attrs: ClassVar[dict[str, Attr]] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._attrs = cls._declared = _collect(cls, Attr)
