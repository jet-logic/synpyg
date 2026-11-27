"""Strict, round-trip-conscious parsing for the supported parts of Synfig .sif.

The parser builds the model classes used by the writer. Layer types that have
no registered Python implementation are errors; unknown parameters and
attributes on known layers are retained as opaque XML so opening and saving a
file does not silently discard fields the current model does not understand.
"""

from __future__ import annotations

import copy
import math
import os
from typing import Any
from xml.etree import ElementTree as ET

from .animated import Animated
from .base import Param, Property
from .canvas import Canvas, CanvasKeyframe
from .fields import Attr
from .layer import (
    AdvancedOutlineLayer,
    CircleLayer,
    ConicalGradientLayer,
    GroupLayer,
    Layer,
    LinearGradientLayer,
    MotionBlurLayer,
    OutlineLayer,
    RadialGradientLayer,
    RectangleLayer,
    RegionLayer,
    SolidColorLayer,
    SpiralGradientLayer,
)
from .ref import Ref
from .timeutil import tosec
from .kinds import Boolean as BooleanKind
from .value import (
    Angle,
    Boolean,
    Color,
    DashItem,
    DashItemList,
    DynamicList,
    Gradient,
    Integer,
    List,
    Matrix,
    Real,
    Segment,
    Spline,
    SplinePoint,
    String,
    Time,
    Transformation,
    Value,
    ValueNode,
    Vector,
    WidthPoint,
    WidthPointList,
)
from .valuenode import Add, Divide, Multiply, Step, Subtract, Switch


class SIFParseError(ValueError):
    """Base exception for malformed or unsupported SIF XML."""


class MissingLayerTypeError(SIFParseError):
    """A ``<layer>`` element did not declare its ``type`` attribute."""


class UnsupportedLayerError(SIFParseError):
    """The SIF contains a layer type without a registered model class."""


class UnsupportedValueError(SIFParseError):
    """A parameter uses an XML value representation the model cannot parse."""


_LAYER_TYPES: dict[str, type[Layer]] = {
    "solid_color": SolidColorLayer,
    "circle": CircleLayer,
    "rectangle": RectangleLayer,
    "region": RegionLayer,
    "outline": OutlineLayer,
    "linear_gradient": LinearGradientLayer,
    "radial_gradient": RadialGradientLayer,
    "conical_gradient": ConicalGradientLayer,
    "spiral_gradient": SpiralGradientLayer,
    "advanced_outline": AdvancedOutlineLayer,
    "motion_blur": MotionBlurLayer,
    "group": GroupLayer,
    # Synfig has used this spelling in some files/builds. The XML spelling is
    # retained on the instance so saving does not rewrite it to "group".
    "paste_canvas": GroupLayer,
}

_VALUE_TYPES: dict[str, type[Value]] = {
    cls.tag: cls
    for cls in (
        Real,
        Integer,
        Boolean,
        String,
        Angle,
        Time,
        Color,
        Gradient,
        Vector,
        Segment,
        Spline,
        WidthPointList,
        DashItemList,
        Transformation,
        Matrix,
        List,
        DynamicList,
    )
}
_NODE_TYPES = {
    cls.node_type: cls for cls in (Add, Subtract, Multiply, Divide, Switch, Step)
}


def register_layer(layer_type: str, layer_class: type[Layer]) -> None:
    """Register a layer type so :func:`parse_sif` can construct it.

    ``layer_class`` must be a ``Layer`` subclass with the same constructor
    conventions as the built-in layer classes. Registering an existing name
    replaces its class deliberately, allowing applications to extend or
    customize a built-in layer implementation.
    """
    if not isinstance(layer_type, str) or not layer_type:
        raise ValueError("layer_type must be a non-empty string")
    if not isinstance(layer_class, type) or not issubclass(layer_class, Layer):
        raise TypeError("layer_class must be a Layer subclass")
    _LAYER_TYPES[layer_type] = layer_class


def registered_layers() -> dict[str, type[Layer]]:
    """Return a copy of the currently registered XML layer types."""
    return dict(_LAYER_TYPES)


