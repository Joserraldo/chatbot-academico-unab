import json
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from app.bold import firma_integridad, firma_webhook, verificar_webhook
from conftest import CLAVE, CODIGO, OTRO

RESERVA = {"codigoEstudiante": CODIGO, "espacio": "PRUEBA-AUD", "fecha": "2099-11-22",
           "horaInicio": "10:00", "horas": 2}


def pedir_orden(cliente, concepto, **campos):
    return cliente.post("/api/pagos/orden", headers=CLAVE, json={
        "codigoEstudiante": CODIGO, "concepto": concepto, **campos,
    })


def activar_bold(monkeypatch):
    monkeypatch.setenv("BOLD_API_KEY", "identidad-sintetica")
    monkeypatch.setenv("BOLD_SECRET_KEY", "secreto-sintetico")


def test_vectores_firmas(monkeypatch):
    assert firma_integridad("UNAB-MAT-ab12cd34ef56", 9850000, "COP", "secreto-sintetico") == (
        "ce8aba24455a462586a527ff609ef6bb4385c152ea9447e56191e940eb8aaea9"
    )
    monkeypatch.setenv("BOLD_WEBHOOK_SECRET", "clave-sintetica")
    assert verificar_webhook(b"{}", "93d9360a9d3350c684d9a6bbdc818da3e14dbd42de2d8b955379da39184a3830")
    assert not verificar_webhook(b"{ }", firma_webhook(b"{}", "clave-sintetica"))
    assert not verificar_webhook(b"{}", "ñ")
    monkeypatch.setenv("BOLD_WEBHOOK_SECRET", "")
    firma_vacia = "c69083828b2eb5e9c13ae672b897d30f8e7f2c2b96e95bf5cb7cb5a8191656ea"
    monkeypatch.setenv("BOLD_MODO", "pruebas")
    assert verificar_webhook(b"{}", firma_vacia)
    monkeypatch.setenv("BOLD_MODO", "produccion")
    assert not verificar_webhook(b"{}", firma_vacia)


def test_montos_y_matricula_solo_lectura(cliente, admin, monkeypatch):
    orden = pedir_orden(cliente, "matricula", monto=1).json()
    assert orden["monto"] == 9850000
    assert orden["bold"] is None and orden["simulado"]
    assert pedir_orden(cliente, "matricula", referencia="2099-1").json() == orden
    multa = pedir_orden(cliente, "multa_biblioteca").json()
    assert multa["monto"] == 3200
    url = f"/api/pagos/{orden['orderId']}"
    assert cliente.get(url).json() == orden
    monkeypatch.setenv("PAGOS_PERMITIR_SIMULADO", "false")
    assert cliente.post(f"{url}/simular", json={"resultado": "aprobado"}).status_code == 403
    monkeypatch.setenv("PAGOS_PERMITIR_SIMULADO", "true")
    assert cliente.post(f"{url}/simular", json={"resultado": "aprobado"}).json()["estado"] == "aprobado"
    assert cliente.post(f"{url}/simular", json={"resultado": "rechazado"}).json()["estado"] == "aprobado"
    assert pedir_orden(cliente, "matricula").status_code == 409
    hoy = cliente.get(f"/api/hoy/{CODIGO}", headers=CLAVE).json()
    assert hoy["estudiante"]["estado_matricula"] == "pagada"
    assert hoy["pagos_pendientes"] == [multa]
    assert admin.execute("""
        SELECT estado FROM academico.matricula WHERE estudiante_id = 900001 AND periodo_id = 900002
    """).fetchone() == ("pendiente_pago",)


def test_reserva_monto_choque_y_confirmacion(cliente):
    espacios = cliente.get("/api/espacios", params={"tipo": "auditorio"}, headers=CLAVE)
    assert any(e["codigo"] == "PRUEBA-AUD" for e in espacios.json())
    respuesta = cliente.post("/api/reservas", json=RESERVA, headers=CLAVE)
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    reserva, pago = datos["reserva"], datos["pago"]
    assert reserva["estado"] == "pendiente_pago" and reserva["orderId"] == pago["orderId"]
    assert pago["monto"] == 36000 == pedir_orden(cliente, "reserva", referencia=str(reserva["id"])).json()["monto"]
    ajena = pedir_orden(cliente, "reserva", referencia=str(reserva["id"]), codigoEstudiante=OTRO)
    assert ajena.status_code == 422
    for hora in ("09:30", "10:00", "11:00"):
        choque = cliente.post("/api/reservas", headers=CLAVE, json={
            **RESERVA, "codigoEstudiante": OTRO, "horaInicio": hora, "horas": 1,
        })
        assert choque.status_code == 409
    disponibilidad = cliente.get("/api/espacios/PRUEBA-AUD/disponibilidad", headers=CLAVE,
                                 params={"fecha": RESERVA["fecha"]}).json()
    franjas = disponibilidad["franjas"]
    assert len(franjas) == 14
    assert franjas[0] == {"horaInicio": "07:00", "horaFin": "08:00", "libre": True}
    assert franjas[-1]["horaFin"] == "21:00"
    assert [f["horaInicio"] for f in franjas if not f["libre"]] == ["10:00", "11:00"]
    cliente.post(f"/api/pagos/{pago['orderId']}/simular", json={"resultado": "aprobado"})
    assert cliente.get(f"/api/hoy/{CODIGO}", headers=CLAVE).json()["reservas"][0]["estado"] == "confirmada"
    gratis = cliente.post("/api/reservas", json={**RESERVA, "espacio": "PRUEBA-SALA"}, headers=CLAVE).json()
    assert gratis["pago"] is None and gratis["reserva"]["estado"] == "confirmada"


