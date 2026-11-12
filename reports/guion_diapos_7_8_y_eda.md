# Guion diapos 7-8 + EDA en vivo — Primera entrega

> Pptx: `reports/Triage_Alertas_SOC.pptx` (9 slides). Notebook: `notebooks/eda_precinct6.ipynb` (25 celdas, 12 secciones). EDA reproducible: `reports/eda/resumen_eda.md`.

## 1. Qué contiene el pptx (para ubicarte)

1. Portada: triage SOC.
2. Intro/motivación: SOC ahogado, 2M eventos 26jul–1ago, 4 orgs, 19 productos, 12 vendors. Problema = clasificar cada evento con desbalance + deriva.
3. Lit caso 1 Devign (NeurIPS19): GGNN sobre grafos de código, +10.51% acc / +8.68% F1. Precedente de M3-grafo. Contraste: ellos etiquetas manuales 600h limpias, nosotros automáticas ruidosas.
4. Lit caso 2 CVSS-BERT (ICMLA21): 8 BERTs texto→CVSS, MAE 0.73. Precedente de M2-texto. Limitación que heredamos: la etiqueta depende del asignador.
5. Solución flujo: Cassandra → sanear 4 capas → 261 reglas → GraphML+reportes → cascada M1/M2/M3 → consola.
6. Metodología: P1-P5 + complejidad + protocolo temporal 80/20, métricas F1-macro / PR-AUC / recall@FPR, accuracy solo contraste.
7. **Dataset: números + tabla 3 niveles.**
8. **Visualización y hallazgos: 2 gráficas + 3 hallazgos.**
9. Cierre: 3 experimentos planeados + ablaciones + limitaciones.

## 2. Diapo 7 — cómo explicarla (60-90 seg)

Lo que hay: 4 cifras grandes arriba (2.011.674 eventos, 38 cols, 4·19·12, 261 reglas), tabla benign 1.897.153/94.31% – suspicious 106.793/5.31% – malicious 7.728/0.38%, nota "etiquetas automáticas Precinct, no analista", y bloque "también incluye" (238k históricas, 47k nodos, 1.7M aristas, 51k reportes, Apache-2.0).

Guion literal sugerido:

> "Este es el dataset que usamos, no uno de juguete: `witfoo/precinct6-cybersecurity` v2.1.0, Apache 2.0, de HuggingFace. Son 2 millones de eventos reales en 6 días, 38 columnas por señal, 4 organizaciones, 19 productos, 12 vendors, 261 reglas de detección. La tabla es lo importante: 94% benigno, 5% sospechoso, 0.38% malicioso. Esos 7.728 maliciosos son leads de 1.584 incidentes in-window. Y ojo: las etiquetas las pone la correlación automática de Precinct, no un analista — es un oráculo fuerte pero ruidoso, la mayoría sigue en `Unprocessed`. Abajo lo que también trae: histórico, grafo de proveniencia y 51 mil reportes en lenguaje natural, que es lo que alimenta el grafo y la consola."

Frases si preguntan:

- ¿Por qué 3 clases y no binario? Porque el tier medio `suspicious` (match ≥1 regla sin ser lead) es el que el analista vigila; colapsarlo esconde el trade-off M1 vs M2/M3.
- ¿Por qué no mezclar `incident_signals`? Otro timeline (2022-2024), rompería el split temporal.
- ¿38 columnas? timestamps, identidad (`artifact_id` = join key, IPs, `username`), fuente (`message_type` ~40 valores, stream/product/vendor), contenido (`action`, `severity` 49% vacía, `protocol`), labels Precinct.

## 3. Diapo 8 — cómo explicar las 2 gráficas (90-120 seg, el corazón)

Lo que hay: izquierda gráfico de barras "Eventos por nivel (escala logarítmica)" con datos [1.897.153, 106.793, 7.728]; derecha imagen temporal (volumen por día, malicious termina 07-30); abajo 3 hallazgos: DESBALANCE 245:1 / DERIVA TEMPORAL / ETIQUETAS AUTOMÁTICAS.

### Gráfica izquierda — barras en log

> "Esta barra es la razón de todo el proyecto. En escala lineal el malicioso ni se ve: 1.9 millones contra 7 mil. Por eso está en logarítmica — si no, la tercera barra es invisible. La razón benigno:malicioso es 245 a 1. Y el dato que tienen que llevarse: predecir siempre 'benigno' da 94.31% de accuracy y no sirve para nada. Por eso no optimizamos accuracy, sino F1-macro y PR-AUC por clase, y reportamos recall de malicioso a FPR fijo. En seguridad un falso negativo cuesta una brecha, un falso positivo cuesta una revisión."

Si te interrumpen: "¿600 maliciosos no bastan?" → No, son 7.728 pero enterrados en 2M; el modelo tabular M1 de hecho colapsa ahí (recall 0.0045), esa es la hipótesis del exp. 1.

### Gráfica derecha — temporal

