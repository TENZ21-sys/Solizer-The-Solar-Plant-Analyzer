import docx

doc = docx.Document('../Example report .docx')
print("Total tables:", len(doc.tables))
for idx, table in enumerate(doc.tables):
    print(f"\n--- Table {idx+1} ---")
    for r_idx, row in enumerate(table.rows):
        cells = [c.text.strip().replace('\n', ' ') for c in row.cells]
        print(f"Row {r_idx}: {cells}")
