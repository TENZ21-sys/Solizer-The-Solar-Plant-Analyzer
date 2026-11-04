"""
SoliZer Intelligence Platform - Analytics Router.

Provides endpoints for dashboard summaries, generation analysis, KPIs,
inverter comparisons, loss breakdowns, degradation tracking, and
irradiation data.

All endpoints now call the calculation engines instead of returning
placeholder data.
"""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Alert, Plant, Recommendation, Inverter, DailyRecord
from app.engines.aggregation import (
    aggregate_to_lifetime,
    aggregate_to_monthly,
    get_daily_plant_records,
    get_per_inverter_aggregations,
)
from app.engines.kpi_calculator import (
    calculate_availability,
    compute_lifetime_kpis,
    compute_monthly_kpis,
    calculate_pr,
    calculate_cuf,
    calculate_specific_yield,
)
from app.engines.degradation import compute_degradation
from app.engines.inverter_analysis import analyze_inverters
from app.engines.loss_analysis import compute_loss_analysis
from app.engines.irradiation_analysis import (
    compute_irradiation_analysis,
    compute_monthly_irradiation,
)
from app.schemas.analytics_schemas import (
    AlertResponse,
    DashboardSummary,
    DegradationData,
    DegradationDataPoint,
    GenerationData,
    GenerationDataPoint,
    InverterSummary,
    InverterResponse,
    InverterTimeSeriesPoint,
    IrradiationData,
    IrradiationDataPoint,
    KPIData,
    LossBreakdown,
    LossCategory,
    LossDetail,
    LossDataPoint,
    RecommendationResponse,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_plant_or_404(plant_id: int, db: Session) -> Plant:
    """Return the Plant instance or raise a 404."""
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plant with id {plant_id} not found.",
        )
    return plant


