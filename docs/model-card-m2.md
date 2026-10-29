# Model Card — M2 texto+tabular (`models/m2.pkl`)

> Versión: `m2-texto-v1`, encoder `tfidf-5k`, train 24,000 / test 6,000.

## Descripción
P1–P3 + `TfidfVectorizer(5k, word+char, sublinear, min_df=5)` sobre `message_sanitized` concatenado (`hstack`) + tabulares one-hot → `XGBClassifier(300×6, lr 0.08, subsample 0.8, multi:softprob, sample_weight balanceado)`. Camino MiniLM-384 documentado para después.

## Uso previsto / fuera de alcance
Previsto: confirmar malicious por texto en ~100ms b-32 (`/score` cascada `m2`). Fuera: suspicious (lo pierde), mensajes vacíos/adversariales, idiomas no vistos.

## Evaluación
F1-macro **0.7084** · benign 1.0/1.0/1.0 (PR 1.0) · malicious 0.7905/0.9698/0.8711 (PR 0.8261) · suspicious 0.6188/0.16/0.2543 (PR 0.4256) · recall malicious @1%FPR 0.0813. Especialista malicious vía tokens T1190; sacrifica tier medio.

## Limitaciones
Vocabulario fijo 5k; sensible a ofuscación; benign 1.0 = volumen. Complejidad TF-IDF `O(L)` + XGBoost `O(T·depth)`.

## Mantenimiento
Repro: `uv run python experiments/m2_texto/train.py --n 30000 [--encoder miniml]`.
