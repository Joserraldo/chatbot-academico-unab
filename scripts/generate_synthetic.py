"""
Generador de datos SINTÉTICOS para el Asistente Académico UNAB.

Entrada : data/plan_estudios_ing_sistemas.json  (plan real, extraído del PDF institucional)
Salidas : db/init/03_seed.sql                     (carga de la BD; corre sola en el primer arranque)
          data/calendario_academico.csv           (para importar en Google Sheets)
          data/docs_ccd/plan_de_estudios.md       (documento para el RAG)

Determinista (semilla fija): siempre produce lo mismo. Sin dependencias externas.
Uso:  python scripts/generate_synthetic.py [--estudiantes 200]
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
rng = random.Random(42)

NOMBRES = ["Santiago", "Valentina", "Sebastián", "Mariana", "Juan Pablo", "Daniela", "Andrés", "Laura",
           "Nicolás", "Camila", "Samuel", "Sofía", "Felipe", "Isabella", "Mateo", "Gabriela", "David",
           "Paula", "Alejandro", "Natalia", "Tomás", "María José", "Julián", "Juliana", "Diego", "Sara",
           "Esteban", "Manuela", "Carlos", "Ana María", "Miguel", "Luisa", "Daniel", "Valeria", "Óscar"]
APELLIDOS = ["Rodríguez", "Gómez", "Martínez", "Pérez", "Díaz", "Rueda", "Ardila", "Serrano", "Vargas",
             "Quintero", "Mantilla", "Gélvez", "Prada", "Sanabria", "Ortiz", "Castillo", "Reyes", "Duarte",
             "Pinzón", "Niño", "Jaimes", "Suárez", "Barrera", "Carreño", "Torres", "Rojas", "Galvis", "Meneses"]

# Prerrequisitos ILUSTRATIVOS (el PDF no los trae). Nombre curso -> nombres requeridos.
PRERREQ = {
    "Cálculo Integral": ["Cálculo Diferencial"],
    "Cálculo en varias Variables": ["Cálculo Integral"],
    "Ecuaciones Diferenciales": ["Cálculo Integral", "Álgebra Lineal"],
    "Mecánica y Laboratorio": ["Cálculo Diferencial"],
    "Electromagnetismo y Laboratorio": ["Mecánica y Laboratorio", "Cálculo Integral"],
    "Programación de Computadores": ["Fundamentos de Programación"],
    "Estructura de Datos y Análisis de Algoritmos": ["Programación de Computadores"],
    "Matemáticas Computacionales": ["Álgebra Lineal"],
    "Seminario de Ingeniería II": ["Seminario de Ingeniería I"],
    "Estadística General": ["Cálculo Integral"],
    "Bases de Datos I": ["Estructura de Datos y Análisis de Algoritmos"],
    "Inteligencia Artificial": ["Estructura de Datos y Análisis de Algoritmos", "Matemáticas Computacionales"],
    "Tecnologías Móviles": ["Programación de Computadores"],
    "Bases de Datos II": ["Bases de Datos I"],
    "Ingeniería de Software I": ["Bases de Datos I"],
    "Arquitectura de Software": ["Ingeniería de Software I"],
    "Ingeniería de Software II": ["Ingeniería de Software I"],
    "Ciencias de Datos": ["Estadística General", "Bases de Datos II"],
    "Internet de las Cosas": ["Infraestructura Tecnológica"],
    "Investigación de Operaciones I": ["Estadística General", "Álgebra Lineal"],
    "Investigación de Operaciones II": ["Investigación de Operaciones I"],
    "Dinámica de Sistemas": ["Ecuaciones Diferenciales", "Teoría de Sistemas y Organizaciones"],
    "Proyecto en Ing. de Sistemas II": ["Proyecto en Ing. de Sistemas I"],
    "Práctica en Ing. de Sistemas": ["Proyecto en Ing. de Sistemas II"],
}

CURSOS_CD = [  # catálogo SINTÉTICO del Centro de Competencias Digitales
    ("CD-B01", "Ofimática y productividad en la nube", "básico", 20, "virtual"),
    ("CD-B02", "Ciudadanía digital y seguridad básica", "básico", 16, "virtual"),
    ("CD-B03", "Búsqueda y gestión de información académica", "básico", 16, "virtual"),
    ("CD-B04", "Excel para análisis de datos", "básico", 24, "híbrido"),
    ("CD-I01", "Visualización de datos con Power BI", "intermedio", 30, "híbrido"),
    ("CD-I02", "Python para análisis de datos", "intermedio", 32, "virtual"),
    ("CD-I03", "IA generativa responsable en el aula", "intermedio", 20, "virtual"),
    ("CD-I04", "Trabajo colaborativo con Git y GitHub", "intermedio", 20, "presencial"),
    ("CD-A01", "Automatización de procesos con n8n", "avanzado", 30, "híbrido"),
    ("CD-A02", "Fundamentos de computación en la nube (AWS)", "avanzado", 36, "virtual"),
    ("CD-A03", "Introducción a ciberseguridad ofensiva y defensiva", "avanzado", 32, "presencial"),
]

REQUISITOS = [
    ("INGLES_B1", "Inglés nivel B1", "Certificar nivel B1 de inglés (prueba institucional o examen internacional)."),
    ("SABER_PRO", "Presentar Saber Pro", "Presentar el examen de Estado Saber Pro (requisito de ley para graduarse)."),
    ("INSIGNIA_CD", "Insignia de competencias digitales", "Obtener la insignia del CCD: 3 cursos aprobados, al menos uno intermedio o avanzado."),
    ("PRACTICA", "Práctica profesional aprobada", "Aprobar la Práctica en Ingeniería de Sistemas (semestre 9)."),
    ("PAZ_SALVO", "Paz y salvo financiero y de biblioteca", "Estar a paz y salvo con la universidad antes de solicitar grado."),
]


def q(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def ins(table: str, cols: list[str], rows: list[tuple]) -> str:
    if not rows:
        return ""
    vals = ",\n".join("(" + ", ".join(q(v) for v in r) + ")" for r in rows)
    return f"INSERT INTO academico.{table} ({', '.join(cols)}) VALUES\n{vals};\n\n"


def periodos(desde=2021, hasta=2026):
    out = []
    for y in range(desde, hasta + 1):
        out.append((f"{y}-1", date(y, 2, 2), date(y, 6, 13)))
        out.append((f"{y}-2", date(y, 8, 3), date(y, 12, 5)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--estudiantes", type=int, default=200)
    args = ap.parse_args()

    plan = json.loads((ROOT / "data/plan_estudios_ing_sistemas.json").read_text(encoding="utf-8"))
    cursos = plan["cursos"]
    sql = ["-- GENERADO por scripts/generate_synthetic.py — NO editar a mano. Datos 100% sintéticos.\n",
           "SET search_path TO academico, public;\n\n"]

    n_sem = max(c["semestre"] for c in cursos)
    sql.append(ins("programa", ["id", "codigo", "nombre", "facultad", "creditos_totales", "semestres", "version_plan"],
                   [(1, "ISIS", plan["programa"], "Facultad de Ingeniería", plan["creditos_totales"], n_sem,
                     plan.get("version_plan") or "vigente")]))

    # Códigos sintéticos AREA + semestre + consecutivo (el PDF no trae códigos)
    rows, by_name, cnt = [], {}, {}
    for i, c in enumerate(cursos, start=1):
        area = (c.get("area") or "GEN")[:4]
        cnt[(area, c["semestre"])] = cnt.get((area, c["semestre"]), 0) + 1
        codigo = c.get("codigo") or f"{area}{c['semestre']}{cnt[(area, c['semestre'])]:02d}"
        c["_id"], c["_codigo"] = i, codigo
        rows.append((i, 1, codigo, c["nombre"], c["semestre"], c["creditos"], c["tipo"], c.get("area")))
        by_name.setdefault(c["nombre"], i)
    sql.append(ins("curso_plan", ["id", "programa_id", "codigo", "nombre", "semestre", "creditos", "tipo", "area"], rows))

    pre = [(by_name[k], by_name[r]) for k, reqs in PRERREQ.items() for r in reqs if k in by_name and r in by_name]
    sql.append(ins("prerrequisito", ["curso_id", "requiere_id"], pre))

    pers = periodos()
    actual_idx = len(pers) - 1  # 2026-2
    sql.append(ins("periodo", ["id", "codigo", "fecha_inicio", "fecha_fin", "actual"],
                   [(i + 1, p[0], p[1].isoformat(), p[2].isoformat(), i == actual_idx) for i, p in enumerate(pers)]))

    sql.append(ins("requisito_grado", ["id", "codigo", "nombre", "descripcion"],
                   [(i + 1, *r) for i, r in enumerate(REQUISITOS)]))
    sql.append(ins("curso_cd", ["id", "codigo", "nombre", "nivel", "horas", "modalidad", "descripcion"],
                   [(i + 1, c[0], c[1], c[2], c[3], c[4], f"Curso {c[2]} del CCD ({c[3]} h, {c[4]}).")
                    for i, c in enumerate(CURSOS_CD)]))

    by_sem: dict[int, list[dict]] = {}
    for c in cursos:
        by_sem.setdefault(c["semestre"], []).append(c)

    est, mat, hist, ereq, ecd, diag = [], [], [], [], [], []
    for n in range(1, args.estudiantes + 1):
        codigo = f"U{n:08d}"
        if n == 1:   # perfil demo fijo para la presentación
            sem, habilidad = 6, 3.7
        else:
            sem = rng.choices(range(1, n_sem + 1), weights=[14, 13, 12, 12, 11, 11, 10, 9, 8])[0]
            habilidad = rng.gauss(3.8, 0.45)
        nom, ape = rng.choice(NOMBRES), f"{rng.choice(APELLIDOS)} {rng.choice(APELLIDOS)}"
        email = f"{nom.split()[0].lower()}.{ape.split()[0].lower()}{n}@estudiantes.ejemplo.edu.co"
        cohorte_idx = actual_idx - (sem - 1)
        est.append((n, codigo, nom, ape, email, 1, pers[cohorte_idx][0], sem, "activo"))

        pendientes: list[dict] = []
        for k in range(sem):            # k = semestres cursados (0 = cohorte)
            per_id = cohorte_idx + k + 1
            es_actual = per_id - 1 == actual_idx
            carga = pendientes + by_sem.get(k + 1, [])
            pendientes = []
            for c in carga:
                if es_actual:
                    hist.append((n, c["_id"], per_id, None, "cursando"))
                    continue
                nota = round(min(5.0, max(0.5, rng.gauss(habilidad, 0.6))), 1)
                if n == 1 and c["nombre"] == "Estadística General":
                    nota = 2.6
                estado = "aprobado" if nota >= 3.0 else "reprobado"
                hist.append((n, c["_id"], per_id, nota, estado))
                if estado == "reprobado":
                    pendientes.append(c)
            cred = sum(c["creditos"] for c in carga)
            if es_actual:
                e_mat = "matriculado" if n == 1 else rng.choices(
                    ["matriculado", "pendiente_pago", "preinscrito", "aplazado"], [80, 10, 5, 5])[0]
            else:
                e_mat = "matriculado"
            pago = None if e_mat != "matriculado" else (pers[per_id - 1][1].replace(day=1)).isoformat()
            mat.append((n, per_id, e_mat, 9_850_000 if cred >= 12 else 6_400_000, pago, cred))

        # requisitos de grado (probabilidad crece con el semestre)
        for rid, (rc, *_r) in enumerate(REQUISITOS, start=1):
            p = {"INGLES_B1": sem / 10, "SABER_PRO": 0.9 if sem >= 8 else 0, "INSIGNIA_CD": 0,
                 "PRACTICA": 0, "PAZ_SALVO": 0.6}[rc]
            ok = rng.random() < p
            ereq.append((n, rid, ok, pers[actual_idx - 1][2].isoformat() if ok else None,
                         "Certificado sintético" if ok else None))

        # competencias digitales
        n_cd = 2 if n == 1 else min(len(CURSOS_CD), rng.choices([0, 1, 2, 3, 4], [20, 25, 25, 20, 10])[0])
        elegidos = [CURSOS_CD[0], CURSOS_CD[5]] if n == 1 else rng.sample(CURSOS_CD, n_cd)
        for cd in elegidos:
            cid = CURSOS_CD.index(cd) + 1
            estado = "aprobado" if (n == 1 or rng.random() < 0.8) else rng.choice(["en_curso", "no_aprobado"])
            punt = rng.randint(70, 98) if estado == "aprobado" else (None if estado == "en_curso" else rng.randint(30, 59))
            ecd.append((n, cid, date(2024 + rng.randint(0, 2), rng.randint(2, 11), rng.randint(1, 28)).isoformat(),
                        estado, punt))
        pd_ = rng.randint(35, 95)
        diag.append((n, pers[cohorte_idx][1].isoformat(), pd_, "básico" if pd_ < 60 else "intermedio" if pd_ < 80 else "avanzado"))

    sql.append(ins("estudiante", ["id", "codigo", "nombres", "apellidos", "email", "programa_id", "cohorte",
                                  "semestre_actual", "estado"], est))
    sql.append(ins("matricula", ["estudiante_id", "periodo_id", "estado", "valor", "fecha_pago", "creditos_inscritos"], mat))
    for i in range(0, len(hist), 2000):
        sql.append(ins("historial_curso", ["estudiante_id", "curso_id", "periodo_id", "nota", "estado"], hist[i:i + 2000]))
    sql.append(ins("estudiante_requisito", ["estudiante_id", "requisito_id", "cumplido", "fecha", "detalle"], ereq))
    sql.append(ins("estudiante_curso_cd", ["estudiante_id", "curso_cd_id", "fecha", "estado", "puntaje"], ecd))
    sql.append(ins("prueba_diagnostica", ["estudiante_id", "fecha", "puntaje", "nivel_asignado"], diag))

    # Requisito INSIGNIA_CD coherente con la vista v_insignia
    sql.append("""UPDATE academico.estudiante_requisito er SET cumplido = TRUE, detalle = 'Insignia emitida (sintético)'
