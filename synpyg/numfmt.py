import math


def fmt_num(x: float) -> str:
    """24, 0.5, -2.25; never exponent notation. Rounded to 9 decimals."""
    if not math.isfinite(x):
        raise ValueError(f"Cannot format non-finite number {x!r}")
    s = f"{x:.9f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s
