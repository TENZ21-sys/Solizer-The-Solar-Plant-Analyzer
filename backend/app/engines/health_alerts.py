"""
SoliZer Intelligence Platform - Health, Alerts & Recommendations Engine.

Analyzes plant-level and inverter-level daily/monthly records to:
1. Generate operational alerts (severity: critical, warning, info).
2. Generate actionable recommendations (priority: high, medium, low).
"""

from __future__ import annotations

from datetime import date
from sqlalchemy.orm import Session

from app.db.models import Alert, Recommendation, Plant, DailyRecord
from app.engines.aggregation import (
    get_daily_plant_records,
    aggregate_to_lifetime,
    aggregate_to_monthly,
    get_per_inverter_aggregations,
)
from app.engines.kpi_calculator import (
    calculate_availability,
    compute_lifetime_kpis,
    compute_monthly_kpis,
    compute_inverter_pr,
    calculate_pr,
)
from app.engines.loss_analysis import compute_loss_analysis
from app.engines.degradation import compute_degradation


def generate_alerts_and_recommendations(db: Session, plant_id: int) -> None:
    """Analyze the plant's operational data and populate alerts and recommendations tables.

    Clears any existing active alerts/recommendations for the plant before running.
    """
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        return

    # Clear old alerts and recommendations
    db.query(Alert).filter(Alert.plant_id == plant_id).delete()
    db.query(Recommendation).filter(Recommendation.plant_id == plant_id).delete()
    db.commit()

    # Get aggregated data
    daily_records = get_daily_plant_records(db, plant_id)
    if not daily_records:
        return

    lifetime = aggregate_to_lifetime(daily_records)
    monthly_records = aggregate_to_monthly(daily_records)
    kpis = compute_lifetime_kpis(plant, lifetime)
    monthly_kpis = compute_monthly_kpis(plant, monthly_records)
    loss = compute_loss_analysis(lifetime)
    deg = compute_degradation(monthly_kpis, plant.expected_pr, plant.annual_degradation_rate, plant.commission_date)
    inverter_aggs = get_per_inverter_aggregations(db, plant_id)

    # Use the last record date or today
    analysis_date = daily_records[-1].record_date if daily_records else date.today()

    new_alerts: list[Alert] = []
    new_recs: list[Recommendation] = []

    # ═══════════════════════════════════════════════════════════════════════
    # 1. Performance Ratio (PR) Alerts & Recommendations
    # ═══════════════════════════════════════════════════════════════════════
    pr_diff = plant.expected_pr - kpis.performance_ratio
    if pr_diff >= 10.0:
        new_alerts.append(
            Alert(
                plant_id=plant_id,
                alert_date=analysis_date,
                severity="critical",
                category="Performance Ratio",
                message=(
                    f"Critical performance shortfall: PR is {kpis.performance_ratio}% "
                    f"which is {pr_diff:.1f}% below the expected target of {plant.expected_pr}%."
                ),
                status="active",
            )
        )
        new_recs.append(
            Recommendation(
                plant_id=plant_id,
                generated_date=analysis_date,
                category="Performance Improvement",
                description=(
                    f"Perform a comprehensive string-level diagnostic and check for "
                    f"extreme dust/soiling or module faults. Overall PR shortfall is {pr_diff:.1f}%."
                ),
                priority="high",
                status="pending",
            )
        )
    elif pr_diff >= 4.0:
        new_alerts.append(
            Alert(
                plant_id=plant_id,
                alert_date=analysis_date,
                severity="warning",
                category="Performance Ratio",
                message=(
                    f"Moderate performance shortfall: PR is {kpis.performance_ratio}% "
                    f"({pr_diff:.1f}% below target of {plant.expected_pr}%)."
                ),
                status="active",
            )
        )
        new_recs.append(
            Recommendation(
                plant_id=plant_id,
                generated_date=analysis_date,
                category="Maintenance",
                description="Schedule a solar panel cleaning cycle to recover lost performance due to soiling.",
                priority="medium",
                status="pending",
            )
        )

    # ═══════════════════════════════════════════════════════════════════════
    # 2. Availability Alerts & Recommendations
    # ═══════════════════════════════════════════════════════════════════════
    availability = calculate_availability(lifetime.total_generation, lifetime.total_possible_generation)
    avail_diff = plant.expected_availability - availability
    if avail_diff >= 5.0:
        new_alerts.append(
            Alert(
                plant_id=plant_id,
                alert_date=analysis_date,
                severity="critical",
                category="Availability",
                message=(
                    f"Critical availability loss: Plant availability is {availability:.2f}% "
                    f"({avail_diff:.1f}% below target of {plant.expected_availability}%)."
                ),
                status="active",
            )
        )
        new_recs.append(
            Recommendation(
                plant_id=plant_id,
                generated_date=analysis_date,
                category="Maintenance",
                description="Investigate long-duration inverter trips or AC-side connection issues causing low availability.",
                priority="high",
                status="pending",
            )
        )
    elif avail_diff >= 2.0:
        new_alerts.append(
            Alert(
                plant_id=plant_id,
                alert_date=analysis_date,
                severity="warning",
                category="Availability",
                message=(
                    f"Minor availability shortfall: Plant availability is {availability:.2f}% "
                    f"({avail_diff:.1f}% below target of {plant.expected_availability}%)."
                ),
                status="active",
            )
        )
        new_recs.append(
            Recommendation(
                plant_id=plant_id,
                generated_date=analysis_date,
                category="Operations",
                description="Adjust inverter preventive maintenance schedules to execute during non-solar hours.",
                priority="medium",
                status="pending",
            )
        )

    # ═══════════════════════════════════════════════════════════════════════
    # 3. Loss Alerts & Recommendations (Grid Failures & Machine Losses)
    # ═══════════════════════════════════════════════════════════════════════
    total_possible = lifetime.total_possible_generation
    grid_fail_pct = (lifetime.grid_failure / total_possible * 100.0) if total_possible > 0 else 0.0
    machine_loss_pct = (lifetime.machine_loss / total_possible * 100.0) if total_possible > 0 else 0.0

    if grid_fail_pct >= 5.0:
        new_alerts.append(
            Alert(
                plant_id=plant_id,
                alert_date=analysis_date,
                severity="warning",
                category="Grid Outage",
                message=f"High grid outage impact: Grid failures cost {grid_fail_pct:.2f}% of possible generation.",
                status="active",
            )
        )
        new_recs.append(
            Recommendation(
                plant_id=plant_id,
                generated_date=analysis_date,
                category="Grid Relations",
                description="Liaise with grid operator regarding frequent transmission line outages and voltage stability.",
                priority="medium",
                status="pending",
            )
        )

    if machine_loss_pct >= 3.0:
        new_alerts.append(
            Alert(
                plant_id=plant_id,
                alert_date=analysis_date,
                severity="critical",
                category="Machine Loss",
                message=f"Critical equipment downtime: Machine losses represent {machine_loss_pct:.2f}% of possible generation.",
                status="active",
            )
        )
        new_recs.append(
            Recommendation(
                plant_id=plant_id,
                generated_date=analysis_date,
                category="Equipment Inspection",
                description="Perform thermal imaging and check inverter cooling fans and internal component health to reduce machine losses.",
                priority="high",
                status="pending",
            )
        )
    elif machine_loss_pct >= 1.0:
        new_alerts.append(
            Alert(
                plant_id=plant_id,
                alert_date=analysis_date,
                severity="warning",
                category="Machine Loss",
                message=f"Moderate machine loss observed: Machine losses represent {machine_loss_pct:.2f}% of possible generation.",
                status="active",
            )
        )

    # ═══════════════════════════════════════════════════════════════════════
    # 4. Degradation Alerts & Recommendations
    # ═══════════════════════════════════════════════════════════════════════
    deg_diff = deg.annual_degradation_rate - plant.annual_degradation_rate
    if deg_diff >= 2.0:
        new_alerts.append(
            Alert(
                plant_id=plant_id,
                alert_date=analysis_date,
                severity="critical",
                category="Degradation",
                message=(
                    f"Accelerated degradation detected: Annual decline rate is {deg.annual_degradation_rate}% "
                    f"which exceeds the expected rate of {plant.annual_degradation_rate}% by {deg_diff:.2f}%."
                ),
                status="active",
            )
        )
        new_recs.append(
            Recommendation(
                plant_id=plant_id,
                generated_date=analysis_date,
                category="Module Diagnostics",
                description="Conduct a thermal imaging sweep and EL imaging to identify micro-cracks, PID, or hot spots.",
                priority="high",
                status="pending",
            )
        )
    elif deg_diff >= 0.5:
        new_alerts.append(
            Alert(
                plant_id=plant_id,
                alert_date=analysis_date,
                severity="warning",
                category="Degradation",
                message=(
                    f"Elevated degradation observed: Annual decline rate is {deg.annual_degradation_rate}% "
                    f"(target: {plant.annual_degradation_rate}%)."
                ),
                status="active",
            )
        )

    # ═══════════════════════════════════════════════════════════════════════
    # 5. Inverter-level Deviation Alerts
    # ═══════════════════════════════════════════════════════════════════════
    if len(inverter_aggs) > 1:
        inv_prs = []
        for inv_agg in inverter_aggs:
            pr_inv = compute_inverter_pr(plant, inv_agg)
            inv_prs.append((inv_agg.name, pr_inv, inv_agg))

        avg_inv_pr = sum(p[1] for p in inv_prs) / len(inv_prs)
        for name, pr_inv, inv_agg in inv_prs:
            deviation = avg_inv_pr - pr_inv
            if deviation >= 5.0:
                new_alerts.append(
                    Alert(
                        plant_id=plant_id,
                        alert_date=analysis_date,
                        severity="warning",
                        category="Inverter Deviation",
                        message=(
                            f"Performance deviation on {name}: PR is {pr_inv:.2f}%, "
                            f"which is {deviation:.2f}% below the plant average of {avg_inv_pr:.2f}%."
                        ),
                        status="active",
                    )
                )
                new_recs.append(
                    Recommendation(
                        plant_id=plant_id,
                        generated_date=analysis_date,
                        category="Equipment Maintenance",
                        description=f"Inspect inverter '{name}' and associated DC fuse box / string connections for faults.",
                        priority="medium",
                        status="pending",
                    )
                )

    # ═══════════════════════════════════════════════════════════════════════
    # 6. Data Quality / Irradiance Anomaly Alerts
    # ═══════════════════════════════════════════════════════════════════════
    eff_frac = plant.module_efficiency / 100.0
    for d in daily_records:
        pr_val = calculate_pr(
            generation_kwh=d.generation,
            irradiation_wh_m2_sum=d.irradiation,
            panel_area_sqm=plant.total_panel_area_sqm,
            module_efficiency_frac=eff_frac,
            daily_running_hours=plant.daily_running_hours,
        )
        if pr_val > 100.0:
            new_alerts.append(
                Alert(
                    plant_id=plant_id,
                    alert_date=d.record_date,
                    severity="warning",
                    category="Data Quality",
                    message=(
                        f"Irradiance anomaly detected on {d.record_date}: "
                        f"Physically impossible Performance Ratio of {pr_val:.2f}% computed "
                        f"(Generation: {d.generation:.1f} kWh, Irradiation: {d.irradiation:.1f} Wh/m²). "
                        f"Irradiance value appears too low relative to power generated."
                    ),
                    status="active",
                )
            )

    # ═══════════════════════════════════════════════════════════════════════
    # Default Info Alert/Rec if plant is healthy
    # ═══════════════════════════════════════════════════════════════════════
    performance_alerts = [a for a in new_alerts if a.category != "Data Quality"]
    if not performance_alerts:
        new_alerts.append(
            Alert(
                plant_id=plant_id,
                alert_date=analysis_date,
                severity="info",
                category="System Health",
                message="All key performance metrics (PR, availability, losses) are operating within target thresholds.",
                status="active",
            )
        )
        new_recs.append(
            Recommendation(
                plant_id=plant_id,
                generated_date=analysis_date,
                category="Operations",
                description="Continue standard preventive maintenance schedule and monthly soiling checks.",
                priority="low",
                status="pending",
            )
        )

    # Save to database
    db.add_all(new_alerts)
    db.add_all(new_recs)
    db.commit()
