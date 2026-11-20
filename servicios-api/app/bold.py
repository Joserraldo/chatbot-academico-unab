import base64
import hashlib
import hmac
import os
import secrets

import httpx
from fastapi import HTTPException
from psycopg.types.json import Jsonb

from .db import bloquear_pagos

PREFIJOS = {"matricula": "MAT", "reserva": "RES", "multa_biblioteca": "BIB"}
ESTADOS_BOLD = {
    "APPROVED": "aprobado", "REJECTED": "rechazado",
    "FAILED": "fallido", "VOIDED": "anulado",
}
EVENTOS_BOLD = {
    "SALE_APPROVED": "aprobado", "SALE_REJECTED": "rechazado",
    "VOID_APPROVED": "anulado",
}


def bold_configurado():
    return bool(os.getenv("BOLD_API_KEY") and os.getenv("BOLD_SECRET_KEY"))


def firma_integridad(order_id, monto, moneda, secreto):
    return hashlib.sha256(f"{order_id}{monto}{moneda}{secreto}".encode()).hexdigest()


def firma_webhook(cuerpo, secreto):
    return hmac.new(secreto.encode(), base64.b64encode(cuerpo), "sha256").hexdigest()


def verificar_webhook(cuerpo, firma):
    secreto = os.getenv("BOLD_WEBHOOK_SECRET", "")
    if not secreto and os.getenv("BOLD_MODO", "pruebas") != "pruebas":
        return False
    return bool(firma) and hmac.compare_digest(
        firma_webhook(cuerpo, secreto).encode(), firma.encode()
    )


def ruta_pago(order_id):
    return f"/app/pagar.html?order={order_id}"


def pago_orden(fila):
    orden = {
        "orderId": fila["order_id"],
        "codigoEstudiante": fila["codigo_estudiante"],
        "concepto": fila["concepto"],
        "descripcion": fila["descripcion"],
        "monto": int(fila["monto"]),
        "moneda": fila["moneda"],
        "estado": fila["estado"],
        "proveedor": fila["proveedor"],
        "simulado": fila["proveedor"] == "simulado",
        "bold": None,
    }
    if orden["proveedor"] == "bold" and bold_configurado():
        orden["bold"] = {
            "apiKey": os.environ["BOLD_API_KEY"],
            "integritySignature": firma_integridad(
                orden["orderId"], orden["monto"], orden["moneda"], os.environ["BOLD_SECRET_KEY"]
            ),
            "amount": str(orden["monto"]),
            "currency": orden["moneda"],
            "orderId": orden["orderId"],
            "description": orden["descripcion"],
            "redirectionUrl": os.getenv("PUBLIC_BASE_URL", "").rstrip("/") + ruta_pago(orden["orderId"]),
        }
    return orden


def accion_pago(fila):
    return {
        "tipo": "pago", "orderId": fila["order_id"], "concepto": fila["concepto"],
        "descripcion": fila["descripcion"], "monto": int(fila["monto"]),
        "moneda": fila["moneda"], "estado": fila["estado"], "url": ruta_pago(fila["order_id"]),
    }


def crear_orden(conn, codigo, concepto, referencia=None):
    bloquear_pagos(conn, codigo)
    if concepto == "matricula":
        datos = conn.execute("""
            SELECT p.codigo AS referencia, m.valor AS monto,
                   'Matrícula ' || p.codigo AS descripcion
            FROM academico.matricula m
            JOIN academico.estudiante e ON e.id = m.estudiante_id
            JOIN academico.periodo p ON p.id = m.periodo_id
            WHERE e.codigo = %s AND p.actual AND m.estado = 'pendiente_pago'
            ORDER BY p.fecha_inicio DESC LIMIT 1
        """, (codigo,)).fetchone()
    elif concepto == "multa_biblioteca":
        datos = conn.execute("""
            SELECT string_agg(p.id::text, ',' ORDER BY p.id) AS referencia,
                   SUM(p.multa) AS monto, 'Multa de biblioteca' AS descripcion
            FROM academico.prestamo_biblioteca p
            JOIN academico.estudiante e ON e.id = p.estudiante_id
            WHERE e.codigo = %s AND p.estado = 'vencido' AND p.multa > 0
        """, (codigo,)).fetchone()
    else:
        datos = conn.execute("""
            SELECT r.id::text AS referencia,
                   EXTRACT(EPOCH FROM (r.hora_fin - r.hora_inicio)) / 3600 * e.tarifa_hora AS monto,
                   LEFT('Reserva de ' || e.nombre, 100) AS descripcion
            FROM servicios.reserva r JOIN servicios.espacio e ON e.id = r.espacio_id
            WHERE r.codigo_estudiante = %s AND r.id::text = %s AND r.estado = 'pendiente_pago'
        """, (codigo, referencia)).fetchone()

    if not datos or not datos["monto"] or datos["monto"] < 0:
        raise HTTPException(422, "No hay un saldo pendiente para este concepto.")
    existente = conn.execute("""
        SELECT * FROM servicios.pago_orden
        WHERE codigo_estudiante = %s AND concepto = %s AND referencia = %s
          AND estado IN ('aprobado', 'pendiente')
        ORDER BY (estado = 'aprobado') DESC, creado_en DESC, order_id LIMIT 1
    """, (codigo, concepto, datos["referencia"])).fetchone()
    if existente:
        if existente["estado"] == "aprobado":
            raise HTTPException(409, "Este concepto ya fue pagado.")
        return existente

    proveedor = "bold" if bold_configurado() else "simulado"
    if proveedor == "bold" and datos["monto"] < 1000:
        raise HTTPException(422, "El monto mínimo de Bold es de 1.000 COP.")
    orden = conn.execute("""
        INSERT INTO servicios.pago_orden
            (order_id, codigo_estudiante, concepto, referencia, descripcion, monto, proveedor)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING *
    """, (
        f"UNAB-{PREFIJOS[concepto]}-{secrets.token_hex(6)}", codigo, concepto,
        datos["referencia"], datos["descripcion"], datos["monto"], proveedor,
    )).fetchone()
    if concepto == "reserva":
        conn.execute(
            "UPDATE servicios.reserva SET order_id = %s WHERE id::text = %s",
            (orden["order_id"], datos["referencia"]),
        )
    return orden


