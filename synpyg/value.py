from typing import TYPE_CHECKING, Any, ClassVar, Optional, Self
from collections.abc import Mapping
from . import kinds
from .attrs import StringAttr
from .fields import Kind
from .numfmt import fmt_num


from .base import WithFields, WithXML

if TYPE_CHECKING:
    from .animated import Animated
    from .ref import Ref


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

    def interpolate(self, other: "Value", amount: float) -> Self:
        """Interpolate to ``other``; composite subclasses may override this.

        The default implementation is intentionally unsupported. Scalar and
        fixed-tuple values are interpolated by :class:`ValueKind` using their
        ``data_kind`` instead.
        """
        raise TypeError(f"{type(self).__name__} values cannot be interpolated")

    def add(self, other: "Value") -> Self:
        """Return a new value that is ``self + other`` (used by ``add=True`` waypoints).

        Values are not addable by default; addable subclasses override this.
        The result carries no ``id``/``guid``: it is a new, unexported value.
        """
        raise TypeError(f"{type(self).__name__} values cannot be added")

    def as_prop(self, name=""):
        from .base import Property

        return Property(self.as_kind(), name, self)

    def _xml_attrs(self):
        d = self.__dict__
        return {k: d[k] for k in ("id", "guid") if d.get(k)}

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


class _Summable(Const):
    """A ``Const`` whose ``data`` can be added: numbers add, tuples add componentwise."""

    def add(self, other: Value) -> Self:
        if type(other) is not type(self):
            raise TypeError(
                f"cannot add {type(other).__name__} to {type(self).__name__}"
            )
        a, b = self.data, other.data  # type: ignore[attr-defined]
        if isinstance(a, tuple):
            return type(self)(tuple(x + y for x, y in zip(a, b)))
        return type(self)(a + b)


class Real(_Summable):
    tag = "real"
    data_kind = kinds.Number


class Integer(_Summable):
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


class Angle(_Summable):
    tag = "angle"
    data_kind = kinds.AngleKind()


class Time(_Summable):
    data: float  # seconds
    tag = "time"
    data_kind = kinds.TimeKind("fps")  # frames ("12f") are resolved with self.fps

    def __init__(self, data, fps: float | None = None, **kwargs):
        """``data`` may be seconds or a time string; frames ("12f") need ``fps``."""
        self.fps = fps  # read by the kind during coercion
        super().__init__(data, **kwargs)


class _Floats(_Summable):
    data: tuple[float, ...]


class Color(_Floats):
    tag = "color"
    data_kind = kinds.Vec4

    def to_xml_element(self, et):
        element = et.Element(self.tag, self._xml_attrs())
        for channel, n in zip(("r", "g", "b", "a"), self.data):
            et.SubElement(element, channel).text = fmt_num(n)
        return element


class Gradient(Value):
    """An ordered sequence of (position, color) stops."""

    tag = "gradient"

    def __init__(self, stops=(), **kwargs):
        super().__init__(**kwargs)
        if isinstance(stops, Gradient):
            stops = stops.stops
        elif isinstance(stops, Mapping):
            stops = stops.items()

        parsed = []
        for pos, color in stops:
            pos = kinds.Number.coerce(pos, name="gradient position")
            if not 0.0 <= pos <= 1.0:
                raise ValueError(
                    f"gradient position must be between 0 and 1, got {pos!r}"
                )
            parsed.append((pos, Color.coerce(color)))
        self.data = tuple(sorted(parsed, key=lambda stop: stop[0]))

    @classmethod
    def check_value(cls, value):
        if isinstance(value, cls):
            return value
        if isinstance(value, (Mapping, list, tuple)):
            return cls(value)
        raise ValueError(
            "Gradient expects a mapping or sequence of (position, color) stops"
        )

    @property
    def stops(self):
        return self.data

    def interpolate(self, other: "Gradient", amount: float) -> "Gradient":
        raise TypeError("Gradient interpolation is not implemented yet")

    def to_xml_element(self, et):
        element = et.Element(self.tag, self._xml_attrs())
        for pos, color in self.stops:
            child = color.to_xml_element(et)
            child.set("pos", fmt_num(pos))
            element.append(child)
        return element


