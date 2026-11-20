#!/usr/bin/env bash
# Aplica la v2 sobre una BD YA existente (la EC2), sin borrar volúmenes ni tocar n8n.
# Uso (en el directorio del proyecto):  bash scripts/migrate-v2.sh
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a
: "${SERVICIOS_DB_PASSWORD:?Falta SERVICIOS_DB_PASSWORD en .env (openssl rand -hex 24)}"

psql_run() { docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d unab "$@"; }

echo "==> 04 esquema v2";   psql_run < db/init/04_v2_schema.sql
echo "==> 05 semilla v2";   psql_run < db/init/05_v2_seed.sql
if [[ -f db/init/07_v2_riesgo.sql ]]; then echo "==> 07 riesgo (modelo ML)"; psql_run < db/init/07_v2_riesgo.sql; fi
echo "==> 06 roles v2"
docker compose exec -T -e SERVICIOS_DB_PASSWORD="$SERVICIOS_DB_PASSWORD" -e POSTGRES_DB=unab postgres \
  bash < db/init/06_v2_roles.sh
echo "==> listo. Verificación rápida:"
psql_run -c "SELECT count(*) AS personas FROM academico.persona_demo;" \
         -c "SELECT count(*) AS espacios FROM servicios.espacio;"
