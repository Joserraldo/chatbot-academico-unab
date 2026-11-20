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


@pytest.fixture(scope="session")
def postgres():
    with TemporaryDirectory(prefix="unab-api-", ignore_cleanup_errors=True) as temporal:
        assert temporal.isascii(), "Configura TEMP y TMP en una ruta sin tildes."
        servidor = pgserver.get_server(Path(temporal) / "datos")
        dsn = servidor.get_uri()
        try:
            with psycopg.connect(dsn, autocommit=True) as conn:
                conn.execute("CREATE ROLE chatbot_ro")
                archivos = ["01_schema.sql", "02_views.sql"]
                if (SQL / "05_v2_seed.sql").exists():
                    archivos.append("03_seed.sql")
                archivos.append("04_v2_schema.sql")
                if (SQL / "05_v2_seed.sql").exists():
                    archivos.append("05_v2_seed.sql")
                for nombre in archivos:
                    conn.execute((SQL / nombre).read_text(encoding="utf-8"), prepare=False)
                conn.execute(Path(__file__).with_name("fixtures.sql").read_text(encoding="utf-8"), prepare=False)
            yield dsn, make_conninfo(dsn, user="servicios_rw")
        finally:
            servidor.cleanup()


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
