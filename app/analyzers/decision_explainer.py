"""Human-readable explanations for product decisions."""

CROSS_SELL_PROTECTION_REASON = (
    "Product generates sufficient cross-sell revenue to justify keeping "
    "it active despite not meeting direct performance requirements."
)


class DecisionExplainer:
    """Format metric-based explanations for product decisions."""

    _INSUFFICIENT_DATA_EXPLANATION = "Cost below pause threshold.\nNeed more data."

    def performance_summary(
        self,
        *,
        roas: float,
        cost: float,
        conversion_value: float,
        conversions: float,
    ) -> str:
        """Explain a performance-based decision (KEEP, SCALE, low-ROAS WATCH)."""
        return "\n".join(
            (
                f"ROAS = {_format_metric(roas)}",
                f"Cost = {_format_metric(cost)}",
                f"Revenue = {_format_metric(conversion_value)}",
                f"Conversions = {_format_metric(conversions)}",
            )
        )

    def spend_without_conversions(
        self,
        *,
        cost: float,
        clicks: int,
        conversions: float,
    ) -> str:
        """Explain a PAUSE decision caused by spend with no conversions."""
        return "\n".join(
            (
                f"Cost = {_format_metric(cost)}",
                f"Clicks = {_format_metric(clicks)}",
                f"Conversions = {_format_metric(conversions)}",
            )
        )

    def cross_sell_protection(
        self,
        *,
        assist_revenue: float,
        cross_sell_roas: float,
        min_cross_sell_roas: float,
    ) -> str:
        """Explain a WATCH decision protected by cross-sell revenue."""
        return "\n".join(
            (
                f"Cross-sell revenue = {_format_metric(assist_revenue)}",
                f"Cross-sell ROAS = {cross_sell_roas:.2f}",
                f"Threshold = {min_cross_sell_roas:.2f}",
                CROSS_SELL_PROTECTION_REASON,
            )
        )

    def insufficient_data(self) -> str:
        """Explain a WATCH decision for products below the spend threshold."""
        return self._INSUFFICIENT_DATA_EXPLANATION


def _format_metric(value: float) -> str:
    """Format a metric as an integer when whole, otherwise with two decimals."""
    numeric_value = float(value)

    if numeric_value.is_integer():
        return str(int(numeric_value))

    return f"{numeric_value:.2f}"
