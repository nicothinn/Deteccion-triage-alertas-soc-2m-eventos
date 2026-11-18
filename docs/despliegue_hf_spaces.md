# Despliegue gratis en Hugging Face Spaces (Docker)

> Publica la consola SOC (API + web) en `https://TU_USUARIO-TU_SPACE.hf.space` sin pagar.
> Tiempo estimado: 30–45 min la primera vez. El dataset ya vive en HF; solo tus 3 `.pkl`
> necesitan un hogar nuevo porque no están en git.

## 0. Requisitos

- Cuenta en [huggingface.co](https://huggingface.co) (gratis).
- Este repo funcionando en local (`docker compose up --build` verificado).
- Tu usuario de HF a mano: aparece arriba a la derecha en huggingface.co. En esta guía es `TU_USUARIO`.

## 1. Subir los modelos a Hugging Face (5 min, por web)

Los `.pkl` no están en git, así que el build en la nube no los ve. Súbelos a un repo de modelos:

1. Abre [huggingface.co/new-model](https://huggingface.co/new-model).
2. Owner: tú. Name: `precinct6-soc-models`. Visibility: **Private** (recomendado) o Public.
3. Create → pestaña **Files → Add file → Upload files**.
4. Arrastra `models/m1.pkl`, `models/m2.pkl`, `models/m3.pkl` → **Commit**.
5. Verifica que existen en: `huggingface.co/TU_USUARIO/precinct6-soc-models/tree/main`.

Alternativa por terminal (si prefieres comandos):

```powershell
uv run --with huggingface_hub hf upload TU_USUARIO/precinct6-soc-models models/m1.pkl m1.pkl --repo-type model
uv run --with huggingface_hub hf upload TU_USUARIO/precinct6-soc-models models/m2.pkl m2.pkl --repo-type model
uv run --with huggingface_hub hf upload TU_USUARIO/precinct6-soc-models models/m3.pkl m3.pkl --repo-type model
```

## 2. Ajustar el `Dockerfile` (2 min)

El `Dockerfile` actual hace `COPY data/... models/*.pkl` desde tu disco. En la nube
esos archivos no existen: hay que **descargarlos de HF durante el build**.
`huggingface-hub` ya es dependencia del proyecto, no se añade nada.

Reemplaza estas líneas:

```dockerfile
COPY data/signals/signals.parquet ./data/signals/signals.parquet
COPY data/graph/nodes.parquet data/graph/edges-00000.parquet data/graph/attack_reports.parquet ./data/graph/
COPY models/m1.pkl models/m2.pkl models/m3.pkl ./models/
COPY models/*.json ./models/
```

por estas:

```dockerfile
ENV PORT=7860
RUN .venv/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download('witfoo/precinct6-cybersecurity', allow_patterns=['signals/signals.parquet','graph/nodes.parquet','graph/edges-*.parquet','graph/attack_reports.parquet'], local_dir='data')" \
 && .venv/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download('TU_USUARIO/precinct6-soc-models', allow_patterns=['*.pkl'], local_dir='models')"
COPY models/*.json ./models/
```

Notas:

- Cambia `TU_USUARIO` por tu usuario real en la segunda línea.
- `ENV PORT=7860`: Spaces exige el puerto **7860**. En local no se rompe nada porque
  `compose.yml` ya pasa su propio `PORT` (8000).
- Los `models/*.json` sí están en git, por eso se siguen copiando con `COPY`.
- El timeout de descarga ya está cubierto (`UV_HTTP_TIMEOUT=300` en el `Dockerfile`).

Si tu repo de modelos es **privado**, añade tu token en el Space:
Settings del Space → **Variables and secrets** → New secret → nombre `HF_TOKEN`,
valor: tu token de [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
(permiso *Read* basta). `huggingface_hub` lo usa automáticamente.

## 3. Crear el Space y subir el código (10 min + 5 min de build)

1. Abre [huggingface.co/new-space](https://huggingface.co/new-space).
2. Owner: tú. Space name: p. ej. `soc-precinct6`. SDK: **Docker** → **Blank** → Create.
3. En tu PC, clona el Space y copia el proyecto **sin** lo pesado/privado:

```powershell
git clone https://huggingface.co/spaces/TU_USUARIO/soc-precinct6
$dst = "soc-precinct6"
Copy-Item -Recurse -Force app, src, soc-ui, configs "$dst/"
Copy-Item pyproject.toml, uv.lock, Dockerfile, compose.yml, README.md "$dst/"
Copy-Item models/*.json "$dst/models/"   # crea la carpeta models/ primero si no existe
Set-Location $dst
git add -A; git commit -m "deploy spaces"; git push
```

> **NO copies**: `.venv/`, `data/*.parquet`, `models/*.pkl`, `soc-ui/node_modules/`,
> `soc-ui/dist/`, `experiments/mlruns/`, `notebooks/`, `papers/`, `contexto/`.
> (El `Dockerfile` ya descarga datos y modelos; `soc-ui/dist` se construye en el build.)

4. Al hacer `push`, el Space empieza a construir solo. Sigue el **log en la página
   del Space** (~5 min: `npm ci` + `uv sync` + descarga de parquets).
5. Cuando el log diga `Started` / el badge pase a *Running*, abre
   `https://TU_USUARIO-soc-precinct6.hf.space`.

## 4. Verificar que todo sirve (2 min)

```text
https://TU_USUARIO-soc-precinct6.hf.space/health          → {"ok":true,...,"m3_loaded":true}
https://TU_USUARIO-soc-precinct6.hf.space/queue?label=malicious&limit=2  → 2 eventos reales
https://TU_USUARIO-soc-precinct6.hf.space/                → la consola (Cola/Incidente/Grafo/Cobertura/Lab/Panorama)
```

Prueba el flujo demo: Cola → filtra `malicious` → Puntuar → abre un incidente →
Grafo con `ORG-0004/user:USER-0719` → Lab.

## 5. Día de la demo (checklist)

- [ ] Entra al Space **5 min antes**: si estaba dormido (~48 h sin visitas), tarda 1–2 min en despertar y cargar modelos.
- [ ] Plan B local por si no hay internet: `docker compose up --build` (imagen de ~3 GB ya construida) o `uv run uvicorn app.main:app` + `npm run dev` en `soc-ui/`.
- [ ] Tras la demo, descarga el feedback si te importa: el Space no lo conserva para siempre.
  En local vive en el volumen `soc_feedback` (`FEEDBACK_PATH`).

## 6. Límites del plan gratis (que no te sorprendan)

| Tema | Realidad |
|---|---|
| Precio | $0. 2 vCPU + 16 GB RAM + 50 GB disco en CPU Basic. |
| Suspensión | Se duerme tras ~48 h sin visitas; despierta al entrar. |
| Visibilidad | Público por defecto. Tus datos ya son públicos; cualquiera podrá usar `/score` y `/feedback`. No subas nada sensible. |
| Feedback | Se guarda en el disco del contenedor: sobrevive reinicios, se pierde si el Space se reconstruye. |
| Tamaño | La imagen (~3 GB, casi todo dependencias Python + CUDA de XGBoost) cabe sin problema. |

## 7. Si algo falla

| Síntoma | Causa probable | Arreglo |
|---|---|---|
| Build muere en `nvidia-nccl-cu12` / timeout | Red lenta descargando 335 MB | Ya cubierto con `UV_HTTP_TIMEOUT=300`; reintenta el build (botón *Restart* / nuevo `push`). |
| `404` descargando modelos | Nombre de usuario/repo mal en el `Dockerfile`, o repo privado sin `HF_TOKEN` | Corrige el nombre; o añade el secret `HF_TOKEN` (paso 2). |
| El Space dice *Running* pero la web no carga | Escucha en puerto distinto de 7860 | Revisa `ENV PORT=7860` y que el CMD use `${PORT}`. |
| `/health` dice `loaded:false` | Faltan `.pkl` en `models/` | Revisa el log de descarga del paso `snapshot_download` de modelos. |
| `Out of memory` (raro aquí) | Pico de RAM | Recarga; con 16 GB no debería pasar con este proyecto. |

## 8. Alternativas (si HF no te sirve)

- **Render Free**: mismo `Dockerfile`, pero 512 MB RAM (justo para 3 modelos + PyArrow) y se duerme a los 15 min. Plan B aceptable.
- **Cloud Run (Google)**: tier gratis generoso, pero pide tarjeta de crédito.
- **Solo frontend en Vercel/Netlify**: no sirve para este proyecto, el backend FastAPI no corre ahí.
