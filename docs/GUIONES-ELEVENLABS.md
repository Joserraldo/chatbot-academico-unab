# Guiones para ElevenLabs y prompts de música

> Complementa a [VIDEOS.md](VIDEOS.md). **Un solo audio por video:** pega el texto completo en ElevenLabs y descarga un único mp3. Las pausas `<break time="…" />` ya están medidas contra la línea de tiempo del video. Después, `python mezcla.py split` corta el audio por sus silencios largos y pone cada frase en su segundo exacto, así que una pausa que salga un poco más larga o más corta no descuadra nada.
>
> Los textos ya vienen escritos para que la voz los pronuncie bien: "Unab" (se dice "u-nab"), "trescientos sesenta", "eme ce pe", "cu erre", "a pe ka". No los cambies a siglas.
>
> **Modelo: `Eleven Multilingual v2` en los dos videos.** Las etiquetas `<break>` solo funcionan en v2 (Eleven v3 las ignora). Cada `<break>` admite hasta 3 s; las pausas más largas se escriben encadenando varias.

## Video 2 · Tráiler (listo para generar)

**Ajustes:** Stability 35 % · Similarity 80 % · Style 50 % · Speaker boost activado · Velocidad 0,9.
**Voz:** en Voice Library filtra *Spanish* y *Latin American* (o *Colombian*), en la categoría *Advertisement* o *Narrative*. Busca una voz grave de tráiler y pruébala primero con la última frase.

**Texto para pegar (todo de una vez):**

```
Notas. <break time="0.5s" /> Tareas. <break time="0.5s" /> Pagos. <break time="0.5s" /> Trámites.
<break time="1.2s" />
Cuatro plataformas. <break time="0.5s" /> Diez pestañas. <break time="0.6s" /> Cero tiempo.
<break time="2.3s" />
¿Y si todo cupiera... en una sola conversación?
<break time="1.5s" />
Pregunta cómo vas... y míralo.
<break time="3s" /> <break time="3s" /> <break time="0.6s" />
Muéstrale una foto. <break time="0.6s" /> La entiende.
<break time="3s" /> <break time="1.2s" />
Paga tu matrícula sin salir del chat.
<break time="3s" /> <break time="1.8s" />
En tu computador. <break time="0.7s" /> En tu celular.
<break time="3s" /> <break time="3s" /> <break time="3s" /> <break time="3s" /> <break time="0.4s" />
Asistente Unab trescientos sesenta. <break time="0.8s" /> Tu universidad, en una conversación.
```

**Dónde cae cada frase en el video** (cada bloque no debe pasar de su duración máxima; si una frase sale más larga, regenera o sube la velocidad a 1,0):

| # | Frase | Entra en | Duración máxima | Qué se ve |
|---|---|---|---|---|
| 1 | Notas… Trámites. | 0:00.3 | 5,6 s | Palabras de impacto sobre negro |
| 2 | Cuatro plataformas… Cero tiempo. | 0:06.3 | 5,4 s | Se apilan 10 pestañas y se cierran |
| 3 | ¿Y si todo cupiera…? | 0:13.9 | 3,8 s | Silencio, burbuja de chat, aparece el logo |
| 4 | Pregunta cómo vas… y míralo. | 0:19.2 | 3,0 s | Se dibuja la gráfica de notas |
| 5 | Muéstrale una foto. La entiende. | 0:28.8 | 3,9 s | Escaneo del cartel y "QR detectado" |
| 6 | Paga tu matrícula sin salir del chat. | 0:36.9 | 3,1 s | Clic en Bold y "¡Pago aprobado!" |
| 7 | En tu computador. En tu celular. | 0:44.8 | 4,0 s | Laptop y celular Android |
| — | (sin voz) | 0:52 a 1:00 | — | Cifras al golpe de la música |
| 8 | Asistente Unab trescientos sesenta… | 1:01.2 | 6,4 s | Logo y URL sobre el degradado |

Guarda el mp3 como `videos/trailer-elevenlabs.mp3` y, desde `videos/`:

```
python mezcla.py split trailer-elevenlabs.mp3 hf-trailer t01,t02,t03,t04,t05,t06,t07,t09
python mezcla.py prep hf-trailer
```

## Video 1 · Demo funcional (listo para generar)

**Ajustes:** Multilingual v2 · Stability 50 % · Similarity 75 % · Style 15 % · Speaker boost activado · Velocidad 1,0.
**Voz:** filtra *Spanish* y *Latin American* (o *Colombian*), en la categoría *Conversational* o *Educational*. Busca una voz cálida de "explicador" de 25 a 35 años.

