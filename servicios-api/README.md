# servicios-api

API FastAPI de la v2 "Asistente UNAB 360": reservas, pagos (Bold o simulados), QR, gráficas,
visión, panel "Hoy", enriquecimiento determinista del chat y analítica.
Contrato: `docs/CONTRATOS-V2.md` (§1 auth, §3 acciones y gráficas, §4 endpoints). Datos 100 % sintéticos.

## Endpoints (todos bajo `/api`, Caddy no recorta el prefijo)

Públicos (sin clave): `GET /health`, `GET /demo/personas`, `GET /qr`, `GET /pagos/{orderId}`,
`POST /pagos/{orderId}/simular`, `POST /pagos/bold/webhook`, `GET /noticias/hoy`.
El resto exige `X-Chatbot-Key` (401 si falta, 403 si es incorrecta; comparación en tiempo constante).

| Ruta | Qué hace |
|---|---|
| `GET /health` | `{ok, bold, vision}` |
| `GET /demo/personas` | Tarjetas de login, ordenadas por `orden` |
| `GET /hoy/{codigo}` | Panel: tareas, evaluaciones, préstamos, pagos pendientes, reservas, horario de hoy (America/Bogota), noticias y riesgo. Muestra matrícula `pagada` si hay orden aprobada |
| `GET /graficas/{codigo}?tipo=` | `notas_semestre`, `avance`, `creditos_area`, `parciales`, `riesgo` (404 si no hay modelo), `cohorte` |
| `GET /espacios?tipo=` · `GET /espacios/{codigo}/disponibilidad?fecha=` | Espacios y franjas de 07:00 a 21:00 |
| `POST /reservas` | 409 si hay choque; con tarifa > 0 queda `pendiente_pago` y crea orden |
| `POST /pagos/orden` | El monto lo calcula el servidor (matrícula pendiente, multa de biblioteca, reserva). Reutiliza la orden pendiente; 409 si ya está pagada |
| `GET /pagos/{orderId}` | Si está pendiente y es Bold, consulta `payment-voucher` y actualiza |
| `POST /pagos/{orderId}/simular` | `{resultado: aprobado\|rechazado}`; solo órdenes simuladas y con `PAGOS_PERMITIR_SIMULADO=true` |
| `POST /pagos/bold/webhook` | Verifica `x-bold-signature`, idempotente por `id`, responde rápido |
| `GET /qr?url=&tam=` | PNG |
| `POST /vision` | dataURL JPEG/PNG/WebP ≤ 4 MB; QR local con OpenCV (x1 y x2) + LLM de visión; si el LLM falla responde igual |
| `POST /asistente/enriquecer` | Reglas 1-6 deterministas, sin LLM; ante cualquier error devuelve `{acciones:[],graficas:[]}` |
| `GET /noticias/hoy?limite=` · `GET /tramites` · `GET /analitica/resumen` | Según contrato (la analítica funciona con `riesgo_estudiante`/`modelo_riesgo` vacíos) |

Reglas de `enriquecer`: (1) reservar/espacios/gimnasio, (2) pagar matrícula, (3) biblioteca,
(4) Cosmos/TEMA/evaluación docente, (5) gráficas (máx. 2), (6) toda orden creada hace < 5 min.
Se deduplica y se limita a 4 acciones. La intención `bloqueado` no enriquece.

## Variables de entorno

`SERVICIOS_DATABASE_URL` (rol `servicios_rw`), `CHATBOT_KEY`, `PUBLIC_BASE_URL`, `LLM_BASE_URL`,
`LLM_API_KEY`, `VISION_MODEL` (def. `qwen3.8`), `BOLD_API_KEY`, `BOLD_SECRET_KEY`,
`BOLD_WEBHOOK_SECRET` (vacío en pruebas), `BOLD_MODO` (`pruebas`|`produccion`),
`PAGOS_PERMITIR_SIMULADO` (def. `true`). Sin `BOLD_API_KEY` y `BOLD_SECRET_KEY` las órdenes son
`simulado` y `bold` es `null`.

El rol `servicios_rw` solo hace `SELECT` en `academico` y escribe en `servicios`; por eso la matrícula
no se actualiza en `academico`: el pago queda en `servicios.pago_orden` y el panel la muestra `pagada`.

## Bold (modo pruebas)

- Firma de integridad: `sha256_hex(orderId + monto + moneda + BOLD_SECRET_KEY)`; monto entero mínimo 1000 COP.
- Webhook: `HMAC-SHA256(key=BOLD_WEBHOOK_SECRET, msg=base64(cuerpo crudo))` en hex. En pruebas la llave es `""`.
  En `produccion` con la llave vacía se rechaza todo.
- **En modo pruebas Bold NO envía el webhook solo.** Hay dos caminos: pulsar "Probar el webhook" en el panel de
  Bold (apuntando a `https://DOMAIN/api/pagos/bold/webhook`), o confiar en el sondeo: `pagar.html` consulta
  `GET /api/pagos/{orderId}` y la API pregunta a `payments.api.bold.co/v2/payment-voucher/{orderId}`.
- Tarjetas de prueba: `4111111111111111` aprueba, `4970110000000062` rechaza.
- La redirección (`?bold-tx-status=approved`) no es definitiva; se confirma con la consulta.

## Pruebas

Necesitan Python 3.12 (pgserver no tiene wheel para 3.13) y un `TEMP` sin espacios ni tildes
(la carpeta de datos de Postgres se crea ahí). No requieren Docker: levantan un Postgres embebido,
cargan `db/init/01..05` y aplican los GRANT de `06_v2_roles.sh`, y se conectan como `servicios_rw`.

```bash
py -3.12 -m venv "$TEMP/venv-api"
"$TEMP/venv-api/Scripts/python.exe" -m pip install -r servicios-api/requirements-test.txt
cd servicios-api && "$TEMP/venv-api/Scripts/python.exe" -m pytest -q
```

- `tests/test_api.py`, `tests/test_pagos.py`: base `pruebas` con datos propios (periodo 2099-2).
- `tests/test_semilla.py`: base `semilla` con las personas U00000201-206 (montos 8.500.000 y 22.500, historias).
- El Postgres embebido no trae zona horaria `America/Bogota`; por eso el SQL usa `INTERVAL '-05:00'` (Colombia no tiene horario de verano).

## Correr local

```bash
cd servicios-api
SERVICIOS_DATABASE_URL=postgresql://servicios_rw:clave@localhost:5432/unab CHATBOT_KEY=k python -m uvicorn app.main:app --port 8000
```

Docker: `docker build -t servicios-api servicios-api` (python:3.12-slim, usuario no root, puerto 8000, healthcheck en `/api/health`).
