"""Dhan margin API adapter and multi-leg option basket margin reconciler."""

from __future__ import annotations

from typing import Any

from app.analytics.options_margin import BasketMarginResult, calculate_basket_margin
from app.analytics.strategy_builder import OptionLeg


class DhanMarginAdapter:
    """Adapter for Dhan broker order and basket margin evaluation."""

    def __init__(self, is_live_allowed: bool = False) -> None:
        self.is_live_allowed = is_live_allowed

    def calculate_basket_margin(
        self,
        underlying: str,
        spot_price: float,
        legs: list[OptionLeg],
        broker_response_override: dict[str, Any] | None = None,
    ) -> BasketMarginResult:
        """Compute basket margin with Dhan margin calculator reconciliation."""
        if broker_response_override is not None:
            # Reconcile from provided mock/recorded broker response
            try:
                total_margin = float(broker_response_override.get("totalMargin", 0.0))
                span_margin = float(broker_response_override.get("spanMargin", 0.0))
                exposure_margin = float(broker_response_override.get("exposureMargin", 0.0))
                benefit = float(broker_response_override.get("marginBenefit", 0.0))
                gross = total_margin + benefit

                return BasketMarginResult(
                    underlying=underlying.upper(),
                    spot_price=spot_price,
                    gross_margin=round(gross, 2),
                    total_span_margin=round(span_margin, 2),
                    total_exposure_margin=round(exposure_margin, 2),
                    total_premium_margin=0.0,
                    hedging_benefit_margin=round(benefit, 2),
                    net_required_margin=round(total_margin, 2),
                    is_available=True,
                )
            except Exception as e:
                return BasketMarginResult(
                    underlying=underlying.upper(),
                    spot_price=spot_price,
                    gross_margin=0.0,
                    total_span_margin=0.0,
                    total_exposure_margin=0.0,
                    total_premium_margin=0.0,
                    hedging_benefit_margin=0.0,
                    net_required_margin=0.0,
                    is_available=False,
                    unreliable_reason=f"Failed to parse Dhan margin response: {e}",
                )

        # Analytical exchange SPAN / Exposure model
        return calculate_basket_margin(
            underlying=underlying,
            spot_price=spot_price,
            legs=legs,
        )


dhan_margin_adapter = DhanMarginAdapter()
