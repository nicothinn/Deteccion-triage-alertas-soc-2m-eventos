# Deteccion-triage-alertas-soc-2m-eventos

![Python 3.10](https://img.shields.io/badge/python-3.10-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-:8000-green) ![Docker](https://img.shields.io/badge/docker-ready-blue) ![Paper IEEE](https://img.shields.io/badge/paper-IEEE-lightgrey)

**Clasifica cada alerta de un SOC real en benign / suspicious / malicious y la sirve en una consola de triage (cola por riesgo, cadena del incidente, cobertura MITRE).**

Sobre **2,011,674 eventos reales** (`witfoo/precinct6-cybersecurity` v2.1.0): el baseline tabular llega a F1-macro 0.599 pero no ve lo malicioso (R 0.00); el texto (M2, 0.708) y el grafo de proveniencia (M3, 0.719) lo cazan (R ~0.97). La cascada M1→M2→M3 convierte el fallo tabular en arquitectura.

## 1. Estructura del Proyecto

```text
.
├── app/                            # Despliegue: API FastAPI en :8000
│   └── main.py                     # /health /score /queue /incident /score_graph /explain /feedback
├── soc-ui/                         # Frontend React+TS (Cola/Incidente/Grafo/Cobertura/Lab/Panorama)
│   └── src/pages/                  # Queue.tsx Incident.tsx Graph.tsx Coverage.tsx Lab.tsx Panorama.tsx
├── src/                            # Código fuente modular
│   ├── dataset.py                  # carga local parquet
│   ├── explorar.py                 # util EDA rápido
│   └── eda_report.py               # EDA completo → reports/eda/ (checklist 2026)
├── experiments/                    # Entrenamiento reproducible (mismo split temporal 80/20)
│   ├── m1_tabular/train.py         # LightGBM tabular → models/m1.pkl
│   ├── m2_texto/train.py           # TF-IDF 5k + XGBoost → models/m2.pkl
│   ├── m3_grafo/train.py           # vecindario ±5min + XGBoost → models/m3.pkl
│   └── m1_tabular/leaderboard.csv  # 8 variantes MLflow (F1/F2/F3 × lgbm/xgb/rf/logreg)
├── models/                         # Serializados: m*.pkl NO en git · m*_metrics.json + m*_meta.json sí
├── data/                           # Parquets NO en git (ver §3)
│   ├── signals/ + graph/ + build/ + reference/
│   └── README_HF.md                # data card original WitFoo
├── notebooks/                      # EDA y experimentación
│   ├── eda_precinct6.ipynb         # EDA inicial (12 secciones)
│   └── m1_variants_mlflow.ipynb    # 8 variantes × F1/F2/F3
├── reports/
│   ├── paper.tex / paper.pdf       # artículo IEEE (3 pp)
│   ├── figures/                    # 4 PDFs (labels, temporal, confusion, architecture)
│   └── eda/                        # resumen_eda.md + diccionario_datos.csv (generado)
├── docs/                           # índice en §8
├── papers/                         # PDFs arXiv locales (NO en git, ver links en §8)
├── Dockerfile                      # multi-stage: node build + python:3.10-slim
├── compose.yml                     # un servicio, :8000
├── pyproject.toml + uv.lock        # dependencias pineadas (uv)
└── README.md
```

## 2. Requisitos e Instalación

- **Python exacto: 3.10** (los pickles son sklearn 1.7.2 / xgboost 3.2.0; el Dockerfile usa `python:3.10-slim` para igualar versiones y evitar warnings de unpickle). O Docker.
- Los parquets (`signals.parquet` 117MB, `edges` 34MB, modelos `*.pkl`) **no están en el repo**.

```bash
git clone https://github.com/nicothinn/Deteccion-triage-alertas-soc-2m-eventos.git
cd Deteccion-triage-alertas-soc-2m-eventos
uv sync
# descargar parquets a data/signals/ y data/graph/ desde:
# https://huggingface.co/datasets/witfoo/precinct6-cybersecurity
#   signals/signals.parquet, signals/incident_signals.parquet,
#   graph/nodes.parquet, graph/edges-00000.parquet, graph/attack_reports.parquet
```

## 3. Datos (Data Source)

- **Origen:** [`witfoo/precinct6-cybersecurity`](https://huggingface.co/datasets/witfoo/precinct6-cybersecurity) v2.1.0 (Apache-2.0) + variante 114M [`precinct6-cybersecurity-100m`](https://huggingface.co/datasets/witfoo/precinct6-cybersecurity-100m) (solo referencia de escala). Generado con [`dataset-from-precinct6`](https://github.com/witfoo/dataset-from-precinct6) (sanitización 4 capas, 261 lead rules).
- **Features (38 por señal):** identidad (`org_id`, `artifact_id` = join key al grafo, `src/dst_ip`, `username`), fuente (`message_type` ≈40 valores, `stream_name`, `product/vendor_name`, `pipeline`), contenido (`action`, `severity` ≈49% vacía, `protocol`, `message_sanitized`), y labels Precinct (`attack_techniques/tactics`, `mo_name`, `suspicion_score`, `disposition`, `incident_ids`). Ventana live 2024-07-26 → 08-01, 4 orgs.
- **Target:** `label_binary` = benign 1,897,153 (94.31%) / suspicious 106,793 (5.31%) / malicious 7,728 (0.38%, leads in-window de 1,584 incidentes). IR benign:malicious ≈ 245:1. Labels = correlación automática Precinct (oráculo fuerte pero imperfecto, no verdad analista).
- **Almacenamiento:** parquets fuera del repo (ver §2). Mirrors locales en `data/` para no re-descargar. Diccionario autogenerado: [`reports/eda/diccionario_datos.csv`](reports/eda/diccionario_datos.csv).

## 4. Pipeline del Proyecto (Cómo ejecutarlo)

Scripts de producción (no solo notebooks), mismo protocolo temporal 80/20 en los 3:

```bash
# Paso 0: EDA completo reproducible (checklist OMSCS/Insper 2026)
uv run python src/eda_report.py            # → reports/eda/resumen_eda.md

# Paso 1: entrenar los 3 modelos
uv run python experiments/m1_tabular/train.py --n 200000   # → models/m1.pkl + m1_metrics.json
uv run python experiments/m2_texto/train.py --n 30000      # → models/m2.pkl (TF-IDF 5k + XGBoost)
uv run python experiments/m3_grafo/train.py --n 30000      # → models/m3.pkl (vecindario ±5min + XGBoost)

# Paso 2: evaluar (métricas a models/*_metrics.json + MLflow en experiments/mlruns)
# Paso 3: servir
uv run uvicorn app.main:app --reload      # http://127.0.0.1:8000/health
```

## 5. Resultados y Evaluación del Modelo

Test temporal futuro (sin shuffle). Métrica principal macro-F1 + PR-AUC por clase (accuracy es vacua: ≈94% con siempre-benign).

| Modelo | F1-macro | malicious P/R/F1 | PR-AUC mal | recall@1%FPR | train/test |
|---|---|---|---|---|---|
| Baseline M1 tabular LightGBM | **0.5991** | 0.0507 / 0.0045 / 0.0082 | 0.3023 | — | 112848 / 28212 |
| M2 TF-IDF 5k + XGBoost | **0.7084** | 0.7905 / 0.9698 / 0.8711 | 0.8261 | 0.0813 | 24000 / 6000 |
| M3 vecindario ±5min + XGBoost (final) | **0.7186** | 0.7946 / 0.9620 / 0.8703 | 0.8154 | 0.0376 | 24000 / 6000 |

Lectura: M1 recupera suspicious (R 0.96) pero colapsa en malicious; M2/M3 cazan malicious (R ~0.97) vía tokens T1190 / cadenas USER_ACTION, a costa de suspicious (R 0.16/0.19). Figuras en `reports/figures/`: `label_distribution.pdf` (IR 245:1), `temporal_volume.pdf` (malicious termina 07-30 → justifica split temporal), `confusion_m1.pdf` (malicious → benign/suspicious), `architecture.pdf` (pipeline). Variantes en `experiments/m1_tabular/leaderboard.csv` (logreg-F2 0.6148 supera en F1 pero se queda LGBM por latencia).

## 6. Despliegue e Inferencia (Deployment)

```bash
# Local
uv run uvicorn app.main:app --reload

# API: ejemplo con curl
curl -X POST http://127.0.0.1:8000/score \
  -H "Content-Type: application/json" \
  -d '{"message_type":"firewall_action","action":"block","message":"exploit T1190 test"}'
# → {"label":"malicious","proba":{...},"triage":"escalar","m2":{...}}

# Docker (recomendado demo: API + web en un :8000)
docker build -t soc-precinct6 .
docker run -p 8000:8000 soc-precinct6
# o: docker compose up --build
```

Endpoints: `GET /health /info /stats /queue?label&limit /incident/{id} /graph/vecindario?node` · `POST /score /score_batch /score_graph /explain /feedback`. La consola React (`soc-ui/`, `npm run dev`) consume solo esos endpoints; `/` sirve la web. Regla de triage: `escalar` iff malicious o (suspicious + action=block).

## 7. Tecnologías Utilizadas

- **Core:** Python 3.10, Pandas, PyArrow, Scikit-Learn, LightGBM, XGBoost, Matplotlib/Seaborn.
- **MLOps / Tracking:** MLflow (`experiments/mlruns`), uv + `uv.lock` pineado.
- **API / Despliegue:** FastAPI, Uvicorn, Docker (+ Compose), React+TS+Vite (ECharts, ReactFlow), Hugging Face Datasets.

## 8. Documentación y Referencias

| Quiero... | Lee |
|---|---|
| Entenderlo todo end-to-end (recomendado) | [`docs/documentacion_end_to_end.md`](docs/documentacion_end_to_end.md) |
| No soy técnico | [`docs/glosario_soc_no_tecnico.md`](docs/glosario_soc_no_tecnico.md) |
| Qué datos son y sus límites | [`docs/datasheet.md`](docs/datasheet.md) (Gebru) + [`reports/eda/resumen_eda.md`](reports/eda/resumen_eda.md) + [`reports/eda/diccionario_datos.csv`](reports/eda/diccionario_datos.csv) |
| Qué hace cada modelo | [`docs/model-card-m1.md`](docs/model-card-m1.md) · [`docs/model-card-m2.md`](docs/model-card-m2.md) · [`docs/model-card-m3.md`](docs/model-card-m3.md) |
| Cómo se despliega y qué cambió | [`docs/factsheet-changelog.md`](docs/factsheet-changelog.md) |
| Consigna del curso | [`docs/guia_proyecto.md`](docs/guia_proyecto.md) (`contexto/course_project_guide.pdf`) |
| Literatura del primer entregable | [`docs/referencias_primer_entregable.md`](docs/referencias_primer_entregable.md) |
| SOTA multi-label ATT&CK y qué implementar | [`docs/sota_attck_multilabel.md`](docs/sota_attck_multilabel.md) |
| Paper final | [`reports/paper.pdf`](reports/paper.pdf) ([`.tex`](reports/paper.tex)) |

Dataset y pipeline: [2M](https://huggingface.co/datasets/witfoo/precinct6-cybersecurity) · [100M](https://huggingface.co/datasets/witfoo/precinct6-cybersecurity-100m) · [dataset-from-precinct6](https://github.com/witfoo/dataset-from-precinct6) · [research WitFoo](https://witfoo.com/research). Marco: [ATT&CK](https://attack.mitre.org/) · [Navigator](https://mitre-attack.github.io/attack-navigator/) · [Design & Philosophy](https://attack.mitre.org/docs/ATTACK_Design_and_Philosophy_March_2020.pdf). Provenance IDS: [NODLINK](https://arxiv.org/abs/2311.02331) ([DOI](https://doi.org/10.14722/ndss.2024.23204)) · [KnowHow](https://arxiv.org/abs/2509.05698) · [FLASH](https://doi.org/10.1109/sp54263.2024.00139) ([código](https://github.com/DART-Laboratory/Flash-IDS)) · [PROVSYN](https://arxiv.org/abs/2506.06226) · [OMNISEC](https://arxiv.org/abs/2503.03108) · [Survey](https://arxiv.org/abs/2006.01722) · [threaTrace](https://arxiv.org/abs/2111.04333) · [GraphSAGE](https://arxiv.org/abs/1706.02216) · [E-GraphSAGE](https://arxiv.org/pdf/2103.16329v8) · [PIDSMaker](https://ubc-provenance.github.io/PIDSMaker/tutorial/). Imbalance/texto/sim: [Focal Loss](https://arxiv.org/abs/1708.02002) · [Cost-sensitive IDS](https://arxiv.org/pdf/0807.2043) · [PWG-IDS](https://arxiv.org/abs/2110.03445) · [TF-IDF vs MiniLM](https://arxiv.org/abs/2407.06753) · [CybORG](https://arxiv.org/abs/2002.10667) · LightGBM (Ke et al., NeurIPS 2017).

**Limitaciones:** labels = correlación automática Precinct (no verdad analista); T1190 domina malicious; ORG-0004 49.5%; `severity` 49% vacía por construcción. Detalle en paper §Limitations.
