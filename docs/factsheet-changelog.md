# Factsheet servicio + Changelog

## Servicio (combinación M1+M2+M3)
API `app/main.py` + React `soc-ui/`, un :8000 en Docker. Cascada: M1 rankea → M2 confirma texto → M3 confirma contexto → regla `escalar iff malicious o (suspicious+block)`. Endpoints: `GET /health /info /stats /queue /incident/{id} /graph/vecindario`, `POST /score /score_batch /score_graph /explain /feedback`. Latencias: M1 <50ms, M2 ~100ms b-32, M3 ~s. Tests: `TestClient` con lifespan (sin él, stubs `loaded:false` — normal). Monitoreo: `/model/metrics` lee los `*_metrics.json`; `feedback.csv` acumula correcciones para re-entrenar. Riesgo conocido: pickles sklearn 1.7.2/xgboost 3.2.0 → Docker usa `python:3.10-slim` para igualar versiones.

## Changelog
- 2026-10-29: quitar Streamlit + README 8 secciones + M4 multi-label (notebook) + SOTA ATT&CK (TRAM/SciBERT/TwoStage, 2 PDFs en papers/).
- 2026-10-28: paper sin TODOs + 4 figuras + `python:3.10-slim` + README/doc end-to-end + EDA completo + datasheet/model-cards.
- 2026-10-27: M3 entrenado (F1 0.7186).
- 2026-10-23: M2 entrenado (F1 0.7084) + variantes MLflow.
- 2026-10-22: M1 entrenado (F1 0.5991) + API + paper draft + figuras placeholder.
