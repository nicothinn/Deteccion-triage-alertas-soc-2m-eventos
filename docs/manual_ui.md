# Manual de la consola SOC — página por página

Qué hay en cada pantalla, qué hace cada botón, cada selector y cada tabla.
Consola: https://soc-precinct6.onrender.com

> Recordatorio de datos: la cola muestra **20,000 eventos** (muestra), no 2,011,674.
> Los totales del Panorama y Cobertura sí son los reales: están fijos en el código.

---

## 0. Estructura común

### Barra superior (siempre visible)

| Elemento | Qué es |
|---|---|
| `PRECINCT/6 triage` | logo, a la izquierda |
| `26 jul – 01 ago 2024 · 19 productos · 4 orgs` | ventana y alcance de la captura |
| Punto de color + texto | **verde** = `m1-tabar-v1 · listo` (pkl cargados); **naranja** = `stub sin pkl`; gris = `conectando a :8000…`. Se refresca cada **15 s** contra `GET /health` |

### Navegación (6 pestañas)

`Cola` · `Panorama` · `Incidente` · `Grafo` · `Cobertura` · `Lab`

La activa se subraya en verde ácido. El contenido vive en un contenedor de máx. 1480 px.

### Rutas

| Pestaña | URL |
|---|---|
| Cola | `/` |
| Panorama | `/panorama` |
| Incidente | `/incidente` o `/incidente/<id>` |
| Grafo | `/grafo` |
| Cobertura | `/cobertura` |
| Lab | `/lab` |

---

## 1. Cola (`/`) — la única página que ejecuta modelos

Dos columnas: tabla (izquierda) y **Detalle y puntuación** (derecha).

### 1.1 Panel "Qué estás viendo"

Texto fijo + dos desplegables (`<details>`):

| Desplegable | Contenido |
|---|---|
| **Cómo se puntúa (M1 + M2; M3 manual)** | Qué hace cada modelo, que las etiquetas de la cola son de Precinct y no del modelo, y que el feedback no reentrena |
| **Qué técnicas y tácticas verás (ATT&CK)** | T1190, T1041, T1567, T1204 y las tácticas TA0001/TA0002/TA0009/TA0010 |

### 1.2 Filtros

Se aplican **solo al pulsar `Aplicar`** (no son reactivos).

| Control | Tipo | Opciones | Defecto |
|---|---|---|---|
| **Etiqueta** | select | `todas` · `maliciosas` · `sospechosas` · `benignas` | todas |
| **Organización** | select | `todas` · `ORG-0001` · `ORG-0003` · `ORG-0004` · `ORG-0005` | todas |
| **Tipo de evento** | select | `todos (top 30)` + 30 tipos (security_audit_event, management_message, java_error, 4662, 5156, firewall_action, network_flow_data, dns_event, pam_event…) | todos |
| **Severidad** | select | `todas` · `(vacía — 49%)` · `Info` · `Start` · `alert` · `critical` · `debug` · `error` · `informational` · `notice` · `warning` | todas |
| **Desde (UTC)** | input date | — | vacío |
| **Hasta (UTC)** | input date | — | vacío (incluye el día completo) |
| **Buscar ID, IP, host o regla** | texto | substring, sin distinguir mayúsculas, sobre `artifact_id`, `src_ip`, `dst_ip`, `src_host`, `dst_host`, `username`, `message_type`, `product_name`, `vendor_name`, `matched_rules` | vacío |

| Botón | Acción |
|---|---|
| **Aplicar** | envía los filtros y vuelve a la página 1 |
| **Limpiar** | restaura todos los filtros y la página 1 |

Validación: si `Desde` > `Hasta` aparece **"La fecha Desde debe ser igual o anterior a Hasta."** y no se aplica.

### 1.3 Tabla "Cola de eventos"

