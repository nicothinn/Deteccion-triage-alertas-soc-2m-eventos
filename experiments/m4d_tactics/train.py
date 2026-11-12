"""M4d: multilabel por TACTICA ATT&CK con XGBoost (Fase A barata).
Misma receta que M4b pero con attack_tactics (5 labels).
Corre: uv run python experiments/m4d_tactics/train.py
Guarda: models/m4d_metrics.json. Protocolo: threat live, split temporal 80/20.
"""
# ponytail: espejo de M4b, cambia solo la columna label y la lista de labels
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import hstack
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (accuracy_score, average_precision_score,
                             classification_report, f1_score, hamming_loss)
from sklearn.preprocessing import MultiLabelBinarizer, OneHotEncoder
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[2]
TACTICS = ["TA0001", "TA0002", "TA0009", "TA0010", "TA0040"]
CATS = ["message_type", "stream_name", "product_name", "vendor_name", "pipeline",
        "org_id", "action", "severity", "protocol"]
TEXT = "message_sanitized"


def parse_tactics(v):
    try:
        return [x for x in (json.loads(v) if v else []) if x in TACTICS]
    except Exception:
        return []


def main():
    cols = ["label_binary", "timestamp", "event_time", TEXT, "attack_tactics"] + CATS
    df = pd.read_parquet(ROOT / "data" / "signals" / "signals.parquet", columns=cols)
    th = df[df.label_binary != "benign"].copy().reset_index(drop=True)
    th["tactic_list"] = th.attack_tactics.fillna("").map(parse_tactics)
    print("threat:", th.shape,
          {t: int((th.tactic_list.map(lambda l: t in l)).sum()) for t in TACTICS})

    th["hour"] = pd.to_datetime(th["timestamp"], unit="s", utc=True).dt.hour
    th["msg_len"] = th[TEXT].fillna("").str.len()
    th["lag_h"] = ((th["timestamp"] - th["event_time"]) / 3600).clip(-1e4, 1e4).fillna(-1)
    for c in CATS:
        th[c] = th[c].fillna("").astype(str)
    msg = th[TEXT].fillna("")
    cutoff = th["timestamp"].quantile(0.8)
    tr = (th["timestamp"] <= cutoff).to_numpy()
    te = ~tr
    print(f"train/test: {tr.sum()}/{te.sum()}")

    Y = MultiLabelBinarizer(classes=TACTICS).fit_transform(th.tactic_list)
    vec = TfidfVectorizer(max_features=5000, ngram_range=(1, 2),
                          sublinear_tf=True, min_df=5)
    Ttr = vec.fit_transform(msg[tr].tolist())
    Tte = vec.transform(msg[te].tolist())
    tab = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", max_categories=30), CATS),
        ("num", "passthrough", ["hour", "msg_len", "lag_h"]),
    ])
    Atr = tab.fit_transform(th[tr][CATS + ["hour", "msg_len", "lag_h"]])
    Ate = tab.transform(th[te][CATS + ["hour", "msg_len", "lag_h"]])
    Xtr = hstack([Ttr, Atr]).tocsr()
    Xte = hstack([Tte, Ate]).tocsr()
    print("X:", Xtr.shape, Xte.shape)

    P = np.zeros_like(Y[te])
    skipped = []
    for j, t in enumerate(TACTICS):
        pos = int(Y[tr][:, j].sum())
        neg = int(tr.sum()) - pos
        if pos < 2:
            skipped.append(t)
            continue
        clf = XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.08,
                            subsample=0.8, colsample_bytree=0.8, tree_method="hist",
                            objective="binary:logistic", scale_pos_weight=neg / pos,
                            eval_metric="logloss", n_jobs=-1, random_state=42)
        clf.fit(Xtr, Y[tr][:, j])
        P[:, j] = (clf.predict_proba(Xte)[:, 1] >= 0.5).astype(int)
        print(f"{t}: pos train {pos} spw {neg / pos:.0f}", flush=True)
    print(f"skipped (sin soporte train): {skipped}")

    print(classification_report(Y[te], P, target_names=TACTICS, zero_division=0))
    res = {"model": "m4d-xgb-pertactic-v1", "labels": TACTICS,
           "micro_f1": round(float(f1_score(Y[te], P, average="micro")), 4),
           "macro_f1": round(float(f1_score(Y[te], P, average="macro")), 4),
           "hamming": round(float(hamming_loss(Y[te], P)), 4),
           "subset_acc": round(float(accuracy_score(Y[te], P)), 4),
           "skipped": skipped,
           "n_train": int(tr.sum()), "n_test": int(te.sum())}
    prauc = {}
    for j, t in enumerate(TACTICS):
        try:
            prauc[t] = round(float(average_precision_score(Y[te][:, j], P[:, j])), 4)
        except Exception:
            prauc[t] = 0.0
    res["pr_auc"] = prauc
    print(res)
    (ROOT / "models" / "m4d_metrics.json").write_text(json.dumps(res, indent=2))
    print("guardado models/m4d_metrics.json")


if __name__ == "__main__":
    main()
