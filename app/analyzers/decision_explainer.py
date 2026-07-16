"""Human-readable explanations for product decisions."""


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

    def insufficient_data(self) -> str:
        """Explain a WATCH decision for products below the spend threshold."""
        return self._INSUFFICIENT_DATA_EXPLANATION


def _format_metric(value: float) -> str:
    """Format a metric as an integer when whole, otherwise with two decimals."""
    numeric_value = float(value)

    if numeric_value.is_integer():
        return str(int(numeric_value))

    return f"{numeric_value:.2f}"