def test_concurrencia(cliente):
    with ThreadPoolExecutor(max_workers=4) as hilos:
        ordenes = list(hilos.map(lambda _: pedir_orden(cliente, "matricula").json(), range(4)))
        assert len({orden["orderId"] for orden in ordenes}) == 1
        peticiones = (RESERVA, {**RESERVA, "codigoEstudiante": OTRO, "horaInicio": "11:00"})
        respuestas = list(hilos.map(lambda p: cliente.post("/api/reservas", json=p, headers=CLAVE), peticiones))
    assert sorted(respuesta.status_code for respuesta in respuestas) == [200, 409]


def test_webhook_idempotente(cliente, admin, monkeypatch):
    activar_bold(monkeypatch)
    reserva = cliente.post("/api/reservas", json=RESERVA, headers=CLAVE).json()
    orden = reserva["pago"]
    assert orden["proveedor"] == "bold" and not orden["simulado"]
    assert orden["bold"] == {
        "apiKey": "identidad-sintetica",
        "integritySignature": firma_integridad(orden["orderId"], 36000, "COP", "secreto-sintetico"),
        "amount": "36000", "currency": "COP", "orderId": orden["orderId"],
        "description": "Reserva de Auditorio de prueba",
        "redirectionUrl": f"https://demo.example/app/pagar.html?order={orden['orderId']}",
    }
    evento = {
        "id": "prueba-api-id-unico", "type": "SALE_APPROVED",
        "data": {"payment_id": "pago-sintetico", "payment_method": "PSE",
                 "metadata": {"reference": orden["orderId"]}},
    }

    def notificar(payload, secreto=""):
        cuerpo = json.dumps(payload, indent=2).encode()
        return cliente.post("/api/pagos/bold/webhook", content=cuerpo, headers={
            "x-bold-signature": firma_webhook(cuerpo, secreto),
        })

    assert notificar(evento, "otra-clave").status_code == 401
    assert notificar(evento).json() == {"ok": True}
    assert notificar({**evento, "type": "VOID_APPROVED"}).json() == {"ok": True}
    assert admin.execute("SELECT count(*) FROM servicios.bold_evento WHERE id = %s", (evento["id"],)).fetchone() == (1,)
    assert admin.execute("""
        SELECT estado, bold_payment_id, metodo FROM servicios.pago_orden WHERE order_id = %s
    """, (orden["orderId"],)).fetchone() == ("aprobado", "pago-sintetico", "PSE")
    assert cliente.get(f"/api/hoy/{CODIGO}", headers=CLAVE).json()["reservas"][0]["estado"] == "confirmada"
    monkeypatch.setenv("BOLD_WEBHOOK_SECRET", "webhook-sintetico")
    anulacion = {**evento, "id": "prueba-api-anulacion", "type": "VOID_APPROVED"}
    assert notificar(anulacion).status_code == 401
    assert notificar(anulacion, "webhook-sintetico").status_code == 200
    assert admin.execute("SELECT estado FROM servicios.pago_orden WHERE order_id = %s", (orden["orderId"],)).fetchone() == ("anulado",)


@pytest.mark.parametrize(("remoto", "local"), [
    ("APPROVED", "aprobado"), ("REJECTED", "rechazado"), ("FAILED", "fallido"),
    ("VOIDED", "anulado"), ("PROCESSING", "pendiente"), (None, "pendiente"),
])
def test_consulta_bold(cliente, monkeypatch, remoto, local):
    activar_bold(monkeypatch)
    orden = pedir_orden(cliente, "matricula").json()

    def consultar(url, *, headers, timeout):
        assert url == f"https://payments.api.bold.co/v2/payment-voucher/{orden['orderId']}"
        assert headers == {"Authorization": "x-api-key identidad-sintetica"} and timeout == 5
        if remoto is None:
            raise httpx.ReadTimeout("Espera agotada")
        return httpx.Response(200, json={"payment_status": remoto}, request=httpx.Request("GET", url))

    monkeypatch.setattr("app.bold.httpx.get", consultar)
    respuesta = cliente.get(f"/api/pagos/{orden['orderId']}")
    assert respuesta.status_code == 200 and respuesta.json()["estado"] == local
