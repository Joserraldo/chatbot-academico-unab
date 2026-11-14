-- =====================================================================
-- Esquema académico SINTÉTICO que simula Banner/Cosmos (SIS de la UNAB).
-- Ningún dato es real. Sirve para que los agentes del chatbot consulten
-- matrícula, avance del plan, requisitos y cursos de competencias digitales.
-- Compatible con PostgreSQL 16 local (docker) y con Supabase.
-- =====================================================================
CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS academico;
SET search_path TO academico, public;

-- ---------- Catálogo institucional ----------
CREATE TABLE programa (
    id              SERIAL PRIMARY KEY,
    codigo          TEXT UNIQUE NOT NULL,
    nombre          TEXT NOT NULL,
    facultad        TEXT NOT NULL,
    creditos_totales INT NOT NULL,
    semestres       INT NOT NULL,
    version_plan    TEXT
);

CREATE TABLE curso_plan (
    id              SERIAL PRIMARY KEY,
    programa_id     INT NOT NULL REFERENCES programa(id),
    codigo          TEXT NOT NULL,
    nombre          TEXT NOT NULL,
    semestre        INT,                    -- semestre sugerido en el plan
    creditos        INT NOT NULL DEFAULT 0,
    tipo            TEXT NOT NULL DEFAULT 'obligatorio', -- obligatorio | electiva | ...
    area            TEXT,
    UNIQUE (programa_id, codigo)
);

CREATE TABLE prerrequisito (
    curso_id        INT NOT NULL REFERENCES curso_plan(id) ON DELETE CASCADE,
    requiere_id     INT NOT NULL REFERENCES curso_plan(id) ON DELETE CASCADE,
    PRIMARY KEY (curso_id, requiere_id)
);

CREATE TABLE periodo (
    id              SERIAL PRIMARY KEY,
    codigo          TEXT UNIQUE NOT NULL,   -- p.ej. 2026-2
    fecha_inicio    DATE NOT NULL,
    fecha_fin       DATE NOT NULL,
    actual          BOOLEAN NOT NULL DEFAULT FALSE
);

-- ---------- Estudiantes (Banner) ----------
CREATE TABLE estudiante (
    id              SERIAL PRIMARY KEY,
    codigo          TEXT UNIQUE NOT NULL,   -- U00000001 ...
    nombres         TEXT NOT NULL,
    apellidos       TEXT NOT NULL,
    email           TEXT NOT NULL,
    programa_id     INT NOT NULL REFERENCES programa(id),
    cohorte         TEXT NOT NULL,          -- periodo de ingreso
    semestre_actual INT NOT NULL,
    estado          TEXT NOT NULL DEFAULT 'activo' -- activo | inactivo | graduado
);

CREATE TABLE matricula (
    id              SERIAL PRIMARY KEY,
    estudiante_id   INT NOT NULL REFERENCES estudiante(id) ON DELETE CASCADE,
    periodo_id      INT NOT NULL REFERENCES periodo(id),
    estado          TEXT NOT NULL,          -- matriculado | pendiente_pago | preinscrito | aplazado
    valor           NUMERIC(12,0) NOT NULL,
    fecha_pago      DATE,
    creditos_inscritos INT NOT NULL DEFAULT 0,
    UNIQUE (estudiante_id, periodo_id)
);

CREATE TABLE historial_curso (
    id              SERIAL PRIMARY KEY,
    estudiante_id   INT NOT NULL REFERENCES estudiante(id) ON DELETE CASCADE,
    curso_id        INT NOT NULL REFERENCES curso_plan(id),
    periodo_id      INT NOT NULL REFERENCES periodo(id),
    nota            NUMERIC(3,1),           -- 0.0 - 5.0 ; NULL si está cursando
    estado          TEXT NOT NULL           -- aprobado | reprobado | cursando
);
CREATE INDEX ON historial_curso (estudiante_id);

-- ---------- Requisitos de grado ----------
CREATE TABLE requisito_grado (
    id              SERIAL PRIMARY KEY,
    codigo          TEXT UNIQUE NOT NULL,
    nombre          TEXT NOT NULL,
    descripcion     TEXT NOT NULL
);

CREATE TABLE estudiante_requisito (
    estudiante_id   INT NOT NULL REFERENCES estudiante(id) ON DELETE CASCADE,
    requisito_id    INT NOT NULL REFERENCES requisito_grado(id),
    cumplido        BOOLEAN NOT NULL DEFAULT FALSE,
    fecha           DATE,
    detalle         TEXT,
    PRIMARY KEY (estudiante_id, requisito_id)
);

-- ---------- Centro de Competencias Digitales (CCD) ----------
CREATE TABLE curso_cd (
    id              SERIAL PRIMARY KEY,
    codigo          TEXT UNIQUE NOT NULL,
    nombre          TEXT NOT NULL,
    nivel           TEXT NOT NULL,          -- básico | intermedio | avanzado
    horas           INT NOT NULL,
    modalidad       TEXT NOT NULL,          -- virtual | presencial | híbrido
    cuenta_insignia BOOLEAN NOT NULL DEFAULT TRUE,
    descripcion     TEXT
);

CREATE TABLE estudiante_curso_cd (
    estudiante_id   INT NOT NULL REFERENCES estudiante(id) ON DELETE CASCADE,
    curso_cd_id     INT NOT NULL REFERENCES curso_cd(id),
    fecha           DATE NOT NULL,
    estado          TEXT NOT NULL,          -- aprobado | en_curso | no_aprobado
    puntaje         INT,                    -- 0-100
    PRIMARY KEY (estudiante_id, curso_cd_id)
);

CREATE TABLE prueba_diagnostica (
    estudiante_id   INT NOT NULL REFERENCES estudiante(id) ON DELETE CASCADE,
    fecha           DATE NOT NULL,
    puntaje         INT NOT NULL,           -- 0-100
    nivel_asignado  TEXT NOT NULL,
    PRIMARY KEY (estudiante_id, fecha)
);

-- ---------- Calendario (copia de respaldo; la fuente principal es Google Sheets) ----------
CREATE TABLE calendario_evento (
    id              SERIAL PRIMARY KEY,
    periodo         TEXT NOT NULL,
    evento          TEXT NOT NULL,
    categoria       TEXT NOT NULL,          -- inscripciones | diagnostica | inicio_cursos | matricula | ...
    fecha_inicio    DATE NOT NULL,
    fecha_fin       DATE,
    detalle         TEXT
);

-- ---------- Noticias (llenadas por el scraper / workflow 04) ----------
CREATE TABLE noticia (
    id              SERIAL PRIMARY KEY,
    titulo          TEXT NOT NULL,
    url             TEXT UNIQUE NOT NULL,
    resumen         TEXT,
    categoria       TEXT,                   -- curso | convocatoria | certificacion | general
    fuente          TEXT NOT NULL,
    fecha_publicacion DATE,
    capturada_en    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- Auditoría del chatbot (guardrails y evidencias) ----------
CREATE TABLE chat_log (
    id              BIGSERIAL PRIMARY KEY,
    session_id      TEXT NOT NULL,
    codigo_estudiante TEXT,
    intencion       TEXT,
    mensaje         TEXT NOT NULL,
    respuesta       TEXT,
    bloqueado       BOOLEAN NOT NULL DEFAULT FALSE,
    motivo_bloqueo  TEXT,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON chat_log (session_id);
