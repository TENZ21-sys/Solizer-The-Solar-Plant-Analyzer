"""
SoliZer XLSX Import Parsing & Validation Engine.
"""

import io
from datetime import datetime, date
from typing import List, Tuple, Dict, Any, Optional
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from app.db.models import Plant, Inverter, DailyRecord
from app.schemas.import_schemas import ImportValidationResult, ValidationError


def normalize_headers(columns: pd.Index) -> List[str]:
    """Strip spaces and convert headers to lowercase."""
    return [str(col).strip().lower() for col in columns]


def find_column(headers: List[str], keywords: List[str]) -> Optional[int]:
    """Find the column index matching any of the keywords."""
    for keyword in keywords:
        kw = keyword.lower().strip()
        for idx, header in enumerate(headers):
            if kw in header:
                return idx
    return None


def parse_excel_date(val: Any) -> Optional[date]:
    """Flexibly parse a date value from Excel."""
    # pd.NaT is a subclass of datetime, so we must check it FIRST
    if pd.isna(val):
        return None
        
    if isinstance(val, (datetime, date)):
        if isinstance(val, datetime):
            return val.date()
        return val
        
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ("nan", "nat"):
        return None
        
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(val_str.split()[0], fmt).date()
        except (ValueError, IndexError):
            continue
            
    try:
        # Try pandas parser for fallback
        ts = pd.to_datetime(val_str)
        if pd.isna(ts):
            return None
        return ts.date()
    except Exception:
        return None


def parse_float(val: Any) -> float:
    """Safe parse float with nan fallback to 0.0. Rounds off extremely small values."""
    try:
        if pd.isna(val) or val is None:
            return 0.0
        v = float(val)
        if np.isnan(v):
            return 0.0
        # Round to 4 decimal places to ignore values like 0.0000XX
        v = round(v, 4)
        # Ensure exact zero for floating point noise near zero
        return 0.0 if v == 0.0 else v
    except (ValueError, TypeError):
        return 0.0


