-- Datos de prueba separados de los identificadores de la demo.
SET search_path TO academico, public;

CREATE ROLE servicios_rw LOGIN;
GRANT USAGE ON SCHEMA academico, servicios TO servicios_rw;
GRANT SELECT ON ALL TABLES IN SCHEMA academico TO servicios_rw;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA servicios TO servicios_rw;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA servicios TO servicios_rw;

UPDATE periodo SET actual = false WHERE actual;
INSERT INTO periodo (id, codigo, fecha_inicio, fecha_fin, actual) VALUES
    (900001, '2099-1', '2099-01-01', '2099-06-30', false),
    (900002, '2099-2', '2099-07-01', '2099-12-31', true);
INSERT INTO programa (id, codigo, nombre, facultad, creditos_totales, semestres)
VALUES (900001, 'PRUEBA', 'Programa sintético', 'Facultad sintética', 12, 3);
INSERT INTO estudiante
    (id, codigo, nombres, apellidos, email, programa_id, cohorte, semestre_actual)
VALUES
    (900001, 'U90000001', 'Luz', 'Sintética', 'luz@example.test', 900001, '2099-1', 2),
    (900002, 'U90000002', 'Sol', 'Sintético', 'sol@example.test', 900001, '2099-1', 2);
INSERT INTO persona_demo (codigo, titulo, descripcion, emoji, orden) VALUES
    ('U90000001', 'Persona de pruebas', 'Historia sintética', '🎓', -1);
INSERT INTO curso_plan (id, programa_id, codigo, nombre, creditos, area) VALUES
    (900001, 900001, 'P1', 'Métodos', 3, 'Bases'),
    (900002, 900001, 'P2', 'Datos', 2, 'Bases'),
    (900003, 900001, 'P3', 'Laboratorio', 4, 'Aplicada'),
    (900004, 900001, 'P4', 'Proyecto', 3, 'Aplicada');
INSERT INTO historial_curso (estudiante_id, curso_id, periodo_id, nota, estado) VALUES
    (900001, 900001, 900001, 4.0, 'aprobado'),
    (900001, 900002, 900001, 2.0, 'reprobado'),
    (900001, 900002, 900002, NULL, 'cursando'),
    (900001, 900003, 900002, NULL, 'cursando'),
    (900002, 900001, 900001, 3.0, 'aprobado'),
    (900002, 900003, 900002, 5.0, 'aprobado');
INSERT INTO matricula (estudiante_id, periodo_id, estado, valor) VALUES
    (900001, 900001, 'matriculado', 1000),
    (900001, 900002, 'pendiente_pago', 9850000),
    (900002, 900002, 'matriculado', 9850000);
INSERT INTO docente (id, nombre, email) VALUES
    (900001, 'Docente de prueba', 'docente@example.test');
INSERT INTO seccion (id, curso_id, periodo_id, docente_id, grupo, horario, salon) VALUES
    (900001, 900002, 900002, 900001, '01',
     'Lun 07:00-09:00; Mar 07:00-09:00; Mié 07:00-09:00; Jue 07:00-09:00; Vie 07:00-09:00; Sáb 07:00-09:00; Dom 07:00-09:00', 'A1');
INSERT INTO inscripcion_seccion (estudiante_id, seccion_id) VALUES (900001, 900001);
INSERT INTO nota_parcial (estudiante_id, seccion_id, corte, porcentaje, nota) VALUES
    (900001, 900001, 1, 30, 3.5), (900001, 900001, 2, 30, 4.2), (900001, 900001, 3, 40, NULL);
INSERT INTO tarea_tema (id, seccion_id, titulo, tipo, fecha_entrega) VALUES
    (900001, 900001, 'Práctica sintética', 'tarea', '2099-11-25 08:00-05');
INSERT INTO evaluacion_docente (estudiante_id, seccion_id, estado, fecha_limite) VALUES
    (900001, 900001, 'pendiente', '2099-12-09');
INSERT INTO prestamo_biblioteca
    (estudiante_id, titulo, autor, fecha_prestamo, fecha_vencimiento, estado, multa)
VALUES
    (900001, 'Libro vencido 1', 'Autor sintético', '2099-01-01', '2099-01-05', 'vencido', 1100),
    (900001, 'Libro vencido 2', 'Autor sintético', '2099-01-01', '2099-01-05', 'vencido', 2100),
    (900001, 'Libro activo', 'Autor sintético', '2099-01-01', '2099-01-05', 'activo', 9000),
    (900001, 'Libro devuelto', 'Autor sintético', '2099-01-01', '2099-01-05', 'devuelto', 9000);
INSERT INTO enlace_tramite (codigo, nombre, url, descripcion, pasos) VALUES
    ('biblioteca_renovar', 'Renueva tus préstamos', 'https://biblioteca.example.test/', 'Portal de prueba', 'Ingresa'),
    ('reservas', 'Reserva de espacios', 'https://reservas.example.test/', 'Portal de prueba', 'Ingresa'),
    ('gimnasio', 'Gimnasio de prueba', 'https://gimnasio.example.test/', 'Portal de prueba', 'Ingresa'),
    ('cosmos', 'Cosmos de prueba', 'https://cosmos.example.test/', 'Portal de prueba', 'Ingresa'),
    ('tema', 'TEMA de prueba', 'https://tema.example.test/', 'Portal de prueba', 'Ingresa'),
    ('evaluacion_docente', 'Evalúa a tu docente', 'https://evaluar.example.test/', 'Portal de prueba', 'Ingresa')
ON CONFLICT (codigo) DO UPDATE SET nombre = EXCLUDED.nombre, url = EXCLUDED.url;
INSERT INTO noticia (titulo, url, fuente, fecha_publicacion) VALUES
    ('Noticia reciente sintética', 'https://noticia.example.test/nueva', 'Pruebas', current_date),
    ('Noticia antigua sintética', 'https://noticia.example.test/vieja', 'Pruebas', current_date - 20);
INSERT INTO chat_log (session_id, codigo_estudiante, intencion, mensaje, bloqueado, motivo_bloqueo, creado_en) VALUES
    ('prueba-1', 'U90000001', 'historial', 'Mensaje de prueba', false, null, '2099-11-20 01:30+00'),
    ('prueba-2', 'U90000001', 'bloqueado', 'Mensaje de prueba', true, 'Motivo de prueba', '2099-11-20 01:31+00');

INSERT INTO servicios.espacio (id, codigo, nombre, tipo, sede, capacidad, tarifa_hora) VALUES
    (900001, 'PRUEBA-SALA', 'Sala de prueba', 'sala_estudio', 'Sede sintética', 4, 0),
    (900002, 'PRUEBA-AUD', 'Auditorio de prueba', 'auditorio', 'Sede sintética', 50, 18000);
INSERT INTO servicios.riesgo_estudiante (codigo, probabilidad, nivel, factores, modelo)
VALUES ('U90000001', 0.7500, 'alto', '[{"factor":"Nota baja","valor":2,"aporte":0.25}]', 'Modelo de prueba');
INSERT INTO servicios.modelo_riesgo (nombre, auc, f1, accuracy, matriz, importancias, n_train, n_test, entrenado_en)
VALUES ('Modelo de prueba', 0.85, 0.78, 0.81, '[[3,1],[1,4]]', '[]', 40, 9, '2099-12-01');
