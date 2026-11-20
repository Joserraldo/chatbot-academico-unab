# Bitácora del proyecto

Registro cronológico de decisiones, avances y problemas. Formato: fecha · responsable · qué se hizo · problemas/decisiones.

---

## 2026-11-13 · José Téllez — Arranque del repositorio

**Hecho**
- Lectura del enunciado (Tema 2, diapositivas 6-12) y del plan de estudios vigente (PDF institucional).
- Extracción del plan a `data/plan_estudios_ing_sistemas.json`: 48 cursos, 151 créditos, 9 semestres. El PDF no trae códigos de curso ni prerrequisitos → se generaron códigos (`ÁREA+semestre+consecutivo`) y 31 prerrequisitos **ilustrativos**, documentados como tales.
- Modelo de datos `academico` que simula Banner/Cosmos + 8 vistas analíticas para agentes.
- Generador de datos sintéticos determinista (200 estudiantes, estudiante demo `U00000001`).
- Servidor MCP con FastMCP (10 herramientas, Streamable HTTP en el puerto 9000, bearer token, rol de BD de solo lectura).
- Scraper de noticias sobre el RSS público de unab.edu.co.
- 6 workflows de n8n generados como código (router + 01-04 + ingesta).
- App Android (Kotlin + Compose) que consume el webhook.
- docker-compose (Postgres+pgvector, n8n, MCP, scraper, Caddy), scripts de EC2/DuckDNS/importación/smoke test.
- Documentación: README, arquitectura, despliegue AWS, proveedor LLM, modelo de datos, continuación, evidencias.

**Pruebas locales** (sin Docker en el PC): Postgres embebido (`pgserver`) para BD/vistas/MCP/scraper; n8n 2.47.7 instalado con npm para validar la importación, publicar los workflows y probar el webhook (rama de guardrails). Detalle en `docs/CONTINUACION.md`.

**Decisiones**
- LLM por API compatible con OpenAI (b.ai, `qwen-flash`): las instancias de AWS Academy no tienen GPU ni RAM para un modelo local.
- Postgres+pgvector en la misma VM en lugar de Supabase (sin cuentas externas ni pausas del plan gratuito; el SQL es compatible con Supabase).
- Guardrails deterministas en nodos Code (costo cero, auditables) + guardrail de salida.
- Calendario: Google Sheet publicado como CSV (evita OAuth en la VM) con respaldo desde la BD.
- Sub-workflows con IDs fijos para que el router funcione al importar en cualquier instancia.

**Problemas encontrados**
- `initdb` de Postgres falla si la ruta contiene tildes → los entornos de prueba se crearon fuera de la carpeta del proyecto.
- Al importar workflows con *tags* n8n intenta crear la etiqueta dos veces (`UNIQUE constraint tag_entity.name`) → se quitaron los tags.
- `Execute Workflow` v1.1 usa selector de workflow (no string) → corregido en el generador.
- n8n 2.x no deja publicar el router si los sub-workflows no están publicados → `n8n-import.sh` los publica en orden.
- Las funciones decoradas con `@mcp.tool` dejan de ser invocables entre sí → la lógica compartida usa `_query` directamente.

**Siguiente:** despliegue en AWS por Santiago (ver `docs/CONTINUACION.md`).

---

## 2026-11-18 · Equipo UNAB con Codex — Despliegue y verificación

- Se confirmó en la EC2 la cuenta existente de n8n y los cinco contenedores. Se importaron seis workflows y se publicaron el router y los cuatro sub-workflows.
- Se configuró B.AI en `https://api.b.ai/v1` con `qwen3.8-flash`. La API rechazó la ruta de embeddings, por lo que se habilitó un modelo multilingüe en CPU y se publicaron 20 fragmentos en pgvector.
- Se verificaron las cuatro intenciones, dos bloqueos, la memoria de agentes y una consulta MCP por HTTPS desde Claude Code. El calendario funcionó con el respaldo de PostgreSQL.
- Se agregó a la app la entrada enmascarada de la clave del webhook para distribuir el APK de depuración sin incrustar una llave.
- Una consulta móvil de historial superó los 90 segundos. Se desactivó el razonamiento extendido de Qwen en los nodos de chat, se volvió a pasar el smoke test y el emulador recibió la respuesta de historial.
- Las pruebas y pendientes de acceso a consolas están en [evidencias](docs/evidencias/README.md).

---

## 2026-11-19 · Santiago — Frontend UNAB, auditoría de requisitos y corrección del RAG

- Interfaz web de chat en `/app/` (Caddy) y rediseño de la app Android con identidad UNAB (naranja `#FF9D00`, morado `#8600DD`, logo y favicon oficiales). Trabajo mecánico delegado a DeepSeek y revisado por Claude.
- Auditoría contra las diapositivas del profesor con las preguntas reales del enunciado: ruta y cursos, RAG, calendario, historial, noticias y guardrails responden. Latencias de 6 a 51 s (104 s en frío).
- **Problema:** insignia y recomendaciones respondían «no encontré información». Causa: n8n llamaba a `/v1/embeddings` con una clave desactualizada (401). **Solución:** `bash scripts/n8n-import.sh` para refrescar credenciales; el RAG vuelve a citar los documentos.
- Pendiente de cuentas externas: Google Sheet publicado para el calendario, capturas de AWS Academy y compilación de la app en Android Studio.

---

## 2026-11-19 · José — v2 "Asistente UNAB 360" (orquestación multiagente)

