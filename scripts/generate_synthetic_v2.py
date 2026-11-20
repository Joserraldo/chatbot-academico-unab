"""
Generador de datos SINTÉTICOS v2 para el "Asistente UNAB 360".

Entrada : db/init/03_seed.sql (se LEE para reutilizar estudiantes, plan y matrículas de v1)
Salida  : db/init/05_v2_seed.sql  (se aplica ENCIMA de v1 con psql; idempotente)

Qué agrega: 5 programas nuevos con su plan, 6 estudiantes demo (ids 201-206) con historia
completa, y la capa Cosmos/TEMA/Biblioteca del periodo ACTUAL (2026-2) para los 206 estudiantes,
más enlaces de trámites y espacios reservables.

Determinista (semilla fija). No toca generate_synthetic.py, así que la salida v1 no cambia.
Uso:  python scripts/generate_synthetic_v2.py
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parent.parent
rng = random.Random(2027)

HOY = date(2026, 11, 19)          # "hoy" de la demo (la demo es el 2026-11-20)
ACTUAL_IDX = 11                   # 2026-2 -> periodo id 12
PERIODO_ACTUAL_ID = 12
MULTA_DIA = 1500
HIST_ID_BASE = 100000             # ids explícitos de historial_curso (v1 llega a ~6200)


# ----------------------------------------------------------------------------- utilidades SQL
def q(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def ins(table: str, cols: list[str], rows: list[tuple], chunk: int = 800) -> str:
    out = []
    for i in range(0, len(rows), chunk):
        part = rows[i:i + chunk]
        vals = ",\n".join("(" + ", ".join(q(v) for v in r) + ")" for r in part)
        out.append(f"INSERT INTO {table} ({', '.join(cols)}) VALUES\n{vals}\nON CONFLICT DO NOTHING;\n\n")
    return "".join(out)


def periodos(desde=2021, hasta=2026):
    out = []
    for y in range(desde, hasta + 1):
        out.append((f"{y}-1", date(y, 2, 2), date(y, 6, 13)))
        out.append((f"{y}-2", date(y, 8, 3), date(y, 12, 5)))
    return out


PERS = periodos()


def nota(mu: float, sd: float, lo=0.5, hi=5.0) -> float:
    return round(min(hi, max(lo, rng.gauss(mu, sd))), 1)


# ----------------------------------------------------------------------------- lectura de v1
def leer_v1():
    txt = (ROOT / "db/init/03_seed.sql").read_text(encoding="utf-8")
    isis = []
    for m in re.finditer(r"^\((\d+), 1, '(\w+)', '(.*?)', (\d+), (\d+), '(\w+)', '(\w+)'\)", txt, re.M):
        isis.append(dict(id=int(m[1]), codigo=m[2], nombre=m[3], semestre=int(m[4]), creditos=int(m[5]),
                         tipo=m[6], area=m[7], programa_id=1))
    est = {}
    for m in re.finditer(r"^\((\d+), '(U\d{8})', '(.*?)', '(.*?)', '.*?', 1, '(\d{4}-\d)', (\d+), 'activo'\)", txt, re.M):
        est[int(m[1])] = dict(id=int(m[1]), codigo=m[2], nombres=m[3], apellidos=m[4], cohorte=m[5],
                              semestre=int(m[6]), programa_id=1)
    mat = {}
    for m in re.finditer(r"^\((\d+), (\d+), '(\w+)', (\d+), (NULL|'[\d-]+'), (\d+)\)", txt, re.M):
        mat[(int(m[1]), int(m[2]))] = m[3]
    hist = []
    for m in re.finditer(r"^\((\d+), (\d+), (\d+), (NULL|[\d.]+), '(\w+)'\)", txt, re.M):
        hist.append((int(m[1]), int(m[2]), int(m[3]), None if m[4] == "NULL" else float(m[4]), m[5]))
    assert len(est) == 200 and len(isis) == 48, (len(est), len(isis))
    return isis, est, mat, hist


# ----------------------------------------------------------------------------- programas nuevos
# (nombre, créditos, área, tipo) por semestre. Plan 100% sintético, ilustrativo.
O, E = "obligatorio", "electiva"
PLANES = {
    "MED": dict(id=2, nombre="Medicina", facultad="Facultad de Ciencias de la Salud", semestres=12, valor=16_200_000, plan={
        1: [("Biología Celular y Molecular", 4, "BIOL", O), ("Anatomía Humana I", 5, "ANAT", O), ("Introducción a la Medicina", 3, "MEDI", O)],
        2: [("Bioquímica", 5, "BIOQ", O), ("Anatomía Humana II", 4, "ANAT", O), ("Histología y Embriología", 4, "MORF", O)],
        3: [("Fisiología I", 5, "FISI", O), ("Microbiología y Parasitología", 4, "MICR", O), ("Salud Pública y Epidemiología", 3, "SALU", O)],
        4: [("Fisiología II", 5, "FISI", O), ("Inmunología", 3, "INMU", O), ("Patología General", 4, "PATO", O)],
        5: [("Farmacología I", 4, "FARM", O), ("Semiología Médica", 5, "SEMI", O), ("Bioestadística", 3, "ESTA", O)],
        6: [("Farmacología II", 4, "FARM", O), ("Patología Sistémica", 4, "PATO", O), ("Psicología Médica", 3, "PSIC", O)],
        7: [("Medicina Interna I", 6, "MEDI", O), ("Cirugía General I", 5, "CIRU", O), ("Imagenología", 3, "IMAG", O)],
        8: [("Medicina Interna II", 6, "MEDI", O), ("Pediatría I", 5, "PEDI", O), ("Ginecología y Obstetricia I", 5, "GINE", O)],
        9: [("Pediatría II", 5, "PEDI", O), ("Ginecología y Obstetricia II", 5, "GINE", O), ("Ortopedia y Traumatología", 3, "ORTO", O)],
        10: [("Psiquiatría", 4, "PSIQ", O), ("Urgencias y Medicina Crítica", 5, "URGE", O), ("Medicina Legal y Bioética", 3, "LEGA", O)],
        11: [("Internado Rotatorio I", 12, "INTE", O), ("Electiva Profesional Médica", 3, "ELCT", E)],
        12: [("Internado Rotatorio II", 12, "INTE", O), ("Trabajo de Grado", 4, "INVE", O)],
    }, prereq={
        "Anatomía Humana II": ["Anatomía Humana I"], "Bioquímica": ["Biología Celular y Molecular"],
        "Fisiología I": ["Bioquímica", "Anatomía Humana II"], "Fisiología II": ["Fisiología I"],
        "Inmunología": ["Microbiología y Parasitología"], "Farmacología I": ["Fisiología II"],
        "Farmacología II": ["Farmacología I"], "Medicina Interna I": ["Semiología Médica", "Patología Sistémica"],
        "Medicina Interna II": ["Medicina Interna I"], "Pediatría II": ["Pediatría I"],
        "Ginecología y Obstetricia II": ["Ginecología y Obstetricia I"], "Internado Rotatorio II": ["Internado Rotatorio I"],
    }),
    "DER": dict(id=3, nombre="Derecho", facultad="Facultad de Ciencias Jurídicas y Políticas", semestres=10, valor=9_400_000, plan={
        1: [("Introducción al Derecho", 3, "DERE", O), ("Historia del Derecho Colombiano", 3, "HIST", O), ("Argumentación y Lógica Jurídica", 3, "ARGU", O), ("Sociología Jurídica", 2, "SOCI", O)],
        2: [("Derecho Romano", 3, "DERE", O), ("Derecho Constitucional General", 3, "CONS", O), ("Derecho Civil: Personas", 3, "CIVI", O), ("Metodología de la Investigación Jurídica", 2, "INVE", O)],
        3: [("Derecho Constitucional Colombiano", 3, "CONS", O), ("Derecho Civil: Bienes", 3, "CIVI", O), ("Derecho Penal General", 3, "PENA", O), ("Economía y Derecho", 2, "ECON", O)],
        4: [("Derecho Civil: Obligaciones", 3, "CIVI", O), ("Derecho Penal Especial", 3, "PENA", O), ("Derecho Administrativo General", 3, "ADMI", O), ("Derechos Humanos y DIH", 3, "DEHU", O)],
        5: [("Derecho Civil: Contratos", 3, "CIVI", O), ("Teoría General del Proceso", 3, "PROC", O), ("Derecho Laboral Individual", 3, "LABO", O), ("Derecho Comercial General", 3, "COME", O)],
        6: [("Procedimiento Civil", 4, "PROC", O), ("Derecho Laboral Colectivo", 3, "LABO", O), ("Derecho Societario", 3, "COME", O), ("Procedimiento Penal", 4, "PROC", O)],
        7: [("Derecho de Familia y Sucesiones", 3, "CIVI", O), ("Derecho Probatorio", 3, "PROB", O), ("Derecho Tributario", 3, "TRIB", O), ("Consultorio Jurídico I", 4, "CONJ", O)],
        8: [("Derecho Internacional Público", 3, "INTE", O), ("Derecho Contencioso Administrativo", 3, "ADMI", O), ("Seguridad Social", 3, "LABO", O), ("Consultorio Jurídico II", 4, "CONJ", O)],
        9: [("Derecho Ambiental", 2, "AMBI", O), ("Ética Profesional y Deontología", 2, "ETIC", O), ("Electiva Jurídica I", 3, "ELCT", E), ("Consultorio Jurídico III", 4, "CONJ", O), ("Trabajo de Grado I", 2, "INVE", O)],
        10: [("Electiva Jurídica II", 3, "ELCT", E), ("Trabajo de Grado II", 3, "INVE", O), ("Práctica Jurídica Final", 3, "PRAC", O)],
    }, prereq={
        "Derecho Constitucional Colombiano": ["Derecho Constitucional General"], "Derecho Civil: Bienes": ["Derecho Civil: Personas"],
        "Derecho Civil: Obligaciones": ["Derecho Civil: Bienes"], "Derecho Civil: Contratos": ["Derecho Civil: Obligaciones"],
        "Derecho Penal Especial": ["Derecho Penal General"], "Procedimiento Civil": ["Teoría General del Proceso"],
        "Procedimiento Penal": ["Teoría General del Proceso", "Derecho Penal Especial"],
        "Consultorio Jurídico II": ["Consultorio Jurídico I"], "Consultorio Jurídico III": ["Consultorio Jurídico II"],
        "Trabajo de Grado II": ["Trabajo de Grado I"],
    }),
    "PSI": dict(id=4, nombre="Psicología", facultad="Facultad de Ciencias de la Salud", semestres=10, valor=9_100_000, plan={
        1: [("Introducción a la Psicología", 3, "PSIC", O), ("Neurociencias I", 3, "NEUR", O), ("Epistemología de la Psicología", 3, "FILO", O), ("Lectura y Escritura Académica", 2, "EXPR", O)],
        2: [("Psicología del Desarrollo I", 3, "DESA", O), ("Neurociencias II", 3, "NEUR", O), ("Estadística Aplicada a la Psicología", 3, "ESTA", O), ("Historia de la Psicología", 2, "HIST", O)],
        3: [("Psicología del Desarrollo II", 3, "DESA", O), ("Procesos Cognitivos", 3, "COGN", O), ("Psicología Social", 3, "SOCI", O), ("Metodología de la Investigación", 3, "INVE", O)],
        4: [("Psicología del Aprendizaje", 3, "APRE", O), ("Psicometría", 3, "PSIM", O), ("Teorías de la Personalidad", 3, "PERS", O), ("Motivación y Emoción", 2, "EMOC", O)],
        5: [("Evaluación Psicológica", 4, "EVAL", O), ("Psicopatología I", 3, "PATO", O), ("Psicología Educativa", 3, "EDUC", O), ("Psicología Organizacional I", 3, "ORGA", O)],
        6: [("Psicopatología II", 3, "PATO", O), ("Entrevista Psicológica", 3, "EVAL", O), ("Psicología Clínica I", 4, "CLIN", O), ("Psicología Organizacional II", 3, "ORGA", O)],
        7: [("Psicología Clínica II", 4, "CLIN", O), ("Intervención en Crisis", 3, "CLIN", O), ("Psicología de la Salud", 3, "SALU", O), ("Electiva Psicología I", 3, "ELCT", E)],
        8: [("Terapias Cognitivo-Conductuales", 4, "CLIN", O), ("Psicología Comunitaria", 3, "COMU", O), ("Ética y Deontología", 2, "ETIC", O), ("Práctica Profesional I", 6, "PRAC", O)],
        9: [("Práctica Profesional II", 8, "PRAC", O), ("Electiva Psicología II", 3, "ELCT", E), ("Trabajo de Grado I", 3, "INVE", O)],
        10: [("Práctica Profesional III", 8, "PRAC", O), ("Trabajo de Grado II", 4, "INVE", O)],
    }, prereq={
        "Neurociencias II": ["Neurociencias I"], "Psicología del Desarrollo II": ["Psicología del Desarrollo I"],
        "Psicometría": ["Estadística Aplicada a la Psicología"], "Psicopatología I": ["Teorías de la Personalidad"],
        "Psicopatología II": ["Psicopatología I"], "Psicología Clínica I": ["Evaluación Psicológica"],
        "Psicología Clínica II": ["Psicología Clínica I"], "Práctica Profesional II": ["Práctica Profesional I"],
        "Práctica Profesional III": ["Práctica Profesional II"], "Trabajo de Grado II": ["Trabajo de Grado I"],
    }),
    "ADM": dict(id=5, nombre="Administración de Empresas", facultad="Facultad de Ciencias Económicas, Administrativas y Contables", semestres=9, valor=8_500_000, plan={
        1: [("Fundamentos de Administración", 3, "ADMI", O), ("Matemáticas Básicas", 3, "MATE", O), ("Contabilidad General", 3, "CONT", O), ("Introducción a la Economía", 3, "ECON", O)],
        2: [("Cálculo para Administración", 3, "MATE", O), ("Microeconomía", 3, "ECON", O), ("Contabilidad de Costos", 3, "CONT", O), ("Comportamiento Organizacional", 3, "ORGA", O)],
        3: [("Estadística Descriptiva", 3, "ESTA", O), ("Macroeconomía", 3, "ECON", O), ("Contabilidad Financiera", 3, "CONT", O), ("Derecho Comercial y Laboral", 3, "DERE", O), ("Mercadeo I", 3, "MERC", O)],
        4: [("Estadística Inferencial", 3, "ESTA", O), ("Matemáticas Financieras", 3, "FINA", O), ("Mercadeo II", 3, "MERC", O), ("Gestión del Talento Humano", 3, "TALE", O)],
        5: [("Finanzas Corporativas I", 3, "FINA", O), ("Investigación de Operaciones", 3, "OPER", O), ("Gestión de Operaciones", 3, "OPER", O), ("Sistemas de Información Gerencial", 3, "SIST", O), ("Investigación de Mercados", 3, "MERC", O)],
        6: [("Finanzas Corporativas II", 3, "FINA", O), ("Gestión de Proyectos", 3, "PROY", O), ("Plan de Negocios y Emprendimiento", 3, "EMPR", O), ("Electiva de Administración I", 3, "ELCT", E)],
        7: [("Estrategia Empresarial", 3, "ESTR", O), ("Logística y Cadena de Suministro", 3, "LOGI", O), ("Legislación Tributaria", 3, "TRIB", O), ("Comercio Internacional", 3, "COME", O), ("Electiva de Administración II", 3, "ELCT", E)],
        8: [("Gerencia Estratégica", 3, "ESTR", O), ("Gestión de la Calidad", 3, "CALI", O), ("Consultoría Empresarial", 3, "CONS", O), ("Electiva de Administración III", 3, "ELCT", E)],
        9: [("Práctica Empresarial", 8, "PRAC", O), ("Trabajo de Grado", 4, "INVE", O), ("Liderazgo y Ética Gerencial", 2, "ETIC", O)],
    }, prereq={
        "Cálculo para Administración": ["Matemáticas Básicas"], "Microeconomía": ["Introducción a la Economía"],
        "Contabilidad de Costos": ["Contabilidad General"], "Macroeconomía": ["Microeconomía"],
        "Contabilidad Financiera": ["Contabilidad General"], "Estadística Inferencial": ["Estadística Descriptiva"],
        "Matemáticas Financieras": ["Cálculo para Administración"], "Mercadeo II": ["Mercadeo I"],
        "Finanzas Corporativas I": ["Matemáticas Financieras"], "Finanzas Corporativas II": ["Finanzas Corporativas I"],
        "Gerencia Estratégica": ["Estrategia Empresarial"], "Práctica Empresarial": ["Gerencia Estratégica"],
    }),
    "MEC": dict(id=6, nombre="Ingeniería Mecatrónica", facultad="Facultad de Ingeniería", semestres=10, valor=10_300_000, plan={
        1: [("Cálculo Diferencial", 4, "MATE", O), ("Álgebra Lineal", 3, "MATE", O), ("Introducción a la Ingeniería Mecatrónica", 2, "MECA", O), ("Fundamentos de Programación", 3, "COMP", O)],
        2: [("Cálculo Integral", 4, "MATE", O), ("Física Mecánica", 4, "FISI", O), ("Programación de Computadores", 3, "COMP", O), ("Dibujo y CAD Mecánico", 3, "DIBU", O)],
        3: [("Cálculo Vectorial", 3, "MATE", O), ("Electromagnetismo", 4, "FISI", O), ("Ecuaciones Diferenciales", 3, "MATE", O), ("Estática", 3, "MECA", O)],
        4: [("Dinámica", 3, "MECA", O), ("Circuitos Eléctricos I", 4, "ELEC", O), ("Resistencia de Materiales", 3, "MECA", O), ("Probabilidad y Estadística", 3, "ESTA", O), ("Termodinámica", 3, "TERM", O)],
        5: [("Circuitos Eléctricos II", 3, "ELEC", O), ("Electrónica Analógica", 4, "ELEC", O), ("Mecánica de Fluidos", 3, "MECA", O), ("Ciencia de los Materiales", 3, "MATE", O), ("Métodos Numéricos", 3, "MATE", O)],
        6: [("Electrónica Digital", 4, "ELEC", O), ("Sistemas de Control I", 4, "CONT", O), ("Diseño de Máquinas", 3, "MECA", O), ("Procesos de Manufactura", 3, "MANU", O), ("Microcontroladores", 3, "ELEC", O)],
        7: [("Sistemas de Control II", 4, "CONT", O), ("Instrumentación y Sensores", 3, "ELEC", O), ("Neumática e Hidráulica", 3, "MECA", O), ("Robótica I", 4, "ROBO", O)],
        8: [("Robótica II", 4, "ROBO", O), ("Automatización Industrial y PLC", 4, "AUTO", O), ("Visión Artificial", 3, "COMP", O), ("Electiva de Profundización I", 3, "ELCT", E)],
        9: [("Proyecto de Diseño Mecatrónico", 4, "PROY", O), ("Gestión de Proyectos de Ingeniería", 3, "PROY", O), ("Electiva de Profundización II", 3, "ELCT", E), ("Seminario de Investigación", 2, "INVE", O)],
        10: [("Práctica Profesional", 12, "PRAC", O), ("Trabajo de Grado", 4, "INVE", O)],
    }, prereq={
        "Cálculo Integral": ["Cálculo Diferencial"], "Programación de Computadores": ["Fundamentos de Programación"],
        "Cálculo Vectorial": ["Cálculo Integral"], "Electromagnetismo": ["Física Mecánica", "Cálculo Integral"],
        "Ecuaciones Diferenciales": ["Cálculo Integral", "Álgebra Lineal"], "Dinámica": ["Estática"],
        "Circuitos Eléctricos I": ["Electromagnetismo"], "Circuitos Eléctricos II": ["Circuitos Eléctricos I"],
        "Electrónica Analógica": ["Circuitos Eléctricos I"], "Electrónica Digital": ["Electrónica Analógica"],
        "Sistemas de Control I": ["Ecuaciones Diferenciales", "Circuitos Eléctricos II"], "Sistemas de Control II": ["Sistemas de Control I"],
        "Robótica I": ["Sistemas de Control I", "Microcontroladores"], "Robótica II": ["Robótica I"],
        "Automatización Industrial y PLC": ["Sistemas de Control II"], "Práctica Profesional": ["Proyecto de Diseño Mecatrónico"],
    }),
}

REQUISITOS = ["INGLES_B1", "SABER_PRO", "INSIGNIA_CD", "PRACTICA", "PAZ_SALVO"]   # ids 1..5 (ya existen en v1)

# ----------------------------------------------------------------------------- bibliografía por programa
LIBROS = {
    1: [("Introduction to Algorithms", "Thomas H. Cormen"), ("Clean Code", "Robert C. Martin"),
        ("Ingeniería de Software", "Ian Sommerville"), ("Fundamentos de Bases de Datos", "Abraham Silberschatz"),
        ("Inteligencia Artificial: un enfoque moderno", "Stuart Russell"), ("Redes de Computadoras", "Andrew S. Tanenbaum"),
        ("Cálculo de una Variable", "James Stewart"), ("Estadística para Ingeniería", "Douglas C. Montgomery")],
    2: [("Anatomía Humana", "Frank H. Netter"), ("Tratado de Fisiología Médica", "John E. Hall"),
        ("Harrison. Principios de Medicina Interna", "Dennis L. Kasper"), ("Histología", "Michael H. Ross"),
        ("Bioquímica de Harper", "Victor W. Rodwell"), ("Farmacología Básica y Clínica", "Bertram G. Katzung")],
    3: [("Teoría General del Derecho", "Hans Kelsen"), ("Curso de Derecho Civil", "Arturo Valencia Zea"),
        ("Derecho Constitucional Colombiano", "Manuel José Cepeda"), ("Manual de Derecho Penal", "Fernando Velásquez"),
        ("Derecho Procesal Civil", "Hernando Devis Echandía"), ("Curso de Derecho Laboral", "Guillermo Guerrero Figueroa")],
    4: [("Psicología", "David G. Myers"), ("Principios de Neurociencia", "Eric R. Kandel"),
        ("Psicopatología y Psiquiatría", "Michael B. First"), ("Teorías de la Personalidad", "Duane P. Schultz"),
        ("Psicología del Desarrollo", "Diane E. Papalia"), ("Psicometría", "Anne Anastasi")],
    5: [("Administración", "Stephen P. Robbins"), ("Fundamentos de Finanzas Corporativas", "Stephen A. Ross"),
        ("Marketing", "Philip Kotler"), ("Contabilidad Financiera", "Jerry J. Weygandt"),
        ("Administración de Operaciones", "Jay Heizer"), ("Estrategia Competitiva", "Michael E. Porter")],
    6: [("Ingeniería de Control Moderna", "Katsuhiko Ogata"), ("Mecatrónica: Sistemas de Control Electrónico", "William Bolton"),
        ("Introducción a la Mecánica de Fluidos", "Robert W. Fox"), ("Electrónica: Teoría de Circuitos", "Robert L. Boylestad"),
        ("Robótica", "John J. Craig"), ("Diseño en Ingeniería Mecánica de Shigley", "Richard G. Budynas")],
}

DOCENTES = [
    "Carlos Eduardo Mendoza Ruiz", "Luz Marina Cáceres Ortiz", "Jorge Armando Valdivieso", "Martha Cecilia Jaimes Rey",
    "Hernán Darío Pabón Gómez", "Claudia Patricia Rangel", "Ricardo Andrés Villamizar", "Sandra Milena Arenas",
    "Fabio Alberto Ordóñez", "Diana Carolina Toscano", "Édgar Leonardo Camargo", "Patricia Elena Ballesteros",
    "Wilson Fernando Mejía", "Ángela María Plata", "Néstor Raúl Silva Cárdenas", "Yolanda Beatriz Acevedo",
    "Gustavo Adolfo Rincón", "Liliana Andrea Bohórquez", "Mauricio José Parra", "Rocío Esperanza Villabona",
    "Álvaro Javier Díaz Mora", "Gloria Inés Santos", "Rafael Antonio Cortés", "Marcela Johanna Uribe", "Henry Alexander Peña",
]

DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"]


# ----------------------------------------------------------------------------- historia académica
def construir_historia(est_id, por_sem, sem, nota_fn, overrides=None, omitir=(), saltar=()):
    """Como v1: un semestre por periodo hasta el actual; lo reprobado pasa a la carga siguiente.
    overrides {(nombre, per_id): nota}; omitir {nombre} (nunca se cursa); saltar {(nombre, per_id)}."""
    overrides = overrides or {}
    cohorte_idx = ACTUAL_IDX - (sem - 1)
    hist, mat_cred = [], []
    pend = []
    for k in range(sem):
        per_id = cohorte_idx + k + 1
        actual = per_id == PERIODO_ACTUAL_ID
        carga = [c for c in pend]
        pend = []
        carga += [c for c in por_sem.get(k + 1, []) if c["nombre"] not in omitir]
        cursadas = []
        for c in carga:
            if (c["nombre"], per_id) in saltar:
                pend.append(c)
                continue
            cursadas.append(c)
            if actual:
                hist.append((est_id, c["id"], per_id, None, "cursando"))
                continue
            n = overrides.get((c["nombre"], per_id), nota_fn(c))
            est = "aprobado" if n >= 3.0 else "reprobado"
            hist.append((est_id, c["id"], per_id, n, est))
            if est == "reprobado":
                pend.append(c)
        mat_cred.append((per_id, sum(c["creditos"] for c in cursadas)))
    return hist, mat_cred, cohorte_idx


# ----------------------------------------------------------------------------- main
def main():
    isis, est1, mat1, hist1 = leer_v1()
    sql = ["-- GENERADO por scripts/generate_synthetic_v2.py — NO editar. Datos 100% sintéticos.\n",
           "-- Se aplica ENCIMA de v1 (01-04). Idempotente: ON CONFLICT DO NOTHING con ids explícitos.\n",
           "SET search_path TO academico, public;\n\n"]

    # ---- 1. programas y planes
    programas, cursos, prereqs = [], [], []
    por_programa: dict[int, dict[int, list[dict]]] = {1: {}}
    for c in isis:
        por_programa[1].setdefault(c["semestre"], []).append(c)
    next_id = 1000
    for cod, p in PLANES.items():
        por_programa[p["id"]] = {}
        por_nombre, cont = {}, {}
        for sem, lst in p["plan"].items():
            for nombre, cred, area, tipo in lst:
                cont[(area, sem)] = cont.get((area, sem), 0) + 1
                c = dict(id=next_id, programa_id=p["id"], codigo=f"{area}{sem}{cont[(area, sem)]:02d}", nombre=nombre,
                         semestre=sem, creditos=cred, tipo=tipo, area=area)
                next_id += 1
                cursos.append(c)
                por_nombre[nombre] = c["id"]
                por_programa[p["id"]].setdefault(sem, []).append(c)
        for k, reqs in p["prereq"].items():
            for r in reqs:
                prereqs.append((por_nombre[k], por_nombre[r]))
        total = sum(c["creditos"] for c in cursos if c["programa_id"] == p["id"])
        p["creditos_totales"] = total
        programas.append((p["id"], cod, p["nombre"], p["facultad"], total, p["semestres"], "sintético 2026"))
    todos_cursos = {c["id"]: c for c in isis + cursos}
    sql.append(ins("academico.programa", ["id", "codigo", "nombre", "facultad", "creditos_totales", "semestres", "version_plan"], programas))
    sql.append(ins("academico.curso_plan", ["id", "programa_id", "codigo", "nombre", "semestre", "creditos", "tipo", "area"],
                   [(c["id"], c["programa_id"], c["codigo"], c["nombre"], c["semestre"], c["creditos"], c["tipo"], c["area"]) for c in cursos]))
    sql.append(ins("academico.prerrequisito", ["curso_id", "requiere_id"], prereqs))

    # ---- 2. estudiantes demo
    ABIL = {}
    DEMO = [
        # id, nombres, apellidos, programa, semestre
        (201, "Santiago", "Ardila Mantilla", 1, 9),
        (202, "Valentina", "Quintero Reyes", 2, 4),
        (203, "Juan Camilo", "Gélvez Prada", 3, 10),
        (204, "Sofía", "Carreño Duarte", 4, 1),
        (205, "Andrés Felipe", "Pinzón Niño", 5, 5),
        (206, "Nicolás", "Barrera Galvis", 6, 6),
    ]
    est_rows, mat_rows, hist_rows, ereq_rows, ecd_rows, diag_rows = [], [], [], [], [], []
    inscritos_demo = {}
    hist_all = list(hist1)  # (est, curso, per, nota, estado) de v1 + demo (para secciones)
    hid = HIST_ID_BASE

    def sin_tilde(s):
        return s.lower().translate(str.maketrans("áéíóúñü ", "aeiounu."))

    perfiles = {
        201: dict(fn=lambda c: nota(4.75, 0.17, 4.3, 5.0)),
        202: dict(fn=lambda c: nota(3.5, 0.3, 3.0, 4.2),
                  over={("Histología y Embriología", 10): 2.3, ("Microbiología y Parasitología", 11): 2.5},
                  omitir={"Inmunología"}, saltar={("Histología y Embriología", 11)}),
        203: dict(fn=lambda c: nota(3.9, 0.3, 3.2, 4.8)),
        204: dict(fn=lambda c: 3.5),
        205: dict(fn=lambda c: nota(3.7, 0.4, 3.0, 4.6)),
        206: dict(fn=lambda c: nota(3.6, 0.4, 3.0, 4.5)),
    }
    for eid, nom, ape, pid, sem in DEMO:
        pr = perfiles[eid]
        hist, mc, cidx = construir_historia(eid, por_programa[pid], sem, pr["fn"], pr.get("over"), pr.get("omitir", ()), pr.get("saltar", ()))
        email = f"{sin_tilde(nom.split()[0])}.{sin_tilde(ape.split()[0])}{eid}@unab.edu.co"
        est_rows.append((eid, f"U{eid:08d}", nom, ape, email, pid, PERS[cidx][0], sem, "activo"))
        prog = next(p for p in PLANES.values() if p["id"] == pid) if pid != 1 else dict(valor=9_850_000)
        for per_id, cred in mc:
            actual = per_id == PERIODO_ACTUAL_ID
            valor = prog["valor"]
            if actual and eid == 205:
                mat_rows.append((eid, per_id, "pendiente_pago", 8_500_000, None, cred))
            elif actual:
                mat_rows.append((eid, per_id, "matriculado", valor, "2026-08-01", cred))
            else:
                mat_rows.append((eid, per_id, "matriculado", valor, PERS[per_id - 1][1].replace(day=1).isoformat(), cred))
        for h in hist:
            hist_rows.append((hid,) + h)
            hid += 1
        hist_all += hist
        ABIL[eid] = {201: 4.8, 202: 2.9, 203: 3.9, 204: 3.4, 205: 3.7, 206: 3.6}[eid]
        # competencias digitales + diagnóstica (ids curso_cd de v1: B01=1 B02=2 B03=3 B04=4 I01=5 I02=6 A01=9)
        cd = {201: [(1, 91), (6, 95), (9, 88)], 202: [], 203: [(1, 84), (2, 79)], 204: [],
              205: [(4, 82)], 206: [(1, 76)]}[eid]
        for cid, pt in cd:
            ecd_rows.append((eid, cid, (PERS[cidx][1] + timedelta(days=200 + cid * 9)).isoformat(), "aprobado", pt))
        if eid == 202:
            ecd_rows.append((eid, 2, "2026-09-28", "en_curso", None))
        if eid == 206:
            ecd_rows.append((eid, 5, "2026-09-28", "en_curso", None))
        pd_ = {201: 96, 202: 71, 203: 83, 204: 58, 205: 74, 206: 79}[eid]
        diag_rows.append((eid, PERS[cidx][1].isoformat(), pd_, "básico" if pd_ < 60 else "intermedio" if pd_ < 80 else "avanzado"))
        fin = PERS[ACTUAL_IDX - 1][2].isoformat()
        cumplidos = {201: {"INGLES_B1", "SABER_PRO", "INSIGNIA_CD"}, 202: set(), 203: {"INGLES_B1"},
                     204: set(), 205: {"INGLES_B1"}, 206: set()}[eid]
        for rid, rc in enumerate(REQUISITOS, start=1):
            ok = rc in cumplidos
            ereq_rows.append((eid, rid, ok, fin if ok else None, "Certificado sintético" if ok else None))

    sql.append(ins("academico.estudiante", ["id", "codigo", "nombres", "apellidos", "email", "programa_id", "cohorte", "semestre_actual", "estado"], est_rows))
    sql.append(ins("academico.matricula", ["estudiante_id", "periodo_id", "estado", "valor", "fecha_pago", "creditos_inscritos"], mat_rows))
    sql.append(ins("academico.historial_curso", ["id", "estudiante_id", "curso_id", "periodo_id", "nota", "estado"], hist_rows))
    sql.append(ins("academico.estudiante_requisito", ["estudiante_id", "requisito_id", "cumplido", "fecha", "detalle"], ereq_rows))
    sql.append(ins("academico.estudiante_curso_cd", ["estudiante_id", "curso_cd_id", "fecha", "estado", "puntaje"], ecd_rows))
    sql.append(ins("academico.prueba_diagnostica", ["estudiante_id", "fecha", "puntaje", "nivel_asignado"], diag_rows))

    # ---- estudiantes (v1 + demo) para la capa Cosmos/TEMA/Biblioteca
    estudiantes = {}
    sums = {}
    for (e, c, p, n, s) in hist1:
        if n is not None:
            sums.setdefault(e, []).append(n)
    for eid, e in est1.items():
        estudiantes[eid] = dict(codigo=e["codigo"], programa_id=1, hab=sum(sums[eid]) / len(sums[eid]) if eid in sums else 3.7)
    for eid, nom, ape, pid, sem in DEMO:
        estudiantes[eid] = dict(codigo=f"U{eid:08d}", programa_id=pid, hab=ABIL[eid])
    estado_mat = {}
    for eid in est1:
        estado_mat[eid] = mat1.get((eid, PERIODO_ACTUAL_ID), "sin_matricula")
    for r in mat_rows:
        if r[1] == PERIODO_ACTUAL_ID:
            estado_mat[r[0]] = r[2]

    cursando = {}          # est -> [curso_id]
    for (e, c, p, n, s) in hist_all:
        if p == PERIODO_ACTUAL_ID and s == "cursando":
            cursando.setdefault(e, []).append(c)
    inscribibles = {e for e, st in estado_mat.items() if st in ("matriculado", "pendiente_pago")}
    cursos_cursando = sorted({c for e, lst in cursando.items() for c in lst})
    alumnos_curso = {c: [e for e in sorted(cursando) if c in cursando[e] and e in inscribibles] for c in cursos_cursando}

    # ---- 4a. docentes y secciones (sin choques de horario de estudiantes, docentes ni salones)
    docentes = [(i + 1, n, f"{sin_tilde(n.split()[0])}.{sin_tilde(n.split()[-1])}@unab.edu.co") for i, n in enumerate(DOCENTES)]
    sql.append(ins("academico.docente", ["id", "nombre", "email"], docentes))

    plantillas = []
    for par in [("Lun", "Mié"), ("Mar", "Jue"), ("Lun", "Jue"), ("Mar", "Vie"), ("Mié", "Vie"), ("Lun", "Vie"), ("Jue", "Sáb")]:
        for h in range(7, 20):
            plantillas.append(([(par[0], h, 2), (par[1], h, 2)]))
    for h in (7, 13):
        plantillas.append([("Sáb", h + 1, 4)])

    def horas(ses):
        return {(d, h + i) for d, h, dur in ses for i in range(dur)}

    ocup_est: dict[int, set] = {e: set() for e in estudiantes}
    ocup_doc: dict[int, set] = {d[0]: set() for d in docentes}
    ocup_salon: dict[str, set] = {}
    secciones, choques = [], 0
    orden = sorted(cursos_cursando, key=lambda c: (-len(alumnos_curso[c]), c))
    edificios = {1: "Edificio L", 2: "Edificio Salud", 3: "Edificio Jurídico", 4: "Edificio Salud", 5: "Edificio B", 6: "Edificio K"}
    for cid in orden:
        al = alumnos_curso[cid]
        cands = plantillas[:]
        rng.shuffle(cands)
        mejor = None
        for cand in cands:
            hs = horas(cand)
            n_ch = sum(1 for e in al if ocup_est[e] & hs)
            if mejor is None or n_ch < mejor[0]:
                mejor = (n_ch, cand)
            if n_ch == 0:
                break
        n_ch, ses = mejor
        choques += n_ch
        hs = horas(ses)
        docs = [d[0] for d in docentes]
        rng.shuffle(docs)
        doc = next((d for d in docs if not (ocup_doc[d] & hs)), docs[0])
        pid = todos_cursos[cid]["programa_id"]
        for _ in range(200):
            salon = f"{edificios[pid]} - {rng.choice([1, 2, 3, 4])}{rng.randint(1, 15):02d}"
            if not (ocup_salon.get(salon, set()) & hs):
                break
        for e in al:
            ocup_est[e] |= hs
        ocup_doc[doc] |= hs
        ocup_salon.setdefault(salon, set()).update(hs)
        horario = "; ".join(f"{d} {h:02d}:00-{h + dur:02d}:00" for d, h, dur in ses)
        secciones.append(dict(id=0, curso_id=cid, doc=doc, grupo=rng.choice(["A", "A", "B"]), horario=horario, salon=salon))
    secciones.sort(key=lambda s: s["curso_id"])
    for i, s in enumerate(secciones, start=1):
        s["id"] = i
    sec_de = {s["curso_id"]: s for s in secciones}
    sql.append(ins("academico.seccion", ["id", "curso_id", "periodo_id", "docente_id", "grupo", "horario", "salon"],
                   [(s["id"], s["curso_id"], PERIODO_ACTUAL_ID, s["doc"], s["grupo"], s["horario"], s["salon"]) for s in secciones]))

    # ---- 4b. inscripciones, notas parciales, tareas, entregas, evaluación docente
    insc, parc, tareas, entregas, evals = [], [], [], [], []
    TIPOS = ["tarea", "quiz", "foro", "proyecto"]
    tid = 1
    for s in secciones:
        curso = todos_cursos[s["curso_id"]]
        n = rng.randint(2, 4)
        tipos = ["tarea", "quiz"] + rng.choices(TIPOS, [4, 2, 2, 2], k=n - 2)
        rng.shuffle(tipos)
        pesos = {2: [50, 50], 3: [30, 30, 40], 4: [20, 20, 30, 30]}[n]
        s["tareas"] = []
        for k, tp in enumerate(tipos):
            titulo = {"tarea": f"Taller {k + 1}: {curso['nombre']}", "quiz": f"Quiz {k + 1} de {curso['nombre']}",
                      "foro": f"Foro de discusión: {curso['nombre']}", "proyecto": f"Entrega del proyecto de {curso['nombre']}"}[tp]
            dia = date(2026, 11, 5) + timedelta(days=rng.randint(0, 30))
            dt = f"{dia.isoformat()} 23:59:00-05"
            tareas.append((tid, s["id"], titulo, tp, dt, pesos[k]))
            s["tareas"].append((tid, dia))
            tid += 1

    ev_forzada: dict[int, int] = {}
    for eid in sorted(estudiantes):
        if eid not in inscribibles:
            continue
        hab = estudiantes[eid]["hab"]
        mis = [sec_de[c] for c in cursando.get(eid, [])]
        mis.sort(key=lambda s: s["id"])
        p_venc = 0.0 if eid == 201 else 0.30 if eid == 202 else min(0.35, 0.04 + max(0.0, 3.6 - hab) * 0.12)
        forzar_venc = 2 if eid == 202 else 0
        for s in mis:
            insc.append((eid, s["id"]))
            # notas por corte: 1 y 2 calificados (30 % c/u); el corte 3 (40 %) aún no
            if eid == 201:
                mu, sd = 4.7, 0.2
            elif eid == 202:
                mu, sd = 2.4, 0.4
            elif eid == 204:
                mu, sd = 3.5, 0.3
            else:
                mu, sd = hab, 0.5
            n1 = nota(mu, sd, 1.0 if eid == 202 else 0.5, 3.0 if eid == 202 else 5.0)
            n2 = nota(mu + (0.2 if eid == 202 else 0), sd, 1.0 if eid == 202 else 0.5, 3.4 if eid == 202 else 5.0)
            if eid == 201:
                n1, n2 = max(n1, 4.3), max(n2, 4.3)
            parc += [(eid, s["id"], 1, 30, n1), (eid, s["id"], 2, 30, n2), (eid, s["id"], 3, 40, None)]
            for t_id, dia in s["tareas"]:
                if dia < HOY:
                    if forzar_venc > 0:
                        est, nt = "vencida", None
                        forzar_venc -= 1
                    elif rng.random() < p_venc:
                        est, nt = "vencida", None
                    elif dia <= HOY - timedelta(days=5):
                        est, nt = "calificada", nota(hab if eid != 202 else 3.0, 0.5, 1.0, 5.0)
                    else:
                        est, nt = "entregada", None
                else:
                    est, nt = ("entregada", None) if rng.random() < (0.25 if eid != 202 else 0.05) else ("pendiente", None)
                entregas.append((eid, t_id, est, nt))
            if rng.random() < 0.55 and eid != 201:
                evals.append([eid, s["id"], "pendiente", "2026-11-28"])
            else:
                evals.append([eid, s["id"], "completada", "2026-11-28"])
        # garantías de la historia de cada demo
        mine = [e for e in evals if e[0] == eid]
        pend = [e for e in mine if e[2] == "pendiente"]
        if eid == 201:
            for e in mine:
                e[2] = "completada"
            mine[0][2] = "pendiente"          # exactamente 1 evaluación pendiente
        elif eid >= 202 and not pend and mine:
            mine[0][2] = "pendiente"
    evals = [tuple(e) for e in evals]

    sql.append(ins("academico.inscripcion_seccion", ["estudiante_id", "seccion_id"], insc))
    sql.append(ins("academico.nota_parcial", ["estudiante_id", "seccion_id", "corte", "porcentaje", "nota"], parc))
    sql.append(ins("academico.tarea_tema", ["id", "seccion_id", "titulo", "tipo", "fecha_entrega", "peso"], tareas))
    sql.append(ins("academico.entrega_tema", ["estudiante_id", "tarea_id", "estado", "nota"], entregas))
    sql.append(ins("academico.evaluacion_docente", ["estudiante_id", "seccion_id", "estado", "fecha_limite"], evals))

    # ---- 4c. biblioteca
    prestamos, pid_ = [], 1

    def add_prestamo(eid, libro, prest, venc, ren, estado):
        nonlocal pid_
        multa = MULTA_DIA * (HOY - venc).days if estado == "vencido" else 0
        prestamos.append((pid_, eid, libro[0], libro[1], prest.isoformat(), venc.isoformat(), ren, estado, multa))
        pid_ += 1

    fijos = {
        201: [("Clean Code", "Robert C. Martin"), "activo", date(2026, 11, 9), date(2026, 11, 23), 0],
        202: [("Anatomía Humana", "Frank H. Netter"), "activo", date(2026, 11, 12), date(2026, 11, 26), 0],
        203: [("Manual de Derecho Penal", "Fernando Velásquez"), "activo", date(2026, 11, 2), date(2026, 11, 23), 1],
        204: [("Psicología", "David G. Myers"), "activo", date(2026, 11, 10), date(2026, 11, 24), 0],
        205: [("Marketing", "Philip Kotler"), "devuelto", date(2026, 10, 1), date(2026, 10, 15), 0],
    }
    for eid, (libro, estado, pr, vc, rn) in fijos.items():
        add_prestamo(eid, libro, pr, vc, rn, estado)
    # 206: préstamo VENCIDO con multa + uno activo
    add_prestamo(206, ("Introducción a la Mecánica de Fluidos", "Robert W. Fox"), date(2026, 10, 14), date(2026, 11, 4), 1, "vencido")
    add_prestamo(206, ("Ingeniería de Control Moderna", "Katsuhiko Ogata"), date(2026, 11, 9), date(2026, 11, 23), 0, "activo")
    for eid in sorted(est1):
        if rng.random() >= 0.40:
            continue
        for _ in range(rng.choice([1, 1, 2])):
            libro = rng.choice(LIBROS[1])
            r = rng.random()
            if r < 0.50:
                pr = HOY - timedelta(days=rng.randint(1, 12))
                ren = rng.choice([0, 0, 1])
                add_prestamo(eid, libro, pr, pr + timedelta(days=14 + 7 * ren), ren, "activo")
            elif r < 0.65:
                vc = HOY - timedelta(days=rng.randint(2, 25))
                ren = rng.choice([0, 1])
                add_prestamo(eid, libro, vc - timedelta(days=14 + 7 * ren), vc, ren, "vencido")
            else:
                pr = HOY - timedelta(days=rng.randint(20, 120))
                ren = rng.choice([0, 1, 2])
                add_prestamo(eid, libro, pr, pr + timedelta(days=14 + 7 * ren), ren, "devuelto")
    sql.append(ins("academico.prestamo_biblioteca", ["id", "estudiante_id", "titulo", "autor", "fecha_prestamo", "fecha_vencimiento", "renovaciones", "estado", "multa"], prestamos))

    # ---- 5. enlaces de trámites (URLs verificadas con curl el 2026-11-19; ver docs/CONTRATOS-V2.md)
    RES = "https://reservas.unab.edu.co/auth/login"
    enlaces = [
        ("reservas", "Reservas UNAB", RES,
         "Plataforma institucional para reservar espacios, el gimnasio y escenarios deportivos.",
         "1. Ingresa a la plataforma de reservas con tu cuenta institucional UNAB.\n2. Elige el espacio que necesitas (sala de estudio, auditorio, cancha, laboratorio, sala de música o gimnasio).\n3. Selecciona la fecha y la franja horaria disponible.\n4. Confirma la reserva. Si el espacio tiene tarifa, el sistema te indica cómo pagar; las salas de estudio y el gimnasio son gratis.\n5. Revisa tu correo UNAB: allí llega la confirmación.",
         ["reserva", "reservar", "espacio", "sala", "salas de estudio", "auditorio", "cancha", "laboratorio", "sala de música", "escenario deportivo"]),
        ("biblioteca_renovar", "Renovar préstamos de biblioteca", "https://catalogo.unab.edu.co/",
         "Catálogo de la Biblioteca UNAB. Es el enlace del QR del cartel \"Renueva tus préstamos y evita sanciones\".",
         "1. Escanea el código QR del cartel \"Renueva tus préstamos y evita sanciones\" o abre el enlace del catálogo.\n2. Inicia sesión con tu cuenta UNAB.\n3. Entra a \"Mi cuenta\" y abre la lista de tus préstamos.\n4. Selecciona el material y pulsa \"Renovar\" antes de la fecha de vencimiento.\n5. Si el préstamo ya venció, la multa es de $1.500 COP por día de retraso y debes pagarla antes de renovar.",
         ["biblioteca", "renovar", "renovación", "préstamo", "prestamo", "libro", "multa", "sanción", "devolver", "catálogo"]),
        ("gimnasio", "Gimnasio (Bienestar Universitario)", RES,
         "El gimnasio se reserva en la misma plataforma de reservas; es gratis para estudiantes.",
         "1. Ingresa a la plataforma de reservas con tu cuenta institucional UNAB.\n2. Busca el espacio \"Gimnasio\".\n3. Escoge el día y la franja horaria con cupo.\n4. Confirma la reserva; no tiene costo para estudiantes activos.\n5. Llega 10 minutos antes con tu carné y ropa deportiva.",
         ["gimnasio", "gym", "ejercicio", "deporte", "bienestar", "entrenar", "pesas"]),
        ("cosmos", "Cosmos", "https://cosmos.unab.edu.co/",
         "Sistema académico: notas por corte, horario, historial y datos de matrícula.",
         "1. Ingresa a Cosmos con tu usuario y contraseña institucionales.\n2. En \"Notas\" consulta las calificaciones por corte (30 %, 30 % y 40 %) del periodo actual.\n3. En \"Horario\" revisa tus clases, salones y docentes.\n4. En \"Historial\" descarga tu registro de notas y créditos aprobados.",
         ["cosmos", "notas", "calificaciones", "corte", "horario", "historial", "matrícula", "créditos"]),
        ("tema", "TEMA", "https://tema.unab.edu.co/",
         "Plataforma virtual de cursos: tareas, quices, foros y materiales de cada asignatura.",
         "1. Ingresa a TEMA con tu cuenta institucional.\n2. Abre el curso (sección) que quieres revisar.\n3. En el calendario o en cada curso verás las tareas, quices y foros con su fecha de entrega.\n4. Sube tu entrega antes de la fecha límite (23:59) y verifica que quede en estado \"entregada\".",
         ["tema", "tarea", "tareas", "quiz", "foro", "entrega", "aula virtual", "plataforma", "moodle"]),
        ("evaluacion_docente", "Evaluación docente", "https://tema.unab.edu.co/",
         "Calificación anónima de tus profesores al final del periodo. Se hace desde TEMA (o Cosmos).",
         "1. Ingresa a TEMA (https://tema.unab.edu.co/) o a Cosmos (https://cosmos.unab.edu.co/) con tu cuenta institucional.\n2. Abre la opción \"Evaluación docente\".\n3. Selecciona cada profesor pendiente y responde el cuestionario.\n4. Envía la evaluación antes de la fecha límite (2026-11-28 en 2026-2). Es anónima.",
         ["evaluación docente", "evaluacion docente", "calificar al profesor", "calificar profesor", "encuesta docente", "evaluar docente"]),
        ("unab", "Portal UNAB", "https://unab.edu.co",
         "Portal principal de la Universidad Autónoma de Bucaramanga.",
         "1. Ingresa al portal principal de la UNAB.\n2. Usa el buscador o el menú para encontrar programas, calendario académico, bienestar y servicios.\n3. Para trámites con usuario, entra a Cosmos, TEMA o la plataforma de reservas con tu cuenta institucional.",
         ["unab", "portal", "universidad", "información general", "página web", "contacto"]),
    ]
    filas = []
    for cod, nom, url, desc, pasos, kw in enlaces:
        arr = "ARRAY[" + ", ".join(q(k) for k in kw) + "]::text[]"
        filas.append(f"({q(cod)}, {q(nom)}, {q(url)}, {q(desc)}, {q(pasos)}, {arr})")
    sql.append("INSERT INTO academico.enlace_tramite (codigo, nombre, url, descripcion, pasos, palabras_clave) VALUES\n"
               + ",\n".join(filas) + "\nON CONFLICT DO NOTHING;\n\n")

    # ---- 3. personas demo (U00000001 se describe con datos reales del seed v1)
    h1 = [h for h in hist1 if h[0] == 1]
    ap = sum(todos_cursos[h[1]]["creditos"] for h in h1 if h[4] == "aprobado")
    pond = sum(h[3] * todos_cursos[h[1]]["creditos"] for h in h1 if h[3] is not None) / sum(todos_cursos[h[1]]["creditos"] for h in h1 if h[3] is not None)
    rep = sorted({todos_cursos[h[1]]["nombre"] for h in h1 if h[4] == "reprobado"})
    d1 = f"Semestre 6, promedio {pond:.1f} y {ap / 151 * 100:.0f} % de avance"
    if rep:
        d1 += f", con {len(rep)} cursos reprobados (p. ej. Estadística General). Pregúntale cómo recuperarlos y qué le falta para avanzar"
    personas = [
        ("U00000001", "Laura · Sistemas · semestre 6", d1 + ".", "🧑‍💻", 1),
        ("U00000201", "Santiago · Sistemas · casi graduado", "Pregúntale qué requisitos de grado le faltan y qué necesita para graduarse.", "🎓", 2),
        ("U00000202", "Valentina · Medicina · en riesgo", "Pregúntale por su riesgo académico y sus tareas vencidas.", "🩺", 3),
        ("U00000203", "Juan Camilo · Derecho · cerca del grado", "Pregúntale cuántos semestres le quedan y qué requisitos de grado tiene pendientes.", "⚖️", 4),
        ("U00000204", "Sofía · Psicología · primer semestre", "Pregúntale por su horario, el calendario y cómo moverse en la universidad.", "🧠", 5),
        ("U00000205", "Andrés Felipe · Administración · matrícula pendiente", "Pídele pagar su matrícula 2026-2 con Bold (modo pruebas).", "💼", 6),
        ("U00000206", "Nicolás · Mecatrónica · multa de biblioteca", "Pregúntale por su préstamo vencido: renovar en el catálogo y pagar la multa.", "🤖", 7),
    ]
    sql.append(ins("academico.persona_demo", ["codigo", "titulo", "descripcion", "emoji", "orden"], personas))

    # ---- 6. espacios
    CJ = "Campus El Jardín"
    esp = [
        (1, "SALA-BIB-1", "Sala de estudio 1", "sala_estudio", f"{CJ} - Biblioteca", 6, 0, "Sala individual/pequeño grupo, silenciosa, con tomas y tablero."),
        (2, "SALA-BIB-2", "Sala de estudio 2", "sala_estudio", f"{CJ} - Biblioteca", 8, 0, "Sala para grupos pequeños con tablero y pantalla."),
        (3, "SALA-BIB-3", "Sala de estudio 3", "sala_estudio", f"{CJ} - Biblioteca", 10, 0, "Sala de trabajo en grupo con pantalla y HDMI."),
        (4, "SALA-BIB-4", "Sala de estudio grupal 4", "sala_estudio", f"{CJ} - Biblioteca", 12, 0, "Sala amplia para proyectos y presentaciones."),
        (5, "AUD-MAYOR", "Auditorio Mayor", "auditorio", CJ, 400, 180000, "Auditorio con sonido, proyección y camerinos para eventos."),
        (6, "CANCHA-SINT", "Cancha sintética fútbol 7", "cancha", "Campus Cañaveral", 14, 90000, "Cancha sintética con iluminación nocturna."),
        (7, "LAB-MAC", "Laboratorio Mac", "laboratorio", f"{CJ} - Edificio de Ingeniería, piso 4", 30, 60000, "30 equipos Mac con Xcode, Final Cut y suite Adobe."),
        (8, "SALA-MUSICA", "Sala de música y ensayo", "musica", "Bienestar Universitario", 8, 25000, "Sala insonorizada con batería, amplificadores y teclado."),
        (9, "GIMNASIO", "Gimnasio", "gimnasio", "Bienestar Universitario", 40, 0, "Zona de pesas, cardio y funcional; gratis para estudiantes."),
        (10, "CANCHA-MULT", "Cancha múltiple cubierta", "cancha", "Campus Cañaveral", 20, 45000, "Baloncesto, voleibol y microfútbol bajo techo."),
    ]
    sql.append(ins("servicios.espacio", ["id", "codigo", "nombre", "tipo", "sede", "capacidad", "tarifa_hora", "descripcion"], esp))

    # ---- secuencias (los ids explícitos no avanzan los SERIAL)
    sql.append("-- Alinear las secuencias con los ids explícitos para que los INSERT futuros no choquen\n")
    for tabla in ["programa", "curso_plan", "estudiante", "historial_curso", "matricula", "docente", "seccion", "tarea_tema", "prestamo_biblioteca"]:
        sql.append(f"SELECT setval(pg_get_serial_sequence('academico.{tabla}', 'id'), (SELECT MAX(id) FROM academico.{tabla}));\n")
    sql.append("SELECT setval(pg_get_serial_sequence('servicios.espacio', 'id'), (SELECT MAX(id) FROM servicios.espacio));\n")

    out = ROOT / "db/init/05_v2_seed.sql"
    out.write_text("".join(sql), encoding="utf-8")
    print(f"OK: {len(secciones)} secciones, {len(insc)} inscripciones, {len(tareas)} tareas, {len(entregas)} entregas, "
          f"{len(prestamos)} préstamos, choques de horario={choques} -> {out}")


if __name__ == "__main__":
    main()
