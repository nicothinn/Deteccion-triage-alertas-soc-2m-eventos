"""API SOC Precinct6: sirve M1 tabular (+ stubs M2/M3). uv run uvicorn app.main:app --reload"""
# ponytail: un archivo, carga perezosa del pkl, sin capas de más
import json
import pickle
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
MODEL = {"pipe": None, "meta": None, "name": "m1-stub",
         "m2": None, "m2name": "m2-stub",
         "m3": None, "m3name": "m3-stub"}

# ponytail: tecnicas ATT&CK derivadas del tier (oraculo M4: micro-F1 0.9994 en test temporal;
# en live son priors de regla, no atribucion por evento — ver notebooks/m4b_xgb_pertecnica_out.ipynb).
# M4b-XGB aprendido NO se despliega (T1041/T1567 P 0.08 mentirian al analista).
TIER_TECH = {
    "malicious": (["T1190", "T1041", "T1567"], ["TA0001", "TA0010"]),
    "suspicious": (["T1190"], ["TA0001"]),
    "benign": ([], []),
}
TECH_SRC = "tier-mapping M4-oracle (micro-F1 0.9994 test temporal)"
BASELINE = {"f1_macro": 0.599, "n_train": 112848, "note": "M1 tabular, split temporal 80/20, IR 245:1"}
SIG = ROOT / "data" / "signals" / "signals.parquet"
REP = ROOT / "data" / "graph" / "attack_reports.parquet"
QCOLS = ["artifact_id", "timestamp", "message_type", "stream_name", "pipeline",
         "product_name", "vendor_name", "src_ip", "dst_ip", "action",
         "severity", "protocol", "label_binary", "attack_techniques", "attack_tactics",
         "message_sanitized", "org_id", "incident_ids"]
# ponytail: conteos fijos del EDA, evita escanear 2M por request
STATS = {"total": 2011674, "benign": 1897153, "suspicious": 106793, "malicious": 7728,
         "top_types": {"security_audit_event": 336425, "management_message": 266320,
                       "java_error": 154491, "4662": 115553, "5156": 101277,
                       "firewall_action": 95062},
         "top_orgs": {"ORG-0004": 995985, "ORG-0005": 576817, "ORG-0003": 433904, "ORG-0001": 4968},
         "top_tech": {"T1190": 6120, "T1078": 890, "T1041": 410},
         "severity": {"vacia": 991253, "informational": 479472, "Info": 427432,
                      "warning": 95150, "notice": 17699, "error": 616},
         "disposition": {"Unprocessed": 2005877, "Disrupted": 5779, "Open": 15, "Cold Case": 3},
         "top_products": {"AWS Instance Backup": 543159, "Windows Active Directory": 421587,
                          "Windows Logs": 336425, "VMWare VCenter": 266201, "ASA Firewall": 95143},
         "top_vendors": {"Microsoft": 758482, "Amazon Web Services": 562378, "VMWare": 266201,
                         "Cisco": 95488, "Barracuda": 15261},
         "graph": {"nodes": 47585, "edges": 1740438, "incidents": 51371,
                   "edge_types": {"USER_ACTION": 692375, "AUDIT_EVENT": 336425,
                                  "INCIDENT_LINK": 335645, "NETWORK_FLOW": 323376,
                                  "EVENT": 45063, "DNS_RESOLVE": 7554}},
         "window": "2024-07-26 a 2024-08-01"}

def load():
    pkl = ROOT / "models" / "m1.pkl"
    if pkl.exists():
        with open(pkl, "rb") as f:
            d = pickle.load(f)
        MODEL.update(pipe=d["pipe"], meta=d["meta"], name="m1-tabar-v1")
    m2 = ROOT / "models" / "m2.pkl"
    if m2.exists():
        with open(m2, "rb") as f:
            MODEL["m2"] = pickle.load(f)
        MODEL["m2name"] = "m2-texto-v1"
    m3 = ROOT / "models" / "m3.pkl"
    if m3.exists():
        with open(m3, "rb") as f:
            MODEL["m3"] = pickle.load(f)
        MODEL["m3name"] = "m3-grafo-v1"

