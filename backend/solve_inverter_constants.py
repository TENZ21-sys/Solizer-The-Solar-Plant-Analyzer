import sqlite3

conn = sqlite3.connect('data/solizer.db')
c = conn.cursor()

# Get each inverter's name, total generation, and total irradiation from database
c.execute("""
    select 
        i.name,
        sum(d.generation) as gen,
        sum(d.irradiation) as irr
    from inverters i
    join daily_records d on d.inverter_id = i.id
    group by i.id
    order by i.name
""")
db_inverters = c.fetchall()

# Report PRs for 2023-2024 from Table 3
report_prs = {
    'B1 inv 1': 81.01,
    'B1 inv 2': 80.99,
    'B2 inv 1': 80.45,
    'B2 inv 2': 81.67,
    'B3 inv 1': 81.60,
    'B3 inv 2': 79.87,
    'B4 inv 1': 81.18,
    'B4 inv 2': 81.17,
    'B5 inv 1': 80.88,
    'B5 inv 2': 78.82
}

# The sheet names in Excel were 'B1 inv 1', etc., which were mapped to inverter names.
# Let's clean report keys to match db names or vice versa.
print(f"{'Inverter Name':15} | {'Gen (kWh)':12} | {'Irr (raw)':12} | {'Report PR (%)':13} | {'Implicit Factor K':15}")
print("-" * 80)

for name, gen, irr in db_inverters:
    # Clean the name to find in report_prs
    cleaned_name = name.strip()
    # Let's map 'B1 inv 1' to the database inverter name (e.g. 'B1 inv 1' or 'B1-I1')
    # If the database inverter names are the sheet names, let's find the matching key
    matching_key = None
    for k in report_prs.keys():
        # Match 'B1 inv 1' with 'B1 inv 1'
        if k.replace(' ', '').replace('inv', '').replace('-', '').lower() == cleaned_name.replace(' ', '').replace('inv', '').replace('-', '').lower():
            matching_key = k
            break
            
    if matching_key:
        pr = report_prs[matching_key]
        # PR = Gen / (Irr_kWh_m2 * K) * 100 => K = Gen / (Irr_kWh_m2 * PR) * 100
        # Irr_raw is Wh/m2 daily. Sum of Irr_raw is over 366 days.
        # Irr_kWh_m2 = Irr_raw / 100.
        irr_kwh = irr / 100.0
        k_factor = (gen * 100.0) / (irr_kwh * pr)
        print(f"{name:15} | {gen:12.1f} | {irr:12.1f} | {pr:13.2f} | {k_factor:15.4f}")
    else:
        print(f"No match for {name}")

conn.close()
