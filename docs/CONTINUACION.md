# Continuación del proyecto — handoff a Santiago Cabezas

Estado al 13-nov-2026 (José): **todo el código está hecho y probado en local**. Falta desplegar en AWS, conectar el LLM real, tomar evidencias y grabar el video.

## Qué ya está probado (y cómo)

| Pieza | Prueba hecha | Resultado |
|---|---|---|
| Esquema + vistas + datos sintéticos | Cargados en PostgreSQL 16 embebido | 200 estudiantes, 6.168 registros de historial, vistas correctas para `U00000001` |
| MCP server | Cliente FastMCP llamando las 10 herramientas con el rol `chatbot_ro`; `initialize` por HTTP | OK; sin token → 401; código inválido → error de validación |
| Scraper | `scraper.py --once` contra el RSS real de unab.edu.co | 10 noticias insertadas y clasificadas |
| Workflows n8n | Importados en n8n 2.47.7 local; tipos/versiones/parámetros validados contra el catálogo de nodos; publicados por CLI | OK |
| Webhook + guardrails | `POST /webhook/chat` con inyección de prompt y con código ajeno | Bloqueados, respuesta JSON correcta, filas en `chat_log`; sin `X-Chatbot-Key` → 403 |
| App Android | `./gradlew assembleDebug` | Compila (APK debug) |

## Qué NO se ha probado (no había llave del LLM en el PC)

- Las ramas con LLM: clasificador de intención, agentes 01/03, cadenas 02/04.
- La ingesta RAG (necesita el endpoint de embeddings).
- La app contra el servidor real.

Por eso lo primero en la VM, después de llenar `.env`, es correr las verificaciones de [LLM-PROVEEDOR.md](LLM-PROVEEDOR.md) §2.

## Checklist para Santiago

- [ ] Aceptar la invitación al repo y clonar.
- [ ] Crear la EC2, Security Group, Elastic IP y DuckDNS — [DESPLIEGUE-AWS.md](DESPLIEGUE-AWS.md) §2-§4.
- [ ] `bootstrap-ec2.sh`, `.env`, `docker compose up -d --build` — §5-§7.
- [ ] Verificar la API de b.ai con `curl` (chat y embeddings).
- [ ] `bash scripts/n8n-import.sh` y ejecutar **05 Ingesta RAG** — §8.
- [ ] Google Sheet del calendario publicado como CSV — §9.
- [ ] `bash scripts/smoke-test.sh` (las 4 intenciones deben responder) — §10.
- [ ] Compilar la app con `chatbot.baseUrl=https://<DOMAIN>` y `chatbot.key=<CHATBOT_KEY>` y probarla en el celular/emulador — `android/README.md`.
- [ ] Conectar Claude Code/Desktop al MCP (README §6).
- [ ] Tomar todas las capturas de [evidencias/README.md](evidencias/README.md) y llenar la tabla de ese archivo.
- [ ] Actualizar el README: dominio real en la tabla de estado y enlace al video.
- [ ] Anotar en [../BITACORA.md](../BITACORA.md) cada sesión de trabajo (fecha, quién, qué, problemas).
- [ ] Grabar el video demostración (guion abajo).

## Si algo falla en un nodo de n8n

1. Ver la ejecución fallida en *Executions* (muestra el nodo y el error).
2. Errores típicos: credencial sin seleccionar → abrir el nodo y elegir la credencial; modelo inexistente → revisar `LLM_MODEL`; el modelo no soporta tools → usar otro modelo del proveedor.
3. Si se arregla editando en la UI, **exportar** el workflow (⋯ → Download) y reemplazar el JSON en `n8n/workflows/` (y si se puede, reflejar el cambio en `n8n/build_workflows.py`). Así el repo sigue siendo replicable.

## Guion sugerido del video (5-7 min)

1. Arquitectura (diagrama del README) y criterios cubiertos — 45 s.
2. AWS: instancia, Security Group (puerto 9000), Elastic IP, DuckDNS, `docker compose ps` — 1 min.
3. n8n: router (guardrails + clasificador) y los 5 workflows; ejecutar la ingesta RAG — 1,5 min.
4. App Android con el estudiante `U00000001`: las 6 sugerencias rápidas (avance, competencias digitales, inscripciones, insignia, novedades, semestres que faltan) — 2 min.
5. Guardrails: intentar ver las notas de `U00000002` y una inyección de prompt; mostrar `chat_log` — 45 s.
6. Cliente MCP: Claude usando las herramientas del servidor — 45 s.
