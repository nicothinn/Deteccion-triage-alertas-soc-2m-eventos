# Resumen EDA completo — Precinct6 (generado del parquet real)

Fases: 0 objetivo · 1 inspeccion (diccionario+calidad+target+split) · 2 univariado · 3 bivariado/multivariado · 4 prepro · 5 sintesis.


## F1. Inspeccion inicial

Shape: 2,011,674 filas x 38 columnas. Ventana: 2024-07-26 11:10:23.729254961+00:00 → 2024-08-01 06:00:03.239708900+00:00

Duplicados artifact_id: 0 (politica: 1 fila por artifact_id, join a leads por artifact_id).

Top missing % (NaN reales):

```
                     miss_%
event_time        75.450794
timestamp          0.000000
timestamp_source   0.000000
origin             0.000000
org_id             0.000000
artifact_id        0.000000
message_type       0.000000
stream_name        0.000000
pipeline           0.000000
src_ip             0.000000
```

Top vacios % (string vacio = nivel propio, no imputar):

```
               empty_%
mo_name      99.615842
status_name  99.615842
protocol     94.275315
dst_port     93.626452
dst_ip       93.161019
src_port     89.680634
dst_host     82.539020
action       72.805981
username     64.126096
src_ip       60.315190
```

Diccionario completo: 38 columnas en diccionario_datos.csv.


## Target integrity (label_binary)

benign 1,897,153 (94.31%) · suspicious 106,793 (5.31%) · malicious 7,728 (0.38%) · IR benign:malicious 245:1

label_confidence por tier (no es P(malicioso), es evidencia corroborante):

```
                  count      mean       std  min  25%     50%       75%   max
label_binary                                                                 
benign        1897153.0  0.500000  0.000000  0.5  0.5  0.5000  0.500000  0.50
malicious        7728.0  0.787450  0.138010  0.6  0.6  0.8875  0.894531  0.95
suspicious     106793.0  0.600115  0.003392  0.6  0.6  0.6000  0.600000  0.70
```

Definicion: malicious=lead de incidente Precinct · suspicious=matcheo ≥1 regla sin ser lead · benign=resto. Exclusiones: incident_signals es otro timeline (origin), no mezclar.


## F2. Univariado

Numericas (hour, msg_len, lag_h, suspicion_score, label_confidence):

```
                      count        mean          std  min  25%    50%     75%          max
hour              2011674.0   11.419315     6.936570  0.0  4.0   12.0    18.0     23.00000
msg_len           2011674.0  963.840373  1385.262744  0.0  0.0  180.0  1739.0  65116.00000
label_confidence  2011674.0    0.506419     0.029700  0.5  0.5    0.5     0.5      0.95000
suspicion_score   2011674.0    0.002670     0.046331  0.0  0.0    0.0     0.0      0.96625
```

message_type top5: {'security_audit_event': 336425, 'management_message': 266320, 'java_error': 154491, '4662': 115553, '5156': 101277} (cardinalidad 595)

org_id top5: {'ORG-0004': 995985, 'ORG-0005': 576817, 'ORG-0003': 433904, 'ORG-0001': 4968} (cardinalidad 4)

action top5: {'': 1464619, 'File System': 117934, 'Directory Service Access': 115332, 'block': 114310, 'Filtering Platform Connection': 106589} (cardinalidad 44)

severity top5: {'': 991253, 'informational': 479472, 'Info': 427432, 'warning': 95150, 'notice': 17699} (cardinalidad 10)

protocol top5: {'': 1896512, '17': 88007, '6': 24491, '1': 2655, '88': 8} (cardinalidad 6)


## F3. Bivariado, leakage y drift

message_type x malicious top:

```
                           malicious
message_type                        
network_flow_data               4156
firewall_action                 3525
endpoint_protection_event         20
auth_failure                      16
GEO_IP_BLOCK                       4
GRIP_IP_BLACKLISTED                2
MALFORMED_VERSION                  2
SLASH_DOT_IN_URL                   2
UNKNOWN_CONTENT_TYPE               1
102                                0
```

action x label:

```
label_binary                    benign  malicious  suspicious
action                                                       
                               1464537         20          62
Audit Policy Change                 20          0           0
Authorization Policy Change        449          0           0
Backup                             137          0           0
Credential Validation             5445          0           0
Detailed File Share                 24          0           0
Directory Service Access        115332          0           0
Directory Service Changes           60          0           0
DnsRegistration                      2          0           0
File Share                        1221          0           0
File System                     117934          0           0
Filtering Platform Connection   106589          0           0
General                            131          0           0
Group Membership                   130          0           0
Guest Library API                    5          0           0
```

org x label %:

```
label_binary  benign  malicious  suspicious
org_id                                     
ORG-0001        99.8        0.0         0.2
ORG-0003       100.0        0.0         0.0
ORG-0004        98.1        0.4         1.5
ORG-0005        83.5        0.6        15.9
```

Leakage scan: attack_techniques/tactics, mo_name, suspicion_score, incident_ids, matched_rules, set_roles, disposition VACIOS en benign → son priors del motor, NO features (M1/M2/M3 no los usan). label_confidence deriva del tier → excluida. timestamp/event_time solo via hour/lag_h + split temporal.

Drift (dia x label, malicious termina 07-30, benign sigue a 08-01 → justifica split temporal 80/20, no shuffle):

```
label_binary               benign  malicious  suspicious
day                                                     
2024-07-26 00:00:00+00:00  560534       3260       50119
2024-07-27 00:00:00+00:00  655920        916       44912
2024-07-28 00:00:00+00:00   10822          0           0
2024-07-29 00:00:00+00:00  397315       3515       10734
2024-07-30 00:00:00+00:00  161715         37         816
2024-07-31 00:00:00+00:00   87364          0         188
2024-08-01 00:00:00+00:00   23483          0          24
```

Outliers: msg_len cola larga en windows XML (no remover, es señal para M2); lag_h clip [-1e4,1e4], -1 si falta; severity vacia 49% = nivel propio.


## F4. Plan de prepro (de este EDA salen P1-P5)

P1 one-hot 9 cat (max_categories=30, ignore unknown) · P2 hour+lag_h + split temporal · P3 subsample estratificado max(n/3,2000) + class_weight/sample_weight, sin SMOTE · P4 TF-IDF 5k message_sanitized · P5 vecindario ±5min ORG|host/user → 8 feats. Todo fit SOLO en train.


## F5. Sintesis: hipotesis, shortlist, riesgos

H1: tokens exploit/T1190 separan malicious (M2 R~0.97) — VERIFICADO. H2: vecinos ±5min (frac_block, frac_authfail) delatan lateralidad invisible a 1 fila (M3 F1 0.719) — VERIFICADO. H3: suspicious es tier medio recuperable solo tabular (M1 R 0.96 vs M2/M3 R~0.17) — VERIFICADO, trade-off documentado.

Shortlist: message_type, action, org_id, severity, protocol, hour, msg_len, lag_h + texto + 8 grafo. Riesgos: labels = oraculo imperfecto Precinct; T1190+ORG-0004 dominan; benign 1.0 = separabilidad por volumen con split estricto, no leakage.

Repro: `uv run jupyter nbconvert --to notebook --execute notebooks/eda_completo.ipynb` o este script `python src/eda_report.py` (seed 42).
