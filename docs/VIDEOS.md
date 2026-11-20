# Brief de producción: dos videos del Asistente UNAB 360

> **Para el agente que haga los videos.** Este documento basta para producir los dos videos sin preguntar. Cada cifra y cada función que aparezca en pantalla o en la voz debe estar en el [README](../README.md); si no está ahí, no va en el video. Antes de empezar, carga las skills `producto-promo-video-es`, `app-promo-video` y `hyperframes`, que tienen el pipeline probado en esta máquina.

| | Video 1 · **Demo funcional** | Video 2 · **Tráiler promocional** |
|---|---|---|
| Para qué | Que el profesor vea que **todo funciona de verdad**, en la web y en Android | Que parezca un lanzamiento de la UNAB: emoción, orgullo y "esto ya existe" |
| Duración | 3:30 a 4:30 min | 60 a 75 s (más un corte vertical de 30 s, opcional) |
| Formato | 1920x1080, 30 fps, MP4 H.264 + AAC | 1920x1080 (y 1080x1920 para el corte vertical) |
| Imagen | **Grabaciones de pantalla reales**, con títulos y resaltados encima | Planos cortos de las grabaciones + tipografía cinética + logo |
| Voz | Narrador cercano, explica paso a paso | Narrador cinematográfico, frases cortas |
| Música | Suave, tecnológica, por debajo de la voz | Épica que crece, con remate en el logo |
| Salida | `videos/01-demo-funcional.mp4` | `videos/02-trailer-unab360.mp4` (+ `02-trailer-vertical.mp4`) |

La carpeta `videos/` **no se sube al repo** (está en `.gitignore`, por tamaño). Los videos se suben como "no listados" a YouTube o a Drive, y el enlace se agrega a la tabla de entregables del README.

---

## 1. Antes de grabar

1. **Limpiar la demo** (borra órdenes, reservas e historial de chat):
   ```
   ssh -i llaveplaca.pem ubuntu@3.231.250.5 'cd ~/chatbot-academico-unab && bash scripts/reset-demo.sh'
   ```
   Repetirlo antes de cada toma de pago o de reserva: si Andrés Felipe ya pagó, la tarjeta de matrícula no vuelve a salir.
2. **Comprobar que todo responde:** `curl https://chatbotunab.duckdns.org/api/health` debe devolver `{"ok":true,"bold":true,"vision":true}`.
3. **Nunca mostrar la clave de acceso.** En el login de la web y de Android, escribe la clave fuera de cámara o tápala con un desenfoque. Tampoco se pueden ver terminales con `.env`, llaves `.pem` ni tokens.
4. **Calentar el modelo.** La primera pregunta del día puede tardar más de 60 s. Haz 2 o 3 preguntas de prueba antes de grabar, y en edición recorta las esperas largas (acelerar ×4 con un indicador "⏩ respuesta en tiempo real: 12 s" es honesto; borrarlas sin decirlo, no).
5. **Material.**
   - Logo: `web/assets/logo-unab.png` e isotipo en `android/app/src/main/res/drawable-nodpi/`.
   - Capturas de referencia: `docs/evidencias/v2/` (de la 30 a la 48).
   - Foto del cartel de biblioteca para la prueba de imagen: la misma de la captura `36-imagen-qr.png`.

### Cómo grabar

| Qué | Herramienta |
|---|---|
| Web en escritorio | Playwright con `record_video_dir` a 1920x1080, o OBS. Zoom del navegador al 110 % para que el texto se lea |
| Web en móvil | Playwright con viewport 390x844 (`39b`, `39c` y `39d` son la referencia) |
| Android | Emulador `emulator-5554` con el APK de `web/descargas/asistente-unab-360.apk`. `adb shell screenrecord /sdcard/x.mp4` corta a los **180 s**: graba por escenas y baja cada archivo con `adb pull` |
| Montaje, títulos y tráiler | HyperFrames (skills de arriba) + `ffmpeg` |

---

## 2. Identidad visual (igual en los dos videos)

| Token | Valor | Uso |
|---|---|---|
| Naranja UNAB | `#FF9D00` (fuerte `#E09900`) | Acento principal, barras, botones |
| Morado UNAB | `#8600DD` (fuerte `#6B00B3`) | Secundario, degradados, resaltados |
| Azul noche | `#1B2A4E` | Fondos oscuros del tráiler, texto sobre claro |
| Crema | `#FFFBEE` / `#FFF7E6` | Fondo claro (el mismo de la app) |
| Tipografía | Segoe UI (o Inter de respaldo), pesos 700-800 en títulos | La misma de la web y de la presentación |

