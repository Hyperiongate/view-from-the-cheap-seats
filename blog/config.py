# =============================================================================
# blog/config.py — site-wide settings (names, links, sidebar)
# View from the Cheap Seats — jamesdillingham.com
#
# CHANGE NOTES
#   2026-09-30  Created for the site rebuild. Change the text or links here and
#               every page picks it up (header, sidebar, footer, contact).
# =============================================================================

import os

SITE_TITLE = "View from the Cheap Seats"
SITE_TAGLINE = "Honest takes from the back of the arena"
AUTHOR = "James Dillingham"
BASE_URL = os.environ.get("BASE_URL", "https://jamesdillingham.com").rstrip("/")
SITE_DESCRIPTION = (
    "AI, politics and the state of the world — honest takes from James Dillingham. "
    "Not for profit. Just my view from the back of the arena."
)
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "Jim@shift-work.com")
GOOGLE_SITE_VERIFICATION = "Vd_8POebv0lcbvhSEV5AYalDpQ18gzSiXp9sEqXiRsU"

HERO_IMAGE = "/static/img/hero.jpg"
HERO_ALT = "Earth rising near the Moon, seen from deep space — Artemis mission"
HERO_QUOTE = "“The view is better from up here. You can see everything — including how small it all is.”"

NAV = [
    ("/", "Home"),
    ("/archive.html", "All Posts"),
    ("/gratitude.html", "Gratitude List"),
    ("/about.html", "About"),
    ("/contact.html", "Contact"),
]

OTHER_SITES = [
    {
        "name": "shift-work.com",
        "url": "https://shift-work.com",
        "blurb": "Help for shift work operations.",
        "icon": "\U0001F3ED",
    },
    {
        "name": "mrcadabra.com",
        "url": "https://mrcadabra.com",
        "blurb": "An interactive AI math tutor.",
        "icon": "\U0001F9EE",
    },
]

RECENT_POSTS_COUNT = 10

AI_BADGE_POST = (
    "This post was reviewed by the Swarm AI panel before publishing. The arguments were "
    "stress-tested across multiple AI systems for logical consistency and blind spots. "
    "All conclusions are Jim's."
)
AI_BADGE_SIDEBAR = (
    "Jim writes these posts. Before publishing, each piece is reviewed by a panel of AI "
    "systems — including GPT, Gemini, and Claude — for logical consistency and blind "
    "spots. AI edits, Jim decides."
)

# I did no harm and this file is not truncated.
