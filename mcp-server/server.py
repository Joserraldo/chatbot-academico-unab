"""
Servidor MCP del Asistente Académico UNAB (FastMCP, transporte Streamable HTTP).

Expone herramientas relacionales de SOLO LECTURA sobre PostgreSQL/Supabase
(esquema `academico`, datos sintéticos) y una búsqueda semántica sobre la
tabla de embeddings que llena n8n (`public.rag_documentos`).

Clientes: el AI Agent de n8n (nodo "MCP Client Tool"), Claude Desktop/Code,
o cualquier cliente MCP compatible con Streamable HTTP.

Endpoint:  http://<host>:9000/mcp      Auth: header  Authorization: Bearer <MCP_TOKEN>
"""
from __future__ import annotations

import os
import re
from datetime import date, datetime
from decimal import Decimal
from hmac import compare_digest
from threading import Lock

import httpx
import uvicorn
from fastmcp import FastMCP
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from starlette.concurrency import run_in_threadpool
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

DATABASE_URL = os.environ.get("MCP_DATABASE_URL", "postgresql://chatbot_ro:cambia_esto@localhost:5432/unab")
MCP_TOKEN = os.environ.get("MCP_TOKEN", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "").rstrip("/")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "text-embedding-v3")
LOCAL_EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
RAG_TABLE = os.environ.get("RAG_TABLE", "rag_documentos")

_encoder = None
_encoder_lock = Lock()


def _local_embeddings(texts: list[str]) -> list[list[float]]:
    global _encoder
    with _encoder_lock:
        if _encoder is None:
            from fastembed import TextEmbedding

            _encoder = TextEmbedding(LOCAL_EMBED_MODEL, threads=2)
    return [vector.tolist() for vector in _encoder.embed(texts)]

CODIGO_RE = re.compile(r"^U\d{8}$")

pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=4, open=False,
                      kwargs={"row_factory": dict_row, "autocommit": True})

mcp = FastMCP(
    name="asistente-academico-unab",
    instructions=(
        "Herramientas de consulta académica (datos SINTÉTICOS que simulan Banner/Cosmos) para "
        "estudiantes de Ingeniería de Sistemas de la UNAB. Todas son de solo lectura. "
        "Siempre pide o usa el código del estudiante (formato U + 8 dígitos)."
    ),
)


