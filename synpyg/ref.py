"""References to exported nodes (the ``use`` attribute of the .sif format)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .value import Value, ValueKind

if TYPE_CHECKING:
    from .animated import Animated


class Ref:
    """A reference to an exported value or value node, written as ``use="id"``.

    ``target`` is the exported node itself, or a plain ``use`` string for
    something that is not an object here (another file, a hand-written id).
    The id of an object target is read when it is serialized, so a node can
    be given its ``id`` after the ``Ref`` is created.

    A ``Ref`` is accepted wherever a value is: ``Property.value`` (so layer
    params) and ``Waypoint.value``. The spec forbids a child element beside
    ``use``, so a ``Ref`` serializes as an attribute only.
    """

    target: "Value | Animated | str"

    def __init__(self, target: "Value | Animated | str") -> None:
        from .animated import Animated

        if isinstance(target, Ref):
            raise TypeError("cannot make a Ref to a Ref")
        if isinstance(target, str):
            if not target:
                raise ValueError("Ref target must be a non-empty string")
        elif not isinstance(target, (Value, Animated)):
            raise TypeError(
                f"Ref target must be a Value, an Animated or a str, "
                f"got {type(target).__name__}"
            )
        self.target = target

    @property
    def kind(self) -> ValueKind | None:
        """The kind of the target, or ``None`` for a plain ``use`` string."""
        t = self.target
        if isinstance(t, str):
            return None
        if isinstance(t, Value):
            return t.as_kind()
        return t.kind

    @property
    def use(self) -> str:
        """The text for the ``use`` attribute."""
        t = self.target
        if isinstance(t, str):
            return t
        node_id = getattr(t, "id", None)  # unset field raises AttributeError
        if not node_id:
            raise ValueError(
                f"Ref target {t!r} has no id; export it (give it an id) first"
            )
        return node_id

    def check_kind(self, kind: ValueKind) -> None:
        """Raise ``ValueError`` if the target is known to be of another kind."""
        mine = self.kind
        if mine is not None and mine != kind:
            raise ValueError(f"Ref to {mine.name} does not match {kind.name}")

    def __repr__(self) -> str:
        return f"Ref({self.target!r})"