def parse_and_validate_xlsx(
    db: Session,
    plant: Plant,
    file_bytes: bytes,
    import_type: str = "multi_sheet"
) -> Tuple[ImportValidationResult, List[DailyRecord]]:
    """
    Parse an Excel workbook, validate rows, create/map inverters, and construct DailyRecord objects.
    """
    validation_errors: List[ValidationError] = []
    warnings: List[str] = []
    daily_records_to_insert: List[DailyRecord] = []
    
    try:
        xls = pd.ExcelFile(io.BytesIO(file_bytes))
    except Exception as e:
        return ImportValidationResult(
            is_valid=False,
            total_rows=0,
            valid_rows=0,
            errors=[ValidationError(row=1, column="File", message=f"Failed to open Excel workbook: {e}", value="")],
            warnings=[]
        ), []
        
    sheets = xls.sheet_names
    print(f"Excel sheets found: {sheets}")
    
    # 1. Topology Validation
    if import_type == "multi_sheet":
        # Identify valid sheets by checking required columns
        valid_sheets = []
        for sheet_name in sheets:
            try:
                df_test = pd.read_excel(xls, sheet_name=sheet_name, nrows=0)
                headers = normalize_headers(df_test.columns)
                if (find_column(headers, ["date", "time", "timestamp"]) is not None and
                    find_column(headers, ["irradiation", "irr", "radiation", "poa"]) is not None and
                    find_column(headers, ["total generation", "generation", "gen", "energy"]) is not None):
                    valid_sheets.append(sheet_name)
            except Exception:
                pass
                
        if len(valid_sheets) == 0:
            return ImportValidationResult(
                is_valid=False,
                total_rows=0,
                valid_rows=0,
                errors=[ValidationError(row=1, column="Sheets", message="No valid data sheets found in workbook.", value="")],
                warnings=[]
            ), []
            
        # Dynamically update the plant's number of inverters
        if plant.number_of_inverters != len(valid_sheets):
            plant.number_of_inverters = len(valid_sheets)
            db.commit()
            
        sheets = valid_sheets
            
        # 2. Get or create inverters mapped sequentially
        inverters = db.query(Inverter).filter(Inverter.plant_id == plant.id).order_by(Inverter.id).all()
        
        # Ensure we have enough inverters created
        if len(inverters) < len(sheets):
            for i in range(len(inverters), len(sheets)):
                if len(sheets) == 1:
                    inv_name = "Total Plant Data"
                    block_name = "Plant"
                else:
                    inv_name = sheets[i]
                    block_name = f"Block {i // max(1, plant.number_of_blocks) + 1}"
                    
                inv = Inverter(
                    plant_id=plant.id,
                    name=inv_name,
                    block_name=block_name
                )
                db.add(inv)
            db.commit()
            inverters = db.query(Inverter).filter(Inverter.plant_id == plant.id).order_by(Inverter.id).all()
            
        # Map inverters and update their names
        for i, sheet_name in enumerate(sheets):
            if len(sheets) == 1:
                inverters[i].name = "Total Plant Data"
            else:
                inverters[i].name = sheet_name
        db.commit()
            
        inverter_map = {sheet_name: inverters[i] for i, sheet_name in enumerate(sheets)}
        
        total_rows_processed = 0
        total_valid_rows = 0
        
        # 3. Process each sheet
        for sheet_name in sheets:
            try:
                df = pd.read_excel(xls, sheet_name=sheet_name)
            except Exception as e:
                validation_errors.append(
                    ValidationError(row=1, column="Sheet", message=f"Failed to read sheet '{sheet_name}': {e}", value="")
                )
                continue
                
            headers = normalize_headers(df.columns)
            
            # Map columns
            date_idx = find_column(headers, ["date", "time", "timestamp"])
            irrad_idx = find_column(headers, ["irradiation", "irr", "radiation", "poa"])
            gen_idx = find_column(headers, ["total generation", "generation", "gen", "energy"])
            grid_fail_idx = find_column(headers, ["grid failure", "grid outage", "grid fail"])
            curtail_idx = find_column(headers, ["curtailment", "capped"])
            grid_loss_idx = find_column(headers, ["grid loss"])
            mach_loss_idx = find_column(headers, ["machine loss", "equipment loss"])
            
            # Verification of essential columns
            if date_idx is None:
                validation_errors.append(
                    ValidationError(row=1, column="Headers", message=f"Sheet '{sheet_name}' is missing a 'Date' column.", value="")
                )
                continue
            if gen_idx is None:
                validation_errors.append(
                    ValidationError(row=1, column="Headers", message=f"Sheet '{sheet_name}' is missing a 'Generation' column.", value="")
                )
                continue
            if irrad_idx is None:
                validation_errors.append(
                    ValidationError(row=1, column="Headers", message=f"Sheet '{sheet_name}' is missing an 'Irradiation' column.", value="")
                )
                continue
                
            inverter = inverter_map[sheet_name]
            
            # Parse rows
            for idx, row in df.iterrows():
                row_num = idx + 2  # 1-indexed + header row
                total_rows_processed += 1
                
                # Parse Date
                raw_date = row.iloc[date_idx]
                parsed_date = parse_excel_date(raw_date)
                if parsed_date is None:
                    validation_errors.append(
                        ValidationError(
                            row=row_num,
                            column="Date",
                            message=f"[{sheet_name}] Invalid date format or empty date cell.",
                            value=str(raw_date)
                        )
                    )
                    continue
                    
                # Parse values
                raw_gen = row.iloc[gen_idx]
                raw_irr = row.iloc[irrad_idx]
                
                gen = parse_float(raw_gen)
                irr = parse_float(raw_irr)
                
                # Check negatives
                if gen < 0:
                    validation_errors.append(
                        ValidationError(
                            row=row_num,
                            column="Generation",
                            message=f"[{sheet_name}] Generation cannot be negative.",
                            value=str(raw_gen)
                        )
                    )
                    continue
                if irr < 0:
                    validation_errors.append(
                        ValidationError(
                            row=row_num,
                            column="Irradiation",
                            message=f"[{sheet_name}] Irradiation cannot be negative.",
                            value=str(raw_irr)
                        )
                    )
                    continue
                    
                grid_fail = parse_float(row.iloc[grid_fail_idx]) if grid_fail_idx is not None else 0.0
                curtail = parse_float(row.iloc[curtail_idx]) if curtail_idx is not None else 0.0
                grid_loss = parse_float(row.iloc[grid_loss_idx]) if grid_loss_idx is not None else 0.0
                mach_loss = parse_float(row.iloc[mach_loss_idx]) if mach_loss_idx is not None else 0.0
                
                # Negatives validation for losses
                if any(v < 0 for v in (grid_fail, curtail, grid_loss, mach_loss)):
                    validation_errors.append(
                        ValidationError(
                            row=row_num,
                            column="Losses",
                            message=f"[{sheet_name}] Loss metrics cannot be negative.",
                            value=f"GF:{grid_fail}, C:{curtail}, GL:{grid_loss}, ML:{mach_loss}"
                        )
                    )
                    continue
                
                # Calculate totals
                # Possible Generation = Generation + Grid Loss + Machine Loss
                possible_gen = gen + grid_loss + mach_loss
                
                record = DailyRecord(
                    inverter_id=inverter.id,
                    record_date=parsed_date,
                    irradiation=irr,
                    generation=gen,
                    grid_failure=grid_fail,
                    curtailment=curtail,
                    grid_loss=grid_loss,
                    machine_loss=mach_loss,
                    total_generation=gen,
                    total_possible_generation=possible_gen
                )
                daily_records_to_insert.append(record)
                total_valid_rows += 1
                
        # Deduplicate or check warning for duplicate dates
        seen_dates: Dict[int, set] = {}
        duplicates_count = 0
        for record in daily_records_to_insert:
            inv_id = record.inverter_id
            rec_date = record.record_date
            if inv_id not in seen_dates:
                seen_dates[inv_id] = set()
            if rec_date in seen_dates[inv_id]:
                duplicates_count += 1
            else:
                seen_dates[inv_id].add(rec_date)
                
        if duplicates_count > 0:
            warnings.append(f"Found {duplicates_count} rows with duplicate dates for the same inverter. Only the last entry will be preserved in DB.")
            
        is_valid = len(validation_errors) == 0
        
        return ImportValidationResult(
            is_valid=is_valid,
            total_rows=total_rows_processed,
            valid_rows=total_valid_rows,
            errors=validation_errors[:100],  # cap at 100 errors to prevent flooding
            warnings=warnings
        ), daily_records_to_insert
        
    elif import_type == "single_sheet":
        # Single sheet mode
        # Expose a simple mapping where all columns are mapped to a single virtual inverter,
        # or grouped by an inverter column if present.
        # For simplicity, if there is only 1 inverter or a single sheet, we map it to the first inverter.
        inverters = db.query(Inverter).filter(Inverter.plant_id == plant.id).order_by(Inverter.id).all()
        if len(inverters) == 0:
            # Create a single default inverter
            inv = Inverter(plant_id=plant.id, name="Main Inverter", block_name="Block 1")
            db.add(inv)
            db.commit()
            inverters = [inv]
            
        inverter = inverters[0]
        
        try:
            df = pd.read_excel(xls, sheet_name=0)
        except Exception as e:
            return ImportValidationResult(
                is_valid=False,
                total_rows=0,
                valid_rows=0,
                errors=[ValidationError(row=1, column="Sheet", message=f"Failed to read sheet: {e}", value="")],
                warnings=[]
            ), []
            
        headers = normalize_headers(df.columns)
        
        date_idx = find_column(headers, ["date", "time", "timestamp"])
        irrad_idx = find_column(headers, ["irradiation", "irr", "radiation", "poa"])
        gen_idx = find_column(headers, ["total generation", "generation", "gen", "energy"])
        grid_fail_idx = find_column(headers, ["grid failure", "grid outage", "grid fail"])
        curtail_idx = find_column(headers, ["curtailment", "capped"])
        grid_loss_idx = find_column(headers, ["grid loss"])
        mach_loss_idx = find_column(headers, ["machine loss", "equipment loss"])
        
        if date_idx is None or gen_idx is None or irrad_idx is None:
            return ImportValidationResult(
                is_valid=False,
                total_rows=0,
                valid_rows=0,
                errors=[ValidationError(row=1, column="Headers", message="Workbook is missing required Date, Generation, or Irradiation columns.", value="")],
                warnings=[]
            ), []
            
        total_rows_processed = 0
        total_valid_rows = 0
        
        for idx, row in df.iterrows():
            row_num = idx + 2
            total_rows_processed += 1
            
            raw_date = row.iloc[date_idx]
            parsed_date = parse_excel_date(raw_date)
            if parsed_date is None:
                validation_errors.append(
                    ValidationError(row=row_num, column="Date", message="Invalid date format.", value=str(raw_date))
                )
                continue
                
            raw_gen = row.iloc[gen_idx]
            raw_irr = row.iloc[irrad_idx]
            
            gen = parse_float(raw_gen)
            irr = parse_float(raw_irr)
            
            if gen < 0 or irr < 0:
                validation_errors.append(
                    ValidationError(row=row_num, column="Values", message="Irradiation and Generation cannot be negative.", value=f"Gen:{raw_gen}, Irr:{raw_irr}")
                )
                continue
                
            grid_fail = parse_float(row.iloc[grid_fail_idx]) if grid_fail_idx is not None else 0.0
            curtail = parse_float(row.iloc[curtail_idx]) if curtail_idx is not None else 0.0
            grid_loss = parse_float(row.iloc[grid_loss_idx]) if grid_loss_idx is not None else 0.0
            mach_loss = parse_float(row.iloc[mach_loss_idx]) if mach_loss_idx is not None else 0.0
            
            # Possible Generation = Generation + Grid Loss + Machine Loss
            possible_gen = gen + grid_loss + mach_loss
            
            record = DailyRecord(
                inverter_id=inverter.id,
                record_date=parsed_date,
                irradiation=irr,
                generation=gen,
                grid_failure=grid_fail,
                curtailment=curtail,
                grid_loss=grid_loss,
                machine_loss=mach_loss,
                total_generation=gen,
                total_possible_generation=possible_gen
            )
            daily_records_to_insert.append(record)
            total_valid_rows += 1
            
        is_valid = len(validation_errors) == 0
        return ImportValidationResult(
            is_valid=is_valid,
            total_rows=total_rows_processed,
            valid_rows=total_valid_rows,
            errors=validation_errors[:100],
            warnings=warnings
        ), daily_records_to_insert
        
    else:
        return ImportValidationResult(
            is_valid=False,
            total_rows=0,
            valid_rows=0,
            errors=[ValidationError(row=1, column="Config", message=f"Unsupported import type: {import_type}", value="")],
            warnings=[]
        ), []