Las pausas largas son los momentos en que el video muestra la app trabajando sin narración (respuestas del modelo, el checkout de Bold). Con ellas el mp3 crudo ya queda en sincronía con el video.

> **Si ElevenLabs acelera la voz o mete ruidos** (pasa cuando hay muchas etiquetas `<break>` en una sola generación), cambia cada cadena de pausas largas por un solo `<break time="3s" />`. La sincronía no se pierde, porque `mezcla.py split` vuelve a poner cada bloque en su segundo exacto.

**Texto para pegar (todo de una vez):**

```
Este es el Asistente Unab trescientos sesenta. <break time="0.4s" /> Un asistente académico con inteligencia artificial que conoce tus notas, tus tareas y tus trámites... en la web y en Android.
<break time="1.5s" />
Corre en Amazon Web Services. <break time="0.3s" /> Un router en n ocho n revisa cada pregunta, la clasifica y la envía al agente indicado: documentos, calendario, historial, noticias o trámites.
<break time="1.7s" />
Para la demo hay siete estudiantes de prueba, de seis carreras. <break time="0.3s" /> Entro como Santiago, de Ingeniería de Sistemas.
<break time="3s" /> <break time="3s" /> <break time="2.1s" />
Le pido mis notas en gráfica. <break time="0.3s" /> El agente consulta la base de datos por eme ce pe... y dibuja mi promedio por semestre.
<break time="3s" /> <break time="3s" /> <break time="3s" /> <break time="3s" /> <break time="1.2s" />
El panel Hoy junta mi horario, las tareas de Tema por vencer, el recordatorio de calificar a mis profesores... y las noticias del día, con su fuente y su fecha.
<break time="3s" /> <break time="3s" /> <break time="3s" /> <break time="3s" /> <break time="0.3s" />
Las preguntas institucionales las responde con los documentos oficiales de la universidad, y cita de dónde sacó la respuesta.
<break time="3s" /> <break time="3s" /> <break time="3s" /> <break time="3s" /> <break time="3s" /> <break time="3s" /> <break time="0.8s" />
Andrés Felipe tiene la matrícula pendiente. <break time="0.3s" /> El asistente crea la orden y abre el botón de Bold dentro de la misma página.
<break time="3s" /> <break time="3s" /> <break time="3s" /> <break time="3s" /> <break time="2.8s" />
Pago con una tarjeta de prueba...
<break time="3s" /> <break time="3s" /> <break time="3s" /> <break time="3s" /> <break time="0.8s" />
Y queda aprobado.
<break time="3s" /> <break time="0.4s" />
También lee imágenes. <break time="0.3s" /> Le muestro el cartel de la biblioteca: lee el texto, decodifica el código cu erre y me da el enlace oficial.
<break time="3s" /> <break time="3s" /> <break time="2.6s" />
Valentina tiene riesgo alto. <break time="0.3s" /> Un modelo de machine learning, entrenado con el historial, calcula su probabilidad... y el asistente le explica por qué y qué hacer.
<break time="3s" /> <break time="3s" /> <break time="1.4s" />
Y si pido las notas de otro estudiante... <break time="0.3s" /> se niega. Los datos de cada persona están protegidos.
<break time="2.7s" />
En Android es la misma experiencia. <break time="0.3s" /> Entro como Santiago desde el celular.
<break time="3s" /> <break time="3s" /> <break time="3s" /> <break time="1.8s" />
Le pido mis notas en gráfica, con la línea de aprobación en tres.
<break time="3s" /> <break time="3s" /> <break time="1s" />
Y el panel Hoy, con mi horario, mis tareas y las noticias. <break time="0.3s" /> El a pe ka se descarga desde el código cu erre de la página.
<break time="3s" /> <break time="0.7s" />
El dashboard muestra el uso del asistente y las métricas del modelo de riesgo.
<break time="3s" /> <break time="3s" /> <break time="3s" /> <break time="0.3s" />
Asistente Unab trescientos sesenta. <break time="0.4s" /> Hecho por José Téllez y Santiago Cabezas, para Ciencia de Datos.
```

