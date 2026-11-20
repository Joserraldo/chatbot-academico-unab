from pathlib import Path
from tempfile import TemporaryDirectory

import pgserver
import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.conninfo import make_conninfo

from app.main import app

CODIGO = "U90000001"
OTRO = "U90000002"
CLAVE = {"X-Chatbot-Key": "clave-local-sintetica"}
SQL = Path(__file__).resolve().parents[2] / "db" / "init"


def sql_roles():
    """Extrae el SQL de 06_v2_roles.sh para probar con los mismos GRANT que producción."""
    texto = (SQL / "06_v2_roles.sh").read_text(encoding="utf-8")
    cuerpo = texto.split("<<-EOSQL", 1)[1].split("EOSQL", 1)[0]
    cuerpo = cuerpo.replace("\\$", "$").replace("${SERVICIOS_DB_PASSWORD:-cambia_esto}", "cambia_esto")
    return cuerpo


@pytest.fixture(scope="session")
def servidor():
    # Directorio SIN espacios ni tildes: pgserver falla con rutas como "D:/jose sin tilde".
    with TemporaryDirectory(prefix="unab-api-", ignore_cleanup_errors=True) as temporal:
        assert temporal.isascii(), "Configura TEMP y TMP en una ruta sin tildes."
        srv = pgserver.get_server(Path(temporal) / "datos")
        with psycopg.connect(srv.get_uri(), autocommit=True) as conn:
            conn.execute("CREATE ROLE chatbot_ro")
        try:
            yield srv
        finally:
            srv.cleanup()


def crear_base(servidor, nombre, archivos, extra=None):
    """Crea una base con los scripts de db/init y el rol servicios_rw con los GRANT reales."""
    base = servidor.get_uri()
    with psycopg.connect(base, autocommit=True) as conn:
        conn.execute(f"CREATE DATABASE {nombre}")
    dsn = servidor.get_uri(nombre)
    with psycopg.connect(dsn, autocommit=True) as conn:
        for archivo in archivos:
            conn.execute((SQL / archivo).read_text(encoding="utf-8"), prepare=False)
        if extra:
            conn.execute(extra.read_text(encoding="utf-8"), prepare=False)
        conn.execute(sql_roles(), prepare=False)
    return dsn, make_conninfo(dsn, user="servicios_rw", password="cambia_esto")


@pytest.fixture(scope="session")
def postgres(servidor):
    """Base con datos sintéticos propios (periodo 2099-2), aislada de la semilla."""
    esquema = ["01_schema.sql", "02_views.sql", "04_v2_schema.sql"]
    yield crear_base(servidor, "pruebas", esquema, Path(__file__).with_name("fixtures.sql"))


@pytest.fixture(scope="session")
def semilla(servidor):
    """Base con 01-05 (la semilla v2 con las personas U00000201-206) + roles de producción."""
    archivos = ["01_schema.sql", "02_views.sql", "03_seed.sql", "04_v2_schema.sql", "05_v2_seed.sql"]
    yield crear_base(servidor, "semilla", archivos)


@pytest.fixture
def admin(postgres):
    with psycopg.connect(postgres[0], autocommit=True) as conn:
        conn.execute("DELETE FROM servicios.reserva WHERE codigo_estudiante IN (%s, %s)", (CODIGO, OTRO))
        conn.execute("DELETE FROM servicios.pago_orden WHERE codigo_estudiante IN (%s, %s)", (CODIGO, OTRO))
        conn.execute("DELETE FROM servicios.bold_evento WHERE id LIKE 'prueba-api-%%'")
        yield conn


@pytest.fixture
def cliente(postgres, admin, monkeypatch):
    for variable in ("BOLD_API_KEY", "BOLD_SECRET_KEY", "BOLD_WEBHOOK_SECRET", "LLM_BASE_URL", "LLM_API_KEY"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("CHATBOT_KEY", CLAVE["X-Chatbot-Key"])
    monkeypatch.setenv("SERVICIOS_DATABASE_URL", postgres[1])
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://demo.example")
    monkeypatch.setenv("PAGOS_PERMITIR_SIMULADO", "true")
    monkeypatch.setenv("BOLD_MODO", "pruebas")
    with TestClient(app) as cliente:
        app.state.pool.wait(timeout=5)
        yield cliente


@pytest.fixture
def cliente_semilla(semilla, monkeypatch):
    for variable in ("BOLD_API_KEY", "BOLD_SECRET_KEY", "BOLD_WEBHOOK_SECRET", "LLM_BASE_URL", "LLM_API_KEY"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("CHATBOT_KEY", CLAVE["X-Chatbot-Key"])
    monkeypatch.setenv("SERVICIOS_DATABASE_URL", semilla[1])
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://demo.example")
    monkeypatch.setenv("PAGOS_PERMITIR_SIMULADO", "true")
    monkeypatch.setenv("BOLD_MODO", "pruebas")
    with psycopg.connect(semilla[0], autocommit=True) as conn:
        conn.execute("DELETE FROM servicios.pago_orden")
        conn.execute("DELETE FROM servicios.reserva")
    with TestClient(app) as cliente:
        app.state.pool.wait(timeout=5)
        yield cliente
