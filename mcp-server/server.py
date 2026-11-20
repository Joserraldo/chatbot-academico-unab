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
import unicodedata
from datetime import date, datetime
from decimal import Decimal
from hmac import compare_digest
from threading import Lock

import httpx
import uvicorn
from fastmcp import FastMCP
from psycopg import errors as psycopg_errors
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
        "Herramientas de consulta académica (datos SINTÉTICOS que simulan Banner/Cosmos, TEMA y la "
        "biblioteca) para estudiantes de cualquier programa de la UNAB. Todas son de solo lectura. "
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


def _query_opt(sql: str, params: tuple = ()) -> list[dict] | None:
    """Como _query, pero devuelve None si la tabla aún no existe o el rol no tiene permiso
    (p. ej. un despliegue sin la migración v2). Así una herramienta no tumba al agente."""
    try:
        return _query(sql, params)
    except (psycopg_errors.UndefinedTable, psycopg_errors.InsufficientPrivilege):
        return None


def _sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


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
    """Recomendaciones personalizadas para el éxito académico de cualquier programa de la UNAB
    (reglas sobre promedio, cursos reprobados, prerrequisitos, competencias digitales, requisitos
    de grado, tareas de TEMA pendientes, evaluación docente y préstamos vencidos)."""
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
    # Requisitos de grado: aplica a cualquier programa; se mencionan cuando el estudiante ya
    # está en la recta final (últimos 3 semestres del plan o >= 70 % de avance), no solo en ISIS.
    req = _query("SELECT nombre FROM academico.v_requisitos_grado WHERE codigo=%s AND NOT cumplido", (codigo,))
    plan = _query("SELECT p.semestres FROM academico.estudiante e JOIN academico.programa p ON p.id = e.programa_id "
                  "WHERE e.codigo = %s", (codigo,))
    semestres_plan = (plan[0]["semestres"] if plan else None) or 9
    recta_final = ((ea.get("semestre_actual") or 0) >= semestres_plan - 2
                   or (ea.get("porcentaje_avance") or 0) >= 70)
    if req and recta_final:
        recs.append("Requisitos de grado pendientes: " + ", ".join(r["nombre"] for r in req) + ".")
    # TEMA, evaluación docente y biblioteca (tablas v2; se omiten si no existen)
    tareas = _query_opt(
        "SELECT COUNT(*) AS n FROM academico.entrega_tema et JOIN academico.estudiante e ON e.id = et.estudiante_id "
        "WHERE e.codigo = %s AND et.estado IN ('pendiente','vencida')", (codigo,))
    if tareas and tareas[0]["n"]:
        recs.append(f"Tienes {tareas[0]['n']} tarea(s) de TEMA pendientes o vencidas: organízalas por fecha de entrega.")
    evals = _query_opt(
        "SELECT COUNT(*) AS n FROM academico.evaluacion_docente ed JOIN academico.estudiante e ON e.id = ed.estudiante_id "
        "WHERE e.codigo = %s AND ed.estado = 'pendiente'", (codigo,))
    if evals and evals[0]["n"]:
        recs.append(f"Recuerda calificar a tus profesores en TEMA: tienes {evals[0]['n']} evaluación(es) docente(s) pendiente(s).")
    venc = _query_opt(
        "SELECT COUNT(*) AS n FROM academico.prestamo_biblioteca pb JOIN academico.estudiante e ON e.id = pb.estudiante_id "
        "WHERE e.codigo = %s AND pb.estado = 'vencido'", (codigo,))
    if venc and venc[0]["n"]:
        recs.append(f"Tienes {venc[0]['n']} préstamo(s) de biblioteca vencido(s): renuévalos o devuélvelos para evitar multas.")
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


# ----------------------------------------------------------------- v2: Cosmos, TEMA, biblioteca, riesgo
_DIAS = {"lun": "Lun", "mar": "Mar", "mie": "Mié", "jue": "Jue", "vie": "Vie", "sab": "Sáb", "dom": "Dom"}
_DIAS_SEMANA = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


