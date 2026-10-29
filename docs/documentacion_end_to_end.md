# Documentación end-to-end — Triage SOC Precinct6

> Todo el proyecto en un solo documento: fenómeno, dataset, problema ML, preproceso (5 metodologías), 3 modelos + complejidad, evaluación con números reales, despliegue, reproducción, limitaciones y referencias. Complementa al paper [`reports/paper.pdf`](../reports/paper.pdf) y al glosario no-técnico [`glosario_soc_no_tecnico.md`](glosario_soc_no_tecnico.md).

## 1. Fenómeno y problema a abordar

Un SOC moderno ingiere syslog, auditoría Windows, VPC flows y telemetría endpoint de decenas de productos. WitFoo Precinct correlaciona todo con **261 lead rules** en *incidentes* (conjunto de señales disparadoras + subgrafo de proveniencia + reporte de caza). El analista sufre (i) **volumen** — millones de eventos mayormente benignos por semana — y (ii) **cambio de contexto** — decidir `escalar` vs `monitorear` exige el mensaje crudo, el mapeo MITRE y la cadena de ataque, no solo un score.

**Lo que se construye:** triage de alertas. Dado un evento, predecir su tier (`benign/suspicious/malicious`) con probabilidades calibradas, hints ATT&CK y decisión operativa, en <50ms para rankear la cola y con path batch para backfill. Ground truth = correlación automática de Precinct (oráculo fuerte pero imperfecto: `disposition=Unprocessed` en 2,005,877/2,011,674 señales).

## 2. Obtención y descripción del dataset

Fuente: **`witfoo/precinct6-cybersecurity` v2.1.0** (Apache-2.0, HuggingFace), mirrors locales en `data/` para no re-descargar. Captura viva **2024-07-26 → 2024-08-01**, 4 orgs. Generado con pipeline open-source de 4 capas (regex+parsers+ML/NER+Claude).

### 2.1 Tiers (IR benign:malicious ≈ 245:1)

| Tier | Rows | Share |
|---|---|---|
| benign | 1,897,153 | 94.31% |
| suspicious | 106,793 | 5.31% |
| malicious (leads in-window, 1,584 incidentes) | 7,728 | 0.38% |
| **Total live** | **2,011,674** | 100% |
| Historical `incident_signals` (todo malicious) | 238,511 | — |

### 2.2 Escala

| Componente | Count |
|---|---|
| Nodos proveniencia (HOST 36,974 / CRED 10,575 / misc) | 47,585 |
| Aristas (USER_ACTION 692k / AUDIT 336k / FLOW 323k) | 1,740,438 |
| Incidentes con GraphML + reporte NL | 51,371 |
| Lead rules / productos / vendors (catálogo; 19/12 observados) | 261 / 158 / 106 |
| Técnica top en malicious | T1190 |
| Ventana | 2024-07-26 → 08-01 |

### 2.3 Columnas (38 por señal)

Timestamps (`timestamp` ingest Precinct, `event_time` device clock con NaNs), identidad (`org_id`, `artifact_id` = join key al grafo, `src/dst_ip`, `username` → `user:USER-NNNN`), fuente (`message_type` ≈40 valores, `stream_name`, `product/vendor_name`, `pipeline`), contenido (`action`, `severity` ≈49% vacía, `protocol`, `message_sanitized`), labels Precinct (`label_binary`, `label_confidence`, `attack_techniques/tactics` priors, `mo_name`, `suspicion_score`, `disposition`, `incident_ids`). Orgs: ORG-0004 995,985 / ORG-0005 576,817 / ORG-0003 433,904 / ORG-0001 4,968. Top streams: `aws_cloudtrail_events`, `microsoft-windows-security-auditing`, `vcenter`, `cisco_asa`. Ver EDA completo en `notebooks/eda_precinct6.ipynb`.

### 2.4 Las otras 3 tablas

`incident_signals` 238k (histórico malicious 2022-2024, timeline separada con columna `origin`), `nodes.parquet` 47k + `edges-00000.parquet` 1.7M (grafo mergeado, ids `ORG|IP` y `ORG|user:USER-NNNN` compartidos entre live e incidentes), `attack_reports.parquet` 51k reportes NL deterministas por incidente.

## 3. Problema de machine learning

**Tipo:** clasificación multiclase supervisada con desbalance extremo, drift temporal y humano en el loop. **Tarea:** aprender `f: x ↦ (y, p)` donde `x` = un evento (campos tabulares + mensaje crudo + subgrafo vecindario ±5min), `y ∈ {benign, suspicious, malicious}`, `p` probabilidades; la consola mapea `(y,p,action)` → `escalar` iff `y=`malicious o (`y=`suspicious ∧ action`=`block). **Protocolo:** split temporal (train pasado / test futuro, corte = cuantil 80% de timestamp) para penalizar memorizar bursts; métricas macro-F1 + PR-AUC por clase + recall malicious a FPR fijo. Accuracy solo para mostrar que es vacua (≈94% con siempre-benign).

