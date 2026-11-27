from types import MappingProxyType
from typing import Any, Mapping
from .animated import Animated
from .base import WithFields
from .attrs import PositiveFloatAttr, PositiveIntAttr, QuadFloatAttr, StringAttr, TimeAttr
from .kinds import Boolean
from .timeutil import fmt_time, tosec
from .grouping import Grouping
from .ref import Ref
from .value import Value


def _waypoint_slots(where, anim):
    for w in anim.waypoints:
        value = w.__dict__.get("value")
        if value is not None:
            yield f"{where}, waypoint at {w.__dict__.get('time')}s", value


def _value_slots(where, value):
    if value is not None:
        yield where, value
        if isinstance(value, Animated):
            yield from _waypoint_slots(where, value)


def _embedded(container):
    """Yield every value/Ref held by params below ``container``."""
    from .layer import Layer

    for layer in container:
        if not isinstance(layer, Layer):
            continue  # serializing reports it
        for _, prop in layer._enum_params():
            where = f"{layer.layer_type} layer, param {prop.name!r}"
            yield from _value_slots(where, prop.value)
        if isinstance(layer, Grouping):
            yield from _embedded(layer)


def _find_ref_cycle(defs: Mapping[str, Any]) -> list[str] | None:
    """Return the ids along a cycle of ``Ref``s between exported nodes, else ``None``.

    Only an ``Animated`` can hold a ``Ref`` (in a waypoint), so only exported
    animations have outgoing edges. Iterative, so a long chain cannot hit the
    recursion limit.
    """
    ids = {id(node): key for key, node in defs.items()}

    def edges(key):
        node = defs[key]
        if isinstance(node, Animated):
            for _, v in _waypoint_slots("", node):
                if isinstance(v, Ref) and not isinstance(v.target, str):
                    target = ids.get(id(v.target))
                    if target is not None:
                        yield target

    state: dict[str, int] = {}  # 1 = on the current path, 2 = finished
    for start in defs:
        if start in state:
            continue
        state[start] = 1
        path = [start]
        stack = [iter(edges(start))]
        while stack:
            for nxt in stack[-1]:
                seen = state.get(nxt)
                if seen == 1:
                    return path[path.index(nxt) :] + [nxt]
                if seen is None:
                    state[nxt] = 1
                    path.append(nxt)
                    stack.append(iter(edges(nxt)))
                    break
            else:
                state[path.pop()] = 2
                stack.pop()
    return None


class CanvasKeyframe:
    """A named time marker on a top-level Synfig canvas.

    This is distinct from an animation ``Waypoint``: a canvas keyframe marks
    a time in the timeline and carries an optional human-readable description.
    ``time`` is stored in seconds; frame strings are resolved using the
    containing canvas frame rate.
    """

    def __init__(self, time, description: str = "", *, active: bool = True, fps: float = 24.0):
        self.time = tosec(time, fps)
        self.fps = fps
        if not isinstance(description, str):
            raise TypeError("keyframe description must be a string")
        self.description = description
        self.active = Boolean.coerce(active, name="keyframe active")

    def to_xml_element(self, et, *, fps: float | None = None):
        element = et.Element("keyframe", {
            "time": fmt_time(self.time, self.fps if fps is None else fps),
            "active": Boolean.dump(self.active),
        })
        if self.description:
            element.text = self.description
        return element

    def __repr__(self) -> str:
        return (f"CanvasKeyframe(time={self.time!r}, "
                f"description={self.description!r}, active={self.active!r})")


