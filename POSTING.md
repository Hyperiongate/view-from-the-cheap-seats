# How to publish a post — View from the Cheap Seats

_Last updated 2026-09-30 (site rebuild; comments and Gratitude List switched off)._

## The short version

1. Give Claude your post (paste it, dictate it, or attach a Word doc) in a Cowork session with the **view-from-the-cheap-seats** folder connected.
2. Claude writes **one file** into the `posts` folder.
3. Open **GitHub Desktop**, look over the change, then click **Commit to main** and **Push origin**.
4. Render rebuilds the site. A minute or two later the post is on the home page. The archive, the "Recent Posts" sidebar, the sitemap and the RSS feed update themselves.

That's the whole process. You never touch the home page, archive or sitemap again.

## What a post file looks like (for Claude)

The file goes in `posts/`. Its name is the web address: `posts/super-ai-short-term.md` becomes `jamesdillingham.com/super-ai-short-term.html`. Use lowercase letters, numbers and dashes only.

```
---
title: Super AI — What Does It Look Like in the Short Term?
date: 2026-10-01
tag: Technology & Society
excerpt: One or two sentences for the archive page and link previews.
image: https://images.unsplash.com/photo-XXXXXXXX?w=1200&h=630&fit=crop&q=80&auto=format
image_alt: Short description of the photo
image_credit: Photographer Name on Unsplash
image_credit_url: https://unsplash.com/@username?utm_source=jamesdillingham&utm_medium=referral
---
The post itself, written in Markdown.

A blank line starts a new paragraph. **Bold**, *italic*, and

> a pull quote (gets the red left border)

## A subheading
```

Rules:

- **Required:** `title` and `date` (written as `YYYY-MM-DD`). Everything else is optional.
- **Tags used so far:** Political Analysis, Technology & Society.
- **Future dates:** a post dated in the future stays hidden until that day (Pacific time). This lets you schedule posts.
- **Drafts:** add `draft: yes` to keep a post off the site.
- **AI review note:** the "reviewed by the Swarm AI panel" box shows by default. Add `ai_reviewed: no` to hide it.
- **Photos:** use free Unsplash photos only, and always credit them. Check the photo ID and the photographer on Unsplash itself before using one.
- **Older posts:** the three posts from April are `.html` files, carried over word for word from the old site. New posts should be `.md` (Markdown).
- **Mistakes in a file:** if a file has an error (for example, a missing date), the rest of the site keeps working. Claude checks for problems like this before you push.

## Comments and the Gratitude List

Both are switched off for now, so there's nothing to moderate. Readers reach you through the Contact page (jim@shift-work.com). To bring either back, see the end of `DEPLOY.md`.

## Where things live

| What | Where |
|---|---|
| Posts | `posts/` |
| About page text | `pages/about.html` |
| Site name, tagline, nav, sidebar links, contact email, on/off switches | `blog/config.py` |
| Page layouts | `blog/templates/` |
| Styles, scripts, images | `blog/static/` |
| Web server | `blog/main.py` |