class Vector(_Floats):
    tag = "vector"
    data_kind = kinds.Vec2

    def to_xml_element(self, et):
        element = et.Element(self.tag, self._xml_attrs())
        for s, n in zip(("x", "y"), self.data):
            et.SubElement(element, s).text = fmt_num(n)
        return element


class Segment(Value):
    """One cubic Bézier segment: endpoints ``p1``/``p2`` and tangent vectors.

    Tangents are control-handle offsets relative to their respective endpoints.
    """

    tag = "segment"

    def __init__(self, p1=(0, 0), t1=(0, 0), p2=(0, 0), t2=(0, 0), **kwargs):
        super().__init__(**kwargs)
        self.data = tuple(Vector.coerce(v) for v in (p1, t1, p2, t2))

    @classmethod
    def check_value(cls, value):
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            return cls(**value)
        if isinstance(value, (tuple, list)) and len(value) == 4:
            return cls(*value)
        raise ValueError("Segment expects p1, t1, p2, and t2")

    @property
    def p1(self):
        return self.data[0]

    @property
    def t1(self):
        return self.data[1]

    @property
    def p2(self):
        return self.data[2]

    @property
    def t2(self):
        return self.data[3]

    def interpolate(self, other: "Segment", amount: float) -> "Segment":
        """Linearly interpolate all four Bézier vectors independently."""
        other = type(self).coerce(other)
        vectors = (
            Vector(tuple(a + (b - a) * amount for a, b in zip(left.data, right.data)))
            for left, right in zip(self.data, other.data)
        )
        return type(self)(*vectors)

    def to_xml_element(self, et):
        element = et.Element(self.tag, self._xml_attrs())
        for name, vector in zip(("p1", "t1", "p2", "t2"), self.data):
            child = et.SubElement(element, name)
            child.append(vector.to_xml_element(et))
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
    ) -> "Value | Ref":
        from .ref import Ref

        if isinstance(value, Ref):  # a reference stands in for a value
            value.check_kind(self)
            return value
        return self.value_type.coerce(value)

    def dump(self, value: Value) -> str:
        raise TypeError("a Value serializes as an XML element, not as text")

    def add(self, a: "Value | Ref", b: "Value | Ref") -> Value:
        """Return ``a + b`` as a new ``Value`` of this kind.

        Both operands must be concrete values of this kind: a ``Ref`` is only
        a name, so there is nothing to add. Kinds whose values are not
        addable (``Boolean``, ``String``) raise ``TypeError``.
        """
        from .ref import Ref

        for v in (a, b):
            if isinstance(v, Ref):
                raise ValueError("cannot add a Ref: it has no value of its own")
        a = self.value_type.coerce(a)
        b = self.value_type.coerce(b)
        return a.add(b)

    def interpolate(self, start: "Value", end: "Value", amount: float) -> Value:
        """Interpolate the underlying data and wrap it in this Value type."""
        start = self.value_type.coerce(start)
        end = self.value_type.coerce(end)
        if type(start).interpolate is not Value.interpolate:
            return start.interpolate(end, amount)
        data = self.value_type.data_kind.interpolate(start.data, end.data, amount)
        return self.value_type(data)

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


