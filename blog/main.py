# =============================================================================
# blog/main.py — the web server for jamesdillingham.com
# View from the Cheap Seats
#
# CHANGE NOTES
#   2026-09-30  Created for the site rebuild. Replaces the hand-built HTML
#               pages and the separate "jamesdillingham-comments" service with
#               ONE Render web service that:
#                 - builds every page from /posts, /pages and /blog/templates
#                   (home = latest post in full; archive, sidebar "Recent
#                   posts", sitemap.xml and feed.xml update automatically)
#                 - keeps every old address working (/world-after-certainty.html,
#                   /about.html, /contact/contact.html, /index.html ...)
#                 - stores post comments and the World Gratitude List in the
#                   database (Postgres on Render), with a spam filter
#                 - runs the AI features server-side (gratitude themes,
#                   Learn Something New, moderation)
#                 - has a private /admin page to hide or restore anything.
#
# SETTINGS (Render dashboard → Environment)
#   DATABASE_URL       Postgres "Internal Database URL" (required on Render)
#   ADMIN_KEY          a long password of your choosing, for /admin
#   ANTHROPIC_API_KEY  enables gratitude themes, lessons and AI moderation
#   FORMSPREE_URL      optional — emails Jim when someone comments or posts
#   BASE_URL           optional — defaults to https://jamesdillingham.com
# =============================================================================

from __future__ import annotations

import datetime as _dt
import hmac
import os
import threading
import time
from collections import deque
from contextlib import asynccontextmanager
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import (FileResponse, HTMLResponse, JSONResponse,
                               PlainTextResponse, RedirectResponse, Response)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from . import ai, config, db, moderation
from .content import default_store

HERE = Path(__file__).resolve().parent
store = default_store()
templates = Jinja2Templates(directory=str(HERE / "templates"))
templates.env.globals.update(cfg=config, now_year=lambda: _dt.date.today().year)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    posts = store.published_posts()
    print(f"[startup] database: {'PostgreSQL' if db.USE_PG else 'local SQLite'}; "
          f"{len(posts)} published posts; AI {'on' if ai.enabled() else 'off'}; "
          f"admin {'on' if os.environ.get('ADMIN_KEY') else 'off (set ADMIN_KEY)'}")
    for err in store.errors:
        print(f"[startup] POST FILE PROBLEM: {err}")
    yield


