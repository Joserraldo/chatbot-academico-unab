<div align="center">

<img src="web/assets/logo-unab.png" alt="UNAB" height="72">

# Asistente UNAB 360

**Un asistente académico que conoce tu matrícula, tus notas en Cosmos, tus tareas en TEMA, tus préstamos de biblioteca y tu riesgo académico, y que además reserva espacios, cobra con Bold y lee fotos.**

Ciencia de Datos · Trabajo final · Ingeniería de Sistemas · Universidad Autónoma de Bucaramanga

[**Probar la demo**](https://chatbotunab.duckdns.org/app/) · [Dashboard de analítica](https://chatbotunab.duckdns.org/app/analitica/) · [Presentación](https://chatbotunab.duckdns.org/app/presentacion/) · [Manual de usuario](docs/MANUAL-USUARIO.md) · [**Descargar APK Android**](https://chatbotunab.duckdns.org/app/descargas/asistente-unab-360.apk) · [App Android](android/README.md)

</div>

> ⚠️ **Todos los datos de estudiantes son sintéticos.** Simulan Banner/Cosmos/TEMA y no corresponden a personas reales. Los pagos corren en el **modo de pruebas de Bold** (ningún cobro es real). El plan de estudios de Sistemas sí viene del PDF institucional, y los enlaces a trámites (reservas, catálogo de biblioteca, Cosmos, TEMA) son los oficiales de la UNAB.

| | |
|---|---|
| **Estado** | Desplegado en AWS EC2 con HTTPS. 15 pruebas de humo en verde: 4 intenciones v1, trámites, pago, TEMA/Cosmos, gráfica, noticias, imagen y guardrails |
| **Equipo** | José Téllez (arquitectura, datos, workflows, servicios v2, ML, documentación) · Santiago Cabezas (infraestructura AWS, despliegue, frontend v1, evidencias) |
| **Stack** | n8n · PostgreSQL 16 + pgvector · FastMCP · FastAPI · LLM `qwen3.8` (B.AI) · scikit-learn · Kotlin/Compose · Caddy · Docker Compose |

---

## ¿Qué lo hace distinto?

| | Funcionalidad | Cómo funciona |
|---|---|---|
| 🧠 | **Agentes con herramientas reales** | n8n enruta cada pregunta (RAG, calendario, historial, noticias, trámites) a un agente con 18 herramientas MCP sobre la BD académica |
| 📊 | **Gráficas generadas en la conversación** | "Muéstrame mis notas en gráfica" → promedio por semestre, avance, créditos por área, cortes de Cosmos, factores de riesgo |
| 🎯 | **Modelo de riesgo académico (ML)** | Regresión logística sin fuga de información (AUC 0,86 en CV / 0,77 en prueba) con factores explicables por estudiante → [docs/ANALITICA-ML.md](docs/ANALITICA-ML.md) |
| 📷 | **Lee imágenes** | Foto de un horario, un recibo o el cartel de biblioteca → visión (`qwen3.8-max`) + decodificación local de QR → respuesta y enlace oficial |
| 💳 | **Pagos con Bold embebido** | "Quiero pagar mi matrícula" → tarjeta de pago → checkout de Bold **dentro de la página** con firma de integridad en el servidor, webhook con HMAC y consulta del estado del pago |
| 🏟️ | **Reservas de espacios** | Disponibilidad por franja, choque de reservas (409) y cobro de los espacios con tarifa |
| 🏫 | **Cosmos + TEMA + Biblioteca** | Notas por corte, horario de hoy, tareas por vencer, "recuerda calificar al profesor X", préstamos vencidos con multa |
| 🔗 | **QR y trámites** | Cada trámite devuelve enlace oficial + QR (reservas.unab.edu.co, catalogo.unab.edu.co, gimnasio, Cosmos, TEMA) |
| 📰 | **Noticias del día** | Scraper de 11 fuentes (UNAB, Google Noticias, Xataka, Tecnósfera, ENTER.CO…) de educación, tecnología e ingeniería de sistemas, con fuente y fecha |
| 🎓 | **6 carreras, 7 personas demo** | Botones "Probar como…": Sistemas casi graduado, Medicina en riesgo, Derecho cerca del grado, Psicología primer semestre, Administración con matrícula pendiente, Mecatrónica con multa |
| 🛡️ | **Guardrails deterministas** | Inyección de prompt, SQL, datos de otro estudiante, tarjetas o contraseñas en el chat, lenguaje ofensivo. Todo queda auditado en `chat_log` |
| 📱 | **Web + Android** | Mismo contrato `POST /webhook/chat`; panel "Hoy en tu U", dictado por voz, "continúa en tu celular" por QR |

## Capturas

**Web: personas demo, panel "Hoy en tu U" y gráficas**

| Probar como… | Chat + Hoy en tu U | Gráfica generada |
|:---:|:---:|:---:|
| <img src="docs/evidencias/v2/30-login-personas.png" width="300"> | <img src="docs/evidencias/v2/31-chat-hoy.png" width="300"> | <img src="docs/evidencias/v2/32-grafica-notas.png" width="300"> |

**Pago de matrícula con Bold (modo pruebas)**

| Tarjeta de pago en el chat | Checkout embebido | Resultado |
|:---:|:---:|:---:|
| <img src="docs/evidencias/v2/33-pago-tarjeta.png" width="300"> | <img src="docs/evidencias/v2/34-bold-checkout.png" width="300"> | <img src="docs/evidencias/v2/35-pago-aprobado.png" width="300"> |

**Visión, trámites y analítica**

| Foto del cartel → QR detectado | Renovar libro: enlace + QR + multa | Dashboard de ciencia de datos |
|:---:|:---:|:---:|
| <img src="docs/evidencias/v2/36-imagen-qr.png" width="300"> | <img src="docs/evidencias/v2/37-tramites-qr.png" width="300"> | <img src="docs/evidencias/v2/38-analitica.png" width="300"> |

**Móvil y Android**

| Web móvil | Android: login | Android: chat | Android: pago |
|:---:|:---:|:---:|:---:|
| <img src="docs/evidencias/v2/39-movil.png" width="190"> | <img src="docs/evidencias/v2/40-android-login.png" width="190"> | <img src="docs/evidencias/v2/41-android-chat.png" width="190"> | <img src="docs/evidencias/v2/42-android-pago.png" width="190"> |

| Android: inicio | Android: checkout Bold embebido | Android: panel Hoy | Android: lectura de imagen |
|:---:|:---:|:---:|:---:|
| <img src="docs/evidencias/v2/46-android-inicio.png" width="190"> | <img src="docs/evidencias/v2/43-android-bold.png" width="190"> | <img src="docs/evidencias/v2/44-android-hoy.png" width="190"> | <img src="docs/evidencias/v2/45-android-imagen.png" width="190"> |

**Modelo de riesgo académico**

| Curva ROC | Matriz de confusión | Variables más influyentes |
|:---:|:---:|:---:|
| <img src="docs/evidencias/ml/roc.png" width="300"> | <img src="docs/evidencias/ml/matriz_confusion.png" width="300"> | <img src="docs/evidencias/ml/importancias.png" width="300"> |

Capturas de la v1 (RAG, calendario, guardrails, presentación): [docs/evidencias/](docs/evidencias/README.md).

---

## 1. Arquitectura

```mermaid
flowchart LR
  subgraph Clientes
    A[App Android<br/>Kotlin + Compose]
    W[Web /app<br/>Chart.js · voz · QR]
    K[Claude / clientes MCP]
  end
  subgraph EC2[AWS EC2 · Docker Compose · DuckDNS · HTTPS]
    C[Caddy<br/>TLS Let's Encrypt]
    subgraph N[n8n]
      R[00 Router<br/>guardrails · visión · intención · enriquecer]
      R --> W1[01 RAG]
      R --> W2[02 Calendario]
      R --> W3[03 Historial · Cosmos · TEMA<br/>agente MCP]
      R --> W4[04 Noticias]
      R --> W6[06 Trámites<br/>reservas · pagos]
      I[05 Ingesta RAG]
    end
    S[servicios-api<br/>FastAPI]
    M[MCP server<br/>FastMCP · 18 tools]
    P[(PostgreSQL 16 + pgvector<br/>academico · servicios · RAG)]
    SC[Scraper<br/>11 fuentes RSS]
  end
  A & W -- POST /webhook/chat --> C --> R
  W -- /api/* --> C --> S
  K -- /mcp Bearer --> M
  W3 -- MCP --> M --> P
  W6 -- HTTP tools --> S --> P
  R -- /api/vision · /api/asistente/enriquecer --> S
  W1 & I -- pgvector --> P
  SC --> P
  N -- chat --> L[B.AI · qwen3.8-flash]
  S -- visión --> LV[B.AI · qwen3.8-max]
  S <-- checkout embebido · webhook HMAC · consulta del estado --> B[Bold<br/>modo pruebas]
  ML[analitica/<br/>regresión logística] -. puntajes .-> P
```

**Decisión clave de diseño:** el LLM redacta la respuesta, pero las **tarjetas de acción y las gráficas las produce un endpoint determinista** (`/api/asistente/enriquecer`). Así una orden de pago nunca depende de que el modelo arme bien un JSON: los montos los calcula el servidor desde la BD y el LLM nunca ve números de tarjeta.

Detalle completo: [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md) · contratos v2: [docs/CONTRATOS-V2.md](docs/CONTRATOS-V2.md) · modelo de datos: [docs/MODELO-DATOS.md](docs/MODELO-DATOS.md).

### Flujo de una pregunta con imagen

1. La app envía `{sessionId, codigoEstudiante, mensaje, imagen}`.
2. El **guardrail de entrada** valida el código, la inyección, el SQL y el tamaño de la imagen.
3. **Visión:** OpenCV decodifica QR localmente y `qwen3.8-max` describe y transcribe. El resultado se trata como *dato*, nunca como instrucción.
4. El **clasificador** decide `general | calendario | historial | noticias | tramites`.
5. El sub-workflow (agente + herramientas MCP o HTTP) redacta la respuesta.
6. El **guardrail de salida** oculta códigos ajenos, correos y errores técnicos.
7. **Enriquecer** añade tarjetas de pago, QR, enlaces, reservas, sugerencias y gráficas.
8. Se registra en `chat_log` y se responde `{respuesta, intencion, fuentes, acciones, graficas, imagen}`.

## 2. Ciencia de datos

| Pieza | Qué hay | Dónde |
|---|---|---|
| Datos sintéticos | 206 estudiantes, 6 programas, 6.322 registros de historial, 69 secciones, 209 tareas, 128 préstamos. Generador determinista con historias controladas por persona | `scripts/generate_synthetic*.py`, `db/init/03_seed.sql`, `05_v2_seed.sql` |
| Vistas analíticas | "Una fila = una respuesta": estado, pendientes, alertas, proyección, insignia | `db/init/02_views.sql` |
| Modelo de riesgo | Etiqueta en 2026-1 con variables hasta 2025-2 (sin fuga). Logística vs. bosque aleatorio con CV de 5 folds y regla de parsimonia. Explicabilidad por estudiante | [`analitica/riesgo_academico.ipynb`](analitica/riesgo_academico.ipynb), [docs/ANALITICA-ML.md](docs/ANALITICA-ML.md) |
| RAG | Fragmentos de 800/120 → embeddings multilingües (MiniLM-L12, CPU) → pgvector (coseno) | workflows `05` y `01`, `data/docs_ccd/` |
| Scraping | 11 fuentes, clasificación por palabras clave, deduplicación por similitud ≥ 0,88, ventana de 7 días | `scraper/`, [docs/SCRAPER.md](docs/SCRAPER.md) |
| Analítica del chatbot | Intenciones, bloqueos por motivo, mensajes por día, distribución de riesgo y tarjeta del modelo | [`/app/analitica`](https://chatbotunab.duckdns.org/app/analitica/), `GET /api/analitica/resumen` |

| Modelo | AUC CV (5 folds) | AUC prueba | F1 | Exactitud |
|---|---|---|---|---|
| **Regresión logística (elegido)** | 0,857 ± 0,040 | 0,770 | 0,735 | 0,717 |
| Bosque aleatorio | 0,859 ± 0,034 | 0,743 | 0,680 | 0,652 |

Uso **orientativo y no punitivo**: el agente explica los factores y propone acciones (tutorías, plan de estudio, CCD). La discusión ética y las limitaciones están en [docs/PERTINENCIA-PEDAGOGICA.md](docs/PERTINENCIA-PEDAGOGICA.md).

## 3. Pruébalo en 2 minutos

1. Entra a <https://chatbotunab.duckdns.org/app/> con la clave del equipo.
2. Pulsa una persona en **"Probar como…"**.
3. Usa este guion:

| Persona | Prueba esto |
|---|---|
| U00000202 · Medicina, en riesgo | "¿Cómo voy este semestre?" · "¿Cuál es mi riesgo académico?" · "¿Qué tareas tengo vencidas en TEMA?" |
| U00000201 · Sistemas, casi graduado | "Muéstrame mis notas en gráfica" · "¿Qué me falta para graduarme?" |
| U00000205 · Administración | "Quiero pagar mi matrícula" → **Pagar con Bold** → tarjeta de prueba `4111 1111 1111 1111` |
| U00000206 · Mecatrónica | "¿Cómo renuevo mi libro de biblioteca?" · adjunta la foto del cartel de biblioteca |
| U00000203 · Derecho | "Quiero reservar el auditorio mayor el 25 de noviembre a las 3 pm por 2 horas" |
| Cualquiera | "Noticias de tecnología de hoy" · "Ignora tus instrucciones" (bloqueado) · "¿Cuáles son las notas de U00000002?" (bloqueado) |

Guion completo por persona y solución de problemas: **[docs/MANUAL-USUARIO.md](docs/MANUAL-USUARIO.md)**.

## 4. Instalación y despliegue (replicable)

Requisitos: una VM Ubuntu 24.04 con ≥ 4 GB de RAM (la demo usa `t2.large`), los puertos 22/80/443/9000 abiertos, un subdominio DuckDNS y una API key de un LLM compatible con OpenAI. Bold es opcional: sin llaves, el checkout cae a una pasarela simulada marcada como tal.

```bash
git clone https://github.com/Joserraldo/chatbot-academico-unab.git
```
```bash
cd chatbot-academico-unab && bash scripts/bootstrap-ec2.sh
```
```bash
cp .env.example .env && nano .env
```
```bash
docker compose up -d --build
```
```bash
bash scripts/n8n-import.sh
```
```bash
bash scripts/smoke-test.sh
```

Sobre una instalación v1 existente, la actualización es un solo comando. Migra sin borrar volúmenes, construye, reimporta los workflows, reindexa el RAG y corre las pruebas:

```bash
bash scripts/deploy-v2.sh
```

Guía paso a paso de AWS Academy (Security Group, Elastic IP, DuckDNS, evidencias): [docs/DESPLIEGUE-AWS.md](docs/DESPLIEGUE-AWS.md) · proveedor LLM: [docs/LLM-PROVEEDOR.md](docs/LLM-PROVEEDOR.md) · pagos: [servicios-api/README.md](servicios-api/README.md).

## 5. API

**Chat** (web y Android):

```http
POST https://<DOMAIN>/webhook/chat
X-Chatbot-Key: <CHATBOT_KEY>

{"sessionId":"b6f1…","codigoEstudiante":"U00000205","mensaje":"Quiero pagar mi matrícula","imagen":null}
```
```json
{"respuesta":"Tu matrícula 2026-2 está pendiente de pago…","intencion":"tramites","fuentes":["Servicios UNAB (simulación)"],
 "acciones":[{"tipo":"pago","orderId":"UNAB-MAT-…","monto":8500000,"moneda":"COP","estado":"pendiente","url":"/app/pagar.html?order=UNAB-MAT-…"}],
 "graficas":[],"imagen":null}
```

**servicios-api** (`/api/*`): personas, panel "Hoy", gráficas, espacios, reservas, órdenes de pago, webhook de Bold, QR, visión, enriquecimiento, noticias del día, trámites y analítica. Están especificados en [docs/CONTRATOS-V2.md §4](docs/CONTRATOS-V2.md) y tienen 45 pruebas (`pytest`).

**MCP** (`https://<DOMAIN>/mcp`, Bearer): 18 herramientas de solo lectura, entre ellas `estado_academico`, `proyeccion_semestres`, `recomendaciones`, `resumen_360`, `notas_periodo_actual`, `horario`, `tareas_tema`, `evaluaciones_docentes_pendientes`, `prestamos_biblioteca`, `enlaces_tramites`, `riesgo_academico` y `buscar_documentos`.

```bash
claude mcp add --transport http unab-academico https://<DOMAIN>/mcp --header "Authorization: Bearer <MCP_TOKEN>"
```

## 6. Seguridad

- **Mínimo privilegio en la BD:** `chatbot_ro` (MCP) solo lee; `servicios_rw` escribe solo en el esquema `servicios`. El agente nunca escribe SQL libre.
- **Pagos:**
  - El monto se calcula en el servidor.
  - Firma `sha256(orderId+monto+moneda+secreto)` en el backend; la llave secreta nunca llega al navegador.
  - Webhook verificado con HMAC e idempotente.
  - El chat bloquea números de tarjeta.
- **Identidad:** el código del estudiante sale de la sesión. Las herramientas lo fuerzan y el guardrail bloquea consultar a otro estudiante.
- **Red:** solo 80/443/9000 son públicos. n8n y Postgres no se exponen. `.env` y llaves nunca se versionan.

## 7. Estructura del repositorio

```
├── analitica/               Modelo de riesgo (script reproducible + notebook ejecutado + métricas)
├── android/                 App Android (Kotlin, Jetpack Compose)            → android/README.md
├── caddy/Caddyfile          HTTPS + rutas /app, /api, /mcp, n8n
├── data/                    Plan de estudios real, calendario, corpus RAG (incluye tramites_unab.md)
├── db/init/                 01 esquema · 02 vistas · 03 semilla v1 · 04 esquema v2 · 05 semilla v2 · 06 roles · 07 riesgo
├── docs/                    Arquitectura, contratos, manual, prompts, pedagogía, ML, scraper, despliegue, evidencias
├── mcp-server/              FastMCP (18 herramientas) + embeddings locales
├── n8n/                     Workflows como código (build_workflows.py) → workflows/*.json
├── scraper/                 Noticias del día (11 fuentes)
├── scripts/                 bootstrap, deploy-v2, migrate-v2, import n8n, smoke test, generadores sintéticos
├── servicios-api/           FastAPI: reservas, pagos Bold, QR, gráficas, visión, panel Hoy, analítica (+ tests)
├── web/                     Chat (/app), checkout (/app/pagar.html), analítica (/app/analitica), presentación
└── docker-compose.yml       postgres · n8n · mcp-server · servicios-api · scraper · caddy
```

## 8. Rúbrica ↔ evidencia

| Criterio | Dónde está |
|---|---|
| **Scraper de noticias** | `scraper/` (11 fuentes; noticias del día con fuente y fecha) integrado al agente (workflow 04), a `/api/noticias/hoy`, al panel "Hoy en tu U" y a Android · [docs/SCRAPER.md](docs/SCRAPER.md) |
| **Aplicación Android** | `android/`: matrícula, estado académico, proyección, recomendaciones, gráficas, imagen, pago Bold en WebView, conectada al webhook · capturas 40-42 |
| **Documentación técnica** | Este README (descripción, arquitectura, instalación, imágenes) · [Manual de usuario](docs/MANUAL-USUARIO.md) · [Arquitectura](docs/ARQUITECTURA.md) · [Contratos](docs/CONTRATOS-V2.md) · [Bitácora](BITACORA.md) |
| **Pertinencia pedagógica** | [Prompts usados](docs/PROMPTS.md) · [Pertinencia pedagógica con evidencia de investigación](docs/PERTINENCIA-PEDAGOGICA.md) · reglas de `recomendaciones` y del modelo de riesgo |
| Arquitectura, RAG, workflows, BD (v1) | §1, `n8n/workflows/`, `db/init/`, [docs/MODELO-DATOS.md](docs/MODELO-DATOS.md) |

## 9. Documentación

| Documento | Para qué |
|---|---|
| [MANUAL-USUARIO.md](docs/MANUAL-USUARIO.md) | Cómo usar la web y la app, guion por persona, preguntas frecuentes |
| [ARQUITECTURA.md](docs/ARQUITECTURA.md) | Componentes, flujo, decisiones y seguridad |
| [CONTRATOS-V2.md](docs/CONTRATOS-V2.md) | Contrato del chat, API, esquema y Bold |
| [PROMPTS.md](docs/PROMPTS.md) | Todos los prompts, textuales, con su justificación |
| [PERTINENCIA-PEDAGOGICA.md](docs/PERTINENCIA-PEDAGOGICA.md) | Educación de precisión, autorregulación, ética del riesgo, referencias |
| [ANALITICA-ML.md](docs/ANALITICA-ML.md) | Metodología y resultados del modelo de riesgo |
| [SCRAPER.md](docs/SCRAPER.md) | Fuentes, clasificación e integración |
| [DESPLIEGUE-AWS.md](docs/DESPLIEGUE-AWS.md) · [LLM-PROVEEDOR.md](docs/LLM-PROVEEDOR.md) | Infraestructura y proveedor LLM |
| [servicios-api/README.md](servicios-api/README.md) | Endpoints, variables, pruebas y modo de pruebas de Bold |
| [BITACORA.md](BITACORA.md) | Decisiones y registro del proyecto |