@asynccontextmanager
async def lifespan(app: FastAPI):
    load()
    yield

app = FastAPI(title="SOC Precinct6", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class LogIn(BaseModel):
    message_type: str = "firewall_action"
    stream_name: str = "cisco_asa"
    product_name: str = "ASA Firewall"
    vendor_name: str = "Cisco"
    pipeline: str = "syslog"
    org_id: str = "ORG-0004"
    action: str = "block"
    severity: str = "warning"
    protocol: str = "6"
    message: str = Field(default="", description="message_sanitized")

class LogOut(BaseModel):
    label: str
    proba: dict
    techniques: list
    tactics: list
    techniques_source: str = ""
    model: str
    triage: str  # regla operativa: block+malicious→escalar
    m2: dict | None = None  # cascada texto: {label, proba, model}

def featurize(log: LogIn) -> pd.DataFrame:
    now = datetime.now(timezone.utc)
    return pd.DataFrame([{
        "message_type": log.message_type, "stream_name": log.stream_name,
        "product_name": log.product_name, "vendor_name": log.vendor_name,
        "pipeline": log.pipeline, "org_id": log.org_id, "action": log.action,
        "severity": log.severity, "protocol": log.protocol,
        "hour": now.hour, "msg_len": len(log.message), "lag_h": -1,
    }])

def predict(df: pd.DataFrame):
    if MODEL["pipe"] is None:
        return "benign", {"benign": 1.0}
    pipe = MODEL["pipe"]
    proba = pipe.predict_proba(df)[0]
    labels = list(pipe.classes_)
    return labels[int(proba.argmax())], {k: round(float(v), 4) for k, v in zip(labels, proba)}

def predict_m2(log: LogIn):
    # ponytail: misma P1-P3 que train.py + TF-IDF del mensaje
    from scipy.sparse import hstack
    m = MODEL["m2"]
    if m is None:
        return None
    now = datetime.now(timezone.utc)
    msg = log.message or ""
    row = pd.DataFrame([{
        "message_type": log.message_type, "stream_name": log.stream_name,
        "product_name": log.product_name, "vendor_name": log.vendor_name,
        "pipeline": log.pipeline, "org_id": log.org_id, "action": log.action,
        "severity": log.severity, "protocol": log.protocol,
        "hour": now.hour, "msg_len": len(msg), "lag_h": -1,
        "word_count": len(msg.split()),
        "digit_ratio": sum(c.isdigit() for c in msg) / max(len(msg), 1),
        "upper_ratio": sum(c.isupper() for c in msg) / max(len(msg), 1),
    }])
    T = m["vectorizer"].transform([msg])
    A = m["tab"].transform(row[m["meta"]["cats"] + m["meta"]["nums"]])
    proba = m["clf"].predict_proba(hstack([T, A]).tocsr())[0]
    labels = list(m["le"].inverse_transform(range(len(proba))))
    lab = labels[int(proba.argmax())]
    return {"label": lab, "proba": {k: round(float(v), 4) for k, v in zip(labels, proba)},
            "model": MODEL["m2name"]}

GCOLS = ["artifact_id", "timestamp", "event_time", "org_id", "message_type",
         "stream_name", "product_name", "vendor_name", "pipeline",
         "src_ip", "dst_ip", "username", "action", "severity", "protocol"]

def predict_graph(artifact_id: str):
    # ponytail: slice ±5min por timestamp (pushdown) + match de entidades; sin indice en RAM
    m = MODEL["m3"]
    if m is None:
        raise HTTPException(400, "M3 no cargado")
    import pyarrow.parquet as pq
    tbl = pq.read_table(SIG, columns=GCOLS,
                        filters=[("artifact_id", "=", artifact_id)]).to_pandas()
    if len(tbl) == 0:
        raise HTTPException(404, "artifact_id desconocido")
    c = tbl.iloc[0].fillna("")
    t, org = float(c["timestamp"]), str(c["org_id"])
    win = pq.read_table(
        SIG, columns=["artifact_id", "timestamp", "message_type", "action",
                      "src_ip", "dst_ip", "username"],
        filters=[("timestamp", ">=", t - 300), ("timestamp", "<=", t + 300)]).to_pandas()
    keys = {f"{org}|{c['src_ip']}", f"{org}|{c['dst_ip']}", f"{org}|{c['username']}"} - {f"{org}|"}
    # match por cualquiera de las 3 entidades (host origen, host destino, credencial)
    wfull = win.copy()
    wfull["k"] = org + "|" + wfull["src_ip"].fillna("") + ";" + org + "|" + wfull["dst_ip"].fillna("") + ";" + org + "|" + wfull["username"].fillna("")
    keep = [any(k in row.split(";") for k in keys) for row in wfull["k"]]
    nb = wfull[(wfull["artifact_id"] != artifact_id) & pd.Series(keep, index=wfull.index)]
    feats = [0.0] * 8
    if len(nb):
        hosts = set(nb["src_ip"].fillna("").tolist()) | set(nb["dst_ip"].fillna("").tolist())
        hosts.discard("")
        users = set(nb["username"].fillna("").tolist())
        users.discard("")
        feats = [float(len(nb)), float(len(hosts)), float(len(users)),
                 float((nb["action"] == "block").mean()),
                 float((nb["message_type"] == "firewall_action").mean()),
                 float((nb["message_type"] == "auth_failure").mean()),
                 float(nb["message_type"].nunique()),
                 float(nb["timestamp"].max() - nb["timestamp"].min()) / 60.0]
    row = pd.DataFrame([{
        "message_type": str(c["message_type"]), "stream_name": str(c["stream_name"]),
        "product_name": str(c["product_name"]), "vendor_name": str(c["vendor_name"]),
        "pipeline": str(c["pipeline"]), "org_id": org, "action": str(c["action"]),
        "severity": str(c["severity"]), "protocol": str(c["protocol"]),
        "hour": pd.to_datetime(t, unit="s", utc=True).hour,
        "msg_len": 0, "lag_h": float((t - float(c["event_time"])) / 3600) if c["event_time"] != "" else -1,
        **dict(zip(m["meta"]["gfeats"], feats)),
    }])
    X = m["tab"].transform(row[m["meta"]["cats"] + m["meta"]["nums"] + m["meta"]["gfeats"]])
    proba = m["clf"].predict_proba(X)[0]
    labels = list(m["le"].inverse_transform(range(len(proba))))
    lab = labels[int(proba.argmax())]
    return {"label": lab, "proba": {k: round(float(v), 4) for k, v in zip(labels, proba)},
            "model": MODEL["m3name"], "n_vecinos": int(feats[0])}

class GraphIn(BaseModel):
    artifact_id: str = ""

@app.post("/score_graph")
def score_graph(g: GraphIn):
    try:
        return predict_graph(g.artifact_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, str(e))

@app.get("/health")
def health():
    return {"ok": True, "model": MODEL["name"], "loaded": MODEL["pipe"] is not None,
            "m2": MODEL["m2name"], "m2_loaded": MODEL["m2"] is not None,
            "m3": MODEL["m3name"], "m3_loaded": MODEL["m3"] is not None}

@app.get("/info")
def info():
    return {"dataset": "witfoo/precinct6-cybersecurity (2M)",
            "links": {"hf": "https://huggingface.co/datasets/witfoo/precinct6-cybersecurity",
                      "code": "https://github.com/witfoo/dataset-from-precinct6"},
            "baseline": BASELINE, "classes": (MODEL["meta"] or {}).get("classes", ["benign"])}

@app.get("/stats")
def stats():
    return STATS

@app.get("/model/metrics")
def model_metrics():
    # ponytail: lee el json que escribe train.py; fallback al baseline
    f = ROOT / "models" / "m1_metrics.json"
    out = (json.loads(f.read_text()) if f.exists()
           else {"model": MODEL["name"], "f1_macro": BASELINE["f1_macro"],
                 "n_train": BASELINE["n_train"], "note": "corre train.py para el reporte completo"})
    g = ROOT / "models" / "m2_metrics.json"
    if g.exists():
        out["m2"] = json.loads(g.read_text())
    h = ROOT / "models" / "m3_metrics.json"
    if h.exists():
        out["m3"] = json.loads(h.read_text())
    for m in ("m4_metrics.json", "m4b_metrics.json"):
        f = ROOT / "models" / m
        if f.exists():
            out[m.split("_")[0]] = json.loads(f.read_text())
    return out

@app.post("/explain")
def explain(log: LogIn, top: int = 14):
    # ponytail: importancia global LightGBM x valor activo, sin shap
    if MODEL["pipe"] is None:
        raise HTTPException(400, "modelo no cargado")
    try:
        df = featurize(log)
        pre = MODEL["pipe"].named_steps["pre"]
        clf = MODEL["pipe"].named_steps["clf"]
        names = list(pre.get_feature_names_out())
        vals = pre.transform(df).toarray()[0]
        imps = clf.feature_importances_
    except Exception as e:
        raise HTTPException(400, str(e))
    feats = sorted(({"feature": n, "importance": int(i), "value": round(float(v), 4),
                     "active": bool(v != 0)}
                    for n, i, v in zip(names, imps, vals)),
                   key=lambda d: d["importance"], reverse=True)[:top]
    label, proba = predict(df)
    return {"label": label, "proba": proba, "model": MODEL["name"], "top_features": feats}

class FeedbackIn(BaseModel):
    artifact_id: str = ""
    decision: str = "escalar"  # escalar | monitorear | falso_positivo
    note: str = ""

@app.post("/feedback")
def feedback(fb: FeedbackIn):
    # ponytail: append csv, el analista corrige y eso re-entrena despues
    f = ROOT / "data" / "feedback.csv"
    new = not f.exists()
    with open(f, "a", encoding="utf-8") as fh:
        if new:
            fh.write("ts,artifact_id,decision,note\n")
        note = fb.note.replace("\n", " ").replace(",", ";")[:500]
        fh.write(f"{datetime.now(timezone.utc).isoformat()},{fb.artifact_id},{fb.decision},{note}\n")
    n = sum(1 for _ in open(f, encoding="utf-8")) - 1
    return {"ok": True, "n": n}

@app.get("/graph/vecindario")
def vecindario(node: str, tipos: str = "", limit: int = 150):
    # ponytail: 1 salto sobre 1.7M aristas, acotado por limit
    gf = ROOT / "data" / "graph" / "edges-00000.parquet"
    nf = ROOT / "data" / "graph" / "nodes.parquet"
    if not gf.exists():
        raise HTTPException(404, "grafo no disponible")
    e = pd.read_parquet(gf, columns=["src", "dst", "type"])
    m = (e["src"] == node) | (e["dst"] == node)
    if tipos:
        want = {t.strip() for t in tipos.split(",") if t.strip()}
        m &= e["type"].isin(want)
    e = e[m].head(limit)
    ids = {node} | set(e["src"]) | set(e["dst"])
    nodes_out = []
    if nf.exists():
        n = pd.read_parquet(nf)
        n = n[n["node_id"].isin(ids)]
        for _, r in n.iterrows():
            a = r["attrs"] if isinstance(r["attrs"], dict) else {}
            def num(k, d=0):
                try:
                    v = a.get(k, d)
                    return float(v) if v is not None else d
                except Exception:
                    return d
            nodes_out.append({"id": r["node_id"], "type": r["type"],
                              "signal_count": int(num("signal_count")),
                              "suspicion": round(num("suspicion_score"), 4),
                              "org": str(a.get("org_id", ""))})
    return {"node": node, "n_edges": len(e), "nodes": nodes_out,
            "edges": [{"src": r["src"], "dst": r["dst"], "type": r["type"]}
                      for _, r in e.iterrows()]}

@app.get("/queue")
def queue(label: str = "all", limit: int = 60):
    # ponytail: maliciosos primero, sin paginacion real
    df = pd.read_parquet(SIG, columns=QCOLS)
    if label != "all":
        df = df[df.label_binary == label]
        out = df.sort_values("timestamp", ascending=False).head(limit)
    else:
        mal = df[df.label_binary == "malicious"]
        sus = df[df.label_binary == "suspicious"].sample(min((df.label_binary == "suspicious").sum(), limit // 2), random_state=7)
        ben = df[df.label_binary == "benign"].sample(min((df.label_binary == "benign").sum(), limit // 4), random_state=7)
        out = pd.concat([mal.head(limit // 4), sus, ben]).sort_values("timestamp", ascending=False).head(limit)
    return out.fillna("").to_dict("records")

@app.get("/incident/{inc_id}")
def incident(inc_id: str, limit: int = 200):
    df = pd.read_parquet(SIG)
    ev = df[df["incident_ids"].str.contains(inc_id, na=False)].sort_values("timestamp").head(limit)
    rep = None
    if REP.exists():
        r = pd.read_parquet(REP)
        hit = r[r.incident_id == inc_id]
        if len(hit):
            rep = hit.iloc[0].fillna("").to_dict()
    return {"incident_id": inc_id, "n": int((df["incident_ids"].str.contains(inc_id, na=False)).sum()),
            "events": ev.fillna("").to_dict("records"), "report": rep}

@app.post("/score", response_model=LogOut)
def score(log: LogIn):
    try:
        label, proba = predict(featurize(log))
        m2 = predict_m2(log)
    except Exception as e:
        raise HTTPException(400, str(e))
    # cascada: M1 rankea, M2 confirma por texto; basta uno en malicious para escalar.
    # tecnicas del tier decidido (oraculo M4), no del message_type.
    mal = label == "malicious" or (m2 is not None and m2["label"] == "malicious")
    tier = "malicious" if mal else label
    tech, tact = TIER_TECH.get(tier, ([], []))
    triage = "escalar" if (mal or (label == "suspicious" and log.action == "block")) else "monitorear"
    return LogOut(label=label, proba=proba, techniques=tech, tactics=tact,
                  techniques_source=TECH_SRC,
                  model=MODEL["name"], triage=triage, m2=m2)

@app.post("/score_batch")
def score_batch(logs: list[LogIn]):
    if len(logs) > 500:
        raise HTTPException(400, "máx 500 por lote")
    df = pd.concat([featurize(l) for l in logs], ignore_index=True)
    if MODEL["pipe"] is None:
        return [{"label": "benign", "model": MODEL["name"]} for _ in logs]
    preds = MODEL["pipe"].predict(df)
    probas = MODEL["pipe"].predict_proba(df)
    out = []
    for l, pr, pb in zip(logs, preds, probas):
        tech, tact = TIER_TECH.get(str(pr), ([], []))
        out.append({"label": str(pr),
                    "proba": {k: round(float(v), 4) for k, v in zip(MODEL["pipe"].classes_, pb)},
                    "techniques": tech, "tactics": tact, "techniques_source": TECH_SRC,
                    "model": MODEL["name"]})
    return out

# ponytail: en la imagen Docker el mismo :8000 sirve API + web (SPA).
# Rutas explicitas (el catch-all /{path:path} no matchea "/" en este Starlette).
DIST = ROOT / "soc-ui" / "dist"
if DIST.joinpath("index.html").exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    def _index():
        return FileResponse(DIST / "index.html")

    for _p in ("/", "/index.html", "/panorama", "/incidente", "/grafo",
               "/cobertura", "/lab", "/incidente/{inc_id}"):
        app.get(_p, include_in_schema=False)(lambda _p=_p: _index())
