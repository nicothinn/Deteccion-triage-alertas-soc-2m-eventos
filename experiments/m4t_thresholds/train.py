"""M4t: umbrales por tecnica afinados en validacion (F2, seguridad prefiere recall).
Retraina la arquitectura M4b (TF-IDF 5k + tabular, XGB por tecnica) con split
train/val/test por tiempo (cuantiles 60/80) y elige umbral por tecnica maximizando
F2 en val. Evalua en test con umbrales afinados vs 0.5 fijo.
Corre: uv run python experiments/m4t_thresholds/train.py
Guarda: models/m4t_metrics.json.
"""
# ponytail: mismo X que M4b, solo cambia el umbral; barato y honesto
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import hstack
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (accuracy_score, average_precision_score, fbeta_score,
                             f1_score, hamming_loss)
from sklearn.preprocessing import MultiLabelBinarizer, OneHotEncoder
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[2]
TECHS = ["T1190", "T1041", "T1567", "T1204", "T1486", "T1566"]
CATS = ["message_type", "stream_name", "product_name", "vendor_name", "pipeline",
        "org_id", "action", "severity", "protocol"]
TEXT = "message_sanitized"


def parse_labels(v):
    try:
        return [x for x in (json.loads(v) if v else []) if x in TECHS]
    except Exception:
        return []


def pick_threshold(y, s, beta=2.0):
    """Umbral que maximiza F-beta en validacion; (0.5, 0.0) sin positivos."""
    y = np.asarray(y).astype(int)
    s = np.asarray(s, dtype=float)
    if int(y.sum()) == 0:
        return 0.5, 0.0
    best_thr, best_f = 0.5, -1.0
    for thr in np.arange(0.05, 1.0, 0.05):
        p = (s >= thr).astype(int)
        f = fbeta_score(y, p, beta=beta, zero_division=0)
        if f > best_f:
            best_thr, best_f = round(float(thr), 2), round(float(f), 4)
    return best_thr, best_f


