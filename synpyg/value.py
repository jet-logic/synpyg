from typing import TYPE_CHECKING, Any, Optional, Self
from .field import StringAttr
from .numeric import to_float, to_float_tuple, to_int
from .numfmt import fmt_num
from .timeutil import fmt_time, tosec


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
    pass


class Real(Const):
    tag = "real"

    def __init__(self, data: float, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = to_float(data, name=type(self).__name__)

    @classmethod
    def check_value(cls, value: Any) -> Self:
        return cls(value)

    def to_xml_element(self, et):
        return et.Element(self.tag, {"value": fmt_num(self.data), **self._xml_attrs()})


class Integer(Const):
    tag = "integer"

    def __init__(self, data: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = to_int(data, name=type(self).__name__)

    @classmethod
    def check_value(cls, value: Any) -> Self:
        return cls(value)

    def to_xml_element(self, et):
        return et.Element(self.tag, {"value": str(self.data)}, **self._xml_attrs())


class Boolean(Const):
    tag = "bool"

    def __init__(self, data: bool = False, **kwargs):
        super().__init__(**kwargs)
        if not isinstance(data, bool):
            raise ValueError(f"Unexpected {type(self).__name__} value: {data!r}")
        self.data = data

    @classmethod
    def check_value(cls, value):
        return cls(value)

    def to_xml_element(self, et):
        return et.Element(
            self.tag, {"value": "true" if self.data else "false"}, **self._xml_attrs()
        )


class String(Const):
    tag = "string"

    def __init__(self, data: str, **kwargs) -> None:
        super().__init__(**kwargs)
        if not isinstance(data, str):
            raise ValueError(f"Unexpected {type(self).__name__} value: {data!r}")
        self.data = data

    @classmethod
    def check_value(cls, value: Any) -> Self:
        return cls(value)

    def to_xml_element(self, et):
        return et.Element(self.tag, {"value": self.data}, **self._xml_attrs())


class Angle(Const):
    tag = "angle"

    def __init__(self, data: float, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = to_float(data, name=type(self).__name__)

    @classmethod
    def check_value(cls, value: Any) -> Self:
        return cls(value)

    def to_xml_element(self, et):
        return et.Element(self.tag, {"value": fmt_num(self.data)}, **self._xml_attrs())


class Time(Const):
    data: float  # seconds
    tag = "time"

    def __init__(self, data, fps: float | None = None, **kwargs):
        """``data`` may be seconds or a time string; frames ("12f") need ``fps``."""
        super().__init__(**kwargs)
        self.data = tosec(data, fps)

    @classmethod
    def check_value(cls, value):
        return cls(value)

    def to_xml_element(self, et):
        return et.Element(self.tag, {"value": fmt_time(self.data)}, **self._xml_attrs())


class _Floats(Const):
    data: tuple[float, ...]
    _length: int | None = None

    def __init__(self, data, **kwargs) -> None:
        if isinstance(data, (str, bytes, bytearray)):
            raise ValueError(f"Unexpected {type(self).__name__} {data!r}")

        try:
            data = tuple(data)
        except TypeError:
            raise ValueError(f"Unexpected {type(self).__name__} {data!r}") from None

        if self._length is not None and len(data) != self._length:
            raise ValueError(
                f"{type(self).__name__} needs exactly {self._length} "
                f"components, got {len(data)}"
            )

        super().__init__(**kwargs)
        self.data = to_float_tuple(data, name=type(self).__name__)

    @classmethod
    def check_value(cls, value: Any):
        return cls(value)


class Color(_Floats):
    tag = "color"
    _length = 4

    def to_xml_element(self, et):
        element = et.Element(self.tag, self._xml_attrs())
        for channel, n in zip(("r", "g", "b", "a"), self.data):
            et.SubElement(element, channel).text = fmt_num(n)
        return element


class Vector(_Floats):
    tag = "vector"
    _length = 2

    def to_xml_element(self, et):
        element = et.Element(self.tag, self._xml_attrs())
        for s, n in zip(("x", "y"), self.data):
            et.SubElement(element, s).text = fmt_num(n)
        return element
