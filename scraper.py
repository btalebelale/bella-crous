#!/usr/bin/env python3
"""Scraper de logements CROUS.

Récupère la page de résultats (rendue côté serveur) de trouverunlogement.lescrous.fr,
extrait les annonces, et signale les NOUVELLES annonces par rapport au dernier passage.

Aucune dépendance externe : uniquement la bibliothèque standard Python.

Variables d'environnement :
  SEARCH_URL   URL(s) de recherche CROUS (obligatoire), séparées par des espaces ou
               des retours à la ligne, ex :
               https://trouverunlogement.lescrous.fr/tools/42/search?bounds=2.2_48.9_2.4_48.8
  STATE_FILE   Fichier de suivi des annonces déjà vues (défaut : state.json)
  GITHUB_OUTPUT  (fourni par GitHub Actions) reçoit has_new / count / subject
"""

import gzip
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from html import unescape

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Un bloc "annonce" commence par class="fr-card " (espace = carte externe, pas fr-card__…)
CARD_SPLIT = 'class="fr-card '
RE_LINK = re.compile(r'href="(/tools/\d+/accommodations/(\d+))"[^>]*>([^<]+)</a>')
RE_PRICE = re.compile(r'fr-badge">([^<]+)</p>')
RE_DESC = re.compile(r'fr-card__desc">([^<]+)</p>')
RE_COUNT = re.compile(r'(\d+)\s+logements?\s+trouv')
BASE = "https://trouverunlogement.lescrous.fr"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        return raw.decode("utf-8", errors="replace")


def parse(html: str):
    """Retourne (count_annonce, liste d'annonces)."""
    count_match = RE_COUNT.search(html)
    count = int(count_match.group(1)) if count_match else None

    listings = {}
    for chunk in html.split(CARD_SPLIT)[1:]:
        link = RE_LINK.search(chunk)
        if not link:
            continue
        rel_url, ident, title = link.group(1), link.group(2), unescape(link.group(3).strip())
        price = RE_PRICE.search(chunk)
        desc = RE_DESC.search(chunk)
        listings[ident] = {
            "id": ident,
            "title": title,
            "price": unescape(price.group(1).strip()) if price else "",
            "address": unescape(desc.group(1).strip()) if desc else "",
            "url": BASE + rel_url,
        }
    return count, list(listings.values())


def load_state(path: str):
    try:
        with open(path, encoding="utf-8") as f:
            return set(json.load(f).get("seen", []))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_state(path: str, ids):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"seen": sorted(ids)}, f, ensure_ascii=False, indent=2)


def zone_label(url: str) -> str:
    """Nom de la zone d'une URL de recherche (paramètre locationName), sinon l'URL."""
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    name = qs.get("locationName", [""])[0]
    return name or url


def build_html(new_listings, urls):
    buttons = "".join(
        f"""<a href="{u}" style="background:#000091;color:#fff;padding:10px 16px;
           text-decoration:none;border-radius:4px;margin-right:8px;display:inline-block;
           margin-bottom:8px">{zone_label(u)}</a>"""
        for u in urls
    )
    rows = "".join(
        f"""<tr>
          <td style="padding:8px;border-bottom:1px solid #eee">
            <a href="{l['url']}" style="font-weight:bold;color:#000091">{l['title']}</a><br>
            <span style="color:#666;font-size:13px">{l['address']}</span>
          </td>
          <td style="padding:8px;border-bottom:1px solid #eee;white-space:nowrap">{l['price']}</td>
        </tr>"""
        for l in new_listings
    )
    return f"""<div style="font-family:Arial,sans-serif;max-width:600px">
      <h2 style="color:#000091">🏠 {len(new_listings)} nouveau(x) logement(s) CROUS disponible(s)</h2>
      <table style="width:100%;border-collapse:collapse">{rows}</table>
      <p style="margin-top:16px">{buttons}</p>
      <p style="color:#999;font-size:12px">Dépêche-toi, les logements CROUS partent vite.</p>
    </div>"""


def set_output(key: str, value: str):
    out = os.environ.get("GITHUB_OUTPUT")
    if not out:
        return
    with open(out, "a", encoding="utf-8") as f:
        f.write(f"{key}={value}\n")


def main() -> int:
    urls = os.environ.get("SEARCH_URL", "").split()
    if not urls:
        print("ERREUR : la variable SEARCH_URL n'est pas définie.", file=sys.stderr)
        return 2

    state_file = os.environ.get("STATE_FILE", "state.json")

    listings_by_id = {}
    for url in urls:
        try:
            html = fetch(url)
        except Exception as exc:  # réseau / HTTP : on n'écrase pas l'état, on retente au prochain run
            print(f"ERREUR de récupération ({zone_label(url)}) : {exc}", file=sys.stderr)
            return 1
        count, listings = parse(html)
        print(f"{zone_label(url)} — compteur du site : {count} | annonces parsées : {len(listings)}")
        for l in listings:
            listings_by_id[l["id"]] = l
    listings = list(listings_by_id.values())

    seen = load_state(state_file)
    current_ids = {l["id"] for l in listings}
    new_listings = [l for l in listings if l["id"] not in seen]

    for l in new_listings:
        print(f"  NOUVEAU  {l['title']} — {l['price']} — {l['url']}")

    # L'état devient la liste actuelle : une annonce qui disparaît puis revient re-déclenche.
    save_state(state_file, current_ids)

    if new_listings:
        with open("notification.html", "w", encoding="utf-8") as f:
            f.write(build_html(new_listings, urls))
        set_output("has_new", "true")
        set_output("count", str(len(new_listings)))
        set_output("subject", f"🏠 {len(new_listings)} logement(s) CROUS dispo !")
    else:
        set_output("has_new", "false")
        print("Aucune nouvelle annonce.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
