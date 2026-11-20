#!/usr/bin/env bash
# Deja las personas demo como "recién llegadas" antes de una sustentación:
# borra órdenes de pago, eventos de Bold y reservas creadas en pruebas, y la memoria del chat.
# No toca datos académicos (solo el esquema servicios y n8n_chat_histories).
# Uso (en la EC2, directorio del proyecto):  bash scripts/reset-demo.sh
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d unab <<'SQL'
BEGIN;
DELETE FROM servicios.bold_evento;
DELETE FROM servicios.reserva;
DELETE FROM servicios.pago_orden;
DELETE FROM public.n8n_chat_histories WHERE to_regclass('public.n8n_chat_histories') IS NOT NULL;
COMMIT;
SELECT 'listo: ' || (SELECT count(*) FROM servicios.pago_orden) || ' órdenes, '
       || (SELECT count(*) FROM servicios.reserva) || ' reservas' AS estado;
SQL