- Degradado del encabezado de la presentación: naranja → morado. Úsalo en cortinillas y en la tarjeta final.
- Rótulo fijo en cada escena con datos: *"Datos sintéticos · Bold en modo pruebas"*, pequeño, en una esquina.

---

## 3. Video 1: demo funcional (guion)

Tono: un estudiante de la UNAB enseñándole la app a un compañero. Explica con claridad, sin exagerar. Cada escena dice **qué pide el enunciado** y lo **muestra funcionando**.

| # | Tiempo aprox. | Pantalla | Narración (texto para la voz) |
|---|---|---|---|
| 1 | 0:00-0:15 | Logo, título "Asistente UNAB 360" y URL | "Este es el Asistente UNAB 360: un asistente académico con inteligencia artificial que conoce tus notas, tus tareas y tus trámites, en la web y en Android." |
| 2 | 0:15-0:35 | Diagrama de arquitectura (diapositiva 5) y captura del router de n8n (`48-n8n-00-router`) | "Corre en Amazon Web Services. Un router en n8n revisa cada pregunta, la clasifica y la envía al agente indicado: documentos, calendario, historial, noticias o trámites." |
| 3 | 0:35-0:55 | Web: "Probar como…" con las 7 personas; clic en **Santiago, Sistemas** | "Para la demo hay siete estudiantes de prueba de seis carreras. Entro como Santiago, de Ingeniería de Sistemas." |
| 4 | 0:55-1:20 | Pregunta: *"Muéstrame mis notas en gráfica"* → respuesta + gráfica | "Le pido mis notas en gráfica. El agente consulta la base de datos por MCP y dibuja mi promedio por semestre." |
| 5 | 1:20-1:45 | Panel **Hoy en tu U**: horario, tareas de TEMA, evaluación docente pendiente, noticias del día | "El panel Hoy junta mi horario, las tareas de TEMA por vencer, el recordatorio de calificar a mis profesores y las noticias del día con su fuente y su fecha." |
| 6 | 1:45-2:05 | Pregunta: *"¿Cuándo son las inscripciones de asignaturas 2027-1?"* y una sobre la insignia de competencias digitales (RAG, con fuente) | "Las preguntas institucionales las responde con los documentos oficiales de la universidad y cita de dónde sacó la respuesta." |
| 7 | 2:05-2:35 | Persona **Andrés Felipe, Administración**: *"Quiero pagar mi matrícula"* → tarjeta de $8.500.000 → **Pagar con Bold** → checkout embebido → tarjeta `4111 1111 1111 1111` → aprobado | "Andrés Felipe tiene la matrícula pendiente. El asistente crea la orden y abre el botón de Bold dentro de la misma página. Pago con una tarjeta de prueba… y queda aprobado." |
| 8 | 2:35-2:55 | Adjuntar la foto del cartel de biblioteca → descripción + QR detectado + enlace al catálogo | "También lee imágenes. Le muestro el cartel de la biblioteca: lee el texto, decodifica el código QR y me da el enlace oficial." |
| 9 | 2:55-3:10 | Persona **Valentina, Medicina**: *"¿Cuál es mi riesgo académico?"* | "Valentina tiene riesgo alto. Un modelo de machine learning entrenado con el historial calcula su probabilidad, y el asistente le explica por qué y qué hacer." |
| 10 | 3:10-3:20 | Guardrail: *"¿Cuáles son las notas de U00000002?"* → bloqueado | "Y si pido las notas de otro estudiante, se niega: los datos de cada persona están protegidos." |
| 11 | 3:20-3:50 | **Android**: login con persona, chat con gráfica y línea de 3.0 (`47`), panel Hoy (`44`), pago con Bold en la app (`42`, `43`) | "En Android es la misma experiencia: chat, gráficas, panel Hoy y pago con Bold sin salir de la app. El APK se descarga desde el QR de la página." |
| 12 | 3:50-4:05 | Dashboard de analítica `/app/analitica/` | "El dashboard muestra el uso del asistente y las métricas del modelo de riesgo." |
| 13 | 4:05-4:15 | Tarjeta final: URL, enlace a GitHub y nombres del equipo | "Asistente UNAB 360. Hecho por José Téllez y Santiago Cabezas para Ciencia de Datos." |

Edición:
- Resalta con un recuadro naranja el elemento del que habla la voz.
- Usa un rótulo con el criterio de la rúbrica en las escenas que lo cubren, por ejemplo "Scraper de noticias · 10 %" (escena 5), "Aplicación Android · 15 %" (escena 11) y "RAG · 20 %" (escena 6).

---

## 4. Video 2: tráiler promocional (guion)