def buscar_orden(conn, order_id):
    orden = conn.execute(
        "SELECT * FROM servicios.pago_orden WHERE order_id = %s", (order_id,)
    ).fetchone()
    if orden is None:
        raise HTTPException(404, "Orden de pago no encontrada.")
    return orden


def actualizar_estado(conn, orden, estado, *, payment_id=None, metodo=None):
    bloquear_pagos(conn, orden["codigo_estudiante"])
    orden = buscar_orden(conn, orden["order_id"])
    vigente = orden["estado"]
    if vigente != "pendiente" and (vigente != "aprobado" or estado != "anulado"):
        return orden
    orden = conn.execute("""
        UPDATE servicios.pago_orden
        SET estado = %s, bold_payment_id = COALESCE(%s, bold_payment_id),
            metodo = COALESCE(%s, metodo), actualizado_en = now()
        WHERE order_id = %s RETURNING *
    """, (estado, payment_id, metodo, orden["order_id"])).fetchone()
    if orden["concepto"] == "reserva" and estado in ("aprobado", "anulado"):
        anterior, nuevo = ("pendiente_pago", "confirmada") if estado == "aprobado" else (
            "confirmada", "pendiente_pago"
        )
        conn.execute("""
            UPDATE servicios.reserva SET estado = %s WHERE order_id = %s AND estado = %s
        """, (nuevo, orden["order_id"], anterior))
    return orden


def consultar_bold(order_id):
    try:
        respuesta = httpx.get(
            f"https://payments.api.bold.co/v2/payment-voucher/{order_id}",
            headers={"Authorization": f"x-api-key {os.environ['BOLD_API_KEY']}"},
            timeout=5,
        )
        respuesta.raise_for_status()
        datos = respuesta.json()
        if isinstance(datos, dict):
            estado = datos.get("payment_status")
            if isinstance(estado, str):
                return ESTADOS_BOLD.get(estado)
    except (httpx.HTTPError, ValueError):
        pass
    return None


def registrar_evento(conn, payload):
    datos = payload.get("data")
    if not isinstance(datos, dict):
        datos = {}
    metadata = datos.get("metadata")
    order_id = metadata.get("reference") if isinstance(metadata, dict) else None
    payment_id = datos.get("payment_id")
    metodo = datos.get("payment_method")
    tipo = payload.get("type")
    if not all(valor is None or isinstance(valor, str) for valor in (order_id, payment_id, metodo, tipo)):
        raise HTTPException(422, "Los datos del evento de Bold no son válidos.")
    nuevo = conn.execute("""
        INSERT INTO servicios.bold_evento (id, payment_id, tipo, order_id, payload)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING RETURNING id
    """, (payload["id"], payment_id, tipo, order_id, Jsonb(payload))).fetchone()
    if nuevo and order_id and tipo in EVENTOS_BOLD:
        orden = conn.execute("""
            SELECT * FROM servicios.pago_orden WHERE order_id = %s AND proveedor = 'bold'
        """, (order_id,)).fetchone()
        if orden:
            actualizar_estado(conn, orden, EVENTOS_BOLD[tipo], payment_id=payment_id, metodo=metodo)
