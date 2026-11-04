"""
SoliZer Intelligence Platform - FastAPI Backend Application
Main entry point and application factory.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, plants, data_import, analytics, alerts, reports
from app.db.database import engine, Base


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="SoliZer Intelligence Platform",
        description="Solar Plant Performance Analysis & Intelligence Platform",
        version="1.0.0-mvp",
    )

    # CORS middleware - allow frontend dev server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000", "tauri://localhost"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    # Mount static files folder for generated reports
    import os
    from fastapi.staticfiles import StaticFiles
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    reports_dir = os.path.join(appdata, "Solizer", "data", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    app.mount("/static-reports", StaticFiles(directory=reports_dir), name="reports")

    # Register API routers
    app.include_router(health.router, prefix="/api", tags=["Health"])
    app.include_router(plants.router, prefix="/api/plants", tags=["Plants"])
    app.include_router(data_import.router, prefix="/api/plants", tags=["Data Import"])
    app.include_router(analytics.router, prefix="/api/plants", tags=["Analytics"])
    app.include_router(alerts.router, prefix="/api/plants", tags=["Alerts"])
    app.include_router(reports.router, prefix="/api/plants", tags=["Reports"])


    # Serve Frontend UI
    import sys
    import webbrowser
    import threading
    import mimetypes
    
    # Register core mime types explicitly to avoid Windows registry corruption bugs
    mimetypes.add_type("application/javascript", ".js")
    mimetypes.add_type("text/css", ".css")
    mimetypes.add_type("image/svg+xml", ".svg")
    
    # Extract path for bundled frontend
    if hasattr(sys, '_MEIPASS'):
        frontend_dir = os.path.join(sys._MEIPASS, "frontend_dist")
    else:
        frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "dist")
        
    if os.path.exists(frontend_dir):
        from fastapi.responses import FileResponse, RedirectResponse
        from fastapi import HTTPException, Request
        
        @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
        async def serve_frontend(request: Request, full_path: str):
            # Exclude backend API and static reports from wildcard frontend routing
            if full_path.startswith("api") or full_path.startswith("static-reports"):
                if full_path.endswith("/"):
                    raise HTTPException(status_code=404, detail="Not Found")
                # Use 307 Temporary Redirect to preserve the HTTP method (GET, POST, PUT, etc.) and body
                return RedirectResponse(url=f"/{full_path}/", status_code=307)

            # For non-GET requests to frontend assets/pages, return 405 Method Not Allowed
            if request.method != "GET":
                raise HTTPException(status_code=405, detail="Method Not Allowed")

            file_path = os.path.join(frontend_dir, full_path)
            if os.path.isfile(file_path):
                media_type = None
                if file_path.endswith(".js"):
                    media_type = "application/javascript"
                elif file_path.endswith(".css"):
                    media_type = "text/css"
                elif file_path.endswith(".svg"):
                    media_type = "image/svg+xml"
                return FileResponse(file_path, media_type=media_type)
            return FileResponse(os.path.join(frontend_dir, "index.html"))

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    import sys
    import os
    import threading
    import time
    import webview
    
    # Force logging to app.log when frozen (as executable)
    is_frozen = getattr(sys, 'frozen', False)
    if is_frozen:
        log_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Solizer")
        os.makedirs(log_dir, exist_ok=True)
        log_file = open(os.path.join(log_dir, "app.log"), "w", encoding="utf-8", buffering=1)
        sys.stdout = log_file
        sys.stderr = log_file
        
    def start_server():
        try:
            print("Starting Uvicorn server...", flush=True)
            uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
        except Exception as e:
            print(f"Uvicorn server error: {e}", flush=True)

    # Start FastAPI in a background daemon thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Give the server a moment to bind to the port
    time.sleep(0.5)
    
    print("Creating WebView window...", flush=True)
    # Create pywebview window
    webview.create_window(
        title="Solize- The Solar Plant Analyzer",
        url="http://127.0.0.1:8000",
        width=1280,
        height=720,
        resizable=True
    )
    
    # Start the GUI loop
    webview.start()
    
    print("WebView window closed. Exiting application.", flush=True)
    sys.exit(0)

