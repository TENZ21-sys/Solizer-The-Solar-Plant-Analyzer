"""
Reverse-engineer the exact plant constants used in the Example report.

From Report:
  PR (%) = Generation (kWh) / (Irradiance(W/sqm) x Total Panel Area (sqm) x Module Efficiency x Running Hours per day) x 100%

Known from Report Table 1 (2023-2024):
  Total Generation = 20,362.3 MWh (this is Gen + Curtailment)
  Total Irradiation = 1,907.5 kWh/m2
  PR = 80.03%
  Plant capacity: DC 12.5 MW, AC 10 MW

From our DB:
  sum(generation) across all inverters = 20,109,834 kWh = 20,109.8 MWh
  sum(irradiation) per inverter (raw) = 190,748.9 => 1907.5 kWh/m2
  
Report says Total Generation = 20,362.3 MWh but our DB gen = 20,109.8 MWh.
Difference = 20,362.3 - 20,109.8 = 252.5 MWh
This is because Report Total Generation = Generation + Curtailment.
But curtailment is 0 in our data...

Wait - let's look at the report more carefully:
  Table 1: Total Generation = 20,362.3 MWh  
  Table 8: Generation = 20,109.8 MWh (Loss table)
  
So Table 1's "Total Generation" includes curtailment:
  Total Generation = Generation + Curtailment = 20,109.8 + 252.5 = 20,362.3 MWh
  
But our database has curtailment = 0! The curtailment must be part of another column.
Let's check the Excel data more carefully.
"""
import sqlite3
import pandas as pd

conn = sqlite3.connect('data/solizer.db')
c = conn.cursor()

# Check actual curtailment in DB
c.execute("select sum(curtailment), sum(grid_failure), sum(grid_loss), sum(machine_loss) from daily_records")
curt, gf, gl, ml = c.fetchone()
print(f"DB sums: Curtailment={curt}, Grid Failure={gf:.1f}, Grid Loss={gl:.1f}, Machine Loss={ml:.1f}")

# Let's look at the Excel directly for one inverter to check curtailment
xls = pd.ExcelFile('../Example xlsx file.xlsx')
df = pd.read_excel(xls, sheet_name=0)
df.columns = [str(c).strip() for c in df.columns]
print("\nSheet 1 columns:", df.columns.tolist())
print("\nCurtailment stats:")
print(df['Curtailment'].describe())
print(f"\nSum of Curtailment: {df['Curtailment'].sum()}")
print(f"Sum of Generation: {df['Generation'].sum()}")
print(f"Sum of Total Generation: {df['Total Generation'].sum()}")

# So Total Generation in Excel = Generation + Curtailment
# Let's verify
print(f"\nGeneration + Curtailment = {df['Generation'].sum() + df['Curtailment'].sum()}")
print(f"Total Generation col = {df['Total Generation'].sum()}")

# Now let's sum Total Generation across all 10 sheets
total_gen_all = 0
total_curt_all = 0
gen_only_all = 0
for sheet in xls.sheet_names:
    sdf = pd.read_excel(xls, sheet_name=sheet)
    sdf.columns = [str(c).strip() for c in sdf.columns]
    total_gen_all += sdf['Total Generation'].sum()
    gen_only_all += sdf['Generation'].sum()
    if 'Curtailment' in sdf.columns:
        total_curt_all += sdf['Curtailment'].sum()

print(f"\nAll sheets: Generation only = {gen_only_all:.1f} kWh = {gen_only_all/1000:.1f} MWh")
print(f"All sheets: Curtailment = {total_curt_all:.1f} kWh = {total_curt_all/1000:.1f} MWh")
print(f"All sheets: Total Generation = {total_gen_all:.1f} kWh = {total_gen_all/1000:.1f} MWh")
print(f"Report Table 1: Total Generation = 20,362.3 MWh")

# Now compute PR using Total Generation (Gen + Curtailment)
# PR = TotalGen_kWh / (Irr_raw_sum * K) * 100 = 80.03
# K = TotalGen_kWh * 100 / (Irr_raw_sum * PR)
K = total_gen_all * 100 / (190748.9 * 80.03)
print(f"\nImplied K factor: {K:.6f}")
print(f"K * 190748.9 * 80.03 / 100 = {K * 190748.9 * 80.03 / 100:.1f} (should match total gen)")

# K should equal: Area * Eff * Hours / (some unit conversion)
# Let's try: K = Area * Eff(fraction) * Hours / 1000
# area=50000, eff=0.21, hours=5.5 => 50000*0.21*5.5/1000 = 57.75
# But we got K = different value. 
# The actual Vydexa plant has different specs than our test plant!
# We need to figure out the actual Area and Eff values.

# From the PR formula:
# PR(%) = Gen_kWh / (Irr_W_m2_sum * Area * Eff * Hours / 1000) * 100
# Irr_W_m2_sum = 190748.9 (daily W/m2 values summed)
# Wait, if irr values are daily averages in W/m2:
#   daily energy from irradiance per m2 = Irr_W_m2 * Hours * 3600 / 1,000,000 kWh? No...
#   Or Irr_W_m2 * Hours (W*hr) = Wh => / 1000 = kWh
# So: PR = Gen_kWh / (sum_daily_Irr_Wm2 * Area * Eff * Hours / 1000) * 100

# For the whole year for all inverters together:
# 80.03 = total_gen_all / (190748.9 * Area * Eff * Hours / 1000) * 100
# => Area * Eff * Hours = total_gen_all * 100 * 1000 / (190748.9 * 80.03)
AEH = total_gen_all * 100 * 1000 / (190748.9 * 80.03)
print(f"\nArea * Eff * Hours = {AEH:.2f}")
print(f"If Hours=5.5, Area*Eff = {AEH/5.5:.2f}")
print(f"If Eff=0.21, Area = {AEH/(5.5*0.21):.2f}")
print(f"If Eff=0.195, Area = {AEH/(5.5*0.195):.2f}")

# For per-inverter PR:
# PR_inv = Inv_Gen_kWh / (190748.9 * InvArea * Eff * Hours / 1000) * 100
# For B1 Inv 1: 81.01 = gen / (190748.9 * InvArea * Eff * Hours / 1000) * 100
# gen (Total Gen for B1 Inv 1) from report = 2024.7 MWh = 2,024,700 kWh
gen_b1i1 = 2024700
AEH_inv = gen_b1i1 * 100 * 1000 / (190748.9 * 81.01)
print(f"\nPer-inverter AEH = {AEH_inv:.2f}")
print(f"If Hours=5.5, InvArea*Eff = {AEH_inv/5.5:.2f}")
print(f"InvArea = TotalArea/10 = {AEH_inv/(5.5*0.21*10):.2f} (implies TotalArea)")

conn.close()