**Hecho**
- Contrato congelado primero ([docs/CONTRATOS-V2.md](docs/CONTRATOS-V2.md)) y DDL común (`04_v2_schema.sql`). Después, ocho frentes en paralelo, cada uno en su propio git worktree:
  - `servicios-api`: reservas, pagos Bold, QR, gráficas, visión, panel "Hoy", analítica.
  - Semilla v2: 5 carreras, 7 personas, Cosmos, TEMA, biblioteca y espacios.
  - MCP: 8 herramientas más.
  - Router n8n con visión y enriquecimiento, y workflow 06 de trámites.
  - Web y Android v2.
  - Scraper de 11 fuentes.
  - Modelo de riesgo.
  - Documentación: prompts, manual y pertinencia.
- Modelos: Claude Opus como líder (contratos, integración, despliegue, revisión), Claude Sonnet para código y documentación, Codex (GPT Sol 6.2) para los primeros borradores del API, Android y ML.
- Despliegue en la EC2 con `scripts/deploy-v2.sh`, sin borrar volúmenes. Antes se sacaron backups del proyecto y un `pg_dumpall` en `~/backups/`. Quedaron 15 pruebas de humo en verde, el RAG reindexado (26 fragmentos, incluido `tramites_unab.md`) y el riesgo puntuado para los 206 estudiantes.

**Problemas / decisiones**
- **Tarjetas y gráficas deterministas** (`/api/asistente/enriquecer`) en lugar de pedirle JSON al LLM: la demo no puede depender de que un modelo *flash* arme bien una orden de pago.
- **Visión:** `qwen3.8` no existe en B.AI. Se probaron 4 modelos con la foto del cartel de biblioteca y se eligió `qwen3.8-max` (5 s, buena transcripción). El QR se decodifica localmente con OpenCV: `https://catalogo.unab.edu.co/`.
- **Bold:**
  - El botón embebido (`data-render-mode="embedded"`) no tiene callbacks JS. El pago se confirma con el webhook (HMAC sobre el cuerpo en base64; llave vacía en modo pruebas) o consultando `payment-voucher`.
  - En pruebas Bold no envía el webhook solo.
  - Bold prohíbe iframes, así que la web navega a `pagar.html` y conserva la conversación en `sessionStorage`. Android usa un WebView propio.
- **ML:** se descartó usar tareas de TEMA y el corte 1 como variables, porque solo existen para el periodo actual y meterlas en el entrenamiento sería fuga o columnas vacías. La regla de parsimonia eligió la logística: empate técnico en CV y mejor desempeño en prueba.
- **Codex se quedó sin cuota a mitad de camino:** Sonnet retomó sus borradores. El del API resultó casi completo (el único bug fue la zona horaria, porque pgserver no trae tzdata). El de ML hubo que corregirlo y ejecutarlo.
- **EC2:** no era un clon de git (se despliega con `git archive`). El Caddyfile del servidor no tenía `email`, porque con `ACME_EMAIL` vacío Caddy no arranca; se quitó del repo. Caddy hay que recrearlo para que lea el Caddyfile nuevo. `n8n execute` por CLI choca con el puerto del task broker, así que se le pasa `N8N_RUNNERS_BROKER_PORT` aparte.

**Evidencias:** `docs/evidencias/v2/`, `docs/evidencias/ml/`, `analitica/riesgo_academico.ipynb`, salida de `scripts/smoke-test.sh`.

---

## 2026-11-20 · José Téllez — Videos, pago de Bold en Android y guía de recorrido
**Hecho**
- Videos entregados: [demo funcional (4:28)](https://youtu.be/iAiiowTgKYs) y [tráiler (1:10)](https://youtu.be/e0BDTLoeVEg). Se grabaron con Playwright (web) y con el emulador (Android) y se montaron en HyperFrames. Voz y música de ElevenLabs, a −14 LUFS. Producción en [docs/VIDEOS.md](docs/VIDEOS.md) y guiones en [docs/GUIONES-ELEVENLABS.md](docs/GUIONES-ELEVENLABS.md).
- Corregido el pago con Bold dentro de la app Android (`web/pagar.html`). APK 2.2 publicado en `web/descargas/`.
- [docs/GUIA-RECORRIDO.md](docs/GUIA-RECORRIDO.md): recorrido en vivo para la sustentación.

**Problemas / decisiones**
- **Bold en el WebView:** el checkout embebido cargaba (por CDP se vio el iframe y la API de Bold respondiendo 200) pero quedaba invisible. En el WebView de la app las unidades `vh`/`dvh` miden 0, y el modal de Bold usa `height: 100vh` dentro de un shadow root cerrado, así que no se puede corregir con CSS. Solución: si el UA trae `; wv)`, se usa `data-render-mode="redirect"`. Se verificó de punta a punta en el emulador: checkout, pago aprobado y regreso a `pagar.html`. No hace falta recompilar la app; el APK 2.2 solo sube la versión.
- **Voz de ElevenLabs:** salió sin las pausas largas, así que se cortó por palabras con una transcripción de Whisper en lugar de por silencios.

**Evidencias:** videos en YouTube (no listados); grabaciones crudas en `videos/raw/` (no versionadas).

---

<!-- Plantilla para nuevas entradas
## AAAA-MM-DD · Nombre — Título
**Hecho**
-
**Problemas / decisiones**
-
**Evidencias:** docs/evidencias/…
-->
