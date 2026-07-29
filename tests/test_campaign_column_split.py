"""Tests for campaign detection from the export's campaign column."""

from pathlib import Path

import pandas as pd

from app.services.multi_campaign_analyzer import MultiCampaignAnalyzer


def _row(campaign: str, sku: str, cost: float = 350.0) -> dict:
    """One product row with a campaign name."""
    return {
        "Кампанія": campaign,
        "Item ID": sku,
        "Impressions": 1000,
        "Clicks": 10,
        "Cost": cost,
        "Conversions": 2.0,
        "Conversion Value": 900.0,
    }


def test_campaign_column_splits_one_file_into_campaigns(tmp_path: Path) -> None:
    """Every distinct campaign value becomes its own campaign."""
    source_path = tmp_path / "zvit.csv"
    pd.DataFrame(
        [
            _row("High Price", "H-1"),
            _row("High Price", "H-2"),
            _row("Лов Прайс", "L-1"),
        ]
    ).to_csv(source_path, index=False)

    report = MultiCampaignAnalyzer().analyze([source_path])

    names = [campaign.metadata.name for campaign in report.campaigns]
    types = [campaign.metadata.campaign_type for campaign in report.campaigns]
    assert names == ["High Price", "Лов Прайс"]
    assert types == ["High priority", "Low priority"]
    assert report.overall_summary.total_products == 3
    assert set(report.products["campaign_name"]) == {"High Price", "Лов Прайс"}


def test_ukrainian_campaign_names_derive_types(tmp_path: Path) -> None:
    """Ukrainian tier words map to the campaign types."""
    source_path = tmp_path / "zvit.csv"
    pd.DataFrame(
        [
            _row("Аверейдж прайс", "A-1"),
            _row("Високий пріоритет", "H-1"),
        ]
    ).to_csv(source_path, index=False)

    report = MultiCampaignAnalyzer().analyze([source_path])

    types = {
        campaign.metadata.name: campaign.metadata.campaign_type for campaign in report.campaigns
    }
    assert types["Аверейдж прайс"] == "Medium priority"
    assert types["Високий пріоритет"] == "High priority"


def test_file_without_campaign_column_stays_one_campaign(tmp_path: Path) -> None:
    """The file-name fallback still applies without a campaign column."""
    source_path = tmp_path / "low_price.csv"
    rows = [_row("X", "L-1")]
    for row in rows:
        row.pop("Кампанія")
    pd.DataFrame(rows).to_csv(source_path, index=False)

    report = MultiCampaignAnalyzer().analyze([source_path])

    assert len(report.campaigns) == 1
    assert report.campaigns[0].metadata.name == "low_price"
    assert report.campaigns[0].metadata.campaign_type == "Low priority"
