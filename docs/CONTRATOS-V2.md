# Contratos v2 — "Asistente UNAB 360"

Documento de referencia para todos los módulos de la versión 2. Si un módulo necesita cambiar un contrato, se actualiza aquí primero.

Datos 100 % sintéticos. Pagos en **modo pruebas** de Bold o simulados.

---

## 1. Servicios y rutas públicas

| Ruta pública (Caddy) | Destino interno | Notas |
|---|---|---|
| `/webhook/*` y `/` | `n8n:5678` | Igual que en v1 |
| `/mcp*` | `mcp-server:9000` | Igual que en v1 |
| `/api/*` | `servicios-api:8000` | **Nuevo**. FastAPI. Las rutas incluyen el prefijo `/api` (no se recorta) |
| `/app/*` | archivos de `./web` montados en `/srv/web` | `handle_path /app*` + `file_server` |

`servicios-api` lee estas variables de entorno:

| Variable | Valor o uso |
|---|---|
| `SERVICIOS_DATABASE_URL` | `postgresql://servicios_rw:${SERVICIOS_DB_PASSWORD}@postgres:5432/unab` |
| `CHATBOT_KEY` | Mismo valor que el webhook |
| `PUBLIC_BASE_URL` | `https://${DOMAIN}` |
| `LLM_BASE_URL`, `LLM_API_KEY` | Proveedor de visión |
| `VISION_MODEL` | Por defecto `qwen3.8` |
| `BOLD_API_KEY` | Llave de identidad |
| `BOLD_SECRET_KEY` | Firma de integridad |
| `BOLD_WEBHOOK_SECRET` | Vacío en modo pruebas |
| `BOLD_MODO` | `pruebas` o `produccion` |
| `PAGOS_PERMITIR_SIMULADO` | Por defecto `true` |

**Autenticación de `/api`:** el header `X-Chatbot-Key` es obligatorio, salvo en estas rutas públicas: `GET /api/health`, `GET /api/demo/personas`, `GET /api/qr`, `GET /api/pagos/{orderId}`, `POST /api/pagos/{orderId}/simular`, `POST /api/pagos/bold/webhook` y `GET /api/noticias/hoy`. Las tres rutas de pago usan un `orderId` aleatorio que no se puede adivinar.

---

## 2. Base de datos (nuevo; la base v1 no cambia)

**Archivos de inicialización.** En un despliegue nuevo se ejecutan en orden alfabético. En la EC2 se aplican con `scripts/migrate-v2.sh`.

| Archivo | Contenido |
|---|---|
| `db/init/04_v2_schema.sql` | DDL idempotente (`IF NOT EXISTS`) |
| `db/init/05_v2_seed.sql` | GENERADO por `scripts/generate_synthetic.py`; idempotente (`ON CONFLICT DO NOTHING`) |
| `db/init/06_v2_roles.sh` | Rol `servicios_rw` con `SERVICIOS_DB_PASSWORD`, más los GRANT |

**Permisos:**
- `chatbot_ro`: `SELECT` en las tablas nuevas de `academico` y en `servicios.*`.
- `servicios_rw`:
  - `SELECT` en `academico.*` (incluye `chat_log`).
  - `SELECT, INSERT, UPDATE` en `servicios.*` y uso de sus secuencias.

### 2.1 `academico` (datos institucionales simulados: Cosmos, TEMA y biblioteca)

