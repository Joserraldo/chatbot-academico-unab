"""
Scraper de noticias y novedades (cursos, convocatorias, certificaciones).

Lee los feeds RSS públicos configurados en sources.json, clasifica cada entrada
por palabras clave y hace UPSERT en academico.noticia (url única).
Se ejecuta en bucle cada SCRAPE_INTERVAL_HOURS (contenedor `scraper`) o una vez con --once.

Buenas prácticas: usa feeds RSS (formato pensado para ser consumido), User-Agent
identificable, timeout, y frecuencia baja (por defecto cada 6 h).
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx
import psycopg

DATABASE_URL = os.environ.get("SCRAPER_DATABASE_URL", "postgresql://unab_admin:cambia_esto@localhost:5432/unab")
INTERVAL_H = float(os.environ.get("SCRAPE_INTERVAL_HOURS", "6"))
UA = "AsistenteAcademicoUNAB-scraper/1.0 (proyecto academico)"

CATEGORIAS = {
    "curso": r"\b(curso|diplomado|taller|bootcamp|capacitaci[oó]n|moodle|formaci[oó]n)\b",
    "convocatoria": r"\b(convocatoria|inscripci[oó]n|becas?|semillero|postulaci[oó]n|beca)\b",
    "certificacion": r"\b(certificaci[oó]n|certificado|insignia|badge|acreditaci[oó]n)\b",
}


def clasificar(texto: str) -> str:
    t = texto.lower()
    for cat, patron in CATEGORIAS.items():
        if re.search(patron, t):
            return cat
    return "general"


def limpiar(s: str | None, n: int = 400) -> str:
    s = re.sub(r"<[^>]+>", " ", html.unescape(s or ""))
    return re.sub(r"\s+", " ", s).strip()[:n]


def leer_feed(url: str, fuente: str) -> list[dict]:
    r = httpx.get(url, headers={"User-Agent": UA}, timeout=20, follow_redirects=True)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    items = []
    for it in root.iter("item"):
        titulo = limpiar(it.findtext("title"), 300)
        link = (it.findtext("link") or "").strip()
        if not titulo or not link:
            continue
        resumen = limpiar(it.findtext("description"))
        fecha = None
        if it.findtext("pubDate"):
            try:
                fecha = parsedate_to_datetime(it.findtext("pubDate")).date()
            except (TypeError, ValueError):
                pass
        items.append({"titulo": titulo, "url": link, "resumen": resumen, "fuente": fuente,
                      "fecha": fecha, "categoria": clasificar(f"{titulo} {resumen}")})
    return items


def guardar(items: list[dict]) -> int:
    sql = """INSERT INTO academico.noticia (titulo, url, resumen, categoria, fuente, fecha_publicacion)
             VALUES (%(titulo)s, %(url)s, %(resumen)s, %(categoria)s, %(fuente)s, %(fecha)s)
             ON CONFLICT (url) DO UPDATE SET titulo = EXCLUDED.titulo, resumen = EXCLUDED.resumen,
                                             categoria = EXCLUDED.categoria, capturada_en = now()"""
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, items)
    return len(items)


def ejecutar() -> None:
    fuentes = json.loads((Path(__file__).parent / "sources.json").read_text(encoding="utf-8"))
    total = 0
    for f in fuentes:
        try:
            items = leer_feed(f["url"], f["nombre"])
            total += guardar(items)
            print(f"[scraper] {f['nombre']}: {len(items)} entradas")
        except Exception as e:  # una fuente caída no detiene las demás
            print(f"[scraper] ERROR en {f['nombre']}: {e}")
    print(f"[scraper] total upsert: {total}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args()
    while True:
        ejecutar()
        if a.once:
            break
        time.sleep(INTERVAL_H * 3600)
