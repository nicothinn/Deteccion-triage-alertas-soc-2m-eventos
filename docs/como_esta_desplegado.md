# Cómo está desplegada la aplicación

Estado: **en producción y verificado**.
URL: https://soc-precinct6.onrender.com
Rama desplegada: `feature-nicolas/deploy-free-tier` · commit `31ed027`
Build medido: 2 m 49 s.

---

## 1. Resumen en una línea

Un **único contenedor Docker** en **Render (plan free)** sirve la API FastAPI **y** la web React
compilada en el mismo puerto. Los modelos viajan dentro de la imagen; el dataset completo **no**
se despliega, se reemplaza por muestras compactas generadas con un script.

```
GitHub (rama deploy)
        │  push
        ▼
Render Blueprint (render.yaml)
        │  docker build
        ▼
┌──────────────────────────────────────────────┐
│ Imagen: python:3.10-slim                     │
│  app/ + src/ + soc-ui/dist (build de Node)   │
│  models/m1.pkl m2.pkl m3.pkl  (8 MB)         │
│  data/signals/signals_sample.parquet (2.6 MB)│
│  data/graph/*.parquet (9.6 MB)               │
└──────────────────────────────────────────────┘
        │  uvicorn --host 0.0.0.0 --port $PORT
        ▼
https://soc-precinct6.onrender.com   (TLS incluido)
```

## 2. Servicios utilizados

| Servicio | Rol | Plan | Costo |
|---|---|---|---|
| **GitHub** | hospeda el repo y la rama de deploy | público | $0 |
| **Render** | cómputo: construye la imagen y corre el contenedor | Free (512 MB, 0.1 CPU) | $0 |
| **Docker Hub** | imágenes base `node:22-alpine` y `python:3.10-slim` | público | $0 |
| **ghcr.io/astral-sh/uv** | binario `uv` para instalar dependencias | público | $0 |
| **Hugging Face** | origen del dataset (solo para regenerar muestras, no en runtime) | público | $0 |

No hay base de datos, ni bucket, ni CDN, ni Vercel. Un solo servicio y una sola URL.

## 3. Cómo se hizo el despliegue (paso a paso)

1. **Se creó una rama aparte** (`feature-nicolas/deploy-free-tier`) para no tocar `main`. Esa rama
   contiene solo lo necesario para construir la imagen.
2. **Se añadió `render.yaml`** con el servicio, el plan free y las variables de entorno.
3. En Render: **New + → Blueprint → repo → rama `feature-nicolas/deploy-free-tier`**.
   Render leyó `render.yaml` y creó el servicio `soc-precinct6`.
4. **Build multi-stage** (definido en `Dockerfile`):