Tono: anuncio de lanzamiento universitario. Frases cortas con pausas, y la música manda. Plano rápido (1 a 2 s por toma) con texto grande.

| # | Tiempo | Imagen | Voz / texto en pantalla |
|---|---|---|---|
| 1 | 0:00-0:06 | Negro → destellos naranja y morado; texto "Tu vida universitaria" | Voz: *"Notas. Tareas. Pagos. Trámites."* |
| 2 | 0:06-0:12 | Collage veloz de pestañas (Cosmos, TEMA, reservas, biblioteca) que se cierran | *"Cuatro plataformas. Diez pestañas. Cero tiempo."* |
| 3 | 0:12-0:18 | Silencio de golpe → aparece el logo UNAB y escribe "Asistente UNAB 360" | *"¿Y si todo cupiera en una sola conversación?"* |
| 4 | 0:18-0:28 | Gráfica que se dibuja + panel Hoy | *"Pregunta cómo vas… y míralo."* |
| 5 | 0:28-0:36 | Foto del cartel → QR detectado | *"Muéstrale una foto. La entiende."* |
| 6 | 0:36-0:44 | Botón Bold → "Pago aprobado" | *"Paga tu matrícula sin salir del chat."* |
| 7 | 0:44-0:52 | Teléfono Android girando con la app + web en laptop | *"En tu computador. En tu celular."* |
| 8 | 0:52-0:60 | Cifras grandes, una por golpe de música: "6 carreras" · "18 herramientas" · "11 fuentes de noticias" · "IA que predice el riesgo académico" | (sin voz, solo música) |
| 9 | 0:60-0:70 | Degradado naranja → morado, logo, "Asistente UNAB 360" y la URL | *"Asistente UNAB 360. Tu universidad, en una conversación."* |

- **Corte vertical de 30 s:** escenas 3, 4, 6, 7 y 9, con el texto centrado y una zona segura de 250 px arriba y abajo.
- No uses imágenes de personas reales ni fotos del campus que no sean nuestras. La identidad viene del logo y los colores.

---

## 5. Voces de ElevenLabs

> El conector de ElevenLabs de claude.ai **necesita autorización** en la configuración de conectores de claude.ai antes de usarse. Si no está autorizado, el agente prepara los textos y el usuario genera las voces en elevenlabs.io.

**Cómo elegir (no inventar nombres de voces):** en **Voice Library** filtra *Language: Spanish* y *Accent: Latin American* (si existe, *Colombian*). Prueba **3 candidatas por video** con la frase de prueba, guarda las muestras en `videos/voces/` y elige la que suene más natural en *matrícula*, *Bucaramanga* y *UNAB* (se pronuncia "u-nab", no "u-ene-a-be"). Anota el nombre y el `voice_id` elegidos al final de este documento.

| | Video 1 · Demo funcional | Video 2 · Tráiler |
|---|---|---|
| Perfil | Mujer o hombre de 25 a 35 años, acento latino neutro o colombiano, cálido, de "explicador" | Hombre de voz grave o mujer con presencia, acento latino, estilo de **tráiler o comercial** |
| Categoría en la librería | *Narrative & Story*, *Conversational* o *Educational* | *Advertisement*, *Characters & Animation* (épica) o *Narrative* (grave) |
| Modelo | `eleven_multilingual_v2` (estable y consistente en textos largos) | `eleven_v3` (más expresivo; admite marcas como `[pausa]` o `[susurro]`); si suena raro, `eleven_multilingual_v2` |
| Stability | 0,50 | 0,30-0,40 (más dramática) |
| Similarity | 0,75 | 0,80 |
| Style | 0,15 | 0,45-0,60 |
| Speaker boost | Sí | Sí |
| Velocidad | 1,0 | 0,9 (frases lentas y con peso) |
| Frase de prueba | "Le pido mis notas en gráfica y el agente consulta la base de datos por MCP." | "Asistente UNAB 360. Tu universidad, en una conversación." |

- Genera **un mp3 por escena** (no todo el guion de una vez), mide cada uno con `ffprobe` y ajusta la duración de las escenas a la voz real.
- **Si ElevenLabs no está disponible:** usa `edge-tts` con `es-CO-SalomeNeural` (Video 1) y `es-CO-GonzaloNeural` (Video 2), como en la skill `producto-promo-video-es`.

---

## 6. Música de fondo