class _RawParameter(Property):
    """Opaque parameter wrapper used to preserve fields unknown to this model."""

    def __init__(self, element: ET.Element):
        super().__init__(String, name=element.get("name", ""))
        self._element = copy.deepcopy(element)

    @property
    def has_value(self) -> bool:
        return True

    def to_xml_element(self, et):
        # Return a detached copy so callers may safely modify the output tree.
        return copy.deepcopy(self._element)


def _path(parent: str, child: str) -> str:
    return f"{parent}/{child}" if parent else child


def _identity(element: ET.Element) -> dict[str, str]:
    return {name: element.attrib[name] for name in ("id", "guid") if name in element.attrib}


def _text(element: ET.Element, *, where: str) -> str:
    value = element.text
    if value is None or not value.strip():
        raise SIFParseError(f"{where}: expected text content")
    return value.strip()


def _child(parent: ET.Element, name: str, *, where: str) -> ET.Element:
    matches = parent.findall(name)
    if len(matches) != 1:
        raise SIFParseError(
            f"{where}: expected exactly one <{name}> child, found {len(matches)}"
        )
    return matches[0]


def _wrapped_value(parent: ET.Element, name: str, *, where: str, fps: float):
    wrapper = _child(parent, name, where=where)
    if len(wrapper) != 1:
        raise SIFParseError(f"{_path(where, name)}: expected one nested value")
    return _parse_any_value(wrapper[0], fps=fps, where=_path(where, name))


def _wrapped_scalar(parent: ET.Element, name: str, *, where: str, fps: float) -> float:
    value = _wrapped_value(parent, name, where=where, fps=fps)
    if not isinstance(value, (Real, Angle, Integer, Time)):
        raise SIFParseError(f"{_path(where, name)}: expected a scalar value")
    return float(value.data)


def _parse_vector(element: ET.Element, *, where: str, **identity) -> Vector:
    values = []
    for axis in ("x", "y"):
        child = _child(element, axis, where=where)
        if len(child):
            if len(child) != 1:
                raise SIFParseError(f"{_path(where, axis)}: expected one nested scalar")
            scalar = child[0].get("value")
            if scalar is None:
                scalar = _text(child[0], where=_path(where, axis))
        else:
            scalar = _text(child, where=_path(where, axis))
        values.append(float(scalar))
    return Vector(values, **identity)


def _parse_color(element: ET.Element, *, where: str, **identity) -> Color:
    rgba = []
    for channel in ("r", "g", "b", "a"):
        child = _child(element, channel, where=where)
        if len(child):
            if len(child) != 1:
                raise SIFParseError(f"{_path(where, channel)}: expected one nested scalar")
            raw = child[0].get("value")
            if raw is None:
                raw = _text(child[0], where=_path(where, channel))
        else:
            raw = _text(child, where=_path(where, channel))
        rgba.append(float(raw))
    return Color(rgba, **identity)


def _parse_spline_point(element: ET.Element, *, where: str) -> SplinePoint:
    if element.tag != "composite" or element.get("type") != "bline_point":
        raise SIFParseError(f"{where}: expected <composite type='bline_point'>")
    point_value = _wrapped_value(element, "point", where=where, fps=24.0)
    if not isinstance(point_value, Vector):
        raise SIFParseError(f"{_path(where, 'point')}: expected vector")

    tangents: dict[str, tuple[float, float]] = {}
    for name in ("t1", "t2"):
        nodes = element.findall(name)
        if not nodes:
            continue
        if len(nodes) != 1:
            raise SIFParseError(f"{where}: duplicate <{name}> tangent")
        tangent = nodes[0]
        radius = _wrapped_scalar(tangent, "radius", where=_path(where, name), fps=24.0)
        theta = _wrapped_scalar(tangent, "theta", where=_path(where, name), fps=24.0)
        radians = math.radians(theta)
        tangents[name] = (radius * math.cos(radians), radius * math.sin(radians))

    tangent1 = tangents.get("t1", (0.0, 0.0))
    tangent2 = tangents.get("t2", tangent1)
    width = _wrapped_scalar(element, "width", where=where, fps=24.0)
    origin = _wrapped_scalar(element, "origin", where=where, fps=24.0)
    split_nodes = element.findall("split")
    split = None
    if split_nodes:
        if len(split_nodes) != 1 or len(split_nodes[0]) != 1:
            raise SIFParseError(f"{where}: malformed <split> value")
        parsed_split = _parse_any_value(split_nodes[0][0], fps=24.0, where=_path(where, "split"))
        if not isinstance(parsed_split, Boolean):
            raise SIFParseError(f"{where}/split: expected bool")
        split = parsed_split.data

    return SplinePoint(
        point_value.data,
        tangent1,
        tangent2,
        width,
        origin,
        split_tangent=split,
    )