```sql
-- Personas demo para probar el sistema (una por carrera)
persona_demo(codigo TEXT PK, titulo TEXT, descripcion TEXT, emoji TEXT, orden INT)
docente(id SERIAL PK, nombre TEXT, email TEXT)
seccion(id SERIAL PK, curso_id INT FK curso_plan, periodo_id INT FK periodo, docente_id INT FK docente,
        grupo TEXT, horario TEXT,            -- 'Lun 07:00-09:00; Mié 07:00-09:00'
        salon TEXT)
inscripcion_seccion(estudiante_id INT FK, seccion_id INT FK, PK(estudiante_id, seccion_id))
nota_parcial(estudiante_id INT FK, seccion_id INT FK, corte INT /*1..3*/, porcentaje INT /*30,30,40*/,
             nota NUMERIC(3,1) NULL /*NULL = aún no calificado*/, PK(estudiante_id, seccion_id, corte))
tarea_tema(id SERIAL PK, seccion_id INT FK, titulo TEXT, tipo TEXT /*tarea|quiz|foro|proyecto*/,
           fecha_entrega TIMESTAMPTZ, peso INT)
entrega_tema(estudiante_id INT FK, tarea_id INT FK, estado TEXT /*pendiente|entregada|calificada|vencida*/,
             nota NUMERIC(3,1) NULL, PK(estudiante_id, tarea_id))
evaluacion_docente(estudiante_id INT FK, seccion_id INT FK, estado TEXT /*pendiente|completada*/,
                   fecha_limite DATE, PK(estudiante_id, seccion_id))
prestamo_biblioteca(id SERIAL PK, estudiante_id INT FK, titulo TEXT, autor TEXT, fecha_prestamo DATE,
                    fecha_vencimiento DATE, renovaciones INT, estado TEXT /*activo|vencido|devuelto*/,
                    multa NUMERIC(12,0) DEFAULT 0)
enlace_tramite(codigo TEXT PK, nombre TEXT, url TEXT, descripcion TEXT, pasos TEXT, palabras_clave TEXT[])
```

**Programas nuevos** (ids 2 a 6): MED Medicina, DER Derecho, PSI Psicología, ADM Administración de Empresas y MEC Ingeniería Mecatrónica. Cada uno tiene un plan sintético con ids de `curso_plan` ≥ 1000.

**Personas demo** (ids de estudiante 201 a 206). `U00000001` (Sistemas, v1) también aparece como persona.

| Código | Carrera | Historia (los datos deben producirla) |
|---|---|---|
| U00000201 | Ing. Sistemas | Excelente: promedio ≥ 4.5, casi lista para el grado, tareas al día y 1 evaluación docente pendiente |
| U00000202 | Medicina | **En riesgo**: 2 reprobados, parcial 1 bajo, 3 tareas vencidas o pendientes |
| U00000203 | Derecho | Cerca del grado: ~92 % de avance y requisitos de grado pendientes |
| U00000204 | Psicología | Primer semestre: sin historial previo, mucha orientación |
| U00000205 | Administración | Matrícula `pendiente_pago`, para la demo del pago de matrícula con Bold |
| U00000206 | Ing. Mecatrónica | Préstamo de biblioteca **vencido** con multa > 0, para renovar y pagar la multa |

**`enlace_tramite`** (URLs reales de la UNAB):

| Código | URL | Uso |
|---|---|---|
| `reservas` | https://reservas.unab.edu.co/auth/login | Espacios, gimnasio y escenarios deportivos |
| `biblioteca_renovar` | https://catalogo.unab.edu.co/ | Sale del QR del cartel "Renueva tus préstamos": escanear e ingresar con la cuenta UNAB |
| `gimnasio` | Igual a `reservas` | Pasos propios |
| `cosmos` | https://cosmos.unab.edu.co/ | — |
| `tema` | https://tema.unab.edu.co/ | — |
| `evaluacion_docente` | — | Cómo calificar al profesor en TEMA o Cosmos |
| `unab` | https://unab.edu.co | — |

Si no se conoce la URL exacta, se usa el portal principal y se indica en `descripcion`.

### 2.2 `servicios` (escribe `servicios-api`)

