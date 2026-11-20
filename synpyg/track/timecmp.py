"""Time comparison and snapping for the track package (stdlib only; shared by ``animated``)."""

import math

# Two times closer than this are the same instant (animation times are small,
# so a fixed absolute tolerance is enough).
TIME_ABS_TOL = 1e-9

# Computed times are rounded to this many decimals, so that repeated float
# addition (ten steps of 0.1s) lands on 1.0 rather than 0.9999999999999999.
# It matches TIME_ABS_TOL: finer differences are already treated as equal.
TIME_DECIMALS = 9


def same_time(a: float, b: float) -> bool:
    return abs(a - b) <= TIME_ABS_TOL


def snap_time(t: float) -> float:
    """Round a computed time to ``TIME_DECIMALS``; non-finite values pass through."""
    return round(t, TIME_DECIMALS) if math.isfinite(t) else t
