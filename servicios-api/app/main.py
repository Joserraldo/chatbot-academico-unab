import hmac
import io
import json
import logging
import os
import re
from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated, Literal
from urllib.parse import urlsplit

import qrcode
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Path, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from PIL import Image
from psycopg import Error
from psycopg_pool import PoolTimeout
from pydantic import BaseModel, BeforeValidator, Field, StringConstraints

from .academico import analitica, noticias, panel_hoy
from .bold import (
    actualizar_estado, bold_configurado, buscar_orden, consultar_bold, crear_orden,
    pago_orden, registrar_evento, verificar_webhook,
)
from .db import crear_pool, pool_db
from .enriquecer import enriquecer
from .graficas import grafica
from .reservas import disponibilidad, reservar
from .vision import MAX_DATA_URL, analizar_imagen, vision_configurada

REGISTRO = logging.getLogger(__name__)
CODIGO = r"^U[0-9]{8}$"
Codigo = Annotated[str, StringConstraints(pattern=CODIGO)]
CodigoRuta = Annotated[str, Path(pattern=CODIGO)]
OrderId = Annotated[str, Path(pattern=r"^UNAB-(MAT|RES|BIB)-[0-9a-f]{12}$")]
Pool = Annotated[object, Depends(pool_db)]


def validar_fecha(valor):
    if isinstance(valor, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", valor):
        return valor
    raise ValueError("Usa una fecha YYYY-MM-DD.")


Fecha = Annotated[date, BeforeValidator(validar_fecha)]


class OrdenEntrada(BaseModel):
    codigoEstudiante: Codigo
    concepto: Literal["matricula", "reserva", "multa_biblioteca"]
    referencia: Annotated[str, Field(max_length=100)] | None = None


class ReservaEntrada(BaseModel):
    codigoEstudiante: Codigo
    espacio: Annotated[str, Field(min_length=1, max_length=100)]
    fecha: Fecha
    horaInicio: Annotated[str, Field(pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")]
    horas: Annotated[int, Field(strict=True, ge=1, le=4)]


class SimulacionEntrada(BaseModel):
    resultado: Literal["aprobado", "rechazado"]


class VisionEntrada(BaseModel):
    codigoEstudiante: Codigo
    mensaje: Annotated[str, Field(max_length=4000)]
    imagen: Annotated[str, Field(max_length=MAX_DATA_URL)]


class AsistenteEntrada(BaseModel):
    codigoEstudiante: Codigo
    sessionId: Annotated[str, Field(max_length=250)]
    mensaje: Annotated[str, Field(max_length=4000)]
    intencion: Annotated[str, Field(max_length=50)]
    respuesta: Annotated[str, Field(max_length=20_000)]


class LimiteCuerpo:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST":
            return await self.app(scope, receive, send)
        path = scope["path"].rstrip("/")
        limite = MAX_DATA_URL + 32_768 if path == "/api/vision" else 256 * 1024
        cuerpo = bytearray()
        while True:
            mensaje = await receive()
            if mensaje["type"] == "http.disconnect":
                return
            parte = mensaje.get("body", b"")
            if len(cuerpo) + len(parte) > limite:
                respuesta = JSONResponse(
                    {"detail": "El cuerpo de la petición supera el tamaño permitido."}, 413
                )
                return await respuesta(scope, receive, send)
            cuerpo.extend(parte)
            if not mensaje.get("more_body"):
                break

        enviado = False

        async def releer():
            nonlocal enviado
            if enviado:
                return await receive()
            enviado = True
            return {"type": "http.request", "body": bytes(cuerpo), "more_body": False}

        await self.app(scope, releer, send)


def autenticar(request: Request):
    recibida = request.headers.get("X-Chatbot-Key")
    if not recibida:
        raise HTTPException(401, "Falta el encabezado X-Chatbot-Key.")
    esperada = os.getenv("CHATBOT_KEY", "")
    if not esperada or not hmac.compare_digest(recibida.encode(), esperada.encode()):
        raise HTTPException(403, "La clave del chatbot no es válida.")


@asynccontextmanager
async def vida(app):
    pool = crear_pool()
    app.state.pool = pool
    if pool is not None:
        pool.open()
    try:
        yield
    finally:
        if pool is not None:
            pool.close()


app = FastAPI(
    title="Asistente UNAB 360", lifespan=vida, docs_url=None, redoc_url=None, openapi_url=None
)
app.add_middleware(LimiteCuerpo)
publica = APIRouter(prefix="/api")
privada = APIRouter(prefix="/api", dependencies=[Depends(autenticar)])


@app.exception_handler(RequestValidationError)
async def error_validacion(request, error):
    lugar = error.errors()[0]["loc"]
    campo = lugar[1] if len(lugar) > 1 and isinstance(lugar[1], str) else None
    mensaje = f"El campo «{campo}» falta o no es válido." if campo else "La petición no es válida."
    return JSONResponse({"detail": mensaje}, status_code=422)


@app.exception_handler(Error)
@app.exception_handler(PoolTimeout)
async def error_base_datos(request, error):
    REGISTRO.warning("Fallo de base de datos: %s", type(error).__name__)
    return JSONResponse({"detail": "La base de datos no está disponible."}, status_code=503)


@app.exception_handler(Exception)
async def error_interno(request, error):
    return JSONResponse({"detail": "No fue posible completar la solicitud."}, status_code=500)


@publica.get("/health")
def salud():
    return {"ok": True, "bold": bold_configurado(), "vision": vision_configurada()}


@publica.get("/demo/personas")
def personas(pool: Pool):
    with pool.connection() as conn:
        return conn.execute("""
            SELECT pd.codigo, e.nombres || ' ' || e.apellidos AS nombre, p.nombre AS programa,
                   pd.titulo, pd.descripcion, pd.emoji
            FROM academico.persona_demo pd
            JOIN academico.estudiante e ON e.codigo = pd.codigo
            JOIN academico.programa p ON p.id = e.programa_id
            ORDER BY pd.orden, pd.codigo
        """).fetchall()


@privada.get("/hoy/{codigo}")
def hoy(codigo: CodigoRuta, pool: Pool):
    with pool.connection() as conn:
        return panel_hoy(conn, codigo)


@privada.get("/graficas/{codigo}")
def obtener_grafica(
    codigo: CodigoRuta, pool: Pool,
    tipo: Literal["notas_semestre", "avance", "creditos_area", "parciales", "riesgo", "cohorte"],
):
    with pool.connection() as conn:
        return grafica(conn, codigo, tipo)


@privada.get("/espacios")
def espacios(pool: Pool, tipo: Annotated[str | None, Query(max_length=30)] = None):
    with pool.connection() as conn:
        return conn.execute("""
            SELECT * FROM servicios.espacio WHERE (%s::text IS NULL OR tipo = %s)
            ORDER BY nombre, codigo
        """, (tipo, tipo)).fetchall()


@privada.get("/espacios/{codigo}/disponibilidad")
def consultar_disponibilidad(codigo: Annotated[str, Path(max_length=100)], fecha: Fecha, pool: Pool):
    with pool.connection() as conn:
        return disponibilidad(conn, codigo, fecha)


@privada.post("/reservas")
def crear_reserva(peticion: ReservaEntrada, pool: Pool):
    with pool.connection() as conn:
        return reservar(conn, peticion)


@privada.post("/pagos/orden")
def nueva_orden(peticion: OrdenEntrada, pool: Pool):
    with pool.connection() as conn:
        return pago_orden(crear_orden(conn, peticion.codigoEstudiante, peticion.concepto, peticion.referencia))


@publica.get("/pagos/{orderId}")
def obtener_orden(orderId: OrderId, pool: Pool):
    with pool.connection() as conn:
        orden = buscar_orden(conn, orderId)
    if orden["estado"] == "pendiente" and orden["proveedor"] == "bold" and bold_configurado():
        estado = consultar_bold(orderId)
        if estado:
            with pool.connection() as conn:
                orden = actualizar_estado(conn, orden, estado)
    return pago_orden(orden)


@publica.post("/pagos/{orderId}/simular")
def simular_orden(orderId: OrderId, peticion: SimulacionEntrada, pool: Pool):
    if os.getenv("PAGOS_PERMITIR_SIMULADO", "true").lower() != "true":
        raise HTTPException(403, "Los pagos simulados están deshabilitados.")
    with pool.connection() as conn:
        orden = buscar_orden(conn, orderId)
        if orden["proveedor"] != "simulado":
            raise HTTPException(409, "La orden debe confirmarse con Bold.")
        return pago_orden(actualizar_estado(conn, orden, peticion.resultado))


async def cuerpo_webhook(request: Request):
    cuerpo = await request.body()
    if not verificar_webhook(cuerpo, request.headers.get("x-bold-signature")):
        raise HTTPException(401, "La firma de Bold no es válida.")
    return cuerpo


@publica.post("/pagos/bold/webhook")
def webhook(cuerpo: Annotated[bytes, Depends(cuerpo_webhook)], pool: Pool):
    try:
        payload = json.loads(cuerpo)
    except (ValueError, RecursionError) as error:
        raise HTTPException(422, "El cuerpo del evento de Bold no es JSON válido.") from error
    identificador = payload.get("id") if isinstance(payload, dict) else None
    if not isinstance(identificador, str) or not identificador.strip() or len(identificador) > 200:
        raise HTTPException(422, "Falta el identificador del evento de Bold.")
    with pool.connection() as conn:
        registrar_evento(conn, payload)
    return {"ok": True}


@publica.get("/qr")
def generar_qr(url: Annotated[str, Query(min_length=1, max_length=500)],
               tam: Annotated[int, Query(ge=64, le=1024)] = 224):
    try:
        destino = urlsplit(url)
        valido = destino.scheme in ("http", "https") and destino.hostname and not any(
            letra.isspace() or ord(letra) < 32 or ord(letra) == 127 for letra in url
        )
    except ValueError:
        valido = False
    if not valido:
        raise HTTPException(422, "Usa una URL válida que empiece por http:// o https://.")
    qr = qrcode.QRCode(box_size=1, border=4)
    qr.add_data(url)
    imagen = qr.make_image().get_image()
    escala = tam // imagen.width
    if escala == 0:
        raise HTTPException(422, "El tamaño solicitado es muy pequeño para este enlace.")
    ancho = imagen.width * escala
    codigo = imagen.resize((ancho, ancho), Image.Resampling.NEAREST)
    lienzo = Image.new("1", (tam, tam), 1)
    lienzo.paste(codigo, ((tam - ancho) // 2, (tam - ancho) // 2))
    salida = io.BytesIO()
    lienzo.save(salida, format="PNG")
    return Response(salida.getvalue(), media_type="image/png")


@privada.post("/vision")
def vision(peticion: VisionEntrada, request: Request):
    return analizar_imagen(peticion, request.app.state.pool)


@privada.post("/asistente/enriquecer")
def asistente(peticion: AsistenteEntrada, request: Request):
    try:
        with pool_db(request).connection() as conn:
            return enriquecer(conn, peticion)
    except Exception as error:
        REGISTRO.warning("No se pudo enriquecer la respuesta: %s", type(error).__name__)
        return {"acciones": [], "graficas": []}


@publica.get("/noticias/hoy")
def noticias_hoy(pool: Pool, limite: Annotated[int, Query(ge=1, le=100)] = 10):
    with pool.connection() as conn:
        return noticias(conn, limite)


@privada.get("/tramites")
def tramites(pool: Pool):
    with pool.connection() as conn:
        return conn.execute("SELECT * FROM academico.enlace_tramite ORDER BY codigo").fetchall()


@privada.get("/analitica/resumen")
def resumen(pool: Pool):
    with pool.connection() as conn:
        return analitica(conn)


app.include_router(publica)
app.include_router(privada)