```sql
espacio(id SERIAL PK, codigo TEXT UNIQUE, nombre TEXT, tipo TEXT /*sala_estudio|auditorio|laboratorio|cancha|gimnasio|musica*/,
        sede TEXT, capacidad INT, tarifa_hora NUMERIC(12,0) /*0 = gratis*/, descripcion TEXT)
reserva(id SERIAL PK, codigo_estudiante TEXT, espacio_id INT FK, fecha DATE, hora_inicio TIME, hora_fin TIME,
        estado TEXT /*pendiente_pago|confirmada|cancelada*/, order_id TEXT NULL, creado_en TIMESTAMPTZ DEFAULT now())
  -- índice único parcial (espacio_id, fecha, hora_inicio) WHERE estado <> 'cancelada'
pago_orden(order_id TEXT PK /* 'UNAB-MAT-<12hex>' | 'UNAB-RES-..' | 'UNAB-BIB-..' */, codigo_estudiante TEXT,
           concepto TEXT /*matricula|reserva|multa_biblioteca*/, referencia TEXT, descripcion TEXT,
           monto NUMERIC(12,0), moneda TEXT DEFAULT 'COP',
           estado TEXT /*pendiente|aprobado|rechazado|fallido|anulado*/, proveedor TEXT /*bold|simulado*/,
           bold_payment_id TEXT, metodo TEXT, creado_en TIMESTAMPTZ DEFAULT now(), actualizado_en TIMESTAMPTZ DEFAULT now(),
           detalle JSONB)
bold_evento(id TEXT PK /*id de la notificación*/, payment_id TEXT, tipo TEXT, order_id TEXT,
            recibido_en TIMESTAMPTZ DEFAULT now(), payload JSONB)
riesgo_estudiante(codigo TEXT PK, probabilidad NUMERIC(5,4), nivel TEXT /*bajo|medio|alto*/,
                  factores JSONB /*[{factor, valor, aporte}]*/, modelo TEXT, actualizado_en TIMESTAMPTZ DEFAULT now())
modelo_riesgo(id SERIAL PK, nombre TEXT, auc NUMERIC, f1 NUMERIC, accuracy NUMERIC, matriz JSONB,
              importancias JSONB, n_train INT, n_test INT, entrenado_en TIMESTAMPTZ DEFAULT now())
```

La semilla v2 trae 10 espacios: salas de estudio gratis y, con tarifa, un auditorio, una cancha sintética, un laboratorio Mac, una sala de música y el gimnasio.

---

## 3. Chat: contrato ampliado (compatible hacia atrás)

**Petición** a `POST /webhook/chat`, con el header `X-Chatbot-Key`:

```json
{"sessionId":"…","codigoEstudiante":"U00000205","mensaje":"quiero pagar mi matrícula",
 "imagen":"data:image/jpeg;base64,…"}
```

`imagen` es opcional: JPEG, PNG o WebP de hasta 4 MB en base64. La app la reduce a ≤ 1280 px antes de enviarla.

**Respuesta:**

```json
{"respuesta":"…markdown…","intencion":"general|calendario|historial|noticias|tramites|bloqueado",
 "fuentes":["…"],
 "acciones":[ Accion ],
 "graficas":[ Grafica ],
 "imagen":{"descripcion":"…","qr":["https://…"]}}
```

### Tipos de `Accion`

`tipo` es el discriminador:

```json
{"tipo":"pago","orderId":"UNAB-MAT-ab12…","concepto":"matricula","descripcion":"Matrícula 2026-2",
 "monto":9850000,"moneda":"COP","estado":"pendiente","url":"/app/pagar.html?order=UNAB-MAT-ab12…"}
{"tipo":"enlace","titulo":"Reservas UNAB","url":"https://reservas.unab.edu.co/auth/login","descripcion":"…"}
{"tipo":"qr","titulo":"Renueva tus préstamos","url":"https://catalogo.unab.edu.co/","imagen":"/api/qr?url=https%3A%2F%2Fcatalogo.unab.edu.co%2F"}
{"tipo":"reserva","id":12,"espacio":"Sala de estudio 3","fecha":"2026-11-21","horaInicio":"10:00","horaFin":"12:00",
 "estado":"pendiente_pago|confirmada","orderId":"UNAB-RES-…|null"}
{"tipo":"sugerencias","opciones":["Muéstrame mis notas en gráfica","¿Qué tareas tengo en TEMA?"]}
```

### `Grafica` (sin depender de una librería)

```json
{"id":"notas_semestre","tipo":"bar|line|doughnut|radar","titulo":"Promedio por semestre",
 "labels":["2025-1","2025-2"],"series":[{"nombre":"Promedio","datos":[3.9,4.2]}],
 "unidad":"nota 0-5","nota":"Línea de referencia: 3.0 aprueba"}
```

### Quién produce `acciones` y `graficas`

Para que la demo sea robusta, las produce el router con una llamada **determinista**: `POST http://servicios-api:8000/api/asistente/enriquecer` después del guardrail de salida. El LLM nunca arma este JSON. Si la llamada falla, se devuelven `[]` y la respuesta sigue igual.

---

## 4. API `servicios-api`

Todas las respuestas son JSON salvo `/api/qr` (PNG). Los errores tienen la forma `{"detail":"mensaje en español"}`.

