# Deteccion-triage-alertas-soc-2m-eventos

Triage de alertas SOC sobre **2,011,674 eventos reales** (`witfoo/precinct6-cybersecurity` v2.1.0): clasifica cada evento en **benign / suspicious / malicious** y lo sirve en una consola SOC (cola por riesgo, cadena del incidente, cobertura MITRE).

**Resultado:** M1 tabular F1-macro **0.599** (malicious R 0.00) → M2 texto **0.708** (malicious R 0.97) → M3 grafo **0.719** (malicious R 0.96). La cascada M1→M2→M3 convierte el fallo tabular en arquitectura.

Paper IEEE: [`reports/paper.pdf`](reports/paper.pdf) · Documentación completa: [`docs/documentacion_end_to_end.md`](docs/documentacion_end_to_end.md) · Glosario no-técnico: [`docs/glosario_soc_no_tecnico.md`](docs/glosario_soc_no_tecnico.md)

## Arquitectura

```
Cassandra/Precinct 2M eventos → sanitize 4 capas → 261 lead rules → signals + GraphML + reports
        → M1 tabular (rankea) → M2 texto (confirma) → M3 vecindario ±5min (cadena) → fusión → consola
        → FastAPI :8000 (/score, /queue, /incident, /score_graph) → React soc-ui + Streamlit fallback
```

## Paso a paso para correrlo

Requisitos: Python ≥3.10 + `uv`, o Docker. Los parquets (`data/signals/signals.parquet` 117MB, `data/graph/*`) **no van en git** — descárgalos de HuggingFace (ver abajo).

### 1. Clonar + datos

```powershell
git clone https://github.com/nicothinn/Deteccion-triage-alertas-soc-2m-eventos.git
cd Deteccion-triage-alertas-soc-2m-eventos
uv sync
# descargar parquets a data/signals/ y data/graph/ desde:
# https://huggingface.co/datasets/witfoo/precinct6-cybersecurity
#   signals/signals.parquet, signals/incident_signals.parquet,
#   graph/nodes.parquet, graph/edges-00000.parquet, graph/attack_reports.parquet
```

### 2. API local (modelos ya entrenados en `models/m*.pkl`)

```powershell
uv run uvicorn app.main:app --reload
# http://127.0.0.1:8000/health  → 3 modelos loaded:true
# http://127.0.0.1:8000/        → consola web
```

### 3. Docker (recomendado para la demo: API + web en un :8000)

```powershell
docker build -t soc-precinct6 .
docker run -p 8000:8000 soc-precinct6
# o: docker compose up --build
```

### 4. Re-entrenar (mismo protocolo temporal 80/20 para los 3)

```powershell
uv run python experiments/m1_tabular/train.py --n 200000   # → models/m1.pkl + m1_metrics.json
uv run python experiments/m2_texto/train.py --n 30000      # → models/m2.pkl (TF-IDF 5k + XGBoost)
uv run python experiments/m3_grafo/train.py --n 30000      # → models/m3.pkl (vecindario ±5min + XGBoost)
```

### 5. Streamlit fallback (si no hay Node) + React dev

```powershell
uv run streamlit run app/streamlit_app.py
cd soc-ui; npm ci; npm run dev
```

### 6. Paper

```powershell
pdflatex paper.tex  # en reports/ (requiere MiKTeX/TeXLive, figuras en reports/figures/)
```

## Probar la API

```powershell
# salud + métricas
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/model/metrics
# puntuar (cascada M1+M2, triage escalar/monitorear)
@{message_type="firewall_action"; action="block"; message="exploit T1190 test"} |
  ConvertTo-Json | Invoke-RestMethod -Uri http://127.0.0.1:8000/score -Method Post -ContentType "application/json"
# grafo (requiere artifact_id real de signals.parquet)
Invoke-RestMethod -Uri "http://127.0.0.1:8000/score_graph" -Method Post -ContentType "application/json" -Body '{"artifact_id":"<id>"}'
```

Endpoints: `GET /health /info /stats /queue?label&limit /incident/{id} /graph/vecindario?node` · `POST /score /score_batch /score_graph /explain /feedback`.

## Resultados (test temporal, sin shuffle)

| Modelo | F1-macro | malicious P/R/F1 | PR-AUC mal | recall@1%FPR | train/test |
|---|---|---|---|---|---|
| M1 tabular LightGBM | **0.5991** | 0.0507 / 0.0045 / 0.0082 | 0.3023 | — | 112848 / 28212 |
| M2 TF-IDF 5k + XGBoost | **0.7084** | 0.7905 / 0.9698 / 0.8711 | 0.8261 | 0.0813 | 24000 / 6000 |
| M3 vecindario ±5min + XGBoost | **0.7186** | 0.7946 / 0.9620 / 0.8703 | 0.8154 | 0.0376 | 24000 / 6000 |

Lectura: M1 recupera suspicious (R 0.96) pero pierde malicious; M2/M3 cazan malicious (R ~0.97) a costa de suspicious (R 0.16/0.19). Ver [`reports/paper.pdf`](reports/paper.pdf) sec 5-6.

## Estructura (árbol)

