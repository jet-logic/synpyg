from typing import Any


from synpyg.fields.attr import Attr
from synpyg.fields.kind import Kind


class StrEnumKind(Kind[str]):
    choices: tuple[str, ...]

    def coerce(
        self, value: Any, *, name: str = "value", owner: object | None = None
    ) -> str:
        if not isinstance(value, str):
            raise ValueError(f"{name} must be a string, got {type(value).__name__}")
        if value not in self.choices:
            raise ValueError(f"{name}: expected one of {self.choices!r}, got {value!r}")
        return value


class InterpolationEnumKind(StrEnumKind):
    choices = ("auto", "clamped", "constant", "ease", "halt", "linear", "manual")


InterpolationKind = InterpolationEnumKind()


class InterpolationAttr(Attr[str]):
    def __init__(self, name: str | None = None, **ctx):
        super().__init__(InterpolationKind, name, **ctx)
