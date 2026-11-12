"""M3 grafo: features tabulares + estadisticas de vecinos previos (5 min) -> XGBoost.
Corre: uv run python experiments/m3_grafo/train.py --n 30000
Guarda: models/m3.pkl y models/m3_metrics.json. Mismo split temporal y metricas que M1/M2.
Vecindario: eventos previos que comparten host/credencial en [t-300s, t).
"""
# ponytail: indice hash full-data (rapido) + agregacion solo del sample; feats sin labels
import argparse
import json
import pickle
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (classification_report, f1_score,
                             average_precision_score, roc_curve)
from sklearn.preprocessing import LabelEncoder, OneHotEncoder
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.temporal_split import WINDOW_LABELS, population_summary, temporal_windows

CATS = ["message_type", "stream_name", "product_name", "vendor_name", "pipeline",
        "org_id", "action", "severity", "protocol"]
NUMS = ["hour", "msg_len", "lag_h"]
GFEATS = ["n_neigh", "n_hosts", "n_users", "frac_block",
          "frac_fw", "frac_authfail", "n_types", "span_min"]
W = 300  # ±5 min
ECOLS = ["src_ip", "dst_ip", "username"]


def features(df):
    df = df.copy()
    ts = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    df["hour"] = ts.dt.hour
    df["msg_len"] = df["message_sanitized"].fillna("").str.len()
    df["lag_h"] = ((df["timestamp"] - df["event_time"]) / 3600).clip(-1e4, 1e4).fillna(-1)
    for c in CATS:
        df[c] = df[c].fillna("").astype(str)
    return df


