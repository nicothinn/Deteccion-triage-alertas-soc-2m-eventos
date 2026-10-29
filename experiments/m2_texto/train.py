"""M2 texto+tabular: TF-IDF 5k sobre message_sanitized + P1-P3 tabular -> XGBoost.
Corre: uv run python experiments/m2_texto/train.py --n 30000
Guarda: models/m2.pkl (vectorizer + tabular + clf) y models/m2_metrics.json.
Mismo protocolo que M1 (split temporal 80/20) o no vale comparar.
MiniLM despues: --encoder miniml (requiere sentence-transformers).
"""
# ponytail: TF-IDF primero (gana con poco dato), mismo split y metricas que M1
import argparse
import json
import pickle
from pathlib import Path

import pandas as pd
from scipy.sparse import hstack
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report, f1_score, average_precision_score, roc_curve
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[2]
CATS = ["message_type", "stream_name", "product_name", "vendor_name", "pipeline",
        "org_id", "action", "severity", "protocol"]
NUMS = ["hour", "msg_len", "lag_h"]
TEXT = "message_sanitized"


def features(df):
    df = df.copy()
    ts = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    df["hour"] = ts.dt.hour
    df["msg_len"] = df[TEXT].fillna("").str.len()
    df["lag_h"] = ((df["timestamp"] - df["event_time"]) / 3600).clip(-1e4, 1e4).fillna(-1)
    for c in CATS:
        df[c] = df[c].fillna("").astype(str)
    df[TEXT] = df[TEXT].fillna("")
    return df


def sample30k(df, n):
    # ponytail: todos los malicious + resto estratificado hasta n
    mal = df[df.label_binary == "malicious"]
    rest = df[df.label_binary != "malicious"]
    n_rest = max(n - len(mal), 2000)
    sus = rest[rest.label_binary == "suspicious"]
    ben = rest[rest.label_binary == "benign"]
    n_sus = min(len(sus), n_rest // 3)
    n_ben = min(len(ben), n_rest - n_sus)
    out = pd.concat([mal, sus.sample(n_sus, random_state=42),
                     ben.sample(n_ben, random_state=42)])
    return out.sample(frac=1.0, random_state=42).reset_index(drop=True)


def recall_at_fpr(y_true, scores, fpr_max=0.01):
    fpr, tpr, _ = roc_curve(y_true, scores)
    ok = fpr <= fpr_max
    return round(float(tpr[ok].max()) if ok.any() else 0.0, 4)


def main(n, encoder):
    cols = ["label_binary", "timestamp", "event_time", TEXT] + CATS
    df = pd.read_parquet(ROOT / "data" / "signals" / "signals.parquet", columns=cols)
    df = features(sample30k(df, n))
    X, y = df[CATS + NUMS + [TEXT]], df["label_binary"]
    cutoff = df["timestamp"].quantile(0.8)
    tr, te = (df["timestamp"] <= cutoff).to_numpy(), (df["timestamp"] > cutoff).to_numpy()

    if encoder == "miniml":
        from sentence_transformers import SentenceTransformer  # requiere pip extra
        enc = SentenceTransformer("all-MiniLM-L6-v2")
        import numpy as np
        Ttr = enc.encode(X[TEXT][tr].tolist(), show_progress_bar=False,
                         batch_size=256).astype("float32")
        Tte = enc.encode(X[TEXT][te].tolist(), show_progress_bar=False,
                         batch_size=256).astype("float32")
        enc_name, vec = "minilm-384", enc
    else:
        vec = TfidfVectorizer(max_features=5000, ngram_range=(1, 2),
                              sublinear_tf=True, min_df=5)
        Ttr = vec.fit_transform(X[TEXT][tr].tolist())
        Tte = vec.transform(X[TEXT][te].tolist())
        enc_name = "tfidf-5k"

    tab = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", max_categories=30), CATS),
        ("num", "passthrough", NUMS),
    ])
    Atr = tab.fit_transform(X[tr][CATS + NUMS])
    Ate = tab.transform(X[te][CATS + NUMS])
    import numpy as np
    Xtr = hstack([Ttr, Atr]).tocsr()
    Xte = hstack([Tte, Ate]).tocsr()

    # ponytail: multi:softprob no acepta scale_pos_weight; sample_weight por clase = equivalente
    # xgboost>=3 exige labels enteros -> LabelEncoder + mapeo inverso al reportar
    from sklearn.preprocessing import LabelEncoder
    le = LabelEncoder().fit(sorted(y[tr].unique().tolist()))
    ytr, yte = le.transform(y[tr]), le.transform(y[te])
    counts = y[tr].value_counts()
    w = len(y[tr]) / (len(counts) * counts)
    sw = y[tr].map(w).to_numpy()
    clf = XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.08,
                        subsample=0.8, colsample_bytree=0.8, tree_method="hist",
                        objective="multi:softprob", num_class=3,
                        eval_metric="mlogloss", n_jobs=-1, random_state=42)
    clf.fit(Xtr, ytr, sample_weight=sw)
    p = le.inverse_transform(clf.predict(Xte))
    proba = clf.predict_proba(Xte)
    classes = le.classes_.tolist()

    rep = classification_report(y[te], p, output_dict=True, zero_division=0)
    f1m = f1_score(y[te], p, average="macro")
    print(classification_report(y[te], p, zero_division=0))
    print("F1-macro:", f1m)
    prauc, per_class = {}, {}
    for i, c in enumerate(classes):
        try:
            prauc[str(c)] = round(float(average_precision_score((yte == i).astype(int), proba[:, i])), 4)
        except Exception:
            prauc[str(c)] = 0.0
    for c in classes:
        per_class[c] = {"precision": round(rep[c]["precision"], 4),
                        "recall": round(rep[c]["recall"], 4),
                        "f1": round(rep[c]["f1-score"], 4),
                        "support": int(rep[c]["support"]), "pr_auc": prauc[str(c)]}
    mal_idx = classes.index("malicious")
    r1 = recall_at_fpr((yte == mal_idx).astype(int), proba[:, mal_idx])
    print("recall malicious @1% FPR:", r1)
    metrics = {"model": "m2-texto-v1", "encoder": enc_name, "f1_macro": round(float(f1m), 4),
               "recall_mal_at_1fpr": r1, "per_class": per_class,
               "n_train": int(tr.sum()), "n_test": int(te.sum()),
               "config": {"tfidf": "5k word+char sublinear min_df=5" if enc_name == "tfidf-5k" else enc_name,
                          "xgb": "300x6 lr=0.08 subsample=0.8", "split": "temporal 80/20",
                          "sample_n": n, "class_weight": "sample_weight balanceado"}}
    (ROOT / "models" / "m2_metrics.json").write_text(json.dumps(metrics, indent=2))
    with open(ROOT / "models" / "m2.pkl", "wb") as f:
        pickle.dump({"vectorizer": vec, "encoder": enc_name, "tab": tab,
                     "clf": clf, "le": le, "meta": {"cats": CATS, "nums": NUMS}}, f)
    print("guardado models/m2.pkl", enc_name, metrics["f1_macro"], "mal-recall:", per_class["malicious"]["recall"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30000)
    ap.add_argument("--encoder", choices=["tfidf", "miniml"], default="tfidf")
    a = ap.parse_args()
    main(a.n, a.encoder)