| Columna | Contenido | ¿Ordenable? |
|---|---|---|
| (sin título) | icono de forma según etiqueta: **rombo** = malicious, **cuadro** = suspicious, **punto** = benign | no |
| **Hora UTC** | `MM-DD HH:MM:SS` | sí |
| **Tipo** | `message_type` | sí |
| **Origen** | `src_ip` (o `—`) | sí |
| **Acción** | `action` (o `—`) | **no** |
| **Etiqueta** | `benign` / `suspicious` / `malicious` | sí |

- Orden por defecto: etiqueta (malicious → suspicious → benign) y fecha descendente. Viene del backend.
- Click en una fila = seleccionarla (fondo verde + barra ácida a la izquierda).
- Al cambiar de página se limpia la selección y todos los resultados de puntuación.
- Contador superior derecho: `20.000 resultados`.
- Paginación: **60 por página**, botones `Anterior` / `Siguiente`, texto `1–60 de 20.000`.
- Vacío: `No hay eventos con estos filtros.`
- La primera fila se selecciona sola al cargar (el panel derecho nunca aparece vacío si hay datos).

### 1.4 Panel "Detalle y puntuación"

Leyenda: *"Rombo = actúa · cuadro = mira · punto = ruido. El color repite la etiqueta Precinct."*

**a) Cinta de tier** — 3 casillas `benign` / `suspicious` / `malicious`; la que coincide con la etiqueta Precinct del evento se marca con borde ácido.

**b) Cabecera y campos**

| Campo | Fuente |
|---|---|
| `artifact_id` | mono, completo |
| Tipo | `message_type` |
| Acción | `action` o `—` |
| Severidad | `severity` o `vacía` |
| Org | `org_id` |
| Técnicas | `attack_techniques` (etiqueta del dataset) o `—` |
| Tácticas | `attack_tactics` o `—` |
| Mensaje | `message_sanitized`, caja con scroll |

**c) Incidente** — si el evento tiene `incident_ids`, aparece `Incidente: 7f63aba9` (8 caracteres) y enlaza a `/incidente/<id completo>`.

**d) Regla de triage** — texto fijo: *"Escala si sale malicious, o suspicious con action block. Lo demás se monitorea."*

**e) Botón `Puntuar con M1`**

| Aspecto | Detalle |
|---|---|
| Llamadas | `POST /score` (M1 + M2 en cascada) y luego `POST /explain` |
| Mientras corre | el botón pasa a `Puntuando…` y se deshabilita |
| Resultado | `malicious → escalar` + `{benign, suspicious, malicious}` + `m1-tabar-v1 · ATT&CK [...]` + fuente de técnicas + línea **`M2 texto: <label> {…}`** |

**f) Botón `Consultar vecindario M3 (grafo)`**

| Aspecto | Detalle |
|---|---|
| Cuándo aparece | **solo después** de puntuar |
| Llamada | `POST /score_graph` con el `artifact_id` |
| Mientras corre | `Leyendo vecindario ±5min…` |
| Resultado | `M3 grafo: <label> {…} · N vecinos · m3-grafo-v1` |

**g) Bloque "Por qué dice {label}"** — top 8 features de LightGBM con `■` (activa en el evento) / `□` (inactiva) e importancia global entre paréntesis. Es `POST /explain`.

**h) Feedback — "Tu turno: ¿está bien puntuado?"**

| Control | Detalle |
|---|---|
| `escalar` / `monitorear` / `falso_positivo` | `POST /feedback`, guarda una fila CSV |
| Nota | texto libre, máx. 500 caracteres |
| Confirmación | `Guardado (N correcciones) para revisión y entrenamiento posterior.` |

---

## 2. Panorama (`/panorama`)

### 2.1 Cabecera

| Elemento | Contenido |
|---|---|
| Texto | "Seis días de telemetría Precinct · 4 organizaciones · 19 productos…" |
| Cifra grande | **`245:1`** benignas por cada maliciosa |
| Línea mono | 2,011,674 eventos · 7,728 leads maliciosos (0.38%) · 47,585 nodos / 1.7M aristas · 51,371 incidentes |

