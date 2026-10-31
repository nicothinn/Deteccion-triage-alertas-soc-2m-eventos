# Primera entrega completa — propuesta con 2 casos verificados

> Consigna (`contexto/course_project_guide.pdf`, 8va sesión): presentación con **(1) introducción y motivación, (2) revisión de literatura, (3) solución/proceso + diagrama, (4) dataset + visualización**. Formato: **slides, 15 min + 5 min preguntas**.
> Mapa de dónde está cada cosa en el repo: `docs/primer_entregable_mapa.md`.

## 1. Introducción y motivación (nuestro problema)

Los SOC se ahogan en alertas: nuestra captura tiene **2,011,674 eventos en 6 días** (4 orgs, 19 productos, 12 vendors) con solo **0.38% malicious** (IR 245:1). Los analistas sufren (i) **volumen** — millones de eventos mayormente benignos — y (ii) **cambio de contexto** — decidir `escalar` vs `monitorear` exige mensaje crudo + MITRE + cadena, no solo un score. Nuestro proyecto: **triage de alertas** — clasificar cada evento (benign/suspicious/malicious) con probabilidades, hints ATT&CK y decisión operativa en <50ms (detalle: `reports/paper.pdf` §1, `docs/documentacion_end_to_end.md` §1).

## 2. Revisión de literatura — 2 casos (+ conexión con lo nuestro)

### Caso 1: Devign — GNN sobre grafos de código (clasificación binaria vulnerable/no)

- **Cita verificada:** Yaqin Zhou, Shangqing Liu, Jingkai Siow, Xiaoning Du, Yang Liu, *"Devign: Effective Vulnerability Identification by Learning Comprehensive Program Semantics via Graph Neural Networks"*, **NeurIPS 2019** (33rd, poster 14038). arXiv: https://arxiv.org/abs/1909.03496 — PDF: https://arxiv.org/pdf/1909.03496 — proceedings: https://proceedings.neurips.cc/paper/2019/hash/49265d2447bc3bbfe9e76306ce40a31f-Abstract.html — local: `papers/Devign-1909.03496.pdf` — datasets: https://sites.google.com/view/devign.
- **Enfoque:** red neuronal de grafos (GGNN + módulo Conv propio) sobre representación compuesta del código (AST como backbone + control/data dependency en un grafo multi-arista). Formula el problema como **clasificación binaria a nivel de función**: ¿vulnerable o no? La Conv elige jerárquicamente los nodos/features relevantes para la predicción a nivel de grafo.
- **Datos:** etiquetados **manualmente (~600 horas-persona)** de **4 librerías C populares y diversas** (Linux Kernel, QEMU, Wireshark, FFmpeg) — código real complejo, no sintético (critican datasets con "good/bad" marcados y labels de analizadores estáticos con falsos positivos). Split 75/25, Adam lr 0.0001, batch 128, early stopping.
- **Resultado:** supera baselines en **+10.51% accuracy y +8.68% F1 promedio** (mínimos por dataset: +8.54% acc en QEMU; F1 +2.31–11.80%); la Conv aporta +4.66% acc / +6.37% F1; **+27.99% F1 vs analizadores estáticos** (Cppcheck, Flawfinder); **74.11% accuracy en 40 CVEs nuevos** (112 funciones) → sirve para zero-days.
- **Limitación:** etiquetas manuales carísimas (600 h) y granulidad función (no línea); depende de parsear bien el grafo.
- **Conexión con nuestro proyecto:** es el **precedente GNN de M3** (nuestro vecindario ±5min + XGBoost; ellos grafo de código + GGNN). Pero contrasta en etiquetas: ellos pagan 600 h manuales; nosotros usamos **labels automáticas de Precinct (imperfectas)** — nuestro riesgo es el opuesto (barato pero ruidoso). Citar Devign justifica "grafos + aprendizaje > reglas/estáticos" también en SOC.

### Caso 2: CVSS-BERT — severidad desde texto (un BERT por métrica CVSS)

