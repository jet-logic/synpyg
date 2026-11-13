import math
from typing import Any
from .numfmt import fmt_num


def tosec(value: Any, fps: float | None = None) -> float:
    if isinstance(value, bool):
        raise ValueError(f"Invalid time {value!r}")
    if isinstance(value, (int, float)):
        result = float(value)
    elif isinstance(value, str):
        result = _parse(value.strip(), fps, value)
    else:
        raise ValueError(f"Invalid time {value!r}")
    if not math.isfinite(result):
        raise ValueError(f"Invalid time {value!r}")
    return result


def _parse(s: str, fps: float | None, original: str) -> float:
    if s.endswith("ms"):
        return float(s[:-2]) / 1000
    if s.endswith("s"):
        return float(s[:-1])
    if s.endswith("f"):
        n = float(s[:-1])
        if n == 0:
            return n
        if fps is None:
            raise ValueError(f"Frames require fps: {original!r}")
        if fps <= 0:
            raise ValueError(f"fps must be positive, got {fps!r}")
        return n / fps
    if ":" in s:
        sign = -1.0 if s.startswith("-") else 1.0
        parts = [float(p) for p in s.lstrip("+-").split(":")]
        if len(parts) > 3:
            raise ValueError(f"Invalid time {original!r}")
        return sign * sum(p * 60**i for i, p in enumerate(reversed(parts)))
    return float(s)


def fmt_time(seconds: float) -> str:
    return fmt_num(seconds) + "s"