class SplinePoint:
    """One Synfig BLine point (vertex, tangents, width and origin).

    Tangents are vectors relative to the vertex. ``tangent2`` defaults to
    ``tangent1``; set ``split_tangent`` when the two handles differ.
    """

    def __init__(
        self,
        vertex=(0, 0),
        tangent1=(0, 0),
        tangent2=None,
        width=1.0,
        origin=0.5,
        split_tangent=None,
    ):
        self.vertex = Vector(vertex)
        self.tangent1 = Vector(tangent1)
        self.tangent2 = Vector(tangent1 if tangent2 is None else tangent2)
        self.width = Real(width)
        self.origin = Real(origin)
        self.split_tangent = Boolean(
            self.tangent1.data != self.tangent2.data
            if split_tangent is None
            else split_tangent
        )

    @classmethod
    def coerce(cls, value):
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            return cls(**value)
        if isinstance(value, (tuple, list)) and len(value) == 2:
            if all(
                isinstance(component, (int, float)) and not isinstance(component, bool)
                for component in value
            ):
                return cls(vertex=value)
            return cls(vertex=value[0], tangent1=value[1])
        raise ValueError(
            f"expected SplinePoint, mapping, or (vertex, tangent), got {value!r}"
        )

    def to_xml_element(self, et):
        # Synfig's composite representation preserves split handles.
        element = et.Element("composite", {"type": "bline_point"})
        point = et.SubElement(element, "point")
        point.append(self.vertex.to_xml_element(et))
        for name, tangent in (("t1", self.tangent1), ("t2", self.tangent2)):
            if name == "t2" and not self.split_tangent.data:
                continue
            radial = et.SubElement(element, name, {"type": "vector"})
            radius = et.SubElement(radial, "radius")
            radius.append(
                Real(
                    (tangent.data[0] ** 2 + tangent.data[1] ** 2) ** 0.5
                ).to_xml_element(et)
            )
            import math

            theta = et.SubElement(radial, "theta")
            theta.append(
                Angle(
                    math.degrees(math.atan2(tangent.data[1], tangent.data[0]))
                ).to_xml_element(et)
            )
        for name, value in (
            ("width", self.width),
            ("origin", self.origin),
            ("split", self.split_tangent),
        ):
            child = et.SubElement(element, name)
            child.append(value.to_xml_element(et))
        return element


class Spline(Value):
    """A Synfig BLine (ordered spline points plus its closed/loop flag)."""

    tag = "bline"

    def __init__(self, points=(), loop=False, **kwargs):
        super().__init__(**kwargs)
        if isinstance(points, Spline):
            loop, points = points.data
        self.data = (tuple(SplinePoint.coerce(p) for p in points), bool(loop))

    @classmethod
    def check_value(cls, value):
        if isinstance(value, dict):
            return cls(**value)
        return cls(value)

    @property
    def points(self):
        return self.data[0]

    @property
    def loop(self):
        return self.data[1]

    def to_xml_element(self, et):
        attrs = {"type": "bline_point"}
        if self.loop:
            attrs["loop"] = "true"
        element = et.Element("bline", attrs)
        for point in self.points:
            entry = et.SubElement(element, "entry")
            entry.append(point.to_xml_element(et))
        return element


class WidthPoint:
    """One variable-width control point used by Synfig's advanced outline."""

    def __init__(
        self,
        position=0.0,
        width=1.0,
        side_before=0,
        side_after=0,
        lower_bound=0.0,
        upper_bound=1.0,
        guid="",
    ):
        self.position = Real(position)
        self.width = Real(width)
        self.side_before = Integer(side_before)
        self.side_after = Integer(side_after)
        self.lower_bound = Real(lower_bound)
        self.upper_bound = Real(upper_bound)
        self.guid = guid

    @classmethod
    def coerce(cls, value):
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            return cls(**value)
        if isinstance(value, (tuple, list)) and 2 <= len(value) <= 4:
            return cls(*value)
        raise ValueError(
            "WidthPoint expects a mapping or (position, width[, side_before, side_after])"
        )

    def to_xml_element(self, et):
        element = et.Element("composite", {"type": "width_point"})
        if self.guid:
            element.set("guid", self.guid)

        for name, value in (
            ("position", self.position),
            ("width", self.width),
            ("side_before", self.side_before),
            ("side_after", self.side_after),
            ("lower_bound", self.lower_bound),
            ("upper_bound", self.upper_bound),
        ):
            child = et.SubElement(element, name)
            child.append(value.to_xml_element(et))
        return element


