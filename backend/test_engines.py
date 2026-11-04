"""
SoliZer - Unit Tests for Calculation Engines.
Uses standard unittest library to verify calculations of:
- KPI calculator (PR, CUF, Specific Yield)
- Degradation engine (YoY slope, expected lifetime)
- Loss analysis engine (Grid loss, machine loss, percentage allocation)
- Aggregation engine
"""
import unittest
from dataclasses import dataclass
from typing import List

# Mock objects or imports
from app.db.models import Plant
from app.engines.kpi_calculator import (
    calculate_pr,
    calculate_cuf,
    calculate_specific_yield,
    calculate_availability,
    MonthlyKPI,
)
from app.engines.degradation import compute_degradation, DegradationPoint
from app.engines.loss_analysis import compute_loss_analysis
from app.engines.aggregation import LifetimePlantRecord


class TestKPICalculations(unittest.TestCase):
    def test_calculate_pr(self):
        # Sample values
        gen = 1000.0  # kWh
        irr_sum = 100.0  # Wh/m2 daily sum
        area = 50000.0  # sqm
        eff = 0.20  # 20%
        hours = 5.5
        
        # Denominator = 100.0 * 50000.0 * 0.20 * 5.5 / 1000 = 5500.0 kWh
        # PR = 1000 / 5500.0 * 100 = 18.1818%
        pr = calculate_pr(gen, irr_sum, area, eff, hours)
        self.assertAlmostEqual(pr, 18.181818, places=4)

        # Zero denominator safety
        self.assertEqual(calculate_pr(gen, 0.0, area, eff, hours), 0.0)

    def test_calculate_cuf(self):
        # Gen = 1000 kWh = 1 MWh
        # AC = 10 MW
        # Hours = 24
        # CUF = 1 / (10 * 24) * 100 = 1 / 240 * 100 = 0.4167%
        cuf = calculate_cuf(1000.0, 10.0, 24.0)
        self.assertAlmostEqual(cuf, 0.416666, places=4)
        
        self.assertEqual(calculate_cuf(1000.0, 0.0, 24.0), 0.0)

    def test_calculate_specific_yield(self):
        # Gen = 5000 kWh
        # DC = 1.0 MW = 1000 kWp
        # Yield = 5000 / 1000 = 5.0 kWh/kWp
        sy = calculate_specific_yield(5000.0, 1.0)
        self.assertEqual(sy, 5.0)

    def test_calculate_availability(self):
        # Gen = 800, Possible = 1000 => 80.0%
        avail = calculate_availability(800.0, 1000.0)
        self.assertEqual(avail, 80.0)
        
        self.assertEqual(calculate_availability(800.0, 0.0), 0.0)


class TestDegradationEngine(unittest.TestCase):
    def test_compute_degradation_decreasing(self):
        from datetime import date
        # Create a series of monthly KPIs with declining PR
        monthly_kpis = [
            MonthlyKPI(year=2023, month=5, label="May 2023", generation_mwh=100.0, irradiation_kwh_m2=100.0, pr=80.0, cuf=15.0, specific_yield=10.0),
            MonthlyKPI(year=2023, month=6, label="Jun 2023", generation_mwh=100.0, irradiation_kwh_m2=100.0, pr=79.5, cuf=15.0, specific_yield=10.0),
            MonthlyKPI(year=2023, month=7, label="Jul 2023", generation_mwh=100.0, irradiation_kwh_m2=100.0, pr=79.0, cuf=15.0, specific_yield=10.0),
            MonthlyKPI(year=2023, month=8, label="Aug 2023", generation_mwh=100.0, irradiation_kwh_m2=100.0, pr=78.5, cuf=15.0, specific_yield=10.0),
        ]
        # Month index: 0, 1, 2, 3
        # PR: 80.0, 79.5, 79.0, 78.5
        # Slope is exactly -0.5% PR per month.
        # Annual decline = -0.5 * 12 = -6.0% per year.
        deg = compute_degradation(monthly_kpis, expected_pr=80.0, configured_annual_degradation_rate=0.5, commission_date=date(2023, 1, 15))
        self.assertEqual(deg.annual_degradation_rate, 6.0)
        self.assertEqual(deg.cumulative_degradation, 1.5)  # 80.0 - 78.5 = 1.5%
        self.assertAlmostEqual(deg.expected_degradation, 0.31, places=2)

    def test_compute_degradation_empty(self):
        from datetime import date
        deg = compute_degradation([], expected_pr=80.0, configured_annual_degradation_rate=0.5, commission_date=date(2023, 1, 15))
        self.assertEqual(deg.annual_degradation_rate, 0.0)
        self.assertEqual(deg.expected_degradation, 0.0)


