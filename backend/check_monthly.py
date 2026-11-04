import sqlite3
from datetime import datetime

conn = sqlite3.connect('data/solizer.db')
c = conn.cursor()

c.execute("""
    select 
        strftime('%Y-%m', record_date) as ym,
        sum(generation),
        sum(irradiation),
        sum(grid_failure),
        sum(curtailment),
        sum(grid_loss),
        sum(machine_loss),
        sum(total_possible_generation)
    from daily_records
    group by ym
    order by ym
""")
rows = c.fetchall()

print(f"{'Year-Month':10} | {'Gen (MWh)':10} | {'Irr (kWh/m2)':12} | {'GF (MWh)':10} | {'Curt (MWh)':10} | {'GL (MWh)':10} | {'ML (MWh)':10} | {'Possible (MWh)':15}")
print("-" * 110)

for row in rows:
    ym = row[0]
    gen = row[1] / 1000.0
    irr = row[2] / 1000.0
    gf = row[3] / 1000.0
    curt = row[4] / 1000.0
    gl = row[5] / 1000.0
    ml = row[6] / 1000.0
    pos = row[7] / 1000.0
    print(f"{ym:10} | {gen:10.1f} | {irr:12.1f} | {gf:10.1f} | {curt:10.1f} | {gl:10.1f} | {ml:10.1f} | {pos:15.1f}")

conn.close()
