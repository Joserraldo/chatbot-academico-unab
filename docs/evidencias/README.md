# Evidencias del despliegue

Guardar aquí las capturas (PNG, sin datos sensibles: **tapar tokens, llaves, contraseñas y la IP si se prefiere**). Al terminar, marcar la tabla y enlazar las más importantes desde el README principal.

| # | Archivo | Qué debe verse | ✔ |
|---|---|---|---|
| 01 | `01-learner-lab.png` | Learner Lab iniciado (punto verde) | |
| 02 | `02-security-group.png` | Reglas 22 (My IP), 80, 443, 9000 | |
| 03 | `03-instancia-running.png` | Instancia `chatbot-unab` en *running*, tipo t3.small/medium | |
| 04 | `04-elastic-ip.png` | Elastic IP asociada a la instancia | |
| 05 | `05-duckdns.png` | Subdominio apuntando a la Elastic IP | |
| 06 | `06-docker-compose-ps.png` | 5 contenedores *running/healthy* | |
| 07 | `07-n8n-login-https.png` | n8n en `https://<dominio>` con candado | |
| 08 | `08-ingesta-rag.png` | Ejecución exitosa de 05 Ingesta (n.º de chunks) | |
| 09 | `09-workflows-activos.png` | Lista de workflows publicados | |
| 10-15 | `10-wf00-router.png` … `15-wf05-ingesta.png` | Lienzo de cada workflow | |
| 16 | `16-google-sheet.png` | Calendario en Google Sheets publicado | |
| 17 | `17-smoke-test.png` | Salida de `scripts/smoke-test.sh` | |
| 18 | `18-ejecuciones.png` | Ejecuciones de las 4 intenciones | |
| 19 | `19-chat-log-guardrails.png` | `chat_log` con casos bloqueados | |
| 20 | `20-app-*.png` | App: inicio, chat con cada intención, error/reintentar | |
| 21 | `21-cliente-mcp-claude.png` | Claude usando una herramienta del MCP | |
