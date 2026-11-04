"""
SoliZer Intelligence Platform - Degradation Engine.

Computes year-over-year degradation metrics based on monthly PR
trend analysis.  Uses linear regression on monthly PR values to
determine the annual PR decline rate, matching the methodology
described in the Example report (Section 5.1).

Observed PR Trend Rate is calculated via linear regression on
monthly PR values.
"""

from __future__ import annotations
from datetime import date
from dataclasses import dataclass
from typing import List, Optional

from app.engines.kpi_calculator import MonthlyKPI


@dataclass
class DegradationResult:
    """Results of the degradation analysis."""
    annual_degradation_rate: float      # % per year (positive = declining)
    cumulative_degradation: float       # % total decline over the period
    expected_lifetime_years: float      # estimated years until PR drops below threshold
    expected_degradation: float         # expected cumulative degradation % (plant age * degradation rate)
    trend: List[DegradationPoint] = None

    def __post_init__(self):
        if self.trend is None:
            self.trend = []


@dataclass
class DegradationPoint:
    """A data point for degradation trend charting."""
    year: str
    pr: float              # actual average PR for the year
    expected_pr: float     # expected PR based on configured degradation rate


def compute_degradation(
    monthly_kpis: List[MonthlyKPI],
    expected_pr: float,
    configured_annual_degradation_rate: float,
    commission_date: date,
) -> DegradationResult:
    """Compute degradation metrics from monthly KPI data.

    Parameters
    ----------
    monthly_kpis : list
        Monthly KPI records (must have ``pr`` and ``year`` fields).
    expected_pr : float
        The expected/baseline Performance Ratio (%) from plant configuration.
    configured_annual_degradation_rate : float
        The configured annual degradation rate (%) — used for "expected" PR
        projections.
    commission_date : date
        The date the plant was commissioned.

    Returns
    -------
    DegradationResult
    """
    if not monthly_kpis or len(monthly_kpis) < 2:
        return DegradationResult(
            annual_degradation_rate=0.0,
            cumulative_degradation=0.0,
            expected_lifetime_years=0.0,
            expected_degradation=0.0,
        )

    # ── Linear regression on monthly PR values ──────────────────────
    # x = month index (0, 1, 2, …), y = PR(%)
    n = len(monthly_kpis)
    xs = list(range(n))
    ys = [m.pr for m in monthly_kpis]

    x_mean = sum(xs) / n
    y_mean = sum(ys) / n

    ss_xy = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    ss_xx = sum((x - x_mean) ** 2 for x in xs)

    if ss_xx == 0:
        slope = 0.0
    else:
        slope = ss_xy / ss_xx  # PR change per month

    # Annual PR decline = slope × 12
    annual_decline = slope * 12.0  # negative means declining
    annual_degradation_rate = abs(annual_decline)

    # First and last PR for cumulative calculation
    first_pr = ys[0]
    last_pr = ys[-1]
    cumulative_degradation = max(first_pr - last_pr, 0.0)

    # Expected lifetime: how many years until PR drops below a threshold
    # (using 50% PR as end-of-useful-life)
    threshold_pr = 50.0
    if annual_decline < 0 and last_pr > threshold_pr:
        remaining_years = (last_pr - threshold_pr) / annual_degradation_rate
        # Total elapsed years
        total_months = n
        elapsed_years = total_months / 12.0
        expected_lifetime_years = elapsed_years + remaining_years
    elif annual_degradation_rate > 0:
        expected_lifetime_years = max(
            (expected_pr - threshold_pr) / annual_degradation_rate, 0
        )
    else:
        expected_lifetime_years = 25.0  # default for no-degradation

    # ── Build year-level trend points ───────────────────────────────
    # Group monthly KPIs by study year and compute average PR
    from collections import defaultdict
    yearly_prs: dict[str, List[float]] = defaultdict(list)
    for m in monthly_kpis:
        start_year = m.year if m.month >= 5 else m.year - 1
        label = f"{start_year}-{start_year+1}"
        yearly_prs[label].append(m.pr)

    trend: List[DegradationPoint] = []
    sorted_years = sorted(yearly_prs.keys())
    for i, year_label in enumerate(sorted_years):
        actual_avg_pr = sum(yearly_prs[year_label]) / len(yearly_prs[year_label])
        # Expected PR declines by configured rate per year from the baseline
        exp_pr = expected_pr - (configured_annual_degradation_rate * i)
        trend.append(
            DegradationPoint(
                year=year_label,
                pr=round(actual_avg_pr, 2),
                expected_pr=round(exp_pr, 2),
            )
        )

    # Calculate plant age at the end of the study period and expected cumulative degradation
    latest_kpi = max(monthly_kpis, key=lambda m: (m.year, m.month))
    end_date = date(latest_kpi.year, latest_kpi.month, 28)
    age_days = (end_date - commission_date).days
    plant_age = max(age_days / 365.25, 0.0)
    expected_degradation = plant_age * configured_annual_degradation_rate

    return DegradationResult(
        annual_degradation_rate=round(annual_degradation_rate, 2),
        cumulative_degradation=round(cumulative_degradation, 2),
        expected_lifetime_years=round(expected_lifetime_years, 1),
        expected_degradation=round(expected_degradation, 2),
        trend=trend,
    )
