# Primer entregable — mapa: qué piden vs dónde está resuelto

> Guía: `docs/guia_proyecto.md` (`contexto/course_project_guide.pdf`). Formato pedido: **slides, 15 min + 5 min preguntas**, con estas 4 secciones.

## 1. Introducción y motivación — ✅ resuelto
- `reports/paper.tex` §1 (fenómeno SOC, fatiga de alertas, escalar vs monitorear) y Abstract.
- `docs/documentacion_end_to_end.md` §1 · `README.md` (propósito en negrita) · `docs/glosario_soc_no_tecnico.md` (versión no-técnica).

## 2. Revisión de literatura — ✅ resuelto
- `docs/referencias_primer_entregable.md` (mapeo a la guía + cómo hacer cada modelo + links).
- `papers/` locales (14 PDFs, no van a git) + tabla arXiv abajo + `docs/sota_attck_multilabel.md` (Fase 2/3).

## 3. Descripción de solución/proceso + diagrama — ✅ resuelto
- Diagrama: `reports/figures/architecture.pdf` (Cassandra → sanitize 4 capas → 261 reglas → GraphML → M1/M2/M3 → fusión → consola), incluido en `paper.tex` Fig. 4.
- Proceso en `docs/documentacion_end_to_end.md` §4–§5§7, `README.md` (arquitectura + pipeline paso 0–3), API `app/main.py`, consola `soc-ui/`.

## 4. Explicación y visualización del dataset — ✅ resuelto
- `reports/figures/label_distribution.pdf` (IR 245:1) y `temporal_volume.pdf` (malicious termina 07-30 → justifica split temporal), incluidas en `paper.tex`.
- `notebooks/eda_precinct6.ipynb` (12 secciones) + `src/eda_report.py` → `reports/eda/resumen_eda.md` + `reports/eda/diccionario_datos.csv` (38 columnas, missingness, leakage, drift).
- Tablas de tiers/escala en `paper.tex` §2 y `docs/documentacion_end_to_end.md` §2.

## Papers de arXiv revisados (todos con PDF local salvo indicación)

| arXiv | Título | Qué sacamos | Local |
|---|---|---|---|
| 2311.02331 | NODLINK (NDSS 24, APT online, VAE + Steiner Tree) | Baseline provenance-graph IDS que superamos en alcance | `papers/NODLINK-2311.02331.pdf` |
| 2509.05698 | KnowHow (NDSS 26, CTI + provenance interpretable) | Citado en README Precinct6; línea interpretable | `papers/KnowHow-2509.05698.pdf` |
| 2506.06226 | PROVSYN (sintetiza grafos con LLM+GNN) | Idea contra desbalance 0.38% | `papers/PROVSYN-2506.06226.pdf` |
| 2503.03108 | OMNISEC (LLM + provenance con RAG) | Línea reportes NL | `papers/OMNISEC-2503.03108.pdf` |
| 2006.01722 | Survey provenance IDS | Base teórica §2 | `papers/Survey-provenance-2006.01722.pdf` |
| 2111.04333 | threaTrace (GraphSAGE node-level APT) | Diseño M3 (1 modelo por tipo nodo + threshold) | `papers/threaTrace-2111.04333.pdf` |
| 1706.02216 | GraphSAGE (inductivo) | Fundamento M3 (nodos no vistos en streaming) | `papers/GraphSAGE-1706.02216.pdf` |
| 2002.10667 | CybORG (gym agentes blue/red) | Justifica despliegue como agente SOC | `papers/CybORG-2002.10667.pdf` |
| 1708.02002 | Focal Loss | Fórmula FL, γ=2/α=0.25; alternativa a class_weight | `papers/FocalLoss-1708.02002.pdf` |
| 0807.2043 | Cost-sensitive IDS | Matriz FN>>FP; justifica no usar accuracy | `papers/CostSensitive-IDS-0807.2043.pdf` |
| 2110.03445 | PWG-IDS (WGAN-GP + LightGBM) | Augmentation si SMOTE no basta | `papers/PWG-IDS-2110.03445.pdf` |
| 2407.06753 | TF-IDF gana a BERT/MiniLM/RoBERTa en threat→CVE (P 75%, F1 64%) | Justifica M2 TF-IDF-primero | `papers/ThreatCVE-TFIDF-2407.06753.pdf` |
| 2411.18755 | Two-stage LLM (resume + SciBERT rebalanceado, +5-9pp macro-F1) | Receta Fase 3 contra la cola | `papers/TwoStage-LLM-2411.18755.pdf` |
| 2103.16329 | E-GraphSAGE (flows como grafo) | Útil para `NETWORK_FLOW/USER_ACTION` | Solo link (en `referencias_primer_entregable.md` §6) |

No-arXiv (completan el SOTA, §8 de referencias): TRAM MITRE (repo + notebooks SciBERT), MITREtrieval (IEEE TNSM, F2 58/62/69%), TTPXHunter (ACM, aumento cola), ALERT NIST (active learning −77% datos), AnnoCTR (LREC 2024, 165 técnicas), ModernBERT⊕TF-IDF (MDPI, micro-prec 72.25%), FLASH S&P 2024 (`papers/FLASH-SP2024.pdf`, DOI en repo), ATT&CK oficial + Navigator.

## Qué falta (honesto)
- Pasar esto a **slides** (el repo tiene paper + demo, no `.pptx`): armar 4 secciones en ~15 min con figuras de `reports/figures/`.
- Ensayar demo 20 min del entregable final (`docker compose up` → Cola → Incidente → Cobertura) — guion en `README.md` §6 / `docs/factsheet-changelog.md`.