# Fechas 'de hoy' en hora de Colombia (UTC-5, sin horario de verano), sin depender de la base de zonas horarias.
def _dia_abrev(dia: str) -> str | None:
    """'miércoles', 'miercoles', 'Mié', 'hoy', 'mañana' -> 'Mié'. None si no se entiende."""
    d = _sin_tildes((dia or "").strip())
    hoy = _query("SELECT EXTRACT(ISODOW FROM (timezone('UTC', now()) - interval '5 hours')::date)::int AS d")[0]["d"]
    if d == "hoy":
        return _DIAS_SEMANA[hoy - 1]
    if d == "manana":
        return _DIAS_SEMANA[hoy % 7]
    return _DIAS.get(d[:3])


def _notas_corte(codigo: str) -> list[dict]:
    """Notas por corte del periodo actual, agrupadas por curso con nota acumulada."""
    filas = _query(
        "SELECT c.codigo AS codigo_curso, c.nombre AS curso, c.creditos, s.grupo, np.corte, np.porcentaje, np.nota "
        "FROM academico.nota_parcial np "
        "JOIN academico.estudiante e ON e.id = np.estudiante_id "
        "JOIN academico.seccion s ON s.id = np.seccion_id "
        "JOIN academico.periodo p ON p.id = s.periodo_id AND p.actual "
        "JOIN academico.curso_plan c ON c.id = s.curso_id "
        "WHERE e.codigo = %s ORDER BY c.nombre, np.corte", (codigo,))
    cursos: dict[str, dict] = {}
    for f in filas:
        c = cursos.setdefault(f["codigo_curso"], {
            "curso": f["curso"], "codigo_curso": f["codigo_curso"], "grupo": f["grupo"],
            "creditos": f["creditos"], "cortes": []})
        c["cortes"].append({"corte": f["corte"], "porcentaje": f["porcentaje"], "nota": f["nota"]})
    resultado = []
    for c in cursos.values():
        calificados = [k for k in c["cortes"] if k["nota"] is not None]
        pct = sum(k["porcentaje"] for k in calificados)
        acum = round(sum(k["nota"] * k["porcentaje"] / 100 for k in calificados), 2)
        c["nota_acumulada"] = acum if calificados else None
        c["porcentaje_calificado"] = pct
        c["promedio_sobre_calificado"] = round(acum * 100 / pct, 2) if pct else None
        restante = 100 - pct
        if calificados and restante > 0:
            necesaria = (3.0 - acum) / (restante / 100)
            c["nota_necesaria_para_aprobar"] = (
                0.0 if necesaria <= 0 else round(necesaria, 2) if necesaria <= 5 else None)
            c["aprobacion_imposible"] = necesaria > 5
        c["estado_corte"] = ("sin calificar" if not calificados else
                             "en riesgo" if (acum * 100 / pct) < 3.0 else "al día")
        resultado.append(c)
    return resultado


def _tareas(codigo: str, solo_pendientes: bool, dias: int | None = None) -> list[dict]:
    sql = ("SELECT t.titulo, t.tipo, c.nombre AS curso, t.peso, et.estado, et.nota, t.fecha_entrega, "
           "((timezone('UTC', t.fecha_entrega) - interval '5 hours')::date "
           " - (timezone('UTC', now()) - interval '5 hours')::date) AS dias_restantes "
           "FROM academico.entrega_tema et "
           "JOIN academico.estudiante e ON e.id = et.estudiante_id "
           "JOIN academico.tarea_tema t ON t.id = et.tarea_id "
           "JOIN academico.seccion s ON s.id = t.seccion_id "
           "JOIN academico.periodo p ON p.id = s.periodo_id AND p.actual "
           "JOIN academico.curso_plan c ON c.id = s.curso_id "
           "WHERE e.codigo = %s")
    params: list = [codigo]
    if solo_pendientes:
        sql += " AND et.estado IN ('pendiente','vencida')"
        if dias is not None:  # próximos N días (y todo lo vencido)
            sql += " AND (et.estado = 'vencida' OR t.fecha_entrega <= now() + make_interval(days => %s))"
            params.append(dias)
    sql += " ORDER BY t.fecha_entrega"
    return _query(sql, tuple(params))


