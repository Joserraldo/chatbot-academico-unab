import base64
import io
from datetime import date
from time import perf_counter

import httpx
import pytest
import qrcode
from PIL import Image

from app import academico
from app.vision import MAX_BYTES, cargar_imagen, leer_qr
from conftest import CLAVE, CODIGO, OTRO
from test_pagos import RESERVA, pedir_orden


def enriquecer(cliente, mensaje, *, intencion="tramites", codigo=CODIGO):
    respuesta = cliente.post("/api/asistente/enriquecer", headers=CLAVE, json={
        "codigoEstudiante": codigo, "sessionId": "sesion-pruebas",
        "mensaje": mensaje, "intencion": intencion, "respuesta": "Respuesta sintética.",
    })
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def test_auth_y_validacion(cliente):
    assert cliente.get("/api/health").json() == {"ok": True, "bold": False, "vision": False}
    assert cliente.get("/api/tramites").status_code == 401
    assert cliente.get("/api/tramites", headers={"X-Chatbot-Key": "incorrecta"}).status_code == 403
    assert cliente.get("/api/tramites", headers=CLAVE).status_code == 200
    assert cliente.get("/api/hoy/Uabcdef99", headers=CLAVE).status_code == 422
    assert cliente.get("/api/hoy/U99999999", headers=CLAVE).status_code == 404
    assert cliente.post("/api/reservas", headers=CLAVE, json={**RESERVA, "horas": 5}).status_code == 422
    assert cliente.post("/api/reservas", headers=CLAVE, json={**RESERVA, "fecha": "2099-2-5"}).status_code == 422
    assert cliente.post("/api/reservas", headers=CLAVE, content=b"x" * (256 * 1024 + 1)).status_code == 413
    respuesta = cliente.get("/api/demo/personas")
    assert respuesta.status_code == 200
    assert respuesta.json()[0] == {
        "codigo": CODIGO, "nombre": "Luz Sintética", "programa": "Programa sintético",
        "titulo": "Persona de pruebas", "descripcion": "Historia sintética", "emoji": "🎓",
    }


def test_panel_noticias_y_analitica(cliente, admin, monkeypatch):
    monkeypatch.setattr(academico, "hoy_bogota", lambda: date(2099, 11, 18))
    panel = cliente.get(f"/api/hoy/{CODIGO}", headers=CLAVE).json()
    assert set(panel) == {
        "estudiante", "tareas", "evaluaciones", "prestamos", "pagos_pendientes",
        "reservas", "horario_hoy", "noticias", "riesgo",
    }
    assert panel["estudiante"]["promedio"] == 3.2
    assert panel["tareas"][0]["estado"] == "pendiente"
    assert panel["evaluaciones"][0]["docente"] == "Docente de prueba"
    assert panel["horario_hoy"] == [
        {"curso": "Datos", "horario": "Mié 07:00-09:00", "salon": "A1", "docente": "Docente de prueba"}
    ]
    assert {p["estado"] for p in panel["prestamos"]} == {"activo", "vencido"}
    assert panel["riesgo"]["probabilidad"] == 0.75
    recientes = cliente.get("/api/noticias/hoy", params={"limite": 100}).json()
    assert any(n["titulo"] == "Noticia reciente sintética" for n in recientes)
    assert not any(n["titulo"] == "Noticia antigua sintética" for n in recientes)
    admin.execute("""
        UPDATE academico.noticia SET fecha_publicacion = current_date - 3
        WHERE titulo = 'Noticia reciente sintética'
    """)
    try:
        ultimas = cliente.get("/api/noticias/hoy", params={"limite": 100}).json()
        if not any(n["fuente"] != "Pruebas" and n["fecha_publicacion"] for n in ultimas):
            assert [n["titulo"] for n in ultimas] == ["Noticia reciente sintética", "Noticia antigua sintética"]
    finally:
        admin.execute("""
            UPDATE academico.noticia SET fecha_publicacion = current_date
            WHERE titulo = 'Noticia reciente sintética'
        """)
    resumen = cliente.get("/api/analitica/resumen", headers=CLAVE).json()
    assert {"motivo": "Motivo de prueba", "n": 1} in resumen["bloqueos"]
    assert {"dia": "2099-11-19", "n": 2} in resumen["por_dia"]
    assert resumen["modelo"]["auc"] == 0.85
    assert resumen["totales"]["estudiantes"] >= 1