### 2.2 Sección "Modelos (test temporal 80/20, sin shuffle)" — 6 gráficos

| Gráfico | Qué muestra |
|---|---|
| **F1-macro (M3 histórico, no comparable)** | barras M3 / M2 / M1 |
| **Recall malicious frente a etiquetas Precinct** | 0.962 (M3 ±5min) · 0.002 (M2) · 0.0107 (M1) |
| **F1 por clase** | barras agrupadas benign / suspicious / malicious para M1, M2 y M3 |
| **PR-AUC malicious (ranking bajo IR 245:1)** | 0.815 / 0.218 / 0.233 |
| **M1: matriz de confusión histórica (EDA, n=28,212)** | heatmap 3×3 rojo; cálculo antiguo del EDA |
| **M4b ATT&CK por técnica — no desplegado** | micro/macro-F1, hamming, subset-acc, train/test y las 6 etiquetas |

Cada gráfico trae una nota al pie aclarando que M3 es histórico y no causal.

### 2.3 Sección "Datos (de dónde viene el volumen)" — 6 barras horizontales

Cada una muestra el **top 10** ordenado de mayor a menor.

| Título | Datos |
|---|---|
| ¿De dónde viene el ruido? | `top_products` |
| ¿Quién genera el volumen? | `top_vendors` |
| ¿Qué severidad trae cada evento? | `severity` |
| ¿Qué hizo Precinct con cada alerta? | `disposition` |
| ¿De dónde viene el ruido por tipo? | `top_types` |
| ¿Por dónde se movería M3? | `graph.edge_types` |

Estados: `Leyendo /stats (conteos fijos del EDA)…` y error con instrucción de levantar uvicorn.

---

## 3. Incidente (`/incidente/:id?`)

### 3.1 Panel "Qué estás viendo"

Explica que cada incidente = señales encadenadas + reporte. Desplegable **"Cómo leer la cadena"** (3 reglas: orden temporal, color = etiqueta automática, comparar tamaños).

### 3.2 Selector y entrada manual

| Control | Detalle |
|---|---|
| **Select "Elige un incidente del dataset…"** | 6 ejemplos precargados, todos `Precinct: Data Theft` con 501 / 445 / 120 / 20 / 10 / 7 señales |
| **Input "…o pega un incident_id manual"** | acepta cualquier UUID de incidente |
| Botón **Abrir** | navega a `/incidente/<id>` |

Si eliges uno de los 6 ejemplos aparece un recuadro verde **"Qué mirar aquí"** con la lectura de ese incidente.

Sin incidente: `Sin incidente: ve a Cola y pulsa el hash de incidente de un evento malicioso.`

### 3.3 Resultado

| Bloque | Detalle |
|---|---|
| Cabecera | `<incident_id> · N eventos totales` |
| **Cadena (ReactFlow, 300 px)** | hasta 10 eventos en orden temporal, izquierda→derecha; borde rojo/ámbar/verde según etiqueta |
| Paginación | `1–30 de N eventos` + `Anterior` / `Siguiente` (**30 por página**) |
| **Tabla** | columnas **Hora** · **Tipo** · **Src** · **Etiqueta** |
| **Reporte de Precinct** | `mo_name · suspicion <score> · <report_source>` y el texto del reporte con scroll |

Si no hay reporte: `Sin reporte asociado.`

---

## 4. Grafo (`/grafo`)

### 4.1 Panel "Qué estás viendo"

Nodo ★ = punto de partida; verde = máquina/credencial sin sospecha; **rojo = `suspicion_score > 0`**; anillo 1 = vecinos directos, anillo 2 = vecinos de vecinos.
Desplegable **"Cómo leerlo (3 reglas)"**: concentración, color de arista y sospecha heredada de Precinct.