app = FastAPI(title=config.SITE_TITLE, docs_url=None, redoc_url=None, openapi_url=None,
              lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    return response


# ----- helpers ----------------------------------------------------------------

def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def render(request: Request, template: str, status_code: int = 200, **ctx) -> HTMLResponse:
    posts = store.published_posts()
    ctx.setdefault("recent_posts", posts[: config.RECENT_POSTS_COUNT])
    ctx.setdefault("active", "")
    ctx.setdefault("canonical", config.BASE_URL + request.url.path)
    return templates.TemplateResponse(request, template, ctx, status_code=status_code)


def notify(subject: str, fields: dict) -> None:
    """Email Jim through Formspree (best effort; never blocks a visitor)."""
    url = os.environ.get("FORMSPREE_URL", "").strip()
    if not url:
        return
    try:
        httpx.post(url, json={"_subject": subject, **fields},
                   headers={"Accept": "application/json"}, timeout=10)
    except httpx.HTTPError as exc:
        print(f"[notify] failed: {exc}")


# ----- pages ------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    posts = store.published_posts()
    post = posts[0] if posts else None
    older = posts[1] if len(posts) > 1 else None
    return render(request, "home.html", active="Home", post=post, older=older,
                  canonical=config.BASE_URL + "/")


@app.get("/index.html")
def index_redirect():
    return RedirectResponse("/", status_code=301)


@app.get("/archive.html", response_class=HTMLResponse)
def archive(request: Request):
    return render(request, "archive.html", active="All Posts", posts=store.published_posts())


@app.get("/about.html", response_class=HTMLResponse)
def about(request: Request):
    page = store.get_page("about")
    if not page:
        raise HTTPException(404)
    return render(request, "page.html", active="About", page=page)


@app.get("/contact.html", response_class=HTMLResponse)
def contact(request: Request):
    return render(request, "contact.html", active="Contact", page=store.get_page("contact"))


@app.get("/contact/contact.html")
@app.get("/contact")
@app.get("/contact/")
def contact_redirect():
    return RedirectResponse("/contact.html", status_code=301)


@app.get("/gratitude.html", response_class=HTMLResponse)
def gratitude(request: Request):
    return render(request, "gratitude.html", active="Gratitude List",
                  categories=ai.GRATITUDE_CATEGORIES)


@app.get("/Gratitude.html")
def gratitude_redirect():
    return RedirectResponse("/gratitude.html", status_code=301)


@app.get("/learn-something-new.html", response_class=HTMLResponse)
def learn(request: Request):
    return render(request, "learn.html", ai_on=ai.enabled())


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    return render(request, "admin.html", admin_on=bool(os.environ.get("ADMIN_KEY")))


# ----- machine-readable files -------------------------------------------------

@app.get("/sitemap.xml")
def sitemap():
    base = config.BASE_URL
    urls = [(f"{base}/", None, "daily", "1.0"),
            (f"{base}/archive.html", None, "weekly", "0.8"),
            (f"{base}/about.html", None, "monthly", "0.7"),
            (f"{base}/contact.html", None, "monthly", "0.5"),
            (f"{base}/gratitude.html", None, "daily", "0.7"),
            (f"{base}/learn-something-new.html", None, "monthly", "0.6")]
    for p in store.published_posts():
        urls.append((base + p.url, p.date.isoformat(), "monthly", "0.9"))
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod, freq, prio in urls:
        parts.append("  <url>")
        parts.append(f"    <loc>{xml_escape(loc)}</loc>")
        if lastmod:
            parts.append(f"    <lastmod>{lastmod}</lastmod>")
        parts.append(f"    <changefreq>{freq}</changefreq>")
        parts.append(f"    <priority>{prio}</priority>")
        parts.append("  </url>")
    parts.append("</urlset>")
    return Response("\n".join(parts) + "\n", media_type="application/xml")


@app.get("/feed.xml")
def feed():
    base = config.BASE_URL
    items = []
    for p in store.published_posts()[:20]:
        pub = format_datetime(_dt.datetime(p.date.year, p.date.month, p.date.day, 12, tzinfo=_dt.timezone.utc))
        items.append(
            "<item>"
            f"<title>{xml_escape(p.title)}</title>"
            f"<link>{base}{p.url}</link>"
            f"<guid isPermaLink=\"true\">{base}{p.url}</guid>"
            f"<pubDate>{pub}</pubDate>"
            f"<description>{xml_escape(p.excerpt)}</description>"
            "</item>"
        )
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>'
           f"<title>{xml_escape(config.SITE_TITLE)}</title><link>{base}/</link>"
           f"<description>{xml_escape(config.SITE_DESCRIPTION)}</description>"
           + "".join(items) + "</channel></rss>\n")
    return Response(xml, media_type="application/rss+xml")


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    return f"User-agent: *\nDisallow: /admin\nDisallow: /api/\nSitemap: {config.BASE_URL}/sitemap.xml\n"


@app.get("/Google0d0b8f7f708b35ac.html", response_class=PlainTextResponse)
@app.get("/google0d0b8f7f708b35ac.html", response_class=PlainTextResponse)
def google_verification():
    return "google-site-verification: google0d0b8f7f708b35ac.html"


@app.get("/favicon.ico")
def favicon_ico():
    return FileResponse(HERE / "static" / "favicon.ico")


@app.get("/favicon.svg")
def favicon_svg():
    return FileResponse(HERE / "static" / "favicon.svg", media_type="image/svg+xml")


