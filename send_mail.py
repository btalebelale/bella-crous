#!/usr/bin/env python3
"""Envoi des alertes par email, un message séparé par destinataire.

Chaque destinataire reçoit son propre message : il ne voit pas les adresses des
autres, et un envoi qui échoue n'empêche pas les suivants.

Aucune dépendance externe : uniquement la bibliothèque standard Python.

Variables d'environnement :
  MAIL_USERNAME   compte Gmail expéditeur (obligatoire)
  MAIL_PASSWORD   mot de passe d'application Gmail (obligatoire)
  MAIL_TO         destinataires, séparés par des virgules, points-virgules,
                  espaces ou retours à la ligne (obligatoire)
  MAIL_TO_EXTRA   destinataires supplémentaires, même format (facultatif) ;
                  fusionnés avec MAIL_TO, les doublons sont ignorés
  MAIL_SUBJECT    objet du message (défaut : "Veille CROUS")
  MAIL_HTML_FILE  fichier contenant le corps HTML
  MAIL_HTML       corps HTML en clair (utilisé si MAIL_HTML_FILE est absent)
  MAIL_FROM_NAME  nom affiché de l'expéditeur (défaut : "Veille CROUS")
  SMTP_SERVER     serveur SMTP (défaut : smtp.gmail.com)
  SMTP_PORT       port SMTP SSL (défaut : 465)
"""

import os
import re
import smtplib
import sys
from email.message import EmailMessage
from email.utils import formataddr

SPLIT_RE = re.compile(r"[,;\s]+")


def recipients(raw: str):
    """Liste dédoublonnée des destinataires, dans l'ordre d'apparition."""
    seen, out = set(), []
    for addr in SPLIT_RE.split(raw.strip()):
        if addr and addr.lower() not in seen:
            seen.add(addr.lower())
            out.append(addr)
    return out


def build_message(sender: str, from_name: str, to: str, subject: str, html: str):
    msg = EmailMessage()
    msg["From"] = formataddr((from_name, sender))
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(
        "Ce message contient une version HTML. Ouvre-le dans un client mail compatible."
    )
    msg.add_alternative(html, subtype="html")
    return msg


def main() -> int:
    sender = os.environ.get("MAIL_USERNAME", "").strip()
    password = os.environ.get("MAIL_PASSWORD", "")
    raw_to = " ".join(
        v for v in (os.environ.get("MAIL_TO", ""), os.environ.get("MAIL_TO_EXTRA", "")) if v
    )

    missing = [
        name
        for name, value in (
            ("MAIL_USERNAME", sender),
            ("MAIL_PASSWORD", password),
            ("MAIL_TO / MAIL_TO_EXTRA", raw_to.strip()),
        )
        if not value
    ]
    if missing:
        print(f"ERREUR : variable(s) manquante(s) : {', '.join(missing)}", file=sys.stderr)
        return 2

    to_list = recipients(raw_to)
    if not to_list:
        print("ERREUR : aucun destinataire valide dans MAIL_TO.", file=sys.stderr)
        return 2

    html_file = os.environ.get("MAIL_HTML_FILE", "")
    if html_file:
        with open(html_file, encoding="utf-8") as f:
            html = f.read()
    else:
        html = os.environ.get("MAIL_HTML", "")
    if not html.strip():
        print("ERREUR : corps HTML vide (MAIL_HTML_FILE ou MAIL_HTML).", file=sys.stderr)
        return 2

    subject = os.environ.get("MAIL_SUBJECT", "Veille CROUS")
    from_name = os.environ.get("MAIL_FROM_NAME", "Veille CROUS")
    server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "465"))

    failures = []
    with smtplib.SMTP_SSL(server, port, timeout=30) as smtp:
        smtp.login(sender, password)
        for to in to_list:
            try:
                smtp.send_message(build_message(sender, from_name, to, subject, html))
                print(f"  envoyé  {to}")
            except Exception as exc:  # un destinataire KO ne bloque pas les autres
                print(f"  ÉCHEC   {to} : {exc}", file=sys.stderr)
                failures.append(to)

    print(f"{len(to_list) - len(failures)}/{len(to_list)} message(s) envoyé(s) séparément.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
