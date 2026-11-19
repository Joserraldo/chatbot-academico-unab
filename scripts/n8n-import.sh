#!/usr/bin/env bash
# Importa credenciales y workflows en el contenedor de n8n y los publica.
# Idempotente: reimportar sobrescribe por ID.
# Uso (desde la raíz del repo, con el stack arriba):  bash scripts/n8n-import.sh
set -euo pipefail
cd "$(dirname "$0")/.."

trap 'rm -f n8n/.credentials.json' EXIT
umask 077
python3 scripts/render_n8n_credentials.py
docker compose exec -T n8n n8n import:credentials --input=/bootstrap/.credentials.json
rm -f n8n/.credentials.json   # no dejar secretos en texto plano en disco

docker compose exec -T n8n n8n import:workflow --separate --input=/bootstrap/workflows/

# n8n 2.x exige publicar primero los sub-workflows y después el router que los llama.
for id in wf01GeneralRAG00 wf02Calendario00 wf03CursosMCP000 wf04Noticias0000 wfRouterChatUNAB; do
  docker compose exec -T n8n n8n publish:workflow --id="$id"
done
docker compose restart n8n

for attempt in {1..30}; do
  status=$(curl -s --max-time 2 -o /dev/null -w '%{http_code}' \
    -H 'Content-Type: application/json' -d '{}' http://127.0.0.1:5678/webhook/chat || true)
  if [[ "$status" == 403 ]]; then
    break
  fi
  sleep 2
done
if [[ "$status" != 403 ]]; then
  echo "n8n no habilitó el webhook. Revisa: docker compose logs n8n" >&2
  exit 1
fi

echo
echo "Listo. Entra a https://$(grep ^DOMAIN= .env | cut -d= -f2) y abre '05 Ingesta RAG' -> 'Execute workflow' (crea los embeddings)."
