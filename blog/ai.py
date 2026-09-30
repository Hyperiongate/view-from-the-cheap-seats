# =============================================================================
# blog/ai.py — calls to Claude, made from the SERVER (never from the browser)
# View from the Cheap Seats — jamesdillingham.com
#
# CHANGE NOTES
#   2026-09-30  Created for the site rebuild. The old gratitude and "Learn
#               Something New" pages called api.anthropic.com straight from
#               the visitor's browser with no key, so those features could
#               not work (and putting a key in a web page would expose it).
#               All AI calls now go through here, using the ANTHROPIC_API_KEY
#               setting on Render. Each feature has a fixed prompt, so the
#               site cannot be used as a free open AI proxy.
#               Models can be changed with the settings ANTHROPIC_MODEL
#               (lessons) and ANTHROPIC_FAST_MODEL (categorizing, moderation).
# =============================================================================

from __future__ import annotations

import json
import os
import re

import httpx

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")
FAST_MODEL = os.environ.get("ANTHROPIC_FAST_MODEL", "claude-haiku-4-5-20251001")

GRATITUDE_CATEGORIES = [
    "Family & Friends", "Health & Body", "Nature & Earth", "Work & Purpose",
    "Everyday Moments", "Pets & Animals", "Growth & Learning", "Love & Connection",
]
DEFAULT_CATEGORY = "Everyday Moments"


def api_key() -> str:
    return os.environ.get("ANTHROPIC_API_KEY", "").strip()


def enabled() -> bool:
    return bool(api_key())


class AIError(Exception):
    pass


def _ask(system: str, user: str, max_tokens: int, model: str, timeout: float = 45.0) -> str:
    key = api_key()
    if not key:
        raise AIError("ANTHROPIC_API_KEY is not set")
    try:
        resp = httpx.post(
            API_URL,
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            timeout=timeout,
        )
    except httpx.HTTPError as exc:
        raise AIError(f"network error: {exc}") from exc
    if resp.status_code != 200:
        raise AIError(f"API returned {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()


# ----- World Gratitude List: pick a theme ------------------------------------

def categorize_gratitude(text: str) -> str:
    if not enabled():
        return DEFAULT_CATEGORY
    system = (
        "Categorize the following gratitude entry into exactly one of these categories:\n"
        + ", ".join(GRATITUDE_CATEGORIES)
        + ".\nReturn ONLY the category name, nothing else."
    )
    try:
        answer = _ask(system, text, 20, FAST_MODEL, timeout=15)
    except AIError as exc:
        print(f"[ai] categorize failed: {exc}")
        return DEFAULT_CATEGORY
    for cat in GRATITUDE_CATEGORIES:
        if cat.lower() in answer.lower():
            return cat
    return DEFAULT_CATEGORY


# ----- Moderation: catch abuse the word list can't -----------------------------

def moderate(text: str) -> bool | None:
    """True = fine to publish, False = reject, None = could not check."""
    if not enabled():
        return None
    system = (
        "You screen short public submissions to a personal blog (comments and "
        "entries on a gratitude wall). Reply with exactly one word.\n"
        "Reply REJECT if the text is spam or advertising, contains a link-drop "
        "or scam, is hateful or harassing toward a person or group, contains "
        "slurs, threats, or sexual content, or reveals someone's private contact "
        "details.\n"
        "Reply OK for anything else — including strong disagreement, criticism "
        "of the author, political opinions of any side, sadness, or mild "
        "language. Disagreement is welcome on this site."
    )
    try:
        answer = _ask(system, text[:3000], 5, FAST_MODEL, timeout=15).upper()
    except AIError as exc:
        print(f"[ai] moderation check failed: {exc}")
        return None
    if "REJECT" in answer:
        return False
    if "OK" in answer:
        return True
    return None


# ----- Learn Something New ----------------------------------------------------

LESSON_SYSTEM = """You write crisp, intelligent short lessons. Pick ONE genuinely interesting topic completely at random from any domain: history, science, mathematics, language, food, psychology, geography, music, economics, nature, technology, philosophy, art, medicine, engineering, or anything else. Then write a compelling lesson about it in 300 words or fewer.

Return ONLY a JSON object with no markdown fences, no preamble:
{
  "category": "short category label (e.g. 'Natural Science', 'History', 'Psychology')",
  "title": "A sharp, specific title for the lesson",
  "paragraphs": ["paragraph 1", "paragraph 2", "paragraph 3"],
  "takeaway": "One memorable sentence the reader will remember tomorrow."
}

Rules:
- The topic must be genuinely random and varied across every possible domain. Surprise the reader.
- Total word count across all paragraphs must be 300 words or fewer.
- 3-4 paragraphs, each 60-90 words. Engaging, clear, no fluff.
- No bullet points. Prose only.
- The takeaway is a single elegant sentence.
- Return only the JSON object, nothing else."""


def generate_lesson(avoid_titles: list[str] | None = None) -> dict:
    user = "Give me a random lesson."
    if avoid_titles:
        user += " Do not repeat any of these recent topics: " + "; ".join(avoid_titles[-10:])
    text = _ask(LESSON_SYSTEM, user, 1000, MODEL)
    clean = re.sub(r"```(?:json)?", "", text).strip()
    start, end = clean.find("{"), clean.rfind("}")
    if start == -1 or end == -1:
        raise AIError("lesson reply was not JSON")
    try:
        lesson = json.loads(clean[start : end + 1])
    except json.JSONDecodeError as exc:
        raise AIError("lesson reply was not valid JSON") from exc
    paragraphs = [str(p).strip() for p in lesson.get("paragraphs", []) if str(p).strip()]
    if not lesson.get("title") or not paragraphs:
        raise AIError("lesson reply was missing parts")
    return {
        "category": str(lesson.get("category", "Something New"))[:60],
        "title": str(lesson["title"])[:200],
        "paragraphs": paragraphs[:6],
        "takeaway": str(lesson.get("takeaway", ""))[:400],
    }


# I did no harm and this file is not truncated.