## 4. Preprocesamiento (5 metodologías, requisito ≥3)

**P1 — Categóricas con sanitización.** `severity` vacía (≈49%) e IPs faltantes se quedan como string vacío (nivel propio), nunca imputación mediana. 9 categóricas (`message_type, stream_name, product/vendor_name, pipeline, org_id, action, severity, protocol`) → `OneHotEncoder(handle_unknown='ignore', max_categories=30)`: ancho acotado, robusto a vendors no vistos.

**P2 — Temporales + anti-leakage.** De `timestamp/event_time` → `hour` (fase de turno) y `lag_h=(timestamp-event_time)/3600` clip `[-1e4,1e4]` (-1 si falta). Split temporal, no shuffle: campañas de fines de julio no fugan al test.

**P3 — Desbalance por diseño.** Subsampleo estratificado que conserva los 7,728 malicious y capa cada tier en `max(n/3,2000)`, luego `class_weight='balanced'` (M1) o `sample_weight` equivalente (M2/M3, porque `multi:softprob` no acepta `scale_pos_weight`). Sin SMOTE sobre one-hot (fabricaría combinaciones imposibles).

**P4 — Vectorización de logs (M2).** `message_sanitized` → TF-IDF 5k (word+char, sublinear, min_df=5) concatenado con P1–P3. Camino MiniLM-384 + XGBoost con SHAP documentado para después.

**P5 — Subgrafos de proveniencia (M3).** Por evento, aristas con `|t-t0|≤5min` que compartan host/credencial (`ORG|valor` = node ids del grafo), 8 feats agregadas (`n_neigh, n_hosts, n_users, frac_block, frac_fw, frac_authfail, n_types, span_min`). Clasificación inductiva (hosts no vistos en serve).

## 5. Modelos y complejidad

|  | M1 tabular | M2 texto+tabular | M3 grafo |
|---|---|---|---|
| Input | 9 cat + 3 num | P1–P3 + mensaje | subgrafo ±5min |
| Learner | LightGBM (200 árboles, 63 hojas, balanced) | TF-IDF 5k + XGBoost (300×6) | Agregación vecindario + XGBoost (300×6) |
| Output | `p(y\|x)` + hint | `p(y\|x)` (+SHAP futuro) | tier nodo + cadena |
| Train | minutos CPU | ~minutos CPU | ~minutos CPU (+índice full-data) |
| Infer | <50ms | ~100ms b-32 | ~s / subgrafo |

**Complejidad.** M1: fit `O(T·n·d_bin)` histogramas (`T=200, n=112,848, d≈9×30+3`); inferencia un root-to-leaf por árbol. M2: TF-IDF `O(L)` por mensaje + XGBoost `O(T·depth)`. M3: índice hash full-data + agregación por evento `O(vecinos en ventana)` + XGBoost; inductivo a hosts nuevos — el único que ve movimiento lateral invisible a una fila. Orden de serve en cascada: M1 rankea, M2 re-scorea top-k con evidencia textual, M3 dispara en formación de incidente.

Variantes comparadas en `experiments/m1_tabular/leaderboard.csv` (MLflow `experiments/mlruns`): logreg-F2 F1 0.6148 > lgbm — M1 se queda por latencia/simplicidad, documentado en `notebooks/m1_variants_mlflow.ipynb`.

## 6. Evaluación (medido, mismo protocolo)

### M1 — F1-macro 0.5991 (train 112,848 / test 28,212)

| Tier | Prec | Rec | F1 | PR-AUC | sup |
|---|---|---|---|---|---|
| benign | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 18506 |
| suspicious | 0.6696 | 0.9602 | 0.7890 | 0.6758 | 6576 |
| malicious | 0.0507 | 0.0045 | 0.0082 | 0.3023 | 3130 |

Suspicious se recupera, benign domina, malicious colapsa. Matriz en `reports/figures/confusion_m1.pdf`. Este negativo es el hinge del paper: lo tabular no ve semántica (M2) ni multi-paso (M3).

### M2 — F1-macro 0.7084 (train 24,000 / test 6,000, TF-IDF 5k + XGBoost)

benign 1.0/1.0/1.0 (3012, PR 1.0) · malicious 0.7905/0.9698/0.8711 (2288, PR 0.8261) · suspicious 0.6188/0.16/0.2543 (700, PR 0.4256) · recall malicious @1%FPR 0.0813. Levanta malicious vía tokens T1190; sacrifica suspicious.

