# Fuentes Primer Entregable — Precinct6 chica (detección intrusiones SOC)

> Propuesta: clasificación de alertas SOC + grafos de proveniencia con `witfoo/precinct6-cybersecurity` (2M). Paper IEEE posterior.

## 0. Aclaración paper

No hay paper peer-reviewed formal (arXiv/NeurIPS/ACM) sobre este dataset específico todavía. Lo que existe es dataset + código + research page. Esto es ventaja para propuesta: problema real, poca literatura saturada.

## 1. Dataset oficial (citar en slides 4)

| Recurso | Enlace | Uso en entregable |
|---|---|---|
| Dataset 2M (usar este) | https://huggingface.co/datasets/witfoo/precinct6-cybersecurity | `signals` 2,011,674 eventos, 51,371 grafos, 238k triggering signals, GraphML + reportes NL. Licencia Apache-2.0 |
| Dataset 114M (solo referencia) | https://huggingface.co/datasets/witfoo/precinct6-cybersecurity-100m | 114,421,340 eventos, 101M aristas, 67k nodos. No descargar, solo para justificar escala |
| Código generación oficial | https://github.com/witfoo/dataset-from-precinct6 | Pipeline 4 capas sanitización (regex+parsers+ML/NER+Claude), 261 lead rules, Cassandra→grafos. Fuente para sección 3 (proceso) |
| Research WitFoo | https://witfoo.com/research | Student work: Ben Irvine (2026) testing provenance-graph IDS sobre 1 día real; hashing consistente; simulación. Filosofía "Empathetic Processing" (Charles Herring, nov 2025) |

Datos clave dataset (para slide dataset):
- SOC real prod, 4 orgs (versión chica) / 5 orgs (grande), ventana 2024-07-26 a 2024-08-01 (chica).
- Fuentes: syslog, Windows, VPC flows, endpoint, 158 productos de >70 vendors.
- Labels: benign / suspicious / malicious. Solo 7,728 leads maliciosos in-window (0.38%) → desbalance extremo, hablar de esto.
- Columnas: `signals`, `incident_signals` (con `origin`), `graph_nodes` (47,585 nodos), `graph_edges` (1.7M), `attack_reports` (51k textos).
- Mapeos MITRE ATT&CK incluidos.

## 2. Literatura para sección 2 (2-3 citas mínimo)

### Obligatorios marco
- MITRE ATT&CK oficial: https://attack.mitre.org/ — taxonomía tácticas/técnicas. Usar Navigator: https://mitre-attack.github.io/attack-navigator/ para visualizar cobertura.
- Paper diseño/filosofía ATT&CK: https://attack.mitre.org/docs/ATTACK_Design_and_Philosophy_March_2020.pdf

### Provenance-graph IDS — PDFs en `papers/`
1. **NODLINK (NDSS 2024)** — APT online, VAE + Steiner Tree, evaluado en producción. Leer primero.
   - arXiv: https://arxiv.org/abs/2311.02331 — DOI: https://doi.org/10.14722/ndss.2024.23204
   - local: `papers/NODLINK-2311.02331.pdf`
2. **KnowHow (NDSS 2026)** — CTI + provenance, interpretable, baja FPs. Citado en README Precinct6.
   - arXiv: https://arxiv.org/abs/2509.05698
   - local: `papers/KnowHow-2509.05698.pdf`
3. **FLASH (IEEE S&P 2024)** — GNN + Word2Vec semántico-temporal, embedding recycling DB. Evaluado en DARPA OpTC.
   - DOI: https://doi.org/10.1109/sp54263.2024.00139 — PDF: https://dartlab.org/assets/pdf/flash.pdf — código: https://github.com/DART-Laboratory/Flash-IDS
   - local: `papers/FLASH-SP2024.pdf`
4. **PROVSYN (2025)** — sintetiza security graphs con LLM+GNN (para nuestro desbalance 0.38%).
   - arXiv: https://arxiv.org/abs/2506.06226
   - local: `papers/PROVSYN-2506.06226.pdf`
5. **OMNISEC (2025)** — LLM + provenance con RAG, reconstruye attack graph.
   - arXiv: https://arxiv.org/abs/2503.03108
   - local: `papers/OMNISEC-2503.03108.pdf`
6. **Survey provenance (2020)** — base teórica obligatoria.
   - arXiv: https://arxiv.org/abs/2006.01722
   - local: `papers/Survey-provenance-2006.01722.pdf`