| | Video 1 · Demo funcional | Video 2 · Tráiler |
|---|---|---|
| Estilo | *Corporate tech* o *lo-fi* suave: piano o pluck, pads, batería ligera. Sin voces | *Epic cinematic hybrid*: pulso de sintetizador → percusión que crece → golpe orquestal y *riser* antes del logo. Sin voces |
| BPM | 85-100 | 110-128 (o 90 en *half-time* con impactos) |
| Estructura | Plana y constante, que no distraiga. Loop limpio de 4 min o dos pistas encadenadas | Intro tensa (0-12 s) → **silencio** en la escena 3 → crece (18-52 s) → *drop* con las cifras (52-60 s) → golpe final en el logo |
| Volumen | −22 a −26 dB bajo la voz, con *ducking* automático (sidechain); sube a −14 dB en las transiciones sin voz | −18 dB bajo la voz y a pleno en la escena 8 |
| Búsqueda | "corporate technology background", "lofi study beat", "inspiring tech ambient" | "epic cinematic trailer", "hybrid trailer", "inspirational epic build" |

**Fuentes con licencia libre** (en orden):
1. **ElevenLabs Music**, si el plan lo incluye: genera la pista con el prompt de la tabla y la duración exacta.
2. **Pixabay Music:** licencia libre sin atribución obligatoria.
3. **Biblioteca de audio de YouTube:** filtra por "No se requiere atribución".

- Anota título, autor y enlace de cada pista en la sección 8 de este documento.
- **No uses música comercial** (canciones conocidas, bandas sonoras de películas).

**Mezcla final:** normaliza a **−14 LUFS** integrados y pico real de −1 dBTP. Haz *fade in* de 1 s y *fade out* de 2 s. Comprueba que la voz se entiende en el parlante de un portátil.

---

## 7. Verificación antes de entregar

- [ ] `ffprobe`: la duración coincide con la planeada y hay pista de audio AAC.
- [ ] Extraer 6 fotogramas por video (`ffmpeg -ss <t> -i video.mp4 -vframes 1 f.png`) y revisar que:
  - no haya texto cortado;
  - no se vea ninguna clave;
  - el logo se vea completo.
- [ ] Cada cifra dicha o escrita aparece en el README (26 fragmentos RAG, 18 herramientas MCP, 11 fuentes, 206 estudiantes, 6 carreras, AUC 0,86 en validación cruzada).
- [ ] Rótulo "Datos sintéticos · Bold en modo pruebas" visible en la demo.
- [ ] Ejecutar `reset-demo.sh` al terminar, para que la EC2 quede limpia para la presentación.
- [ ] Subir los videos, poner los enlaces en la tabla de entregables del README (fila "Video de demostración") y hacer commit.

## 8. Registro (lo llena el agente)

| Video | Voz (nombre · voice_id · modelo) | Música (título · autor · fuente · licencia) | Enlace |
|---|---|---|---|
| 01 Demo funcional (4:28) | ElevenLabs, un solo audio cortado en 17 bloques (nombre y voice_id: por anotar) | ElevenLabs Music, dos partes unidas con fundido de 4 s, recortada a la duración del video | <https://youtu.be/iAiiowTgKYs> |
| 02 Tráiler (1:10) | ElevenLabs, un solo audio cortado en 8 bloques (nombre y voice_id: por anotar) | ElevenLabs Music, 70 s, retrasada 1 s para que la entrada caiga en 18 s y el drop en 52 s | <https://youtu.be/e0BDTLoeVEg> |

**Cómo se arman:** las grabaciones crudas quedan en `videos/raw/` y los proyectos HyperFrames en `videos/hf-demo/` y `videos/hf-trailer/`. `videos/demo_spec.py` define las escenas de la demo (recortes, velocidades, resaltados y voces), `videos/demo_build.py` genera los clips y las composiciones, y `videos/mezcla.py` corta el audio único de ElevenLabs (`split` por silencios; si la voz sale sin pausas largas, se corta por palabras con una transcripción de Whisper), normaliza las voces y le baja la música bajo la voz (`prep`, demo con ganancia 0,45 y ducking 0,55; tráiler 1,0 y 0,75), rehace la pista de audio sin volver a renderizar (`mixdown`) y masteriza a −14 LUFS (`master`). La voz queda unos 8 dB por encima de la música.

**Nota de grabación (20-nov-2026):** al grabar, el botón "Pagar con Bold" de la app Android no abría el checkout: en el WebView las unidades `vh`/`dvh` valen 0 y el modal embebido de Bold quedaba con alto 0. Por eso la escena 11 muestra chat, gráfica y panel Hoy en Android, y el pago se ve en la web. Ya está corregido en `web/pagar.html`: dentro del WebView se usa el modo `redirect` de Bold (verificado de punta a punta en el emulador, con pago aprobado y regreso a la app).
