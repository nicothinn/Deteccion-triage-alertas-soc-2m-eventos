# SOC Precinct6 — rama de despliegue

Contiene **solo lo necesario para construir y desplegar** la consola SOC: `app/`, `soc-ui/`,
`src/make_sample.py`, los 3 modelos, los parquet reducidos y el `Dockerfile`.

- Plan completo: [`docs/plan_despliegue_gratis.md`](docs/plan_despliegue_gratis.md)
- Código fuente completo (notebooks, paper, EDA, tests): rama `main`
- No mergear esta rama en `main`: las eliminaciones se propagarían. Para llevar los cambios
  de deploy al proyecto, usar `git cherry-pick e8d6e2e`.

```bash
docker compose up --build     # http://127.0.0.1:8000
```
