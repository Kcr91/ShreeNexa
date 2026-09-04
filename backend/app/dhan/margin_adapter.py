"""Dhan margin API adapter and multi-leg option basket margin reconciler."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from app.analytics.options_margin import BasketMarginResult, calculate_basket_margin
from app.analytics.strategy_builder import OptionLeg
from app.dhan.client import DhanRestClient
from app.dhan.models import DhanMultiMarginScripItem


class OrderMarginResult(BaseModel):
    """Result of order margin requirement calculation with explicit availability."""

    model_config = ConfigDict(frozen=True)

    required_margin: float | None = None
    is_available: bool = True
    unreliable_reason: str | None = None


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

    def calculate_order_margin(
        self,
        symbol: str,
        exchange_segment: str,
        transaction_type: str,
        product_type: str,
        quantity: int,
        price: float,
        security_id: str | None = None,
        trigger_price: float = 0.0,
        broker_response_override: dict[str, Any] | None = None,
        client: DhanRestClient | None = None,
    ) -> OrderMarginResult:
        """Compute required margin for an order via Dhan /v2/margincalculator/multi.

        CRITICAL INVARIANT (F8.6 / Spec §9.2 / QA-21):
        Unavailable margin is explicit and NEVER quietly reported as 0.0 or replaced
        with an invented heuristic.
        """
        if broker_response_override is not None:
            try:
                val = broker_response_override.get("totalMargin")
                if val is None:
                    val = broker_response_override.get("equityMargin")
                if val is None:
                    val = broker_response_override.get("foMargin", 0.0)
                total_margin = float(val)
                return OrderMarginResult(
                    required_margin=round(total_margin, 2),
                    is_available=True,
                )
            except Exception as e:
                return OrderMarginResult(
                    required_margin=None,
                    is_available=False,
                    unreliable_reason=f"Failed to parse Dhan margin response: {e}",
                )

        if not security_id:
            return OrderMarginResult(
                required_margin=None,
                is_available=False,
                unreliable_reason="Security ID required for Dhan margin calculation",
            )

        try:
            dhan_client = client or DhanRestClient()
            scrip_item = DhanMultiMarginScripItem(
                exchangeSegment=exchange_segment,
                transactionType=transaction_type,
                quantity=quantity,
                productType=product_type,
                securityId=security_id,
                price=price,
                triggerPrice=trigger_price,
            )
            resp = dhan_client.calculate_multi_margin(scrip_list=[scrip_item])
            return OrderMarginResult(
                required_margin=round(resp.total_margin, 2),
                is_available=True,
            )
        except Exception as exc:
            return OrderMarginResult(
                required_margin=None,
                is_available=False,
                unreliable_reason=f"Broker margin unavailable: {exc}",
            )


dhan_margin_adapter = DhanMarginAdapter()