| Método y ruta | Entrada | Salida |
|---|---|---|
| `GET /api/health` | — | `{"ok":true,"bold":bool,"vision":bool}` |
| `GET /api/demo/personas` | — | `[{codigo,nombre,programa,titulo,descripcion,emoji}]`, ordenado por `orden` |
| `GET /api/hoy/{codigo}` | — | `{estudiante:{codigo,nombre,programa,semestre_actual,promedio,porcentaje_avance,estado_matricula}, tareas:[{titulo,curso,tipo,fecha_entrega,estado}], evaluaciones:[{curso,docente,fecha_limite}], prestamos:[{titulo,fecha_vencimiento,estado,multa}], pagos_pendientes:[PagoOrden], reservas:[…], horario_hoy:[{curso,horario,salon,docente}], noticias:[{titulo,url,fuente,fecha}], riesgo:{nivel,probabilidad,factores}\|null}` |
| `GET /api/graficas/{codigo}?tipo=` | `tipo` ∈ `notas_semestre\|avance\|creditos_area\|parciales\|riesgo\|cohorte` | `Grafica` |
| `GET /api/espacios?tipo=` | — | `[Espacio]` |
| `GET /api/espacios/{codigo}/disponibilidad?fecha=YYYY-MM-DD` | — | `{espacio, fecha, franjas:[{horaInicio:"07:00",horaFin:"08:00",libre:bool}]}`, de 07:00 a 21:00 |
| `POST /api/reservas` | `{codigoEstudiante, espacio:"codigo", fecha, horaInicio:"10:00", horas:1..4}` | `{reserva, pago: PagoOrden\|null}`. 409 si hay choque. Si la tarifa es > 0, crea una orden `reserva` y la reserva queda en `pendiente_pago` |
| `POST /api/pagos/orden` | `{codigoEstudiante, concepto, referencia?}` | `PagoOrden`. **El monto lo calcula el servidor** (matrícula pendiente, multa o reserva) y reutiliza la orden pendiente si ya existe |
| `GET /api/pagos/{orderId}` | — | `PagoOrden`. Si está pendiente y Bold está configurado, consulta `payment-voucher` y actualiza |
| `POST /api/pagos/{orderId}/simular` | `{resultado:"aprobado"\|"rechazado"}` | `PagoOrden`. Solo si `PAGOS_PERMITIR_SIMULADO=true` |
| `POST /api/pagos/bold/webhook` | Cuerpo crudo de Bold y header `x-bold-signature` | `200 {"ok":true}` rápido; 401 si la firma es inválida. Es idempotente por `id` |
| `GET /api/qr?url=&tam=` | `url` http(s) de ≤ 500 caracteres | `image/png` |
| `POST /api/vision` | `{codigoEstudiante, mensaje, imagen(dataURL)}` | `{descripcion, texto, qr:[str], tipo:"horario\|recibo\|cartel\|documento\|captura\|otro"}` |
| `POST /api/asistente/enriquecer` | `{codigoEstudiante, sessionId, mensaje, intencion, respuesta}` | `{acciones:[Accion], graficas:[Grafica]}` |
| `GET /api/noticias/hoy?limite=10` | — | `[{titulo,url,resumen,categoria,fuente,fecha_publicacion}]`, de las últimas 48 h o, si no hay, las más recientes |
| `GET /api/tramites` | — | `[enlace_tramite]` |
| `GET /api/analitica/resumen` | — | `{intenciones:[{intencion,n}], bloqueos:[{motivo,n}], por_dia:[{dia,n}], riesgo:[{nivel,n}], modelo:modelo_riesgo\|null, totales:{mensajes,estudiantes,bloqueados}}` |

### `PagoOrden`

```json
{"orderId","codigoEstudiante","concepto","descripcion","monto","moneda","estado","proveedor",
 "simulado":bool,
 "bold":{"apiKey","integritySignature","amount":"9850000","currency":"COP","orderId","description",
         "redirectionUrl":"https://DOMAIN/app/pagar.html?order=…"} | null}
```

### Detalles de Bold (de developers.bold.co)

**Script de la librería:** `https://checkout.bold.co/library/boldPaymentButton.js`. El botón se inyecta con JS **después** de cargar la librería:

```html
<script data-bold-button="dark-L" data-api-key data-amount data-currency="COP"
        data-order-id data-integrity-signature data-description(2-100)
        data-redirection-url data-render-mode="embedded"></script>
```

