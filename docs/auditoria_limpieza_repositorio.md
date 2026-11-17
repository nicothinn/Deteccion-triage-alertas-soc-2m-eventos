# Auditoría de limpieza y versionado

**Fecha:** 2026-11-16
**Alcance:** inventario del árbol, `git status`, reglas de Git/Docker ignore, archivos de configuración, código fuente, experimentos, notebooks, pruebas y entregables. En la limpieza se borraron solo los artefactos listados en “Eliminado”; no se tocaron notebooks, Parquet, pesos ni métricas del usuario.

> No es una inspección forense de los bytes internos de cada Parquet, pickle, PDF o PPTX. Esos artefactos se clasifican por su función, referencias y metadatos disponibles. Tampoco se analizó metadata oculta de PDF/PPTX.

## Resumen ejecutivo

- **No limpiar el árbol con `git clean` ni `git reset`.** Hay cambios de trabajo en notebooks, métricas, reportes y UI; algunos son previos a esta auditoría.
- **No ignorar todos los notebooks ni todas las figuras.** Son parte de la investigación y algunos archivos se usan en el paper y las diapositivas.
- Mantener en Git el código, pruebas, locks, documentación final, métricas JSON y entregables citados.
- Mantener fuera de Git los Parquet, pickles, feedback de analistas, entornos virtuales, cachés y logs temporales.
- Corregir los cálculos y afirmaciones obsoletas antes de regenerar los informes; de otro modo, volverán a aparecer en la próxima ejecución.

## Qué conservar en Git

| Grupo | Archivos | Motivo |
|---|---|---|
| Aplicación | `app/`, `src/`, `soc-ui/src/`, `soc-ui/public/` | API, lógica de carga/análisis y UI mantenible. |
| Pruebas | `tests/test_*.py` | Protegen el comportamiento del proyecto y las rutas de la consola. |
| Dependencias y despliegue | `pyproject.toml`, `uv.lock`, `soc-ui/package.json`, `soc-ui/package-lock.json`, configs de Vite/TS, `Dockerfile`, `compose.yml` | Reproducibilidad y construcción de la aplicación. |
| Experimentos | `experiments/**/train.py`, `experiments/m1_tabular/leaderboard.csv` | Código necesario para reproducir los resultados; no incluir el tracking local de MLflow. |
| Investigación | `notebooks/00_...` a `notebooks/10_...` | EDA, ablaciones y evidencia del proceso. Revisar outputs antes de entregar; no ignorar toda la carpeta. |
| Resultados compactos | `models/*_metrics.json`, `models/m1_meta.json` | Los lee `/model/metrics` y alimentan Lab/Panorama. Mantenerlos sincronizados con los entrenamientos. |
| Procedencia | `data/README_HF.md`, `data/reference/lead_rules_catalog.json`, `data/build/*.json` | Documentan origen, reglas y verificaciones del dataset. Los JSON de `data/build` ya están versionados. |
| Entregables | `reports/paper.tex`, el PDF final aprobado, fuentes de presentación y las figuras que usan | Son productos académicos, no caché. El paper referencia `architecture.pdf`, `confusion_m1.pdf`, `label_distribution.pdf` y `temporal_volume.pdf`. |
| Documentación | `README.md`, `docs/*.md`, `reports/eda/*.md` y CSV del diccionario | Instalación, metodología, límites y lectura de resultados. Corregir primero las afirmaciones obsoletas señaladas abajo. |

Los archivos `models/m1.pkl`, `m2.pkl` y `m3.pkl` **no deben borrarse del entorno de despliegue**: Docker los requiere para cargar M1/M2/M3. La recomendación es no meterlos en Git; deben obtenerse o entrenarse antes de construir la imagen.

## Qué no incluir en Git

Ya están ignorados correctamente: `.venv/`, cachés y bytecode Python, `data/**/*.parquet`, `models/*.pkl`, `experiments/mlruns/`, `data/feedback.csv`, `soc-ui/dist/`, PDFs locales de `papers/` y `contexto/`, y auxiliares de LaTeX (`*.aux`, `*.log`, `*.out`, etc.). `soc-ui/.gitignore` excluye `node_modules`, `dist` y `*.log`.

Ajustes de ignore aplicados:

- `.gitignore` ahora excluye checkpoints de notebooks, `out_tmp.txt`, `out3_tmp.txt` y los PDFs regenerables no usados por el paper o la presentación final.
- `.dockerignore` ahora excluye `data/feedback.csv`, experimentos, tests, docs, contexto y reportes que el Dockerfile no copia. Evita enviar feedback local y archivos de investigación al builder.
- **No se ignora `reports/figures/` entera.** Se conservan las figuras citadas por el paper y `reports/presentacion_final.tex` (`compare_m123.pdf` y `pr_m2.pdf`).
- Los notebooks y otras figuras sin seguimiento siguen siendo trabajo en progreso; añadirlos selectivamente, no con `git add .`.

## Eliminado tras verificar referencias

- `out_tmp.txt`, `out3_tmp.txt`: volcados temporales; sus métricas principales ya están en los notebooks M2/M3.
- `reports/paper.aux`, `reports/paper.log`, `reports/paper.out` y `soc-ui/dev.log`: salidas/logs recreables.
- `soc-ui/src/assets/hero.png`, `react.svg`, `vite.svg`: búsqueda completa sin referencias en la UI.
- PDFs regenerables de `reports/figures/` no utilizados por paper o presentación final: `compare_m1_m2.pdf`, `compare_m4family.pdf`, `compare_m6.pdf`, `confusion_m2.pdf`, `confusion_m3.pdf`, `graph_feats_m3.pdf`, `pr_m3.pdf`, `tactics_m4d.pdf`, `thresholds_m4t.pdf` y `tokens_m2.pdf`.
- Se conservaron `architecture.pdf`, `confusion_m1.pdf`, `label_distribution.pdf`, `temporal_volume.pdf` (paper/diapositivas) y `compare_m123.pdf`, `pr_m2.pdf` (presentación final).
- `configs/` sigue vacía y no aparece en Git; Git no versiona directorios vacíos.

