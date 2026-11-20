# Asistente UNAB 360 para Android

Cliente nativo en Kotlin y Jetpack Compose. El chat consume el webhook de n8n y el panel **Hoy en tu U** consulta la API de servicios. Los perfiles usan datos sintéticos y el checkout de la demo funciona en modo de pruebas.

## Compilar en Windows

Requiere JDK 17 y la plataforma Android SDK 35. En Git Bash, desde la raíz del proyecto:

```bash
cd android
export JAVA_HOME="/c/Program Files/Android/Android Studio/jbr"
./gradlew.bat assembleDebug testDebugUnitTest
```

Configura `sdk.dir=C:/Users/jose/AppData/Local/Android/Sdk` en `local.properties` si Gradle no encuentra el SDK. El APK queda en `app/build/outputs/apk/debug/app-debug.apk`. Para instalarlo en un emulador o teléfono conectado:

```bash
~/AppData/Local/Android/Sdk/platform-tools/adb install -r app/build/outputs/apk/debug/app-debug.apk
```

## Probar la demo

1. En **Probar como…**, elige un perfil e introduce la clave de acceso del equipo en la app.
2. Con **Valentina · Medicina**, toca **Mis notas en gráfica** y abre **Hoy** para consultar el promedio, el riesgo y las tareas.
3. Con **Nicolás · Mecatrónica**, abre **Hoy → Préstamos → ¿Cómo renuevo?** para consultar el trámite y su QR.
4. Con **Andrés Felipe · Administración**, envía **Pagar matrícula** y abre **Pagar con Bold**. Usa el checkout de pruebas. Al volver, el chat consulta el estado de la orden.
5. Adjunta una imagen desde el clip y verifica la miniatura antes de enviar. Si el dispositivo ofrece reconocimiento de voz, el micrófono permite dictar la pregunta en español de Colombia.

La URL por defecto es `https://chatbotunab.duckdns.org`. Para usar otro servidor cambia **Opciones avanzadas → URL del servidor**. Desde el emulador, `http://10.0.2.2:<puerto>` apunta al equipo anfitrión.

El menú del chat permite iniciar una conversación nueva o cerrar sesión. Android conserva el código, la URL, la clave ingresada y el identificador de sesión en el almacenamiento privado de la aplicación. El historial visible se mantiene en memoria.

## Código

- `ui/Theme.kt` define los colores y la tipografía UNAB. `ui/componentes/` contiene las superficies, las burbujas y el compositor.
- `ChatViewModel.kt` mantiene el estado y los flujos de chat, imagen y pago. `data/ChatApi.kt` implementa el cliente HTTP.
- `testDebugUnitTest` verifica la compatibilidad del chat v1/v2, los adjuntos, el checkout y los datos de Hoy. Las rutas y formatos están en [Contratos v2](../docs/CONTRATOS-V2.md).