@pytest.mark.parametrize(("tipo", "estilo", "labels", "datos"), [
    ("notas_semestre", "line", ["2099-1"], [[3.2]]),
    ("avance", "doughnut", ["Aprobados", "Cursando", "Pendientes"], [[3, 6, 3]]),
    ("creditos_area", "bar", ["Bases"], [[3]]),
    ("parciales", "bar", ["Datos"], [[3.5], [4.2], [None]]),
    ("riesgo", "bar", ["Nota baja"], [[0.25]]),
    ("cohorte", "line", ["2099-1", "2099-2"], [[3.2, None], [3.1, 5]]),
])
def test_graficas(cliente, tipo, estilo, labels, datos):
    respuesta = cliente.get(f"/api/graficas/{CODIGO}", headers=CLAVE, params={"tipo": tipo})
    assert respuesta.status_code == 200, respuesta.text
    grafica = respuesta.json()
    assert set(grafica) == {"id", "tipo", "titulo", "labels", "series", "unidad", "nota"}
    assert (grafica["id"], grafica["tipo"], grafica["labels"]) == (tipo, estilo, labels)
    assert [serie["datos"] for serie in grafica["series"]] == datos
    if tipo == "riesgo":
        assert cliente.get(f"/api/graficas/{OTRO}?tipo=riesgo", headers=CLAVE).status_code == 404


def test_enriquecer_reserva_y_gimnasio(cliente, admin):
    acciones = enriquecer(cliente, "¿Dónde puedo apartar una sala?")["acciones"]
    assert [a["tipo"] for a in acciones] == ["enlace", "qr", "sugerencias"]
    assert acciones[2]["opciones"] == [
        "Reservar una sala de estudio mañana a las 10", "¿Qué espacios hay disponibles?",
    ]
    assert enriquecer(cliente, "¿Dónde queda el gimnasio?")["acciones"][0]["url"] == "https://gimnasio.example.test/"
    reserva = cliente.post("/api/reservas", headers=CLAVE, json=RESERVA).json()
    admin.execute("UPDATE servicios.pago_orden SET creado_en = now() - interval '8 minutes' WHERE order_id = %s",
                  (reserva["pago"]["orderId"],))
    acciones = enriquecer(cliente, "Ya aparté el auditorio")["acciones"]
    assert acciones[0] == {"tipo": "reserva", **reserva["reserva"]}
    assert acciones[1]["orderId"] == reserva["pago"]["orderId"]
    assert len(acciones) == 2


def test_enriquecer_matricula_y_orden_reciente(cliente):
    accion, = enriquecer(cliente, "Quiero abonar la matrícula")["acciones"]
    assert accion["tipo"] == "pago" and accion["monto"] == 9850000
    assert enriquecer(cliente, "Mi matrícula", intencion="historial")["acciones"] == [accion]
    assert enriquecer(cliente, "Gracias")["acciones"] == [accion]
    assert enriquecer(cliente, "Pagar matrícula", intencion="bloqueado") == {"acciones": [], "graficas": []}
    cliente.post(f"/api/pagos/{accion['orderId']}/simular", json={"resultado": "aprobado"})
    assert enriquecer(cliente, "¿Cómo hago el pago de matrícula?")["acciones"] == []


def test_enriquecer_biblioteca_enlaces_graficas_y_limites(cliente):
    acciones = enriquecer(cliente, "Quiero renovar mi préstamo de biblioteca")["acciones"]
    assert [a["tipo"] for a in acciones] == ["enlace", "qr", "pago"]
    assert acciones[-1]["concepto"] == "multa_biblioteca" and acciones[-1]["monto"] == 3200
    assert acciones[1]["imagen"] == "/api/qr?url=https%3A%2F%2Fbiblioteca.example.test%2F"
    enlaces = enriquecer(cliente, "Cosmos, tareas y evaluación docente", codigo=OTRO)["acciones"]
    assert [e["titulo"] for e in enlaces] == ["Cosmos de prueba", "TEMA de prueba", "Evalúa a tu docente"]
    resultado = enriquecer(cliente, "Quiero un diagrama para comparar mi promedio, riesgo y avance")
    assert [g["id"] for g in resultado["graficas"]] == ["cohorte", "riesgo"]
    resultado = enriquecer(cliente, "Mis notas de corte y créditos", intencion="historial")
    assert [g["id"] for g in resultado["graficas"]] == ["parciales", "notas_semestre"]
    pedir_orden(cliente, "matricula")
    acciones = enriquecer(cliente, "Reservas, biblioteca, Cosmos, tareas y evaluación docente")["acciones"]
    assert len(acciones) == 4
    pagos = [a for a in acciones if a["tipo"] == "pago"]
    assert len(pagos) == len({p["orderId"] for p in pagos}) == 2


