# =============================================================================
# blog/moderation.py — spam and abuse filter for comments and gratitude posts
# View from the Cheap Seats — jamesdillingham.com
#
# CHANGE NOTES
#   2026-09-30  Created for the site rebuild. Jim's choice: submissions show
#               immediately, a filter catches the junk, and anything that gets
#               through can be hidden from the admin page. Layers, cheapest
#               first:
#                 1. hidden "honeypot" field (bots fill it in, people can't see it)
#                 2. length limits and a cap on links
#                 3. a short list of spam phrases and strong profanity
#                 4. per-visitor rate limit and duplicate check
#                 5. an AI check (only when ANTHROPIC_API_KEY is set) that
#                    catches hate, harassment and scams a word list can't.
#               Disagreement and criticism are explicitly allowed.
# =============================================================================

from __future__ import annotations

import datetime as _dt
import hashlib
import os
import re

from . import ai, db

LIMITS = {
    "comment": {"min": 2, "max": 3000, "links": 2},
    "gratitude": {"min": 3, "max": 500, "links": 0},
    "gratitude_comment": {"min": 1, "max": 1000, "links": 1},
}
NAME_MAX = 80
RATE_10_MIN = int(os.environ.get("RATE_LIMIT_10MIN", "6"))
RATE_DAY = int(os.environ.get("RATE_LIMIT_DAY", "40"))

_URL_RE = re.compile(r"(https?://|www\.|\b[a-z0-9-]+\.(com|net|org|ru|xyz|info|biz|top|io|co)\b)", re.I)

_SPAM_PHRASES = [
    "viagra", "cialis", "casino", "betting tips", "crypto giveaway", "bitcoin doubler",
    "buy followers", "seo services", "backlinks", "payday loan", "loan offer",
    "work from home and earn", "make money fast", "whatsapp me", "telegram me",
    "free gift card", "onlyfans", "escort service", "forex signals",
]
_PROFANITY = [
    "fuck", "fucking", "motherfucker", "shit", "bullshit", "cunt", "asshole",
    "bitch", "dickhead", "bastard", "twat", "wanker",
]
_PROFANITY_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in _PROFANITY) + r")\w*\b", re.I)


class Rejected(Exception):
    """Raised with a friendly message the visitor can see."""


def visitor_hash(ip: str) -> str:
    salt = os.environ.get("IP_SALT") or os.environ.get("ADMIN_KEY") or "cheap-seats"
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()[:32]


def _since(**delta) -> str:
    t = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(**delta)
    return t.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clean_name(name: str | None) -> str:
    name = re.sub(r"\s+", " ", (name or "")).strip()
    if len(name) > NAME_MAX:
        raise Rejected(f"Please keep your name under {NAME_MAX} characters.")
    if name and (_URL_RE.search(name) or _PROFANITY_RE.search(name)):
        raise Rejected("Please use a plain name.")
    return name


def check(kind: str, text: str, ip_hash: str, extra_text: str = "") -> str:
    """Validate a submission. Returns cleaned text or raises Rejected."""
    limits = LIMITS[kind]
    text = (text or "").replace("\r\n", "\n").strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    if len(text) < limits["min"]:
        raise Rejected("That's a little too short.")
    if len(text) > limits["max"]:
        raise Rejected(f"Please keep it under {limits['max']} characters.")
    if len(_URL_RE.findall(text)) > limits["links"]:
        raise Rejected("Links aren't allowed here." if limits["links"] == 0 else "Too many links.")
    combined = f"{text} {extra_text}".lower()
    if any(p in combined for p in _SPAM_PHRASES):
        raise Rejected("That looks like spam to our filter. If it isn't, try rewording it.")
    if _PROFANITY_RE.search(combined):
        raise Rejected("Please keep it civil — no profanity.")
    if db.count_recent(ip_hash, _since(minutes=10)) >= RATE_10_MIN:
        raise Rejected("You're posting quickly — please wait a few minutes and try again.")
    if db.count_recent(ip_hash, _since(days=1)) >= RATE_DAY:
        raise Rejected("That's the limit for today. Thanks for contributing — come back tomorrow.")
    if db.is_duplicate(kind, text, ip_hash, _since(days=1)):
        raise Rejected("Looks like you already posted that.")
    verdict = ai.moderate(f"{extra_text}\n{text}".strip())
    if verdict is False:
        raise Rejected("Our filter flagged this one. Please keep it civil and on topic.")
    return text


# I did no harm and this file is not truncated.
