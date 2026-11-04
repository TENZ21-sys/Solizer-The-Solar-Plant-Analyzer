"""
SoliZer Intelligence Platform - Loss Analysis Engine.

Computes loss breakdowns matching the Example report's Table 8 and
Section 6 methodology.

Loss categories:
  - Grid Loss (Grid Failure + Curtailment combined, as per report)
  - Machine Loss
  - Total Loss = Grid Loss + Machine Loss
  - Loss % = Total Loss / (Total Possible Generation) × 100
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.engines.aggregation import (
    DailyPlantRecord,
    MonthlyPlantRecord,
    LifetimePlantRecord,
)


@dataclass
class LossCategoryResult:
    """A single loss category with its value and metadata."""
    category: str
    loss_kwh: float
    loss_mwh: float
    loss_percentage: float     # % of total possible generation
    description: str
    color: str                 # hex color for charts


@dataclass
class LossAnalysisResult:
    """Complete loss analysis for a period."""
    total_loss_kwh: float
    total_loss_mwh: float
    total_loss_percentage: float
    generation_kwh: float
    generation_mwh: float
    total_possible_generation_kwh: float
    categories: List[LossCategoryResult]


@dataclass
class MonthlyLoss:
    """Loss data for a single month (for stacked bar charts)."""
    year: int
    month: int
    label: str
    grid_failure_mwh: float
    curtailment_mwh: float
    grid_loss_mwh: float
    machine_loss_mwh: float
    total_loss_mwh: float
    loss_percentage: float


# Loss category colors (for charts)
LOSS_COLORS = {
    "Grid Failure": "#ef5350",     # red
    "Curtailment": "#ff9800",      # orange
    "Grid Loss": "#e53935",        # dark red
    "Machine Loss": "#ffa726",     # amber
}


def compute_loss_analysis(
    lifetime: LifetimePlantRecord,
) -> LossAnalysisResult:
    """Compute loss breakdown from lifetime aggregation.

    Matches the Example report's Table 8 structure:
    - Grid Loss = grid_failure + curtailment  (combined as per report)
    - Machine Loss = machine_loss
    """
    total_possible = lifetime.total_possible_generation
    gen = lifetime.total_generation

    # Total loss is the sum of grid loss (which includes curtailment) and machine loss
    total_loss = lifetime.grid_loss + lifetime.machine_loss

    def pct(val: float) -> float:
        return (val / total_possible * 100.0) if total_possible > 0 else 0.0

    categories = []

    # Breakdown categories: Grid Failure (outage), Curtailment, and Machine Loss
    # They do not overlap (since Grid Failure + Curtailment = Grid Loss)
    if lifetime.grid_failure > 0:
        categories.append(
            LossCategoryResult(
                category="Grid Failure",
                loss_kwh=round(lifetime.grid_failure, 1),
                loss_mwh=round(lifetime.grid_failure / 1000.0, 1),
                loss_percentage=round(pct(lifetime.grid_failure), 2),
                description="Energy lost due to grid failures and blackouts.",
                color=LOSS_COLORS["Grid Failure"],
            )
        )

    if lifetime.curtailment > 0:
        categories.append(
            LossCategoryResult(
                category="Curtailment",
                loss_kwh=round(lifetime.curtailment, 1),
                loss_mwh=round(lifetime.curtailment / 1000.0, 1),
                loss_percentage=round(pct(lifetime.curtailment), 2),
                description="Intentional generation limits imposed by grid operator.",
                color=LOSS_COLORS["Curtailment"],
            )
        )

    if lifetime.machine_loss > 0:
        categories.append(
            LossCategoryResult(
                category="Machine Loss",
                loss_kwh=round(lifetime.machine_loss, 1),
                loss_mwh=round(lifetime.machine_loss / 1000.0, 1),
                loss_percentage=round(pct(lifetime.machine_loss), 2),
                description="Energy lost due to equipment failures and maintenance.",
                color=LOSS_COLORS["Machine Loss"],
            )
        )

    return LossAnalysisResult(
        total_loss_kwh=round(total_loss, 1),
        total_loss_mwh=round(total_loss / 1000.0, 1),
        total_loss_percentage=round(pct(total_loss), 2),
        generation_kwh=round(gen, 1),
        generation_mwh=round(gen / 1000.0, 1),
        total_possible_generation_kwh=round(total_possible, 1),
        categories=categories,
    )


def compute_monthly_losses(
    monthly_records: List[MonthlyPlantRecord],
) -> List[MonthlyLoss]:
    """Compute monthly loss breakdowns for charting."""
    _MONTH_NAMES = [
        "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    results: List[MonthlyLoss] = []
    for m in monthly_records:
        total_loss_kwh = m.grid_loss + m.machine_loss
        loss_pct = (
            (total_loss_kwh / m.total_possible_generation * 100.0)
            if m.total_possible_generation > 0
            else 0.0
        )
        results.append(
            MonthlyLoss(
                year=m.year,
                month=m.month,
                label=f"{_MONTH_NAMES[m.month]} {m.year}",
                grid_failure_mwh=round(m.grid_failure / 1000.0, 2),
                curtailment_mwh=round(m.curtailment / 1000.0, 2),
                grid_loss_mwh=round(m.grid_loss / 1000.0, 2),
                machine_loss_mwh=round(m.machine_loss / 1000.0, 2),
                total_loss_mwh=round(total_loss_kwh / 1000.0, 2),
                loss_percentage=round(loss_pct, 2),
            )
        )
    return results


@dataclass
class FinancialLossResult:
    """Monetary revenue loss breakdown based on energy tariff."""
    tariff_per_kwh: float
    currency: str
    total_revenue_lost: float
    grid_loss_revenue: float
    machine_loss_revenue: float
    curtailment_revenue: float
    realized_revenue: float
    potential_total_revenue: float


def compute_financial_losses(
    loss_result: LossAnalysisResult,
    tariff_per_kwh: float = 0.12,
    currency: str = "USD",
) -> FinancialLossResult:
    """Compute financial revenue losses given energy losses and tariff rate."""
    realized_revenue = loss_result.generation_kwh * tariff_per_kwh
    total_revenue_lost = loss_result.total_loss_kwh * tariff_per_kwh
    potential_total = realized_revenue + total_revenue_lost

    grid_rev = 0.0
    machine_rev = 0.0
    curt_rev = 0.0
    for cat in loss_result.categories:
        if "Grid" in cat.category:
            grid_rev += cat.loss_kwh * tariff_per_kwh
        elif "Machine" in cat.category:
            machine_rev += cat.loss_kwh * tariff_per_kwh
        elif "Curtail" in cat.category:
            curt_rev += cat.loss_kwh * tariff_per_kwh

    return FinancialLossResult(
        tariff_per_kwh=tariff_per_kwh,
        currency=currency,
        total_revenue_lost=round(total_revenue_lost, 2),
        grid_loss_revenue=round(grid_rev, 2),
        machine_loss_revenue=round(machine_rev, 2),
        curtailment_revenue=round(curt_rev, 2),
        realized_revenue=round(realized_revenue, 2),
        potential_total_revenue=round(potential_total, 2),
    )

