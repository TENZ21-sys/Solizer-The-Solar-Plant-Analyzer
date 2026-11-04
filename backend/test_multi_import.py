import sqlite3
import pandas as pd
import io
import shutil
import os
from datetime import date
from app.db.database import SessionLocal
from app.db.models import Plant, DailyRecord, Inverter
from app.services.parser import parse_and_validate_xlsx
from app.engines.health_alerts import generate_alerts_and_recommendations

def verify_incremental_import():
    db = SessionLocal()
    try:
        # Get plant ID 2
        plant = db.query(Plant).filter(Plant.id == 2).first()
        if not plant:
            print("Plant ID 2 not found!")
            return
            
        inverter_ids = [inv.id for inv in plant.inverters]
        
        # 1. Clear ALL existing daily records for plant 2 to start fresh
        print("1. Clearing all existing daily records for plant 2 to start fresh...")
        if len(inverter_ids) > 0:
            db.query(DailyRecord).filter(DailyRecord.inverter_id.in_(inverter_ids)).delete(synchronize_session=False)
            db.commit()
            
        print(f"   Daily records count after clearing: {db.query(DailyRecord).filter(DailyRecord.inverter_id.in_(inverter_ids)).count()}")
        
        # Load the example spreadsheet
        xlsx_path = "../Example xlsx file.xlsx"
        with open(xlsx_path, "rb") as f:
            file_bytes = f.read()
            
        # 2. First Import
        print("\n2. Performing first import of Example file...")
        result, records = parse_and_validate_xlsx(db, plant, file_bytes, "multi_sheet")
        print(f"   Parsed records: {len(records)}")
        
        if result.is_valid and len(records) > 0:
            new_dates = {rec.record_date for rec in records}
            date_strings = [d.isoformat() for d in new_dates]
            
            # Deleting existing matching dates (should be 0)
            db.query(DailyRecord).filter(
                DailyRecord.inverter_id.in_(inverter_ids),
                DailyRecord.record_date.in_(date_strings)
            ).delete(synchronize_session=False)
            db.commit()
            
            db.add_all(records)
            db.commit()
            
            first_import_count = db.query(DailyRecord).filter(DailyRecord.inverter_id.in_(inverter_ids)).count()
            print(f"   Daily records count after first import: {first_import_count}")
            assert first_import_count == len(records), "First import count mismatch!"
            
        # 3. Duplicate Import (should overwrite and keep count the same)
        print("\n3. Performing duplicate import (should overwrite and keep count the same)...")
        result2, records2 = parse_and_validate_xlsx(db, plant, file_bytes, "multi_sheet")
        if result2.is_valid and len(records2) > 0:
            new_dates2 = {rec.record_date for rec in records2}
            date_strings2 = [d.isoformat() for d in new_dates2]
            
            # Deleting existing matching dates
            db.query(DailyRecord).filter(
                DailyRecord.inverter_id.in_(inverter_ids),
                DailyRecord.record_date.in_(date_strings2)
            ).delete(synchronize_session=False)
            db.commit()
            
            db.add_all(records2)
            db.commit()
            
            dup_import_count = db.query(DailyRecord).filter(DailyRecord.inverter_id.in_(inverter_ids)).count()
            print(f"   Daily records count after duplicate import: {dup_import_count}")
            assert first_import_count == dup_import_count, "Record count changed on duplicate upload!"
            print("   [SUCCESS] Duplicate upload kept counts identical (overwritten).")
            
        # 4. Create fake second year data (offset dates by 1 year) and upload it
        print("\n4. Creating fake second year data (offset dates by 1 year)...")
        xls = pd.ExcelFile(xlsx_path)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name)
                # Parse and shift dates by 364 days (52 weeks) to avoid calendar collisions and preserve row uniqueness
                df['Date'] = pd.to_datetime(df['Date']) + pd.Timedelta(days=364)
                # Convert date column to string format to simulate normal Excel formatting
                df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
        fake_file_bytes = output.getvalue()
        
        print("   Importing fake second year data...")
        result_fake, records_fake = parse_and_validate_xlsx(db, plant, fake_file_bytes, "multi_sheet")
        print(f"   Parsed fake records: {len(records_fake)}")
        
        if result_fake.is_valid and len(records_fake) > 0:
            fake_dates = {rec.record_date for rec in records_fake}
            fake_date_strings = [d.isoformat() for d in fake_dates]
            
            # Deleting existing matching dates (should be 0)
            db.query(DailyRecord).filter(
                DailyRecord.inverter_id.in_(inverter_ids),
                DailyRecord.record_date.in_(fake_date_strings)
            ).delete(synchronize_session=False)
            db.commit()
            
            db.add_all(records_fake)
            db.commit()
            
            final_count = db.query(DailyRecord).filter(DailyRecord.inverter_id.in_(inverter_ids)).count()
            print(f"   Daily records count after fake second year import: {final_count}")
            # There are 2 overlapping days (April 29 and 30) between original and shifted 364-day dataset.
            # Total unique days = 366 + 366 - 2 = 730 days. Total records = 730 * 10 = 7300.
            assert final_count == 7300, f"Expected 7300 records, got {final_count}"
            print(f"   [SUCCESS] Multi-year data uploaded successfully! Total daily records in DB: {final_count}")
            
    finally:
        db.close()

if __name__ == "__main__":
    verify_incremental_import()