def test_enriquecer_degrada_sin_excepcion(cliente, monkeypatch):
    def fallar(request):
        raise RuntimeError("Fallo sintético")

    monkeypatch.setattr("app.main.pool_db", fallar)
    assert enriquecer(cliente, "Consulta de prueba") == {"acciones": [], "graficas": []}


def url_imagen(datos):
    return "data:image/png;base64," + base64.b64encode(datos).decode()


def test_png_y_vision(cliente, monkeypatch):
    url = "https://biblioteca.example.test/"
    respuesta = cliente.get("/api/qr", params={"url": url, "tam": 256})
    assert respuesta.status_code == 200 and respuesta.headers["content-type"] == "image/png"
    assert Image.open(io.BytesIO(respuesta.content)).size == (256, 256)
    assert leer_qr(cargar_imagen(url_imagen(respuesta.content))) == [url]
    assert cliente.get("/api/qr", params={"url": "file:///archivo"}).status_code == 422
    salida = io.BytesIO()
    qrcode.make(url).save(salida)
    imagen = url_imagen(salida.getvalue())
    assert cliente.post("/api/vision", headers=CLAVE, json={
        "codigoEstudiante": CODIGO, "mensaje": "", "imagen": "data:image/png;base64,AAAA",
    }).status_code == 422
    assert cliente.post("/api/vision", headers=CLAVE, json={
        "codigoEstudiante": CODIGO, "mensaje": "", "imagen": url_imagen(b"x" * (MAX_BYTES + 1)),
    }).status_code == 413
    monkeypatch.setenv("LLM_BASE_URL", "https://llm.example.test/v1/")
    monkeypatch.setenv("LLM_API_KEY", "llave-sintetica")
    monkeypatch.setenv("VISION_MODEL", "qwen-demo")

    def describir(url, *, json, headers, timeout):
        assert url == "https://llm.example.test/v1/chat/completions"
        assert json["model"] == "qwen-demo" and json["enable_thinking"] is False
        assert json["messages"][1]["content"] == [
            {"type": "text", "text": "Lee el cartel."},
            {"type": "image_url", "image_url": {"url": imagen}},
        ]
        assert headers == {"Authorization": "Bearer llave-sintetica"} and timeout == 45
        return httpx.Response(200, json={"choices": [{"message": {"content":
            'Resultado:\n```json\n{"descripcion":"Cartel sintético","texto":"Renueva aquí","tipo":"Cartel"}\n```'
        }}]}, request=httpx.Request("POST", url))

    monkeypatch.setattr("app.vision.httpx.post", describir)
    peticion = {"codigoEstudiante": CODIGO, "mensaje": "Lee el cartel.", "imagen": imagen}
    assert cliente.post("/api/vision", headers=CLAVE, json=peticion).json() == {
        "descripcion": "Cartel sintético El código QR corresponde a: Renueva tus préstamos.",
        "texto": "Renueva aquí", "tipo": "cartel", "qr": [url],
    }

    def fallar(*args, **kwargs):
        raise httpx.ReadTimeout("Espera agotada")

    monkeypatch.setattr("app.vision.httpx.post", fallar)
    respuesta = cliente.post("/api/vision", headers=CLAVE, json=peticion)
    assert respuesta.status_code == 200 and respuesta.json()["qr"] == [url]
    assert respuesta.json()["tipo"] == "otro" and respuesta.json()["texto"] == ""


def test_latencia_local(cliente):
    operaciones = {
        "gráficas": lambda: cliente.get(f"/api/graficas/{CODIGO}?tipo=cohorte", headers=CLAVE),
        "enriquecer": lambda: enriquecer(cliente, "Graficar mi promedio y riesgo", intencion="historial"),
    }
    for nombre, operacion in operaciones.items():
        operacion()
        medidas = []
        for _ in range(10):
            inicio = perf_counter()
            operacion()
            medidas.append(1000 * (perf_counter() - inicio))
        maximo = max(medidas)
        print(f"{nombre}: máximo local {maximo:.1f} ms")
        assert maximo < 300