- **Cita verificada:** Mustafizur R. Shahid, Hervé Debar (Télécom SudParis, Institut Polytechnique de Paris), *"CVSS-BERT: Explainable NLP to Determine the Severity of a Computer Security Vulnerability from its Description"*, **IEEE ICMLA 2021**. DOI: https://doi.org/10.1109/icmla52953.2021.00256 — arXiv: https://arxiv.org/abs/2111.08510 — código: https://github.com/mus-shd/CVSS-BERT — local: `papers/CVSS-BERT-2111.08510.pdf`.
- **Enfoque:** trabaja con **texto, no código**: **8 clasificadores BERT, uno por métrica del vector CVSS v3.1** (AV, AC, PR, UI, S, C, I, A) desde la descripción del CVE; concatena el vector y calcula el score 0–10. **Motivación:** al publicarse una vuln solo hay descripción y el análisis experto tarda días con miles de CVEs/día. **Explicable:** saliency por gradientes → palabras top coinciden con el racional del experto.
- **Datos:** NVD sincronizado con MITRE CVE, **45,926 CVEs 2018–2020** (train/test 22,963 c/u), descripción → vector → score.
- **Resultado:** accuracy por métrica **83.79% (PR) – 96.07% (AC)** (AC inflado: 93% una clase); severidad **MAE 0.73, MSE 1.79**; **55.3% match exacto** y MAE<1 en 75%. Muy cerca del experto humano.
- **Limitación:** los puntajes CVSS **varían según quién asigna** (NVD vs otras fuentes) → las etiquetas dependen del contexto/asignor. Advertencia directa para nosotros: nuestras labels también dependen del asignador (motor Precinct, no analista).
- **Conexión con nuestro proyecto:** es el **precedente texto→severidad de M2** (ellos descripción CVE→CVSS, nosotros `message_sanitized`→tier; ellos 8 BERTs, nosotros TF-IDF+XGBoost con camino MiniLM). Su saliency es el primo de nuestro `/explain` (top features). Y su limitación es nuestra §Limitations del paper: labels = oráculo imperfecto.

### Tabla casos vs nuestro proyecto (para el slide)

|  | Devign | CVSS-BERT | Nosotros (Precinct6) |
|---|---|---|---|
| Input | grafo de código (AST+flujos) | texto CVE | tabular + texto log + subgrafo ±5min |
| Tarea | binaria función vuln/no | 8 métricas CVSS → score | 3 tiers + ATT&CK (M4) |
| Etiquetas | manuales 600 h (caras, limpias) | NVD experto (cara, subjetiva) | Precinct auto (barata, ruidosa) |
| Modelo | GGNN + Conv | 8×BERT + saliency | LightGBM / TF-IDF+XGB / vecindario+XGB |
| Métrica estrella | +10.51% acc / +8.68% F1 | MAE severidad 0.73 | M3 F1-macro 0.719 |
| Lección | grafos > estáticos | texto→severidad + explicar | cascada M1→M2→M3 + explicar |

## 3. Solución/proceso + diagrama

`signals` → prepro P1–P5 (one-hot sanitizado, temporales + split temporal, anti-desbalance, TF-IDF, subgrafo) → M1 rankea / M2 confirma texto / M3 confirma cadena → fusión + consola (cola, incidente, cobertura MITRE). Diagrama: `reports/figures/architecture.pdf` (Fig. 4 del paper). Código: `app/main.py`, `experiments/*/train.py`, `soc-ui/`.

## 4. Dataset + visualización

`witfoo/precinct6-cybersecurity` v2.1.0 (Apache-2.0): 2,011,674 live (94.31/5.31/0.38%), 47,585 nodos, 1,740,438 aristas, 51,371 incidentes + reportes, 261 reglas. Figuras: `label_distribution.pdf` (IR 245:1), `temporal_volume.pdf` (malicious termina 07-30 → split temporal), `confusion_m1.pdf`, EDA `notebooks/eda_precinct6.ipynb` + `reports/eda/`.

## Referencias (links verificados hoy)

```
https://arxiv.org/abs/1909.03496
https://arxiv.org/pdf/1909.03496
https://proceedings.neurips.cc/paper/2019/hash/49265d2447bc3bbfe9e76306ce40a31f-Abstract.html
https://sites.google.com/view/devign
https://doi.org/10.1109/icmla52953.2021.00256
https://arxiv.org/abs/2111.08510
https://github.com/mus-shd/CVSS-BERT
```
