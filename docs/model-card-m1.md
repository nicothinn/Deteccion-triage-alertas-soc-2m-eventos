# Model Card — M1 tabular LightGBM (`models/m1.pkl`)

> Estructura Mitchell et al. / HF. Versión: `m1-tabar-v1`, train 112,848 / test 28,212.

## Descripción
`Pipeline(OneHotEncoder 9 cat max_categories=30 + passthrough 3 num → LGBMClassifier 200×63, lr 0.08, class_weight=balanced)`. Features: `message_type, stream_name, product/vendor_name, pipeline, org_id, action, severity, protocol + hour, msg_len, lag_h`. No lee texto ni grafo.

## Uso previsto / fuera de alcance
Previsto: rankear la cola en <50ms (`/score`, `/queue`). Fuera: cazar malicious raro, decidir bloqueo solo, vendors nuevos sin `handle_unknown`.

## Datos
Subset estratificado n=200k del live (todos los malicious + `max(n/3,2000)` por tier, seed 42), split temporal 80/20. Ver `docs/datasheet.md`.

## Evaluación (test futuro, no shuffle)
F1-macro **0.5991** · benign 1.0/1.0/1.0 (PR 1.0) · suspicious 0.6696/0.9602/0.7890 (PR 0.6758) · malicious 0.0507/0.0045/0.0082 (PR 0.3023). Matriz en `reports/figures/confusion_m1.pdf`. Falla exactamente en lo raro: hinge que justifica M2/M3.

## Limitaciones y sesgos
T1190+ORG-0004 dominan; severity 49% vacía; benign 1.0 = separabilidad por volumen, no leakage (split estricto). Complejidad fit `O(T·n·d_bin)`, inferencia un root-to-leaf por árbol.

## Mantenimiento
Owner: curso. Repro: `uv run python experiments/m1_tabular/train.py --n 200000`. Variantes en `experiments/m1_tabular/leaderboard.csv` (logreg-F2 0.6148 supera en F1 pero se queda LGBM por latencia).