**No eliminado:** Parquet, pickles, `data/feedback.csv`, notebooks sin seguimiento, métricas modificadas ni PDFs/PPTX de entrega. El `git status` mostraba cambios activos en esos grupos; no se asumieron descartables.

## Ediciones recomendadas, por prioridad

| Prioridad | Archivo(s) | Hallazgo | Acción recomendada |
|---|---|---|---|
| Alta | `src/eda_report.py:72,74` | El generador todavía afirma M2 recall ≈0.97 y M3 F1 0.719 como “verificados”; también refiere `notebooks/eda_completo.ipynb`, que no existe en el árbol actual. | Actualizar las conclusiones con la evaluación temporal vigente y las limitaciones no causales de M3; corregir la ruta de reproducción; regenerar `reports/eda/resumen_eda.md`. |
| Alta | `experiments/m4d_tactics/train.py:81,96–99` | PR-AUC se calcula sobre `P`, que ya contiene predicciones binarias (`>=0.5`); `models/m4d_metrics.json` declara que usa scores continuos. | Calcular AP con probabilidades continuas; volver a ejecutar el experimento y regenerar el JSON. |
| Alta | `experiments/m4t_thresholds/train.py:128–131` | La tabla `per_label.fixed_05` guarda el umbral tuned (`thresholds[t]`) aunque esas predicciones se calculan con 0.5. | Guardar `0.5` en las filas fijas; regenerar y comprobar `m4t_metrics.json`. |
| Alta | `app/main.py:34` | El fallback de M1 si falta el JSON usa F1 0.599 y 112,848 filas, resultados retirados; los resultados actuales son F1-macro 0.6276 y train 137,508. | Sincronizar el fallback con el baseline vigente o mostrar un mensaje claro de métricas ausentes. |
| Alta | `docs/glosario_soc_no_tecnico.md`, `docs/documentacion_end_to_end.md`, `reports/paper.tex`, `reports/paper.pdf` | Aún aparecen recall M2 0.97, M3 0.719 como medida vigente o “pendiente” sin la medición causal de muestra. | Alinear con el README y notebooks vigentes; describir 0.7186 como cota no causal y 0.6043 como muestra causal balanceada, no comparable directamente con M1/M2; recompilar el paper desde `.tex`. |
| Media | `docs/referencias_primer_entregable.md:119` | Indica `uv run explorar.py`, pero el script está en `src/explorar.py`. | Cambiar a `uv run python src/explorar.py`. |
| Media | `docs/casos_primera_entrega.md:3` | La consigna apunta a `contexto/course_project_guide.pdf`, pero ese PDF está excluido por `.gitignore`; no llegará en un clon limpio. | Enlazar una fuente accesible o indicar claramente que el archivo no se distribuye; no quitar la regla de ignore sin permiso para redistribuirlo. |
| Media | `pyproject.toml` y `Dockerfile` | `jupyter`, `mlflow`, `datasets`, `matplotlib` y `seaborn` figuran como dependencias principales; `uv sync --no-dev` las instala también en la imagen de runtime. | Separar dependencias de entrenamiento/notebooks de las necesarias para servir la API, y reconstruir el lockfile. Cambio útil para bajar tamaño/tiempo de imagen; probar antes de borrar paquetes. |
| Media | `.dockerignore` | No excluye `data/feedback.csv` ni `experiments/mlruns/`. | Excluir ambos para evitar enviar feedback local y tracking innecesario al builder. |
| Baja | `soc-ui/src/assets/` | `react.svg`, `vite.svg` y `hero.png` parecen no referenciados por la UI. | Confirmar con búsqueda completa y borrar solo los recursos realmente no usados. |

## Comentarios, autoría y marcas

- La búsqueda de texto encontró **25 comentarios `ponytail:` en 12 archivos**. Son etiquetas visibles de estilo/comentario, no una marca de agua incrustada. Revisar cada uno: borrar el prefijo meta si no aporta; conservar o reescribir la razón técnica útil (por ejemplo, límites de escaneo, ventana causal o decisiones de latencia).
- La búsqueda no encontró referencias textuales explícitas a `ChatGPT`, `OpenAI` o `Copilot` en las extensiones revisadas. **No se inspeccionó metadata interna de PDF/PPTX ni bytes de Parquet/pickle**, así que no se puede afirmar que estén libres de toda metadata o marca.
- No recomiendo cambiar el código para aparentar una autoría distinta ni evadir detectores. Para una entrega académica, sigue las reglas del curso y declara asistencia de herramientas cuando corresponda. Mejorar comentarios, pruebas y comprensión sí es una edición técnica legítima.

## Orden de trabajo sugerido

1. Arreglar los dos cálculos M4d/M4t y actualizar el generador EDA; regenerar métricas/informe.
2. Unificar README, glosario, end-to-end, paper y gráficas con los resultados finales.
3. Añadir ignores de checkpoints/temporales y de feedback/MLflow al contexto Docker, sin ignorar notebooks ni figuras citadas.
4. Revisar los archivos untracked uno por uno; separar entregables de archivos temporales antes de preparar cualquier commit.
5. No usar `git clean -fd` ni `git reset --hard`: el árbol contiene cambios activos.
