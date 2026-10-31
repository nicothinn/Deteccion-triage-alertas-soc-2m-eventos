# Desarrollo del Punto 1 — Introducción y motivación

> Entregable: propuesta de proyecto. Secciones pedidas: (1) introducción y motivación — ¿cuál es el problema (aplicación) que abordarás? ¿por qué es importante?
> Este documento es el desarrollo completo del punto 1, listo para exponer en los 15 minutos.

## Qué es un SOC y de dónde salen los datos

Un Centro de Operaciones de Seguridad (SOC) es el equipo y la plataforma que vigilan la infraestructura de una organización: servidores, estaciones de trabajo, red, nube y aplicaciones. Esa vigilancia no la hace un solo programa: se compone de decenas de productos distintos — firewalls, antivirus y EDR, sistemas de identidad (Active Directory), plataformas cloud (AWS), servidores de virtualización, pasarelas de correo, servicios DNS.

Cada uno de esos productos escribe **registros** (logs) continuamente: syslog, auditoría de Windows, flujos de red (VPC flows), telemetría de endpoint, eventos de autenticación. Un SOC mediano genera millones de estos registros por semana. En nuestro caso, la captura que usamos contiene **2,011,674 eventos en solo 6 días**, provenientes de **4 organizaciones**, **19 productos** y **12 vendors** distintos. Esa captura va del **26 de julio al 1 de agosto de 2024**.

Estos registros no llegan "etiquetados". Una plataforma de correlación —en nuestro caso WitFoo Precinct versión 6.x— los normaliza, los sanea y los somete a un catálogo de **261 reglas de detección** (lead rules). Cuando una regla se cumple, el evento queda marcado; cuando varias señales relacionadas se agrupan, la plataforma levanta un **incidente**: un conjunto de señales disparadoras, un subgrafo de proveniencia que muestra qué tocó qué, y un reporte de caza en lenguaje natural.

## Cuál es el problema que se aborda

El problema no es "detectar ataques" en abstracto. El problema concreto es el **triage de alertas**:

> Dado **un** evento de seguridad recién llegado, hay que decidir rápido qué es, con qué confianza, y qué debe hacer el analista con él.

En términos del curso, es un problema de **clasificación supervisada multiclase**: aprender una función `f` que, dada la representación `x` de un evento, devuelva un tier `y` y un vector de probabilidades `p`:

- `x` = un evento, representado con sus campos tabulares (tipo de mensaje, producto, organización, acción, severidad, protocolo, hora, longitud del mensaje, retraso de ingesta), su mensaje crudo saneado (`message_sanitized`) y —cuando aplica— un subgrafo de su vecindario temporal de ±5 minutos.
- `y` ∈ {`benign`, `suspicious`, `malicious`}: benigno (ruido), sospechoso (algo raro, vigilar) o malicioso (parte de un ataque confirmado por incidente).
- `p` = probabilidades por clase, que la consola usa para ordenar y para aplicar umbrales operativos.
- Decisión: `escalar` si el modelo dice malicioso, o si dice sospechoso **y** la acción asociada es de bloqueo; en cualquier otro caso, `monitorear`.

La restricción temporal es parte del problema: la decisión debe tomarse en **menos de 50 milisegundos** para poder ordenar una cola de millones de eventos, y debe existir un camino por lotes para reprocesar historia (`/score_batch`, hasta 500 por llamada).

## Por qué es importante

**Primero, por volumen.** 2,011,674 eventos en 6 días es materialmente imposible de revisar a mano. Si el SOC no prioriza automáticamente, la atención humana se gasta en ruido: la mayoría de esos eventos son benignos por construcción (auditoría de Windows, respaldos de AWS, gestión de VMware), y los ataques reales quedan enterrados. Un triage automático convierte millones de filas en una cola corta ordenada por riesgo.

**Segundo, por desbalance extremo.** De esos 2 millones, **1,897,153 son benignos (94.31%)**, **106,793 sospechosos (5.31%)** y apenas **7,728 son maliciosos (0.38%)** — estos últimos son los leads de **1,584 incidentes** observados dentro de la ventana. La razón benigno:malicioso es aproximadamente **245:1**.

