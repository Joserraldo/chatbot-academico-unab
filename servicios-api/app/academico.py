import unicodedata

from .bold import pago_orden
from .db import estudiante_id, hoy_bogota
from .reservas import CONSULTA_RESERVA, datos_reserva


def normalizar(texto):
    return "".join(
        letra for letra in unicodedata.normalize("NFD", texto.lower())
        if not unicodedata.combining(letra)
    )


def noticias(conn, limite):
    return conn.execute("""
        WITH noticias AS (
            SELECT titulo, url, resumen, categoria, fuente, fecha_publicacion, id,
                   COALESCE(fecha_publicacion::timestamp AT TIME ZONE INTERVAL '-05:00',
                            capturada_en) AS fecha_noticia
            FROM academico.noticia
        )
        SELECT titulo, url, resumen, categoria, fuente, fecha_publicacion
        FROM noticias
        WHERE fecha_noticia >= now() - INTERVAL '48 hours'
           OR NOT EXISTS (SELECT 1 FROM noticias WHERE fecha_noticia >= now() - INTERVAL '48 hours')
        ORDER BY (fecha_noticia::date >= (now() - INTERVAL '24 hours')::date) DESC,
                 CASE WHEN fuente ILIKE 'UNAB%%' THEN 0
                      WHEN categoria IN ('educacion', 'ingenieria_sistemas', 'convocatoria', 'curso', 'certificacion') THEN 1
                      ELSE 2 END,
                 fecha_noticia DESC, id DESC LIMIT %s
    """, (limite,)).fetchall()


