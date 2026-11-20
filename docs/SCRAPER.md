# Scraper de noticias del día

Servicio `scraper/` que alimenta la tabla `academico.noticia` con las noticias del día de
**educación, tecnología e ingeniería de sistemas**, cada una con **fuente** y **fecha**, además
de las novedades de la UNAB (cursos, convocatorias, certificaciones).

## Fuentes (`scraper/sources.json`)

| Tipo | Fuente | `categoria_base` |
|---|---|---|
| RSS UNAB | UNAB - Noticias (`unab.edu.co/feed/`) | general (lógica original) |
| Google Noticias (`hl=es-419&gl=CO&ceid=CO:es-419`) | "educación superior Colombia" | educacion |
| | "ingeniería de sistemas" | ingenieria_sistemas |
| | "inteligencia artificial" | tecnologia |
| | "tecnología Colombia" | tecnologia |
| | "Ministerio de Educación Colombia" | educacion |
| RSS directo | Xataka, El Tiempo - Tecnósfera, ENTER.CO, Hipertextual, WIRED en Español | tecnologia |

Los feeds directos se verificaron con `curl` (HTTP 200, RSS válido y con ítems de la fecha actual).
Se descartaron por fallar: Semana (404), Universia (devuelve HTML, no RSS), Xataka Colombia
(RSS vigente pero con ítems de 2025) y el feed del Ministerio de Educación (sin respuesta).

Cada fuente admite `tipo` (`rss` | `google_news`), `categoria_base`, `timeout` (segundos, por
fuente) y `clasificacion: "unab"` para conservar la lógica original de la UNAB.

**`fuente` es el medio real.** En Google Noticias se toma del elemento `<source>` y se elimina el
sufijo ` - Medio` del título. En los feeds directos es el nombre de la fuente.

## Procesamiento

1. **Aislamiento de errores:** cada fuente tiene su timeout; si una falla se registra y las demás continúan.
2. **Fechas:** se normalizan a la fecha civil de `America/Bogota` (UTC-5 fijo, Colombia no tiene
   horario de verano). Sin fecha se asume la de captura.
3. **Ventana:** solo se conservan los últimos 7 días (`SCRAPE_DIAS`, por defecto 7).
4. **Deduplicación:** por `url` y por títulos casi idénticos (normalizados sin tildes, similitud >= 0,88);
   se queda la primera aparición (la UNAB va primero en `sources.json`).
5. **Upsert:** `INSERT ... ON CONFLICT (url) DO UPDATE` en `academico.noticia`.
6. **Log:** una línea por fuente (`leídas`, `en los últimos 7 días`) y los totales.

## Clasificación

Por palabras clave sobre título + resumen, en orden de prioridad (gana la primera que coincide):
`convocatoria` > `certificacion` > `curso` > `ingenieria_sistemas` > `tecnologia` > `educacion`.
Si nada coincide se usa la `categoria_base` de la fuente. Las entradas de la UNAB solo pueden ser
`curso | convocatoria | certificacion | general` (lógica original). Las expresiones están en
`CATEGORIAS` dentro de `scraper.py`. La columna `categoria` es `TEXT` libre, no requiere migración.

## Frecuencia

Bucle cada `SCRAPE_INTERVAL_HOURS` (por defecto 6, ver `docker-compose.yml`). Frecuencia baja y
User-Agent identificable por cortesía con los medios.

## Integración

```
scraper (RSS + Google Noticias) -> academico.noticia -> v_noticias_recientes
   -> workflow n8n 04 (rama B: el agente responde "noticias de hoy" citando fuente y fecha)
   -> GET /api/noticias/hoy?limite=10  (pública, ver CONTRATOS-V2)
   -> panel "Hoy en tu U" de la web y de la app (GET /api/hoy/{codigo} -> noticias[])
```

Cada noticia se entrega con `titulo`, `url`, `fuente`, `categoria` y `fecha_publicacion`.

## Cómo ejecutarlo

```bash
python -m venv .venv-scraper
.venv-scraper/Scripts/pip install -r scraper/requirements.txt
.venv-scraper/Scripts/python scraper/scraper.py --dry-run --limite 20   # sin base de datos
SCRAPER_DATABASE_URL=postgresql://usuario:clave@localhost:5432/unab .venv-scraper/Scripts/python scraper/scraper.py --once
```

`--dry-run` imprime la tabla de noticias de hoy (categoría, fecha, fuente, título) y los conteos;
si hoy aún no hay noticias, muestra las más recientes. En Docker: `docker compose up -d scraper`
(`docker compose run --rm scraper python scraper.py --once` para una sola pasada).

## Prueba realizada

- `--dry-run` en vivo: 11 fuentes, 190 noticias con fecha de hoy.
- `--once` contra PostgreSQL local (pgserver) con `01_schema.sql` cargado: 320 filas
  (tecnologia 232, educacion 41, ingenieria_sistemas 20, certificacion 14, convocatoria 7, general 6),
  fechas de hoy (190), ayer (75) y días anteriores; una segunda pasada deja 320 filas (upsert idempotente).
