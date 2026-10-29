# Datasheet — witfoo/precinct6-cybersecurity v2.1.0 (subset 2M en este repo)

> Estructura Gebru et al. 2018. Versión de datos: v2.1.0 + subset determinista (seed 42).

## Motivación
SOC reales ahogados en alertas; faltaba dataset SOC multi-vendor con incidentes en contexto, grafos de proveniencia y reportes NL. Financia WitFoo + Univ. Canterbury (battle simulator CybORG, PIDS KnowHow/NodLink).

## Composición
2,011,674 live (benign 94.31% / suspicious 5.31% / malicious 0.38%, 1,584 incidentes in-window) + 238,511 `incident_signals` histórico + 47,585 nodos + 1,740,438 aristas + 51,371 reportes. Unidad: evento + incidente + nodo/arista. Ver `data/README_HF.md` y `reports/eda/resumen_eda.md`.

## Recolección
Producción SOC 4 orgs, 2024-07-26→08-01, 19 productos/12 vendors. Leads = triggers de incidentes Precinct; suspicious = match ≥1 regla sin ser lead. Subset: todos los leads + tráfico ±5min + fill uniforme p=0.00371 (`data/build/subset_stats.json`).

## Preproceso (WitFoo, no nosotros)
Sanitización 4 capas (estructurada+Aho-Corasick, parsers por formato, Presidio/spaCy+BERT NER, revisión LLM WitQ, 85,088 mapeos, tokens compartidos entre tablas). Timestamps reparados (861, `timestamp_source`). Nuestro prepro P1–P5 en `docs/documentacion_end_to_end.md` §4.

## Ground truth y límites
Labels = correlación automática Precinct, **sin verdad analista** (disposition automated `Unprocessed/Disrupted/Open/Cold Case` domina). `label_confidence` = corroboración, no probabilidad. ATT&CK = priors por roles/MO/producto. Sanitización reduce detalle libre. Tokens ≠ v1. IR 245:1, cobertura desigual por org/día → split temporal obligatorio.

## Licencia y acceso
Apache-2.0. HuggingFace `witfoo/precinct6-cybersecurity` (+ `...-100m` 114M). Parquets **no en git** (ver README §1). Regenerable con `witfoo/dataset-from-precinct6`.

## Usos recomendados / desaconsejados
Sí: triage 3-clases con split temporal, ATT&CK multi-label, link-prediction / cadenas, reportes NL, simulación CybORG. No: accuracy como métrica,/biometría/re-identificación, entrenar sin estratificar por tiempo, usar `incident_signals` mezclado con live.
