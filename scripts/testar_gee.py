"""Diagnostic: checks that the Earth Engine service account can read HLS.

Run from the repo root (WSL):
    uv run --with earthengine-api --env-file .env python scripts/testar_gee.py
"""

from datetime import datetime, timezone
import json
import os

import ee

chave = os.environ["SEUGADO_GEE_SERVICE_ACCOUNT_JSON"]
projeto = os.environ["SEUGADO_GEE_PROJECT"]
email = json.loads(chave)["client_email"]
print(f"1/4 conta: {email} | projeto: {projeto}")

ee.Initialize(ee.ServiceAccountCredentials(email=email, key_data=chave), project=projeto)
print("2/4 autenticou no Earth Engine")

hoje = datetime.now(timezone.utc)
ponto = ee.Geometry.Point([-36.09, -9.78])  # Sao Miguel dos Campos, AL
colecao = (
    ee.ImageCollection("NASA/HLS/HLSS30/v002")
    .filterBounds(ponto)
    .filterDate(ee.Date(hoje).advance(-30, "day"), ee.Date(hoje))
)
print(f"3/4 imagens HLSS30 nos ultimos 30 dias: {colecao.size().getInfo()}")

ultima = colecao.sort("system:time_start", False).first()
data = ee.Date(ultima.get("system:time_start")).format("YYYY-MM-dd").getInfo()
medias = ultima.select(["B4", "B8A"]).reduceRegion(ee.Reducer.mean(), ponto.buffer(60), 30).getInfo()
print(f"4/4 ultima imagem {data}: {medias}")
print("OK: a conta de servico funciona.")