- **Firma:** `sha256_hex(orderId + amount + currency + BOLD_SECRET_KEY)`. Monto entero, mínimo 1000 COP. `orderId` de ≤ 60 caracteres `[A-Za-z0-9_-]`.
- **Webhook:**
  - Verificación: `hmac_sha256_hex(key=BOLD_WEBHOOK_SECRET, msg=base64(raw_body)) == x-bold-signature`. En modo pruebas la llave es `""`.
  - Eventos: `SALE_APPROVED`, `SALE_REJECTED`, `VOID_APPROVED` y `VOID_REJECTED`.
  - `data.metadata.reference` = orderId; también `data.payment_id` y `data.payment_method`.
  - En pruebas Bold **no** envía el webhook solo; se dispara con el botón "Probar el webhook" del panel.
- **Consulta del estado:** `GET https://payments.api.bold.co/v2/payment-voucher/{orderId}` con el header `Authorization: x-api-key {BOLD_API_KEY}`.
  - `payment_status`: `APPROVED`, `REJECTED`, `FAILED`, `VOIDED`, `PROCESSING`, `PENDING` o `NO_TRANSACTION_FOUND`.
- **Retorno:** `?bold-order-id=…&bold-tx-status=approved`. No es definitivo; se confirma con la consulta.
- **Tarjetas de prueba:** `4111111111111111` aprueba y `4970110000000062` rechaza.

---

## 5. MCP: herramientas nuevas (solo lectura, validan el código)

| Herramienta | Devuelve |
|---|---|
| `notas_periodo_actual(codigo)` | Notas por corte (Cosmos) del periodo actual y nota parcial acumulada por curso |
| `horario(codigo, dia=None)` | Secciones inscritas con horario, salón y docente |
| `tareas_tema(codigo, solo_pendientes=True)` | Tareas, quices y entregas de TEMA con fecha y estado |
| `evaluaciones_docentes_pendientes(codigo)` | Docentes por calificar ("recuerda calificar a tu profesor X en TEMA") |
| `prestamos_biblioteca(codigo)` | Préstamos con vencimiento y multa |
| `enlaces_tramites(tema=None)` | Enlaces oficiales y pasos, por palabra clave |
| `riesgo_academico(codigo)` | Nivel, probabilidad y factores del modelo de ML, más acciones sugeridas |
| `resumen_360(codigo)` | Todo lo anterior resumido: el "¿cómo voy?" |

---

## 6. n8n

- **Router:**
  - El guardrail de entrada valida `imagen` (prefijo data URL de imagen y ≤ 5.5 MB de texto).
  - Si hay imagen: `HTTP POST /api/vision` → se antepone al mensaje `"[Imagen adjunta: tipo] descripción. Texto: … QR: …"`.
  - El clasificador suma `tramites`: reservar, apartar espacios, gimnasio, pagar matrícula o multa, renovar biblioteca, enlaces, QR, cómo hago el trámite X.
  - Cosmos y TEMA (notas de corte, tareas, horario, evaluación docente, riesgo) → `historial`.
  - Después del guardrail de salida: `HTTP POST /api/asistente/enriquecer` (`onError` continúa) → `Log` → `Responder`, que incluye `acciones`, `graficas` e `imagen`.
- **wf06 `wf06Tramites0000` "06 Trámites, reservas y pagos":**
  - Un agente con memoria y herramientas `toolHttpRequest` hacia `servicios-api`: `listar_espacios`, `disponibilidad`, `crear_reserva`, `crear_orden_pago` y `listar_tramites`.
  - Envía el header `X-Chatbot-Key` con `$env.CHATBOT_KEY`.
- **wf03** se queda con las herramientas MCP nuevas (`include: all`). Su prompt menciona Cosmos, TEMA, la evaluación docente y el riesgo.
- **Variables nuevas del contenedor n8n:** `CHATBOT_KEY` y `SERVICIOS_URL=http://servicios-api:8000`.

---

## 7. Web

| Archivo | Contenido |
|---|---|
| `web/index.html` | Chat. Login con tarjetas de personas (`GET /api/demo/personas`) |
| `web/pagar.html` | Checkout embebido de Bold; si no hay Bold, la simulación |
| `web/analitica/index.html` | Dashboard |

**Chart.js:** `https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js`.

**Android:** el pago abre `https://DOMAIN/app/pagar.html?order=…` en un WebView dentro de la app (JavaScript y DOM storage activados).