def panel_hoy(conn, codigo):
    alumno_id = estudiante_id(conn, codigo)
    fecha = hoy_bogota()
    dia = ("lun", "mar", "mie", "jue", "vie", "sab", "dom")[fecha.weekday()]
    estudiante = conn.execute("""
        SELECT codigo, estudiante AS nombre, programa, semestre_actual,
               promedio_ponderado AS promedio, porcentaje_avance,
               CASE WHEN estado_matricula = 'pendiente_pago' AND EXISTS (
                   SELECT 1 FROM servicios.pago_orden p
                   WHERE p.codigo_estudiante = ea.codigo AND p.referencia = ea.periodo_actual
                     AND p.concepto = 'matricula' AND p.estado = 'aprobado'
               ) THEN 'pagada' ELSE estado_matricula END AS estado_matricula
        FROM academico.v_estado_academico ea
        WHERE codigo = %s ORDER BY periodo_actual DESC NULLS LAST LIMIT 1
    """, (codigo,)).fetchone()
    tareas = conn.execute("""
        SELECT t.titulo, c.nombre AS curso, t.tipo, t.fecha_entrega,
               COALESCE(et.estado, CASE WHEN t.fecha_entrega < now() THEN 'vencida'
                                      ELSE 'pendiente' END) AS estado
        FROM academico.inscripcion_seccion i
        JOIN academico.seccion s ON s.id = i.seccion_id
        JOIN academico.periodo p ON p.id = s.periodo_id AND p.actual
        JOIN academico.curso_plan c ON c.id = s.curso_id
        JOIN academico.tarea_tema t ON t.seccion_id = s.id
        LEFT JOIN academico.entrega_tema et ON et.tarea_id = t.id AND et.estudiante_id = i.estudiante_id
        WHERE i.estudiante_id = %s ORDER BY t.fecha_entrega, t.id
    """, (alumno_id,)).fetchall()
    evaluaciones = conn.execute("""
        SELECT c.nombre AS curso, d.nombre AS docente, ev.fecha_limite
        FROM academico.evaluacion_docente ev
        JOIN academico.seccion s ON s.id = ev.seccion_id
        JOIN academico.periodo p ON p.id = s.periodo_id AND p.actual
        JOIN academico.curso_plan c ON c.id = s.curso_id
        JOIN academico.docente d ON d.id = s.docente_id
        WHERE ev.estudiante_id = %s AND ev.estado = 'pendiente'
        ORDER BY ev.fecha_limite, s.id
    """, (alumno_id,)).fetchall()
    prestamos = conn.execute("""
        SELECT titulo, fecha_vencimiento, estado, multa
        FROM academico.prestamo_biblioteca
        WHERE estudiante_id = %s AND estado IN ('activo', 'vencido')
        ORDER BY fecha_vencimiento, id
    """, (alumno_id,)).fetchall()
    pagos = conn.execute("""
        SELECT * FROM servicios.pago_orden
        WHERE codigo_estudiante = %s AND estado = 'pendiente'
        ORDER BY creado_en DESC, order_id
    """, (codigo,)).fetchall()
    reservas = conn.execute(CONSULTA_RESERVA + """
        WHERE r.codigo_estudiante = %s AND r.fecha >= %s AND r.estado <> 'cancelada'
        ORDER BY r.fecha, r.hora_inicio, r.id
    """, (codigo, fecha)).fetchall()
    secciones = conn.execute("""
        SELECT c.nombre AS curso, s.horario, s.salon, d.nombre AS docente
        FROM academico.inscripcion_seccion i
        JOIN academico.seccion s ON s.id = i.seccion_id
        JOIN academico.periodo p ON p.id = s.periodo_id AND p.actual
        JOIN academico.curso_plan c ON c.id = s.curso_id
        JOIN academico.docente d ON d.id = s.docente_id
        WHERE i.estudiante_id = %s ORDER BY c.nombre, s.id
    """, (alumno_id,)).fetchall()
    horario = []
    for seccion in secciones:
        for tramo in seccion["horario"].split(";"):
            tramo = tramo.strip()
            if normalizar(tramo)[:3] == dia:
                horario.append({**seccion, "horario": tramo})
    riesgo = conn.execute("""
        SELECT nivel, probabilidad, factores FROM servicios.riesgo_estudiante WHERE codigo = %s
    """, (codigo,)).fetchone()
    return {
        "estudiante": estudiante, "tareas": tareas, "evaluaciones": evaluaciones,
        "prestamos": prestamos, "pagos_pendientes": [pago_orden(fila) for fila in pagos],
        "reservas": [datos_reserva(fila) for fila in reservas], "horario_hoy": horario,
        "noticias": [
            {"titulo": n["titulo"], "url": n["url"], "fuente": n["fuente"],
             "fecha": n["fecha_publicacion"]} for n in noticias(conn, 10)
        ],
        "riesgo": riesgo,
    }


def analitica(conn):
    return {
        "intenciones": conn.execute("""
            SELECT COALESCE(intencion, 'sin_clasificar') AS intencion, count(*) AS n
            FROM academico.chat_log GROUP BY 1 ORDER BY n DESC, intencion
        """).fetchall(),
        "bloqueos": conn.execute("""
            SELECT COALESCE(motivo_bloqueo, 'sin_motivo') AS motivo, count(*) AS n
            FROM academico.chat_log WHERE bloqueado GROUP BY 1 ORDER BY n DESC, motivo
        """).fetchall(),
        "por_dia": conn.execute("""
            SELECT (creado_en AT TIME ZONE INTERVAL '-05:00')::date AS dia, count(*) AS n
            FROM academico.chat_log GROUP BY 1 ORDER BY dia
        """).fetchall(),
        "riesgo": conn.execute("""
            SELECT nivel, count(*) AS n FROM servicios.riesgo_estudiante GROUP BY nivel ORDER BY nivel
        """).fetchall(),
        "modelo": conn.execute("""
            SELECT * FROM servicios.modelo_riesgo ORDER BY entrenado_en DESC, id DESC LIMIT 1
        """).fetchone(),
        "totales": conn.execute("""
            SELECT count(*) AS mensajes, count(DISTINCT codigo_estudiante) AS estudiantes,
                   count(*) FILTER (WHERE bloqueado) AS bloqueados
            FROM academico.chat_log
        """).fetchone(),
    }
