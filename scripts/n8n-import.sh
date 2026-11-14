#!/usr/bin/env bash
# Importa credenciales y workflows en el contenedor de n8n y los publica.
# Idempotente: reimportar sobrescribe por ID.
# Uso (desde la raíz del repo, con el stack arriba):  bash scripts/n8n-import.sh
set -euo pipefail
cd "$(dirname "$0")/.."

python3 scripts/render_n8n_credentials.py
docker compose exec -T n8n n8n import:credentials --input=/bootstrap/.credentials.json
rm -f n8n/.credentials.json   # no dejar secretos en texto plano en disco

docker compose exec -T n8n n8n import:workflow --separate --input=/bootstrap/workflows/

# n8n 2.x exige publicar primero los sub-workflows y después el router que los llama.
for id in wf01GeneralRAG00 wf02Calendario00 wf03CursosMCP000 wf04Noticias0000 wfRouterChatUNAB; do
  docker compose exec -T n8n n8n update:workflow --id="$id" --active=true
done
docker compose restart n8n

echo
echo "Listo. Entra a https://$(grep ^DOMAIN= .env | cut -d= -f2) y abre '05 Ingesta RAG' -> 'Execute workflow' (crea los embeddings)."