class Canvas(Value, Grouping):
    """A canvas value that can also serve as a top-level SIF document."""

    tag = "canvas"
    animatable = False
    version = StringAttr(required=True)
    width = PositiveIntAttr(required=True)
    height = PositiveIntAttr(required=True)
    fps = PositiveFloatAttr(required=True)
    begin_time = TimeAttr(name="begin-time", fps_attr="fps")
    end_time = TimeAttr(name="end-time", fps_attr="fps")
    view_box = QuadFloatAttr(name="view-box")

    def __init__(
        self,
        version="1.2",
        width=480,
        height=270,
        fps=24.0,
        begin_time=None,
        end_time=None,
        view_box=None,
        *,
        name: str | None = None,
        desc: str | None = None,
        author: str | None = None,
        use: str | None = None,
        id: str | None = None,
        guid: str | None = None,
    ):
        super().__init__(id=id, guid=guid)
        if use is not None and (not isinstance(use, str) or not use):
            raise ValueError("External canvas reference must be a non-empty string")
        self._use = use
        self.version = version
        self.width = width
        self.height = height
        self.fps = fps  # before the times, so "12f" can be resolved
        # optional attributes stay unset (and out of the XML) when None
        self._assign_given(begin_time=begin_time, end_time=end_time, view_box=view_box)
        self.meta: dict[str, Any] = {}
        self._assign_meta(name=name, desc=desc, author=author)
        self.keyframes: list[CanvasKeyframe] = []
        self._defs: dict[str, Value | Animated] = {}

    @classmethod
    def from_xml(cls, source):
        """Parse a Synfig .sif document from a path, stream, or XML payload."""
        from .xmlio import parse_sif

        return parse_sif(source)

    @classmethod
    def from_xml_element(cls, element):
        """Build a Canvas from an ``xml.etree.ElementTree`` canvas element."""
        from .xmlio import parse_sif

        return parse_sif(element)

    @classmethod
    def new_animated(cls):
        raise TypeError("Canvas values cannot be animated")

    @classmethod
    def check_value(cls, value):
        """Coerce a string into an external-canvas value."""
        if isinstance(value, str):
            return cls(use=value)
        raise ValueError("Canvas expects a Canvas instance or a non-empty use string")

    @property
    def use(self) -> str | None:
        """External canvas reference, or None for an inline canvas."""
        return self._use

    def _assign_meta(self, *, name=None, desc=None, author=None) -> None:
        for key, value in (("name", name), ("desc", desc), ("author", author)):
            if value is not None:
                setattr(self, key, value)

    @property
    def name(self) -> str | None:
        """Canvas name, stored as a ``meta`` element."""
        return self.meta.get("name")

    @name.setter
    def name(self, value: str | None) -> None:
        self._set_meta("name", value)

    @property
    def desc(self) -> str | None:
        """Canvas description, stored as a ``meta`` element."""
        return self.meta.get("desc")

    @desc.setter
    def desc(self, value: str | None) -> None:
        self._set_meta("desc", value)

    @property
    def author(self) -> str | None:
        """Canvas author, stored as a ``meta`` element."""
        return self.meta.get("author")

    @author.setter
    def author(self, value: str | None) -> None:
        self._set_meta("author", value)

    def _set_meta(self, key: str, value: str | None) -> None:
        if value is None:
            self.meta.pop(key, None)
        elif not isinstance(value, str):
            raise TypeError(f"canvas {key} must be a string or None")
        else:
            self.meta[key] = value

    def _append_meta_xml(self, element, et) -> None:
        """Append preserved extra elements, synchronizing the metadata map."""
        import copy

        represented = set()
        for extra in self.__dict__.get("_extra_xml_elements", ()):
            child = copy.deepcopy(extra)
            if child.tag == "meta":
                key = child.get("name")
                if key in ("name", "desc", "author") and key not in self.meta:
                    continue
                if key in self.meta:
                    value = str(self.meta[key])
                    if "content" in child.attrib:
                        child.set("content", value)
                        child.text = None
                    else:
                        child.text = value
                    represented.add(key)
            element.append(child)
        for key, value in self.meta.items():
            if key not in represented:
                child = et.Element("meta", {"name": key})
                child.text = str(value)
                element.append(child)

    def add_keyframe(
        self, time, description: str = "", *, active: bool = True
    ) -> CanvasKeyframe:
        """Add a canvas timeline keyframe and return it.

        ``time`` accepts seconds or Synfig time strings such as ``"12f"``;
        frame values are resolved using this canvas's ``fps``.
        """
        if self.use is not None:
            raise ValueError("external canvas references cannot contain keyframes")
        keyframe = CanvasKeyframe(time, description, active=active, fps=self.fps)
        self.keyframes.append(keyframe)
        return keyframe

    def _root_attrs(self) -> dict[str, str]:
        """Return root-canvas attributes, including preserved unknown fields."""
        attrs = WithFields._xml_attrs(self)
        attrs.update(self.__dict__.get("_extra_xml_attrs", {}))
        return attrs

    def to_param_xml_element(self, et: Any):
        """Serialize this Canvas as a group layer's <canvas> value."""
        if self.use is not None:
            if self.first_child() is not None:
                raise ValueError("an external Canvas reference cannot contain layers")
            if self._defs:
                raise ValueError("an external Canvas reference cannot contain defs")
            attrs = {"use": self.use}
            if self.__dict__.get("id"):
                attrs["id"] = self.id
            if self.__dict__.get("guid"):
                attrs["guid"] = self.guid
            attrs.update(self.__dict__.get("_extra_xml_attrs", {}))
            return et.Element("canvas", attrs)

        if self._defs:
            raise ValueError(
                "defs inside a group canvas are not supported; export values "
                "from the root Canvas instead"
            )
        if self.keyframes:
            raise ValueError("keyframes inside a group canvas are not supported")

        from .layer import Layer

        explicit = self.__dict__.get("_explicit_xml_attrs", set())
        root_attrs = self._root_attrs()
        attrs = {key: root_attrs[key] for key in explicit if key in root_attrs}
        attrs.update(self.__dict__.get("_extra_xml_attrs", {}))
        element = et.Element("canvas", attrs)
        for child in self:
            if not isinstance(child, Layer):
                raise TypeError(
                    f"Canvas children must be Layer instances, got {type(child).__name__}"
                )
            element.append(child.to_xml_element(et))
        self._append_meta_xml(element, et)
        return element

    def fill_time_range(self):
        """Fill unset begin/end times from the canvas animation range.

        Explicitly supplied times are preserved. If the canvas contains no
        animated properties, both times remain unchanged (and may stay unset).
        Returns this canvas so the call can be chained.
        """
        time_range = self.time_range()
        if time_range is None:
            return self

        begin, end = time_range
        if "begin_time" not in self.__dict__:
            self.begin_time = begin
        if "end_time" not in self.__dict__:
            self.end_time = end
        return self

    def __repr__(self) -> str:
        mode = (
            f"use={self.use!r}"
            if self.use is not None
            else f"layers={sum(1 for _ in self)}"
        )
        identity = ""
        if self.__dict__.get("id"):
            identity += f", id={self.id!r}"
        if self.__dict__.get("guid"):
            identity += f", guid={self.guid!r}"
        return f"Canvas({mode}{identity})"

    @property
    def defs(self) -> Mapping[str, Value | Animated]:
        """The exported nodes (the ``<defs>`` library) by id, in export order."""
        return MappingProxyType(self._defs)

    def export(self, id: str, node: Value | Animated):
        """Export ``node`` under ``id`` so it can be referred to with ``Ref(node)``.

        Sets ``node.id`` and returns ``node``. Exporting the same node under the
        same id again is a no-op; reusing an id or renaming a node is an error.
        Ids may not contain ``#`` or ``:``, which separate the parts of a
        ``use`` string.
        """
        if not isinstance(id, str) or not id:
            raise ValueError("export id must be a non-empty string")
        if "#" in id or ":" in id:
            raise ValueError(f"export id {id!r} may not contain '#' or ':'")
        if not isinstance(node, (Value, Animated)):
            raise TypeError(
                f"can export a Value or an Animated, got {type(node).__name__}"
            )
        as_ = next((k for k, n in self._defs.items() if n is node), None)
        if as_ is not None:
            if as_ == id:
                return node
            raise ValueError(f"{node!r} is already exported as {as_!r}")
        if id in self._defs:
            raise ValueError(f"id {id!r} is already exported")
        old = getattr(node, "id", None)  # unset field raises AttributeError
        if old and old != id:
            raise ValueError(f"{node!r} already has id {old!r}")
        node.id = id
        self._defs[id] = node
        return node

    def check_defs(self) -> None:
        """Raise ``ValueError`` if the exports and the tree disagree.

        Every ``Ref`` to a node must point at one exported here, and a node
        with an id must be exported and referred to, not embedded in a param.
        Exported nodes may not refer to each other in a cycle.
        """
        slots = []
        for key, node in self._defs.items():
            if getattr(node, "id", None) != key:
                raise ValueError(
                    f"exported node {key!r} now has id {getattr(node, 'id', None)!r}"
                )
            if isinstance(node, Animated):
                slots.extend(_waypoint_slots(f"export {key!r}", node))
        slots.extend(_embedded(self))
        for where, value in slots:
            if isinstance(value, Ref):
                t = value.target
                if not isinstance(t, str) and not any(
                    t is n for n in self._defs.values()
                ):
                    raise ValueError(
                        f"{value!r} in {where} is not exported from this canvas; "
                        f"call Canvas.export()"
                    )
            elif getattr(value, "id", None):
                raise ValueError(
                    f"{value!r} in {where} has id {value.id!r} but is embedded; "
                    f"export it and refer to it with Ref(...)"
                )
        if cycle := _find_ref_cycle(self._defs):
            raise ValueError(f"reference cycle: {' -> '.join(cycle)}")

    def to_xml_element(self, et: Any):
        from .layer import Layer

        if self.use is not None:
            raise ValueError("an external Canvas reference is only valid in a group layer")
        self.check_defs()
        root = et.Element("canvas", self._root_attrs())
        self._append_meta_xml(root, et)
        for keyframe in self.keyframes:
            if not isinstance(keyframe, CanvasKeyframe):
                raise TypeError(
                    "Canvas.keyframes must contain CanvasKeyframe instances, "
                    f"got {type(keyframe).__name__}"
                )
            root.append(keyframe.to_xml_element(et, fps=self.fps))
        if self._defs:
            defs = et.SubElement(root, "defs")
            for node in self._defs.values():
                defs.append(node.to_xml_element(et))
        for child in self:
            if not isinstance(child, Layer):
                raise TypeError(
                    f"Canvas children must be Layer instances, got {type(child).__name__}"
                )
            root.append(child.to_xml_element(et))
        return root

    def save_xml(self, filename):
        from xml.etree import ElementTree as et

        root = self.to_xml_element(et)

        tree = et.ElementTree(root)
        et.indent(tree, space="    ")

        tree.write(filename, encoding="UTF-8", xml_declaration=True)
