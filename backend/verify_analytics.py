"""
SoliZer - Verification of Analytics Engines.
Reads plant ID 2 (which we just imported) and prints out the dashboard/analytics summary.
"""
import sqlite3
from app.db.database import SessionLocal
from app.db.models import Plant, DailyRecord
from app.engines.aggregation import get_daily_plant_records, aggregate_to_lifetime, aggregate_to_monthly
from app.engines.kpi_calculator import compute_lifetime_kpis, compute_monthly_kpis
from app.engines.degradation import compute_degradation
from app.engines.inverter_analysis import analyze_inverters
from app.engines.loss_analysis import compute_loss_analysis
from app.engines.irradiation_analysis import compute_irradiation_analysis

db = SessionLocal()
try:
    plant = db.query(Plant).filter(Plant.id == 2).first()
    if not plant:
        print("Plant 2 not found!")
    else:
        print(f"Plant specs: Name={plant.name}, Area={plant.total_panel_area_sqm}, Eff={plant.module_efficiency}%, Hours={plant.daily_running_hours}")
        daily_records = get_daily_plant_records(db, 2)
        print(f"Daily records retrieved: {len(daily_records)}")
        
        lifetime = aggregate_to_lifetime(daily_records)
        print(f"Lifetime Aggregation: Gen={lifetime.total_generation:.1f} kWh, Irr={lifetime.irradiation:.1f}, Possible Gen={lifetime.total_possible_generation:.1f} kWh, Days={lifetime.days}")
        
        kpis = compute_lifetime_kpis(plant, lifetime)
        print(f"KPIs: PR={kpis.performance_ratio}%, CUF={kpis.cuf}%, Specific Yield={kpis.specific_yield} kWh/kWp")
        
        monthly = aggregate_to_monthly(daily_records)
        print(f"Monthly records: {len(monthly)}")
        for m in monthly:
            print(f"  {m.year}-{m.month:02d}: Gen={m.total_generation:.1f} kWh, Irr={m.irradiation:.1f}, Days={m.days}")
            
        monthly_kpis = compute_monthly_kpis(plant, monthly)
        print(f"Monthly KPIs:")
        for mk in monthly_kpis:
            print(f"  {mk.label}: Gen={mk.generation_mwh:.1f} MWh, Irr={mk.irradiation_kwh_m2:.1f} kWh/m2, PR={mk.pr}%, CUF={mk.cuf}%")
            
        deg = compute_degradation(monthly_kpis, plant.expected_pr, plant.annual_degradation_rate)
        print(f"Degradation: Rate={deg.annual_degradation_rate}%, Cumulative={deg.cumulative_degradation}%, Lifetime={deg.expected_lifetime_years} years")
        
        loss = compute_loss_analysis(lifetime)
        print(f"Loss analysis: Total Loss={loss.total_loss_kwh:.1f} kWh ({loss.total_loss_percentage:.2f}%)")
        for cat in loss.categories:
            print(f"  Category {cat.category}: {cat.loss_kwh:.1f} kWh ({cat.loss_percentage:.2f}%)")
            
finally:
    db.close()