def _parse_width_point(element: ET.Element, *, where: str) -> WidthPoint:
    if element.tag != "composite" or element.get("type") != "width_point":
        raise SIFParseError(f"{where}: expected <composite type='width_point'>")

    def scalar(name: str, integer: bool = False):
        value = _wrapped_value(element, name, where=where, fps=24.0)
        expected = Integer if integer else Real
        if not isinstance(value, expected):
            raise SIFParseError(f"{_path(where, name)}: expected {expected.tag}")
        return value.data

    return WidthPoint(
        scalar("position"),
        scalar("width"),
        scalar("side_before", True),
        scalar("side_after", True),
        scalar("lower_bound"),
        scalar("upper_bound"),
        guid=element.get("guid", ""),
    )


def _parse_dash_item(element: ET.Element, *, where: str) -> DashItem:
    if element.tag != "composite" or element.get("type") != "dash_item":
        raise SIFParseError(f"{where}: expected <composite type='dash_item'>")

    def scalar(name: str, integer: bool = False):
        value = _wrapped_value(element, name, where=where, fps=24.0)
        expected = Integer if integer else Real
        if not isinstance(value, expected):
            raise SIFParseError(f"{_path(where, name)}: expected {expected.tag}")
        return value.data

    return DashItem(
        scalar("offset"),
        scalar("length"),
        scalar("side_before", True),
        scalar("side_after", True),
        guid=element.get("guid", ""),
    )


