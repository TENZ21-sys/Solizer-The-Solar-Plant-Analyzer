import sqlite3
import pandas as pd

conn = sqlite3.connect('data/solizer.db')

# Load all daily records for plant_id = 1
c = conn.cursor()
c.execute("select total_panel_area_sqm, module_efficiency, daily_running_hours from plants where id = 1")
area, eff, hours = c.fetchone()
print(f"Area: {area}, Eff: {eff}, Hours: {hours}")

query = """
    select 
        record_date,
        avg(irradiation) as irr,
        sum(generation) as gen,
        sum(total_possible_generation) as pos
    from daily_records
    group by record_date
    order by record_date
"""
df = pd.read_sql_query(query, conn)
df['record_date'] = pd.to_datetime(df['record_date'])
df['month'] = df['record_date'].dt.strftime('%Y-%m')

# PR = Gen_kWh / (Irr_Wh_m2 / 1000 * Area * Eff/100) * 100
df['target_gen'] = df['irr'] * area * eff / 10000.0
df['pr_daily'] = (df['gen'] / df['target_gen']) * 100.0

# Group by month and calculate:
monthly = df.groupby('month').agg(
    gen_sum=('gen', 'sum'),
    irr_sum=('irr', 'sum'),
    target_sum=('target_gen', 'sum'),
    pr_simple_avg=('pr_daily', 'mean'),
    days=('record_date', 'count')
).reset_index()

monthly['pr_weighted'] = (monthly['gen_sum'] / monthly['target_sum']) * 100.0

may_df = df[df['month'] == '2023-05']
print("May 2023 Daily Data Sample (first 5 rows):")
print(may_df[['record_date', 'gen', 'irr', 'pr_daily']].head(5))

print("\nMonthly Aggregations:")
for idx, r in monthly.iterrows():
    print(f"Month: {r['month']} | Gen: {r['gen_sum']/1000.0:.1f} MWh | Simple PR: {r['pr_simple_avg']:.2f}% | Weighted PR: {r['pr_weighted']:.2f}%")

conn.close()