class TestLossAnalysisEngine(unittest.TestCase):
    def test_compute_loss_analysis(self):
        # Mock lifetime record
        # Possible gen = 10,000 kWh
        # Gen = 8,000 kWh
        # Grid failure = 1,000 kWh
        # Curtailment = 500 kWh
        # Machine loss = 500 kWh
        # Grid loss = Grid Failure + Curtailment = 1500 kWh
        record = LifetimePlantRecord(
            generation=8000.0,
            irradiation=150000.0,
            grid_failure=1000.0,
            curtailment=500.0,
            grid_loss=1500.0,  # Grid Failure + Curtailment is grouped
            machine_loss=500.0,
            total_generation=8000.0,
            total_possible_generation=10000.0,
            days=365,
        )
        
        loss_res = compute_loss_analysis(record)
        self.assertEqual(loss_res.total_loss_kwh, 2000.0)
        self.assertEqual(loss_res.total_loss_percentage, 20.0)
        
        # Grid failure: 1000 kWh (10%)
        # Curtailment: 500 kWh (5%)
        # Machine loss: 500 kWh (5%)
        categories = {cat.category: cat for cat in loss_res.categories}
        self.assertEqual(categories["Grid Failure"].loss_kwh, 1000.0)
        self.assertEqual(categories["Grid Failure"].loss_percentage, 10.0)
        self.assertEqual(categories["Curtailment"].loss_kwh, 500.0)
        self.assertEqual(categories["Curtailment"].loss_percentage, 5.0)
        self.assertEqual(categories["Machine Loss"].loss_kwh, 500.0)
        self.assertEqual(categories["Machine Loss"].loss_percentage, 5.0)


class TestAlertRecommendationEngine(unittest.TestCase):
    def setUp(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.db.database import Base
        from app.db.models import Plant, Inverter, DailyRecord, Alert, Recommendation
        from datetime import date

        # Setup in-memory database
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        Session = sessionmaker(bind=self.engine)
        self.db = Session()

        # Insert a test plant
        self.plant = Plant(
            name="Alpha Solar",
            location="Anuradhapura",
            country="Sri Lanka",
            installed_dc_capacity_mw=12.5,
            installed_ac_capacity_mw=10.0,
            commission_date=date(2023, 1, 15),
            number_of_blocks=1,
            inverter_type="central",
            number_of_inverters=1,
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
            notes="Alert testing plant"
        )
        self.db.add(self.plant)
        self.db.commit()
        self.db.refresh(self.plant)

        # Insert inverter
        self.inverter = Inverter(plant_id=self.plant.id, name="INV-01", block_name="Block A")
        self.db.add(self.inverter)
        self.db.commit()
        self.db.refresh(self.inverter)

    def tearDown(self):
        self.db.close()

    def test_generate_alerts_and_recommendations_healthy(self):
        from app.engines.health_alerts import generate_alerts_and_recommendations
        from app.db.models import DailyRecord, Alert, Recommendation
        from datetime import date

        # Create healthy daily records:
        # Generation = 15,000 kWh, Irradiation = 550 Wh/m² (equivalent to 5.5 kWh/m²)
        # With area=55000, eff=21.1%, hours=5.5, expected denominator is:
        # Denominator = 550 * 55000 * 0.211 * 5.5 / 1000 = 35122.6 kWh
        # Wait, if generation is 28,000 kWh:
        # PR = 28000 / 35122.6 * 100 = 79.72% (close to expected 78.5%)
        # Availability is 100%
        rec = DailyRecord(
            inverter_id=self.inverter.id,
            record_date=date(2023, 5, 1),
            irradiation=550.0,
            generation=28000.0,
            grid_failure=0.0,
            curtailment=0.0,
            grid_loss=0.0,
            machine_loss=0.0,
            total_generation=28000.0,
            total_possible_generation=28000.0
        )
        self.db.add(rec)
        self.db.commit()

        generate_alerts_and_recommendations(self.db, self.plant.id)

        alerts = self.db.query(Alert).filter(Alert.plant_id == self.plant.id).all()
        recs = self.db.query(Recommendation).filter(Recommendation.plant_id == self.plant.id).all()

        # Should generate a default System Health info alert and low priority recommendation
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].severity, "info")
        self.assertEqual(alerts[0].category, "System Health")

        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0].priority, "low")
        self.assertEqual(recs[0].category, "Operations")

    def test_generate_alerts_and_recommendations_unhealthy(self):
        from app.engines.health_alerts import generate_alerts_and_recommendations
        from app.db.models import DailyRecord, Alert, Recommendation
        from datetime import date

        # Create unhealthy daily records (low PR, high machine loss, low availability)
        # Gen = 10,000 kWh, Possible = 15,000 kWh (5,000 machine loss)
        rec = DailyRecord(
            inverter_id=self.inverter.id,
            record_date=date(2023, 5, 1),
            irradiation=550.0,
            generation=10000.0,
            grid_failure=0.0,
            curtailment=0.0,
            grid_loss=0.0,
            machine_loss=5000.0,
            total_generation=10000.0,
            total_possible_generation=15000.0
        )
        self.db.add(rec)
        self.db.commit()

        generate_alerts_and_recommendations(self.db, self.plant.id)

        alerts = self.db.query(Alert).filter(Alert.plant_id == self.plant.id).all()
        recs = self.db.query(Recommendation).filter(Recommendation.plant_id == self.plant.id).all()

        # Should generate Performance Ratio shortfall alert, Machine Loss alert, Availability alert
        categories = [a.category for a in alerts]
        self.assertIn("Performance Ratio", categories)
        self.assertIn("Machine Loss", categories)
        self.assertIn("Availability", categories)


if __name__ == "__main__":
    unittest.main()