# ----------------------------------------------------------------- utilidades
def _json(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return v


def _query(sql: str, params: tuple = ()) -> list[dict]:
    if not pool._opened:  # apertura perezosa: el server arranca aunque la BD tarde
        pool.open(wait=True, timeout=30)
    with pool.connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [{k: _json(v) for k, v in r.items()} for r in rows]


def _check_codigo(codigo: str) -> str:
    codigo = (codigo or "").strip().upper()
    if not CODIGO_RE.match(codigo):
        raise ValueError("Código inválido. Formato esperado: U seguido de 8 dígitos, p. ej. U00000001")
    return codigo


# ----------------------------------------------------------------- herramientas
@mcp.tool
def estado_academico(codigo: str) -> dict:
    """Estado de matrícula del periodo actual y avance en el plan de estudios
    (créditos aprobados, % de avance, promedio ponderado, cursos reprobados)."""
    codigo = _check_codigo(codigo)
    rows = _query("SELECT * FROM academico.v_estado_academico WHERE codigo = %s", (codigo,))
    return rows[0] if rows else {"error": f"No existe el estudiante {codigo}"}


@mcp.tool
def cursos_pendientes(codigo: str, solo_habilitados: bool = False) -> list[dict]:
    """Cursos del plan que el estudiante no ha aprobado, ordenados por semestre.
    Con solo_habilitados=True devuelve solo los que ya tienen sus prerrequisitos aprobados."""
    codigo = _check_codigo(codigo)
    sql = "SELECT * FROM academico.v_cursos_pendientes p WHERE p.codigo = %s"
    if solo_habilitados:
        sql += (" AND NOT EXISTS (SELECT 1 FROM academico.v_alertas_prerrequisitos a "
                "WHERE a.codigo = p.codigo AND a.curso_bloqueado = p.curso)")
    sql += " ORDER BY semestre_plan NULLS LAST, curso"
    return _query(sql, (codigo,))


@mcp.tool
def alertas_requisitos(codigo: str) -> dict:
    """Alertas: cursos bloqueados por prerrequisitos y requisitos de grado pendientes
    (inglés, Saber Pro, prácticas, insignia de competencias digitales...)."""
    codigo = _check_codigo(codigo)
    return {
        "prerrequisitos_faltantes": _query(
            "SELECT curso_bloqueado, semestre_plan, prerrequisito_faltante "
            "FROM academico.v_alertas_prerrequisitos WHERE codigo = %s "
            "ORDER BY semestre_plan NULLS LAST LIMIT 30", (codigo,)),
        "requisitos_grado": _query(
            "SELECT requisito, nombre, cumplido, fecha, detalle FROM academico.v_requisitos_grado "
            "WHERE codigo = %s ORDER BY cumplido, requisito", (codigo,)),
    }


@mcp.tool
def proyeccion_semestres(codigo: str) -> dict:
    """Proyección de semestres restantes para graduarse según el ritmo histórico de créditos."""
    codigo = _check_codigo(codigo)
    rows = _query("SELECT * FROM academico.v_proyeccion WHERE codigo = %s", (codigo,))
    if not rows:
        return {"error": f"No existe el estudiante {codigo}"}
    r = rows[0]
    r["supuesto"] = ("Se asume el mismo ritmo de créditos aprobados por semestre (entre 12 y 20). "
                     "Es una estimación, no un concepto oficial de Registro Académico.")
    return r


@mcp.tool
def recomendaciones(codigo: str) -> list[str]:
    """Recomendaciones personalizadas para el éxito académico (reglas sobre promedio,
    cursos reprobados, prerrequisitos, competencias digitales e inglés)."""
    codigo = _check_codigo(codigo)
    rows = _query("SELECT * FROM academico.v_estado_academico WHERE codigo = %s", (codigo,))
    if not rows:
        return [f"No existe el estudiante {codigo}"]
    ea = rows[0]
    recs: list[str] = []
    prom = ea.get("promedio_ponderado") or 0
    if prom and prom < 3.5:
        recs.append(f"Tu promedio ponderado es {prom}. Agenda tutorías y revisa la carga de créditos del próximo periodo.")
    elif prom >= 4.2:
        recs.append(f"Promedio de {prom}: considera semilleros de investigación o monitorías académicas.")
    if ea.get("cursos_reprobados", 0) > 0:
        recs.append(f"Tienes {ea['cursos_reprobados']} curso(s) reprobado(s): priorízalos, suelen ser prerrequisitos.")
    if ea.get("estado_matricula") in ("pendiente_pago", "preinscrito", "sin_matricula"):
        recs.append("Tu matrícula del periodo actual no está completa: revisa el pago y las fechas en el calendario académico.")
    bloq = _query("SELECT COUNT(DISTINCT curso_bloqueado) AS n FROM academico.v_alertas_prerrequisitos WHERE codigo=%s", (codigo,))[0]["n"]
    if bloq:
        recs.append(f"Hay {bloq} curso(s) bloqueados por prerrequisitos; inscribe primero los habilitados del semestre más bajo.")
    ins = _query("SELECT * FROM academico.v_insignia WHERE codigo=%s", (codigo,))
    if ins and not ins[0]["insignia_obtenida"]:
        recs.append(f"Llevas {ins[0]['cursos_validos']} curso(s) válidos para la insignia de competencias digitales "
                    "(se requieren 3, con al menos uno intermedio o avanzado). Mira la oferta del CCD.")
    req = _query("SELECT nombre FROM academico.v_requisitos_grado WHERE codigo=%s AND NOT cumplido", (codigo,))
    if req and (ea.get("semestre_actual") or 0) >= 6:
        recs.append("Requisitos de grado pendientes: " + ", ".join(r["nombre"] for r in req) + ".")
    recs.append("Autoaprendizaje: dedica 2 horas semanales a un curso abierto relacionado con tu próxima asignatura.")
    return recs


@mcp.tool
def competencias_digitales(codigo: str) -> dict:
    """Cursos de competencias digitales (CCD) que ha tomado el estudiante y su progreso hacia la insignia."""
    codigo = _check_codigo(codigo)
    return {
        "cursos": _query("SELECT curso_cd, nivel, horas, estado, puntaje, fecha FROM academico.v_competencias_digitales "
                         "WHERE codigo=%s ORDER BY fecha", (codigo,)),
        "insignia": (_query("SELECT cursos_validos, tiene_nivel_intermedio, insignia_obtenida "
                            "FROM academico.v_insignia WHERE codigo=%s", (codigo,)) or [{}])[0],
    }


@mcp.tool
def oferta_competencias_digitales(nivel: str | None = None) -> list[dict]:
    """Catálogo de cursos del Centro de Competencias Digitales. nivel: básico | intermedio | avanzado."""
    if nivel:
        return _query("SELECT codigo, nombre, nivel, horas, modalidad, descripcion FROM academico.curso_cd "
                      "WHERE nivel = %s ORDER BY nombre", (nivel.lower(),))
    return _query("SELECT codigo, nombre, nivel, horas, modalidad, descripcion FROM academico.curso_cd ORDER BY nivel, nombre")


@mcp.tool
def calendario_academico(categoria: str | None = None) -> list[dict]:
    """Fechas del calendario académico (copia en BD del Google Sheet).
    categoria: inscripciones | matricula | diagnostica | inicio_cursos | evaluaciones | grados."""
    if categoria:
        return _query("SELECT * FROM academico.calendario_evento WHERE categoria = %s ORDER BY fecha_inicio",
                      (categoria.lower(),))
    return _query("SELECT * FROM academico.calendario_evento WHERE fecha_inicio >= CURRENT_DATE - 30 "
                  "ORDER BY fecha_inicio LIMIT 20")


@mcp.tool
def noticias_recientes(limite: int = 5, categoria: str | None = None) -> list[dict]:
    """Noticias, nuevos cursos, convocatorias y certificaciones capturadas por el scraper."""
    limite = max(1, min(int(limite), 20))
    if categoria:
        return _query("SELECT * FROM academico.v_noticias_recientes WHERE categoria=%s LIMIT %s", (categoria, limite))
    return _query("SELECT * FROM academico.v_noticias_recientes LIMIT %s", (limite,))


@mcp.tool
def buscar_documentos(pregunta: str, k: int = 4) -> list[dict]:
    """Búsqueda semántica (RAG) en los documentos institucionales del CCD y del programa
    indexados por el workflow de ingesta de n8n en pgvector."""
    k = max(1, min(int(k), 8))
    if EMBED_MODEL == LOCAL_EMBED_MODEL:
        vec = _local_embeddings([pregunta])[0]
    else:
        if not LLM_BASE_URL:
            return [{"error": "Proveedor de embeddings no configurado"}]
        resp = httpx.post(f"{LLM_BASE_URL}/embeddings",
                          headers={"Authorization": f"Bearer {LLM_API_KEY}"},
                          json={"model": EMBED_MODEL, "input": pregunta}, timeout=30)
        resp.raise_for_status()
        vec = resp.json()["data"][0]["embedding"]
    literal = "[" + ",".join(f"{x:.7f}" for x in vec) + "]"
    return _query(
        f"SELECT text AS fragmento, metadata->>'source' AS fuente, "
        f"ROUND((1 - (embedding <=> %s::vector))::numeric, 3) AS similitud "
        f"FROM public.{RAG_TABLE} ORDER BY embedding <=> %s::vector LIMIT %s",
        (literal, literal, k))


# ----------------------------------------------------------------- HTTP / auth
class BearerAuth(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/v1/embeddings", "/v1/models"):
            authorization = request.headers.get("authorization", "").encode()
            if EMBED_MODEL != LOCAL_EMBED_MODEL:
                return JSONResponse({"error": "local embeddings disabled"}, status_code=404)
            if not LLM_API_KEY or not compare_digest(authorization, f"Bearer {LLM_API_KEY}".encode()):
                return JSONResponse({"error": "unauthorized"}, status_code=401)
            return await call_next(request)
        if request.url.path in ("/health", "/calendario.csv"):
            return await call_next(request)
        if MCP_TOKEN and request.headers.get("authorization", "") != f"Bearer {MCP_TOKEN}":
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


@mcp.custom_route("/health", methods=["GET"])
async def health(_: Request):
    return PlainTextResponse("ok")


@mcp.custom_route("/v1/models", methods=["GET"])
async def models(_: Request):
    return JSONResponse({"object": "list", "data": [{"object": "model", "id": LOCAL_EMBED_MODEL}]})


@mcp.custom_route("/v1/embeddings", methods=["POST"])
async def embeddings(request: Request):
    try:
        body = await request.json()
    except ValueError:
        return JSONResponse({"error": "invalid JSON"}, status_code=400)
    if not isinstance(body, dict) or body.get("model") != LOCAL_EMBED_MODEL:
        return JSONResponse({"error": "unknown embedding model"}, status_code=400)
    texts = body.get("input")
    if isinstance(texts, str):
        texts = [texts]
    if not isinstance(texts, list) or not 1 <= len(texts) <= 512 or any(
        not isinstance(text, str) or not 1 <= len(text) <= 16000 for text in texts
    ):
        return JSONResponse({"error": "invalid embedding input"}, status_code=400)
    vectors = await run_in_threadpool(_local_embeddings, texts)
    return JSONResponse({"object": "list", "model": LOCAL_EMBED_MODEL, "data": [
        {"object": "embedding", "index": i, "embedding": vector}
        for i, vector in enumerate(vectors)
    ]})


@mcp.custom_route("/calendario.csv", methods=["GET"])
async def calendario_csv(_: Request):
    """Respaldo del Google Sheet: mismo formato CSV, leído de academico.calendario_evento.
    El workflow 02 lo usa si SHEETS_CSV_URL no está configurado. Datos públicos (sin auth)."""
    import csv
    import io
    rows = _query("SELECT periodo, evento, categoria, fecha_inicio, fecha_fin, detalle "
                  "FROM academico.calendario_evento ORDER BY fecha_inicio")
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["periodo", "evento", "categoria", "fecha_inicio", "fecha_fin", "detalle"])
    w.writeheader()
    w.writerows(rows)
    return PlainTextResponse(buf.getvalue(), media_type="text/csv; charset=utf-8")


app = mcp.http_app(path="/mcp", middleware=[Middleware(BearerAuth)])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("MCP_PORT", "9000")))
