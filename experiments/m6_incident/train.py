"""M6: clasificacion ATT&CK a nivel incidente (receta literatura, sin reinventar).
M6a (TRAM-style): XGB por tecnica a nivel senal (arquitectura M4b) -> voto max por incidente.
M6b (baseline): feats agregadas por incidente -> XGB por tecnica.
Labels: multilabel presencia (el mayoritario sale degenerado: 48440/48441 dan T1041).
Split: por tiempo de incidente (min timestamp), cuantil 80.
Corre: uv run python experiments/m6_incident/train.py
Guarda: models/m6_metrics.json.
"""
# ponytail: dos recetas baratas, mismo split y metricas; gana la literatura (M6a) o el agregado
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import hstack
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (accuracy_score, average_precision_score, f1_score,
                             hamming_loss)
from sklearn.preprocessing import MultiLabelBinarizer, OneHotEncoder
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[2]
TECHS = ["T1190", "T1041", "T1567", "T1204", "T1486", "T1566"]
CATS = ["message_type", "stream_name", "product_name", "vendor_name", "pipeline",
        "org_id", "action", "severity", "protocol"]
TEXT = "message_sanitized"

IFEATS = ["n_signals", "span_min", "frac_block", "frac_fw", "n_types",
          "n_hosts", "n_users", "hour"]


def parse_labels(v):
    try:
        return [x for x in (json.loads(v) if v else []) if x in TECHS]
    except Exception:
        return []


def first_id(v):
    try:
        ids = json.loads(v) if v else []
        return ids[0] if ids else "?"
    except Exception:
        return "?"


def build_incidents(df):
    """Agrega senales a un vector por incidente + matriz multilabel presencia."""
    df = df.copy()
    if "iid" not in df.columns:
        df["iid"] = df["incident_ids"].fillna("").map(first_id)
    df = df[df["iid"] != "?"].reset_index(drop=True)
    df["tech_list"] = df["attack_techniques"].fillna("").map(parse_labels)
    for c in ["message_type", "action", "org_id", "src_ip", "dst_ip", "username"]:
        df[c] = df[c].fillna("").astype(str)
    df["hour"] = pd.to_datetime(df["timestamp"], unit="s", utc=True).dt.hour
    rows = []
    for iid, g in df.groupby("iid"):
        ts = g["timestamp"].to_numpy()
        hosts = set(g["src_ip"].tolist()) | set(g["dst_ip"].tolist())
        hosts.discard("")
        users = set(g["username"].tolist())
        users.discard("")
        rows.append({
            "iid": iid,
            "t0": float(ts.min()),
            "n_signals": len(g),
            "span_min": float(ts.max() - ts.min()) / 60.0,
            "frac_block": float((g["action"] == "block").mean()),
            "frac_fw": float((g["message_type"] == "firewall_action").mean()),
            "n_types": int(g["message_type"].nunique()),
            "n_hosts": len(hosts),
            "n_users": len(users),
            "hour": int(g["hour"].median()),
            "org": g["org_id"].mode().iloc[0] if len(g) else "",
            "tech_list": sorted({t for lst in g["tech_list"] for t in lst}),
        })
    inc = pd.DataFrame(rows).sort_values("t0").reset_index(drop=True)
    Y = MultiLabelBinarizer(classes=TECHS).fit_transform(inc["tech_list"])
    return inc, Y


def incident_vote(proba, labels):
    """Voto max por incidente (TRAM-style): la senal mas segura manda."""
    return proba.groupby("iid", as_index=False)[list(labels)].max()


def signal_matrix(df, vec=None, tab=None, fit=True):
    msg = df[TEXT].fillna("")
    if fit:
        vec = TfidfVectorizer(max_features=5000, ngram_range=(1, 2),
                              sublinear_tf=True, min_df=5)
        T = vec.fit_transform(msg.tolist())
    else:
        T = vec.transform(msg.tolist())
    if fit:
        tab = ColumnTransformer([
            ("cat", OneHotEncoder(handle_unknown="ignore", max_categories=30), CATS),
            ("num", "passthrough", ["hour_sig", "msg_len", "lag_h"]),
        ])
        A = tab.fit_transform(df[CATS + ["hour_sig", "msg_len", "lag_h"]])
    else:
        A = tab.transform(df[CATS + ["hour_sig", "msg_len", "lag_h"]])
    return hstack([T, A]).tocsr(), vec, tab


def fit_binary(Xtr, y, pos_label):
    pos = int(y.sum())
    neg = len(y) - pos
    if pos < 2:
        return None
    clf = XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.08,
                        subsample=0.8, colsample_bytree=0.8, tree_method="hist",
                        objective="binary:logistic", scale_pos_weight=neg / pos,
                        eval_metric="logloss", n_jobs=-1, random_state=42)
    clf.fit(Xtr, y)
    return clf