```
.                                   # raíz: Dockerfile, compose.yml, pyproject.toml, uv.lock
├── app/                            # FastAPI :8000 + Streamlit fallback
│   ├── main.py                     # /health /score /queue /incident /score_graph /explain /feedback
│   ├── streamlit_app.py            # fallback sin Node
│   └── pages/                      # 02_Incidente.py, 03_Cobertura.py
├── soc-ui/                         # React+TS (Cola/Incidente/Grafo/Cobertura/Lab/Panorama)
│   └── src/pages/                  # Queue.tsx Incident.tsx Graph.tsx Coverage.tsx Lab.tsx Panorama.tsx
├── src/
│   ├── dataset.py                  # carga local parquet
│   ├── explorar.py                 # util EDA rápido
│   └── eda_report.py               # EDA completo → reports/eda/ (checklist 2026)
├── experiments/
│   ├── m1_tabular/train.py         # LightGBM tabular → models/m1.pkl
│   ├── m2_texto/train.py           # TF-IDF 5k + XGBoost → models/m2.pkl
│   ├── m3_grafo/train.py           # vecindario ±5min + XGBoost → models/m3.pkl
│   └── m1_tabular/leaderboard.csv  # 8 variantes MLflow
├── models/                         # m*.pkl NO en git · m*_metrics.json + m*_meta.json sí
├── data/                           # parquets NO en git (ver §1)
│   ├── signals/ + graph/ + build/ + reference/
│   └── README_HF.md                # data card original WitFoo
├── notebooks/
│   ├── eda_precinct6.ipynb         # EDA inicial (12 secciones)
│   └── m1_variants_mlflow.ipynb    # 8 variantes × F1/F2/F3
├── reports/
│   ├── paper.tex / paper.pdf       # IEEE 3 pp
│   ├── figures/                    # 4 PDFs (labels, temporal, confusion, architecture)
│   └── eda/                        # resumen_eda.md + diccionario_datos.csv (generado)
├── docs/                           # índice abajo
└── papers/                         # PDFs locales arXiv (NO en git, ver links)
```

## Índice de documentación

| Quiero... | Lee |
|---|---|
| Entenderlo todo end-to-end (recomendado) | [`docs/documentacion_end_to_end.md`](docs/documentacion_end_to_end.md) |
| No soy técnico | [`docs/glosario_soc_no_tecnico.md`](docs/glosario_soc_no_tecnico.md) |
| Qué datos son y sus límites | [`docs/datasheet.md`](docs/datasheet.md) (Gebru) + [`reports/eda/resumen_eda.md`](reports/eda/resumen_eda.md) + [`reports/eda/diccionario_datos.csv`](reports/eda/diccionario_datos.csv) |
| Qué hace cada modelo | [`docs/model-card-m1.md`](docs/model-card-m1.md) · [`docs/model-card-m2.md`](docs/model-card-m2.md) · [`docs/model-card-m3.md`](docs/model-card-m3.md) |
| Cómo se despliega y qué cambió | [`docs/factsheet-changelog.md`](docs/factsheet-changelog.md) |
| Consigna del curso | [`docs/guia_proyecto.md`](docs/guia_proyecto.md) (`contexto/course_project_guide.pdf`) |
| Literatura del primer entregable | [`docs/referencias_primer_entregable.md`](docs/referencias_primer_entregable.md) |
| Paper final | [`reports/paper.pdf`](reports/paper.pdf) ([`.tex`](reports/paper.tex)) |

## Referencias (todas)

Dataset y pipeline:
- https://huggingface.co/datasets/witfoo/precinct6-cybersecurity (2M, usar este)
- https://huggingface.co/datasets/witfoo/precinct6-cybersecurity-100m (114M, solo referencia escala)
- https://github.com/witfoo/dataset-from-precinct6 (sanitización 4 capas, 261 reglas)
- https://witfoo.com/research (Ben Irvine provenance-IDS, Empathetic Processing)

Marco:
- https://attack.mitre.org/ + https://mitre-attack.github.io/attack-navigator/
- https://attack.mitre.org/docs/ATTACK_Design_and_Philosophy_March_2020.pdf

Provenance-graph IDS (`papers/`):
- NODLINK NDSS24 https://arxiv.org/abs/2311.02331 · DOI https://doi.org/10.14722/ndss.2024.23204
- KnowHow NDSS26 https://arxiv.org/abs/2509.05698
- FLASH S&P24 https://doi.org/10.1109/sp54263.2024.00139 · código https://github.com/DART-Laboratory/Flash-IDS
- PROVSYN https://arxiv.org/abs/2506.06226 · OMNISEC https://arxiv.org/abs/2503.03108
- Survey https://arxiv.org/abs/2006.01722 · threaTrace https://arxiv.org/abs/2111.04333
- GraphSAGE https://arxiv.org/abs/1706.02216 · E-GraphSAGE https://arxiv.org/pdf/2103.16329v8
- PIDSMaker tutorial https://ubc-provenance.github.io/PIDSMaker/tutorial/

Imbalance / texto / simulación:
- Focal Loss https://arxiv.org/abs/1708.02002 · Cost-sensitive IDS https://arxiv.org/pdf/0807.2043
- PWG-IDS https://arxiv.org/abs/2110.03445 · TF-IDF vs MiniLM https://arxiv.org/abs/2407.06753
- CybORG https://arxiv.org/abs/2002.10667 · LightGBM Ke et al. NeurIPS 2017

## Limitaciones

Labels = correlación automática de Precinct (no verdad analista); T1190 domina malicious; ORG-0004 49.5%; `severity` 49% vacía por construcción. Detalle en paper sec Limitations.
