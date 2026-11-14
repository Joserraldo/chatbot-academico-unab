-- =====================================================================
-- Vistas analíticas pensadas para agentes conversacionales:
-- una fila = una respuesta lista para el LLM (sin JOINs del lado del agente).
-- =====================================================================
SET search_path TO academico, public;

-- Estado académico consolidado por estudiante
CREATE OR REPLACE VIEW v_estado_academico AS
WITH aprob AS (
    SELECT h.estudiante_id,
           SUM(c.creditos) FILTER (WHERE h.estado = 'aprobado')       AS creditos_aprobados,
           SUM(c.creditos) FILTER (WHERE h.estado = 'cursando')       AS creditos_cursando,
           COUNT(*)        FILTER (WHERE h.estado = 'reprobado')      AS cursos_reprobados,
           ROUND(SUM(h.nota * c.creditos) FILTER (WHERE h.nota IS NOT NULL)
                 / NULLIF(SUM(c.creditos) FILTER (WHERE h.nota IS NOT NULL), 0), 2) AS promedio_ponderado
    FROM historial_curso h
    JOIN curso_plan c ON c.id = h.curso_id
    GROUP BY h.estudiante_id
)
SELECT e.codigo,
       e.nombres || ' ' || e.apellidos                          AS estudiante,
       p.nombre                                                 AS programa,
       e.cohorte,
       e.semestre_actual,
       e.estado                                                 AS estado_estudiante,
       per.codigo                                               AS periodo_actual,
       COALESCE(m.estado, 'sin_matricula')                      AS estado_matricula,
       m.valor                                                  AS valor_matricula,
       m.fecha_pago,
       COALESCE(a.creditos_aprobados, 0)                        AS creditos_aprobados,
       COALESCE(a.creditos_cursando, 0)                         AS creditos_cursando,
       p.creditos_totales,
       ROUND(100.0 * COALESCE(a.creditos_aprobados, 0) / p.creditos_totales, 1) AS porcentaje_avance,
       a.promedio_ponderado,
       COALESCE(a.cursos_reprobados, 0)                         AS cursos_reprobados
FROM estudiante e
JOIN programa p      ON p.id = e.programa_id
LEFT JOIN periodo per ON per.actual
LEFT JOIN matricula m ON m.estudiante_id = e.id AND m.periodo_id = per.id
LEFT JOIN aprob a    ON a.estudiante_id = e.id;

-- Cursos del plan que el estudiante aún no ha aprobado
CREATE OR REPLACE VIEW v_cursos_pendientes AS
SELECT e.codigo,
       c.codigo   AS codigo_curso,
       c.nombre   AS curso,
       c.semestre AS semestre_plan,
       c.creditos,
       c.tipo,
       EXISTS (SELECT 1 FROM historial_curso h
               WHERE h.estudiante_id = e.id AND h.curso_id = c.id AND h.estado = 'cursando') AS cursando,
       EXISTS (SELECT 1 FROM historial_curso h
               WHERE h.estudiante_id = e.id AND h.curso_id = c.id AND h.estado = 'reprobado') AS reprobado_antes
FROM estudiante e
JOIN curso_plan c ON c.programa_id = e.programa_id
WHERE NOT EXISTS (SELECT 1 FROM historial_curso h
                  WHERE h.estudiante_id = e.id AND h.curso_id = c.id AND h.estado = 'aprobado');

-- Alertas: cursos pendientes con prerrequisitos NO aprobados (no se pueden inscribir aún)
CREATE OR REPLACE VIEW v_alertas_prerrequisitos AS
SELECT e.codigo,
       c.nombre  AS curso_bloqueado,
       c.semestre AS semestre_plan,
       r.nombre  AS prerrequisito_faltante
FROM estudiante e
JOIN curso_plan c    ON c.programa_id = e.programa_id
JOIN prerrequisito pr ON pr.curso_id = c.id
JOIN curso_plan r    ON r.id = pr.requiere_id
WHERE NOT EXISTS (SELECT 1 FROM historial_curso h
                  WHERE h.estudiante_id = e.id AND h.curso_id = c.id AND h.estado = 'aprobado')
  AND NOT EXISTS (SELECT 1 FROM historial_curso h
                  WHERE h.estudiante_id = e.id AND h.curso_id = r.id AND h.estado = 'aprobado');

