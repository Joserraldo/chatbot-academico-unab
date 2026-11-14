#!/usr/bin/env bash
# Actualiza el registro DuckDNS con la IP pública actual de la instancia.
# Con Elastic IP basta correrlo una vez; sin Elastic IP, déjalo en cron (la IP cambia al reiniciar el lab):
#   crontab -e   ->   */5 * * * * /home/ubuntu/chatbot-academico-unab/scripts/duckdns-update.sh >/dev/null 2>&1
set -euo pipefail
cd "$(dirname "$0")/.."
SUB=$(grep ^DUCKDNS_SUBDOMAIN= .env | cut -d= -f2)
TOKEN=$(grep ^DUCKDNS_TOKEN= .env | cut -d= -f2)
# ip vacío = DuckDNS usa la IP de origen de la petición (la pública de la EC2)
RES=$(curl -fsS "https://www.duckdns.org/update?domains=${SUB}&token=${TOKEN}&ip=")
echo "$(date -Is) duckdns ${SUB}: ${RES}"
[ "$RES" = "OK" ]
