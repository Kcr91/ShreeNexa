"""Mathematical XIRR (Extended Internal Rate of Return) solver with Excel parity."""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date, datetime


class XIRRError(Exception):
    """Base exception for XIRR calculations."""


class XIRRInvalidCashflowsError(XIRRError):
    """Raised when cash flows are empty or lack both positive and negative values."""


class XIRRConvergenceError(XIRRError):
    """Raised when the numerical solver fails to converge within tolerances."""


def _parse_date(d: date | datetime | str) -> date:
    """Normalize input date representation."""
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        return datetime.fromisoformat(d.replace("Z", "")).date()
    raise ValueError(f"Unsupported date type: {type(d)}")


def calculate_xirr(
    cashflows: Sequence[tuple[date | datetime | str, float]],
    *,
    guess: float = 0.1,
    max_iterations: int = 100,
    tol: float = 1e-7,
) -> float:
    """Calculate Extended Internal Rate of Return (XIRR) matching Excel parity.

    Args:
        cashflows: Sequence of (date, amount) tuples. Cash invested should be negative,
                   returns or terminal value should be positive.
        guess: Initial return estimate (e.g. 0.1 for 10%).
        max_iterations: Maximum Newton-Raphson / bisection iterations.
        tol: Target precision tolerance.

    Returns:
        Annualized internal rate of return as a float (e.g. 0.125 for 12.5%).
    """
    if not cashflows or len(cashflows) < 2:
        raise XIRRInvalidCashflowsError("At least two cashflows are required to compute XIRR.")

    # Parse and sort cashflows chronologically
    parsed = [(_parse_date(d), float(amt)) for d, amt in cashflows]
    parsed.sort(key=lambda x: x[0])

    # Invariant: Must have at least one negative and at least one positive cashflow
    has_positive = any(amt > 0.0 for _, amt in parsed)
    has_negative = any(amt < 0.0 for _, amt in parsed)
    if not has_positive or not has_negative:
        raise XIRRInvalidCashflowsError(
            "Cash flows must contain at least one positive (inflow/value) "
            "and at least one negative (outflow/investment) amount."
        )

    d0 = parsed[0][0]
    # Pre-calculate time fractions in years from initial date
    # Standard 365-day convention matching Microsoft Excel XIRR
    items = [((d - d0).days / 365.0, amt) for d, amt in parsed]

    def npv(rate: float) -> float:
        if rate <= -1.0:
            return float("inf")
        total = 0.0
        for t, amt in items:
            total += amt * math.pow(1.0 + rate, -t)
        return total

    def npv_prime(rate: float) -> float:
        if rate <= -1.0:
            return float("-inf")
        total = 0.0
        for t, amt in items:
            total -= t * amt * math.pow(1.0 + rate, -t - 1.0)
        return total

    # 1. Newton-Raphson iteration
    r = guess
    converged = False

    for _ in range(max_iterations):
        if r <= -0.9999:
            break
        val = npv(r)
        if abs(val) < tol:
            converged = True
            break
        deriv = npv_prime(r)
        if abs(deriv) < 1e-12:
            break
        r_next = r - (val / deriv)
        if abs(r_next - r) < tol:
            r = r_next
            converged = True
            break
        r = r_next

    if converged and r > -0.9999:
        return round(r, 6)

    # 2. Bisection Fallback on bounded brackets
    brackets = [
        (-0.99, -0.5),
        (-0.5, 0.0),
        (0.0, 0.5),
        (0.5, 1.5),
        (1.5, 5.0),
        (5.0, 20.0),
        (20.0, 100.0),
    ]

    for a, b in brackets:
        f_a = npv(a)
        f_b = npv(b)
        if f_a * f_b <= 0.0:
            # Found root bracket
            low, high = a, b
            for _ in range(max_iterations * 2):
                mid = (low + high) / 2.0
                f_mid = npv(mid)
                if abs(f_mid) < tol or (high - low) / 2.0 < tol:
                    return round(mid, 6)
                if f_a * f_mid <= 0.0:
                    high = mid
                else:
                    low = mid
                    f_a = f_mid

    raise XIRRConvergenceError(
        "Numerical solver failed to converge to a valid XIRR root for the given cash flows."
    )
