"""
Scraper de noticias del día (educación, tecnología, ingeniería de sistemas) y novedades
de la UNAB (cursos, convocatorias, certificaciones).

Lee los feeds RSS configurados en sources.json (RSS de la UNAB, búsquedas de Google
Noticias y feeds directos de medios), normaliza fechas a America/Bogota, clasifica por
palabras clave, elimina duplicados y hace UPSERT en academico.noticia (url única).

Uso:
  python scraper.py                 # bucle cada SCRAPE_INTERVAL_HOURS (contenedor `scraper`)
  python scraper.py --once          # una sola pasada contra la base de datos
  python scraper.py --dry-run       # sin base de datos: imprime la tabla de noticias de hoy

Buenas prácticas: feeds RSS (formato pensado para consumirse), User-Agent identificable,
timeout por fuente, aislamiento de errores y frecuencia baja (por defecto cada 6 h).
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import time
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx

DATABASE_URL = os.environ.get("SCRAPER_DATABASE_URL", "postgresql://unab_admin:cambia_esto@localhost:5432/unab")
INTERVAL_H = float(os.environ.get("SCRAPE_INTERVAL_HOURS", "6"))
DIAS_RETENCION = int(os.environ.get("SCRAPE_DIAS", "7"))
UA = "AsistenteAcademicoUNAB-scraper/2.0 (proyecto academico)"

# Colombia no tiene horario de verano: UTC-5 fijo (evita depender de tzdata en la imagen slim).
BOGOTA = timezone(timedelta(hours=-5), "America/Bogota")

# Palabras clave por categoría, en orden de prioridad (la primera que coincida gana).
CATEGORIAS = {
    "convocatoria": r"\b(convocatorias?|inscripci[oó]n(es)?|becas?|semilleros?|postulaci[oó]n(es)?)\b",
    "certificacion": r"\b(certificaci[oó]n(es)?|certificados?|insignias?|badges?|acreditaci[oó]n|acreditad[oa]s?)\b",
    "curso": r"\b(cursos?|diplomados?|talleres?|bootcamps?|capacitaci[oó]n(es)?|moodle|formaci[oó]n)\b",
    "ingenieria_sistemas": (
        r"\b(ingenier[ií]a de sistemas|ingenieros? de sistemas|programaci[oó]n|programadores?|"
        r"desarrollo de software|desarrolladores?|software|c[oó]digo abierto|ciberseguridad|"
        r"machine learning|aprendizaje autom[aá]tico|ciencia de datos|python|javascript|"
        r"computaci[oó]n|inform[aá]tica|algoritmos?|devops|nube|cloud|bases? de datos)\b"
    ),
    "tecnologia": (
        r"\b(tecnolog[ií]as?|tecnol[oó]gic[oa]s?|inteligencia artificial|chatgpt|openai|gemini|"
        r"robots?|rob[oó]tica|digital(es)?|internet|apps?|aplicaci[oó]n(es)? m[oó]vil|celulares?|"
        r"smartphones?|startups?|chips?|semiconductores?|5g|innovaci[oó]n|gadgets?|videojuegos?|"
        r"computadores?|ia)\b"
    ),
    "educacion": (
        r"\b(educaci[oó]n|educativ[oa]s?|universidad(es)?|universitari[oa]s?|colegios?|"
        r"estudiantes?|docentes?|profesores?|icfes|mineducaci[oó]n|matr[ií]cula|"
        r"pregrado|posgrado|escuel(a|as)|acad[eé]mic[oa]s?|ies)\b"
    ),
}
# La UNAB conserva la lógica original: solo estas tres categorías y si no, "general".
CATEGORIAS_UNAB = ("curso", "convocatoria", "certificacion")


def clasificar(texto: str, base: str = "general", unab: bool = False) -> str:
    t = texto.lower()
    for cat in (CATEGORIAS_UNAB if unab else CATEGORIAS):
        if re.search(CATEGORIAS[cat], t):
            return cat
    return "general" if unab else (base or "general")


def limpiar(s: str | None, n: int = 400) -> str:
    s = re.sub(r"<[^>]+>", " ", html.unescape(s or ""))
    return re.sub(r"\s+", " ", s).strip()[:n]


def a_bogota(texto: str | None) -> date | None:
    """Convierte fechas RFC 822 / ISO 8601 a la fecha civil de America/Bogota."""
    if not texto:
        return None
    try:
        dt = parsedate_to_datetime(texto.strip())
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(texto.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(BOGOTA).date()


def leer_feed(f: dict) -> list[dict]:
    r = httpx.get(f["url"], headers={"User-Agent": UA}, timeout=f.get("timeout", 20), follow_redirects=True)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    google = f.get("tipo") == "google_news"
    items = []
    for it in root.iter("item"):
        titulo = limpiar(it.findtext("title"), 300)
        link = (it.findtext("link") or "").strip()
        if not titulo or not link:
            continue
        fuente = f["nombre"]
        if google:
            # Google Noticias: el medio real va en <source> y como sufijo " - Medio" del título.
            medio = limpiar(it.findtext("source"), 120)
            if medio and titulo.endswith(f" - {medio}"):
                titulo = titulo[: -len(medio) - 3].rstrip()
            elif " - " in titulo:
                titulo, _, sufijo = titulo.rpartition(" - ")
                medio = medio or sufijo.strip()
            fuente = medio or "Google Noticias"
            resumen = ""  # el description de Google solo repite el título con enlace
        else:
            resumen = limpiar(it.findtext("description"))
        fecha = a_bogota(it.findtext("pubDate") or it.findtext("{http://purl.org/dc/elements/1.1/}date"))
        items.append({"titulo": titulo, "url": link, "resumen": resumen, "fuente": fuente, "fecha": fecha,
                      "categoria": clasificar(f"{titulo} {resumen}", f.get("categoria_base", "general"),
                                              f.get("clasificacion") == "unab")})
    return items


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", t).split())


def deduplicar(items: list[dict]) -> list[dict]:
    """Quita duplicados por url y títulos casi idénticos (misma noticia en varios medios)."""
    vistas, normas, salida = set(), [], []
    for it in items:
        if it["url"] in vistas:
            continue
        n = _norm(it["titulo"])
        if any(n == m or SequenceMatcher(None, n, m).ratio() >= 0.88 for m in normas):
            continue
        vistas.add(it["url"])
        normas.append(n)
        salida.append(it)
    return salida


def recolectar() -> list[dict]:
    """Lee todas las fuentes (con errores aislados), filtra a 7 días y deduplica."""
    fuentes = json.loads((Path(__file__).parent / "sources.json").read_text(encoding="utf-8"))
    hoy = datetime.now(BOGOTA).date()
    limite = hoy - timedelta(days=DIAS_RETENCION)
    todas = []
    for f in fuentes:
        try:
            items = leer_feed(f)
        except Exception as e:  # una fuente caída no detiene las demás
            print(f"[scraper] ERROR en {f['nombre']}: {type(e).__name__}: {e}")
            continue
        # Sin fecha => se asume capturada hoy; fuera de ventana => se descarta.
        for it in items:
            it["fecha"] = it["fecha"] or hoy
        recientes = [i for i in items if limite <= i["fecha"] <= hoy + timedelta(days=1)]
        print(f"[scraper] {f['nombre']}: {len(items)} leídas, {len(recientes)} en los últimos {DIAS_RETENCION} días")
        todas.extend(recientes)
    unicas = deduplicar(todas)
    print(f"[scraper] total: {len(todas)} recientes, {len(unicas)} tras deduplicar")
    return unicas


def guardar(items: list[dict]) -> int:
    import psycopg  # import tardío: --dry-run no necesita base de datos
    sql = """INSERT INTO academico.noticia (titulo, url, resumen, categoria, fuente, fecha_publicacion)
             VALUES (%(titulo)s, %(url)s, %(resumen)s, %(categoria)s, %(fuente)s, %(fecha)s)
             ON CONFLICT (url) DO UPDATE SET titulo = EXCLUDED.titulo, resumen = EXCLUDED.resumen,
                                             categoria = EXCLUDED.categoria, fuente = EXCLUDED.fuente,
                                             fecha_publicacion = EXCLUDED.fecha_publicacion,
                                             capturada_en = now()"""
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, items)
    return len(items)


def ejecutar() -> None:
    items = recolectar()
    print(f"[scraper] total upsert: {guardar(items)}")


def tabla_hoy(items: list[dict], limite: int = 30) -> None:
    hoy = datetime.now(BOGOTA).date()
    sel = [i for i in items if i["fecha"] == hoy]
    titulo = f"Noticias de hoy ({hoy})"
    if not sel:  # si aún no hay noticias de hoy, muestra las más recientes
        sel = sorted(items, key=lambda i: i["fecha"], reverse=True)[:15]
        titulo = "Sin noticias de hoy; las más recientes"
    print(f"\n{titulo}: {len(sel)}")
    print(f"{'categoria':<20} {'fecha':<11} {'fuente':<26} titulo")
    for i in sorted(sel, key=lambda i: (i["categoria"], i["fuente"]))[:limite]:
        print(f"{i['categoria']:<20} {i['fecha']!s:<11} {i['fuente'][:25]:<26} {i['titulo'][:90]}")
    print(f"(mostrando {min(limite, len(sel))} de {len(sel)})")
    print("Por categoría:", dict(Counter(i["categoria"] for i in sel)))
    print("Por fuente:", dict(Counter(i["fuente"] for i in sel).most_common(8)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="una sola pasada y salir")
    ap.add_argument("--dry-run", action="store_true", help="no usa la base de datos; imprime las noticias de hoy")
    ap.add_argument("--limite", type=int, default=30, help="filas a mostrar con --dry-run")
    a = ap.parse_args()
    if a.dry_run:
        tabla_hoy(recolectar(), a.limite)
        raise SystemExit(0)
    while True:
        ejecutar()
        if a.once:
            break
        time.sleep(INTERVAL_H * 3600)