```dockerfile
# etapa 1: web
FROM node:22-alpine AS web
RUN npm ci --no-audit --no-fund
COPY soc-ui/ ./
RUN VITE_API_URL="" npm run build        # → /w/dist (1.7 MB)

# etapa 2: api
FROM python:3.10-slim
RUN apt-get install libgomp1             # OpenMP que exigen LightGBM/XGBoost
RUN uv sync --frozen --no-dev            # dependencias de uv.lock
COPY app/ src/ models/ data/             # código + pesos + muestras
COPY --from=web /w/dist ./soc-ui/dist    # el front compilado
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

5. Render inyecta `PORT`, arranca el contenedor y valida `GET /health`.
6. **Cada `git push` a esa rama redespliega automáticamente** (Blueprint sincronizado).

> `VITE_API_URL=""` en el build del front es deliberado: la web llama a la API en el **mismo
> origen**, así que no hay CORS ni dominio cruzado.

## 4. Cómo se despliegan los datos

El dataset completo **no se despliega**. Motivo medido:

| Qué | Tamaño | RAM al leerlo |
|---|---|---|
| `signals.parquet` completo (2,011,674 filas × 22 cols) | 117 MB | **4,866 MB por request** |
| `edges-00000.parquet` completo (1,740,438 aristas) | 34 MB | ~220 MB por request |

`/queue` y `/incident` leen el parquet **en cada petición**. Con 512 MB de RAM eso es imposible,
así que se generan muestras compactas y se versionan en la rama de deploy:

```bash
uv run python src/make_sample.py                 # 20,000 filas
uv run python src/make_sample.py --rows 12000    # si hiciera falta más margen
```

Archivos que sí viajan en la imagen:

| Archivo | Peso | Lo usa |
|---|---|---|
| `data/signals/signals_sample.parquet` | 2.6 MB | `/queue`, `/incident`, `/score_graph` |
| `data/graph/edges_sample.parquet` | 1.1 MB | `/graph/vecindario` |
| `data/graph/nodes.parquet` (completo) | 4.3 MB | atributos de nodos del grafo |
| `data/graph/attack_reports.parquet` (completo) | 4.2 MB | reporte de caza en `/incident` |
| `models/m1.pkl` `m2.pkl` `m3.pkl` | 8 MB | inferencia real |
| `models/*_metrics.json` | <1 MB | página Lab |

Las rutas se inyectan por variable de entorno (`render.yaml`):

```
SIGNALS_PATH=/app/data/signals/signals_sample.parquet
EDGES_PATH=/app/data/graph/edges_sample.parquet
```

Si no se definen, la app usa el dataset completo (modo local). `/health` reporta cuál está usando.

## 5. Qué se muestreó exactamente

**Señales — 20,000 filas** (`src/make_sample.py`):

| Clase | En el dataset | En la muestra | Cómo |
|---|---|---|---|
| malicious | 7,728 | **7,728 (todos)** | sin muestreo |
| suspicious | 106,793 | 6,136 | `sample(random_state=42)` |
| benign | 1,897,153 | 6,136 | `sample(random_state=42)` |

Se conservan **todos** los eventos maliciosos para que la cola sea útil en la demo. El resto es
aleatorio con semilla fija (reproducible).

**Grafo — 250,000 de 1,740,438 aristas**: se conservan los vecindarios **completos** de los 800
nodos más conectados (incluye los 5 nodos sugeridos por la UI) y se muestrea el resto.

**Nodos y reportes de incidente**: completos, no se muestrearon.

**Modelos**: los 3 `.pkl` reales, sin recortes.

### Precio de muestrear

| Efecto | Detalle |
|---|---|
| Cola | muestra **20,000** eventos, no 2,011,674 |
| M3 (`/score_graph`) | `n_vecinos` bajo: el muestreo uniforme rompe las ventanas densas de ±5 min |
| Grafo | un nodo fuera de los 800 más conectados devuelve vecindario vacío |
| Totales del Panorama | correctos: están fijos en el código, no salen del parquet |

Nada de esto afecta la inferencia: los modelos son los entrenados.

## 6. Cómo se interactúa con los modelos desde la UI

| Página | Endpoints | Qué hace |
|---|---|---|
| **Cola** | `/queue` `/score` `/explain` `/score_graph` `/feedback` | puntuar eventos y dar feedback |
| **Panorama** | `/stats` `/model/metrics` | retrato del dataset y tablero de modelos |
| **Incidente** | `/incident/{id}` | eventos correlacionados + reporte de caza |
| **Grafo** | `/graph/vecindario` | vecindario de proveniencia por nodo |
| **Cobertura** | `/stats` | cobertura ATT&CK de las etiquetas |
| **Lab** | `/model/metrics` | métricas de M1–M6 |

### Cola (`/`) — aquí se toca el modelo

1. **Filtros**: `Etiqueta`, `Organización`, `Tipo de evento`, `Severidad`, fechas y búsqueda por
   ID/IP/host/regla. La tabla se ordena por etiqueta (malicious → suspicious → benign) y fecha.
2. **Click en una fila** → panel derecho con los datos del evento y su etiqueta Precinct.
3. **Botón "Puntuar con M1"** → ejecuta a la vez:
   - `POST /score`: **M1 tabular + M2 texto** en cascada. Devuelve etiqueta, probabilidades,
     modelo y la regla de triage (`escalar` si malicious, o suspicious + `action=block`).
   - `POST /explain`: top features de LightGBM activas en ese evento.
4. **Botón "Consultar vecindario M3 (grafo)"** → `POST /score_graph` con el `artifact_id`.
   Reconstruye la ventana causal `[t-300s, t)` por org/host/credencial y devuelve predicción y
   número de vecinos.
5. **Feedback** (`escalar` / `monitorear` / `falso_positivo` + nota) → `POST /feedback`,
   escribe una fila en CSV. No reentrena: es un registro para revisión.

## 7. Guion de demo (7–8 min)

**Antes de empezar:** abre la página 2 minutos antes. El plan free duerme a los 15 min y el
primer request tarda ~50 s o más.

| # | Dónde | Qué hacer | Qué decir |
|---|---|---|---|
| 1 | **Panorama** | abrir la pestaña | 2,011,674 señales en 6 días, IR 245:1, solo 7,728 maliciosos. El problema es reducir volumen sin ocultar ataques. |
| 2 | **Cola** | filtro `maliciosas` | 7,728 eventos: la muestra conserva **todos** los maliciosos. |
| 3 | **Cola** | click en una fila, **"Puntuar con M1"** | Compara etiqueta Precinct vs predicción. ⚠️ M1 **casi nunca** predice malicious (recall 0.0107): si dice benign, **eso es el hallazgo del paper**, no un fallo de la demo. M1 ordena volumen y recupera suspicious. |
| 4 | **Cola** | leer el bloque M2 | M2 aporta el ranking por texto: recall@1 %FPR 0.4344. Segunda señal, no decisión automática. |
| 5 | **Cola** | **"Consultar vecindario M3 (grafo)"** | M3 usa contexto causal. En la demo el `n_vecinos` es bajo por el muestreo: dilo antes de que lo pregunten. |
| 6 | **Cola** | panel "Por qué dice X" | Importancia global LightGBM × valor activo del evento. |
| 7 | **Cola** | link del incidente (`Incidente: 7f63aba9`) | Salta a los eventos correlacionados. |
| 8 | **Incidente** | revisar la lista y el reporte | Proveniencia y reporte de caza de Precinct. Contexto, no prueba de causalidad. |
| 9 | **Grafo** | click en `USER-0719` o `100.64.39.157` | Vecindario de proveniencia: 99 hosts, posible movimiento lateral / C2. |
| 10 | **Cobertura** | abrir | Qué técnicas cubren las etiquetas del dataset. |
| 11 | **Lab** | abrir | Métricas M1–M6 con su lectura honesta: M3 0.7186 es cota no causal; M4 aprende mal la cola; M5 no detecta. |
| 12 | **Cola** | feedback `escalar` | Cierra el ciclo analista-en-el-loop. Se guarda en CSV. |

**Qué no afirmar:** que la app detecta campañas futuras, que atribuye ATT&CK por evento, o que
M3 tiene F1 0.7186 en producción. Las técnicas que muestra la cola son el mapeo tier→técnica
(oráculo), no una predicción multilabel aprendida.

## 8. Operación

| Tarea | Cómo |
|---|---|
| Redesplegar | `git push` a `feature-nicolas/deploy-free-tier` |
| Regenerar muestras | `uv run python src/make_sample.py` y push |
| Ajustar RAM del sample | `--rows 12000` |
| Ver estado | `GET /health` (modelos cargados + archivo de señales en uso) |
| Logs | Render → servicio → Logs |

```powershell
curl https://soc-precinct6.onrender.com/health
# {"ok":true,"signals":"signals_sample.parquet","edges":"edges_sample.parquet",
#  "model":"m1-tabar-v1","loaded":true,"m2_loaded":true,"m3_loaded":true}
```

**Límites del plan free:** 512 MB RAM · 0.1 CPU · duerme a los 15 min · 750 h/mes · sistema de
archivos efímero (el CSV de feedback se pierde al reiniciar) · Render puede reiniciar el servicio
en cualquier momento.

## 9. Descartado

- **Vercel**: el `Dockerfile` ya compila y sirve el front; un segundo deploy solo añadía CORS,
  manejo de ramas y un punto más de fallo.
- **Hugging Face Docker Spaces**: pasó a requerir plan PRO para compute.
- **Dataset completo en la nube**: 4.9 GB por request no cabe en ningún plan gratuito.
