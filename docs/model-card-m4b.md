# Model Card — M4b ATT&CK por técnica (`models/m4b_metrics.json`, NO desplegado)

> Versión: `m4b-xgb-perlabel-v1`, train 91,617 / test 22,904 (solo threat live, split temporal 80/20).

## Descripción
Un `XGBClassifier` binario por técnica (6 total: T1190/T1041/T1567/T1204/T1486/T1566, `scale_pos_weight=neg/pos`) con el mismo X de M2 (TF-IDF 5k + tabular one-hot). T1486/T1566 sin soporte en train → ceros. Experimento en `notebooks/m4b_xgb_pertecnica_out.ipynb`.

## Evaluación
micro-F1 **0.79** · macro-F1 **0.26** · hamming 0.089 · subset-acc 0.73. T1190 1.00 (trivial) · T1041/T1567 P 0.08/R 0.06/F1 0.07 (ni lineal ni XGB separan a nivel evento) · T1204 F1 0.39 (10/10 a base de FPs) · T1486/T1566 0. Oráculo-tier: 0.9994/0.4997.

## Decisión: no desplegado
P 0.08 en T1041/T1567 mentiría al analista. En `/score` se sirve el **mapeo tier→técnicas** (oráculo M4) con `techniques_source` declarado. M4b queda como negativo + base para Fase 2 (sentence-level, MiniLM/SciBERT, aumento TTPXHunter).