### 4.2 Buscador

| Control | Detalle |
|---|---|
| Input | placeholder `ORG-0004/user:USER-0719 o ORG-0004/HOST-0032` |
| Botón **Explorar** | consulta `GET /graph/vecindario` |

### 4.3 Botones de ejemplo (5)

| Botón | Nodo | Lectura sugerida |
|---|---|---|
| **C2 · 100.64.39.157** | `100.64.39.157` | 41 vecinos internos, 65 incidentes: patrón C2 |
| **Lateral · USER-0719** | `ORG-0004/user:USER-0719` | una credencial en 99 hosts |
| **Lateral · USER-0728** | `ORG-0004/user:USER-0728` | segunda credencial, 60 hosts |
| **Víctima · 10.187.253.125** | `ORG-0005/10.187.253.125` | 12k incident-links entrando |
| **DNS · vcenter** | `ORG-0005/vcenter` | 7.5k resolves: caza de DNS tunneling |

Al seleccionar uno aparece su descripción y el recuadro verde **"Qué mirar aquí"**.

### 4.4 Controles de consulta

| Control | Opciones | Defecto |
|---|---|---|
| **Profundidad** | `1 salto` · `2 saltos` | 1 salto |
| **Máx. vecinos por nivel** | `25` · `60` · `120` | 60 |
| **Tipos de arista** (checkboxes) | `USER_ACTION` ✓ · `NETWORK_FLOW` ✓ · `AUDIT_EVENT` · `EVENT` · `DNS_RESOLVE` · `INCIDENT_LINK` | solo los dos primeros activos |

Cada tipo tiene su color: USER_ACTION verde ácido, NETWORK_FLOW verde, AUDIT_EVENT verde claro, EVENT verde oscuro, DNS_RESOLVE turquesa, INCIDENT_LINK rojo.

### 4.5 Lienzo

- ReactFlow de **520 px** con fondo de puntos.
- Nodo central `★`, vecinos en anillos de 18, con etiqueta `id · tipo · signal_count`.
- Borde rojo si `suspicion > 0`; verde si no.
- Aristas etiquetadas con el tipo, máximo **300** dibujadas.
- Contador: `<nodo> · N aristas · mostrando M vecinos en D nivel(es)`.
- Pie: *"Rojo = suspicion_score > 0 · anillo 1 = relación directa · anillo 2 = segundo salto. Máximo 120 vecinos por nivel. M3 resume este vecindario en 8 números; su F1 0.719 es cota no causal."*

---

## 5. Cobertura (`/cobertura`)

### 5.1 Cuatro tarjetas KPI

| Tarjeta | Valor |
|---|---|
| Total eventos | 2,011,674 |
| Maliciosos | 7,728 (0.38%) |
| Sospechosos | 106,793 |
| Desbalance IR | 245:1 |

### 5.2 Contenido

| Bloque | Qué muestra |
|---|---|
| **¿Cómo atacan? Técnicas en los 7,728 maliciosos** | `top_tech` (T1190, T1041, T1567, T1204) |
| **¿De dónde viene el volumen?** | `top_types` |
| **¿Dónde están los puntos ciegos?** | `top_orgs` (ORG-0004 concentra ~49.5%) |
| **"Cómo leer esta página en el paper"** | 5 viñetas: ventana y split, métrica F1-macro + PR-AUC, fallo de M1 en malicious, severidad 49% vacía, enlace al glosario |

---

## 6. Lab (`/lab`) — solo métricas, sin inferencia

Intro: *"Mira M1 primero; M2 y M3 responden por qué falla. M4–M6 es el archivo de lo que no funcionó."*

### 6.1 Cuatro tarjetas KPI

`Modelo` · `F1-macro (temporal 80/20)` · `Train / test` · `Recall malicious` (en rojo)

### 6.2 Tabla principal