### M3 — F1-macro 0.7186 (mismo split, 8 feats grafo + XGBoost)

benign 1.0/1.0/1.0 (3012, PR 1.0) · malicious 0.7946/0.9620/0.8703 (2288, PR 0.8154) · suspicious 0.6009/0.1871/0.2854 (700, PR 0.3554) · recall @1%FPR 0.0376. Iguala a M2 vía cadenas USER_ACTION. Trade-off idéntico: especialista malicious, pierde el tier medio.

Figuras: `reports/figures/{label_distribution,temporal_volume,confusion_m1,architecture}.pdf`, compiladas en `reports/paper.pdf`.

## 7. Despliegue

`uv run uvicorn app.main:app` sirve `models/m*.pkl` lazy: `GET /health /info /stats` (conteos fijos EDA, sin escanear 2M), `GET /queue?label&limit` (malicious-first), `GET /incident/{id}` (eventos + fila `attack_reports`), `POST /score` (single + cascada M1+M2 + regla triage), `POST /score_batch` (≤500), `POST /score_graph` (M3 por `artifact_id`), `POST /explain` (top features LightGBM), `POST /feedback` (append `data/feedback.csv` para re-entrenar), `GET /graph/vecindario?node` (1 salto acotado). React `soc-ui/` (`npm run dev`, páginas Cola/Incidente con ReactFlow / Cobertura MITRE con ECharts / Grafo / Lab / Panorama) consume solo esos endpoints; en Docker el mismo :8000 sirve API + `soc-ui/dist`. Fallback Streamlit `app/streamlit_app.py` + `pages/` llama el pickle directo. `Dockerfile` multi-stage (node build + `python:3.10-slim` para igualar sklearn 1.7.2/xgboost 3.2.0 del `.venv` y evitar warnings de unpickle) + `compose.yml` un servicio. Repro: `uv sync && uv run python experiments/m1_tabular/train.py --n 200000`. Env pineado en `uv.lock` (Python ≥3.10, LightGBM, XGBoost, scikit-learn, FastAPI, Streamlit).

## 8. Limitaciones y trabajo futuro

Labels = correlación Precinct, no verdad analista; T1190 domina y ORG-0004 sesga (49.5%); `severity` medio vacía por construcción; subgrafos heredan priors de reglas, no causalidad confirmada. Benign 1.0/1.0 refleja separabilidad por volumen en este sample con split temporal estricto, no leakage. Futuro: ATT&CK multi-label (mejor tarea que tiers), GraphSAGE real inductivo, MiniLM fine-tune + SHAP, reportes NL con LLM+RAG.

## 9. Referencias

Dataset y pipeline: [2M](https://huggingface.co/datasets/witfoo/precinct6-cybersecurity) · [100M](https://huggingface.co/datasets/witfoo/precinct6-cybersecurity-100m) · [dataset-from-precinct6](https://github.com/witfoo/dataset-from-precinct6) · [research](https://witfoo.com/research). Marco: [ATT&CK](https://attack.mitre.org/) · [Navigator](https://mitre-attack.github.io/attack-navigator/) · [Design & Philosophy](https://attack.mitre.org/docs/ATTACK_Design_and_Philosophy_March_2020.pdf). Provenance IDS: [NODLINK](https://arxiv.org/abs/2311.02331) ([DOI](https://doi.org/10.14722/ndss.2024.23204)) · [KnowHow](https://arxiv.org/abs/2509.05698) · [FLASH](https://doi.org/10.1109/sp54263.2024.00139) ([código](https://github.com/DART-Laboratory/Flash-IDS)) · [PROVSYN](https://arxiv.org/abs/2506.06226) · [OMNISEC](https://arxiv.org/abs/2503.03108) · [Survey](https://arxiv.org/abs/2006.01722) · [threaTrace](https://arxiv.org/abs/2111.04333) · [GraphSAGE](https://arxiv.org/abs/1706.02216) · [E-GraphSAGE](https://arxiv.org/pdf/2103.16329v8) · [PIDSMaker](https://ubc-provenance.github.io/PIDSMaker/tutorial/). Imbalance/texto/sim: [Focal Loss](https://arxiv.org/abs/1708.02002) · [Cost-sensitive IDS](https://arxiv.org/pdf/0807.2043) · [PWG-IDS](https://arxiv.org/abs/2110.03445) · [TF-IDF vs MiniLM](https://arxiv.org/abs/2407.06753) · [CybORG](https://arxiv.org/abs/2002.10667) · LightGBM (Ke et al., NeurIPS 2017).
