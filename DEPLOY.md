# Putting the new site live on Render

_Written 2026-09-30 for the site rebuild._

The new site is a **Render Web Service** (a small Python server) plus a **Render PostgreSQL** database. The old site files are still in the repo and untouched, so pushing this change doesn't break whatever currently serves jamesdillingham.com. You switch over only when the new one is working.

## Step 1 — Push the code

In GitHub Desktop, review the changes, then **Commit to main** and **Push origin**.

## Step 2 — Create the database

In the Render dashboard, choose **New → PostgreSQL**.

- **Name:** `cheap-seats-db` (any name works)
- **Region:** pick one and use the same region for the web service in Step 3
- **Plan:** a paid plan. Render deletes free databases after 30 days, and the Gratitude List and comments live here.

Once it's created, copy its **Internal Database URL**.

## Step 3 — Create the web service

Choose **New → Web Service**, then connect the GitHub repo `Hyperiongate/view-from-the-cheap-seats`, branch `main`.

| Setting | Value |
|---|---|
| Runtime / Language | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn blog.main:app --host 0.0.0.0 --port $PORT` |
| Instance type | Starter or higher (free instances go to sleep after 15 minutes idle) |
| Health Check Path | `/healthz` |

Under **Environment**, add these settings:

| Name | Value |
|---|---|
| `DATABASE_URL` | the Internal Database URL from Step 2 |
| `ADMIN_KEY` | a long password you make up, used for `/admin` |
| `ANTHROPIC_API_KEY` | your key from console.anthropic.com. This turns on gratitude themes, Learn Something New and AI spam screening. |
| `FORMSPREE_URL` | `https://formspree.io/f/xzdypeyp` (the address the old site used). This emails you about new comments and gratitude entries. Optional. |

Click **Create Web Service** and wait for the log line that starts with `[startup] database: PostgreSQL; 3 published posts`.

## Step 4 — Test on the temporary address

Render gives the service an address like `https://something.onrender.com`. On that address, check:

- the home page, a post, All Posts, About, Contact
- posting a comment on a post
- adding an entry to the Gratitude List, then commenting on it
- Learn Something New
- `/admin`: log in and hide, then restore, your test comment

## Step 5 — Move the domain

1. In the service that serves jamesdillingham.com today, open **Settings → Custom Domains** and remove `jamesdillingham.com` and `www.jamesdillingham.com`.
2. In the new web service, add both domains under **Settings → Custom Domains**.
3. Render shows the DNS records it expects. If they differ from what your domain registrar has now, update them at the registrar. Render confirms once the domain is verified and its certificate is issued.

## Step 6 — Clean up (after a few good days)

Ask Claude to:

- remove the old files from the repo: the old `.html` pages at the top level, `css/`, `js/`, `assets/`, `contact/`, `post-template.html`, `sitemap.xml` and the old `render.yaml`. The new site builds all of these itself.
- decide what to do with the old **jamesdillingham-comments** service and its database. If any real comments or gratitude entries are in it, Claude can copy them into the new database first. Its code wasn't in this repo, so connect that project's folder if you have it.

Then suspend the old services in Render so they stop billing.