def sample30k(df, n):
    mal = df[df.label_binary == "malicious"]
    rest = df[df.label_binary != "malicious"]
    n_rest = max(n - len(mal), 2000)
    sus = rest[rest.label_binary == "suspicious"]
    ben = rest[rest.label_binary == "benign"]
    n_sus = min(len(sus), n_rest // 3)
    out = pd.concat([mal, sus.sample(n_sus, random_state=42),
                     ben.sample(min(len(ben), n_rest - n_sus), random_state=42)])
    return out.sample(frac=1.0, random_state=42)


def graph_feats(full, sample_pos):
    """Agrega vecindario para las posiciones dadas. full: df con ts/entidades."""
    ts = full["timestamp"].to_numpy()
    msg = full["message_type"].to_numpy()
    act = full["action"].fillna("").to_numpy()
    src = full["src_ip"].fillna("").to_numpy()
    dst = full["dst_ip"].fillna("").to_numpy()
    usr = full["username"].fillna("").to_numpy()
    org = full["org_id"].fillna("").astype(str).to_numpy()
    index, ent = {}, {}
    pos = pd.Series(np.arange(len(full)))
    for c, vals in (("s", src), ("d", dst), ("u", usr)):
        key = np.char.add(org, np.char.add("|", vals.astype(str)))
        ent[c] = key
        for k, s in pos.groupby(key):
            if k.endswith("|"):
                continue
            arr = s.to_numpy()
            index[(c, k)] = arr[np.argsort(ts[arr])]
    print(f"entidades: {len(index)}", flush=True)
    out = np.zeros((len(sample_pos), 8), dtype=np.float32)
    for j, i in enumerate(sample_pos):
        neighbor_slices = []
        for c in ("s", "d", "u"):
            k = ent[c][i]
            if k.endswith("|"):
                continue
            arr = index.get((c, k))
            if arr is None:
                continue
            lo = np.searchsorted(ts[arr], ts[i] - W, side="left")
            hi = np.searchsorted(ts[arr], ts[i], side="left")
            if hi > lo:
                neighbor_slices.append(arr[lo:hi])
        if neighbor_slices:
            # ponytail: NumPy dedup faster than building Python sets per event.
            nb = neighbor_slices[0] if len(neighbor_slices) == 1 else np.unique(np.concatenate(neighbor_slices))
            nb = nb[nb != i]
        else:
            nb = np.empty(0, dtype=np.int64)
        if nb.size:
            hosts = np.unique(np.concatenate((src[nb], dst[nb])))
            n_hosts = int(np.count_nonzero(hosts != ""))
            users = np.unique(usr[nb])
            n_users = int(np.count_nonzero(users != ""))
            a, m, t = act[nb], msg[nb], ts[nb]
            out[j] = [len(nb), n_hosts, n_users,
                      float(np.mean(a == "block")),
                      float(np.mean(m == "firewall_action")),
                      float(np.mean(m == "auth_failure")),
                      float(len(np.unique(m))),
                      float(t.max() - t.min()) / 60.0]
        if (j + 1) % 10000 == 0:
            print(f"{j + 1}/{len(sample_pos)}", flush=True)
    return pd.DataFrame(out, columns=GFEATS)


def main(n):
    fcols = ["timestamp", "org_id", "message_type", "action"] + ECOLS
    full = pd.read_parquet(ROOT / "data" / "signals" / "signals.parquet", columns=fcols)
    cols = ["artifact_id", "label_binary", "timestamp", "event_time",
            "message_sanitized"] + CATS
    raw = pd.read_parquet(ROOT / "data" / "signals" / "signals.parquet", columns=cols)
    train_pop, test, drift = temporal_windows(raw)
    train_df = features(sample30k(train_pop, n))
    test_df = features(test)
    train_graph = graph_feats(full, train_df.index.to_numpy())
    test_graph = graph_feats(full, test_df.index.to_numpy())
    train_df = train_df.reset_index(drop=True).join(train_graph.reset_index(drop=True))
    test_df = test_df.reset_index(drop=True).join(test_graph.reset_index(drop=True))
    X_train, y_train = train_df[CATS + NUMS + GFEATS], train_df["label_binary"]
    X_test, y_test = test_df[CATS + NUMS + GFEATS], test_df["label_binary"]

    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", max_categories=30), CATS),
        ("num", "passthrough", NUMS + GFEATS),
    ])
    Xtr, Xte = pre.fit_transform(X_train), pre.transform(X_test)
    le = LabelEncoder().fit(sorted(y_train.unique().tolist()))
    ytr, yte = le.transform(y_train), le.transform(y_test)
    counts = pd.Series(ytr).value_counts()
    sw = pd.Series(ytr).map(len(ytr) / (len(counts) * counts)).to_numpy()
    clf = XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.08,
                        subsample=0.8, colsample_bytree=0.8, tree_method="hist",
                        objective="multi:softprob", num_class=3,
                        eval_metric="mlogloss", n_jobs=-1, random_state=42)
    clf.fit(Xtr, ytr, sample_weight=sw)
    p = le.inverse_transform(clf.predict(Xte))
    proba = clf.predict_proba(Xte)
    classes = le.classes_.tolist()

    rep = classification_report(y_test, p, output_dict=True, zero_division=0)
    f1m = f1_score(y_test, p, average="macro")
    print(classification_report(y_test, p, zero_division=0))
    print("F1-macro:", f1m)
    prauc = {}
    for i, c in enumerate(classes):
        try:
            prauc[c] = round(float(average_precision_score((yte == i).astype(int), proba[:, i])), 4)
        except Exception:
            prauc[c] = 0.0
    mal_i = classes.index("malicious")
    fpr, tpr, _ = roc_curve((yte == mal_i).astype(int), proba[:, mal_i])
    ok = fpr <= 0.01
    r1 = round(float(tpr[ok].max()) if ok.any() else 0.0, 4)
    print("recall malicious @1% FPR:", r1)
    metrics = {"model": "m3-neighbor-xgb-v2", "f1_macro": round(float(f1m), 4),
               "recall_mal_at_1fpr": r1,
               "per_class": {c: {"precision": round(rep[c]["precision"], 4),
                                 "recall": round(rep[c]["recall"], 4),
                                 "f1": round(rep[c]["f1-score"], 4),
                                 "support": int(rep[c]["support"]), "pr_auc": prauc[c]}
                             for c in classes},
               "n_train": len(y_train), "n_test": len(y_test),
               "evaluation": {"windows": WINDOW_LABELS,
                              "test": population_summary(test),
                              "drift": population_summary(drift)},
               "config": {"vecindario": "±5min por host/credencial (ORG|valor)",
                          "agregacion": "8 estadísticas de vecinos previos + XGBoost 300x6",
                          "split": "fixed UTC temporal window", "sample_n": n}}
    (ROOT / "models" / "m3_metrics.json").write_text(json.dumps(metrics, indent=2))
    with open(ROOT / "models" / "m3.pkl", "wb") as f:
        pickle.dump({"tab": pre, "clf": clf, "le": le,
                     "meta": {"cats": CATS, "nums": NUMS, "gfeats": GFEATS}}, f)
    print("guardado models/m3.pkl F1:", metrics["f1_macro"],
          "mal-recall:", metrics["per_class"]["malicious"]["recall"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30000)
    main(ap.parse_args().n)
