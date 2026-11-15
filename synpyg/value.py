from typing import TYPE_CHECKING, Any, ClassVar, Optional, Self
from . import kinds
from .attrs import StringAttr
from .fields import Kind
from .numfmt import fmt_num


from .base import WithFields, WithXML

if TYPE_CHECKING:
    from .animated import Animated


class Value(WithFields, WithXML):
    tag = ""

    id = StringAttr()
    guid = StringAttr()

    data: Any

    def __init__(
        self,
        id: Optional[str] = None,
        guid: Optional[str] = None,
    ) -> None:
        super().__init__()

        if id is not None:
            self.id = id
        if guid is not None:
            self.guid = guid

    @classmethod
    def check_value(cls, value: Any) -> Self:
        raise NotImplementedError(f"{cls.__name__}")

    @classmethod
    def coerce(cls, value: Any) -> Self:
        """Return ``value`` if it is already a ``cls``, otherwise validate and wrap it."""
        if isinstance(value, cls):
            return value
        return cls.check_value(value)

    @classmethod
    def as_kind(cls) -> "ValueKind":
        """The :class:`ValueKind` that produces values of ``cls``."""
        return ValueKind.of(cls)

    @classmethod
    def new_animated(cls) -> "Animated":
        """Create an :class:`Animated` value node that produces values of ``cls``."""
        return cls.as_kind().new_animated()

    def as_prop(self, name=""):
        from .base import Property

        return Property(self.as_kind(), name, self)

    def _xml_attrs(self):
        return {"guid": guid} if (guid := self.__dict__.get("guid")) else {}

    def __repr__(self) -> str:
        args = [repr(self.__dict__.get("data"))]

        if v := self.__dict__.get("id"):
            args.append(f"id={v!r}")
        if v := self.__dict__.get("guid"):
            args.append(f"guid={v!r}")

        return f"{type(self).__name__}({', '.join(args)})"


class Const(Value):
    """A value whose input checking and text form come from a ``Kind``.

    ``data_kind`` is the kind of the raw ``.data``; see :class:`ValueKind` for
    the kind of the whole ``Value`` object.
    """

    data_kind: ClassVar[Kind]

    def __init__(self, data: Any, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = self.data_kind.coerce(data, name=type(self).__name__, owner=self)

    @classmethod
    def check_value(cls, value: Any) -> Self:
        return cls(value)

    def to_xml_element(self, et):
        return et.Element(
            self.tag, {"value": self.data_kind.dump(self.data), **self._xml_attrs()}
        )


class Real(Const):
    tag = "real"
    data_kind = kinds.Number


class Integer(Const):
    tag = "integer"
    data_kind = kinds.Integer


class Boolean(Const):
    tag = "bool"
    data_kind = kinds.StrictBoolean

    def __init__(self, data: bool = False, **kwargs):
        super().__init__(data, **kwargs)


class String(Const):
    tag = "string"
    data_kind = kinds.String


class Angle(Const):
    tag = "angle"
    data_kind = kinds.Number


class Time(Const):
    data: float  # seconds
    tag = "time"
    data_kind = kinds.TimeKind("fps")  # frames ("12f") are resolved with self.fps

    def __init__(self, data, fps: float | None = None, **kwargs):
        """``data`` may be seconds or a time string; frames ("12f") need ``fps``."""
        self.fps = fps  # read by the kind during coercion
        super().__init__(data, **kwargs)


class _Floats(Const):
    data: tuple[float, ...]


class Color(_Floats):
    tag = "color"
    data_kind = kinds.Vec4

    def to_xml_element(self, et):
        element = et.Element(self.tag, self._xml_attrs())
        for channel, n in zip(("r", "g", "b", "a"), self.data):
            et.SubElement(element, channel).text = fmt_num(n)
        return element


class Vector(_Floats):
    tag = "vector"
    data_kind = kinds.Vec2

    def to_xml_element(self, et):
        element = et.Element(self.tag, self._xml_attrs())
        for s, n in zip(("x", "y"), self.data):
            et.SubElement(element, s).text = fmt_num(n)
        return element


class ValueKind(Kind[Value]):
    """A ``Kind`` for a whole ``Value`` type: ``ValueKind.of(Real)``.

    ``coerce`` turns raw input into a ``Value`` of ``value_type`` (an existing
    instance passes through). ``Param``, ``Property`` and ``Animated`` take
    either a ``ValueKind`` or a bare ``Value`` type, and normalize with
    :meth:`of`. Two kinds are equal when they wrap the same type.
    """

    _cache: ClassVar[dict[type, "ValueKind"]] = {}

    def __init__(self, value_type: type[Value]) -> None:
        if not (isinstance(value_type, type) and issubclass(value_type, Value)):
            raise TypeError(f"expected a Value type, got {value_type!r}")
        self.value_type = value_type

    @classmethod
    def of(cls, spec: "ValueKind | type[Value]") -> "ValueKind":
        """Return ``spec`` if it is a ``ValueKind``, else the shared kind for a ``Value`` type."""
        if isinstance(spec, ValueKind):
            return spec
        if not (isinstance(spec, type) and issubclass(spec, Value)):
            raise TypeError(f"expected a ValueKind or a Value type, got {spec!r}")
        kind = cls._cache.get(spec)
        if kind is None:
            kind = cls._cache[spec] = cls(spec)
        return kind

    @property
    def name(self) -> str:
        return self.value_type.__name__

    @property
    def tag(self) -> str:
        return self.value_type.tag

    def coerce(
        self, value: Any, *, name: str = "value", owner: object | None = None
    ) -> Value:
        return self.value_type.coerce(value)

    def dump(self, value: Value) -> str:
        raise TypeError("a Value serializes as an XML element, not as text")

    def new_animated(self) -> "Animated":
        """Create an :class:`Animated` that produces values of this kind."""
        from .animated import Animated

        return Animated(self)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ValueKind) and self.value_type is other.value_type

    def __hash__(self) -> int:
        return hash((ValueKind, self.value_type))

    def __repr__(self) -> str:
        return f"ValueKind({self.name})"