> "Esta es la deriva temporal: los leads maliciosos se concentran 26-30 de julio y se acaban el 30, mientras el benigno sigue hasta el 1 de agosto. Si hacemos shuffle y partimos al azar, el modelo memoriza ráfagas de campaña y parece excelente sin generalizar. Por eso el protocolo es split temporal: entrenar con el pasado, probar con el futuro, corte en cuantil 80%. Es la decisión metodológica más importante del EDA."

Dato de respaldo (`reports/eda/resumen_eda.md` F3): tabla día×label — 07-26: 3260 mal / 07-29: 3515 / 07-30: 37 / 07-31: 0 / 08-01: 0.

### Hallazgo 3 — etiquetas automáticas

> "Y el tercer hallazgo: etiquetas automáticas. 2.005.877 de 2M siguen en `disposition=Unprocessed`. No es verdad analista, es correlación. Entonces `label_confidence` no es P(malicioso), es corroboración, y las técnicas ATT&CK son priors de regla — por eso no las usamos como features y por eso M4 no se despliega."

Cierre diapo 8 → puente a diapo 9: "Esos tres hallazgos dictan los tres experimentos: M1 colapsa, M2 lo levanta con texto, M3 con grafo."

## 4. Cómo mostrar el notebook EDA en vivo (5-7 min, sin leerlo entero)

No corras las 25 celdas. Corre 5 y menciona el resto. Orden:

### A. Setup (cell 1, 15 seg, solo mostrar)

`SIG/INC/NODES/EDGES/REPORTS` existen. Di: "espejos locales para no re-descargar, parquets fuera de git".

### B. Target (cells 4-5, 1 min — OBLIGATORIO)

```python
df.label_binary.value_counts()
df.label_binary.value_counts(normalize=True)*100
df.groupby('label_binary').label_confidence.describe()
```

Muestra el bar plot. Di lo de diapo 8: IR 245:1, accuracy vacua, confidence 0.5/0.6/0.79 no es probabilidad.

### C. Temporal (cells 6-7, 1.5 min — OBLIGATORIO)

```python
df['ts']=pd.to_datetime(df.timestamp,unit='s',utc=True)
df.set_index('ts').resample('6h').size().plot()  # volumen
pd.crosstab(df.ts.dt.date, df.label_binary)      # drift
```

Muestra caída 07-28 (solo 10k eventos, domingo-infra?) y fin de malicious 07-30. Justifica split temporal. Este es tu argumento anti-"¿por qué no cross-val normal?".

### D. Leakage (cells 16-19, 1 min — lo que te distingue)

```python
pd.crosstab(df.disposition, df.label_binary)
# + top_json attack_techniques
```

Muestra: benign vacío en ATT&CK/mo/suspicion/incident_ids. Di: "son priors del motor, no features; si los meto, leakage y benign 1.0 tramposo". Menciona `label_confidence` excluida por derivar del tier.

### E. Texto + grafo (cells 20-23, 1 min — puente a M2/M3)

```python
df.groupby('label_binary').msg_len.describe()
# tokens malicious vs benign
inc.shape / nodes.type / edges.type / rep.mo_name
```

Muestra: `msg_len` cola larga XML, tokens T1190/exploit en malicious; 47k nodos (HOST 37k/CRED 10k), 1.7M aristas (USER_ACTION 692k/AUDIT 336k/FLOW 323k). Di: "H1 tokens separan (M2), H2 vecinos ±5min delatan lateralidad (M3)".

### Qué NO correr en vivo (solo citar)

Cells 8-15 (orgs, productos, red, action/severity): tené a mano 2 datos por si preguntan — ORG-0004 49.5% + ORG-0005 concentra suspicious 15.9%; `severity` 49% vacía = nivel propio; `message_type` malicious = `network_flow_data` 4156 + `firewall_action` 3525. Cell 24 conclusiones ya están en diapo 9.

## 5. Frases de seguridad (si hay preguntas duras)

- "¿Benign 1.0 es leakage?" → No: separabilidad por volumen con split estricto; M1 también da 1.0 y colapsa en malicious, si hubiera leakage colapsaría en todo o en nada. Features ATT&CK excluidas, verificado en EDA F3.
- "¿Por qué no SMOTE?" → Sobre one-hot fabrica combinaciones imposibles; usamos subsample que conserva todos los malicious + pesos de clase.
- "¿Por qué TF-IDF y no BERT ya?" → Con poco dato TF-IDF gana (cita 2407.06753 en `referencias_primer_entregable.md` §6); MiniLM es camino futuro documentado.
- "¿Grafo real o agregación?" → Agregación vecindario SAGE-mean 1 salto + XGBoost, inductivo a hosts nuevos; GraphSAGE full es trabajo futuro.

## 6. Checklist 10 min antes

- [ ] `data/signals/signals.parquet` presente (117 MB) o el notebook no corre.
- [ ] Kernel `.venv` Python 3.10.
- [ ] Pre-ejecutar `eda_precinct6_out.ipynb` por si el live falla — muestra ese.
- [ ] Tener abierto `reports/eda/resumen_eda.md` como respaldo de números.
- [ ] Tiempo: diapo 7 (1 min) + diapo 8 (2 min) + notebook (5 min) = 8 min, deja 7 para resto.