- UNICORN / HOLMES (baselines que NodLink supera, prior work).

### Cyber defense simulation
- CybORG (DST Group): https://arxiv.org/abs/2002.10667 — gym agentes blue/red. Justifica despliegue como agente SOC.
  - local: `papers/CybORG-2002.10667.pdf`

### Clásicos (referencia indirecta, mismo tipo label)
- UNSW-NB15 / CICIDS2017-2018: RF/XGBoost/CNN-LSTM >97% binario. Citar 1-2 como baseline tabular.
- DARPA OpTC/TC: benchmarks host-level (Precinct6 es SOC multi-vendor = ventaja nuestra).

### Orden lectura: NODLINK → KnowHow → FLASH → PROVSYN → Survey.

## 3. Estructura propuesta (mapeo a guía)

1. **Intro/motivación:** fatiga alertas SOC, 158 productos → ruido, costo breach. Fuente: research page + ATT&CK.
2. **Literatura:** NodLink vs UNICORN/HOLMES + CybORG + ATT&CK.
3. **Solución/proceso + diagrama:** `signals` → prepro (3 métodos) → 3 modelos (ej: XGBoost tabular, TF-IDF+LogReg en `report_text`, GNN/Node2Vec+MLP en grafo) → fusión → demo SOC. Diagrama: Cassandra → sanitización 4 capas (del repo) →Labels 261 reglas → grafos GraphML → modelo.
4. **Dataset + viz:** distribución labels (0.38% malicioso), temporal 26jul-01ago 2024, top técnicas ATT&CK, ejemplo `attack_reports` + subgrafo incidente, tamaño tablas.

## 4. Links rápidos copiar-pegar

```
https://huggingface.co/datasets/witfoo/precinct6-cybersecurity
https://huggingface.co/datasets/witfoo/precinct6-cybersecurity-100m
https://github.com/witfoo/dataset-from-precinct6
https://witfoo.com/research
https://attack.mitre.org/
https://arxiv.org/abs/2311.02331
https://arxiv.org/abs/2509.05698
https://arxiv.org/abs/2506.06226
https://arxiv.org/abs/2006.01722
https://arxiv.org/abs/2503.03108
https://arxiv.org/abs/2002.10667
https://doi.org/10.1109/sp54263.2024.00139
https://github.com/DART-Laboratory/Flash-IDS
```

## 5. Material descargado (`papers/`)

| PDF | Paper |
|---|---|
| `papers/NODLINK-2311.02331.pdf` | NODLINK NDSS24 |
| `papers/KnowHow-2509.05698.pdf` | KnowHow NDSS26 |
| `papers/FLASH-SP2024.pdf` | FLASH S&P24 |
| `papers/PROVSYN-2506.06226.pdf` | PROVSYN 2025 |
| `papers/OMNISEC-2503.03108.pdf` | OMNISEC 2025 |
| `papers/Survey-provenance-2006.01722.pdf` | Survey |
| `papers/CybORG-2002.10667.pdf` | CybORG |

## 6. Cómo hacer cada modelo (base arXiv) — PDFs en `papers/`

**M1 — LightGBM tabular cost-sensitive (IR 245:1):**
- Focal Loss original (Lin et al.): https://arxiv.org/abs/1708.02002 — `papers/FocalLoss-1708.02002.pdf` — fórmula `FL(pt)=-(1-pt)^γ log(pt)`, γ=2, α=0.25. Úsalo en LightGBM (`TPE-FL-LightGBM` para UNSW-NB15) o `scale_pos_weight`.
- Cost-sensitive IDS clásico: https://arxiv.org/pdf/0807.2043 — `papers/CostSensitive-IDS-0807.2043.pdf` — matriz costos FN>>FP, justifica no usar accuracy.
- PWG-IDS (WGAN-GP + LightGBM para imbalance IIoT): https://arxiv.org/abs/2110.03445 — `papers/PWG-IDS-2110.03445.pdf` — alternativa augmentation si SMOTE no basta.

