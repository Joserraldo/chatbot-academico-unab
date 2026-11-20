"""Pruebas contra la semilla v2 real (db/init 01-05) con el rol servicios_rw de producción."""
import psycopg
import pytest

from conftest import CLAVE

PERSONAS = [f"U0000020{n}" for n in range(1, 7)]


def enriquecer(cliente, codigo, mensaje, intencion="general"):
    r = cliente.post("/api/asistente/enriquecer", headers=CLAVE, json={
        "codigoEstudiante": codigo, "sessionId": "s", "mensaje": mensaje,
        "intencion": intencion, "respuesta": "x"})
    assert r.status_code == 200, r.text
    return r.json()


def test_rol_servicios_rw_solo_lee_academico(semilla):
    with psycopg.connect(semilla[1], autocommit=True) as conn:
        assert conn.execute("SELECT count(*) FROM academico.estudiante").fetchone()[0] >= 206
        assert conn.execute("SELECT count(*) FROM academico.chat_log").fetchone() is not None
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("UPDATE academico.matricula SET estado = 'matriculado'")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("INSERT INTO academico.docente (nombre, email) VALUES ('x', 'x')")


def test_personas_demo(cliente_semilla):
    personas = cliente_semilla.get("/api/demo/personas").json()
    codigos = [p["codigo"] for p in personas]
    assert set(PERSONAS) <= set(codigos)
    assert all(set(p) == {"codigo", "nombre", "programa", "titulo", "descripcion", "emoji"} for p in personas)


@pytest.mark.parametrize("codigo", PERSONAS)
def test_panel_hoy_de_cada_persona(cliente_semilla, codigo):
    panel = cliente_semilla.get(f"/api/hoy/{codigo}", headers=CLAVE).json()
    assert panel["estudiante"]["codigo"] == codigo
    assert isinstance(panel["horario_hoy"], list) and len(panel["noticias"]) > 0


def test_historias_de_las_personas(cliente_semilla):
    get = lambda c: cliente_semilla.get(f"/api/hoy/{c}", headers=CLAVE).json()
    assert get("U00000201")["estudiante"]["promedio"] >= 4.5
    assert len(get("U00000201")["evaluaciones"]) == 1
    riesgo = get("U00000202")
    assert sum(t["estado"] in ("vencida", "pendiente") for t in riesgo["tareas"]) >= 3
    assert get("U00000205")["estudiante"]["estado_matricula"] == "pendiente_pago"
    vencido, = [p for p in get("U00000206")["prestamos"] if p["estado"] == "vencido"]
    assert vencido["multa"] > 0


@pytest.mark.parametrize("tipo", ["notas_semestre", "avance", "creditos_area", "parciales", "cohorte"])
def test_graficas_semilla(cliente_semilla, tipo):
    g = cliente_semilla.get(f"/api/graficas/U00000201?tipo={tipo}", headers=CLAVE).json()
    assert g["id"] == tipo and g["labels"] and all(len(s["datos"]) == len(g["labels"]) for s in g["series"])


def test_grafica_riesgo_con_o_sin_modelo(cliente_semilla):
    r = cliente_semilla.get("/api/graficas/U00000202?tipo=riesgo", headers=CLAVE)
    assert r.status_code in (200, 404)
    assert cliente_semilla.get("/api/graficas/U00000202?tipo=inventada", headers=CLAVE).status_code == 422