def _parse_value_inner(element: ET.Element, *, fps: float, where: str) -> Value | Animated:
    """Parse a value tag using the value classes currently implemented."""
    tag = element.tag
    identity = _identity(element)

    if tag == "canvas":
        return _parse_canvas_value(element, where=where)
    if tag == "animated":
        return _parse_animated(element, fps=fps, where=where)
    if tag in _NODE_TYPES:
        return _parse_value_node(element, fps=fps, where=where)

    value_type = _VALUE_TYPES.get(tag)
    if value_type is None:
        raise UnsupportedValueError(f"{where}: unsupported value element <{tag}>")

    if value_type is String:
        # SIF stores strings as character data; accept the library's older
        # value-attribute form as well for backwards compatibility.
        data = element.get("value")
        text_content = data is None
        if text_content:
            data = element.text or ""
        value = String(data, **identity)
        if text_content:
            value._xml_text_content = True
        return value

    if value_type in (Real, Integer, Boolean, Angle, Time):
        raw = element.get("value")
        if raw is None:
            raise SIFParseError(f"{where}: <{tag}> is missing its value attribute")
        if value_type is Boolean:
            from .kinds import Boolean as BooleanKind

            data = BooleanKind.coerce(raw, name=where)
        elif value_type is Time:
            return Time(raw, fps=fps, **identity)
        else:
            data = value_type.data_kind.coerce(raw, name=where)
        return value_type(data, **identity)

    if value_type is Vector:
        return _parse_vector(element, where=where, **identity)
    if value_type is Color:
        return _parse_color(element, where=where, **identity)
    if value_type is Gradient:
        stops = []
        for index, child in enumerate(element):
            if child.tag != "color":
                raise SIFParseError(f"{where}: unexpected <{child.tag}> in gradient")
            pos = child.get("pos")
            if pos is None:
                raise SIFParseError(f"{where}/color[{index + 1}]: missing pos attribute")
            stops.append((float(pos), _parse_color(child, where=f"{where}/color[{index + 1}")))
        return Gradient(stops, **identity)

    if value_type is Segment:
        vectors = []
        for name in ("p1", "t1", "p2", "t2"):
            value = _wrapped_value(element, name, where=where, fps=fps)
            if not isinstance(value, Vector):
                raise SIFParseError(f"{where}/{name}: expected vector")
            vectors.append(value)
        return Segment(*(vector.data for vector in vectors), **identity)

    if value_type is Spline:
        points = []
        for index, entry in enumerate(element.findall("entry")):
            if len(entry) != 1:
                raise SIFParseError(f"{where}/entry[{index + 1}]: expected one child")
            points.append(_parse_spline_point(entry[0], where=f"{where}/entry[{index + 1}]"))
        return Spline(points, loop=element.get("loop", "false").lower() == "true", **identity)

    if value_type is WidthPointList:
        points = []
        for index, entry in enumerate(element.findall("entry")):
            if len(entry) != 1:
                raise SIFParseError(f"{where}/entry[{index + 1}]: expected one child")
            points.append(_parse_width_point(entry[0], where=f"{where}/entry[{index + 1}]"))
        return WidthPointList(points, loop=element.get("loop", "false").lower() == "true", **identity)

    if value_type is DashItemList:
        items = []
        for index, entry in enumerate(element.findall("entry")):
            if len(entry) != 1:
                raise SIFParseError(f"{where}/entry[{index + 1}]: expected one child")
            items.append(_parse_dash_item(entry[0], where=f"{where}/entry[{index + 1}]"))
        return DashItemList(items, loop=element.get("loop", "false").lower() == "true", **identity)

    if value_type is Transformation:
        offset = _wrapped_value(element, "offset", where=where, fps=fps)
        angle = _wrapped_value(element, "angle", where=where, fps=fps)
        skew = _wrapped_value(element, "skew_angle", where=where, fps=fps)
        scale = _wrapped_value(element, "scale", where=where, fps=fps)
        if not isinstance(offset, Vector) or not isinstance(scale, Vector):
            raise SIFParseError(f"{where}: transformation offset and scale must be vectors")
        if not isinstance(angle, Angle) or not isinstance(skew, Angle):
            raise SIFParseError(f"{where}: transformation angles must be angle values")
        return Transformation(offset.data, angle.data, skew.data, scale.data, **identity)

    if value_type is Matrix:
        entries = element.findall("e")
        if len(entries) != 9:
            raise SIFParseError(f"{where}: matrix needs 9 <e> entries, found {len(entries)}")
        return Matrix([float(_text(entry, where=f"{where}/e[{i + 1}]")) for i, entry in enumerate(entries)], **identity)

    if value_type is List:
        return List([_parse_any_value(child, fps=fps, where=f"{where}/{child.tag}") for child in element], **identity)

    if value_type is DynamicList:
        items = []
        for index, entry in enumerate(element.findall("entry")):
            if len(entry) != 1:
                raise SIFParseError(f"{where}/entry[{index + 1}]: expected one child")
            items.append(_parse_any_value(entry[0], fps=fps, where=f"{where}/entry[{index + 1}]"))
        return DynamicList(items, type=element.get("type"), **identity)

    raise UnsupportedValueError(f"{where}: no parser for value element <{tag}>")


def _parse_value(element: ET.Element, *, fps: float, where: str) -> Value | Animated:
    value = _parse_value_inner(element, fps=fps, where=where)
    if isinstance(value, Value) and not isinstance(value, (Canvas, ValueNode)):
        known = {
            "real": {"value", "id", "guid"},
            "integer": {"value", "id", "guid"},
            "bool": {"value", "id", "guid"},
            "string": {"value", "id", "guid"},
            "angle": {"value", "id", "guid"},
            "time": {"value", "id", "guid"},
            "vector": {"id", "guid"},
            "color": {"id", "guid"},
            "gradient": {"id", "guid"},
            "segment": {"id", "guid"},
            "bline": {"id", "guid", "type", "loop"},
            "wplist": {"id", "guid", "type", "loop"},
            "dilist": {"id", "guid", "type", "loop"},
            "transformation": {"id", "guid"},
            "matrix": {"id", "guid"},
            "list": {"id", "guid"},
            "dynamic_list": {"id", "guid", "type"},
        }.get(element.tag, {"id", "guid"})
        extra = {key: val for key, val in element.attrib.items() if key not in known}
        if extra:
            value._extra_xml_attrs = extra
    return value


def _parse_any_value(element: ET.Element, *, fps: float, where: str) -> Value | Animated:
    return _parse_value(element, fps=fps, where=where)


