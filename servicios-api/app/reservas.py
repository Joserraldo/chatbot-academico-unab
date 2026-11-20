from datetime import datetime, time, timedelta

from fastapi import HTTPException
from psycopg.errors import UniqueViolation

from .bold import crear_orden, pago_orden
from .db import bloquear_pagos, estudiante_id

APERTURA = time(7)
CIERRE = time(21)
CONSULTA_RESERVA = """
    SELECT r.id, e.nombre AS espacio, r.fecha, r.hora_inicio, r.hora_fin, r.estado, r.order_id
    FROM servicios.reserva r JOIN servicios.espacio e ON e.id = r.espacio_id
"""


def datos_reserva(fila):
    return {
        "id": fila["id"], "espacio": fila["espacio"], "fecha": fila["fecha"].isoformat(),
        "horaInicio": fila["hora_inicio"].isoformat(timespec="minutes"),
        "horaFin": fila["hora_fin"].isoformat(timespec="minutes"),
        "estado": fila["estado"], "orderId": fila["order_id"],
    }


def buscar_espacio(conn, codigo):
    espacio = conn.execute(
        "SELECT * FROM servicios.espacio WHERE codigo = %s", (codigo,)
    ).fetchone()
    if espacio is None:
        raise HTTPException(404, "Espacio no encontrado.")
    return espacio


def tramos_ocupados(conn, espacio_id, fecha):
    return conn.execute("""
        SELECT hora_inicio, hora_fin FROM servicios.reserva
        WHERE espacio_id = %s AND fecha = %s AND estado <> 'cancelada'
    """, (espacio_id, fecha)).fetchall()


def hay_choque(ocupados, inicio, fin):
    return any(tramo["hora_inicio"] < fin and tramo["hora_fin"] > inicio for tramo in ocupados)


def disponibilidad(conn, codigo, fecha):
    espacio = buscar_espacio(conn, codigo)
    ocupados = tramos_ocupados(conn, espacio["id"], fecha)
    return {
        "espacio": espacio, "fecha": fecha,
        "franjas": [
            {"horaInicio": f"{hora:02}:00", "horaFin": f"{hora + 1:02}:00",
             "libre": not hay_choque(ocupados, time(hora), time(hora + 1))}
            for hora in range(APERTURA.hour, CIERRE.hour)
        ],
    }


def reservar(conn, peticion):
    inicio = time.fromisoformat(peticion.horaInicio)
    fin = datetime.combine(peticion.fecha, inicio) + timedelta(hours=peticion.horas)
    if inicio < APERTURA or fin.date() != peticion.fecha or fin.time() > CIERRE:
        raise HTTPException(422, "La reserva debe estar entre las 07:00 y las 21:00.")

    codigo = peticion.codigoEstudiante
    estudiante_id(conn, codigo)
    bloquear_pagos(conn, codigo)
    espacio = buscar_espacio(conn, peticion.espacio)
    # El índice del esquema cubre inicios iguales. Este bloqueo cubre los solapamientos.
    conn.execute("SELECT id FROM servicios.espacio WHERE id = %s FOR UPDATE", (espacio["id"],))
    ocupados = tramos_ocupados(conn, espacio["id"], peticion.fecha)
    if hay_choque(ocupados, inicio, fin.time()):
        raise HTTPException(409, "El espacio ya está reservado para ese horario.")

    tiene_costo = espacio["tarifa_hora"] > 0
    try:
        reserva = conn.execute("""
            INSERT INTO servicios.reserva
                (codigo_estudiante, espacio_id, fecha, hora_inicio, hora_fin, estado)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, fecha, hora_inicio, hora_fin, estado, order_id
        """, (
            codigo, espacio["id"], peticion.fecha, inicio, fin.time(),
            "pendiente_pago" if tiene_costo else "confirmada",
        )).fetchone()
    except UniqueViolation as error:
        raise HTTPException(409, "El espacio ya está reservado para ese horario.") from error
    reserva["espacio"] = espacio["nombre"]
    pago = None
    if tiene_costo:
        pago = pago_orden(crear_orden(conn, codigo, "reserva", str(reserva["id"])))
        reserva["order_id"] = pago["orderId"]
    return {"reserva": datos_reserva(reserva), "pago": pago}
