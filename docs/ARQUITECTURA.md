# Arquitectura

## 1. Vista general

Todo corre en **una sola VM** (EC2) con Docker Compose. El único servicio externo de cómputo pesado es el LLM, consumido por API.

| Servicio | Imagen / código | Puerto | Rol |
|---|---|---|---|
| `caddy` | `caddy:2.10-alpine` | 80, 443 (públicos) | TLS automático (Let's Encrypt) para el dominio DuckDNS; enruta `/mcp` al MCP y el resto a n8n |
| `n8n` | `n8nio/n8n:2.47.7` | 5678 (solo localhost) | Orquestación: webhook del chat, guardrails, ruteo, agentes, RAG, ingesta, scraping |
| `postgres` | `pgvector/pgvector:0.8.7-pg16` | interno | BD académica sintética (`academico`), vectores (`public.rag_documentos`), memoria del chat, BD interna de n8n |
| `mcp-server` | `mcp-server/` (Python, FastMCP) | 9000 (público, con token) | Herramientas relacionales de solo lectura para agentes (n8n, Claude, OpenAI) |
| `scraper` | `scraper/` (Python) | — | Cada 6 h lee el RSS de unab.edu.co y hace upsert en `academico.noticia` |

> Las diapositivas mencionan **Supabase**. El esquema es 100 % compatible: para usar Supabase en vez del Postgres local se ejecutan `01_schema.sql`, `02_views.sql` y `03_seed.sql` en el SQL Editor de Supabase (con la extensión `vector` activada y el rol `chatbot_ro` creado a mano) y se cambian los hosts en `.env`/credenciales. Se eligió Postgres local por defecto porque no depende de cuentas externas, no tiene límites de pausa del plan gratuito y es más fácil de replicar.

## 2. Flujo de una pregunta

```mermaid
sequenceDiagram
  participant App as App Android
  participant R as n8n · 00 Router
  participant LLM as LLM (b.ai)
  participant Sub as Sub-workflow 01-04
  participant MCP as MCP server
  participant DB as PostgreSQL
  App->>R: POST /webhook/chat {sessionId, codigo, mensaje}
  R->>R: Guardrail de entrada (reglas deterministas)
  alt bloqueado
    R-->>App: mensaje seguro (intencion=bloqueado)
  else permitido
    R->>LLM: Text Classifier → intención
    R->>Sub: Execute Workflow (según intención)
    Sub->>DB: memoria del chat (sessionId)
    opt 01 General
      Sub->>LLM: embedding de la pregunta
      Sub->>DB: top-4 fragmentos (pgvector, coseno)
    end
    opt 03 Historial
      Sub->>MCP: tools/call estado_academico, proyeccion_semestres…
      MCP->>DB: SELECT sobre vistas (rol chatbot_ro)
    end
    Sub->>LLM: generar respuesta con el contexto
    Sub-->>R: {respuesta, fuentes, intencion}
    R->>R: Guardrail de salida
    R->>DB: INSERT chat_log
    R-->>App: {respuesta, intencion, fuentes}
  end
```

## 3. Workflows de n8n

| ID | Nombre | Disparador | Pipeline |
|---|---|---|---|
| `wfRouterChatUNAB` | 00 Router chat | Webhook POST `/webhook/chat` | Guardrail entrada → IF → Text Classifier → Execute Workflow → Guardrail salida → Log → Respond |
| `wf01GeneralRAG00` | 01 Consulta general | Execute Workflow | AI Agent + memoria + herramienta PGVector (retrieve-as-tool) |
| `wf02Calendario00` | 02 Calendario | Execute Workflow | HTTP (Google Sheet CSV) → Code → LLM Chain |
| `wf03CursosMCP000` | 03 Cursos realizados | Execute Workflow | AI Agent + memoria + MCP Client Tool |
| `wf04Noticias0000` | 04 Noticias | Schedule 6 h **y** Execute Workflow | A: RSS → clasificar → upsert · B: SELECT → LLM Chain |
| `wf05IngestaRAG00` | 05 Ingesta RAG | Manual | DROP → leer .md → extraer → chunking → embeddings → PGVector |

Los JSON se generan con `n8n/build_workflows.py` (IDs fijos para que el router encuentre los sub-workflows al importar). Las credenciales también tienen IDs fijos y se crean desde `.env` con `scripts/render_n8n_credentials.py`.

## 4. Decisiones de diseño

| Decisión | Alternativa | Por qué |
|---|---|---|
| LLM por API (OpenAI-compatible) | Modelo local (Ollama) | Las instancias de AWS Academy son pequeñas y sin GPU; un modelo local de 7B no cabe en 2-4 GB. Con API el proveedor se cambia solo con `.env` |
| Guardrails deterministas (Code) | Nodo Guardrails con LLM | Costo cero, latencia cero, comportamiento auditable y fácil de explicar; los casos están en `chat_log` |
| Sub-workflows por intención | Un único agente con todas las herramientas | Cumple el diseño de 4 workflows de la diapositiva 11, cada flujo usa el mínimo de tokens y se prueba por separado |
| MCP con rol de solo lectura | Que el agente escriba SQL libre | Evita inyección SQL y fuga de datos: el agente solo puede llamar herramientas parametrizadas que validan el código del estudiante |
| Vistas analíticas | Consultas con JOINs en las herramientas | "Una fila = una respuesta": menos tokens, menos errores del LLM, reglas de negocio (promedio, proyección, insignia) en un solo lugar |
| Calendario como CSV publicado | Nodo Google Sheets con OAuth | No requiere configurar OAuth de Google en la VM; si no hay Sheet, cae al respaldo `/calendario.csv` del MCP |
| Caddy | Nginx + certbot | HTTPS automático con 6 líneas de configuración |
| Postgres local | Supabase | Ver nota del §1 |

## 5. Seguridad

- Solo 80/443/9000 (y 22 limitado a la IP del equipo) abiertos en el Security Group; n8n y Postgres no se exponen.
- Webhook protegido con header `X-Chatbot-Key`; MCP protegido con bearer token.
- `.env` y las credenciales renderizadas nunca se versionan; `N8N_ENCRYPTION_KEY` cifra las credenciales en la BD de n8n.
- El MCP usa el rol `chatbot_ro` (SELECT en `academico`, INSERT solo en `chat_log`).
- Limitación conocida: la `CHATBOT_KEY` va embebida en el APK (aceptable para un prototipo académico; en producción se usaría login institucional/OAuth y un token por estudiante).
