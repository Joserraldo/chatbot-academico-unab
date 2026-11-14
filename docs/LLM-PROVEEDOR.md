# Proveedor de LLM (b.ai / qwen-flash) — cómo "dropear" las APIs

Todo el sistema habla con el LLM por la **API compatible con OpenAI** (`POST {BASE_URL}/chat/completions` y `POST {BASE_URL}/embeddings`). No hay código atado a un proveedor: cambiar de b.ai a OpenAI, DashScope (Qwen), Groq u OpenRouter es solo cambiar `.env`.

## 1. Dónde van las llaves

Solo en el archivo `.env` de la VM (y en tu `.env` local si pruebas en tu PC). **Nunca** en el código, en un commit, en un issue ni pegadas en un chat. Si una llave se filtra, se rota en el panel del proveedor.

```
LLM_BASE_URL=https://<endpoint>/v1      # termina en /v1 (sin /chat/completions)
LLM_API_KEY=...
LLM_MODEL=qwen-flash                    # nombre exacto del modelo en el proveedor
EMBED_BASE_URL=https://<endpoint>/v1
EMBED_API_KEY=...
EMBED_MODEL=text-embedding-v3
```

`scripts/n8n-import.sh` convierte esas variables en credenciales cifradas de n8n (tipo *OpenAI*, con *Base URL* personalizada). El MCP server lee `EMBED_*` para la herramienta `buscar_documentos`.

## 2. Verificar que la llave y el endpoint sirven (antes de desplegar)

Chat (Git Bash, reemplaza los valores):
```bash
curl -s "$LLM_BASE_URL/chat/completions" -H "Authorization: Bearer $LLM_API_KEY" -H "Content-Type: application/json" -d '{"model":"qwen-flash","messages":[{"role":"user","content":"Hola, responde solo OK"}]}'
```
Embeddings:
```bash
curl -s "$EMBED_BASE_URL/embeddings" -H "Authorization: Bearer $EMBED_API_KEY" -H "Content-Type: application/json" -d '{"model":"text-embedding-v3","input":"prueba"}' | head -c 300
```
Si el primero responde con `choices[0].message.content` y el segundo con `data[0].embedding`, el proveedor es compatible.

## 3. Si el proveedor no ofrece embeddings

El RAG necesita un modelo de embeddings. Opciones, en orden de preferencia:
1. Embeddings del mismo proveedor (si tiene `/v1/embeddings`).
2. DashScope internacional (Qwen) `text-embedding-v3`: `EMBED_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1`.
3. OpenAI `text-embedding-3-small`.

Importante: **todos los vectores deben venir del mismo modelo**. Si cambias `EMBED_MODEL`, vuelve a ejecutar el workflow *05 Ingesta RAG* (borra y recrea la tabla).

## 4. Requisitos del modelo de chat

- Debe soportar **tool calling / function calling** (lo usan los AI Agent de los workflows 01 y 03). Qwen-flash lo soporta.
- Temperatura 0.2 (respuestas) y 0 (clasificador de intención).
- Costo por pregunta: 2 a 4 llamadas (clasificador + agente con 1-3 herramientas).
