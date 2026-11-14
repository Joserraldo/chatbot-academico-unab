# Despliegue en AWS (AWS Academy Learner Lab) + DuckDNS

Guía para replicar el despliegue desde cero. Cada paso marcado con 📸 requiere una captura en `docs/evidencias/` (nombres sugeridos en [evidencias/README.md](evidencias/README.md)).

## 1. Tamaño de instancia

El LLM corre en el proveedor (b.ai), no en la VM. La VM solo necesita RAM para n8n + Postgres.

| Tipo | vCPU / RAM | ¿Sirve? |
|---|---|---|
| t3.micro / t2.micro | 2 / 1 GB | ❌ n8n se queda sin memoria |
| **t3.small** | 2 / 2 GB | ✅ con el swap de 2 GB que crea `bootstrap-ec2.sh` |
| **t3.medium** | 2 / 4 GB | ✅ recomendado si el lab lo permite (más holgura para compilar las imágenes) |

Disco: 25-30 GB gp3 (las imágenes de Docker ocupan ~3 GB). Sistema: **Ubuntu Server 24.04 LTS**.

Particularidades de AWS Academy:
- La sesión del lab dura ~4 h; al terminar, la instancia **se detiene** (no se borra). Al volver a iniciar el lab hay que encenderla; como todos los contenedores tienen `restart: unless-stopped`, el stack arranca solo.
- Sin Elastic IP la IP pública cambia en cada arranque → por eso se usa **Elastic IP** (y además `duckdns-update.sh` en cron como respaldo).
- El presupuesto del lab es limitado: una Elastic IP asociada a una instancia detenida y el almacenamiento consumen crédito. Liberar todo al terminar el curso.

## 2. Crear la instancia

1. Learner Lab → **Start Lab** → cuando el punto esté verde, **AWS** → consola. 📸 `01-learner-lab.png`
2. EC2 → **Launch instance**: nombre `chatbot-unab`, Ubuntu 24.04, `t3.small` o `t3.medium`, key pair `vockey` (o crear una nueva y descargar el `.pem`), 30 GB gp3.
3. **Security Group** `chatbot-unab-sg` — reglas de entrada: 📸 `02-security-group.png`

| Tipo | Puerto | Origen | Para qué |
|---|---|---|---|
| SSH | 22 | My IP | Administración |
| HTTP | 80 | 0.0.0.0/0 | Reto ACME de Let's Encrypt + redirección |
| HTTPS | 443 | 0.0.0.0/0 | n8n, webhook del chat, `/mcp` |
| Custom TCP | 9000 | 0.0.0.0/0 | Servidor MCP Streamable HTTP (requisito del curso) |

4. Launch. 📸 `03-instancia-running.png`

## 3. Elastic IP

EC2 → **Elastic IPs** → *Allocate Elastic IP address* → *Actions → Associate* → instancia `chatbot-unab`. 📸 `04-elastic-ip.png`

## 4. DuckDNS

1. Entrar a https://www.duckdns.org con GitHub/Google, crear el subdominio (ej. `chatbot-unab`) y poner la Elastic IP. 📸 `05-duckdns.png`
2. Copiar el **token** (va en `.env` como `DUCKDNS_TOKEN`; nunca en el repo).

## 5. Preparar la VM

Desde tu PC (Git Bash), con la llave descargada del lab:
```bash
chmod 400 ~/Downloads/labsuser.pem
```
```bash
ssh -i ~/Downloads/labsuser.pem ubuntu@<ELASTIC_IP>
```
En la VM:
```bash
git clone https://github.com/Joserraldo/chatbot-academico-unab.git
```
```bash
cd chatbot-academico-unab && bash scripts/bootstrap-ec2.sh
```
Salir (`exit`) y volver a entrar por SSH (para que el grupo `docker` aplique).

## 6. Configurar `.env`

```bash
cd chatbot-academico-unab && cp .env.example .env
```
Generar secretos (correr 5 veces y pegar en `POSTGRES_PASSWORD`, `APP_DB_PASSWORD`, `N8N_ENCRYPTION_KEY`, `MCP_TOKEN`, `CHATBOT_KEY`):
```bash
openssl rand -hex 24
```
```bash
nano .env
```
Llenar `DOMAIN`, `ACME_EMAIL`, `DUCKDNS_*`, y las variables `LLM_*` / `EMBED_*` (ver [LLM-PROVEEDOR.md](LLM-PROVEEDOR.md)). Guardar una copia del `.env` en un lugar privado del equipo (gestor de contraseñas), **no** en GitHub ni en el chat.

