-- =====================================================================
-- v2 — Asistente UNAB 360. Esquema ADITIVO e idempotente (se puede re-ejecutar).
-- academico.*  : datos institucionales SINTÉTICOS que simulan Cosmos (notas por corte,
--                horario), TEMA (tareas, evaluación docente) y Biblioteca (préstamos).
-- servicios.*  : lo que escribe servicios-api (reservas, órdenes de pago Bold, modelo ML).
-- Contrato completo: docs/CONTRATOS-V2.md
-- =====================================================================
SET search_path TO academico, public;

CREATE TABLE IF NOT EXISTS persona_demo (
    codigo      TEXT PRIMARY KEY,
    titulo      TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    emoji       TEXT NOT NULL DEFAULT '🎓',
    orden       INT  NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS docente (
    id      SERIAL PRIMARY KEY,
    nombre  TEXT NOT NULL,
    email   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS seccion (
    id          SERIAL PRIMARY KEY,
    curso_id    INT NOT NULL REFERENCES curso_plan(id),
    periodo_id  INT NOT NULL REFERENCES periodo(id),
    docente_id  INT NOT NULL REFERENCES docente(id),
    grupo       TEXT NOT NULL,
    horario     TEXT NOT NULL,      -- 'Lun 07:00-09:00; Mié 07:00-09:00'
    salon       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inscripcion_seccion (
    estudiante_id INT NOT NULL REFERENCES estudiante(id) ON DELETE CASCADE,
    seccion_id    INT NOT NULL REFERENCES seccion(id) ON DELETE CASCADE,
    PRIMARY KEY (estudiante_id, seccion_id)
);

CREATE TABLE IF NOT EXISTS nota_parcial (
    estudiante_id INT NOT NULL REFERENCES estudiante(id) ON DELETE CASCADE,
    seccion_id    INT NOT NULL REFERENCES seccion(id) ON DELETE CASCADE,
    corte         INT NOT NULL CHECK (corte BETWEEN 1 AND 3),
    porcentaje    INT NOT NULL,
    nota          NUMERIC(3,1),     -- NULL = aún no calificado
    PRIMARY KEY (estudiante_id, seccion_id, corte)
);

CREATE TABLE IF NOT EXISTS tarea_tema (
    id            SERIAL PRIMARY KEY,
    seccion_id    INT NOT NULL REFERENCES seccion(id) ON DELETE CASCADE,
    titulo        TEXT NOT NULL,
    tipo          TEXT NOT NULL,    -- tarea | quiz | foro | proyecto
    fecha_entrega TIMESTAMPTZ NOT NULL,
    peso          INT NOT NULL DEFAULT 10
);

CREATE TABLE IF NOT EXISTS entrega_tema (
    estudiante_id INT NOT NULL REFERENCES estudiante(id) ON DELETE CASCADE,
    tarea_id      INT NOT NULL REFERENCES tarea_tema(id) ON DELETE CASCADE,
    estado        TEXT NOT NULL,    -- pendiente | entregada | calificada | vencida
    nota          NUMERIC(3,1),
    PRIMARY KEY (estudiante_id, tarea_id)
);

CREATE TABLE IF NOT EXISTS evaluacion_docente (
    estudiante_id INT NOT NULL REFERENCES estudiante(id) ON DELETE CASCADE,
    seccion_id    INT NOT NULL REFERENCES seccion(id) ON DELETE CASCADE,
    estado        TEXT NOT NULL,    -- pendiente | completada
    fecha_limite  DATE NOT NULL,
    PRIMARY KEY (estudiante_id, seccion_id)
);

CREATE TABLE IF NOT EXISTS prestamo_biblioteca (
    id                SERIAL PRIMARY KEY,
    estudiante_id     INT NOT NULL REFERENCES estudiante(id) ON DELETE CASCADE,
    titulo            TEXT NOT NULL,
    autor             TEXT NOT NULL,
    fecha_prestamo    DATE NOT NULL,
    fecha_vencimiento DATE NOT NULL,
    renovaciones      INT  NOT NULL DEFAULT 0,
    estado            TEXT NOT NULL,  -- activo | vencido | devuelto
    multa             NUMERIC(12,0) NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS enlace_tramite (
    codigo         TEXT PRIMARY KEY,
    nombre         TEXT NOT NULL,
    url            TEXT NOT NULL,
    descripcion    TEXT NOT NULL,
    pasos          TEXT NOT NULL,
    palabras_clave TEXT[] NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_insc_est     ON inscripcion_seccion (estudiante_id);
CREATE INDEX IF NOT EXISTS idx_entrega_est  ON entrega_tema (estudiante_id);
CREATE INDEX IF NOT EXISTS idx_prestamo_est ON prestamo_biblioteca (estudiante_id);

-- ---------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS servicios;
SET search_path TO servicios, public;

CREATE TABLE IF NOT EXISTS espacio (
    id          SERIAL PRIMARY KEY,
    codigo      TEXT UNIQUE NOT NULL,
    nombre      TEXT NOT NULL,
    tipo        TEXT NOT NULL,      -- sala_estudio | auditorio | laboratorio | cancha | gimnasio | musica
    sede        TEXT NOT NULL,
    capacidad   INT  NOT NULL,
    tarifa_hora NUMERIC(12,0) NOT NULL DEFAULT 0,   -- 0 = gratis para estudiantes
    descripcion TEXT
);

CREATE TABLE IF NOT EXISTS reserva (
    id                SERIAL PRIMARY KEY,
    codigo_estudiante TEXT NOT NULL,
    espacio_id        INT  NOT NULL REFERENCES espacio(id),
    fecha             DATE NOT NULL,
    hora_inicio       TIME NOT NULL,
    hora_fin          TIME NOT NULL,
    estado            TEXT NOT NULL,  -- pendiente_pago | confirmada | cancelada
    order_id          TEXT,
    creado_en         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_reserva_franja
    ON reserva (espacio_id, fecha, hora_inicio) WHERE estado <> 'cancelada';
CREATE INDEX IF NOT EXISTS idx_reserva_est ON reserva (codigo_estudiante);

CREATE TABLE IF NOT EXISTS pago_orden (
    order_id          TEXT PRIMARY KEY,   -- UNAB-MAT-<12hex> | UNAB-RES-… | UNAB-BIB-…
    codigo_estudiante TEXT NOT NULL,
    concepto          TEXT NOT NULL,      -- matricula | reserva | multa_biblioteca
    referencia        TEXT,
    descripcion       TEXT NOT NULL,
    monto             NUMERIC(12,0) NOT NULL,
    moneda            TEXT NOT NULL DEFAULT 'COP',
    estado            TEXT NOT NULL DEFAULT 'pendiente',  -- pendiente | aprobado | rechazado | fallido | anulado
    proveedor         TEXT NOT NULL,      -- bold | simulado
    bold_payment_id   TEXT,
    metodo            TEXT,
    creado_en         TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en    TIMESTAMPTZ NOT NULL DEFAULT now(),
    detalle           JSONB
);
CREATE INDEX IF NOT EXISTS idx_pago_est ON pago_orden (codigo_estudiante, estado);

CREATE TABLE IF NOT EXISTS bold_evento (
    id          TEXT PRIMARY KEY,
    payment_id  TEXT,
    tipo        TEXT,
    order_id    TEXT,
    recibido_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload     JSONB
);

CREATE TABLE IF NOT EXISTS riesgo_estudiante (
    codigo         TEXT PRIMARY KEY,
    probabilidad   NUMERIC(5,4) NOT NULL,
    nivel          TEXT NOT NULL,     -- bajo | medio | alto
    factores       JSONB NOT NULL DEFAULT '[]',
    modelo         TEXT NOT NULL,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS modelo_riesgo (
    id           SERIAL PRIMARY KEY,
    nombre       TEXT NOT NULL,
    auc          NUMERIC,
    f1           NUMERIC,
    accuracy     NUMERIC,
    matriz       JSONB,
    importancias JSONB,
    n_train      INT,
    n_test       INT,
    entrenado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
