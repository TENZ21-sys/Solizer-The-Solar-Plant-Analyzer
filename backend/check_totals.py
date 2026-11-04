import sqlite3

conn = sqlite3.connect('data/solizer.db')
c = conn.cursor()

# Get plant info
c.execute("select id, name, total_panel_area_sqm, module_efficiency, daily_running_hours, installed_dc_capacity_mw, installed_ac_capacity_mw from plants")
plant = c.fetchone()
print("Plant Specs:", plant)
if plant:
    plant_id, name, area, eff, hours, dc_mw, ac_mw = plant
    
    # Get sums of daily records
    c.execute("select sum(generation), sum(irradiation), sum(total_possible_generation), count(*) from daily_records")
    gen_sum, irr_sum, pos_gen_sum, count = c.fetchone()
    print("Sums: Gen =", gen_sum, "Irr =", irr_sum, "Pos Gen =", pos_gen_sum, "Count =", count)
    
    c.execute("select generation, irradiation from daily_records limit 5")
    print("Sample records (Gen, Irr):", c.fetchall())
    
    c.execute("select record_date, avg(irradiation), sum(generation) from daily_records group by record_date")
    daily_data = c.fetchall()
    plant_irr_sum = sum(row[1] for row in daily_data)
    plant_gen_sum = sum(row[2] for row in daily_data)
    print("Plant level sums: Gen =", plant_gen_sum, "Irr =", plant_irr_sum)
    
    # Let's calculate PR using different formulas
    # Formula A: PR = Gen_kWh / (Irr_kWh_m2 * Area * Eff/100) * 100
    pr_a = (plant_gen_sum) / (plant_irr_sum * area * (eff / 100.0)) * 100
    print("PR Formula A:", pr_a)
    
    # Formula B: PR = Gen_kWh / (Irr_kWh_m2 * Area * Eff/100 * Hours) * 100
    pr_b = (plant_gen_sum) / (plant_irr_sum * area * (eff / 100.0) * hours) * 100
    print("PR Formula B:", pr_b)

conn.close()
