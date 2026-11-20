import logging
import re
from urllib.parse import urlencode

from fastapi import HTTPException

from .academico import normalizar
from .bold import accion_pago, crear_orden
from .db import estudiante_id
from .graficas import grafica
from .reservas import CONSULTA_RESERVA, datos_reserva

REGISTRO = logging.getLogger(__name__)


def adjuntar_enlace(conn, acciones, codigo, *, qr=False):
    enlace = conn.execute("""
        SELECT nombre, descripcion, url FROM academico.enlace_tramite WHERE codigo = %s
    """, (codigo,)).fetchone()
    if enlace:
        acciones.append({
            "tipo": "enlace", "titulo": enlace["nombre"],
            "url": enlace["url"], "descripcion": enlace["descripcion"],
        })
        if qr:
            acciones.append({
                "tipo": "qr", "titulo": enlace["nombre"], "url": enlace["url"],
                "imagen": "/api/qr?" + urlencode({"url": enlace["url"]}),
            })


def adjuntar_pago(conn, acciones, codigo, concepto):
    try:
        acciones.append(accion_pago(crear_orden(conn, codigo, concepto)))
    except HTTPException as error:
        if error.status_code not in (409, 422):
            raise


def elegir_graficas(mensaje, intencion):
    if not (re.search(r"grafic|visualiz|diagrama|chart", mensaje) or (
        intencion == "historial" and re.search(r"nota|promedio|avance|credito|riesgo|parcial|corte|compar", mensaje)
    )):
        return []
    reglas = (
        (r"compar|cohorte", "cohorte"),
        (r"parcial|corte", "parciales"),
        (r"riesgo", "riesgo"),
        (r"promedio|nota", "notas_semestre"),
        (r"avance|credito|semestre", "avance"),
    )
    return [tipo for patron, tipo in reglas if re.search(patron, mensaje)] or ["notas_semestre"]


def limitar_acciones(acciones):
    unicas = {}
    for accion in acciones:
        tipo = accion["tipo"]
        identidad = accion.get("orderId") if tipo == "pago" else accion.get("url", accion.get("id"))
        unicas.setdefault((tipo, identidad), accion)
    claves = sorted(unicas, key=lambda clave: clave[0] not in ("reserva", "pago"))[:4]
    return [accion for clave, accion in unicas.items() if clave in claves]


def enriquecer(conn, peticion):
    codigo = peticion.codigoEstudiante
    mensaje = normalizar(peticion.mensaje)
    intencion = normalizar(peticion.intencion)
    if intencion == "bloqueado":
        return {"acciones": [], "graficas": []}

    alumno_id = estudiante_id(conn, codigo)
    acciones = []
    reserva = None
    if re.search(r"reserv|apartar|espacio|auditorio|sala|cancha|gimnasio", mensaje):
        reserva = conn.execute(CONSULTA_RESERVA + """
            WHERE r.codigo_estudiante = %s AND r.estado <> 'cancelada'
              AND r.creado_en > now() - INTERVAL '5 minutes'
            ORDER BY r.creado_en DESC, r.id DESC LIMIT 1
        """, (codigo,)).fetchone()
        if reserva:
            acciones.append({"tipo": "reserva", **datos_reserva(reserva)})
        else:
            adjuntar_enlace(conn, acciones, "gimnasio" if "gimnasio" in mensaje else "reservas", qr=True)
            acciones.append({"tipo": "sugerencias", "opciones": [
                "Reservar una sala de estudio mañana a las 10", "¿Qué espacios hay disponibles?",
            ]})

    if re.search(r"(pagar|pago|abonar).*matricula|matricula.*(pagar|pago)", mensaje) or (
        intencion == "historial" and "matricula" in mensaje
    ):
        adjuntar_pago(conn, acciones, codigo, "matricula")

    if re.search(r"biblioteca|libro|prestamo|renovar", mensaje):
        adjuntar_enlace(conn, acciones, "biblioteca_renovar", qr=True)
        adjuntar_pago(conn, acciones, codigo, "multa_biblioteca")

    for patron, tramite in (
        (r"cosmos", "cosmos"),
        (r"\btema\b|moodle|tarea|quiz", "tema"),
        (r"calific.*(profe|docente)|evaluacion docente", "evaluacion_docente"),
    ):
        if re.search(patron, mensaje):
            adjuntar_enlace(conn, acciones, tramite)

    graficas = []
    for tipo in elegir_graficas(mensaje, intencion):
        try:
            graficas.append(grafica(conn, codigo, tipo, alumno_id))
        except HTTPException as error:
            if error.status_code != 404:
                raise
        if len(graficas) == 2:
            break

    reservas_order_id = reserva["order_id"] if reserva else None
    pagos = conn.execute("""
        SELECT * FROM servicios.pago_orden
        WHERE codigo_estudiante = %s AND estado = 'pendiente'
          AND (creado_en > now() - INTERVAL '5 minutes' OR order_id = %s)
        ORDER BY (order_id IS NOT DISTINCT FROM %s) DESC, creado_en DESC, order_id
        LIMIT 4
    """, (codigo, reservas_order_id, reservas_order_id)).fetchall()
    acciones.extend(map(accion_pago, pagos))
    return {"acciones": limitar_acciones(acciones), "graficas": graficas}
