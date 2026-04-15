/* ============================================
   View from the Cheap Seats — Site Components
   Shared header, nav, sidebar, footer
   ============================================ */

// ----- Inject favicon if not already present -----
(function() {
  if (!document.querySelector('link[rel="icon"]')) {
    const link = document.createElement('link');
    link.rel = 'icon';
    link.type = 'image/x-icon';
    link.href = 'favicon.ico';
    document.head.appendChild(link);
  }
})();

// ----- Inject shared header -----
function renderHeader(activePage) {
  const nav = [
    { href: 'index.html',   label: 'Home' },
    { href: 'archive.html', label: 'All Posts' },
    { href: 'about.html',   label: 'About' },
    { href: 'contact.html', label: 'Contact' },
  ];

  const navLinks = nav.map(n =>
    `<a href="${n.href}" class="${activePage === n.label ? 'active' : ''}">${n.label}</a>`
  ).join('');

  document.getElementById('site-header').innerHTML = `
    <div class="site-wrapper">
      <div class="site-title">
        View from the Cheap Seats
        <span>Honest takes from the back of the arena</span>
      </div>
      <nav class="site-nav">${navLinks}</nav>
    </div>
  `;
}

// ----- Inject shared sidebar -----
function renderSidebar() {
  document.getElementById('sidebar').innerHTML = `
    <!-- Subscribe widget -->
    <div class="sidebar-widget">
      <h4>Get New Posts</h4>
      <p>Subscribe to get notified when a new post goes up. No spam, no fluff.</p>
      <a href="https://jimdillingham.substack.com/subscribe" target="_blank" rel="noopener" class="btn btn-sm" style="display:block; text-align:center; margin-top:0.5rem;">Subscribe on Substack</a>
    </div>

    <!-- World Gratitude List widget -->
    <div class="sidebar-widget">
      <h4>World Gratitude List</h4>
      <p style="font-size:0.82rem; color:#1a1a1a; margin-bottom:0.75rem; line-height:1.6;">It's nearly impossible to be in a state of gratitude and a state of fear at the same time. Add yours.</p>
      <a href="gratitude.html" class="sidebar-link">
        <span class="icon">🙏</span>
        See what the world is grateful for today
      </a>
    </div>

    <!-- Facts & Fakes widget -->
    <div class="sidebar-widget">
      <h4>Fact-Check It</h4>
      <a href="https://factsandfakes.ai" target="_blank" rel="noopener" class="sidebar-link">
        <span class="icon">🔍</span>
        Facts &amp; Fakes AI — paste any news article and check the claims
      </a>
    </div>

    <!-- Learn Something New widget -->
    <div class="sidebar-widget">
      <h4>Learn Something New</h4>
      <a href="learn-something-new.html" class="sidebar-link">
        <span class="icon">💡</span>
        A random lesson in under 5 minutes — powered by AI
      </a>
      <p class="mt-1" style="font-size:0.78rem; color:var(--muted); font-style:italic;">
        Something different every time. Give it a click.
      </p>
    </div>

    <!-- Podcast widget -->
    <div class="sidebar-widget">
      <h4>The Podcast</h4>
      <p class="sidebar-link" style="cursor:default; border-bottom:none; color:var(--muted);">
        <span class="icon">🎙️</span>
        Meat and the Machine — coming soon to Spotify
      </p>
      <p class="mt-1" style="font-size:0.78rem; color:var(--muted); font-style:italic;">
        Real conversations between a human mind and an artificial one.
      </p>
    </div>

    <!-- AI methodology badge -->
    <div class="sidebar-widget">
      <h4>How Posts Are Made</h4>
      <div class="ai-badge">
        <span class="ai-icon">🤖</span>
        <span>Jim writes these posts. Before publishing, each piece is reviewed by a panel of AI systems — including GPT, Gemini, and Claude — for logical consistency and blind spots. AI edits, Jim decides.</span>
      </div>
    </div>
  `;
}

// ----- Inject shared footer -----
function renderFooter() {
  const year = new Date().getFullYear();
  document.getElementById('site-footer').innerHTML = `
    <div class="site-wrapper">
      <span>© ${year} James Dillingham · View from the Cheap Seats</span>
      <span class="footer-note">Not for profit. Not for sale. Just my view.</span>
    </div>
  `;
}

// ----- Comments -----
const COMMENTS_API = 'https://jamesdillingham-comments.onrender.com';

async function submitComment(btn) {
  const form = btn.closest('.comment-form');
  const body = form.querySelector('textarea').value.trim();
  const name = form.querySelector('input[type="text"]:not([name="_gotcha"])').value.trim();
  const email = form.querySelector('input[type="email"]').value.trim();

  const honeypot = form.querySelector('input[name="_gotcha"]');
  if (honeypot && honeypot.value) return;

  if (!body || !name) {
    alert('Please enter your name and a comment.');
    return;
  }

  const slug = window.location.pathname.replace(/\//g, '').replace('.html', '') || 'home';

  btn.disabled = true;
  btn.textContent = 'Submitting...';

  try {
    // Save to database
    const res = await fetch(`${COMMENTS_API}/comments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ post_slug: slug, name, email, body })
    });
    const data = await res.json();

    // Notify Jim via Formspree
    await fetch('https://formspree.io/f/xzdypeyp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify({
        name: name,
        email: email || 'not provided',
        post: slug,
        comment: body,
        _subject: `New comment on '${slug}' — View from the Cheap Seats`
      })
    });

    form.querySelector('textarea').value = '';
    form.querySelector('input[type="text"]:not([name="_gotcha"])').value = '';
    form.querySelector('input[type="email"]').value = '';
    btn.textContent = 'Comment Submitted';
    btn.disabled = false;

    // Remove any previous success message
    const oldMsg = form.querySelector('.comment-success');
    if (oldMsg) oldMsg.remove();

    const msg = document.createElement('p');
    msg.className = 'comment-success';
    msg.textContent = data.message || 'Your comment has been submitted for review. Thanks!';
    form.appendChild(msg);
  } catch (err) {
    alert('Something went wrong. Please try again.');
    btn.disabled = false;
    btn.textContent = 'Post Comment';
  }
}

async function loadComments(postSlug) {
  const list = document.getElementById('comments-list');
  if (!list) return;
  try {
    const res = await fetch(`${COMMENTS_API}/comments/${postSlug}`);
    const data = await res.json();
    if (data.comments.length === 0) {
      list.innerHTML = '<p style="font-size:0.85rem; color:var(--muted); font-style:italic;">No comments yet. Be the first.</p>';
      return;
    }
    list.innerHTML = data.comments.map(c => `
      <div style="padding:1rem 0; border-top:1px solid var(--border);">
        <strong style="font-size:0.9rem;">${escapeHtml(c.name)}</strong>
        <span style="font-size:0.75rem; color:var(--muted); margin-left:0.5rem;">${new Date(c.created_at).toLocaleDateString()}</span>
        <p style="margin-top:0.4rem; font-size:0.95rem;">${escapeHtml(c.body)}</p>
      </div>
    `).join('');
  } catch (err) {
    console.error('Could not load comments:', err);
  }
}

// Basic XSS protection for displayed comments
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// ----- Event delegation for comment buttons -----
document.addEventListener('click', function(e) {
  if (e.target && e.target.classList.contains('btn') && e.target.closest('.comment-form')) {
    submitComment(e.target);
  }
});
