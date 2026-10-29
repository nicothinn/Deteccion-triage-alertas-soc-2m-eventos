# SOTA multi-label ATT&CK — qué implementar después de M4

> M4-LogReg dio micro 0.75 / macro 0.25: la cabeza se aprende, la cola no. Esto es lo que la literatura hace para ese mismo problema, con qué arquitectura, y qué encaja en nuestro stack (TF-IDF + XGBoost + MiniLM, CPU). PDFs locales en `papers/` (no van a git).

## 1. Datasets parecidos al nuestro

| Dataset | Qué es | Escala | Sirve para |
|---|---|---|---|
| **TRAM** (MITRE CTID, [repo](https://github.com/center-for-threat-informed-defense/tram/)) | Frases de CTI anotadas con técnicas | 50 técnicas, single+multi-label JSON | Baseline + notebooks listos (abajo) |
| **rcATT** (Legoy et al. 2020) | 1,490 reportes públicos → 12 tácticas multi-label | 1,490 docs | Benchmark del paper ModernBERT (72.25% micro-prec) |
| **AnnoCTR** (LREC 2024, [PDF](https://aclanthology.org/2024.lrec-main.103.pdf)) | Reportes anotados por experto (entidades+tácticas+técnicas implícitas) | 700 reportes, 14 tácticas, 165 técnicas | Cola larga realista |
| **MITREtrieval-set** (IEEE TNSM 2024) | 700 reportes CTI, umbrales 6/40/80 | 113 / 46 / 23 TTPs | Comparar F2 58/62/69% |
| **Nuestro live-threat** | Eventos SOC, no reportes | 6 técnicas, T1190 domina | Cabeza trivial, cola T1204/T1486/T1566 |

Ojo: todos clasifican **reportes/frases**, nosotros clasificamos **eventos**. El puente es clasificar a nivel frase del `message_sanitized`/`report_text` y votar por evento (TRAM y MITREtrieval hacen exactamente eso).

## 2. Arquitecturas SOTA (qué hace cada una)

| Sistema | Arquitectura | Resultado | Costo | Encaje nuestro |
|---|---|---|---|---|
| **TRAM baseline** | TF-IDF n-grams + LogReg/árboles, 50 técnicas | Funciona out-of-box en segundos | CPU | = nuestro M4. Ya hecho. Techo conocido. |
| **TRAM SciBERT** ([notebooks](https://github.com/center-for-threat-informed-defense/tram/tree/main/user_notebooks), single + multi-label, Colab OK) | SciBERT fine-tune (vocab científico ≈ vocab CTI) | +prec/rec/F1 vs LogReg en todo menos 1 métrica; bien desde época 1 | GPU (o Colab gratis) | **Fase 3 nuestra:** plantilla lista para fine-tune con nuestros eventos |
| **Two-stage LLM** ([arXiv 2411.18755](https://arxiv.org/abs/2411.18755), local `papers/TwoStage-LLM-2411.18755.pdf`) | LLM resume reporte → SciBERT reentrenado en dataset rebalanceado con datos aumentados | **+5 a 9 pp macro-F1** vs baseline TRAM, micro competitivo | GPU + LLM | Receta contra la cola: resumir + rebalancear + aumentar |
| **TF-IDF ⊕ ModernBERT / ⊕ BERTopic** ([Electronics 2025](https://www.mdpi.com/2079-9292/14/22/4434), rcATT) | TF-IDF + embeddings ModernBERT + MLP; variante con tópicos BERTopic | Micro-prec **72.25%** (+10pp); variante tópicos macro-F0.5 63.20% (+6.3pp, mejor en clases raras) | CPU/GPU leve | **Fase 2 nuestra:** concatenar TF-IDF que ya tenemos con embeddings, tal cual M2→MiniLM planeado |
| **Vuln-feature comparison** ([arXiv 2407.06753](https://arxiv.org/abs/2407.06753), local `papers/ThreatCVE-TFIDF-2407.06753.pdf`) | TF-IDF vs LSI/BERT/MiniLM/RoBERTa en threat-reports→vulnerabilidad | **TF-IDF gana: P 75%, F1 64%** | CPU | Justifica M2-TF-IDF-primero (nuestra decisión documentada en `referencias_primer_entregable.md` §6) |
| **MITREtrieval** (IEEE TNSM 2024) | BERT a nivel frase + ontología (COMAT) + voto por niveles | F2 **58/62/69%** (113/46/23 TTPs), supera rcATT/TTPDrill/AttacKG/TRAM | GPU leve | Idea voto-frase→evento aplicable a `message_sanitized` |
| **TTPXHunter** ([ACM 2024](https://dlnext.acm.org/doi/10.1145/3696427)) | Aumentación de frases con LLM para TTPs minoritarios + modelo dominio | F1 **92.42%** (aumentado) / **97.09%** (reportes) | LLM para aumentar | Receta para T1204/T1486/T1566: generar frases sintéticas minoritarias |
| **ALERT** (NIST 2024) | LLM + active learning (anotar solo lo informativo) | Igual performance con **77% menos datos** | LLM + loop humano | Si algún día anotamos a mano: anotar 23%, no todo |

Consenso SOTA: **sentence-level + embeddings/LLM + voto a documento + aumento para la cola**. Nada de eso contradice nuestro stack; todo es Fase 2/3 encima de M2.

## 3. Notebooks listos para reutilizar

- TRAM [`user_notebooks/`](https://github.com/center-for-threat-informed-defense/tram/tree/main/user_notebooks): fine-tune **single-label y multi-label** SciBERT paso a paso, corre en Colab con GPU gratis (subir reporte, fijar n-gramas, entrenar, exportar pesos). Es la plantilla para nuestra Fase 3.
- Nuestro [`notebooks/m4_multilabel_attack.ipynb`](m4_multilabel_attack.ipynb): baseline M4 reproducible (TF-IDF 5k + tabular + OneVsRest-LogReg, split temporal 80/20, + oráculo-tier).

## 4. Arquitectura recomendada para nosotros (3 fases)

1. **Fase 2 — ya implementable, CPU (días):** por-técnica **XGBoost** con el X de M2 (igual que M3 hace por tipo de nodo) + variante **TF-IDF ⊕ MiniLM-384 + MLP** (receta ModernBERT). Clasificar a **nivel frase** del mensaje/reporte y votar por evento (receta TRAM/MITREtrieval). Aumento sintético de T1204/T1486/T1566 estilo TTPXHunter con `incident_signals` histórico.
2. **Fase 3 — GPU/Colab (semanas):** fine-tune **SciBERT multi-label** con notebooks TRAM sobre `attack_reports` (51k) + frases de eventos; two-stage (resumir→clasificar) si la cola sigue en 0.
3. **No hacer:** prometer ATT&CK por evento en la demo con el M4 actual (macro 0.25). Desplegar el **mapeo tier→técnicas** (oráculo 0.9994) como capa honesta hasta que Fase 2 mida mejor.

## 5. Links rápidos

```
https://github.com/center-for-threat-informed-defense/tram/
https://github.com/center-for-threat-informed-defense/tram/tree/main/user_notebooks
https://arxiv.org/abs/2411.18755
https://arxiv.org/abs/2407.06753
https://aclanthology.org/2024.lrec-main.103.pdf
https://dlnext.acm.org/doi/10.1145/3696427
https://www.mdpi.com/2079-9292/14/22/4434
https://arxiv.org/abs/2509.05698
https://arxiv.org/abs/2311.02331
```