-- Requisitos de grado pendientes
CREATE OR REPLACE VIEW v_requisitos_grado AS
SELECT e.codigo, r.codigo AS requisito, r.nombre, COALESCE(er.cumplido, FALSE) AS cumplido,
       er.fecha, er.detalle, r.descripcion
FROM estudiante e
CROSS JOIN requisito_grado r
LEFT JOIN estudiante_requisito er ON er.estudiante_id = e.id AND er.requisito_id = r.id;

-- Proyección de semestres restantes
-- Supuesto: el ritmo futuro = promedio de créditos aprobados por semestre cursado (mín. 12, máx. 20).
CREATE OR REPLACE VIEW v_proyeccion AS
SELECT ea.codigo,
       ea.creditos_aprobados,
       ea.creditos_totales,
       ea.creditos_totales - ea.creditos_aprobados                                AS creditos_restantes,
       GREATEST(12, LEAST(20, ROUND(ea.creditos_aprobados::numeric
                                    / GREATEST(ea.semestre_actual - 1, 1))))      AS ritmo_creditos_semestre,
       CEIL((ea.creditos_totales - ea.creditos_aprobados - ea.creditos_cursando)::numeric
            / GREATEST(12, LEAST(20, ROUND(ea.creditos_aprobados::numeric
                                           / GREATEST(ea.semestre_actual - 1, 1)))))
         + CASE WHEN ea.creditos_cursando > 0 THEN 1 ELSE 0 END                   AS semestres_restantes_estimados,
       (SELECT COUNT(*) FROM v_requisitos_grado rg WHERE rg.codigo = ea.codigo AND NOT rg.cumplido)
                                                                                  AS requisitos_grado_pendientes
FROM v_estado_academico ea;

-- Historial de competencias digitales + progreso hacia la insignia
CREATE OR REPLACE VIEW v_competencias_digitales AS
SELECT e.codigo,
       cd.codigo AS codigo_curso_cd,
       cd.nombre AS curso_cd,
       cd.nivel,
       cd.horas,
       ecd.estado,
       ecd.puntaje,
       ecd.fecha,
       cd.cuenta_insignia
FROM estudiante e
JOIN estudiante_curso_cd ecd ON ecd.estudiante_id = e.id
JOIN curso_cd cd             ON cd.id = ecd.curso_cd_id;

-- Regla sintética de la insignia: 3 cursos aprobados que cuentan (al menos 1 intermedio o avanzado)
CREATE OR REPLACE VIEW v_insignia AS
SELECT e.codigo,
       COUNT(*) FILTER (WHERE ecd.estado = 'aprobado' AND cd.cuenta_insignia)                    AS cursos_validos,
       BOOL_OR(ecd.estado = 'aprobado' AND cd.nivel IN ('intermedio','avanzado'))               AS tiene_nivel_intermedio,
       (COUNT(*) FILTER (WHERE ecd.estado = 'aprobado' AND cd.cuenta_insignia) >= 3
        AND COALESCE(BOOL_OR(ecd.estado = 'aprobado' AND cd.nivel IN ('intermedio','avanzado')), FALSE))
                                                                                                AS insignia_obtenida
FROM estudiante e
LEFT JOIN estudiante_curso_cd ecd ON ecd.estudiante_id = e.id
LEFT JOIN curso_cd cd             ON cd.id = ecd.curso_cd_id
GROUP BY e.codigo;

CREATE OR REPLACE VIEW v_noticias_recientes AS
SELECT titulo, url, resumen, categoria, fuente, fecha_publicacion, capturada_en
FROM noticia
ORDER BY COALESCE(fecha_publicacion, capturada_en::date) DESC, id DESC;

-- Permisos del rol de solo lectura (creado en 00_databases.sh)
GRANT USAGE ON SCHEMA academico TO chatbot_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA academico TO chatbot_ro;
GRANT INSERT ON academico.chat_log TO chatbot_ro;
GRANT USAGE ON SEQUENCE academico.chat_log_id_seq TO chatbot_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA academico GRANT SELECT ON TABLES TO chatbot_ro;
-- La tabla de vectores (public.rag_documentos) la crea n8n con este mismo usuario admin:
GRANT USAGE ON SCHEMA public TO chatbot_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO chatbot_ro;
