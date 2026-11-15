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
    def new_animated(cls) -> "Animated":
        """Create an :class:`Animated` value node that produces values of ``cls``."""
        from .animated import Animated

        return Animated(cls)

    def as_prop(self, name=""):
        from .base import Property

        p = Property(self.__class__)
        p.set_value(self)
        p.name = name
        return p

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
    """A value whose input checking and text form come from a ``Kind``."""

    kind: ClassVar[Kind]

    def __init__(self, data: Any, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = self.kind.coerce(data, name=type(self).__name__, owner=self)

    @classmethod
    def check_value(cls, value: Any) -> Self:
        return cls(value)

    def to_xml_element(self, et):
        return et.Element(
            self.tag, {"value": self.kind.dump(self.data), **self._xml_attrs()}
        )


class Real(Const):
    tag = "real"
    kind = kinds.Number


class Integer(Const):
    tag = "integer"
    kind = kinds.Integer


class Boolean(Const):
    tag = "bool"
    kind = kinds.StrictBoolean

    def __init__(self, data: bool = False, **kwargs):
        super().__init__(data, **kwargs)


class String(Const):
    tag = "string"
    kind = kinds.String


class Angle(Const):
    tag = "angle"
    kind = kinds.Number


class Time(Const):
    data: float  # seconds
    tag = "time"
    kind = kinds.TimeKind("fps")  # frames ("12f") are resolved with self.fps

    def __init__(self, data, fps: float | None = None, **kwargs):
        """``data`` may be seconds or a time string; frames ("12f") need ``fps``."""
        self.fps = fps  # read by the kind during coercion
        super().__init__(data, **kwargs)


class _Floats(Const):
    data: tuple[float, ...]


class Color(_Floats):
    tag = "color"
    kind = kinds.Vec4

    def to_xml_element(self, et):
        element = et.Element(self.tag, self._xml_attrs())
        for channel, n in zip(("r", "g", "b", "a"), self.data):
            et.SubElement(element, channel).text = fmt_num(n)
        return element


class Vector(_Floats):
    tag = "vector"
    kind = kinds.Vec2

    def to_xml_element(self, et):
        element = et.Element(self.tag, self._xml_attrs())
        for s, n in zip(("x", "y"), self.data):
            et.SubElement(element, s).text = fmt_num(n)
        return element
