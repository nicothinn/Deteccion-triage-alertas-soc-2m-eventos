# Punto 1 — Introducción y motivación (desarrollo completo)

> Sección 1 de la primera entrega (`contexto/course_project_guide.pdf`): *¿cuál es el problema que abordarás? ¿por qué es importante?* Texto listo para exponer (parte de los 15 min).

## Cuál es el problema

Los Centros de Operaciones de Seguridad (SOC) vigilan la infraestructura con decenas de productos: syslog, auditoría de Windows, flujos VPC, telemetría de endpoint. Una plataforma como WitFoo Precinct correlaciona todo eso con 261 reglas de detección y agrupa lo sospechoso en **incidentes** (señales disparadoras + subgrafo de proveniencia + reporte de caza).

El problema que abordamos es el **triage de alertas**: dado **un** evento de seguridad, predecir su tier — `benign` (ruido), `suspicious` (vigilar), `malicious` (ataque) — con probabilidades calibradas, pistas MITRE ATT&CK y una decisión operativa (`escalar` vs `monitorear`), en menos de 50 ms para rankear la cola y con un camino batch para reprocesar historia.

Formalmente: aprender `f: x ↦ (y, p)` donde `x` es un evento (campos tabulares + mensaje crudo + subgrafo vecindario de ±5 min), `y` el tier y `p` las probabilidades. La consola decide `escalar` si `y = malicious`, o si `y = suspicious` con acción de bloqueo.

## Por qué es importante

1. **Volumen imposible a mano.** Nuestra captura real tiene **2,011,674 eventos en 6 días** (4 organizaciones, 19 productos, 12 vendors). Ningún equipo humano lee eso; sin triage automático, los ataques se pierden en el ruido (ver `reports/figures/label_distribution.pdf`).
2. **Desbalance extremo.** Solo **7,728 leads maliciosos in-window (0.38%)**, IR benign:malicious ≈ **245:1**. El accuracy miente (94% diciendo siempre "benigno"); hay que optimizar F1-macro y PR-AUC por clase, y el costo de un falso negativo (brecha) es órdenes de magnitud mayor que el de un falso positivo.
3. **Cambio de contexto del analista.** Decidir exige el mensaje crudo, el mapeo MITRE y la cadena del ataque, no un score suelto. Por eso la salida incluye técnicas (`/score` → capa tier→técnicas) y la consola une cola + cadena + cobertura en una pantalla.
4. **Verdad imperfecta.** Las etiquetas son correlación automática de Precinct (`disposition = Unprocessed` en 2,005,877/2,011,674 señales), no veredicto de analista. El sistema debe funcionar con un oráculo fuerte pero ruidoso — igual que en producción.
5. **Deriva temporal.** Los leads maliciosos terminan el 07-30 pero el tráfico benigno sigue al 08-01 (ver `reports/figures/temporal_volume.pdf`): quien entrena con shuffle hace trampa; el split debe ser temporal.

## Evidencia (dónde está cada afirmación)

| Afirmación | Evidencia |
|---|---|
| 2M eventos, 0.38% malicious, IR 245:1 | `reports/figures/label_distribution.pdf`, `paper.tex` Tab. 1 |
| 4 orgs, 19 productos, 12 vendors, ventana 26 jul–01 ago | `reports/figures/temporal_volume.pdf`, `data/README_HF.md` |
| 261 reglas, 51,371 incidentes + reportes, 47k nodos / 1.7M aristas | `data/reference/lead_rules_catalog.json`, `paper.tex` Tab. 2 |
| Unprocessed 2,005,877/2,011,674 | `notebooks/eda_precinct6.ipynb` §9, `reports/eda/resumen_eda.md` |
| Definición formal `f: x ↦ (y, p)` + protocolo temporal | `docs/documentacion_end_to_end.md` §3 |
| Decisión escalar/monitorear servida | `app/main.py` (`/score`), consola `soc-ui/` |