FROM academico.estudiante e, academico.v_insignia vi, academico.requisito_grado r
WHERE er.estudiante_id = e.id AND vi.codigo = e.codigo AND vi.insignia_obtenida
  AND er.requisito_id = r.id AND r.codigo = 'INSIGNIA_CD';\n\n""")

    # Calendario (también se exporta a CSV para Google Sheets)
    cal = [
        ("2026-2", "Inicio de clases", "inicio_cursos", "2026-08-03", None, "Inicio de clases de pregrado."),
        ("2026-2", "Prueba diagnóstica de competencias digitales", "diagnostica", "2026-08-10", "2026-08-21", "Virtual, obligatoria para primer semestre."),
        ("2026-2", "Inscripciones cursos CCD (corte 2)", "inscripciones", "2026-09-14", "2026-09-25", "Inscripción en la plataforma del CCD."),
        ("2026-2", "Inicio cursos CCD (corte 2)", "inicio_cursos", "2026-09-28", None, "Cursos virtuales e híbridos."),
        ("2026-2", "Exámenes finales", "evaluaciones", "2026-11-23", "2026-12-05", "Semana de evaluaciones finales."),
        ("2027-1", "Inscripción de asignaturas 2027-1", "inscripciones", "2026-12-01", "2026-12-12", "Prematrícula académica en Banner."),
        ("2027-1", "Pago de matrícula ordinaria", "matricula", "2026-12-01", "2027-01-15", "Pago sin recargo."),
        ("2027-1", "Pago de matrícula extraordinaria", "matricula", "2027-01-16", "2027-01-29", "Pago con recargo."),
        ("2027-1", "Prueba diagnóstica de competencias digitales", "diagnostica", "2027-02-08", "2027-02-19", "Estudiantes nuevos y transferencias."),
        ("2027-1", "Inicio de clases", "inicio_cursos", "2027-02-01", None, "Inicio de clases de pregrado."),
        ("2027-1", "Inscripciones cursos CCD (corte 1)", "inscripciones", "2027-02-15", "2027-02-26", "Inscripción en la plataforma del CCD."),
        ("2027-1", "Inicio cursos CCD (corte 1)", "inicio_cursos", "2027-03-01", None, "Cursos del Centro de Competencias Digitales."),
        ("2027-1", "Solicitud de grado", "grados", "2027-03-01", "2027-03-31", "Radicar solicitud con requisitos cumplidos."),
    ]
    sql.append(ins("calendario_evento", ["periodo", "evento", "categoria", "fecha_inicio", "fecha_fin", "detalle"], cal))
    with open(ROOT / "data/calendario_academico.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["periodo", "evento", "categoria", "fecha_inicio", "fecha_fin", "detalle"])
        w.writerows(cal)

    noticias = [
        ("Abiertas inscripciones: Automatización de procesos con n8n", "https://ejemplo.unab.local/noticias/n8n-2027-1",
         "Nuevo curso avanzado del CCD, cupos limitados.", "curso", "semilla-sintetica", "2026-11-04"),
        ("Convocatoria semilleros de investigación 2027-1", "https://ejemplo.unab.local/noticias/semilleros-2027",
         "Facultad de Ingeniería abre convocatoria para semilleros.", "convocatoria", "semilla-sintetica", "2026-10-28"),
        ("Certificación AWS Cloud Practitioner con descuento", "https://ejemplo.unab.local/noticias/aws-cp",
         "Vouchers para estudiantes que aprueben CD-A02.", "certificacion", "semilla-sintetica", "2026-10-15"),
    ]
    sql.append(ins("noticia", ["titulo", "url", "resumen", "categoria", "fuente", "fecha_publicacion"], noticias))

    out = ROOT / "db/init/03_seed.sql"
    out.write_text("".join(sql), encoding="utf-8")

    # Documento del plan para el RAG
    md = [f"# Plan de estudios — {plan['programa']} (UNAB)\n",
          f"Créditos totales: {plan['creditos_totales']}. Semestres: {n_sem}. Fuente: {plan['fuente']}.\n",
          "Los códigos de curso y prerrequisitos de este documento son ilustrativos (sintéticos).\n"]
    for s in sorted(by_sem):
        md.append(f"\n## Semestre {s}\n")
        for c in by_sem[s]:
            req = PRERREQ.get(c["nombre"], [])
            md.append(f"- {c['_codigo']} · {c['nombre']} · {c['creditos']} créditos · {c['tipo']}"
                      + (f" · prerrequisitos: {', '.join(req)}" if req else "") + "\n")
    (ROOT / "data/docs_ccd/plan_de_estudios.md").write_text("".join(md), encoding="utf-8")

    print(f"OK: {len(est)} estudiantes, {len(hist)} registros de historial, {len(mat)} matrículas -> {out}")


if __name__ == "__main__":
    main()
