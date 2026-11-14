"""
Genera n8n/.credentials.json (ignorado por git) a partir de .env, con los mismos IDs
que referencian los workflows. Así la importación es 100 % reproducible y nadie
tiene que crear credenciales a mano en la UI.

Uso (en la VM, desde la raíz del repo):  python3 scripts/render_n8n_credentials.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env(path: Path) -> dict:
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.split(" #")[0].strip()
    return env


e = load_env(ROOT / ".env")
faltan = [k for k in ("POSTGRES_USER", "POSTGRES_PASSWORD", "LLM_BASE_URL", "LLM_API_KEY",
                      "EMBED_BASE_URL", "EMBED_API_KEY", "MCP_TOKEN", "CHATBOT_KEY") if not e.get(k)]
if faltan:
    raise SystemExit(f"Faltan variables en .env: {', '.join(faltan)}")

creds = [
    {"id": "credPgUnab000001", "name": "Postgres UNAB", "type": "postgres",
     "data": {"host": "postgres", "port": 5432, "database": "unab", "user": e["POSTGRES_USER"],
              "password": e["POSTGRES_PASSWORD"], "ssl": "disable", "allowUnauthorizedCerts": False}},
    {"id": "credLlmChat00001", "name": "LLM chat (b.ai / OpenAI compatible)", "type": "openAiApi",
     "data": {"apiKey": e["LLM_API_KEY"], "url": e["LLM_BASE_URL"]}},
    {"id": "credLlmEmbed0001", "name": "LLM embeddings (OpenAI compatible)", "type": "openAiApi",
     "data": {"apiKey": e["EMBED_API_KEY"], "url": e["EMBED_BASE_URL"]}},
    {"id": "credWebhookKey01", "name": "Webhook X-Chatbot-Key", "type": "httpHeaderAuth",
     "data": {"name": "X-Chatbot-Key", "value": e["CHATBOT_KEY"]}},
    {"id": "credMcpBearer001", "name": "MCP server bearer", "type": "httpBearerAuth",
     "data": {"token": e["MCP_TOKEN"]}},
]
out = ROOT / "n8n" / ".credentials.json"
out.write_text(json.dumps(creds, indent=2), encoding="utf-8")
print(f"OK -> {out} ({len(creds)} credenciales)")
