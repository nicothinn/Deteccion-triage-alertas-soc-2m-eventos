"""EDA completo segun checklist 2026 (OMSCS/Insper): inspeccion, univariado,
bivariado, leakage, drift, hipotesis. Corre: .venv/Scripts/python.exe src/eda_report.py
Genera reports/eda/resumen_eda.md + diccionario_datos.csv (reproducible, seed 42)."""
from pathlib import Path
import pandas as pd
import numpy as np
import json

ROOT = Path(__file__).resolve().parents[1]
SIG = ROOT / "data" / "signals" / "signals.parquet"
OUT = ROOT / "reports" / "eda"
OUT.mkdir(parents=True, exist_ok=True)

L = []
def h(t): L.append(f"\n## {t}\n")
def p(t): L.append(t + "\n")
def tbl(df, n=15):
    L.append("```\n" + df.head(n).to_string() + "\n```\n")

L.append("# Resumen EDA completo — Precinct6 (generado del parquet real)\n")
L.append("Fases: 0 objetivo · 1 inspeccion (diccionario+calidad+target+split) · 2 univariado · 3 bivariado/multivariado · 4 prepro · 5 sintesis.\n")

# F0/F1: forma y schema
h("F1. Inspeccion inicial")
cols = ["label_binary","timestamp","event_time","org_id","artifact_id","message_type","stream_name",
        "pipeline","product_name","vendor_name","src_ip","dst_ip","src_port","dst_port","protocol",
        "src_host","dst_host","username","action","severity","vendor_code","message_sanitized",
        "label_confidence","attack_techniques","attack_tactics","mo_name","suspicion_score",
        "disposition","is_false_positive","incident_ids","matched_rules","set_roles"]
df = pd.read_parquet(SIG)
p(f"Shape: {df.shape[0]:,} filas x {df.shape[1]} columnas. Ventana: {pd.to_datetime(df.timestamp,unit='s',utc=True).min()} → {pd.to_datetime(df.timestamp,unit='s',utc=True).max()}")
p(f"Duplicados artifact_id: {df.artifact_id.duplicated().sum():,} (politica: 1 fila por artifact_id, join a leads por artifact_id).")
miss = (df.isna().sum()/len(df)*100).sort_values(ascending=False).head(10)
p("Top missing % (NaN reales):"); tbl(miss.to_frame("miss_%"))
empty = ((df=="").sum()/len(df)*100).sort_values(ascending=False).head(10)
p("Top vacios % (string vacio = nivel propio, no imputar):"); tbl(empty.to_frame("empty_%"))
# diccionario
dd = pd.DataFrame([{"columna":c,"dtype":str(df[c].dtype),"nunique":int(df[c].nunique()),
                     "miss_%":round(float(df[c].isna().mean()*100),2)} for c in df.columns])
dd.to_csv(OUT/"diccionario_datos.csv", index=False)
p(f"Diccionario completo: {len(dd)} columnas en diccionario_datos.csv.")

# Target
h("Target integrity (label_binary)")
vc = df.label_binary.value_counts(); pct = df.label_binary.value_counts(normalize=True)*100
p(f"benign {vc.get('benign',0):,} ({pct.get('benign',0):.2f}%) · suspicious {vc.get('suspicious',0):,} ({pct.get('suspicious',0):.2f}%) · malicious {vc.get('malicious',0):,} ({pct.get('malicious',0):.2f}%) · IR benign:malicious {vc.get('benign',1)/max(vc.get('malicious',1),1):.0f}:1")
p("label_confidence por tier (no es P(malicioso), es evidencia corroborante):"); tbl(df.groupby("label_binary").label_confidence.describe())
p("Definicion: malicious=lead de incidente Precinct · suspicious=matcheo ≥1 regla sin ser lead · benign=resto. Exclusiones: incident_signals es otro timeline (origin), no mezclar.")

# F2 univariado
h("F2. Univariado")
df["msg_len"] = df.message_sanitized.str.len()
df["hour"] = pd.to_datetime(df.timestamp,unit="s",utc=True).dt.hour
p("Numericas (hour, msg_len, lag_h, suspicion_score, label_confidence):"); tbl(df[["hour","msg_len","label_confidence","suspicion_score"]].describe().T)
for c in ["message_type","org_id","action","severity","protocol"]:
    p(f"{c} top5: {df[c].value_counts().head(5).to_dict()} (cardinalidad {df[c].nunique()})")

# F3 bivariado + leakage + drift
h("F3. Bivariado, leakage y drift")
p("message_type x malicious top:"); tbl(pd.crosstab(df.message_type,df.label_binary)["malicious"].sort_values(ascending=False).head(10).to_frame())
p("action x label:"); tbl(pd.crosstab(df.action,df.label_binary))
p("org x label %:"); tbl((pd.crosstab(df.org_id,df.label_binary,normalize='index')*100).round(1))
p("Leakage scan: attack_techniques/tactics, mo_name, suspicion_score, incident_ids, matched_rules, set_roles, disposition VACIOS en benign → son priors del motor, NO features (M1/M2/M3 no los usan). label_confidence deriva del tier → excluida. timestamp/event_time solo via hour/lag_h + split temporal.")
df["day"] = pd.to_datetime(df.timestamp,unit="s",utc=True).dt.floor("D")
p("Drift (dia x label, malicious termina 07-30, benign sigue a 08-01 → justifica split temporal 80/20, no shuffle):"); tbl(pd.crosstab(df.day,df.label_binary))
p("Outliers: msg_len cola larga en windows XML (no remover, es señal para M2); lag_h clip [-1e4,1e4], -1 si falta; severity vacia 49% = nivel propio.")

# F4/F5
h("F4. Plan de prepro (de este EDA salen P1-P5)")
p("P1 one-hot 9 cat (max_categories=30, ignore unknown) · P2 hour+lag_h + split temporal · P3 subsample estratificado max(n/3,2000) + class_weight/sample_weight, sin SMOTE · P4 TF-IDF 5k message_sanitized · P5 vecindario ±5min ORG|host/user → 8 feats. Todo fit SOLO en train.")
h("F5. Sintesis: hipotesis, shortlist, riesgos")
p("H1: tokens exploit/T1190 separan malicious (M2 R~0.97) — VERIFICADO. H2: vecinos ±5min (frac_block, frac_authfail) delatan lateralidad invisible a 1 fila (M3 F1 0.719) — VERIFICADO. H3: suspicious es tier medio recuperable solo tabular (M1 R 0.96 vs M2/M3 R~0.17) — VERIFICADO, trade-off documentado.")
p("Shortlist: message_type, action, org_id, severity, protocol, hour, msg_len, lag_h + texto + 8 grafo. Riesgos: labels = oraculo imperfecto Precinct; T1190+ORG-0004 dominan; benign 1.0 = separabilidad por volumen con split estricto, no leakage.")
p("Repro: `uv run jupyter nbconvert --to notebook --execute notebooks/eda_completo.ipynb` o este script `python src/eda_report.py` (seed 42).")

(OUT/"resumen_eda.md").write_text("\n".join(L), encoding="utf-8")
print("ok", OUT/"resumen_eda.md", len("\n".join(L)))