**M2 — Texto + tabular (message_sanitized → XGBoost):**
- Pipeline MiniLM-384 + XGBoost CPU-only, quantization int8, batch infer (IJEAT 2025): TF-IDF 21% → MiniLM 57% accuracy en logs. Base para nuestro M2 (TF-IDF 5k primero, MiniLM después). SHAP para interpretabilidad.
- TF-IDF vs MiniLM/RoBERTa en threat-reports→CVE: TF-IDF gana con poco dato (prec 75%, F1 64%): https://arxiv.org/abs/2407.06753 — justifica empezar TF-IDF.

**M3 — Grafo provenance (GraphSAGE inductivo):**
- GraphSAGE original (Hamilton et al. NIPS17): https://arxiv.org/abs/1706.02216 — `papers/GraphSAGE-1706.02216.pdf` — sample+aggregate, generaliza a nodos no vistos (clave SOC streaming).
- threaTrace (GraphSAGE node-level APT): https://arxiv.org/abs/2111.04333 — `papers/threaTrace-2111.04333.pdf` — multi-modelo por tipo nodo + threshold = max loss validación. Copia este diseño: 1 modelo HOST + 1 CREDENTIAL.
- E-GraphSAGE NIDS (usa flows como grafo): https://arxiv.org/pdf/2103.16329v8.pdf — edges con features, útil para nuestros `NETWORK_FLOW/USER_ACTION`.
- PIDSMaker tutorial (GraphSAGE + Word2Vec + MLP edge-type, como Kairos/Orthrus): https://ubc-provenance.github.io/PIDSMaker/tutorial/ — receta código directa.

## 7. Próximo paso código

```powershell
uv run explorar.py
# luego: sample 5k → EDA labels, ATT&CK counts, plot temporal
```

## 8. SOTA multi-label ATT&CK (M4/M4b, oct-2026)

Medido en casa: M4-LogReg micro 0.75/macro 0.25, M4b-XGB micro 0.79/macro 0.26 (`notebooks/m4_multilabel_attack_out.ipynb`, `m4b_xgb_pertecnica_out.ipynb`). T1190 trivial; T1041/T1567 no separables a nivel evento; cola sin soporte. Lo que la literatura hace para esto:

- **TRAM (MITRE CTID)** — plataforma open-source + dataset 50 técnicas + notebooks single/multi-label SciBERT (Colab): https://github.com/center-for-threat-informed-defense/tram/ — notebooks: https://github.com/center-for-threat-informed-defense/tram/tree/main/user_notebooks — plantilla Fase 3 (fine-tune SciBERT multi-label con nuestros 51k `attack_reports`).
- **Two-stage LLM (arXiv 2411.18755)** — LLM resume + SciBERT rebalanceado/aumentado, +5-9pp macro-F1 vs TRAM: https://arxiv.org/abs/2411.18755 — local: `papers/TwoStage-LLM-2411.18755.pdf` — receta contra la cola.
- **Vuln-feature comparison (arXiv 2407.06753)** — TF-IDF (P 75%, F1 64%) gana a LSI/BERT/MiniLM/RoBERTa en threat-reports→vulnerabilidad: https://arxiv.org/abs/2407.06753 — local: `papers/ThreatCVE-TFIDF-2407.06753.pdf` — justifica M2-TF-IDF-primero.
- **TF-IDF + ModernBERT/BERTopic (Electronics 2025)** — micro-prec 72.25% (+10pp), variante tópicos macro-F0.5 63.20% en clases raras (rcATT 1,490 reportes): https://www.mdpi.com/2079-9292/14/22/4434 — receta Fase 2: concatenar TF-IDF + embeddings + MLP.
- **MITREtrieval (IEEE TNSM 2024)** — BERT frase + ontología COMAT + voto por niveles, F2 58/62/69%: sentencia→documento, aplicable a `message_sanitized` → voto por evento.
- **TTPXHunter (ACM DTRAP 2024)** — aumento LLM de frases para TTPs minoritarios, F1 92-97%: https://dlnext.acm.org/doi/10.1145/3696427 — receta cola T1204/T1486/T1566 con `incident_signals`.
- **ALERT (NIST 2024)** — LLM + active learning, igual performance con 77% menos anotación — si algún día anotamos a mano.
- **AnnoCTR (LREC 2024)** — 700 reportes / 165 técnicas anotadas por experto: https://aclanthology.org/2024.lrec-main.103.pdf — benchmark cola larga.
- Ver experimentos M4/M4b en `notebooks/m4_multilabel_attack_out.ipynb` y `notebooks/m4b_xgb_pertecnica_out.ipynb`.