def _evaluaciones(codigo: str) -> list[dict]:
    return _query(
        "SELECT c.nombre AS curso, d.nombre AS docente, ed.fecha_limite, "
        "(ed.fecha_limite - (timezone('UTC', now()) - interval '5 hours')::date) AS dias_restantes "
        "FROM academico.evaluacion_docente ed "
        "JOIN academico.estudiante e ON e.id = ed.estudiante_id "
        "JOIN academico.seccion s ON s.id = ed.seccion_id "
        "JOIN academico.docente d ON d.id = s.docente_id "
        "JOIN academico.curso_plan c ON c.id = s.curso_id "
        "WHERE e.codigo = %s AND ed.estado = 'pendiente' ORDER BY ed.fecha_limite", (codigo,))


def _prestamos(codigo: str, incluir_devueltos: bool = False) -> list[dict]:
    sql = ("SELECT pb.titulo, pb.autor, pb.fecha_prestamo, pb.fecha_vencimiento, pb.renovaciones, pb.estado, pb.multa, "
           "(pb.fecha_vencimiento - (timezone('UTC', now()) - interval '5 hours')::date) AS dias_para_vencer "
           "FROM academico.prestamo_biblioteca pb JOIN academico.estudiante e ON e.id = pb.estudiante_id "
           "WHERE e.codigo = %s")
    if not incluir_devueltos:
        sql += " AND pb.estado <> 'devuelto'"
    return _query(sql + " ORDER BY pb.fecha_vencimiento", (codigo,))


_ACCIONES_RIESGO = [  # (palabras del factor, acción sugerida)
    (("promedio acumulado",), "Agenda tutorías o monitorías en los cursos donde tu nota es más baja y reduce la carga del próximo periodo."),
    (("tendencia",), "Tu promedio viene bajando: revisa con tu director de programa qué cambió y ajusta tus hábitos de estudio."),
    (("reprobados",), "Prioriza repetir los cursos reprobados; suelen ser prerrequisito de otros y se acumulan."),
    (("créditos", "brecha"), "Estás aprobando menos créditos de los esperados: habla con tu director de programa para replanificar tu carga."),
    (("diagnóstica",), "Refuerza las bases con los cursos del CCD (nivel básico) y la guía de éxito académico."),
    (("ccd",), "Inscríbete en un curso del Centro de Competencias Digitales: suma a la insignia y refuerza tus bases."),
    (("matrícula",), "Completa tu matrícula (pago o inscripción de materias) cuanto antes; puedo ayudarte a generar la orden de pago."),
    (("tareas",), "Ponte al día con las tareas pendientes o vencidas en TEMA, empezando por las de mayor peso, y escribe al docente si necesitas un plazo."),
    (("corte",), "Tu desempeño en el primer corte fue bajo: pide retroalimentación al docente y usa el segundo corte para recuperar."),
]


def _acciones_riesgo(nivel: str, factores: list[dict]) -> list[str]:
    acciones: list[str] = []
    for f in sorted(factores, key=lambda x: -(x.get("aporte") or 0)):
        if (f.get("aporte") or 0) <= 0:  # solo los factores que SUBEN el riesgo
            continue
        nombre = _sin_tildes(str(f.get("factor", "")))
        for claves, accion in _ACCIONES_RIESGO:
            if any(_sin_tildes(k) in nombre for k in claves) and accion not in acciones:
                acciones.append(accion)
                break
    if nivel in ("medio", "alto"):
        acciones.append("Bienestar Universitario ofrece acompañamiento académico y psicológico gratuito: acércate sin pena.")
    if not acciones:
        acciones.append("Sigue así: mantén tus entregas al día y revisa tus notas de corte con frecuencia.")
    return acciones


