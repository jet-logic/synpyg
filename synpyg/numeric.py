import math
from typing import Any, Iterable


def to_float(value: Any, *, name: str = "value") -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(f"{name} must be a number, got {value!r}")

    try:
        result = float(value)
    except (ValueError, OverflowError):
        raise ValueError(f"{name} must be a number, got {value!r}") from None

    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite, got {value!r}")

    return result


def to_int(value: Any, *, name: str = "value") -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer, got {value!r}")

    if not isinstance(value, (int, float, str)):
        raise ValueError(f"{name} must be an integer, got {value!r}")

    try:
        number = float(value)
    except (ValueError, OverflowError):
        raise ValueError(f"{name} must be an integer, got {value!r}") from None

    if not math.isfinite(number) or not number.is_integer():
        raise ValueError(f"{name} must be an integer, got {value!r}")

    return int(number)


def to_float_tuple(
    values: Iterable[Any],
    *,
    name: str = "components",
    length: int | None = None,
) -> tuple[float, ...]:
    """Convert an iterable to a tuple of finite floats."""
    result = tuple(
        to_float(value, name=f"{name}[{i}]") for i, value in enumerate(values)
    )

    if length is not None and len(result) != length:
        raise ValueError(f"{name} must contain {length} components, got {len(result)}")

    return result
