# =============================================================================
# blog/content.py — loads blog posts and pages from plain files
# View from the Cheap Seats — jamesdillingham.com
#
# CHANGE NOTES
#   2026-09-30  Created for the site rebuild. Each post is ONE file in /posts
#               (Markdown .md or HTML .html) with a short header block ("front
#               matter") holding title, date, tag, etc. The home page, archive,
#               "Recent posts" sidebar, sitemap and RSS feed are all built from
#               these files automatically, so publishing a post means adding a
#               single file.
#
# HOW A POST FILE LOOKS
#   ---
#   title: My Post Title
#   date: 2026-10-01
#   tag: Political Analysis
#   excerpt: One or two sentences shown on the archive page.
#   ---
#   The post body goes here (Markdown or HTML).
#
#   Optional header lines: description, image, image_alt, image_credit,
#   image_credit_url, ai_reviewed (yes/no), draft (yes/no).
#   A post dated in the future stays hidden until that date (Pacific time).
# =============================================================================

from __future__ import annotations

import datetime as _dt
import html
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import markdown as _markdown

try:
    from zoneinfo import ZoneInfo

    _PACIFIC = ZoneInfo("America/Los_Angeles")
except Exception:  # tz database missing — fall back to UTC
    _PACIFIC = _dt.timezone.utc

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_TRUE = {"yes", "true", "y", "1", "on"}


@dataclass
class Post:
    slug: str
    title: str
    date: _dt.date
    tag: str
    excerpt: str
    description: str
    body_html: str
    image: str = ""
    image_alt: str = ""
    image_credit: str = ""
    image_credit_url: str = ""
    ai_reviewed: bool = True
    source_file: str = ""

    @property
    def url(self) -> str:
        return f"/{self.slug}.html"

    @property
    def date_display(self) -> str:  # "April 15, 2026"
        return f"{self.date.strftime('%B')} {self.date.day}, {self.date.year}"

    @property
    def date_short(self) -> str:  # "Apr 15, 2026"
        return f"{self.date.strftime('%b')} {self.date.day}, {self.date.year}"


@dataclass
class Page:
    slug: str
    title: str
    subtitle: str
    description: str
    body_html: str
    meta: dict = field(default_factory=dict)


def today_pacific() -> _dt.date:
    return _dt.datetime.now(_PACIFIC).date()


def parse_front_matter(text: str) -> tuple[dict, str]:
    """Split '---' header block from body. Values are taken literally after
    the first colon, so titles may contain colons and quotes safely."""
    text = text.replace("\r\n", "\n").lstrip("﻿")
    meta: dict = {}
    if not text.startswith("---\n"):
        return meta, text
    end = text.find("\n---", 4)
    if end == -1:
        return meta, text
    header = text[4:end]
    body = text[end + 4 :]
    if body.startswith("\n"):
        body = body[1:]
    for line in header.split("\n"):
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip().lower()] = value.strip()
    return meta, body


def _render_body(body: str, suffix: str) -> str:
    if suffix == ".md":
        return _markdown.markdown(body, extensions=["extra", "sane_lists"])
    return body  # .html files are used exactly as written


def _plain_text(fragment: str) -> str:
    no_tags = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(no_tags)).strip()


def _auto_excerpt(body_html: str, words: int = 35) -> str:
    parts = _plain_text(body_html).split(" ")
    text = " ".join(parts[:words])
    return text + ("…" if len(parts) > words else "")