def _parse_animated(element: ET.Element, *, fps: float, where: str) -> Animated:
    type_tag = element.get("type")
    if not type_tag:
        raise SIFParseError(f"{where}: <animated> is missing its type attribute")
    value_type = _VALUE_TYPES.get(type_tag)
    if value_type is None:
        raise UnsupportedValueError(f"{where}: unsupported animated value type {type_tag!r}")

    kwargs: dict[str, Any] = _identity(element)
    if "interpolation" in element.attrib:
        kwargs["interpolation"] = element.attrib["interpolation"]
    try:
        animation = Animated(value_type, **kwargs)
    except (TypeError, ValueError) as exc:
        raise SIFParseError(f"{where}: invalid animated value: {exc}") from exc

    animation._extra_xml_attrs = {
        key: value for key, value in element.attrib.items()
        if key not in ("type", "id", "guid", "interpolation")
    }
    for index, waypoint_element in enumerate(element.findall("waypoint")):
        waypoint_where = f"{where}/waypoint[{index + 1}]"
        raw_time = waypoint_element.get("time")
        if raw_time is None:
            raise SIFParseError(f"{waypoint_where}: missing time attribute")
        try:
            at = tosec(raw_time, fps)
        except (TypeError, ValueError) as exc:
            raise SIFParseError(f"{waypoint_where}: invalid time {raw_time!r}: {exc}") from exc

        if "use" in waypoint_element.attrib:
            if len(waypoint_element):
                raise SIFParseError(f"{waypoint_where}: use and child value are mutually exclusive")
            value: Value | Ref = Ref(waypoint_element.attrib["use"])
        else:
            if len(waypoint_element) != 1:
                raise SIFParseError(f"{waypoint_where}: expected exactly one value child")
            child = _parse_any_value(waypoint_element[0], fps=fps, where=f"{waypoint_where}/{waypoint_element[0].tag}")
            if not isinstance(child, (Value, Ref)):
                raise SIFParseError(f"{waypoint_where}: invalid waypoint value")
            value = child

        waypoint_kwargs = {}
        for xml_name, py_name in (
            ("before", "before"),
            ("after", "after"),
            ("tension", "tension"),
            ("temporal-tension", "temporal_tension"),
            ("continuity", "continuity"),
            ("bias", "bias"),
        ):
            if xml_name in waypoint_element.attrib:
                waypoint_kwargs[py_name] = waypoint_element.attrib[xml_name]
        try:
            animation.add_keyframe(at, value, **waypoint_kwargs)
        except (TypeError, ValueError) as exc:
            raise SIFParseError(f"{waypoint_where}: {exc}") from exc
        waypoint = animation.waypoints[-1]
        waypoint._extra_xml_attrs = {
            key: val for key, val in waypoint_element.attrib.items()
            if key not in ("time", "use", "before", "after", "tension", "temporal-tension", "continuity", "bias")
        }

    if len(element.findall("waypoint")) != len(element):
        unknown = next(child for child in element if child.tag != "waypoint")
        raise SIFParseError(f"{where}: unexpected <{unknown.tag}> in animated value")
    return animation


def _parse_value_node(element: ET.Element, *, fps: float, where: str) -> Value:
    node_type = _NODE_TYPES.get(element.tag)
    if node_type is None:
        raise UnsupportedValueError(f"{where}: unsupported value node <{element.tag}>")
    links: dict[str, Any] = {}
    link_names = {
        "add": ("lhs", "rhs"),
        "subtract": ("lhs", "rhs"),
        "multiply": ("lhs", "rhs"),
        "divide": ("lhs", "rhs"),
        "switch": ("condition", "if_true", "if_false"),
        "step": ("time", "before", "after"),
    }[element.tag]
    for name in link_names:
        if name in element.attrib:
            if not element.attrib[name]:
                raise SIFParseError(f"{where}: empty reference for link {name!r}")
            links[name] = Ref(element.attrib[name])
    for child in element:
        if child.tag in links:
            raise SIFParseError(f"{where}: duplicate value-node link {child.tag!r}")
        if "use" in child.attrib:
            if len(child):
                raise SIFParseError(f"{where}/{child.tag}: use and child value are mutually exclusive")
            links[child.tag] = Ref(child.attrib["use"])
        elif len(child) == 1:
            links[child.tag] = _parse_any_value(child[0], fps=fps, where=f"{where}/{child.tag}")
        else:
            raise SIFParseError(f"{where}/{child.tag}: expected a use attribute or one nested value")
    try:
        node = node_type(**links, **_identity(element))
    except (TypeError, ValueError) as exc:
        raise SIFParseError(f"{where}: invalid {element.tag} node: {exc}") from exc
    known = {"id", "guid", *link_names}
    extra = {key: value for key, value in element.attrib.items() if key not in known}
    if extra:
        node._extra_xml_attrs = extra
    return node


