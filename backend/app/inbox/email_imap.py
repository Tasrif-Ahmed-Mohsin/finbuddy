"""Read bank-alert emails over IMAP, READ-ONLY.

  * The mailbox is opened with readonly=True and messages are fetched with BODY.PEEK, so nothing is
    marked as read, moved or deleted.
  * Credentials come only from environment variables (SATHI_IMAP_HOST / _USER / _PASSWORD); with
    Gmail this must be an app password, never the account password.
  * Every email still goes through the same filter → redaction → scan pipeline as SMS.
"""
from __future__ import annotations

import email
import imaplib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.header import decode_header, make_header
from email.utils import parseaddr, parsedate_to_datetime


@dataclass
class RawEmail:
    sender: str
    subject: str
    received_at: datetime | None
    text: str


def _strip_html(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def parse_email_bytes(raw: bytes) -> RawEmail:
    msg = email.message_from_bytes(raw)
    subject = str(make_header(decode_header(msg.get("Subject", ""))))
    sender = parseaddr(msg.get("From", ""))[1] or msg.get("From", "")
    try:
        received = parsedate_to_datetime(msg.get("Date")) if msg.get("Date") else None
    except (TypeError, ValueError):
        received = None
    plain, html = None, None
    for part in msg.walk() if msg.is_multipart() else [msg]:
        if part.get_content_maintype() == "multipart" or part.get("Content-Disposition", "").startswith("attachment"):
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        body = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        if part.get_content_type() == "text/plain" and plain is None:
            plain = body
        elif part.get_content_type() == "text/html" and html is None:
            html = body
    text = (plain or (_strip_html(html) if html else "")).strip()
    return RawEmail(sender, subject, received, f"{subject}\n{text}"[:5000])


def fetch_recent(host: str, user: str, password: str, since_days: int = 7, limit: int = 50) -> list[RawEmail]:
    since = (datetime.now() - timedelta(days=since_days)).strftime("%d-%b-%Y")
    conn = imaplib.IMAP4_SSL(host)
    try:
        conn.login(user, password)
        conn.select("INBOX", readonly=True)
        status, data = conn.search(None, "SINCE", since)
        if status != "OK":
            return []
        ids = data[0].split()[-limit:]
        out = []
        for i in ids:
            status, parts = conn.fetch(i, "(BODY.PEEK[])")
            if status == "OK" and parts and isinstance(parts[0], tuple):
                out.append(parse_email_bytes(parts[0][1]))
        return out
    finally:
        try:
            conn.logout()
        except Exception:
            pass