Esto tiene una consecuencia metodológica directa que define todo el proyecto: la métrica accuracy es inútil. Un modelo que siempre responda "benigno" acierta el 94% de las veces y no sirve para nada. Por eso el proyecto optimiza **F1-macro** y **PR-AUC por clase**, y reporta el recall de maliciosos a un FPR fijo. En seguridad el costo de un falso negativo (una brecha no detectada) es órdenes de magnitud mayor que el de un falso positivo (una alerta revisada de más); esa asimetría es el corazón del problema, no un detalle.

**Tercero, por el cambio de contexto del analista.** Decidir "¿escalo o monitoreo?" no se puede hacer con un número suelto. El analista necesita tres cosas a la vez: el **mensaje crudo** (para ver el payload o el comando), el **mapeo MITRE ATT&CK** (para saber qué técnica y qué playbook aplica) y la **cadena del ataque** (para entender si esto es un paso de algo más grande). Por eso la salida del sistema no es solo un tier: incluye probabilidades, técnicas ATT&CK y —en la consola— el grafo del incidente y el reporte de caza. El objetivo es que las tres respuestas (score, palabras, grafo) estén en **una sola pantalla**.

**Cuarto, porque la "verdad" es imperfecta y hay que saberlo.** Las etiquetas no provienen de un analista humano que revisó cada evento: provienen de la correlación automática de Precinct. La mayoría de las señales (2,005,877 de 2,011,674) están en `disposition = Unprocessed`, es decir, correlacionadas pero nunca analizadas por una persona. El sistema, por tanto, tiene que aprender de un **oráculo fuerte pero ruidoso**, que es exactamente la situación de producción. Esto obliga a ser honesto en las conclusiones y a tratar las etiquetas como priors, no como verdad confirmada.

**Quinto, porque el tiempo importa: hay deriva.** Los leads maliciosos terminan el 30 de julio, mientras que el tráfico benigno continúa hasta el 1 de agosto. Esa asimetría significa que si uno mezcla y reparte al azar (shuffle), el modelo puede memorizar ráfagas de campaña y parecer excelente sin generalizar. Por eso el protocolo de evaluación es un **split temporal**: entrenar con el pasado y probar con el futuro. Esto penaliza memorizar y acerca la evaluación a la realidad operativa.

## Cómo se traduce esto en una solución

El problema anterior se convierte en un sistema con tres modelos que se complementan, porque un solo modelo no cubre las tres caras del problema:

- **M1 (tabular, LightGBM)** resuelve el volumen: es rapidísimo (<50 ms) y separa bien lo benigno y lo sospechoso. Pero con un desbalance de 245:1 **colapsa en lo malicioso**: su recall de maliciosos es 0.0045. Es un baseline honesto que demuestra que mirar solo campos no alcanza.
- **M2 (texto, TF-IDF 5k + XGBoost)** resuelve la semántica: al leer el mensaje crudo, eleva el recall de maliciosos a 0.97, porque los tokens de exploit (T1190) son la evidencia que los campos no traen. Cuesta ~100 ms.
- **M3 (grafo, vecindario ±5 min + XGBoost)** resuelve la estructura: junta lo que ocurrió en la misma credencial o máquina en 5 minutos y detecta movimiento lateral y cadenas, invisibles mirando una sola fila. Da el mejor F1-macro (0.719) con recall de maliciosos 0.96.

Los tres se sirven en cascada: M1 ordena la cola, M2 confirma por texto, M3 confirma por contexto. Esa cascada es la respuesta arquitectónica al problema: no se puede ganar en volumen, semántica y estructura con una sola representación.

## Alcance y límites de esta motivación

El proyecto se limita a eventos de la captura viva (`signals`); no mezcla la tabla histórica `incident_signals` (238,511 leads de 2022–2024) porque esa es otra línea de tiempo y hacerlo contaminaría el split temporal. Tampoco promete atribución ATT&CK por evento aprendida: en esta captura las técnicas son priors derivados de las reglas, y un experimento multi-etiqueta (M4/M4b) demostró que a nivel evento solo T1190 es separable, con la cola (T1204, T1486, T1566) sin soporte suficiente. Por eso la consola sirve un **mapeo tier→técnicas** declarado explícitamente como tal, y no un modelo aprendido que mentiría con precisión 0.08.