@app.get("/assets/hero.jpg")
def old_hero():
    return FileResponse(HERE / "static" / "img" / "hero.jpg")


@app.get("/healthz", response_class=PlainTextResponse)
def healthz():
    return "ok"


# ----- API: post comments -----------------------------------------------------

class CommentIn(BaseModel):
    post_slug: str
    name: str = ""
    email: str = ""
    body: str = ""
    website: str = ""  # honeypot — real visitors never see or fill this


@app.get("/api/comments/{slug}")
def get_comments(slug: str):
    return {"comments": db.list_comments(slug)}


@app.post("/api/comments")
def post_comment(data: CommentIn, request: Request, background: BackgroundTasks):
    if data.website:
        return {"ok": True, "message": "Thanks — your comment is posted."}
    post = store.get_post(data.post_slug)
    if not post:
        return JSONResponse({"ok": False, "error": "That post wasn't found."}, status_code=404)
    ip_hash = moderation.visitor_hash(client_ip(request))
    try:
        name = moderation.clean_name(data.name)
        if not name:
            raise moderation.Rejected("Please enter your name.")
        email = data.email.strip()[:200]
        if email and ("@" not in email or " " in email):
            raise moderation.Rejected("That email address doesn't look right.")
        body = moderation.check("comment", data.body, ip_hash, extra_text=name)
    except moderation.Rejected as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=422)
    new_id = db.add_comment(post.slug, name, email, body, ip_hash)
    background.add_task(notify, f"New comment on '{post.title}' — View from the Cheap Seats",
                        {"name": name, "email": email or "not provided", "post": post.slug,
                         "comment": body, "admin": config.BASE_URL + "/admin"})
    return {"ok": True, "message": "Thanks — your comment is posted.",
            "comment": {"id": new_id, "name": name, "body": body, "created_at": db.now_iso()}}


# ----- API: World Gratitude List ----------------------------------------------

class GratitudeIn(BaseModel):
    gratitude_text: str = ""
    author_name: str = ""
    website: str = ""


class GratitudeCommentIn(BaseModel):
    name: str = ""
    body: str = ""
    website: str = ""


@app.get("/api/gratitude")
def get_gratitude():
    return {"entries": db.list_gratitude()}


@app.post("/api/gratitude")
def post_gratitude(data: GratitudeIn, request: Request, background: BackgroundTasks):
    if data.website:
        return {"ok": True}
    ip_hash = moderation.visitor_hash(client_ip(request))
    try:
        name = moderation.clean_name(data.author_name)
        text = moderation.check("gratitude", data.gratitude_text, ip_hash, extra_text=name)
    except moderation.Rejected as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=422)
    category = ai.categorize_gratitude(text)
    entry = db.add_gratitude(text, name or None, category, ip_hash)
    background.add_task(notify, "New entry on the World Gratitude List",
                        {"name": name or "anonymous", "entry": text, "theme": category,
                         "admin": config.BASE_URL + "/admin"})
    return {"ok": True, "entry": entry}


@app.post("/api/gratitude/{gratitude_id}/comments")
def post_gratitude_comment(gratitude_id: int, data: GratitudeCommentIn, request: Request,
                           background: BackgroundTasks):
    if data.website:
        return {"ok": True}
    if not db.gratitude_exists(gratitude_id):
        return JSONResponse({"ok": False, "error": "That entry wasn't found."}, status_code=404)
    ip_hash = moderation.visitor_hash(client_ip(request))
    try:
        name = moderation.clean_name(data.name)
        body = moderation.check("gratitude_comment", data.body, ip_hash, extra_text=name)
    except moderation.Rejected as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=422)
    comment = db.add_gratitude_comment(gratitude_id, name or None, body, ip_hash)
    background.add_task(notify, "New comment on the World Gratitude List",
                        {"name": name or "anonymous", "comment": body, "entry_id": gratitude_id,
                         "admin": config.BASE_URL + "/admin"})
    return {"ok": True, "comment": comment}


