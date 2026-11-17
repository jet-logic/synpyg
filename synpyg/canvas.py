from types import MappingProxyType
from typing import Any, Mapping
from .animated import Animated
from .base import WithFields, WithXML
from .attrs import PositiveFloatAttr, PositiveIntAttr, StringAttr, TimeAttr
from .layer import Grouping, Layer
from .attrs import QuadFloatAttr
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
    """Yield (where, value) for each value or Ref held by a param or waypoint under ``container``."""
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


class Canvas(WithFields, WithXML, Grouping):
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
    ):
        super().__init__()
        self.version = version
        self.width = width
        self.height = height
        self.fps = fps  # before the times, so "12f" can be resolved
        # optional attributes stay unset (and out of the XML) when None
        self._assign_given(begin_time=begin_time, end_time=end_time, view_box=view_box)
        self.meta: dict[str, Any] = {}
        self._defs: dict[str, Value | Animated] = {}

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
                if not isinstance(t, str) and not any(t is n for n in self._defs.values()):
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
        self.check_defs()
        root = et.Element("canvas", self._xml_attrs())
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
