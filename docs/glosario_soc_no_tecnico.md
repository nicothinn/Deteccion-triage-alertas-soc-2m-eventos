# SOC Precinct6 explicado para no-técnicos

> Para alguien que nunca vio ciberseguridad y quiere entender qué hacen M1, M2 y M3 y cómo implementarlos.

## 1. La historia en 30 segundos

Un **SOC** (Centro de Operaciones de Seguridad) es como la portería de un edificio gigante con 2000 cámaras.

* Cada día entran **2 millones de avisos** (logs): "alguien entró", "firewall bloqueó algo", "error de Windows".
* 94% es ruido normal (**benign**), 5% es raro (**suspicious**), 0.38% es ataque real (**malicious**).
* El problema: un humano no puede leer 2 millones. **Lo que se busca es un filtro que ponga lo peligroso arriba de la cola.**

Eso es **cazar**: que el modelo diga "esto es malicious, míralo ya".

## 2. Diccionario mínimo

| Palabra | Qué es en simple | Ejemplo |
|---|---|---|
| **Alerta / señal** | Un renglón de log. Una cámara que grabó algo. | `firewall bloqueó IP 10.0.0.5` |
| **Benign** | Normal, ignorar. | Empleado entra a su PC. |
| **Suspicious** | Raro, vigilar. | 10 claves malas seguidas. |
| **Malicious** | Ataque, escalar ya. | Exploit T1190. |
| **HOST** | Un computador. | `HOST-0101` |
| **Credencial / USER** | Usuario + contraseña. | `USER-0831` |
| **IP src/dst** | De dónde a dónde va la conexión. | `10.0.0.5 -> 8.8.8.8` |
| **Movimiento lateral** | Entrar a HOST-A y saltar a HOST-B con la misma llave robada en minutos. Cada salto solo parece normal, juntos es robo. | A las 10:01 entra a A, a las 10:03 A habla con B, a las 10:04 B roba datos. |
| **Vecindario ±5min** | Juntar todos los avisos de los mismos HOST/USER en 5 min antes y después. Ver la película, no la foto. | 1 evento solo vs 12 eventos juntos. |
| **TF-IDF** | Contar palabras dándoles peso: si "exploit" sale poco pero siempre en ataques, vale mucho. | `exploit=10pts, the=0pts` |
| **XGBoost / LightGBM** | Árboles de preguntas sí/no que votan. Barato y rápido. | ¿action=block? ¿hora=3am? ¿frac_block>0.5? |
| **Precisión** | De lo que grité "ataque", ¿cuánto sí era? | P 0.79 = de 100 gritos, 79 aciertan. |
| **Recall** | De todos los ataques reales, ¿cuántos atrapé? | R 0.97 = de 100 ataques, atrapo 97. |
| **F1 / macro-F1** | Promedio de precisión y recall. Macro = promedio de los 3 tiers. | M3 0.71 > M1 0.59 |
| **PR-AUC** | Nota global 0-1 de qué tan bien separa sin importar el umbral. | 0.82 = bueno. |
| **Split temporal** | Entrenar con el pasado, probar con el futuro. No hacer trampa viendo el futuro. | Train 26-29 jul, test 30 jul-1 ago. |

## 3. Qué hace cada modelo (receta de cocina)

### M1 tabular — el portero rápido
* **Mira:** solo casillas fijas (tipo de mensaje, producto, hora, largo del mensaje). No lee el texto.
* **Hace:** en <50ms dice benign/suspicious/malicious.
* **Puede:** filtrar lo obvio. Atrapa suspicious (R 0.96).
* **No puede:** ver ataques raros (malicious R 0.004 — de 3000 ve 14).
* **Implementar:** `OneHotEncoder` para textos cortos + `hour, msg_len, lag_h` + `LGBMClassifier(class_weight=balanced)`. Ver `experiments/m1_tabular/train.py`.

### M2 texto — el que lee la carta
* **Mira:** lo mismo que M1 + lee la carta completa (`message_sanitized`) con TF-IDF 5k palabras.
* **Hace:** si ve palabras de ataque, sube a malicious en ~100ms.
* **Puede:** cazar malicious R 0.97 (de 2288 atrapa 2219). Por palabras, no por vecinos.
* **No puede:** suspicious (R 0.16). Se volvió especialista en malicious.
* **Implementar:** `TfidfVectorizer(max_features=5000) + tabular` pegados con `hstack` + `XGBClassifier`. Ver `experiments/m2_texto/train.py`.

### M3 grafo — el que ve la película
* **Mira:** lo mismo que M1 + 8 números del vecindario: ¿cuántos vecinos? ¿cuántos HOST? ¿qué % bloqueó el firewall? ¿qué % falló login?
* **Hace:** si en ±5 min el mismo HOST/USER tiene muchos bloqueos/fallos, es ataque aunque cada línea sola parezca normal. Tarda ~1s.
* **Puede:** cazar malicious R 0.96 (2201/2288), igual que M2 pero por comportamiento, no por palabras. Detecta **movimiento lateral**.
* **No puede:** suspicious tampoco (R 0.18), y si no hay vecinos (`n_vecinos=0`) dice benign.
* **Implementar:** para cada `artifact_id`, busca en parquet `timestamp ±300s` con mismo `ORG|ip` o `ORG|user`, calcula los 8 promedios + `XGBClassifier`. Ver `experiments/m3_grafo/train.py`.

## 4. Qué se busca (objetivo)

1. **M1 rankea** la cola de 2M a 60 urgentes.
2. **M2 confirma** por texto ("dice exploit, sí es malo").
3. **M3 confirma** por contexto ("12 eventos juntos en 4 min, sí es ataque").
4. La consola muestra las 3 respuestas: **score + palabras + grafo** en una pantalla. Regla final: `escalar si alguno dice malicious`.

## 5. Cómo implementarlo tú (5 pasos)

1. Carga `data/signals/signals.parquet`.
2. Crea `hour, msg_len, lag_h`. Split por tiempo 80/20.
3. Entrena M1 (5 min CPU). Mide macro-F1.
4. Agrega TF-IDF del mensaje, entrena M2. Verás que malicious sube de 0.00 a 0.97.
5. Agrega vecindario ±5min, entrena M3. Verás F1 0.71, el mejor global.
6. Sirve con `docker compose up` → `http://localhost:8000` → prueba `/score` y `/score_graph`.

Si entiendes portero + lector + camarógrafo, entiendes todo el proyecto.
