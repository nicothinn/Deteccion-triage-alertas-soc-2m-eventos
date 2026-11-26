# Plan de despliegue gratuito

Rama: `feature-nicolas/deploy-free-tier` (no toca `main`).
Esta rama contiene solo lo necesario para construir la imagen; el proyecto completo vive en `main`.
Objetivo: URL pública estable a **$0**, con la consola SOC funcionando.

---

## 1. La restricción que manda: memoria

Medido sobre la app real (RSS), no estimado:

| Escenario | RAM |
|---|---|
| Python + pandas/sklearn/lgbm/xgb + 3 modelos `.pkl` | 177 MB |
| `/queue` + `/incident` + `/score` + grafo con sample de 20k filas | **406 MB pico** |
| `/queue` con `signals.parquet` completo (2M filas × 22 cols) | **4,866 MB por request** |

El endpoint `/queue` re-lee el parquet en cada petición. Con el dataset completo ningún plan
gratuito sirve; con un sample compacto entra en 512 MB.

## 2. Arquitectura elegida

```
Navegador
   │
   ├─► Vercel (Hobby, $0)          ── soc-ui/dist, estático, nunca duerme
   │
   └─► Render (free, $0)           ── FastAPI + m1/m2/m3 + samples
        512 MB · 0.1 CPU · duerme a los 15 min · despierta en ~1 min
        https://<servicio>.onrender.com
```

Ventajas: sin tarjeta de crédito, URL permanente, TLS incluido.
Costo real: $0. Cuota Render: 750 instance-hours/mes (un servicio encendido todo el mes son 744).

## 3. Qué se despliega

| Artefacto | Peso | Para qué |
|---|---|---|
| `app/`, `src/` | <1 MB | API FastAPI |
| `models/m1.pkl` `m2.pkl` `m3.pkl` | 8 MB | `/score`, `/explain`, `/score_graph` |
| `models/*_metrics.json` | <1 MB | página Lab (`/model/metrics`) |
| `data/signals/signals_sample.parquet` | 2.6 MB | `/queue`, `/incident`, `/score_graph` |
| `data/graph/edges_sample.parquet` | 1.1 MB | `/graph/vecindario` |
| `data/graph/nodes.parquet` | 4.3 MB | atributos de nodos del grafo |
| `data/graph/attack_reports.parquet` | 4.2 MB | reporte de caza en `/incident` |
| `soc-ui/dist` | 1.7 MB | compilado dentro de la imagen Docker |

Total en git: ~27 MB. Imagen Docker final: ~1.5–2 GB (el dataset completo queda fuera).

## 4. Preparación (ya hecha en esta rama)

- `src/make_sample.py` — genera los samples; conserva **los 7,728 eventos malicious**.
- `app/main.py` — `SIGNALS_PATH` / `EDGES_PATH` por variable de entorno; `/health` reporta qué
  archivo está usando; 503 con mensaje claro si falta.
- `Dockerfile` — `COPY data/**/*.parquet` con wildcard (no rompe builds sin dataset completo).
- `render.yaml` — blueprint del servicio free apuntando a los samples.
- `soc-ui/vercel.json` — rewrite SPA (sin esto `/panorama` da 404 al refrescar con `BrowserRouter`).
- `.gitignore` — 7 excepciones para los artefactos de deploy.

Si necesitas regenerar los samples (requiere el parquet completo, que no está en git):

```bash
uv run python src/make_sample.py                 # 20k filas
uv run python src/make_sample.py --rows 12000    # si Render se queda corto de RAM
```

## 5. Paso a paso

### 5.1 Subir la rama

```powershell
git switch feature-nicolas/deploy-free-tier
git push -u origin feature-nicolas/deploy-free-tier
```

### 5.2 Render (API) — sin tarjeta

1. render.com → **New +** → **Blueprint**.
2. Elegir el repo y la rama `feature-nicolas/deploy-free-tier`.
3. Render detecta `render.yaml` y crea el servicio `soc-precinct6` (plan `free`).
4. Primer build: ~10–15 min (`npm ci` + `uv sync`, descarga `nvidia-nccl-cu12` ~335 MB).
5. Copiar la URL: `https://soc-precinct6.onrender.com`.

Si prefieres configurarlo a mano (New + → Web Service → Docker):

