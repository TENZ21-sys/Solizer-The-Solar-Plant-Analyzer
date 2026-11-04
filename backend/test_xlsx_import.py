"""
SoliZer XLSX Import Integration Test Script.

Sets up a test plant with 10 configured inverters, starts the backend server,
uploads the Example Excel file, and verifies the database entries.
"""

import json
import os
import subprocess
import time
import urllib.request
import urllib.error
import sys

PORT = 8000
PLANT_URL = f"http://127.0.0.1:{PORT}/api/plants"


def run_xlsx_import_test():
    print("=== STARTING XLSX IMPORT TEST ===")
    
    # 1. Start the uvicorn server in a subprocess
    print("1. Starting FastAPI dev server...")
    python_exe = sys.executable
    server_process = subprocess.Popen(
        [python_exe, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    time.sleep(3)
    
    # 2. Wait for server health
    health_url = f"http://127.0.0.1:{PORT}/api/health"
    server_up = False
    for _ in range(5):
        try:
            with urllib.request.urlopen(health_url, timeout=2) as r:
                if r.status == 200:
                    server_up = True
                    print("   FastAPI server is up!")
                    break
        except Exception:
            time.sleep(1.5)
            
    if not server_up:
        print("!!! ERROR: Failed to start FastAPI server.")
        server_process.terminate()
        sys.exit(1)
        
    try:
        # 3. Create a Plant with 10 configured inverters
        print("3. Creating a test plant with 10 inverters...")
        plant_data = {
            "name": "Import Test Plant",
            "location": "Jaffna",
            "country": "Sri Lanka",
            "installed_dc_capacity_mw": 10.0,
            "installed_ac_capacity_mw": 8.5,
            "commission_date": "2023-01-01",
            "number_of_blocks": 2,
            "inverter_type": "string",
            "number_of_inverters": 10,  # Matches the 10 sheets in the Excel file
            "panel_manufacturer": "JA Solar",
            "panel_model": "JAM72-540",
            "total_panel_area_sqm": 50000.0,
            "module_efficiency": 21.0,
            "daily_running_hours": 5.5,
            "annual_degradation_rate": 0.5,
            "expected_pr": 78.0,
            "expected_cuf": 18.5,
            "expected_availability": 98.0,
            "grid_operator": "CEB",
            "timezone": "Asia/Colombo",
            "has_weather_station": True,
            "has_string_monitoring": False,
            "notes": "XLSX parser verification plant"
        }
        
        req = urllib.request.Request(f"{PLANT_URL}/", method="POST")
        req.add_header("Content-Type", "application/json")
        body = json.dumps(plant_data).encode("utf-8")
        
        with urllib.request.urlopen(req, data=body) as r:
            plant_res = json.loads(r.read().decode("utf-8"))
            plant_id = plant_res["id"]
            
        print(f"   Created plant ID: {plant_id}")
        
        # 4. Load Example xlsx file and construct multipart form upload
        xlsx_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Example xlsx file.xlsx")
        print(f"4. Reading Excel file from: {os.path.abspath(xlsx_path)}...")
        with open(xlsx_path, "rb") as f:
            file_bytes = f.read()
            
        boundary = "----WebKitFormBoundaryE2ESolizerImportBoundary"
        multipart_data = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="Example xlsx file.xlsx"\r\n'
            f"Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n"
        ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
        
        # 5. POST to /api/plants/{id}/import
        import_url = f"{PLANT_URL}/{plant_id}/import?import_type=multi_sheet"
        print(f"5. Uploading file to: {import_url}...")
        req = urllib.request.Request(import_url, method="POST")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        
        with urllib.request.urlopen(req, data=multipart_data) as r:
            import_res = json.loads(r.read().decode("utf-8"))
            
        print("   Upload completed! Response:")
        print(json.dumps(import_res, indent=2))
        
        assert import_res["is_valid"] is True, "Excel validation failed!"
        assert import_res["total_rows"] > 0, "No rows processed"
        assert import_res["valid_rows"] == import_res["total_rows"], "Some rows were rejected"
        
        # 6. Verify in the database directly or via API endpoint
        # Let's call GET /api/plants/{id}/inverters to verify inverters were created and named properly
        print("6. Verifying created inverters via API...")
        inverters_url = f"{PLANT_URL}/{plant_id}/inverters"
        with urllib.request.urlopen(inverters_url) as r:
            inverters_res = json.loads(r.read().decode("utf-8"))
            
        print(f"   Inverters in database: {[inv['name'] for inv in inverters_res]}")
        assert len(inverters_res) == 10, f"Expected 10 inverters, got {len(inverters_res)}"
        
        print("=== XLSX IMPORT TEST SUCCESSFUL ===")
        
    finally:
        print("Terminating FastAPI server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            server_process.kill()


if __name__ == "__main__":
    run_xlsx_import_test()