def report(name, Yte, P, S, labels, skipped, extra=None):
    res = {"model": name,
           "micro_f1": round(float(f1_score(Yte, P, average="micro")), 4),
           "macro_f1": round(float(f1_score(Yte, P, average="macro")), 4),
           "hamming": round(float(hamming_loss(Yte, P)), 4),
           "subset_acc": round(float(accuracy_score(Yte, P)), 4),
           "skipped": skipped,
           "n_train": int(extra["n_train"]), "n_test": int(extra["n_test"])}
    prauc, per = {}, {}
    for j, t in enumerate(labels):
        try:
            ap = round(float(average_precision_score(Yte[:, j], S[:, j])), 4)
        except Exception:
            ap = 0.0
        prauc[t] = ap
        per[t] = {"support": int(Yte[:, j].sum()), "pr_auc": ap}
    res["pr_auc"] = prauc
    res["per_label_support"] = {t: per[t] for t in labels}
    print(f"=== {name} micro={res['micro_f1']} macro={res['macro_f1']} ===")
    return res


def main():
    cols = ["timestamp", "event_time", TEXT, "attack_techniques", "incident_ids",
            "message_type", "stream_name", "product_name", "vendor_name",
            "pipeline", "org_id", "action", "severity", "protocol",
            "src_ip", "dst_ip", "username"]
    df = pd.read_parquet(ROOT / "data" / "signals" / "incident_signals.parquet",
                         columns=cols)
    print("signals:", len(df))
    df["iid"] = df["incident_ids"].fillna("").map(first_id)
    df = df[df["iid"] != "?"].reset_index(drop=True)
    inc, Y = build_incidents(df)
    print("incidentes:", len(inc))
    print("positivos por tecnica:", {t: int(Y[:, j].sum()) for j, t in enumerate(TECHS)})
    cut = inc["t0"].quantile(0.8)
    tr = (inc["t0"] <= cut).to_numpy()
    te = ~tr
    print(f"train/test incidentes: {tr.sum()}/{te.sum()}")
    out = {"split": "por tiempo de incidente (min timestamp), cuantil 80",
           "labels": TECHS}

    # --- M6b: feats agregadas ---
    tab6 = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), ["org"]),
        ("num", "passthrough", IFEATS),
    ])
    Atr = tab6.fit_transform(inc[tr][["org"] + IFEATS])
    Ate = tab6.transform(inc[te][["org"] + IFEATS])
    Pb = np.zeros_like(Y[te])
    Sb = np.zeros_like(Y[te], dtype=float)
    skipped_b = []
    for j, t in enumerate(TECHS):
        clf = fit_binary(Atr, Y[tr][:, j], t)
        if clf is None:
            skipped_b.append(t)
            continue
        Sb[:, j] = clf.predict_proba(Ate)[:, 1]
        Pb[:, j] = (Sb[:, j] >= 0.5).astype(int)
        print(f"M6b {t}: pos train {int(Y[tr][:, j].sum())}", flush=True)
    out["m6b"] = report("m6b-agregado-v1", Y[te], Pb, Sb, TECHS, skipped_b,
                        {"n_train": tr.sum(), "n_test": te.sum()})

    # --- M6a: senal -> voto max (TRAM-style, arquitectura M4b) ---
    tr_iids = set(inc[tr]["iid"])
    dtr = df[df["iid"].isin(tr_iids)].copy()
    dte = df[~df["iid"].isin(tr_iids)].copy()
    for d in (dtr, dte):
        d["hour_sig"] = pd.to_datetime(d["timestamp"], unit="s", utc=True).dt.hour
        d["msg_len"] = d[TEXT].fillna("").str.len()
        d["lag_h"] = ((d["timestamp"] - d["event_time"]) / 3600).clip(-1e4, 1e4).fillna(-1)
        for c in CATS:
            d[c] = d[c].fillna("").astype(str)
        d[TEXT] = d[TEXT].fillna("")
    Ytr = MultiLabelBinarizer(classes=TECHS).fit_transform(
        dtr["attack_techniques"].fillna("").map(parse_labels))
    Yt = MultiLabelBinarizer(classes=TECHS).fit_transform(
        dte["attack_techniques"].fillna("").map(parse_labels))
    Xtr, vec, tab = signal_matrix(dtr, fit=True)
    Xte, _, _ = signal_matrix(dte, vec, tab, fit=False)
    print("X senal:", Xtr.shape, Xte.shape)
    Sall = np.zeros((len(dte), len(TECHS)))
    skipped_a = []
    for j, t in enumerate(TECHS):
        clf = fit_binary(Xtr, Ytr[:, j], t)
        if clf is None:
            skipped_a.append(t)
            continue
        Sall[:, j] = clf.predict_proba(Xte)[:, 1]
        print(f"M6a {t}: pos train {int(Ytr[:, j].sum())}", flush=True)
    v = incident_vote(pd.DataFrame(Sall, columns=TECHS).assign(iid=dte["iid"].tolist()),
                      TECHS)
    v = v.set_index("iid").reindex(inc[te]["iid"]).fillna(0.0)
    S = v[TECHS].to_numpy()
    P = (S >= 0.5).astype(int)
    out["m6a"] = report("m6a-tram-vote-v1", Y[te], P, S, TECHS, skipped_a,
                        {"n_train": tr.sum(), "n_test": te.sum()})

    (ROOT / "models" / "m6_metrics.json").write_text(json.dumps(out, indent=2))
    print("guardado models/m6_metrics.json")


if __name__ == "__main__":
    main()