def interpolate_anomalous_prs(data_points: list[GenerationDataPoint]):
    """Linearly interpolate daily PR values that exceed 100% due to data anomalies."""
    n = len(data_points)
    for i in range(n):
        dp = data_points[i]
        if dp.pr is not None and dp.pr > 100.0:
            # Find nearest valid preceding PR (pr <= 100)
            prev_pr = None
            prev_idx = None
            for j in range(i - 1, -1, -1):
                if data_points[j].pr is not None and data_points[j].pr <= 100.0:
                    prev_pr = data_points[j].pr
                    prev_idx = j
                    break
            
            # Find nearest valid succeeding PR (pr <= 100)
            next_pr = None
            next_idx = None
            for j in range(i + 1, n):
                if data_points[j].pr is not None and data_points[j].pr <= 100.0:
                    next_pr = data_points[j].pr
                    next_idx = j
                    break
            
            # Linear interpolation based on neighboring gradients
            if prev_pr is not None and next_pr is not None:
                dp.pr = prev_pr + (next_pr - prev_pr) * (i - prev_idx) / (next_idx - prev_idx)
            elif prev_pr is not None:
                dp.pr = prev_pr
            elif next_pr is not None:
                dp.pr = next_pr
            else:
                dp.pr = 75.0  # Safe default fallback
            dp.pr = round(dp.pr, 2)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get(
    "/{plant_id}/dashboard",
    response_model=DashboardSummary,
    summary="Get dashboard summary",
)
def get_dashboard_summary(
    plant_id: int,
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """Return a high-level performance summary for the plant's dashboard view."""
    plant = _get_plant_or_404(plant_id, db)

    # Aggregate data
    daily_records = get_daily_plant_records(db, plant_id, start_date=start_date, end_date=end_date)

    if not daily_records:
        return DashboardSummary(
            total_generation_kwh=0.0,
            possible_generation_kwh=0.0,
            performance_ratio=0.0,
            cuf=0.0,
            availability=0.0,
            loss_percentage=0.0,
            health_score=0.0,
            degradation_index=0.0,
            generation_trend=[],
            loss_breakdown=[],
            recent_alerts=[],
            top_recommendations=[],
        )

    lifetime = aggregate_to_lifetime(daily_records)
    monthly_records = aggregate_to_monthly(daily_records)
    kpis = compute_lifetime_kpis(plant, lifetime)
    monthly_kpis = compute_monthly_kpis(plant, monthly_records)

    # Availability
    availability = calculate_availability(
        lifetime.total_generation, lifetime.total_possible_generation
    )

    # Loss percentage (uses non-double-counted grid_loss + machine_loss)
    total_loss = lifetime.grid_loss + lifetime.machine_loss
    loss_pct = (
        (total_loss / lifetime.total_possible_generation * 100.0)
        if lifetime.total_possible_generation > 0
        else 0.0
    )

    # Degradation
    deg = compute_degradation(
        monthly_kpis,
        plant.expected_pr,
        plant.annual_degradation_rate,
        plant.commission_date,
    )

    # Health score: weighted combination of PR, availability, and loss
    # Score out of 100 (higher = better)
    pr_score = min(kpis.performance_ratio / plant.expected_pr * 100, 100) if plant.expected_pr > 0 else 50
    avail_score = min(availability, 100)
    loss_score = max(100 - loss_pct * 5, 0)  # penalize losses
    health_score = round(pr_score * 0.4 + avail_score * 0.4 + loss_score * 0.2, 1)

    # Generation trend (last 12 months) - map expected generation correctly
    generation_trend = []
    for mr, mk in zip(monthly_records[-12:], monthly_kpis[-12:]):
        generation_trend.append(
            GenerationDataPoint(
                date=mk.label,
                actual_kwh=round(mr.total_generation, 1),
                expected_kwh=round(mr.total_possible_generation, 1),
                pr=round(mk.pr, 2),
                cuf=round(mk.cuf, 2),
            )
        )

    # Loss breakdown for pie chart
    loss_breakdown_items = []
    loss_engine = compute_loss_analysis(lifetime)
    for cat in loss_engine.categories:
        loss_breakdown_items.append(
            LossCategory(
                category=cat.category,
                value=cat.loss_mwh,
                color=cat.color,
            )
        )

    # Recent alerts (last 5)
    recent_alerts_db = (
        db.query(Alert)
        .filter(Alert.plant_id == plant_id)
        .order_by(Alert.created_at.desc())
        .limit(5)
        .all()
    )

    # Top recommendations (last 5)
    top_recs_db = (
        db.query(Recommendation)
        .filter(Recommendation.plant_id == plant_id)
        .order_by(Recommendation.created_at.desc())
        .limit(5)
        .all()
    )

    return DashboardSummary(
        total_generation_kwh=round(lifetime.total_generation, 1),
        possible_generation_kwh=round(lifetime.total_possible_generation, 1),
        performance_ratio=kpis.performance_ratio,
        cuf=kpis.cuf,
        availability=round(availability, 2),
        loss_percentage=round(loss_pct, 2),
        health_score=health_score,
        degradation_index=deg.annual_degradation_rate,
        generation_trend=generation_trend,
        loss_breakdown=loss_breakdown_items,
        recent_alerts=recent_alerts_db,
        top_recommendations=top_recs_db,
    )


# ---------------------------------------------------------------------------
# Generation Analysis
# ---------------------------------------------------------------------------

@router.get(
    "/{plant_id}/generation",
    response_model=GenerationData,
    summary="Get generation data",
)
def get_generation_data(
    plant_id: int,
    period: str = Query(
        "daily",
        description="Aggregation period",
        pattern="^(daily|monthly|yearly)$",
    ),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    """Return time-series generation data for the specified plant."""
    plant = _get_plant_or_404(plant_id, db)
    daily_records = get_daily_plant_records(db, plant_id, start_date=start_date, end_date=end_date)

    if not daily_records:
        return GenerationData(
            period=period, data=[], total_actual_kwh=0.0,
            total_expected_kwh=0.0, average_pr=0.0,
        )

    monthly_records = aggregate_to_monthly(daily_records)
    monthly_kpis = compute_monthly_kpis(plant, monthly_records)

    data_points: list[GenerationDataPoint] = []
    eff_frac = plant.module_efficiency / 100.0

    if period == "daily":
        for d in daily_records:
            pr_val = calculate_pr(
                generation_kwh=d.total_generation,
                irradiation_wh_m2_sum=d.irradiation,
                panel_area_sqm=plant.total_panel_area_sqm,
                module_efficiency_frac=eff_frac,
                daily_running_hours=plant.daily_running_hours,
            )
            cuf_val = calculate_cuf(
                generation_kwh=d.total_generation,
                ac_capacity_mw=plant.installed_ac_capacity_mw,
                total_hours=24.0,
            )
            sy_val = calculate_specific_yield(
                generation_kwh=d.total_generation,
                dc_capacity_mw=plant.installed_dc_capacity_mw,
            )
            data_points.append(
                GenerationDataPoint(
                    date=d.record_date.isoformat(),
                    actual_kwh=round(d.total_generation, 1),
                    expected_kwh=round(d.total_possible_generation, 1),
                    pr=round(pr_val, 2),
                    cuf=round(cuf_val, 2),
                    irradiation=round(d.irradiation, 1),
                    specific_yield=round(sy_val, 2),
                )
            )
        interpolate_anomalous_prs(data_points)
    elif period == "monthly":
        for mr, mk in zip(monthly_records, monthly_kpis):
            data_points.append(
                GenerationDataPoint(
                    date=mk.label,
                    actual_kwh=round(mr.total_generation, 1),
                    expected_kwh=round(mr.total_possible_generation, 1),
                    pr=round(mk.pr, 2),
                    cuf=round(mk.cuf, 2),
                    irradiation=round(mr.irradiation, 1),
                    specific_yield=round(mk.specific_yield, 2),
                )
            )
    else:  # yearly — group by study year (May 1st - April 30th)
        from collections import defaultdict
        yearly_data = defaultdict(lambda: {
            "actual": 0.0,
            "expected": 0.0,
            "irradiation": 0.0,
            "days": 0
        })
        for mr in monthly_records:
            start_year = mr.year if mr.month >= 5 else mr.year - 1
            label = f"{start_year}-{start_year+1}"
            yearly_data[label]["actual"] += mr.total_generation
            yearly_data[label]["expected"] += mr.total_possible_generation
            yearly_data[label]["irradiation"] += mr.irradiation
            yearly_data[label]["days"] += mr.days
            
        for study_year in sorted(yearly_data.keys()):
            yd = yearly_data[study_year]
            pr_val = calculate_pr(
                generation_kwh=yd["actual"],
                irradiation_wh_m2_sum=yd["irradiation"],
                panel_area_sqm=plant.total_panel_area_sqm,
                module_efficiency_frac=eff_frac,
                daily_running_hours=plant.daily_running_hours,
            )
            cuf_val = calculate_cuf(
                generation_kwh=yd["actual"],
                ac_capacity_mw=plant.installed_ac_capacity_mw,
                total_hours=yd["days"] * 24.0,
            )
            sy_val = calculate_specific_yield(
                generation_kwh=yd["actual"],
                dc_capacity_mw=plant.installed_dc_capacity_mw,
            )
            data_points.append(
                GenerationDataPoint(
                    date=study_year,
                    actual_kwh=round(yd["actual"], 1),
                    expected_kwh=round(yd["expected"], 1),
                    pr=round(pr_val, 2),
                    cuf=round(cuf_val, 2),
                    irradiation=round(yd["irradiation"], 1),
                    specific_yield=round(sy_val, 2),
                )
            )

    total_actual = sum(dp.actual_kwh for dp in data_points)
    total_expected = sum(dp.expected_kwh for dp in data_points)
    avg_pr = (
        sum(dp.pr for dp in data_points if dp.pr is not None) / len(data_points)
        if data_points
        else 0.0
    )

    return GenerationData(
        period=period,
        data=data_points,
        total_actual_kwh=round(total_actual, 1),
        total_expected_kwh=round(total_expected, 1),
        average_pr=round(avg_pr, 2),
    )


# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------

@router.get(
    "/{plant_id}/kpi",
    response_model=KPIData,
    summary="Get KPI data",
)
def get_kpi_data(
    plant_id: int,
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """Return key performance indicators for the specified plant."""
    plant = _get_plant_or_404(plant_id, db)
    daily_records = get_daily_plant_records(db, plant_id, start_date=start_date, end_date=end_date)

    if not daily_records:
        return KPIData(
            plant_id=plant.id,
            performance_ratio=0.0,
            capacity_utilisation_factor=0.0,
            specific_yield=0.0,
            energy_yield_kwh=0.0,
            average_daily_generation_kwh=0.0,
        )

    lifetime = aggregate_to_lifetime(daily_records)
    kpis = compute_lifetime_kpis(plant, lifetime)

    return KPIData(
        plant_id=plant.id,
        performance_ratio=kpis.performance_ratio,
        capacity_utilisation_factor=kpis.cuf,
        specific_yield=kpis.specific_yield,
        energy_yield_kwh=kpis.energy_yield_kwh,
        average_daily_generation_kwh=kpis.average_daily_generation_kwh,
    )


# ---------------------------------------------------------------------------
# Inverter Analysis
# ---------------------------------------------------------------------------

@router.get(
    "/{plant_id}/inverters",
    response_model=InverterResponse,
    summary="Get inverter summaries",
)
def get_inverter_summaries(
    plant_id: int,
    period: str = Query(
        "monthly",
        description="Aggregation period",
        pattern="^(daily|monthly|yearly)$",
    ),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """Return per-inverter performance summaries for the specified plant."""
    plant = _get_plant_or_404(plant_id, db)
    inv_aggs = get_per_inverter_aggregations(db, plant_id, start_date=start_date, end_date=end_date)

    if not inv_aggs:
        return InverterResponse(summaries=[], time_series=[])

    results = analyze_inverters(plant, inv_aggs)
    summaries = [
        InverterSummary(
            inverter_id=str(r.inverter_id),
            name=r.name,
            capacity_kw=round(
                plant.installed_dc_capacity_mw * 1000 / max(plant.number_of_inverters, 1),
                1,
            ),
            total_generation_kwh=r.total_generation_kwh,
            performance_ratio=r.performance_ratio,
            availability=r.availability,
            status=r.status,
            efficiency=r.efficiency,
            specific_yield=round(
                r.total_generation_kwh / max(plant.installed_dc_capacity_mw * 1000 / max(plant.number_of_inverters, 1), 1.0),
                2
            ),
            machine_loss_kwh=r.machine_loss_kwh,
        )
        for r in results
    ]

    # Calculate time-series details for comparison charts
    inverter_ids = {inv.id: inv.name for inv in db.query(Inverter.id, Inverter.name).filter(Inverter.plant_id == plant_id).all()}
    
    query = (
        db.query(
            DailyRecord.record_date,
            DailyRecord.inverter_id,
            DailyRecord.generation,
            DailyRecord.irradiation,
            DailyRecord.total_possible_generation,
            DailyRecord.machine_loss,
        )
        .filter(DailyRecord.inverter_id.in_(inverter_ids.keys()))
    )
    if start_date:
        query = query.filter(DailyRecord.record_date >= start_date)
    if end_date:
        query = query.filter(DailyRecord.record_date <= end_date)
    
    daily_inv_records = query.order_by(DailyRecord.record_date).all()

    time_series = []
    eff_frac = plant.module_efficiency / 100.0
    inv_area = plant.total_panel_area_sqm / max(plant.number_of_inverters, 1)
    dc_cap_kw = plant.installed_dc_capacity_mw * 1000 / max(plant.number_of_inverters, 1)
    _MONTH_NAMES = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    if period == "daily":
        for r in daily_inv_records:
            inv_name = inverter_ids.get(r.inverter_id, f"Inverter {r.inverter_id}")
            pr_val = calculate_pr(r.generation, r.irradiation, inv_area, eff_frac, plant.daily_running_hours)
            if pr_val > 100.0:
                pr_val = 75.0
            sy_val = r.generation / max(dc_cap_kw, 1.0)
            time_series.append(
                InverterTimeSeriesPoint(
                    date=r.record_date.isoformat(),
                    inverter_name=inv_name,
                    generation_kwh=round(r.generation, 1),
                    pr=round(pr_val, 2),
                    specific_yield=round(sy_val, 2),
                    machine_loss_kwh=round(r.machine_loss, 1),
                )
            )
    elif period == "monthly":
        from collections import defaultdict
        buckets = defaultdict(lambda: {"generation": 0.0, "irradiation": 0.0, "machine_loss": 0.0, "days": 0})
        for r in daily_inv_records:
            key = (r.record_date.year, r.record_date.month, r.inverter_id)
            buckets[key]["generation"] += r.generation
            buckets[key]["irradiation"] += r.irradiation
            buckets[key]["machine_loss"] += r.machine_loss
            buckets[key]["days"] += 1
        
        for (year, month, inv_id), val in sorted(buckets.items()):
            inv_name = inverter_ids.get(inv_id, f"Inverter {inv_id}")
            pr_val = calculate_pr(val["generation"], val["irradiation"], inv_area, eff_frac, plant.daily_running_hours)
            if pr_val > 100.0:
                pr_val = 75.0
            sy_val = val["generation"] / max(dc_cap_kw, 1.0)
            label = f"{_MONTH_NAMES[month]} {year}"
            time_series.append(
                InverterTimeSeriesPoint(
                    date=label,
                    inverter_name=inv_name,
                    generation_kwh=round(val["generation"], 1),
                    pr=round(pr_val, 2),
                    specific_yield=round(sy_val, 2),
                    machine_loss_kwh=round(val["machine_loss"], 1),
                )
            )
    else:  # yearly
        from collections import defaultdict
        buckets = defaultdict(lambda: {"generation": 0.0, "irradiation": 0.0, "machine_loss": 0.0, "days": 0})
        for r in daily_inv_records:
            start_year = r.record_date.year if r.record_date.month >= 5 else r.record_date.year - 1
            study_year = f"{start_year}-{start_year+1}"
            key = (study_year, r.inverter_id)
            buckets[key]["generation"] += r.generation
            buckets[key]["irradiation"] += r.irradiation
            buckets[key]["machine_loss"] += r.machine_loss
            buckets[key]["days"] += 1
        
        for (study_year, inv_id), val in sorted(buckets.items()):
            inv_name = inverter_ids.get(inv_id, f"Inverter {inv_id}")
            pr_val = calculate_pr(val["generation"], val["irradiation"], inv_area, eff_frac, plant.daily_running_hours)
            if pr_val > 100.0:
                pr_val = 75.0
            sy_val = val["generation"] / max(dc_cap_kw, 1.0)
            time_series.append(
                InverterTimeSeriesPoint(
                    date=study_year,
                    inverter_name=inv_name,
                    generation_kwh=round(val["generation"], 1),
                    pr=round(pr_val, 2),
                    specific_yield=round(sy_val, 2),
                    machine_loss_kwh=round(val["machine_loss"], 1),
                )
            )

    return InverterResponse(summaries=summaries, time_series=time_series)


# ---------------------------------------------------------------------------
# Loss Breakdown
# ---------------------------------------------------------------------------

@router.get(
    "/{plant_id}/losses",
    response_model=LossBreakdown,
    summary="Get loss breakdown",
)
def get_loss_breakdown(
    plant_id: int,
    period: str = Query(
        "monthly",
        description="Aggregation period",
        pattern="^(daily|monthly|yearly)$",
    ),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """Return a breakdown of energy losses for the specified plant."""
    plant = _get_plant_or_404(plant_id, db)
    daily_records = get_daily_plant_records(db, plant_id, start_date=start_date, end_date=end_date)

    if not daily_records:
        return LossBreakdown(
            total_loss_kwh=0.0, total_loss_percentage=0.0, categories=[], time_series=[],
        )

    lifetime = aggregate_to_lifetime(daily_records)
    loss_result = compute_loss_analysis(lifetime)

    categories = [
        LossDetail(
            category=cat.category,
            loss_kwh=cat.loss_kwh,
            loss_percentage=cat.loss_percentage,
            description=cat.description,
            color=cat.color,
        )
        for cat in loss_result.categories
    ]

    # Calculate time series
    time_series = []
    _MONTH_NAMES = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    if period == "daily":
        for d in daily_records:
            time_series.append(
                LossDataPoint(
                    date=d.record_date.isoformat(),
                    grid_failure_kwh=round(d.grid_failure, 1),
                    curtailment_kwh=round(d.curtailment, 1),
                    machine_loss_kwh=round(d.machine_loss, 1),
                    total_loss_kwh=round(d.grid_loss + d.machine_loss, 1),
                )
            )
    elif period == "monthly":
        monthly_records = aggregate_to_monthly(daily_records)
        for mr in monthly_records:
            label = f"{_MONTH_NAMES[mr.month]} {mr.year}"
            time_series.append(
                LossDataPoint(
                    date=label,
                    grid_failure_kwh=round(mr.grid_failure, 1),
                    curtailment_kwh=round(mr.curtailment, 1),
                    machine_loss_kwh=round(mr.machine_loss, 1),
                    total_loss_kwh=round(mr.grid_loss + mr.machine_loss, 1),
                )
            )
    else:  # yearly
        from collections import defaultdict
        yearly_data = defaultdict(lambda: {
            "grid_failure": 0.0,
            "curtailment": 0.0,
            "grid_loss": 0.0,
            "machine_loss": 0.0,
        })
        monthly_records = aggregate_to_monthly(daily_records)
        for mr in monthly_records:
            start_year = mr.year if mr.month >= 5 else mr.year - 1
            label = f"{start_year}-{start_year+1}"
            yearly_data[label]["grid_failure"] += mr.grid_failure
            yearly_data[label]["curtailment"] += mr.curtailment
            yearly_data[label]["grid_loss"] += mr.grid_loss
            yearly_data[label]["machine_loss"] += mr.machine_loss
        
        for study_year in sorted(yearly_data.keys()):
            yd = yearly_data[study_year]
            time_series.append(
                LossDataPoint(
                    date=study_year,
                    grid_failure_kwh=round(yd["grid_failure"], 1),
                    curtailment_kwh=round(yd["curtailment"], 1),
                    machine_loss_kwh=round(yd["machine_loss"], 1),
                    total_loss_kwh=round(yd["grid_loss"] + yd["machine_loss"], 1),
                )
            )

    return LossBreakdown(
        total_loss_kwh=loss_result.total_loss_kwh,
        total_loss_percentage=loss_result.total_loss_percentage,
        categories=categories,
        time_series=time_series,
    )


# ---------------------------------------------------------------------------
# Degradation Analysis
# ---------------------------------------------------------------------------

@router.get(
    "/{plant_id}/degradation",
    response_model=DegradationData,
    summary="Get degradation data",
)
def get_degradation_data(
    plant_id: int,
    period: str = Query(
        "yearly",
        description="Aggregation period",
        pattern="^(daily|monthly|yearly)$",
    ),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """Return year-over-year degradation data points for the specified plant."""
    plant = _get_plant_or_404(plant_id, db)
    daily_records = get_daily_plant_records(db, plant_id, start_date=start_date, end_date=end_date)

    if not daily_records:
        return DegradationData(
            annual_degradation_rate=0.0,
            cumulative_degradation=0.0,
            expected_lifetime_years=0.0,
            trend=[],
        )

    monthly_records = aggregate_to_monthly(daily_records)
    monthly_kpis = compute_monthly_kpis(plant, monthly_records)

    deg = compute_degradation(
        monthly_kpis,
        plant.expected_pr,
        plant.annual_degradation_rate,
        plant.commission_date,
    )

    if period == "yearly":
        trend = [
            DegradationDataPoint(
                year=pt.year,
                pr=pt.pr,
                expected_pr=pt.expected_pr,
            )
            for pt in deg.trend
        ]
    elif period == "monthly":
        trend = []
        for mr, mk in zip(monthly_records, monthly_kpis):
            days_elapsed = (date(mr.year, mr.month, 15) - plant.commission_date).days
            years_elapsed = max(days_elapsed / 365.25, 0.0)
            expected_pr_val = plant.expected_pr - (plant.annual_degradation_rate * years_elapsed)
            trend.append(
                DegradationDataPoint(
                    year=mk.label,
                    pr=round(mk.pr, 2),
                    expected_pr=round(expected_pr_val, 2),
                )
            )
    else:  # daily
        trend = []
        eff_frac = plant.module_efficiency / 100.0
        for d in daily_records:
            days_elapsed = (d.record_date - plant.commission_date).days
            years_elapsed = max(days_elapsed / 365.25, 0.0)
            expected_pr_val = plant.expected_pr - (plant.annual_degradation_rate * years_elapsed)
            pr_val = calculate_pr(
                generation_kwh=d.total_generation,
                irradiation_wh_m2_sum=d.irradiation,
                panel_area_sqm=plant.total_panel_area_sqm,
                module_efficiency_frac=eff_frac,
                daily_running_hours=plant.daily_running_hours,
            )
            trend.append(
                DegradationDataPoint(
                    year=d.record_date.isoformat(),
                    pr=round(pr_val, 2),
                    expected_pr=round(expected_pr_val, 2),
                )
            )
        # Interpolate daily anomalies
        n = len(trend)
        for i in range(n):
            dp = trend[i]
            if dp.pr > 100.0:
                prev_pr = None
                prev_idx = None
                for j in range(i - 1, -1, -1):
                    if trend[j].pr <= 100.0:
                        prev_pr = trend[j].pr
                        prev_idx = j
                        break
                next_pr = None
                next_idx = None
                for j in range(i + 1, n):
                    if trend[j].pr <= 100.0:
                        next_pr = trend[j].pr
                        next_idx = j
                        break
                if prev_pr is not None and next_pr is not None:
                    dp.pr = prev_pr + (next_pr - prev_pr) * (i - prev_idx) / (next_idx - prev_idx)
                elif prev_pr is not None:
                    dp.pr = prev_pr
                elif next_pr is not None:
                    dp.pr = next_pr
                else:
                    dp.pr = 75.0
                dp.pr = round(dp.pr, 2)

    return DegradationData(
        annual_degradation_rate=deg.annual_degradation_rate,
        cumulative_degradation=deg.cumulative_degradation,
        expected_lifetime_years=deg.expected_lifetime_years,
        expected_degradation=deg.expected_degradation,
        trend=trend,
    )


# ---------------------------------------------------------------------------
# Irradiation
# ---------------------------------------------------------------------------

@router.get(
    "/{plant_id}/irradiation",
    response_model=IrradiationData,
    summary="Get irradiation data",
)
def get_irradiation_data(
    plant_id: int,
    period: str = Query(
        "daily",
        description="Aggregation period",
        pattern="^(daily|monthly|yearly)$",
    ),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """Return irradiation metrics for the specified plant."""
    plant = _get_plant_or_404(plant_id, db)
    daily_records = get_daily_plant_records(db, plant_id, start_date=start_date, end_date=end_date)

    if not daily_records:
        return IrradiationData(
            plant_id=plant.id,
            total_ghi_kwh_m2=0.0,
            total_poa_kwh_m2=0.0,
            average_daily_ghi=0.0,
            average_daily_poa=0.0,
            peak_sun_hours=0.0,
            data=[],
        )

    lifetime = aggregate_to_lifetime(daily_records)
    irr_result = compute_irradiation_analysis(lifetime, daily_records)

    # Calculate time series points
    data_points = []
    _MONTH_NAMES = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    if period == "daily":
        for d in daily_records:
            val_kwh_m2 = d.irradiation / 100.0
            data_points.append(
                IrradiationDataPoint(
                    date=d.record_date.isoformat(),
                    ghi_kwh_m2=round(val_kwh_m2, 2),
                    poa_kwh_m2=round(val_kwh_m2, 2),
                    peak_sun_hours=round(val_kwh_m2, 2),
                )
            )
    elif period == "monthly":
        monthly_records = aggregate_to_monthly(daily_records)
        for mr in monthly_records:
            val_kwh_m2 = mr.irradiation / 100.0
            psh = val_kwh_m2 / mr.days if mr.days > 0 else 0.0
            label = f"{_MONTH_NAMES[mr.month]} {mr.year}"
            data_points.append(
                IrradiationDataPoint(
                    date=label,
                    ghi_kwh_m2=round(val_kwh_m2, 1),
                    poa_kwh_m2=round(val_kwh_m2, 1),
                    peak_sun_hours=round(psh, 2),
                )
            )
    else:  # yearly
        from collections import defaultdict
        yearly_data = defaultdict(lambda: {"irradiation": 0.0, "days": 0})
        monthly_records = aggregate_to_monthly(daily_records)
        for mr in monthly_records:
            start_year = mr.year if mr.month >= 5 else mr.year - 1
            label = f"{start_year}-{start_year+1}"
            yearly_data[label]["irradiation"] += mr.irradiation
            yearly_data[label]["days"] += mr.days
        
        for study_year in sorted(yearly_data.keys()):
            yd = yearly_data[study_year]
            val_kwh_m2 = yd["irradiation"] / 100.0
            psh = val_kwh_m2 / yd["days"] if yd["days"] > 0 else 0.0
            data_points.append(
                IrradiationDataPoint(
                    date=study_year,
                    ghi_kwh_m2=round(val_kwh_m2, 1),
                    poa_kwh_m2=round(val_kwh_m2, 1),
                    peak_sun_hours=round(psh, 2),
                )
            )

    return IrradiationData(
        plant_id=plant.id,
        total_ghi_kwh_m2=irr_result.total_irradiation_kwh_m2,
        total_poa_kwh_m2=irr_result.total_irradiation_kwh_m2,  # same sensor
        average_daily_ghi=irr_result.average_daily_wh_m2,
        average_daily_poa=irr_result.average_daily_wh_m2,
        peak_sun_hours=irr_result.peak_sun_hours,
        data=data_points,
    )
