# Model Card — M3 grafo vecindario (`models/m3.pkl`)

> Versión: `m3-grafo-v1`, train 24,000 / test 6,000.

## Descripción
Mismo tabular que M1 + 8 feats de vecindario ±300s por `ORG|src_ip|dst_ip|username` (`n_neigh, n_hosts, n_users, frac_block, frac_fw, frac_authfail, n_types, span_min`, índice hash full-data) → `XGBClassifier(300×6, multi:softprob)`. Agregación SAGE-mean 1 salto (no GNN end-to-end todavía).

## Uso previsto / fuera de alcance
Previsto: detectar movimiento lateral / cadenas USER_ACTION en ~s por subgrafo (`POST /score_graph`). Fuera: eventos sin vecinos (`n_vecinos=0` → benign), grafos multi-salto, hosts con clock skew.

## Evaluación
F1-macro **0.7186** (mejor global) · benign 1/1/1 · malicious 0.7946/0.9620/0.8703 (PR 0.8154) · suspicious 0.6009/0.1871/0.2854 · recall @1%FPR 0.0376. Igual que M2 por comportamiento, peor que M2 a FPR ultrabajo.

## Limitaciones
Ventana fija ±5min; feats manuales, no embeddings; hereda priors de reglas. Costo por evento `O(vecinos en ventana)`.

## Mantenimiento
Repro: `uv run python experiments/m3_grafo/train.py --n 30000`. Futuro: GraphSAGE real 2 saltos + link-prediction.