def test_pago_matricula_u205_simulado(cliente_semilla):
    h = CLAVE
    orden = cliente_semilla.post("/api/pagos/orden", headers=h, json={
        "codigoEstudiante": "U00000205", "concepto": "matricula"}).json()
    assert orden["monto"] == 8_500_000 and orden["simulado"] and orden["bold"] is None
    assert orden["orderId"].startswith("UNAB-MAT-")
    otra = cliente_semilla.post("/api/pagos/orden", headers=h, json={
        "codigoEstudiante": "U00000205", "concepto": "matricula"}).json()
    assert otra["orderId"] == orden["orderId"]          # reutiliza la pendiente
    assert cliente_semilla.get(f"/api/pagos/{orden['orderId']}").json()["estado"] == "pendiente"
    aprobada = cliente_semilla.post(f"/api/pagos/{orden['orderId']}/simular", json={"resultado": "aprobado"}).json()
    assert aprobada["estado"] == "aprobado"
    assert cliente_semilla.get("/api/hoy/U00000205", headers=h).json()["estudiante"]["estado_matricula"] == "pagada"
    assert enriquecer(cliente_semilla, "U00000205", "quiero pagar mi matrícula")["acciones"] == []


def test_enriquecer_matricula_u205(cliente_semilla):
    acciones = enriquecer(cliente_semilla, "U00000205", "quiero pagar mi matrícula")["acciones"]
    assert [a["tipo"] for a in acciones] == ["pago"]
    assert acciones[0]["monto"] == 8_500_000 and acciones[0]["concepto"] == "matricula"
    assert acciones[0]["url"] == f"/app/pagar.html?order={acciones[0]['orderId']}"


def test_multa_y_renovacion_u206(cliente_semilla):
    orden = cliente_semilla.post("/api/pagos/orden", headers=CLAVE, json={
        "codigoEstudiante": "U00000206", "concepto": "multa_biblioteca"}).json()
    assert orden["monto"] == 22_500 and orden["orderId"].startswith("UNAB-BIB-")
    acciones = enriquecer(cliente_semilla, "U00000206", "cómo renuevo un libro", "tramites")["acciones"]
    assert [a["tipo"] for a in acciones] == ["enlace", "qr", "pago"]
    assert acciones[0]["url"] == "https://catalogo.unab.edu.co/"
    assert acciones[2]["orderId"] == orden["orderId"]


def test_reserva_de_pago_en_semilla(cliente_semilla):
    espacios = cliente_semilla.get("/api/espacios", headers=CLAVE).json()
    assert len(espacios) == 10 and any(e["tarifa_hora"] == 0 for e in espacios)
    gratis = next(e for e in espacios if e["tarifa_hora"] == 0)
    pago = next(e for e in espacios if e["tarifa_hora"] > 0)
    cuerpo = {"codigoEstudiante": "U00000201", "fecha": "2030-03-04", "horaInicio": "10:00", "horas": 2}
    r = cliente_semilla.post("/api/reservas", headers=CLAVE, json={**cuerpo, "espacio": gratis["codigo"]}).json()
    assert r["reserva"]["estado"] == "confirmada" and r["pago"] is None
    r = cliente_semilla.post("/api/reservas", headers=CLAVE, json={**cuerpo, "espacio": pago["codigo"]}).json()
    assert r["reserva"]["estado"] == "pendiente_pago" and r["pago"]["monto"] == 2 * pago["tarifa_hora"]
    cliente_semilla.post(f"/api/pagos/{r['pago']['orderId']}/simular", json={"resultado": "aprobado"})
    estado = [x for x in cliente_semilla.get("/api/hoy/U00000201", headers=CLAVE).json()["reservas"]
              if x["id"] == r["reserva"]["id"]][0]["estado"]
    assert estado == "confirmada"


def test_analitica_y_tramites_semilla(cliente_semilla):
    r = cliente_semilla.get("/api/analitica/resumen", headers=CLAVE).json()
    assert set(r) == {"intenciones", "bloqueos", "por_dia", "riesgo", "modelo", "totales"}
    codigos = {t["codigo"] for t in cliente_semilla.get("/api/tramites", headers=CLAVE).json()}
    assert {"reservas", "biblioteca_renovar", "gimnasio", "cosmos", "tema", "evaluacion_docente", "unab"} <= codigos
    assert len(cliente_semilla.get("/api/noticias/hoy").json()) >= 1
