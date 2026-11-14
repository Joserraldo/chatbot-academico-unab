# Asistente Académico UNAB — app Android

App nativa (Kotlin + Jetpack Compose + Material 3) que sirve de cliente del chatbot académico de la UNAB
(proyecto de Ingeniería de Sistemas). Envía las preguntas del estudiante al webhook de n8n y muestra la respuesta.

## Qué hace

- **Inicio**: el estudiante escribe su código (`^U\d{8}$`, p. ej. `U00000001`) y, opcionalmente, cambia la URL del servidor
  (precargada con `BuildConfig.BASE_URL`). Todo se guarda en DataStore. El botón **Usar demo** llena `U00000001`.
- **Chat**: burbujas usuario/bot, indicador "escribiendo…", chips de sugerencias rápidas, la intención como etiqueta
  pequeña bajo la respuesta del bot y las fuentes si llegan. Render simple de `**negrita**` y listas con `- `.
- **Errores**: mensaje amable y botón **Reintentar** (reenvía el último mensaje). Timeout de lectura de 90 s.
- **Menú (⋮)**: *Nueva conversación* (genera un `sessionId` nuevo) y *Cerrar sesión*.
- El historial visible vive solo en memoria; la memoria real de la conversación está en el servidor, por `sessionId`.
  El `sessionId` (UUID) se persiste por instalación + estudiante.
- Colores UNAB: naranja `#FFA300`, morado `#8A00E6` (tema claro y oscuro). Ícono adaptativo vectorial.

## Configuración (`local.properties`)

`local.properties` **no se versiona**. Además de `sdk.dir`, admite:

```properties
sdk.dir=C\:/Users/jose/AppData/Local/Android/Sdk
chatbot.baseUrl=https://chatbot-unab.duckdns.org
chatbot.key=TU_CLAVE_X_CHATBOT_KEY
```

Valores por defecto: `chatbot.baseUrl=https://chatbot-unab.duckdns.org`, `chatbot.key=` (vacía).
Se exponen como `BuildConfig.BASE_URL` y `BuildConfig.CHATBOT_KEY`. Si cambias `local.properties` hay que recompilar.

## Compilar (Git Bash)

Requiere JDK 17+ (se usa el JBR de Android Studio) y Android SDK con plataforma 35.

```bash
cd "/d/José Tellez/Documents/universidad/sexto semestre/ciencia de datos/chatbot-academico-unab/android"
export JAVA_HOME="/c/Program Files/Android/Android Studio/jbr"
./gradlew assembleDebug
```

El APK queda en:

```
app/build/outputs/apk/debug/app-debug.apk
```

Nota: la ruta del proyecto tiene tilde (`José`), por eso `gradle.properties` incluye `android.overridePathCheck=true`.

Instalar en un dispositivo/emulador conectado:

```bash
~/AppData/Local/Android/Sdk/platform-tools/adb install -r app/build/outputs/apk/debug/app-debug.apk
```

## Probar

**Contra el emulador (backend local en tu PC):** el emulador ve el host como `10.0.2.2`. En `local.properties`:

```properties
chatbot.baseUrl=http://10.0.2.2:5678
```

o cambia la URL en la pantalla de inicio. El tráfico en claro (`http`) solo se permite para `10.0.2.2` y `localhost`
(`res/xml/network_security_config.xml`); cualquier otro host exige HTTPS.

**Contra el servidor desplegado:** deja `chatbot.baseUrl=https://chatbot-unab.duckdns.org` y pon la clave real en
`chatbot.key`. Entra con `U00000001` (demo) o un código real.

Prueba rápida del contrato sin la app:

```bash
curl -X POST "https://chatbot-unab.duckdns.org/webhook/chat" -H "Content-Type: application/json" -H "X-Chatbot-Key: TU_CLAVE" -d '{"sessionId":"test-1","codigoEstudiante":"U00000001","mensaje":"¿Cuántos semestres me faltan?"}'
```

## Contrato del API

`POST {BASE_URL}/webhook/chat`

Headers: `Content-Type: application/json`, `X-Chatbot-Key: {API_KEY}`

Petición:

```json
{"sessionId": "<uuid por instalación+estudiante>", "codigoEstudiante": "U00XXXXXX", "mensaje": "<texto>"}
```

Respuesta 200:

```json
{"respuesta": "<markdown sencillo>", "intencion": "general|calendario|historial|noticias|ruta|bloqueado", "fuentes": ["..."]}
```

`intencion` y `fuentes` pueden faltar; los campos desconocidos se ignoran. Cualquier código no 2xx, fallo de red o
timeout (lectura 90 s) muestra un mensaje amable con botón Reintentar.

## Estructura

- `app/build.gradle.kts`: lee `local.properties`, define `BuildConfig`, dependencias (Compose BOM, OkHttp, kotlinx.serialization, DataStore).
- `data/ChatApi.kt`: cliente OkHttp + modelos serializables. `data/Prefs.kt`: DataStore (código, URL, sessionId por estudiante).
- `ChatViewModel.kt`: estado (`StateFlow<UiState>`), envío, reintento, nueva conversación, cierre de sesión.
- `ui/`: `LoginScreen`, `ChatScreen`, `Markdown` (negrita/listas), `Theme` (colores UNAB).

## Versiones

Gradle 8.10.2 · AGP 8.7.3 · Kotlin 2.1.0 · Compose BOM 2024.12.01 · compileSdk/targetSdk 35 · minSdk 26.

## Decisiones

- OkHttp directo (sin Retrofit/Ktor) por simplicidad: un solo endpoint.
- Sin librería de markdown: un parser mínimo de negrita y viñetas basta para las respuestas del bot.
- La clave `X-Chatbot-Key` queda embebida en el APK (BuildConfig): sirve para un proyecto de clase, no es un secreto fuerte.
