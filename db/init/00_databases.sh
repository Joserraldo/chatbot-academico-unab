#!/bin/bash
# Se ejecuta UNA sola vez, cuando el volumen de Postgres está vacío.
# Crea la base de n8n y el rol de solo lectura que usan el MCP server y n8n
# para consultar los datos académicos (principio de mínimo privilegio).
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  CREATE DATABASE n8n;
  CREATE EXTENSION IF NOT EXISTS vector;
  DO \$\$
  BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'chatbot_ro') THEN
      CREATE ROLE chatbot_ro LOGIN PASSWORD '${APP_DB_PASSWORD:-cambia_esto}';
    END IF;
  END
  \$\$;
EOSQL
