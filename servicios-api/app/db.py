import os
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException, Request
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

BOGOTA = ZoneInfo("America/Bogota")


def crear_pool():
    dsn = os.getenv("SERVICIOS_DATABASE_URL")
    if not dsn:
        return None
    return ConnectionPool(
        dsn, min_size=1, max_size=6, timeout=2, open=False,
        kwargs={"row_factory": dict_row, "connect_timeout": 3,
                "options": "-c statement_timeout=4000 -c lock_timeout=2000"},
    )


def pool_db(request: Request):
    pool = request.app.state.pool
    if pool is None:
        raise HTTPException(503, "La base de datos no está disponible.")
    return pool


def estudiante_id(conn, codigo):
    fila = conn.execute(
        "SELECT id FROM academico.estudiante WHERE codigo = %s", (codigo,)
    ).fetchone()
    if fila is None:
        raise HTTPException(404, "Estudiante no encontrado.")
    return fila["id"]


def hoy_bogota():
    return datetime.now(BOGOTA).date()


def bloquear_pagos(conn, codigo):
    # Serializa creación y cambios de estado por estudiante sin escribir en academico.
    conn.execute("SELECT pg_advisory_xact_lock(360, hashtext(%s))", (codigo,))