def _parse_canvas_value(element: ET.Element, *, where: str) -> Canvas:
    use = element.get("use")
    if use is not None:
        if not use:
            raise SIFParseError(f"{where}: canvas use attribute must not be empty")
        if len(element):
            raise SIFParseError(f"{where}: an external canvas reference cannot contain children")
        canvas = Canvas(use=use, id=element.get("id"), guid=element.get("guid"))
        canvas._extra_xml_attrs = {
            key: value for key, value in element.attrib.items()
            if key not in ("use", "id", "guid")
        }
        return canvas

    canvas = Canvas()
    attr_fields, _ = _field_maps(Canvas)
    ordered_names = ("version", "width", "height", "fps", "id", "guid", "begin-time", "end-time", "view-box")
    explicit = set()
    for xml_name in ordered_names:
        info = attr_fields.get(xml_name)
        if info is None or xml_name not in element.attrib:
            continue
        py_name, field = info
        try:
            setattr(canvas, py_name, field.kind.coerce(
                element.attrib[xml_name], name=f"{where}@{xml_name}", owner=canvas
            ))
        except (TypeError, ValueError) as exc:
            raise SIFParseError(f"{where}@{xml_name}: {exc}") from exc
        explicit.add(xml_name)
    known = set(ordered_names)
    canvas._explicit_xml_attrs = explicit
    canvas._extra_xml_attrs = {
        key: value for key, value in element.attrib.items() if key not in known
    }
    canvas._extra_xml_elements = []
    for index, child in enumerate(element):
        child_where = f"{where}/{child.tag}[{index + 1}]"
        if child.tag == "layer":
            canvas.append_child(_parse_layer(child, fps=canvas.fps, where=child_where))
        elif child.tag == "defs":
            raise SIFParseError(f"{child_where}: defs inside a group canvas are not supported")
        else:
            canvas._extra_xml_elements.append(copy.deepcopy(child))
    return canvas


def _field_maps(cls):
    attrs: dict[str, tuple[str, Attr]] = {}
    params: dict[str, tuple[str, Param]] = {}
    for py_name, field in cls._fields.items():
        xml_name = field.ctx.get("name") or py_name.rstrip("_")
        if isinstance(field, Param):
            params[xml_name] = (py_name, field)
        elif isinstance(field, Attr):
            attrs[xml_name] = (py_name, field)
    return attrs, params


