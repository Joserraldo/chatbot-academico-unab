#!/bin/bash
# v2: rol servicios_rw (servicios-api). Lee y escribe SOLO el esquema `servicios`;
# lee `academico` (incluido chat_log para la analítica). chatbot_ro (MCP) gana lectura de lo nuevo.
# Idempotente: se puede volver a ejecutar (scripts/migrate-v2.sh lo hace en la EC2).
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "${POSTGRES_DB:-unab}" <<-EOSQL
  DO \$\$
  BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'servicios_rw') THEN
      CREATE ROLE servicios_rw LOGIN PASSWORD '${SERVICIOS_DB_PASSWORD:-cambia_esto}';
    ELSE
      ALTER ROLE servicios_rw PASSWORD '${SERVICIOS_DB_PASSWORD:-cambia_esto}';
    END IF;
  END
  \$\$;
  GRANT USAGE ON SCHEMA academico, servicios TO servicios_rw, chatbot_ro;
  GRANT SELECT ON ALL TABLES IN SCHEMA academico TO servicios_rw, chatbot_ro;
  GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA servicios TO servicios_rw;
  GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA servicios TO servicios_rw;
  GRANT SELECT ON ALL TABLES IN SCHEMA servicios TO chatbot_ro;
EOSQL
