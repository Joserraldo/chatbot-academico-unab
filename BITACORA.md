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

<!-- Plantilla para nuevas entradas
## AAAA-MM-DD · Nombre — Título
**Hecho**
-
**Problemas / decisiones**
-
**Evidencias:** docs/evidencias/…
-->
