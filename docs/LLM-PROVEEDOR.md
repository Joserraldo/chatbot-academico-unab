# B.AI para chat y embeddings multilingües en la EC2

## Configurar o rotar la llave de B.AI

En la EC2, desde el directorio del proyecto, abre el archivo de configuración.

```bash
cd ~/chatbot-academico-unab
chmod 600 .env
nano .env
```

Guarda estos valores con la llave de tu cuenta. `qwen3.8-flash` figura en el catálogo de la credencial probada y se verificó con llamadas de herramientas.

```dotenv
LLM_BASE_URL=https://api.b.ai/v1
LLM_API_KEY=<llave de B.AI>
LLM_MODEL=qwen3.8-flash
```

Si cambias el modelo, vuelve a crear el contenedor n8n para que lea `LLM_MODEL`. La importación actualiza las credenciales cifradas y publica las versiones de los workflows que están en el repositorio.

```bash
docker compose up -d n8n
bash scripts/n8n-import.sh
bash scripts/smoke-test.sh
```

Para consultar los modelos desde la VM con la llave ya guardada, usa el siguiente comando. La salida contiene los IDs de modelos.

```bash
python3 - <<'PY'
import json
from pathlib import Path
from urllib.request import Request, urlopen

lines = Path('.env').read_text().splitlines()
key = next(line.split('=', 1)[1].strip() for line in lines if line.startswith('LLM_API_KEY='))
request = Request('https://api.b.ai/v1/models', headers={'Authorization': 'Bearer ' + key})
with urlopen(request, timeout=20) as response:
    print('\n'.join(model['id'] for model in json.load(response)['data']))
PY
```

Referencia de B.AI para [modelos y Chat Completions](https://docs.b.ai/llmservice/api/).

## Embeddings del RAG

B.AI rechazó `/v1/embeddings` durante la verificación. En el despliegue, FastEmbed genera los vectores de 384 dimensiones en CPU y n8n persiste los fragmentos en pgvector. El primer uso descarga el modelo y lo guarda en el volumen `embedding_models`.

```dotenv
EMBED_BASE_URL=http://mcp-server:9000/v1
EMBED_API_KEY=<secreto independiente generado con openssl rand -hex 24>
EMBED_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

Puedes configurar otro servicio compatible con `POST /embeddings` mediante `EMBED_*`. Después de cambiar de modelo o actualizar el corpus, aplica el entorno con `docker compose up -d --build mcp-server n8n`, reimporta y ejecuta **05 Ingesta RAG**. Las consultas y la ingesta deben usar el mismo modelo. El workflow publica el nuevo índice cuando termina de insertar los fragmentos.