def main():
    cols = ["label_binary", "timestamp", "event_time", TEXT, "attack_techniques"] + CATS
    df = pd.read_parquet(ROOT / "data" / "signals" / "signals.parquet", columns=cols)
    th = df[df.label_binary != "benign"].copy().reset_index(drop=True)
    th["tech_list"] = th.attack_techniques.fillna("").map(parse_labels)
    th["hour"] = pd.to_datetime(th["timestamp"], unit="s", utc=True).dt.hour
    th["msg_len"] = th[TEXT].fillna("").str.len()
    th["lag_h"] = ((th["timestamp"] - th["event_time"]) / 3600).clip(-1e4, 1e4).fillna(-1)
    for c in CATS:
        th[c] = th[c].fillna("").astype(str)
    msg = th[TEXT].fillna("")
    q60, q80 = th["timestamp"].quantile(0.6), th["timestamp"].quantile(0.8)
    itr = (th["timestamp"] <= q60).to_numpy()
    iva = ((th["timestamp"] > q60) & (th["timestamp"] <= q80)).to_numpy()
    ite = (th["timestamp"] > q80).to_numpy()
    print(f"train/val/test: {itr.sum()}/{iva.sum()}/{ite.sum()}")
    Y = MultiLabelBinarizer(classes=TECHS).fit_transform(th.tech_list)

    vec = TfidfVectorizer(max_features=5000, ngram_range=(1, 2),
                          sublinear_tf=True, min_df=5)
    Ttr = vec.fit_transform(msg[itr].tolist())
    Tva = vec.transform(msg[iva].tolist())
    Tte = vec.transform(msg[ite].tolist())
    tab = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", max_categories=30), CATS),
        ("num", "passthrough", ["hour", "msg_len", "lag_h"]),
    ])
    Atr = tab.fit_transform(th[itr][CATS + ["hour", "msg_len", "lag_h"]])
    Ava = tab.transform(th[iva][CATS + ["hour", "msg_len", "lag_h"]])
    Ate = tab.transform(th[ite][CATS + ["hour", "msg_len", "lag_h"]])
    Xtr = hstack([Ttr, Atr]).tocsr()
    Xva = hstack([Tva, Ava]).tocsr()
    Xte = hstack([Tte, Ate]).tocsr()
    print("X:", Xtr.shape, Xva.shape, Xte.shape)

    thresholds, per_label = {}, {}
    Sva = np.zeros((iva.sum(), len(TECHS)))
    Ste = np.zeros((ite.sum(), len(TECHS)))
    skipped = []
    for j, t in enumerate(TECHS):
        pos = int(Y[itr][:, j].sum())
        neg = int(itr.sum()) - pos
        if pos < 2:
            skipped.append(t)
            continue
        clf = XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.08,
                            subsample=0.8, colsample_bytree=0.8, tree_method="hist",
                            objective="binary:logistic", scale_pos_weight=neg / pos,
                            eval_metric="logloss", n_jobs=-1, random_state=42)
        clf.fit(Xtr, Y[itr][:, j])
        Sva[:, j] = clf.predict_proba(Xva)[:, 1]
        Ste[:, j] = clf.predict_proba(Xte)[:, 1]
        thr, f2v = pick_threshold(Y[iva][:, j], Sva[:, j], beta=2.0)
        thresholds[t] = {"threshold": thr, "f2_val": f2v,
                         "pos_train": pos, "pos_val": int(Y[iva][:, j].sum())}
        print(f"{t}: thr={thr} F2val={f2v} (0.5 daria "
              f"{fbeta_score(Y[iva][:, j], (Sva[:, j] >= 0.5).astype(int), beta=2.0, zero_division=0):.4f})",
              flush=True)

    def pack(P, S, tag):
        r = {"micro_f1": round(float(f1_score(Y[ite], P, average="micro")), 4),
             "macro_f1": round(float(f1_score(Y[ite], P, average="macro")), 4),
             "hamming": round(float(hamming_loss(Y[ite], P)), 4),
             "subset_acc": round(float(accuracy_score(Y[ite], P)), 4)}
        for j, t in enumerate(TECHS):
            if t in skipped:
                continue
            p = P[:, j]
            tp = int(((p == 1) & (Y[ite][:, j] == 1)).sum())
            fp = int(((p == 1) & (Y[ite][:, j] == 0)).sum())
            fn = int(((p == 0) & (Y[ite][:, j] == 1)).sum())
            prec = tp / (tp + fp) if tp + fp else 0.0
            rec = tp / (tp + fn) if tp + fn else 0.0
            try:
                ap = round(float(average_precision_score(Y[ite][:, j], S[:, j])), 4)
            except Exception:
                ap = 0.0
            per_label.setdefault(tag, {})[t] = {
                "threshold": thresholds[t]["threshold"], "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1": round(2 * prec * rec / (prec + rec), 4) if prec + rec else 0.0,
                "pr_auc": ap, "support": int(Y[ite][:, j].sum())}
        return r

    Pt = np.zeros_like(Y[ite])
    for j, t in enumerate(TECHS):
        if t not in skipped:
            Pt[:, j] = (Ste[:, j] >= thresholds[t]["threshold"]).astype(int)
    P05 = (Ste >= 0.5).astype(int)
    res = {"model": "m4t-thresholds-v1", "labels": TECHS,
           "split": "train<=q60 / val q60-q80 / test>q80 por timestamp",
           "beta": 2.0, "skipped": skipped,
           "n_train": int(itr.sum()), "n_val": int(iva.sum()), "n_test": int(ite.sum()),
           "tuned": pack(Pt, Ste, "tuned"), "fixed_05": pack(P05, Ste, "fixed_05"),
           "thresholds": thresholds, "per_label": per_label}
    print("tuned:", res["tuned"])
    print("fixed_05:", res["fixed_05"])
    (ROOT / "models" / "m4t_metrics.json").write_text(json.dumps(res, indent=2))
    print("guardado models/m4t_metrics.json")


if __name__ == "__main__":
    main()