```
Plan: Free · Dockerfile: ./Dockerfile · Health check: /health
SIGNALS_PATH=/app/data/signals/signals_sample.parquet
EDGES_PATH=/app/data/graph/edges_sample.parquet
```

### 5.3 Vercel (front) — sin tarjeta

1. vercel.com → **Add New** → **Project** → importar el repo.
2. **Root Directory:** `soc-ui` · Framework: Vite · Build: `npm run build` · Output: `dist`.
3. Environment Variable: `VITE_API_URL = https://soc-precinct6.onrender.com`.
4. Deploy. Anotar el dominio: `https://<proyecto>.vercel.app`.

> Vercel Hobby es solo para uso personal/no comercial. Un proyecto de curso cumple.

### 5.4 CORS (obligatorio, si no el front no lee la API)

En Render → Environment → editar:

```
CORS_ORIGINS=https://<proyecto>.vercel.app
```

Guardar: Render redepliega solo.

### 5.5 Verificación

```powershell
curl https://soc-precinct6.onrender.com/health
# {"ok":true,"signals":"signals_sample.parquet","edges":"edges_sample.parquet",
#  "model":"m1-tabar-v1","loaded":true,"m2_loaded":true,"m3_loaded":true}
```

- Abrir la URL de Vercel → debe cargar la cola (primera vez tarda ~1 min: Render despertando).
- `/queue` debe mostrar **7,728 malicious** en el filtro.
- POST `/score` con `{"action":"block","message":"exploit T1190"}` → `"label":"malicious"`.

## 6. Plan B para la defensa (recomendado tenerlo listo)

Todo completo, sin límites de RAM, desde tu PC:

```powershell
docker compose up --build
cloudflared tunnel --url http://localhost:8000
# imprime una URL https://xxx.trycloudflare.com
```

Sin cuenta ni tarjeta. La URL muere al apagar el PC. Úsala el día de la presentación para no
depender del cold start de Render.

## 7. Alternativas evaluadas (nov 2026)

| Opción | RAM | Modo completo | Tarjeta | Nota |
|---|---|---|---|---|
| **Render free + Vercel** | 512 MB | con sample | No | **elegida** |
| Oracle Always Free (A1) | 12 GB (2 OCPU) | sí | Sí | única $0 permanente con RAM real; sufre "out of host capacity" |
| Google Cloud Run free | hasta 32 GB | sí | Sí | 360k GiB-s/mes ≈ 12 h con 8 GB |
| Azure Container Apps | hasta 8 GB | sí | Sí | grant similar a Cloud Run |
| Fly.io Free | ~256 MB | no | Sí ($5/mes) | $1 de crédito 7 días sin tarjeta |
| Koyeb free | 512 MB / **0.1 vCPU** | no | Sí | peor CPU que Render |
| Railway free | ~100 MB reales | no | No | $1/mes de crédito |
| HF Docker Spaces | 16 GB | sí | **PRO** | ya no hay compute gratis |
| Cloudflare Tunnel | tu PC | sí | No | plan B de la demo |

## 8. Limitaciones conocidas del modo free

- El contador de la cola dice **20,000** eventos (el sample), no 2,011,674. El Panorama sí muestra
  los totales reales porque están hardcodeados en el código.
- `/score_graph` devuelve `n_vecinos` bajo: el sample uniforme rompe las ventanas densas de ±5 min.
- El grafo solo tiene vecindarios completos de los **800 nodos más conectados** (incluye los 5
  nodos sugeridos por la UI). Un nodo fuera de ese conjunto devuelve vacío.
- Render duerme a los 15 min sin tráfico; el primer request tarda ~1 min.
- Sistema de archivos efímero: `/feedback` se pierde en cada reinicio.
- Render puede reiniciar el servicio en cualquier momento (política del plan free).

## 9. Costos

| Servicio | Plan | Costo |
|---|---|---|
| Render | Free (512 MB, 750 h/mes) | $0 |
| Vercel | Hobby | $0 |
| GitHub | repo público | $0 |
| **Total** | | **$0** |

## 10. Rollback

El deploy no modifica `main`. Para descartar todo:

```powershell
git switch main                       # o tu rama de trabajo
git branch -D feature-nicolas/deploy-free-tier
git push origin --delete feature-nicolas/deploy-free-tier
```

En Render/Vercel: borrar el servicio desde su dashboard.
