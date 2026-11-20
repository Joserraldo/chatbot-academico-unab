from fastapi import HTTPException

from .db import estudiante_id

TIPOS = {
    "notas_semestre": ("line", "Promedio por semestre", "nota 0-5"),
    "avance": ("doughnut", "Avance del plan de estudios", "créditos"),
    "creditos_area": ("bar", "Créditos aprobados por área", "créditos"),
    "parciales": ("bar", "Notas por corte del periodo actual", "nota 0-5"),
    "riesgo": ("bar", "Factores de riesgo académico", "aporte al riesgo"),
    "cohorte": ("line", "Tu promedio frente al de tu programa", "nota 0-5"),
}


def grafica(conn, codigo, tipo, alumno_id=None):
    if alumno_id is None:
        alumno_id = estudiante_id(conn, codigo)
    nota = None
    if tipo == "notas_semestre":
        filas = conn.execute("""
            SELECT p.codigo, ROUND(SUM(h.nota * c.creditos) / NULLIF(SUM(c.creditos), 0), 2) AS valor
            FROM academico.historial_curso h
            JOIN academico.periodo p ON p.id = h.periodo_id
            JOIN academico.curso_plan c ON c.id = h.curso_id
            WHERE h.estudiante_id = %s AND h.nota IS NOT NULL
            GROUP BY p.id ORDER BY p.fecha_inicio, p.codigo
        """, (alumno_id,)).fetchall()
        labels = [fila["codigo"] for fila in filas]
        series = [{"nombre": "Promedio", "datos": [fila["valor"] for fila in filas]}]
        nota = "Línea de referencia: 3.0 aprueba."
    elif tipo in ("avance", "creditos_area"):
        filas = conn.execute("""
            SELECT c.area, c.creditos, e.creditos_totales,
                   CASE WHEN EXISTS (
                       SELECT 1 FROM academico.historial_curso h
                       WHERE h.estudiante_id = e.id AND h.curso_id = c.id AND h.estado = 'aprobado'
                   ) THEN 'aprobado' WHEN EXISTS (
                       SELECT 1 FROM academico.historial_curso h
                       JOIN academico.periodo p ON p.id = h.periodo_id AND p.actual
                       WHERE h.estudiante_id = e.id AND h.curso_id = c.id AND h.estado = 'cursando'
                   ) OR EXISTS (
                       SELECT 1 FROM academico.inscripcion_seccion i
                       JOIN academico.seccion s ON s.id = i.seccion_id AND s.curso_id = c.id
                       JOIN academico.periodo p ON p.id = s.periodo_id AND p.actual
                       WHERE i.estudiante_id = e.id
                   ) THEN 'cursando' END AS estado
            FROM (SELECT a.id, a.programa_id, p.creditos_totales
                  FROM academico.estudiante a JOIN academico.programa p ON p.id = a.programa_id
                  WHERE a.id = %s) e
            LEFT JOIN academico.curso_plan c ON c.programa_id = e.programa_id
            ORDER BY c.area NULLS LAST, c.id
        """, (alumno_id,)).fetchall()
        if tipo == "avance":
            aprobados = sum(fila["creditos"] for fila in filas if fila["estado"] == "aprobado")
            cursando = sum(fila["creditos"] for fila in filas if fila["estado"] == "cursando")
            pendientes = max(0, filas[0]["creditos_totales"] - aprobados - cursando)
            labels = ["Aprobados", "Cursando", "Pendientes"]
            series = [{"nombre": "Créditos", "datos": [aprobados, cursando, pendientes]}]
        else:
            areas = {}
            for fila in filas:
                if fila["estado"] == "aprobado":
                    area = fila["area"] or "Sin área"
                    areas[area] = areas.get(area, 0) + fila["creditos"]
            labels = list(areas)
            series = [{"nombre": "Créditos aprobados", "datos": list(areas.values())}]
    elif tipo == "parciales":
        filas = conn.execute("""
            SELECT c.nombre, s.id,
                   MAX(n.nota) FILTER (WHERE n.corte = 1) AS corte1,
                   MAX(n.nota) FILTER (WHERE n.corte = 2) AS corte2,
                   MAX(n.nota) FILTER (WHERE n.corte = 3) AS corte3
            FROM academico.inscripcion_seccion i
            JOIN academico.seccion s ON s.id = i.seccion_id
            JOIN academico.curso_plan c ON c.id = s.curso_id
            JOIN academico.periodo p ON p.id = s.periodo_id AND p.actual
            LEFT JOIN academico.nota_parcial n ON n.estudiante_id = i.estudiante_id AND n.seccion_id = s.id
            WHERE i.estudiante_id = %s GROUP BY c.nombre, s.id ORDER BY c.nombre, s.id
        """, (alumno_id,)).fetchall()
        labels = [fila["nombre"] for fila in filas]
        series = [
            {"nombre": f"Corte {corte}", "datos": [fila[f"corte{corte}"] for fila in filas]}
            for corte in (1, 2, 3)
        ]
    elif tipo == "riesgo":
        fila = conn.execute("""
            SELECT factores FROM servicios.riesgo_estudiante WHERE codigo = %s
        """, (codigo,)).fetchone()
        if fila is None or not fila["factores"]:
            raise HTTPException(404, "No hay factores de riesgo para este estudiante.")
        labels = [factor["factor"] for factor in fila["factores"]]
        series = [{"nombre": "Aporte", "datos": [factor["aporte"] for factor in fila["factores"]]}]
    else:
        filas = conn.execute("""
            WITH promedios AS (
                SELECT h.periodo_id, e.id,
                       SUM(h.nota * c.creditos) / NULLIF(SUM(c.creditos), 0) AS valor
                FROM academico.estudiante e
                JOIN academico.historial_curso h ON h.estudiante_id = e.id
                JOIN academico.curso_plan c ON c.id = h.curso_id
                WHERE e.programa_id = (SELECT programa_id FROM academico.estudiante WHERE id = %s)
                  AND h.nota IS NOT NULL
                GROUP BY h.periodo_id, e.id
            )
            SELECT p.codigo, ROUND(MAX(pr.valor) FILTER (WHERE pr.id = %s), 2) AS estudiante,
                   ROUND(AVG(pr.valor), 2) AS programa
            FROM promedios pr JOIN academico.periodo p ON p.id = pr.periodo_id
            GROUP BY p.id ORDER BY p.fecha_inicio, p.codigo
        """, (alumno_id, alumno_id)).fetchall()
        labels = [fila["codigo"] for fila in filas]
        series = [
            {"nombre": nombre, "datos": [fila[clave] for fila in filas]}
            for clave, nombre in (("estudiante", "Estudiante"), ("programa", "Programa"))
        ]
        nota = "Cada estudiante aporta un promedio ponderado por periodo al promedio del programa."

    estilo, titulo, unidad = TIPOS[tipo]
    return {
        "id": tipo, "tipo": estilo, "titulo": titulo, "labels": labels, "series": series,
        "unidad": unidad, "nota": nota,
    }
