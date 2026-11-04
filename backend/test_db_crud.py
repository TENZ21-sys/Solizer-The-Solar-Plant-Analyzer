"""
SoliZer Database CRUD & Cascade Deletion Verification Script.
"""

import sys
from datetime import date, datetime

from sqlalchemy import select, create_engine
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.db.models import Plant, Inverter, DailyRecord, Alert, Recommendation, Report, SystemSettings


def run_db_validation():
    print("=== STARTING DATABASE VALIDATION ===")
    
    # 1. Setup in-memory database
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)
    Session = sessionmaker(bind=test_engine)
    db = Session()
    
    try:
        # 3. Create a Plant record
        print("2. Inserting test plant...")
        plant = Plant(
            name="Alpha Solar",
            location="Anuradhapura",
            country="Sri Lanka",
            installed_dc_capacity_mw=12.5,
            installed_ac_capacity_mw=10.0,
            commission_date=date(2023, 1, 15),
            number_of_blocks=2,
            inverter_type="central",
            number_of_inverters=2,
            panel_manufacturer="Longi",
            panel_model="LR5-72HPH",
            total_panel_area_sqm=55000.0,
            module_efficiency=21.1,
            daily_running_hours=5.5,
            annual_degradation_rate=0.5,
            expected_pr=78.5,
            expected_cuf=18.2,
            expected_availability=98.5,
            grid_operator="CEB",
            timezone="Asia/Colombo",
            has_weather_station=True,
            has_string_monitoring=False,
            notes="Primary test site"
        )
        db.add(plant)
        db.commit()
        db.refresh(plant)
        print(f"   Saved plant: {plant}")
        
        # 4. Insert Inverters
        print("3. Inserting test inverters...")
        inv1 = Inverter(plant_id=plant.id, name="INV-01", block_name="Block A")
        inv2 = Inverter(plant_id=plant.id, name="INV-02", block_name="Block B")
        db.add_all([inv1, inv2])
        db.commit()
        db.refresh(inv1)
        db.refresh(inv2)
        print(f"   Saved inverters: {inv1}, {inv2}")
        
        # 5. Insert Daily Records
        print("4. Inserting daily records...")
        record1 = DailyRecord(
            inverter_id=inv1.id,
            record_date=date(2026, 6, 1),
            irradiation=5.2,
            generation=4800.0,
            grid_failure=120.0,
            curtailment=0.0,
            grid_loss=30.0,
            machine_loss=50.0,
            total_generation=4800.0,
            total_possible_generation=5000.0
        )
        record2 = DailyRecord(
            inverter_id=inv2.id,
            record_date=date(2026, 6, 1),
            irradiation=5.2,
            generation=4900.0,
            grid_failure=0.0,
            curtailment=50.0,
            grid_loss=30.0,
            machine_loss=20.0,
            total_generation=4900.0,
            total_possible_generation=5000.0
        )
        db.add_all([record1, record2])
        db.commit()
        print("   Saved daily records successfully.")
        
        # 6. Insert Alert, Recommendation, and Report
        print("5. Inserting alert, recommendation, and report...")
        alert = Alert(
            plant_id=plant.id,
            alert_date=date(2026, 6, 1),
            severity="warning",
            category="inverter",
            message="INV-01 efficiency is below normal.",
            status="active"
        )
        rec = Recommendation(
            plant_id=plant.id,
            generated_date=date(2026, 6, 1),
            category="cleaning",
            description="Clean block A solar panels.",
            priority="medium",
            status="pending"
        )
        rep = Report(
            plant_id=plant.id,
            generated_date=datetime.utcnow(),
            report_title="Monthly Performance June 2026",
            report_type="pdf",
            file_path="/reports/report_june_2026.pdf",
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30)
        )
        db.add_all([alert, rec, rep])
        db.commit()
        print("   Saved audit entries successfully.")
        
        # 7. Verify relations and cascades
        print("6. Verifying database count and foreign key lookups...")
        plants_count = db.query(Plant).count()
        inverters_count = db.query(Inverter).count()
        records_count = db.query(DailyRecord).count()
        alerts_count = db.query(Alert).count()
        
        print(f"   Current Counts - Plants: {plants_count}, Inverters: {inverters_count}, DailyRecords: {records_count}, Alerts: {alerts_count}")
        assert plants_count == 1, "Plants count mismatch"
        assert inverters_count == 2, "Inverters count mismatch"
        assert records_count == 2, "Daily records count mismatch"
        assert alerts_count == 1, "Alerts count mismatch"
        
        # 8. Test Cascade Deletion
        print("7. Deleting plant (verifying CASCADE deletes)...")
        db.delete(plant)
        db.commit()
        
        # Recalculate counts
        plants_count_post = db.query(Plant).count()
        inverters_count_post = db.query(Inverter).count()
        records_count_post = db.query(DailyRecord).count()
        alerts_count_post = db.query(Alert).count()
        recs_count_post = db.query(Recommendation).count()
        reps_count_post = db.query(Report).count()
        
        print(f"   Post-Delete Counts - Plants: {plants_count_post}, Inverters: {inverters_count_post}, DailyRecords: {records_count_post}, Alerts: {alerts_count_post}, Recs: {recs_count_post}, Reports: {reps_count_post}")
        
        assert plants_count_post == 0, "Plant not deleted"
        assert inverters_count_post == 0, "Inverters not cascaded deleted"
        assert records_count_post == 0, "DailyRecords not cascaded deleted"
        assert alerts_count_post == 0, "Alerts not cascaded deleted"
        assert recs_count_post == 0, "Recommendations not cascaded deleted"
        assert reps_count_post == 0, "Reports not cascaded deleted"
        
        print("   Cascade deletion verified successfully.")
        print("=== DATABASE VALIDATION SUCCESSFUL ===")
        
    except Exception as e:
        print(f"!!! Error during database CRUD validation: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    run_db_validation()
