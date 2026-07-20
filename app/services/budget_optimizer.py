"""Budget redistribution recommendations across campaigns."""

from app.config import ThresholdConfiguration
from app.models.budget import (
    BudgetAction,
    BudgetOptimizationReport,
    BudgetTransfer,
    CampaignBudgetAssessment,
)
from app.models.campaign import CampaignReport, MultiCampaignReport
from app.models.product_decision import ProductStatus


class BudgetOptimizer:
    """Recommend how to redistribute budget between analyzed campaigns."""

    def __init__(self, configuration: ThresholdConfiguration | None = None) -> None:
        """Initialize the optimizer with the threshold configuration."""
        self._configuration = configuration or ThresholdConfiguration()

    def optimize(self, report: MultiCampaignReport) -> BudgetOptimizationReport:
        """Assess every campaign and propose budget transfers.

        Args:
            report: The combined multi-campaign analysis result.

        Returns:
            A budget optimization report with per-campaign assessments and
            recommended transfers between them.
        """
        assessments = [
            self._assess_campaign(campaign) for campaign in report.campaigns
        ]
        transfers = self._build_transfers(assessments)

        return BudgetOptimizationReport(
            assessments=assessments,
            transfers=transfers,
            total_expected_gain=sum(
                transfer.expected_revenue_increase for transfer in transfers
            ),
        )

    def _assess_campaign(self, campaign: CampaignReport) -> CampaignBudgetAssessment:
        """Score one campaign's budget efficiency and pick its action.

        Marginal efficiency estimates the extra revenue per extra currency
        unit as ROAS multiplied by the growth share — the share of spend
        sitting in proven SCALE products or in products still below the
        campaign's watch threshold (untested headroom). Saturation is the
        complement of the growth share.
        """
        campaign_name = campaign.metadata.name
        decisions = campaign.report.decisions
        spend = sum(decision.cost for decision in decisions)
        revenue = sum(decision.conversion_value for decision in decisions)
        conversions = sum(decision.conversions for decision in decisions)
        roas = revenue / spend if spend else 0.0

        watch_threshold = self._configuration.thresholds_for_campaign(
            campaign_name
        ).watch.max_cost
        growth_spend = sum(
            decision.cost
            for decision in decisions
            if decision.status is ProductStatus.SCALE
            or decision.cost < watch_threshold
        )
        growth_share = growth_spend / spend if spend else 0.0
        marginal_efficiency = roas * growth_share

        return CampaignBudgetAssessment(
            campaign_name=campaign_name,
            current_budget=spend,
            current_spend=spend,
            current_roas=roas,
            marginal_efficiency=marginal_efficiency,
            saturation=1.0 - growth_share,
            conversions=conversions,
            action=self._select_action(marginal_efficiency),
        )

    def _select_action(self, marginal_efficiency: float) -> BudgetAction:
        """Map a marginal efficiency score to a budget action."""
        budget = self._configuration.budget
        if marginal_efficiency >= budget.increase_efficiency:
            return BudgetAction.INCREASE

        if marginal_efficiency <= budget.decrease_efficiency:
            return BudgetAction.DECREASE

        return BudgetAction.KEEP

    def _build_transfers(
        self,
        assessments: list[CampaignBudgetAssessment],
    ) -> list[BudgetTransfer]:
        """Propose one transfer per DECREASE campaign to the best INCREASE one."""
        budget = self._configuration.budget
        destinations = sorted(
            (
                assessment
                for assessment in assessments
                if assessment.action is BudgetAction.INCREASE
            ),
            key=lambda assessment: assessment.marginal_efficiency,
            reverse=True,
        )
        sources = sorted(
            (
                assessment
                for assessment in assessments
                if assessment.action is BudgetAction.DECREASE
            ),
            key=lambda assessment: assessment.marginal_efficiency,
        )
        if not destinations or not sources:
            return []

        best_destination = destinations[0]
        transfers = []
        for source in sources:
            amount = source.current_spend * budget.shift_share
            if amount <= 0:
                continue
            efficiency_gain = (
                best_destination.marginal_efficiency - source.marginal_efficiency
            )
            transfers.append(
                BudgetTransfer(
                    source_campaign=source.campaign_name,
                    destination_campaign=best_destination.campaign_name,
                    amount=amount,
                    expected_revenue_increase=amount * efficiency_gain,
                    confidence=min(
                        1.0,
                        best_destination.conversions / budget.confidence_conversions
                        if budget.confidence_conversions
                        else 1.0,
                    ),
                )
            )

        return transfers