def _riesgo(codigo: str) -> dict | None:
    filas = _query_opt("SELECT codigo, probabilidad, nivel, factores, modelo, actualizado_en "
                       "FROM servicios.riesgo_estudiante WHERE codigo = %s", (codigo,))
    if not filas:
        return None
    r = filas[0]
    factores = r["factores"] if isinstance(r["factores"], list) else []
    return {"nivel": r["nivel"], "probabilidad": r["probabilidad"], "factores": factores,
            "modelo": r["modelo"], "actualizado_en": r["actualizado_en"],
            "acciones_sugeridas": _acciones_riesgo(r["nivel"], factores)}


@mcp.tool
def notas_periodo_actual(codigo: str) -> dict:
    """Notas por corte (Cosmos) del periodo académico ACTUAL, curso por curso. Úsala para
    "¿cómo voy en mis materias?", "¿qué nota tengo en X?", "notas del primer corte" o "¿qué necesito
    para aprobar?". Cada curso trae sus 3 cortes con porcentaje y nota (null = aún sin calificar),
    la nota acumulada ponderada, el promedio sobre lo ya calificado y, si faltan cortes, la nota
    que necesita en el resto para llegar a 3.0 (aprobar). Para el historial de semestres anteriores
    usa estado_academico; para el horario usa horario."""
    codigo = _check_codigo(codigo)
    periodo = _query("SELECT codigo FROM academico.periodo WHERE actual LIMIT 1")
    cursos = _notas_corte(codigo)
    return {"periodo": periodo[0]["codigo"] if periodo else None, "escala": "0.0 a 5.0, aprueba con 3.0",
            "cursos": cursos,
            "aviso": None if cursos else "No hay notas de corte registradas para el periodo actual."}


@mcp.tool
def horario(codigo: str, dia: str | None = None) -> list[dict]:
    """Horario de clases del periodo actual (Cosmos): cada materia inscrita con grupo, días y horas,
    salón y docente. Úsala para "¿qué clases tengo hoy/mañana/el lunes?", "¿dónde es mi clase de X?"
    o "mi horario". dia es opcional: 'hoy', 'mañana' o un día de la semana ('lunes'...'domingo');
    con dia solo devuelve las clases de ese día y sus horas. Sin dia devuelve toda la semana."""
    codigo = _check_codigo(codigo)
    filtro = None
    if dia:
        filtro = _dia_abrev(dia)
        if not filtro:
            raise ValueError("Día no reconocido. Usa 'hoy', 'mañana' o un día entre lunes y domingo.")
    filas = _query(
        "SELECT c.nombre AS curso, c.codigo AS codigo_curso, s.grupo, s.horario, s.salon, d.nombre AS docente "
        "FROM academico.inscripcion_seccion i JOIN academico.estudiante e ON e.id = i.estudiante_id "
        "JOIN academico.seccion s ON s.id = i.seccion_id "
        "JOIN academico.periodo p ON p.id = s.periodo_id AND p.actual "
        "JOIN academico.curso_plan c ON c.id = s.curso_id JOIN academico.docente d ON d.id = s.docente_id "
        "WHERE e.codigo = %s ORDER BY c.nombre", (codigo,))
    resultado = []
    for f in filas:
        franjas = [p.strip() for p in f["horario"].split(";") if p.strip()]
        if filtro:
            franjas = [p for p in franjas if _sin_tildes(p).startswith(_sin_tildes(filtro))]
            if not franjas:
                continue
        f["franjas"] = franjas
        resultado.append(f)
    if filtro:
        resultado.sort(key=lambda f: f["franjas"][0].split(" ", 1)[-1])
    return resultado


@mcp.tool
def tareas_tema(codigo: str, solo_pendientes: bool = True) -> list[dict]:
    """Tareas, quices, foros y proyectos de TEMA (plataforma de cursos) del periodo actual, ordenados
    por fecha de entrega. Con solo_pendientes=True (por defecto) solo las no entregadas: estado
    'pendiente' o 'vencida'. Con solo_pendientes=False incluye también las entregadas y calificadas
    con su nota. Cada una trae curso, tipo, peso (%), fecha_entrega y dias_restantes (negativo =
    ya venció). Úsala para "¿qué tareas tengo?", "¿qué debo entregar esta semana?" o "¿qué se me venció?"."""
    return _tareas(_check_codigo(codigo), bool(solo_pendientes))


