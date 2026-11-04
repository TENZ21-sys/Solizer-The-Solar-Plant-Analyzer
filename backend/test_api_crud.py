"""
SoliZer API REST End-to-End CRUD Integration Test Script.

Starts the FastAPI server locally, issues HTTP requests to perform CRUD
operations on plants, and verifies responses.
"""

import json
import os
import subprocess
import time
import urllib.request
import urllib.error
import sys

PORT = 8000
BASE_URL = f"http://127.0.0.1:{PORT}/api/plants"


def request_json(url, data=None, method="GET"):
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        
    try:
        with urllib.request.urlopen(req, data=body, timeout=5) as response:
            if response.status == 204:
                return None
            res_body = response.read().decode("utf-8")
            return json.loads(res_body)
    except urllib.error.HTTPError as e:
        err_content = e.read().decode("utf-8")
        print(f"   HTTP Error {e.code}: {err_content}")
        raise e
    except Exception as e:
        print(f"   Connection Error: {e}")
        raise e


def run_integration_test():
    print("=== STARTING API INTEGRATION TEST ===")
    
    # 1. Start the uvicorn server in a subprocess
    print("1. Starting FastAPI dev server...")
    python_exe = sys.executable
    server_process = subprocess.Popen(
        [python_exe, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Give the server a few seconds to boot up and check its health
    time.sleep(3)
    
    # Simple poll to check if server started successfully
    health_url = f"http://127.0.0.1:{PORT}/api/health"
    server_up = False
    for i in range(5):
        try:
            with urllib.request.urlopen(health_url, timeout=2) as r:
                if r.status == 200:
                    server_up = True
                    print("   FastAPI server is up and healthy!")
                    break
        except Exception:
            print("   Waiting for server...")
            time.sleep(1.5)
            
    if not server_up:
        print("!!! ERROR: Failed to start FastAPI server.")
        server_process.terminate()
        sys.exit(1)
        
    try:
        # 2. POST /api/plants/ - Create Plant
        print("2. Creating a new plant via POST...")
        new_plant_data = {
            "name": "Beta Solar Farm",
            "location": "Hambantota",
            "country": "Sri Lanka",
            "installed_dc_capacity_mw": 15.0,
            "installed_ac_capacity_mw": 12.0,
            "commission_date": "2024-05-10",
            "number_of_blocks": 3,
            "inverter_type": "string",
            "number_of_inverters": 12,
            "panel_manufacturer": "Trina Solar",
            "panel_model": "Vertex S+",
            "total_panel_area_sqm": 72000.0,
            "module_efficiency": 21.8,
            "daily_running_hours": 6.0,
            "annual_degradation_rate": 0.45,
            "expected_pr": 79.0,
            "expected_cuf": 19.1,
            "expected_availability": 98.8,
            "grid_operator": "CEB",
            "timezone": "Asia/Colombo",
            "has_weather_station": True,
            "has_string_monitoring": True,
            "notes": "E2E testing plant"
        }
        
        plant_res = request_json(f"{BASE_URL}/", data=new_plant_data, method="POST")
        plant_id = plant_res["id"]
        print(f"   Created plant ID: {plant_id}")
        assert plant_res["name"] == "Beta Solar Farm", "Name mismatch"
        assert plant_res["installed_dc_capacity_mw"] == 15.0, "DC capacity mismatch"
        
        # 3. GET /api/plants/ - List Plants
        print("3. Fetching plants list...")
        list_res = request_json(f"{BASE_URL}/", method="GET")
        print(f"   List response contains {len(list_res)} plants.")
        assert len(list_res) >= 1, "List response is empty"
        assert any(p["id"] == plant_id for p in list_res), "Created plant not in list"
        
        # 4. GET /api/plants/{id} - Get details
        print(f"4. Retrieving details for plant {plant_id}...")
        detail_res = request_json(f"{BASE_URL}/{plant_id}", method="GET")
        print(f"   Retrieved name: {detail_res['name']}")
        assert detail_res["panel_model"] == "Vertex S+", "Details mismatch"
        
        # 5. PUT /api/plants/{id} - Update details
        print(f"5. Updating plant {plant_id} efficiency and running hours...")
        update_data = {
            "module_efficiency": 22.5,
            "daily_running_hours": 6.5
        }
        update_res = request_json(f"{BASE_URL}/{plant_id}", data=update_data, method="PUT")
        print(f"   Updated efficiency: {update_res['module_efficiency']}%")
        assert update_res["module_efficiency"] == 22.5, "Efficiency update mismatch"
        assert update_res["daily_running_hours"] == 6.5, "Running hours update mismatch"
        
        # 6. DELETE /api/plants/{id} - Delete plant
        print(f"6. Deleting plant {plant_id}...")
        request_json(f"{BASE_URL}/{plant_id}", method="DELETE")
        print("   Deleted successfully (HTTP 204 received).")
        
        # 7. GET /api/plants/{id} - Verify 404
        print(f"7. Confirming plant {plant_id} no longer exists...")
        try:
            request_json(f"{BASE_URL}/{plant_id}", method="GET")
            print("!!! ERROR: Retrieve succeeded after deletion.")
            sys.exit(1)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print("   Confirmed (HTTP 404 received).")
            else:
                raise e
                
        print("=== API INTEGRATION TEST SUCCESSFUL ===")
        
    finally:
        print("Terminating FastAPI server process...")
        server_process.terminate()
        try:
            server_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            server_process.kill()


if __name__ == "__main__":
    run_integration_test()
