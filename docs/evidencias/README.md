# Evidencias del despliegue

Guardar aquí las capturas (PNG, sin datos sensibles: **tapar tokens, llaves, contraseñas y la IP si se prefiere**). Al terminar, marcar la tabla y enlazar las más importantes desde el README principal.

El [registro de verificación de EC2](VERIFICACION-EC2.md) recoge la evidencia obtenida por SSH, HTTPS, n8n CLI, PostgreSQL y Claude Code. Las capturas del Learner Lab, de AWS, de DuckDNS y del editor n8n requieren acceso a sus respectivas cuentas. El calendario demo está servido desde PostgreSQL hasta que exista un Google Sheet publicado.

El video narrado de la demo está en `android/app/build/outputs/demo-unab.mp4` en la copia de trabajo. Incluye calendario, historial y un bloqueo desde el emulador.

| # | Archivo | Qué debe verse | ✔ |
|---|---|---|---|
| 01 | `01-learner-lab.png` | Learner Lab iniciado (punto verde) | |
| 02 | `02-security-group.png` | Reglas 22 (My IP), 80, 443, 9000 | |
| 03 | `03-instancia-running.png` | Instancia `chatbot-unab` en *running*, tipo t3.small/medium | |
| 04 | `04-elastic-ip.png` | Elastic IP asociada a la instancia | |
| 05 | `05-duckdns.png` | Subdominio apuntando a la Elastic IP | |
| 06 | `06-docker-compose-ps.png` | 5 contenedores *running/healthy* | Verificado por CLI |
| 07 | `07-n8n-login-https.png` | n8n en `https://<dominio>` con candado | HTTPS verificado |
| 08 | `08-ingesta-rag.png` | Ejecución exitosa de 05 Ingesta (n.º de chunks) | Verificado por CLI y SQL |
| 09 | `09-workflows-activos.png` | Lista de workflows publicados | Verificado por SQL |
| 10-15 | `10-wf00-router.png` … `15-wf05-ingesta.png` | Lienzo de cada workflow | |
| 16 | `16-google-sheet.png` | Calendario en Google Sheets publicado | |
| 17 | `17-smoke-test.png` | Salida de `scripts/smoke-test.sh` | Ejecutado con éxito |
| 18 | `18-ejecuciones.png` | Ejecuciones de las 4 intenciones | Verificado por SQL |
| 19 | `19-chat-log-guardrails.png` | `chat_log` con casos bloqueados | Verificado por SQL |
| 20 | `20-app-*.png` | App: inicio, chat y error/reintentar | [Inicio](20-app-inicio.png) · [General](20-app-general.png) · [Calendario](20-app-calendario.png) · [Historial](20-app-historial.png) · [Noticias](20-app-noticias.png) · [Bloqueo](20-app-bloqueado.png) · [Error](20-app-error.png) |
| 21 | `21-cliente-mcp-claude.png` | Claude usando una herramienta del MCP | Verificado en Claude Code CLI |
