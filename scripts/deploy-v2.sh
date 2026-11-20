#!/usr/bin/env bash
# Despliegue de la v2 sobre una EC2 que ya corre la v1. Idempotente.
# Uso (en el directorio del proyecto, con el código v2 ya copiado):  bash scripts/deploy-v2.sh
# No borra volúmenes: n8n, credenciales y datos v1 se conservan.
set -euo pipefail
cd "$(dirname "$0")/.."

# 1) Variables nuevas en .env (solo si faltan)
add_env() { grep -q "^$1=" .env || echo "$1=$2" >> .env; }
add_env SERVICIOS_DB_PASSWORD "$(openssl rand -hex 24)"
add_env VISION_MODEL qwen3.8
add_env BOLD_MODO pruebas
add_env PAGOS_PERMITIR_SIMULADO true
add_env BOLD_WEBHOOK_SECRET ""
chmod 600 .env

# 2) Base de datos: esquema, semilla, riesgo y roles v2
docker compose up -d postgres
bash scripts/migrate-v2.sh

# 3) Servicios (construye servicios-api, MCP y scraper nuevos; recrea n8n y caddy con el entorno nuevo)
docker compose up -d --build
docker compose ps --format 'table {{.Name}}\t{{.Status}}'

# 4) Workflows (router v2 + wf06) y re-ingesta del RAG con el documento de trámites
bash scripts/n8n-import.sh
docker compose exec -T n8n n8n execute --id=wf05IngestaRAG00 >/dev/null && echo "Ingesta RAG ejecutada"

# 5) Pruebas de humo
bash scripts/smoke-test.sh
