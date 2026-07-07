from __future__ import annotations

import re


TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_'-]{1,}|[\u0600-\u06ff]{2,}", re.I)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?966|0)?5\d{8}(?!\d)")
ORDER_RE = re.compile(r"\b(?:order|طلب|ORD)[-_ ]?([A-Z0-9]{4,})\b", re.I)
PROFANITY_RE = re.compile(r"\b(fuck|fucking|shit|damn|angry|scam)\b", re.I)


def tokens(text: str) -> list[str]:
    return [match.group(0).casefold() for match in TOKEN_RE.finditer(text)]


def sanitize(text: str) -> tuple[str, dict]:
    findings = {"email": len(EMAIL_RE.findall(text)), "phone": len(PHONE_RE.findall(text))}
    clean = EMAIL_RE.sub("[EMAIL]", text)
    clean = PHONE_RE.sub("[PHONE]", clean)
    return clean, findings


def extract_entities(text: str) -> dict:
    orders = [match.group(1) for match in ORDER_RE.finditer(text)]
    return {"orders": orders, "has_contact": bool(EMAIL_RE.search(text) or PHONE_RE.search(text)), "is_angry": bool(PROFANITY_RE.search(text))}

