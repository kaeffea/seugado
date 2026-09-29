"""SeuGado API application.

Run with:
    uv run uvicorn seugado.api.main:app --app-dir src --reload
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from seugado.api import (
    rotas_cultivares,
    rotas_fazenda,
    rotas_lotes,
    rotas_piquetes,
    rotas_plano,
    rotas_telegram,
)

app = FastAPI(title="SeuGado API", version="0.1.0")

cors_origins_env = os.environ.get("SEUGADO_CORS_ORIGINS", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins_env.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/saude")
def saude() -> dict[str, bool]:
    """Return API health status."""
    return {"ok": True}


app.include_router(rotas_cultivares.router)
app.include_router(rotas_fazenda.router)
app.include_router(rotas_lotes.router)
app.include_router(rotas_piquetes.router)
app.include_router(rotas_plano.router)
app.include_router(rotas_telegram.router)