def parse_and_validate_csv(
    db: Session,
    plant: Plant,
    file_bytes: bytes,
) -> Tuple[ImportValidationResult, List[DailyRecord]]:
    """Parse and validate CSV monitoring data files."""
    validation_errors: List[ValidationError] = []
    warnings: List[str] = []
    daily_records_to_insert: List[DailyRecord] = []
    total_rows_processed = 0
    total_valid_rows = 0

    try:
        # Try utf-8 then latin-1
        try:
            df = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(io.BytesIO(file_bytes), encoding="latin-1")
    except Exception as e:
        return ImportValidationResult(
            is_valid=False,
            total_rows=0,
            valid_rows=0,
            errors=[ValidationError(row=1, column="File", message=f"Could not parse CSV file: {e}", value="")],
            warnings=[]
        ), []

    if df.empty:
        return ImportValidationResult(
            is_valid=False,
            total_rows=0,
            valid_rows=0,
            errors=[ValidationError(row=1, column="File", message="CSV file is empty.", value="")],
            warnings=[]
        ), []

    headers = normalize_headers(df.columns)
    date_idx = find_column(headers, ["date", "time", "timestamp", "day"])
    gen_idx = find_column(headers, ["generation", "gen", "yield", "energy", "active power", "kwh"])
    irrad_idx = find_column(headers, ["irrad", "solar", "radiation", "ghi", "poa", "w/m", "wh/m"])

    if date_idx is None or gen_idx is None or irrad_idx is None:
        missing = []
        if date_idx is None: missing.append("Date")
        if gen_idx is None: missing.append("Generation")
        if irrad_idx is None: missing.append("Irradiation")
        return ImportValidationResult(
            is_valid=False,
            total_rows=len(df),
            valid_rows=0,
            errors=[ValidationError(row=1, column="Headers", message=f"Missing essential columns: {', '.join(missing)}", value="")],
            warnings=[]
        ), []

    inv_idx = find_column(headers, ["inverter", "device", "inv", "unit", "block"])
    grid_fail_idx = find_column(headers, ["grid failure", "grid fail", "grid trip", "grid_failure"])
    curtail_idx = find_column(headers, ["curtail", "curtailment"])
    grid_loss_idx = find_column(headers, ["grid loss", "grid_loss"])
    mach_loss_idx = find_column(headers, ["machine loss", "inverter loss", "equipment loss", "mach_loss"])

    # Ensure plant inverters exist
    inverters_map: Dict[str, Inverter] = {}
    for inv in plant.inverters:
        inverters_map[inv.name.strip().lower()] = inv

    if not inverters_map:
        num_inv = max(plant.number_of_inverters, 1)
        for i in range(1, num_inv + 1):
            name = f"Inverter {i}"
            new_inv = Inverter(plant_id=plant.id, name=name, block_name="Block 1")
            db.add(new_inv)
        db.commit()
        for inv in plant.inverters:
            inverters_map[inv.name.strip().lower()] = inv

    default_inverter = next(iter(inverters_map.values()))

    for idx, row in df.iterrows():
        row_num = idx + 2
        total_rows_processed += 1

        raw_date = row.iloc[date_idx]
        parsed_date = parse_excel_date(raw_date)
        if parsed_date is None:
            validation_errors.append(
                ValidationError(row=row_num, column="Date", message="Invalid date format.", value=str(raw_date))
            )
            continue

        raw_gen = row.iloc[gen_idx]
        raw_irr = row.iloc[irrad_idx]
        gen = parse_float(raw_gen)
        irr = parse_float(raw_irr)

        if gen < 0 or irr < 0:
            validation_errors.append(
                ValidationError(row=row_num, column="Values", message="Irradiation and Generation cannot be negative.", value=f"Gen:{raw_gen}, Irr:{raw_irr}")
            )
            continue

        grid_fail = parse_float(row.iloc[grid_fail_idx]) if grid_fail_idx is not None else 0.0
        curtail = parse_float(row.iloc[curtail_idx]) if curtail_idx is not None else 0.0
        grid_loss = parse_float(row.iloc[grid_loss_idx]) if grid_loss_idx is not None else 0.0
        mach_loss = parse_float(row.iloc[mach_loss_idx]) if mach_loss_idx is not None else 0.0

        target_inv = default_inverter
        if inv_idx is not None:
            inv_val = str(row.iloc[inv_idx]).strip().lower()
            if inv_val in inverters_map:
                target_inv = inverters_map[inv_val]
            else:
                # Match partial or create if needed
                matched = next((inv for k, inv in inverters_map.items() if k in inv_val or inv_val in k), None)
                if matched:
                    target_inv = matched
                else:
                    new_inv = Inverter(plant_id=plant.id, name=str(row.iloc[inv_idx]).strip(), block_name="Block 1")
                    db.add(new_inv)
                    db.commit()
                    inverters_map[new_inv.name.strip().lower()] = new_inv
                    target_inv = new_inv

        total_gen = gen + curtail
        possible_gen = gen + grid_fail + curtail + grid_loss + mach_loss

        record = DailyRecord(
            inverter_id=target_inv.id,
            record_date=parsed_date,
            irradiation=irr,
            generation=gen,
            grid_failure=grid_fail,
            curtailment=curtail,
            grid_loss=grid_loss,
            machine_loss=mach_loss,
            total_generation=total_gen,
            total_possible_generation=possible_gen,
        )
        daily_records_to_insert.append(record)
        total_valid_rows += 1

    is_valid = len(validation_errors) == 0
    return ImportValidationResult(
        is_valid=is_valid,
        total_rows=total_rows_processed,
        valid_rows=total_valid_rows,
        errors=validation_errors[:100],
        warnings=warnings,
    ), daily_records_to_insert

