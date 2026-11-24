from typing import Any, ClassVar, TYPE_CHECKING, overload
from .tree.linked3 import Node
from .fields import Declarative, Field, iter_descriptors

if TYPE_CHECKING:
    from .animated import Animated
    from .ref import Ref
    from .value import Value, ValueKind


class Base(Node):
    pass


class WithXML:
    def to_xml_element(self, et: Any):
        raise NotImplementedError(f"{self.__class__.__name__}")


class Property(WithXML):
    """
    A Synfig param
    """

    name: str
    # None means "not set": such a property is skipped when serializing.
    value: "Value | Animated | Ref | None" = None

    kind: "ValueKind"

    def __init__(
        self,
        kind: "ValueKind | type[Value] | None" = None,
        name: str = "",
        value: Any = None,
    ):
        super().__init__()
        from .value import String, ValueKind

        self.kind = ValueKind.of(String if kind is None else kind)
        self.name = name
        self.value = None

        if value is not None:
            self.set_value(value)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value!r})"

    @property
    def has_value(self) -> bool:
        return self.value is not None

    def set_value(self, value: Any):
        from .animated import Animated

        if isinstance(value, Animated):
            if value.kind != self.kind:
                raise ValueError(
                    f"Animated type {value.kind.name} does not match "
                    f"param type {self.kind.name}"
                )
            self.value = value
        else:
            self.value = self.kind.coerce(value, name=self.name or "value", owner=self)

    def as_animated(self, *, preserve: bool = True):
        from .animated import Animated

        if isinstance(self.value, Animated):
            return self.value

        old_value = self.value
        animated = self.kind.new_animated()

        if preserve and old_value is not None:
            animated.add_keyframe(0, old_value)

        self.value = animated
        return animated

    def to_xml_element(self, et):
        from .ref import Ref

        if not self.name:
            raise ValueError("Property has no name")
        if isinstance(self.value, Ref):  # `use` and a child element exclude each other
            return et.Element("param", {"name": self.name, "use": self.value.use})
        element = et.Element("param", {"name": self.name})
        if self.value is not None:
            element.append(self.value.to_xml_element(et))
        return element


# ---------------------------------------------------------------------------
# Declarative descriptors
# ---------------------------------------------------------------------------


class Param(Field):
    def __init__(self, typed: "ValueKind | type[Value]", **ctx):
        super().__init__(**ctx)
        from .value import ValueKind

        self.kind = ValueKind.of(typed)

    def __set_name__(self, owner, attr):
        super().__set_name__(owner, attr)
        self.ctx["name"] = self.ctx.get("name") or attr.rstrip("_")

    @property
    def typed(self) -> "type[Value]":
        return self.kind.value_type

    @overload
    def __get__(self, obj: None, owner: type) -> "Param": ...
    @overload
    def __get__(self, obj: object, owner: type) -> Property: ...
    def __get__(self, obj, owner=None):
        if obj is None:
            return self
        prop = obj.__dict__.get(self.py_name)
        if prop is None:
            prop = obj.__dict__[self.py_name] = Property(self.kind, self.ctx["name"])
        return prop

    def __set__(self, obj, value: Any):
        self.__get__(obj, type(obj)).set_value(value)

    def __delete__(self, obj):
        obj.__dict__.pop(self.py_name, None)

    def dumps(self, obj):
        raise TypeError("a Param serializes as a <param> element, not an attribute")

    dump_value = dumps


class WithFields(Declarative):
    _fields: ClassVar[dict[str, Field]] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        found = dict(iter_descriptors(cls, order="parent-first"))
        for k, v in found.items():  # kind may not change on override
            old = cls._fields.get(k)
            if old is not None and isinstance(old, Param) != isinstance(v, Param):
                raise TypeError(
                    f"{cls.__name__}.{k} changes between Param and Field; ..."
                )
        cls._fields = found

    def __setattr__(self, key, value):
        # Dynamic (undeclared) params: name them after the attribute they're stored under.
        if isinstance(value, Property) and key not in self._fields and not value.name:
            value.name = key.rstrip("_")  # same rule Field.__set_name__ uses
        super().__setattr__(key, value)

    def _attr_fields(self):
        """Yield (attr, Field) for declared fields that serialize as XML attributes."""
        for k, f in self._fields.items():
            if not isinstance(f, Param):
                yield k, f

    def _enum_fields(self):
        """Yield (attr, Field, value) for every attribute field that is set, in declaration order."""
        d = self.__dict__
        for k, f in self._attr_fields():
            if k in d:
                yield k, f, d[k]

    def _enum_params(self):
        d = self.__dict__
        for k, f in self._fields.items():
            if isinstance(f, Param) and (p := d.get(k)) is not None:
                yield k, p
        for k, v in d.items():
            if k not in self._fields and isinstance(v, Property):
                yield k, v

    def _xml_attrs(self) -> dict[str, str]:
        d = self.__dict__
        for k, f in self._attr_fields():
            if f.ctx.get("required") and k not in d:
                raise ValueError(f"{self.__class__.__name__} has no {k}")
        return {
            f.ctx.get("name") or k.rstrip("_"): f.dump_value(v)
            for k, f, v in self._enum_fields()
        }
