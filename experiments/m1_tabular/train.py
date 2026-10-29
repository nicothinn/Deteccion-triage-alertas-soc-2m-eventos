"""M1 baseline: tabular LightGBM cost-sensitive sobre signals (sample estratificado).
Corre: uv run python experiments/m1_tabular/train.py --n 200000
Guarda: models/m1.pkl (pipeline + modelo + meta). Métrica: F1-macro + PR-AUC (no accuracy, IR 245:1).
"""
# ponytail: un script, sample estratificado, split temporal simple
import argparse, pickle, json
from pathlib import Path
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.metrics import f1_score, average_precision_score, classification_report
from lightgbm import LGBMClassifier

ROOT = Path(__file__).resolve().parents[2]
CATS = ["message_type", "stream_name", "product_name", "vendor_name", "pipeline", "org_id", "action", "severity", "protocol"]
NUMS = ["hour", "msg_len", "lag_h"]

def features(df):
    df = df.copy()
    ts = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    df["hour"] = ts.dt.hour
    df["msg_len"] = df["message_sanitized"].str.len().fillna(0)
    df["lag_h"] = ((df["timestamp"] - df["event_time"]) / 3600).clip(-1e4, 1e4).fillna(-1)
    for c in CATS:
        df[c] = df[c].fillna("").astype(str)
    return df

def main(n):
    df = pd.read_parquet(ROOT / "data" / "signals" / "signals.parquet")
    df = features(df)
    # sample estratificado por label para que entre malicious
    df = df.groupby("label_binary", group_keys=False).apply(
        lambda g: g.sample(min(len(g), max(n // 3, 2000)), random_state=42)
    )
    X = df[CATS + NUMS]
    y = df["label_binary"]
    # split temporal: train pasado, test futuro (drift SOC)
    cutoff = df["timestamp"].quantile(0.8)
    tr, te = df["timestamp"] <= cutoff, df["timestamp"] > cutoff
    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", max_categories=30), CATS),
        ("num", "passthrough", NUMS),
    ])
    clf = LGBMClassifier(n_estimators=200, learning_rate=0.08, num_leaves=63,
                         class_weight="balanced", n_jobs=-1, verbose=-1)
    pipe = Pipeline([("pre", pre), ("clf", clf)])
    pipe.fit(X[tr], y[tr])
    p = pipe.predict(X[te])
    proba = pipe.predict_proba(X[te])
    rep = classification_report(y[te], p, output_dict=True, zero_division=0)
    f1m = f1_score(y[te], p, average="macro")
    print(classification_report(y[te], p, zero_division=0))
    print("F1-macro:", f1m)
    # ponytail: PR-AUC por clase + json para /model/metrics y el paper
    prauc = {}
    for i, c in enumerate(pipe.classes_):
        try:
            prauc[str(c)] = round(float(average_precision_score((y[te] == c).astype(int), proba[:, i])), 4)
        except Exception:
            prauc[str(c)] = 0.0
    per_class = {c: {"precision": round(rep[c]["precision"], 4), "recall": round(rep[c]["recall"], 4),
                     "f1": round(rep[c]["f1-score"], 4), "support": int(rep[c]["support"]),
                 "pr_auc": prauc[c]}
                 for c in pipe.classes_}
    metrics = {"model": "m1-tabar-v1", "f1_macro": round(float(f1m), 4),
               "per_class": per_class, "n_train": int(tr.sum()), "n_test": int(te.sum()),
               "config": {"n_estimators": 200, "learning_rate": 0.08, "num_leaves": 63,
                          "class_weight": "balanced", "split": "temporal 80/20", "sample_n": n}}
    (ROOT / "models" / "m1_metrics.json").write_text(json.dumps(metrics, indent=2))
    meta = {"cats": CATS, "nums": NUMS, "classes": sorted(y.unique().tolist()),
            "n_train": int(tr.sum()), "n_test": int(te.sum())}
    with open(ROOT / "models" / "m1.pkl", "wb") as f:
        pickle.dump({"pipe": pipe, "meta": meta}, f)
    (ROOT / "models" / "m1_meta.json").write_text(json.dumps(meta, indent=2))
    print("guardado models/m1.pkl", meta)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200000)
    main(ap.parse_args().n)
