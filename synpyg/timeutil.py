import math
import re
from typing import Any
from .numfmt import fmt_num


def tosec(value: Any, fps: float | None = None) -> float:
    if isinstance(value, bool):
        raise ValueError(f"Invalid time {value!r}")
    if isinstance(value, (int, float)):
        try:
            result = float(value)
        except (ValueError, OverflowError):
            raise ValueError(f"Invalid time {value!r}") from None
    elif isinstance(value, str):
        result = _parse(value.strip(), fps, value)
    else:
        raise ValueError(f"Invalid time {value!r}")
    if not math.isfinite(result):
        raise ValueError(f"Invalid time {value!r}")
    return result


def _parse(s: str, fps: float | None, original: str) -> float:
    # Synfig time strings may combine units, e.g. ``1s 6f``.
    if " " in s.strip():
        token_re = re.compile(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))(ms|h|m|s|f)")
        position = 0
        total = 0.0
        tokens = list(token_re.finditer(s))
        if not tokens:
            raise ValueError(f"Invalid time {original!r}")
        for token in tokens:
            if s[position:token.start()].strip():
                raise ValueError(f"Invalid time {original!r}")
            amount = float(token.group(1))
            unit = token.group(2)
            if unit == "ms":
                total += amount / 1000.0
            elif unit == "s":
                total += amount
            elif unit == "m":
                total += amount * 60.0
            elif unit == "h":
                total += amount * 3600.0
            else:
                if fps is None or not math.isfinite(fps) or fps <= 0:
                    if amount == 0 and fps is None:
                        continue
                    raise ValueError("Frames require fps: " + repr(original))
                total += amount / fps
            position = token.end()
        if s[position:].strip():
            raise ValueError(f"Invalid time {original!r}")
        return total
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
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError("fps must be finite and positive")
        return n / fps
    if ":" in s:
        # 1:90 ->150 seconds (Ok, and practical)
        sign = -1.0 if s.startswith("-") else 1.0
        parts = [float(p) for p in s.lstrip("+-").split(":")]
        if len(parts) > 3:
            raise ValueError(f"Invalid time {original!r}")
        return sign * sum(p * 60**i for i, p in enumerate(reversed(parts)))
    return float(s)


def fmt_time(seconds: float, fps: float | None = None) -> str:
    if fps is not None and math.isfinite(fps) and fps > 0:
        frames = round(seconds * fps)
        if math.isclose(seconds * fps, frames, rel_tol=0.0, abs_tol=1e-9):
            return f"{frames}f"
    return fmt_num(seconds) + "s"
