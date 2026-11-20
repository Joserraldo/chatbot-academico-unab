# Guía de recorrido: cómo funciona el Asistente UNAB 360

> Para Santiago, antes de la sustentación. Explica qué hace la app, qué pasa por dentro cuando alguien pregunta algo y un recorrido en vivo, paso a paso, con lo que hay que decir en cada parte. Si quieres ver el recorrido antes de hacerlo, mira el [video demo](https://youtu.be/iAiiowTgKYs) (4:28): sigue el mismo orden.

## 1. En una frase

Un chat académico (web y Android) que **conoce los datos de cada estudiante**: notas de Cosmos, tareas de TEMA, préstamos de biblioteca, matrícula y riesgo académico. Además **hace trámites**: cobra con Bold, reserva espacios y lee fotos con códigos QR. Todo corre en nuestra EC2 de AWS, en <https://chatbotunab.duckdns.org/app/>.

Los datos de estudiantes son **sintéticos** (206 estudiantes, 6 programas) y Bold está en **modo pruebas**. Hay que decirlo siempre que el profe vea plata o notas.

## 2. Qué pasa por dentro cuando alguien pregunta

```
Web / Android ──► Caddy (HTTPS) ──► n8n: workflow 00 Router
                                       │  1. Guardrails (bloquea datos de otro estudiante, inyección de prompt, SQL, tarjetas)
                                       │  2. Visión (si viene una foto: la describe y decodifica el QR)
                                       │  3. Intención (clasifica la pregunta)
                                       ▼
          ┌─────────────┬──────────────┬───────────────┬─────────────┬────────────────────┐
          01 RAG        02 Calendario  03 Historial    04 Noticias   06 Trámites y pagos
          (documentos   (fechas        (agente con     (scraper de   (reservas, Bold,
          oficiales)    académicas)    MCP → Postgres) 11 fuentes)   enlaces oficiales)
                                       ▼
                         4. Enriquecer: servicios-api agrega gráficas, tarjetas de pago y QR
                                       ▼
                                   respuesta al chat
```

Las piezas, por si preguntan:

| Pieza | Qué es | Dato para decir |
|---|---|---|
| **n8n** | Orquestador: 7 workflows (router, 01-04 y 06 de chat, 05 de ingesta RAG) | Los workflows se generan como código (`n8n/build_workflows.py`) |
| **LLM** | `qwen3.8-flash` para el chat y `qwen3.8-max` para leer imágenes, vía B.AI | El modelo **redacta**; los números no los inventa |
| **Servidor MCP** | FastMCP con **18 herramientas de solo lectura** sobre la BD | Usa el rol `chatbot_ro`: no puede escribir. También se puede usar desde Claude |
| **PostgreSQL 16 + pgvector** | Esquema `academico` (33 tablas, 8 vistas), `servicios` (reservas, pagos, riesgo) y los vectores del RAG | Simula Banner, Cosmos y TEMA |
| **RAG** | 26 fragmentos de 6 documentos institucionales, embeddings MiniLM multilingüe (384 dimensiones) | Siempre **cita la fuente** |
| **servicios-api** | FastAPI: pagos con Bold, reservas, gráficas, QR, visión, panel Hoy y analítica | Las tarjetas de pago las arma este endpoint determinista, **no el LLM** |
| **Scraper** | 11 fuentes RSS, corre cada 6 h, deduplica por similitud | Cada noticia trae fuente y fecha |
| **Modelo de riesgo** | Regresión logística con el historial académico | AUC 0,86 en validación cruzada (0,77 en prueba) |

**La decisión de diseño que más vende:** *"el LLM redacta, pero las tarjetas de pago, los QR y las gráficas los produce un endpoint determinista. El monto lo calcula el servidor desde la base de datos y el modelo nunca ve un número de tarjeta"*.

## 3. Recorrido en vivo (unos 8 minutos)

**Antes de empezar (10 minutos antes):**
1. Limpia la demo para que los pagos vuelvan a salir pendientes:
   `ssh -i llaveplaca.pem ubuntu@3.231.250.5 'cd ~/chatbot-academico-unab && bash scripts/reset-demo.sh'`
2. Comprueba que todo esté arriba: <https://chatbotunab.duckdns.org/api/health> debe decir `{"ok":true,"bold":true,"vision":true}`.
3. **Calienta el modelo:** la primera pregunta del día puede tardar más de 60 s. Entra como Juan Camilo (`U00000203`) y haz dos preguntas cualquiera.
4. Ten a mano la clave de acceso (pídemela; no está en el repo) y la foto del cartel de biblioteca (`videos/raw/cartel-biblioteca.png`).

**Paso a paso.** Escribe las preguntas tal cual.

| # | Haz esto | Qué debe aparecer | Qué decir |
|---|---|---|---|
| 1 | Abre <https://chatbotunab.duckdns.org/app/>, baja a **Probar como…** y elige **Santiago · Sistemas** (`U00000201`). Escribe la clave y pulsa **Entrar al chat** | El chat y, a la derecha, el panel **Hoy en tu U** | "Hay 7 estudiantes de prueba de 6 carreras, cada uno con una historia distinta" |
| 2 | `Muéstrame mis notas en gráfica` | Respuesta con el promedio por semestre y la gráfica | "El agente de historial consulta Postgres por MCP; la gráfica la arma servicios-api" |
| 3 | Recorre el panel **Hoy en tu U** | Horario, tareas de TEMA, "Califica a tu profe", biblioteca y noticias del día | "Junta todo lo del día. Las noticias vienen del scraper, con fuente y fecha" |
| 4 | `¿Cuándo son las inscripciones de asignaturas 2027-1?` y abre **Fuentes** | Respuesta con fechas y la fuente citada | "Esto es RAG sobre documentos oficiales: siempre dice de dónde sacó la respuesta" |
| 5 | Sal (icono de la puerta) y entra como **Andrés Felipe · Administración** (`U00000205`). `Quiero pagar mi matrícula` | Tarjeta de **$ 8.500.000** con **Pagar con Bold** | "El servidor crea la orden desde la BD; el LLM no toca el monto" |
| 6 | **Pagar con Bold** → en el checkout, tarjeta `4111 1111 1111 1111`, cualquier fecha futura, CVV `123`, marca las casillas y paga | "¡Pago aprobado!" y la orden en APROBADO | "Es el checkout real de Bold en modo pruebas, embebido en la página" |
| 7 | Entra como **Nicolás · Mecatrónica** (`U00000206`), adjunta la foto del cartel (clip) y escribe `¿Qué es esto y cómo lo uso?` | Explica el cartel y muestra el chip **QR detectado** con `https://catalogo.unab.edu.co/` | "Lee la imagen con un modelo de visión y decodifica el QR; el enlace sale de la lista oficial de trámites" |
| 8 | Entra como **Valentina · Medicina** (`U00000202`). `¿Cuál es mi riesgo académico?` | Riesgo alto y una explicación con qué hacer | "Un modelo de machine learning calcula la probabilidad y el asistente la explica en lenguaje claro" |
| 9 | `¿Cuáles son las notas de U00000002?` | Mensaje de bloqueo con la etiqueta **BLOQUEADO** | "Guardrail determinista: cada estudiante solo ve lo suyo. Todo queda en `chat_log`" |
| 10 | Pulsa **Analítica** en la cabecera | Mensajes atendidos, intenciones, bloqueos y métricas del modelo (AUC, F1, matriz de confusión) | "Aquí se ve el uso del asistente y cómo rinde el modelo de riesgo" |
| 11 | Android: abre la app en el teléfono o emulador, elige una persona y pide `Muéstrame mis notas en gráfica` | La misma gráfica, con la línea de 3.0 | "La app nativa (Kotlin + Compose) usa la misma API; el APK se baja desde el QR de la página de inicio" |

**Si sobra tiempo:**
- Como Laura (`U00000001`): `Reserva una sala de estudio mañana a las 10 por 2 horas`. Crea una reserva real en la BD.
- Como Nicolás: `Quiero pagar mi multa de biblioteca`.

## 4. Android

- **APK 2.2:** <https://chatbotunab.duckdns.org/app/descargas/asistente-unab-360.apk>, o escanea el QR **📱 App Android** de la pantalla de inicio de la web.
- **Mismas funciones que la web:** login con personas, chat, gráficas, panel **Hoy** (botón arriba a la derecha), adjuntar imágenes, voz y pagos.
- **Pago en Android (corregido hoy):** el checkout de Bold no se veía dentro de la app, porque en el WebView de Android las unidades `vh` valen 0 y el modal de Bold quedaba con alto 0. Ahora, dentro de la app, la página de pago usa el modo `redirect` de Bold: toda la pantalla va al checkout y vuelve con "¡Pago aprobado!". En el navegador sigue el modal de siempre.

## 5. Si algo falla en vivo

| Síntoma | Qué hacer |
|---|---|
| La respuesta tarda mucho | Es el tiempo del LLM (en las grabaciones tardó entre 10 y 75 s). Explica el flujo de la sección 2 mientras responde; si pasa de 2 minutos, muestra el [video demo](https://youtu.be/iAiiowTgKYs) |
| La tarjeta de matrícula no aparece | Andrés Felipe ya pagó en un ensayo. Corre `reset-demo.sh` (sección 3) |
| "La clave de acceso no es válida" | Pulsa **Cambiar clave** y escríbela de nuevo |
| Después de pagar, Bold muestra un contador | Es normal: Bold espera unos segundos y regresa solo a nuestra página |
| Algo del servidor no responde | Mira `/api/health`. Si falla, muestra el [video demo](https://youtu.be/iAiiowTgKYs) |

## 6. Preguntas que puede hacer el profe

- **¿Por qué n8n y no solo código?** Porque el enunciado pide workflows, y porque el router con agentes especializados se ve y se audita en el editor. Igual los workflows se generan desde código y están versionados en `n8n/workflows/`.
- **¿Cómo evitan que el modelo invente?** RAG con fuente citada; las cifras salen de la BD por MCP; las tarjetas de pago, los QR y los enlaces los produce código determinista; los guardrails corren antes del LLM.
- **¿Qué es MCP?** Un protocolo estándar para darle herramientas a un LLM. Nuestro servidor expone 18 herramientas de solo lectura sobre la BD académica, y Claude también puede usarlas.
- **¿Los datos son reales?** No. Son sintéticos y simulan Banner, Cosmos y TEMA. El plan de estudios de Sistemas sí viene del PDF institucional, y los enlaces de trámites son los oficiales de la UNAB.
- **¿Qué tan bueno es el modelo de riesgo?** Regresión logística, AUC 0,86 en validación cruzada y 0,77 en prueba, con las variables más importantes explicadas en el dashboard. Es apoyo, no decisión: siempre recomienda hablar con el tutor.
- **¿Dónde corre?** EC2 de AWS con Docker Compose: Caddy (HTTPS con Let's Encrypt), n8n, Postgres + pgvector, servidor MCP, servicios-api y scraper.

## 7. Material de apoyo

| Qué | Dónde |
|---|---|
| Video demo (4:28) | <https://youtu.be/iAiiowTgKYs> |
| Tráiler (1:10) | <https://youtu.be/e0BDTLoeVEg> |
| Presentación (tecla **N** para el guion del orador) | <https://chatbotunab.duckdns.org/app/presentacion/> |
| Manual de usuario completo | [MANUAL-USUARIO.md](MANUAL-USUARIO.md) |
| Arquitectura en detalle | [ARQUITECTURA.md](ARQUITECTURA.md) |
| Cumplimiento del enunciado, criterio por criterio | [README](../README.md#-cumplimiento-del-enunciado-tema-2) |