@mcp.tool
def evaluaciones_docentes_pendientes(codigo: str) -> dict:
    """Evaluaciones docentes que el estudiante AÚN no ha completado en TEMA/Cosmos, con el docente,
    el curso y la fecha límite. Úsala cuando pregunte por la evaluación docente y también como
    recordatorio proactivo al final de una respuesta sobre tareas o notas: si hay pendientes,
    recuérdale "califica a tu profesor X en TEMA". Los pasos para hacerla están en
    enlaces_tramites(tema='evaluación docente')."""
    codigo = _check_codigo(codigo)
    pend = _evaluaciones(codigo)
    return {"pendientes": pend,
            "recordatorio": ("; ".join(f"Califica a tu profesor {p['docente']} ({p['curso']}) en TEMA antes del {p['fecha_limite']}"
                                       for p in pend) if pend else "No tienes evaluaciones docentes pendientes.")}


@mcp.tool
def prestamos_biblioteca(codigo: str, incluir_devueltos: bool = False) -> dict:
    """Préstamos de la biblioteca de la UNAB del estudiante: título, autor, fecha de vencimiento,
    días para vencer (negativo = vencido), renovaciones, estado (activo|vencido) y multa en COP.
    Devuelve además multa_total. Úsala para "¿qué libros tengo prestados?", "¿tengo multas?" o
    "¿cuándo vence mi préstamo?". Renovar se hace en el catálogo (enlaces_tramites(tema='renovar')) y
    la multa se paga en línea creando una orden de pago (trámites). incluir_devueltos=True añade el historial."""
    codigo = _check_codigo(codigo)
    filas = _prestamos(codigo, bool(incluir_devueltos))
    return {"prestamos": filas, "multa_total": sum((f["multa"] or 0) for f in filas),
            "vencidos": sum(1 for f in filas if f["estado"] == "vencido")}


@mcp.tool
def enlaces_tramites(tema: str | None = None) -> list[dict]:
    """Enlaces oficiales y pasos de trámites UNAB (Cosmos, TEMA, reservas de espacios, gimnasio,
    renovación de préstamos en la biblioteca, evaluación docente...). Con tema (texto libre como
    'renovar libro', 'reservar sala', 'gimnasio', 'evaluación docente') devuelve los trámites más
    relacionados con sus pasos; sin tema lista todos (solo nombre, url y descripción). NUNCA
    inventes enlaces: usa solo los que devuelve esta herramienta."""
    filas = _query("SELECT codigo, nombre, url, descripcion, pasos, palabras_clave FROM academico.enlace_tramite ORDER BY codigo")
    if not tema or not tema.strip():
        return [{k: f[k] for k in ("codigo", "nombre", "url", "descripcion")} for f in filas]
    t = _sin_tildes(tema)
    palabras = [w for w in re.split(r"\W+", t) if len(w) > 2]
    puntuadas = []
    for f in filas:
        claves = [_sin_tildes(k) for k in (f["palabras_clave"] or [])]
        texto = _sin_tildes(f"{f['codigo']} {f['nombre']} {f['descripcion']}")
        puntos = sum(3 for k in claves if k and (k in t or t in k))
        puntos += sum(2 for w in palabras if any(w in k or k in w for k in claves if len(k) > 2))
        puntos += sum(1 for w in palabras if w in texto)
        if puntos:
            puntuadas.append((puntos, f))
    puntuadas.sort(key=lambda x: -x[0])
    return [f for _, f in puntuadas[:3]]


@mcp.tool
def riesgo_academico(codigo: str) -> dict:
    """Riesgo de deserción/bajo rendimiento del estudiante según el modelo de aprendizaje automático
    del proyecto: nivel (bajo|medio|alto), probabilidad (0-1), los factores que más pesan (aporte
    positivo = sube el riesgo) y acciones sugeridas. Úsala para "¿estoy en riesgo?", "¿voy bien o
    mal?" o cuando el estudiante tenga notas bajas. Es una ESTIMACIÓN de apoyo, no un concepto
    oficial: preséntala con empatía y enfocada en qué puede hacer."""
    codigo = _check_codigo(codigo)
    r = _riesgo(codigo)
    if r is None:
        return {"disponible": False,
                "mensaje": "Aún no hay un cálculo de riesgo para este estudiante. Usa estado_academico y notas_periodo_actual."}
    return {"disponible": True, **r,
            "aviso": "Estimación estadística de un modelo sobre datos sintéticos; no es un concepto oficial."}


