"""SFG Web GUI - FastAPI 入口。"""
import sys
import os

_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from web.api.devices import router as devices_router
from web.api.templates import router as templates_router
from web.api.experiments import router as experiments_router
from web.api.calibration import router as calibration_router
from web.api.ws import router as ws_router

app = FastAPI(title="SFG Control Panel", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(devices_router, prefix="/api")
app.include_router(templates_router, prefix="/api")
app.include_router(experiments_router, prefix="/api")
app.include_router(calibration_router, prefix="/api")
app.include_router(ws_router)

_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")


def run(host: str = "0.0.0.0", port: int = 8080):
    import uvicorn

    print(f"\n  SFG Panel -> http://localhost:{port}\n")
    uvicorn.run("web.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run()