| # | Bloque | Entra en | Duración máxima |
|---|---|---|---|
| 1 | `d01` | 0:00.8 | 12.5 s |
| 2 | `d02` | 0:13.6 | 14.8 s |
| 3 | `d03` | 0:28.7 | 15.8 s |
| 4 | `d04` | 0:44.8 | 21.2 s |
| 5 | `d05` | 1:06.3 | 22.0 s |
| 6 | `d06` | 1:28.6 | 26.2 s |
| 7 | `d07a` | 1:55.2 | 22.5 s |
| 8 | `d07b` | 2:18.0 | 15.2 s |
| 9 | `d07c` | 2:33.5 | 5.0 s |
| 10 | `d08` | 2:38.8 | 17.6 s |
| 11 | `d09` | 2:56.8 | 17.3 s |
| 12 | `d10` | 3:14.3 | 9.1 s |
| 13 | `d11a` | 3:23.7 | 16.3 s |
| 14 | `d11b` | 3:40.3 | 11.4 s |
| 15 | `d11c` | 3:52.0 | 12.2 s |
| 16 | `d12` | 4:04.4 | 14.2 s |
| 17 | `d13` | 4:18.9 | 9.8 s |

Guarda el mp3 como `videos/demo-elevenlabs.mp3` y, desde `videos/`:

```
python mezcla.py split demo-elevenlabs.mp3 hf-demo d01,d02,d03,d04,d05,d06,d07a,d07b,d07c,d08,d09,d10,d11a,d11b,d11c,d12,d13
python mezcla.py prep hf-demo
python demo_build.py --no-clips
python mezcla.py prep hf-demo
```

(El primer `prep` normaliza las voces nuevas, `demo_build` recoloca las escenas según su duración real y el segundo `prep` vuelve a calcular el ducking de la música con esos tiempos.)

Si algún bloque pasa de su duración máxima, el generador estira la escena y el video sigue cuadrando, pero queda más largo.

## Música (ElevenLabs Music)

Genera cada pista con la duración exacta, en instrumental y sin voces. Guárdala como `musica.mp3` en la carpeta `assets/` del proyecto correspondiente.

### Video 1 · `videos/hf-demo/assets/musica.mp3` (4 min 30 s; el video dura 4:28,5)

```
Instrumental corporate tech / lo-fi background for a university software demo video. 92 BPM, F major, warm and optimistic but understated. Soft electric piano plucks playing gentle eighth-note arpeggios, warm analog pads, round sub bass, light brushed drums with subtle swing, soft shaker. Constant energy, no big drops, no builds, no risers — it must sit under a narrator for 4 minutes 30 seconds without distracting, exact length 4:30. Leave the 2–5 kHz range clear for speech. Every 16 bars change the arpeggio pattern slightly; drop the drums for 8 bars around the middle. Clean ending with a soft 3-second fade. No vocals, no choir, no lead melody.
```

### Video 2 · `videos/hf-trailer/assets/musica.mp3` (70 s exactos, 120 BPM)

```
Epic cinematic hybrid trailer music, exactly 70 seconds, 120 BPM, A minor resolving to C major. Structure with precise timing:
0:00–0:12 tense intro: low drone, ticking clock, pulsing filtered synth in sixteenth notes slowly opening, soft sub boom at 0:00 and 0:06; a short noise riser from 0:11 that cuts off abruptly at 0:12.
0:12–0:18 near silence: only a faint reverb tail and one soft high bell ping at 0:13.5; reverse cymbal swell from 0:17.5 into 0:18.
0:18 big impact hit, then 0:18–0:52 a steady build: taiko and toms, driving synth bass pulse, epic string ostinatos and brass swells, chord progression Am–F–C–G, intensity rising every 8 seconds, long riser 0:48–0:52.
0:52–1:00 drop: four massive trailer hits exactly at 0:52, 0:54, 0:56 and 0:58 with the full pulse between them.
1:00 the biggest orchestral hit, then a wide sustained C major chord with long reverb fading to silence by 1:10.
Inspirational, proud, modern university launch. No vocals.
```

Si el plan de ElevenLabs no incluye música, busca en Pixabay Music con "epic cinematic trailer" o "corporate technology background" y corta la pista a la estructura de arriba.

## Cómo reemplazar y volver a renderizar

Desde la carpeta `videos/`, en Git Bash:

```
cd hf-trailer
npx hyperframes render --quality standard --output ../02-trailer-unab360.mp4
cd ../hf-demo
npx hyperframes render --quality standard --output ../01-demo-funcional.mp4
```

Si cambian las duraciones de la voz del Video 1, avísale al agente para que reajuste los `data-start` de `index.html`. El tráiler no lo necesita mientras cada toma quepa en su duración máxima.