@mcp.tool
def resumen_360(codigo: str) -> dict:
    """Resumen compacto de "¿cómo voy?": combina en UNA llamada el estado académico (avance, promedio,
    matrícula), las notas de corte del periodo actual, las tareas de TEMA pendientes o vencidas
    (próximos 7 días), las evaluaciones docentes pendientes, los préstamos de biblioteca (con multa)
    y el riesgo académico. Úsala para "¿cómo voy?", "dame un resumen", "qué tengo pendiente" o
    "cómo está mi semestre". Luego explica lo más importante en pocas viñetas y ofrece profundizar."""
    codigo = _check_codigo(codigo)
    ea = _query("SELECT codigo, estudiante, programa, semestre_actual, periodo_actual, estado_matricula, "
                "valor_matricula, porcentaje_avance, promedio_ponderado, cursos_reprobados "
                "FROM academico.v_estado_academico WHERE codigo = %s", (codigo,))
    if not ea:
        return {"error": f"No existe el estudiante {codigo}"}
    notas = _notas_corte(codigo)
    notas_compactas = [{"curso": c["curso"], "nota_acumulada": c["nota_acumulada"],
                        "porcentaje_calificado": c["porcentaje_calificado"], "estado": c["estado_corte"],
                        **({"nota_necesaria_para_aprobar": c["nota_necesaria_para_aprobar"]}
                           if c.get("nota_necesaria_para_aprobar") is not None else {})} for c in notas]
    tareas = _tareas(codigo, True, 7)
    tareas_c = [{k: t[k] for k in ("titulo", "curso", "tipo", "fecha_entrega", "estado", "dias_restantes")} for t in tareas]
    evals = _evaluaciones(codigo)
    prest = _prestamos(codigo)
    riesgo = _riesgo(codigo)
    alertas = []
    if ea[0]["estado_matricula"] in ("pendiente_pago", "preinscrito", "sin_matricula"):
        alertas.append(f"Matrícula {ea[0]['estado_matricula']}: falta completarla.")
    if ea[0]["cursos_reprobados"]:
        alertas.append(f"{ea[0]['cursos_reprobados']} curso(s) reprobado(s) en el historial.")
    alertas += [f"Curso {c['curso']} en riesgo de perder (acumulado {c['nota_acumulada']})."
                for c in notas if c["estado_corte"] == "en riesgo"]
    vencidas = [t for t in tareas_c if t["estado"] == "vencida"]
    if vencidas:
        alertas.append(f"{len(vencidas)} tarea(s) vencida(s) en TEMA.")
    if evals:
        alertas.append("Evaluación docente pendiente: " + ", ".join(e["docente"] for e in evals) + ".")
    if any(p["estado"] == "vencido" or (p["multa"] or 0) > 0 for p in prest):
        alertas.append("Tienes préstamos de biblioteca vencidos o con multa.")
    if riesgo and riesgo["nivel"] in ("medio", "alto"):
        alertas.append(f"Riesgo académico {riesgo['nivel']}.")
    return {"estudiante": ea[0], "notas_corte": notas_compactas, "tareas_proximos_7_dias": tareas_c,
            "evaluaciones_docentes_pendientes": evals,
            "prestamos": [{k: p[k] for k in ("titulo", "fecha_vencimiento", "estado", "multa", "dias_para_vencer")} for p in prest],
            "multa_biblioteca_total": sum((p["multa"] or 0) for p in prest),
            "riesgo": ({k: riesgo[k] for k in ("nivel", "probabilidad", "factores", "acciones_sugeridas")} if riesgo else None),
            "alertas": alertas}


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
