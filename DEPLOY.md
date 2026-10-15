# Putting the new site live on Render

_Written 2026-09-30 for the site rebuild. Updated the same day: comments and the Gratitude List are switched off, so **no database is needed**._

The new site is one **Render Web Service** (a small Python server). The old site files are still in the repo and untouched, so pushing this change doesn't break whatever currently serves jamesdillingham.com. You switch over only when the new one is working.

## Step 1 — Push the code

In GitHub Desktop, review the changes, then **Commit to main** and **Push origin**.

## Step 2 — Create the web service

In the Render dashboard, choose **New → Web Service**, then connect the GitHub repo `Hyperiongate/view-from-the-cheap-seats`, branch `main`.

| Setting | Value |
|---|---|
| Runtime / Language | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn blog.main:app --host 0.0.0.0 --port $PORT` |
| Instance type | Starter or higher (free instances go to sleep after 15 minutes idle, so the first visitor waits) |
| Health Check Path | `/healthz` |

Under **Environment**, add one setting:

| Name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | your key from console.anthropic.com. This powers Learn Something New. Without it, that page says lessons are taking a break. |

Click **Create Web Service** and wait for the deploy to finish.

## Step 3 — Test on the temporary address

Render gives the service an address like `https://something.onrender.com`. On that address, check the home page, each post, All Posts, About, Contact (the link should be jim@shift-work.com) and Learn Something New.

## Step 4 — Move the domain

1. In the service that serves jamesdillingham.com today, open **Settings → Custom Domains** and remove `jamesdillingham.com` and `www.jamesdillingham.com`.
2. In the new web service, add both domains under **Settings → Custom Domains**.
3. Render shows the DNS records it expects. If they differ from what your domain registrar has now, update them at the registrar. Render confirms once the domain is verified and its certificate is issued.

## Step 5 — Clean up (after a few good days)

Ask Claude to remove the old files from the repo: the old `.html` pages at the top level, `css/`, `js/`, `assets/`, `contact/`, `post-template.html`, `sitemap.xml` and the old `render.yaml`. The new site builds all of these itself.

Then suspend the old services in Render, including **jamesdillingham-comments** and its database, so they stop billing.

## Turning comments or the Gratitude List back on later

Both are built and tested, just switched off in `blog/config.py`. Ask Claude to turn them on. You'd then add a paid Render PostgreSQL database and set `DATABASE_URL` (plus `ADMIN_KEY` for the `/admin` page).