def _parse_layer(element: ET.Element, *, fps: float, where: str) -> Layer:
    if element.tag != "layer":
        raise SIFParseError(f"{where}: expected <layer>, got <{element.tag}>")
    layer_type = element.get("type")
    if not layer_type:
        raise MissingLayerTypeError(f"{where}: <layer> is missing its type attribute")
    layer_class = _LAYER_TYPES.get(layer_type)
    if layer_class is None:
        raise UnsupportedLayerError(
            f"{where}: unsupported layer type {layer_type!r}; "
            "register a Layer subclass with register_layer() to support it"
        )

    attr_fields, param_fields = _field_maps(layer_class)
    constructor_kwargs: dict[str, Any] = {}
    for xml_name, py_name in (
        ("desc", "desc"),
        ("active", "active"),
        ("exclude_from_rendering", "exclude_from_rendering"),
        ("group", "group"),
    ):
        if xml_name in element.attrib:
            raw = element.attrib[xml_name]
            field_info = attr_fields.get(xml_name)
            constructor_kwargs[py_name] = (
                field_info[1].kind.coerce(raw, name=f"{where}@{xml_name}")
                if field_info
                else raw
            )

    try:
        layer = layer_class(**constructor_kwargs)
    except (TypeError, ValueError) as exc:
        raise SIFParseError(f"{where}: could not construct {layer_type!r} layer: {exc}") from exc

    # Preserve the exact XML type spelling and version rather than replacing
    # them with the built-in class defaults.
    layer.layer_type = layer_type
    if "version" in element.attrib:
        layer.version = element.attrib["version"]

    known_attrs = {"type", "version", "desc", "active", "exclude_from_rendering", "group"}
    extra_attrs = {}
    for xml_name, raw in element.attrib.items():
        if xml_name in known_attrs:
            continue
        field_info = attr_fields.get(xml_name)
        if field_info is not None:
            py_name, field = field_info
            try:
                setattr(layer, py_name, field.kind.coerce(raw, name=f"{where}@{xml_name}", owner=layer))
            except (TypeError, ValueError) as exc:
                raise SIFParseError(f"{where}@{xml_name}: {exc}") from exc
        else:
            extra_attrs[xml_name] = raw
    if extra_attrs:
        layer._extra_xml_attrs = extra_attrs

    seen_params: set[str] = set()
    raw_index = 0
    for index, param_element in enumerate(element):
        param_where = f"{where}/param[{index + 1}]"
        if param_element.tag != "param":
            raise SIFParseError(f"{where}: expected <param>, found <{param_element.tag}>")
        name = param_element.get("name")
        if not name:
            raise SIFParseError(f"{param_where}: missing name attribute")
        if name in seen_params:
            raise SIFParseError(f"{param_where}: duplicate parameter {name!r}")
        seen_params.add(name)

        field_info = param_fields.get(name)
        if field_info is None:
            # Unknown params are kept verbatim, including attributes, nested
            # values, and whitespace. This is distinct from an unknown layer:
            # there is no safe class to instantiate for the latter.
            raw_index += 1
            layer.__dict__[f"_raw_xml_param_{raw_index}"] = _RawParameter(param_element)
            continue

        py_name, field = field_info
        prop = getattr(layer, py_name)
        param_extra_attrs = {
            key: value for key, value in param_element.attrib.items()
            if key not in ("name", "use")
        }
        if param_extra_attrs:
            prop._extra_xml_attrs = param_extra_attrs
        use = param_element.get("use")
        if use is not None:
            if len(param_element):
                raise SIFParseError(f"{param_where}: use and child value are mutually exclusive")
            if not use:
                raise SIFParseError(f"{param_where}: use attribute must not be empty")
            prop.set_value(Ref(use))
            continue
        if len(param_element) == 0:
            # Preserve empty declared params (including a guid attribute)
            # rather than silently dropping the original XML element.
            raw_index += 1
            layer.__dict__[f"_raw_xml_param_{raw_index}"] = _RawParameter(param_element)
            continue
        if len(param_element) != 1:
            raise SIFParseError(f"{param_where}: expected exactly one value child")
        value_element = param_element[0]
        try:
            value = _parse_any_value(value_element, fps=fps, where=f"{param_where}/{value_element.tag}")
            prop.set_value(value)
        except (TypeError, ValueError, SIFParseError) as exc:
            raise SIFParseError(f"{param_where}: {exc}") from exc

    return layer


def _parse_canvas_keyframe(
    element: ET.Element, *, fps: float, where: str
) -> CanvasKeyframe:
    raw_time = element.get("time")
    if raw_time is None:
        raise SIFParseError(f"{where}: missing required time attribute")
    try:
        time = tosec(raw_time, fps)
        active = BooleanKind.coerce(element.get("active", "true"), name=f"{where}@active")
    except (TypeError, ValueError) as exc:
        raise SIFParseError(f"{where}: {exc}") from exc
    if len(element):
        raise SIFParseError(f"{where}: keyframe may contain text only")
    return CanvasKeyframe(time, element.text or "", active=active, fps=fps)