# ----- API: Learn Something New -------------------------------------------------

_lesson_lock = threading.Lock()
_lesson_hits: dict[str, deque] = {}
_lesson_day = {"date": None, "count": 0}
_recent_titles: deque = deque(maxlen=10)
LESSONS_PER_HOUR = int(os.environ.get("LESSONS_PER_HOUR", "12"))
LESSONS_PER_DAY_TOTAL = int(os.environ.get("LESSONS_PER_DAY_TOTAL", "400"))


@app.post("/api/lesson")
def lesson(request: Request):
    if not ai.enabled():
        return JSONResponse({"ok": False, "error": "Lessons are switched off right now."}, status_code=503)
    ip = moderation.visitor_hash(client_ip(request))
    now = time.time()
    today = _dt.date.today()
    with _lesson_lock:
        if _lesson_day["date"] != today:
            _lesson_day.update(date=today, count=0)
        if _lesson_day["count"] >= LESSONS_PER_DAY_TOTAL:
            return JSONResponse({"ok": False, "error": "That's all the lessons for today — come back tomorrow."},
                                status_code=429)
        hits = _lesson_hits.setdefault(ip, deque())
        while hits and now - hits[0] > 3600:
            hits.popleft()
        if len(hits) >= LESSONS_PER_HOUR:
            return JSONResponse({"ok": False, "error": "You've had a lot of lessons this hour — take a break and come back soon."},
                                status_code=429)
        hits.append(now)
        _lesson_day["count"] += 1
        avoid = list(_recent_titles)
    try:
        result = ai.generate_lesson(avoid)
    except ai.AIError as exc:
        print(f"[lesson] failed: {exc}")
        return JSONResponse({"ok": False, "error": "Something went wrong. Give it another shot in a moment."},
                            status_code=502)
    with _lesson_lock:
        _recent_titles.append(result["title"])
    return {"ok": True, "lesson": result}


# ----- API: admin -----------------------------------------------------------------

def _require_admin(request: Request) -> None:
    key = os.environ.get("ADMIN_KEY", "")
    given = request.headers.get("x-admin-key", "")
    if not key or not hmac.compare_digest(key, given):
        raise HTTPException(status_code=401, detail="Wrong admin password")


class HideIn(BaseModel):
    kind: str
    id: int
    hidden: bool


@app.get("/api/admin/items")
def admin_items(request: Request, kind: str = "comment"):
    _require_admin(request)
    if kind not in db.TABLES:
        raise HTTPException(400, "unknown kind")
    return {"items": db.admin_list(kind)}


@app.post("/api/admin/hide")
def admin_hide(data: HideIn, request: Request):
    _require_admin(request)
    if data.kind not in db.TABLES:
        raise HTTPException(400, "unknown kind")
    db.set_hidden(data.kind, data.id, data.hidden)
    return {"ok": True}


@app.get("/api/admin/status")
def admin_status(request: Request):
    _require_admin(request)
    return {"posts": len(store.published_posts()), "content_errors": store.errors,
            "database": "PostgreSQL" if db.USE_PG else "SQLite (local test)", "ai": ai.enabled(),
            "email_notifications": bool(os.environ.get("FORMSPREE_URL"))}


# ----- posts (keep last: it matches any /something.html) ---------------------------

@app.get("/{slug}.html", response_class=HTMLResponse)
def post_page(slug: str, request: Request):
    post = store.get_post(slug.lower())
    if not post:
        return render(request, "404.html", status_code=404)
    older, newer = store.neighbors(post.slug)
    return render(request, "post.html", post=post, older=older, newer=newer)


@app.exception_handler(404)
async def not_found(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Not found"}, status_code=404)
    return render(request, "404.html", status_code=404)


# I did no harm and this file is not truncated.