| Tier | Precision | Recall | F1 | PR-AUC | Support |
|---|---|---|---|---|---|
| benign | 1.00 | 1.00 | 1.00 | 1.00 | 559,030 |
| suspicious | 0.76 | 0.99 | 0.86 | 0.76 | 11,550 |
| malicious | 0.23 | **0.0107** | 0.02 | 0.23 | 3,552 |

### 6.3 Tarjetas de los demás modelos

| Tarjeta | Contenido |
|---|---|
| **M2 texto** | F1-macro 0.6232 · malicious P/R/F1/PR-AUC · `recall@1%FPR` 0.4344 · train/test |
| **M4b ATT&CK por técnica (XGBoost ×6)** | micro 0.7926 / macro 0.2557 · hamming · subset-acc · etiquetas |
| **M4c ATT&CK + grafo (4 experimentos)** | E0 tabular · E1 txt+tab · E2 tab+grafo · E3 full, micro y macro |
| **M4t umbrales por técnica** | tuned vs fijo 0.5 + tabla **Técnica · Umbral · F2 val · Pos train/val** |
| **M5 anomalía IF (solo-benigno)** | recall malicious 0 · PR-AUC · ROC-AUC invertido · FPR benigno |
| **M3 grafo** | F1-macro 0.7186 con la advertencia de que usó vecinos ±5 min (futuro) |

### 6.4 Dos paneles finales

| Panel | Contenido |
|---|---|
| **Configuración M1** | `n_estimators`, `learning_rate`, `num_leaves`, `class_weight`, split, sample_n + nota de complejidad |
| **Lectura para el paper** | 4 viñetas: por qué falla malicious, por qué suspicious sí, qué atacan M2 y M3, y por qué no usar accuracy |

---

## 7. Glosario visual

### Paleta

| Color | Hex | Significado |
|---|---|---|
| Ácido | `#d7ff3e` | acento, foco, selección, "listo" |
| Rojo | `#ff4d4d` | malicious |
| Ámbar | `#e9a13b` | suspicious |
| Verde | `#2fbf8f` | benign |
| Azul info | `#6aa8ff` | series M2 en gráficos |
| Gris mut | `#6e7f7a` | texto secundario |

### Iconos de etiqueta (Cola)

| Forma | Etiqueta | Lectura |
|---|---|---|
| **Rombo** rojo | malicious | hay que actuar |
| **Cuadro** ámbar | suspicious | mirar |
| **Punto** verde | benign | ruido |

Nunca se usa solo el color: forma + color + texto.

---

## 8. Mapa de endpoints por página

| Página | Endpoints que consume |
|---|---|
| Barra superior | `GET /health` (cada 15 s) |
| Cola — tabla | `GET /queue` |
| Cola — puntuar | `POST /score`, `POST /explain` |
| Cola — M3 | `POST /score_graph` |
| Cola — feedback | `POST /feedback` |
| Panorama | `GET /stats`, `GET /model/metrics` |
| Incidente | `GET /incident/{id}` |
| Grafo | `GET /graph/vecindario` |
| Cobertura | `GET /stats` |
| Lab | `GET /model/metrics` |

`/score_batch` y `/info` existen en la API pero **ninguna página los usa** (solo Swagger: `/docs`).

---

## 9. Ruta corta para una demo de 3 minutos

1. **Cola** → filtro `maliciosas` → 7,728 resultados.
2. Click en la primera fila → panel derecho con la etiqueta Precinct.
3. **`Puntuar con M1`** → compara Precinct vs modelo. Si sale `benign`, es el hallazgo del paper (recall 0.0107).
4. Leer la línea **M2** → segunda señal, ranking.
5. **`Consultar vecindario M3`** → contexto; `n_vecinos` bajo por el muestreo.
6. Link **Incidente** → cadena + reporte.
7. **Grafo** → botón `Lateral · USER-0719` → 99 hosts.
8. **Lab** → tabla con el recall y la explicación honesta.