def _parse_canvas_root(element: ET.Element) -> Canvas:
    if element.tag != "canvas":
        raise SIFParseError(f"document root must be <canvas>, got <{element.tag}>")
    if "use" in element.attrib:
        raise SIFParseError("document root <canvas> cannot be an external use reference")

    canvas = Canvas()
    attr_fields, _ = _field_maps(Canvas)
    known = set()
    # Set fps before time attributes because TimeAttr resolves frame strings
    # against the owner object's current fps.
    order = ("version", "width", "height", "fps", "id", "guid", "begin-time", "end-time", "view-box")
    for xml_name in order:
        field_info = attr_fields.get(xml_name)
        if field_info is None or xml_name not in element.attrib:
            continue
        py_name, field = field_info
        try:
            setattr(canvas, py_name, field.kind.coerce(element.attrib[xml_name], name=f"canvas@{xml_name}", owner=canvas))
        except (TypeError, ValueError) as exc:
            raise SIFParseError(f"canvas@{xml_name}: {exc}") from exc
        known.add(xml_name)

    missing = [
        (field.ctx.get("name") or py_name.rstrip("_"))
        for py_name, field in Canvas._fields.items()
        if isinstance(field, Attr)
        and (field.ctx.get("name") or py_name.rstrip("_")) == "version"
        and (field.ctx.get("name") or py_name.rstrip("_")) not in element.attrib
    ]
    if missing:
        raise SIFParseError(f"canvas: missing required attribute(s): {', '.join(missing)}")

    canvas._explicit_xml_attrs = known.intersection(element.attrib)
    canvas._extra_xml_attrs = {key: value for key, value in element.attrib.items() if key not in known}
    canvas._extra_xml_elements = []
    seen_defs = False
    for index, child in enumerate(element):
        child_where = f"canvas/{child.tag}[{index + 1}]"
        if child.tag == "defs":
            if seen_defs:
                raise SIFParseError("canvas: more than one <defs> element")
            seen_defs = True
            _parse_defs(canvas, child, fps=canvas.fps, where=child_where)
        elif child.tag == "layer":
            canvas.append_child(_parse_layer(child, fps=canvas.fps, where=child_where))
        elif child.tag == "keyframe":
            canvas.keyframes.append(
                _parse_canvas_keyframe(child, fps=canvas.fps, where=child_where)
            )
        else:
            if child.tag == "meta":
                name = child.get("name")
                if name:
                    canvas.meta[name] = child.get("content", child.text or "")
            canvas._extra_xml_elements.append(copy.deepcopy(child))
    return canvas


def _parse_defs(canvas: Canvas, element: ET.Element, *, fps: float, where: str) -> None:
    for index, child in enumerate(element):
        child_where = f"{where}/{child.tag}[{index + 1}]"
        try:
            if child.tag == "animated":
                node = _parse_animated(child, fps=fps, where=child_where)
            elif child.tag in _NODE_TYPES:
                node = _parse_value_node(child, fps=fps, where=child_where)
            else:
                node = _parse_value(child, fps=fps, where=child_where)
            node_id = getattr(node, "id", None)
            if not node_id:
                raise SIFParseError(f"{child_where}: exported definitions require an id")
            canvas.export(node_id, node)
        except (TypeError, ValueError, SIFParseError) as exc:
            raise SIFParseError(f"{child_where}: {exc}") from exc


def parse_sif(source: Any) -> Canvas:
    """Parse a Synfig ``.sif`` document into a :class:`Canvas`.

    ``source`` may be a path, an open binary/text stream, XML bytes/text, an
    :class:`xml.etree.ElementTree.Element`, or an ``ElementTree``. Unknown
    attributes and unknown parameters on supported layers are preserved as
    opaque XML. Unsupported layer types raise :class:`UnsupportedLayerError`.
    """
    try:
        if isinstance(source, ET.Element):
            root = source
        elif isinstance(source, ET.ElementTree):
            root = source.getroot()
        elif isinstance(source, bytes):
            root = ET.fromstring(source)
        elif isinstance(source, str) and source.lstrip().startswith("<"):
            root = ET.fromstring(source)
        elif hasattr(source, "read"):
            root = ET.parse(source).getroot()
        else:
            root = ET.parse(os.fspath(source)).getroot()
    except (ET.ParseError, OSError, TypeError, ValueError) as exc:
        raise SIFParseError(f"could not read SIF XML: {exc}") from exc
    return _parse_canvas_root(root)


def load_sif(source: Any) -> Canvas:
    """Alias for :func:`parse_sif`, provided as a file-loading convenience."""
    return parse_sif(source)