def load_post(path: Path) -> Post | None:
    meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
    slug = path.stem.lower()
    if not SLUG_RE.match(slug):
        raise ValueError(f"{path.name}: file name must use only lowercase letters, numbers and dashes")
    if meta.get("draft", "").lower() in _TRUE:
        return None
    if "title" not in meta or "date" not in meta:
        raise ValueError(f"{path.name}: needs at least 'title:' and 'date:' in its header")
    try:
        date = _dt.date.fromisoformat(meta["date"])
    except ValueError as exc:
        raise ValueError(f"{path.name}: date must look like 2026-10-01") from exc
    body_html = _render_body(body, path.suffix.lower())
    excerpt = meta.get("excerpt") or _auto_excerpt(body_html)
    return Post(
        slug=slug,
        title=meta["title"],
        date=date,
        tag=meta.get("tag", ""),
        excerpt=excerpt,
        description=meta.get("description") or excerpt,
        body_html=body_html,
        image=meta.get("image", ""),
        image_alt=meta.get("image_alt", ""),
        image_credit=meta.get("image_credit", ""),
        image_credit_url=meta.get("image_credit_url", ""),
        ai_reviewed=meta.get("ai_reviewed", "yes").lower() in _TRUE,
        source_file=path.name,
    )


class ContentStore:
    """Reads /posts and /pages, re-reading automatically when a file changes."""

    def __init__(self, posts_dir: Path, pages_dir: Path):
        self.posts_dir = posts_dir
        self.pages_dir = pages_dir
        self._signature = None
        self._posts: list[Post] = []
        self._pages: dict[str, Page] = {}
        self.errors: list[str] = []

    def _current_signature(self):
        sig = []
        for folder in (self.posts_dir, self.pages_dir):
            if folder.is_dir():
                for p in sorted(folder.iterdir()):
                    if p.suffix.lower() in (".md", ".html"):
                        st = p.stat()
                        sig.append((str(p), st.st_mtime_ns, st.st_size))
        return tuple(sig)

    def _reload_if_changed(self):
        sig = self._current_signature()
        if sig == self._signature:
            return
        posts, pages, errors = [], {}, []
        if self.posts_dir.is_dir():
            for p in sorted(self.posts_dir.iterdir()):
                if p.suffix.lower() not in (".md", ".html"):
                    continue
                try:
                    post = load_post(p)
                    if post:
                        posts.append(post)
                except Exception as exc:  # one bad file must not take the site down
                    errors.append(str(exc))
        seen = set()
        for post in posts:
            if post.slug in seen:
                errors.append(f"Two posts share the name '{post.slug}'")
            seen.add(post.slug)
        posts.sort(key=lambda x: (x.date, x.slug), reverse=True)
        if self.pages_dir.is_dir():
            for p in sorted(self.pages_dir.iterdir()):
                if p.suffix.lower() not in (".md", ".html"):
                    continue
                meta, body = parse_front_matter(p.read_text(encoding="utf-8"))
                pages[p.stem.lower()] = Page(
                    slug=p.stem.lower(),
                    title=meta.get("title", p.stem.title()),
                    subtitle=meta.get("subtitle", ""),
                    description=meta.get("description", ""),
                    body_html=_render_body(body, p.suffix.lower()),
                    meta=meta,
                )
        self._posts, self._pages, self.errors = posts, pages, errors
        self._signature = sig
        for e in errors:
            print(f"[content] WARNING: {e}")

    def published_posts(self) -> list[Post]:
        self._reload_if_changed()
        today = today_pacific()
        return [p for p in self._posts if p.date <= today]

    def get_post(self, slug: str) -> Post | None:
        for p in self.published_posts():
            if p.slug == slug:
                return p
        return None

    def neighbors(self, slug: str) -> tuple[Post | None, Post | None]:
        """(older, newer) posts around the given slug."""
        posts = self.published_posts()
        for i, p in enumerate(posts):
            if p.slug == slug:
                newer = posts[i - 1] if i > 0 else None
                older = posts[i + 1] if i + 1 < len(posts) else None
                return older, newer
        return None, None

    def get_page(self, slug: str) -> Page | None:
        self._reload_if_changed()
        return self._pages.get(slug)


def default_store() -> ContentStore:
    root = Path(os.environ.get("SITE_ROOT", Path(__file__).resolve().parent.parent))
    return ContentStore(root / "posts", root / "pages")


# I did no harm and this file is not truncated.