```bash
bash scripts/duckdns-update.sh
```
Debe imprimir `OK`.

## 7. Levantar el stack

```bash
docker compose up -d --build
```
```bash
docker compose ps
```
📸 `06-docker-compose-ps.png` (todos `running`/`healthy`). La primera vez Caddy tarda ~1 min en obtener el certificado: `docker compose logs caddy | tail`.

## 8. n8n

1. Abrir `https://<DOMAIN>` → crear la cuenta owner. 📸 `07-n8n-login-https.png` (que se vea el candado)
2. Importar credenciales y workflows:
```bash
bash scripts/n8n-import.sh
```
3. En la UI: abrir **05 Ingesta RAG** → *Execute workflow*. 📸 `08-ingesta-rag.png`
4. Activar (publicar) **00 Router chat (webhook)** y **04 Noticias y nuevos cursos**. 📸 `09-workflows-activos.png`
5. Abrir cada workflow y tomar captura del lienzo. 📸 `10-wf00-router.png` … `15-wf05-ingesta.png`

Si un nodo aparece con advertencia (versión de nodo distinta en n8n), abrirlo, revisar que la credencial esté seleccionada y guardar. Si se modifica un workflow en la UI, exportarlo y actualizar `n8n/build_workflows.py` (o reemplazar el JSON) para que el repo siga siendo replicable.

## 9. Google Sheets (calendario)

1. Crear un Google Sheet e importar `data/calendario_academico.csv` (Archivo → Importar). 📸 `16-google-sheet.png`
2. Archivo → Compartir → **Publicar en la web** → hoja 1 → formato **CSV** → copiar URL.
3. Ponerla en `SHEETS_CSV_URL` del `.env` y aplicar: `docker compose up -d n8n`.

Sin este paso el workflow 02 usa el respaldo `/calendario.csv` del MCP server (mismos datos, desde la BD).

## 10. Verificación

```bash
bash scripts/smoke-test.sh
```
📸 `17-smoke-test.png`. Además:
- Ejecuciones en n8n (menú *Executions*) de cada intención. 📸 `18-ejecuciones.png`
- `chat_log` con los casos bloqueados por guardrails:
```bash
docker compose exec postgres psql -U unab_admin -d unab -c "select creado_en, intencion, bloqueado, motivo_bloqueo, left(mensaje,50) from academico.chat_log order by id desc limit 15;"
```
📸 `19-chat-log-guardrails.png`
- App Android contra el dominio (ver `android/README.md`). 📸 `20-app-*.png`
- Claude Code/Desktop usando el MCP (README §6). 📸 `21-cliente-mcp-claude.png`

## 11. Operación

| Tarea | Comando |
|---|---|
| Ver logs | `docker compose logs -f n8n` |
| Actualizar código | `git pull && docker compose up -d --build` |
| Reimportar workflows | `bash scripts/n8n-import.sh` |
| Backup BD | `docker compose exec postgres pg_dumpall -U unab_admin > backup.sql` |
| Reiniciar desde cero (borra datos) | `docker compose down -v && docker compose up -d --build` |

## 12. Problemas comunes

| Síntoma | Causa / solución |
|---|---|
| Caddy no obtiene certificado | DuckDNS no apunta a la Elastic IP o el puerto 80 está cerrado |
| n8n se reinicia solo | Falta de RAM: confirmar swap con `free -h`; usar t3.medium |
| `401` en el webhook | Header `X-Chatbot-Key` distinto a `CHATBOT_KEY` |
| El agente 03 no ve herramientas | `MCP_TOKEN` distinto en `.env` y en la credencial; reimportar credenciales |
| Error de embeddings / dimensión | Se cambió `EMBED_MODEL`: volver a ejecutar 05 Ingesta (borra y recrea la tabla) |
| Los cambios en `03_seed.sql` no aparecen | Los scripts de `db/init` solo corren con el volumen vacío: `docker compose down -v` |
