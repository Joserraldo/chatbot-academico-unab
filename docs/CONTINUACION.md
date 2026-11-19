# Despliegue y cierre de la entrega

Al 18 de noviembre de 2026 la demo está operativa en [chatbotunab.duckdns.org](https://chatbotunab.duckdns.org). El [registro de verificación](evidencias/VERIFICACION-EC2.md) documenta las pruebas contra EC2. La cuenta de propietario de n8n ya existía y se conservó.

## Qué ya está probado (y cómo)

| Pieza | Prueba hecha | Resultado |
|---|---|---|
| Esquema + vistas + datos sintéticos | Cargados en PostgreSQL 16 embebido | 200 estudiantes, 6.168 registros de historial, vistas correctas para `U00000001` |
| MCP server | Cliente FastMCP llamando las 10 herramientas con el rol `chatbot_ro`; `initialize` por HTTP | OK; sin token → 401; código inválido → error de validación |
| Scraper | `scraper.py --once` contra el RSS real de unab.edu.co | 10 noticias insertadas y clasificadas |
| Workflows n8n | Importados en n8n 2.47.7 local; tipos/versiones/parámetros validados contra el catálogo de nodos; publicados por CLI | OK |
| Webhook + guardrails | `POST /webhook/chat` con inyección de prompt y con código ajeno | Bloqueados, respuesta JSON correcta, filas en `chat_log`; sin `X-Chatbot-Key` → 403 |
| App Android | `./gradlew assembleDebug` | Compila (APK debug) |

## Despliegue verificado

- B.AI configurado con `qwen3.8-flash` y llamadas de herramientas comprobadas. Los embeddings multilingües se generan en la EC2.
- Router y cuatro ramas publicados y probados por HTTPS. La ingesta indexó 20 fragmentos de cinco documentos en pgvector.
- Claude Code conectó con el MCP por HTTPS y consultó `estado_academico` para el estudiante demo.

La configuración y la rotación de la llave están en [LLM-PROVEEDOR.md](LLM-PROVEEDOR.md).

## Checklist de entrega

- [x] EC2 operativa, DuckDNS resolviendo y HTTPS verificado. La asociación de Elastic IP y las reglas exactas del Security Group quedan por confirmar en la consola de AWS.
- [x] `.env` y cinco servicios de Docker Compose operativos.
- [x] Verificar chat y herramientas de B.AI, y proporcionar embeddings locales.
- [x] `bash scripts/n8n-import.sh` y ejecutar **05 Ingesta RAG**.
- [ ] Publicar el calendario sintético en Google Sheets. El respaldo de PostgreSQL está activo. Se requiere una sesión de Google con permiso para publicar el CSV.
- [x] `bash scripts/smoke-test.sh` con cuatro intenciones y dos bloqueos.
- [x] Compilar el APK de depuración sin clave incrustada y probarlo en el emulador contra la EC2. La clave del webhook se ingresa en la app.
- [x] Conectar Claude Code al MCP y hacer una consulta al estudiante demo.
- [ ] Capturas de la consola de AWS, Google Sheets y del editor autenticado de n8n. Las pruebas por CLI y HTTPS están registradas en [evidencias](evidencias/README.md).
- [x] Actualizar README con el dominio y las evidencias.
- [x] Registrar el despliegue y sus decisiones en la [bitácora](../BITACORA.md).
- [x] Renderizar el video de demostración con narración y una grabación real del emulador. Artefacto local `android/app/build/outputs/demo-unab.mp4`.

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