class WidthPointList(Value):
    """Synfig ``wplist`` containing variable-width outline control points."""

    tag = "wplist"

    def __init__(self, points=(), loop=False, **kwargs):
        super().__init__(**kwargs)
        if isinstance(points, WidthPointList):
            points, loop = points.data
        self.data = (tuple(WidthPoint.coerce(p) for p in points), bool(loop))

    @classmethod
    def check_value(cls, value):
        if isinstance(value, dict):
            return cls(**value)
        return cls(value)

    @property
    def points(self):
        return self.data[0]

    @property
    def loop(self):
        return self.data[1]

    def to_xml_element(self, et):
        attrs = {"type": "width_point"}
        if self.loop:
            attrs["loop"] = "true"
        element = et.Element(self.tag, attrs)
        for point in self.points:
            entry = et.SubElement(element, "entry")
            entry.append(point.to_xml_element(et))
        return element


class DashItem:
    """One dash/gap segment in an advanced outline's dash pattern."""

    def __init__(self, offset=0.1, length=0.1, side_before=4, side_after=4, guid=""):
        self.offset = Real(offset)
        self.length = Real(length)
        self.side_before = Integer(side_before)
        self.side_after = Integer(side_after)
        self.guid = guid

    @classmethod
    def coerce(cls, value):
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            return cls(**value)
        if isinstance(value, (tuple, list)) and 2 <= len(value) <= 4:
            return cls(*value)
        raise ValueError(
            "DashItem expects a mapping or (offset, length[, side_before, side_after])"
        )

    def to_xml_element(self, et):
        element = et.Element("composite", {"type": "dash_item"})
        if self.guid:
            element.set("guid", self.guid)
        for name, value in (
            ("offset", self.offset),
            ("length", self.length),
            ("side_before", self.side_before),
            ("side_after", self.side_after),
        ):
            child = et.SubElement(element, name)
            child.append(value.to_xml_element(et))
        return element


class DashItemList(Value):
    """Synfig ``dilist`` containing dash/gap items."""

    tag = "dilist"

    def __init__(self, items=(), loop=False, **kwargs):
        super().__init__(**kwargs)
        if isinstance(items, DashItemList):
            items, loop = items.data
        self.data = (tuple(DashItem.coerce(item) for item in items), bool(loop))

    @classmethod
    def check_value(cls, value):
        if isinstance(value, dict):
            return cls(**value)
        return cls(value)

    @property
    def items(self):
        return self.data[0]

    @property
    def loop(self):
        return self.data[1]

    def to_xml_element(self, et):
        attrs = {"type": "dash_item"}
        if self.loop:
            attrs["loop"] = "true"
        element = et.Element(self.tag, attrs)
        for item in self.items:
            entry = et.SubElement(element, "entry")
            entry.append(item.to_xml_element(et))
        return element


class Transformation(Value):
    """Synfig's affine group transformation value."""

    tag = "transformation"

    def __init__(self, offset=(0, 0), angle=0, skew_angle=0, scale=(1, 1), **kwargs):
        super().__init__(**kwargs)
        self.data = (Vector(offset), Angle(angle), Angle(skew_angle), Vector(scale))

    @classmethod
    def check_value(cls, value):
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            return cls(**value)
        if isinstance(value, (tuple, list)) and len(value) == 4:
            return cls(*value)
        raise ValueError("Transformation expects offset, angle, skew_angle, and scale")

    def to_xml_element(self, et):
        element = et.Element("transformation", self._xml_attrs())
        for name, value in zip(("offset", "angle", "skew_angle", "scale"), self.data):
            child = et.SubElement(element, name)
            child.append(value.to_xml_element(et))
        return element
