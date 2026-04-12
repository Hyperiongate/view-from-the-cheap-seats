/* ============================================
   View from the Cheap Seats — Site Components
   Shared header, nav, sidebar, footer
   ============================================ */

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
      <a href="https://jimdillingham.substack.com/subscribe" target="_blank" rel="noopener" class="btn btn-sm" style="display:block; text-align:center; margin-top:0.5rem;">Subscribe</a>
    </div>

    <!-- Facts & Fakes widget -->
    <div class="sidebar-widget">
      <h4>Fact-Check It</h4>
      <a href="https://factsandfakes.ai" target="_blank" rel="noopener" class="sidebar-link">
        <span class="icon">🔍</span>
        Facts &amp; Fakes AI — paste any news article and check the claims
      </a>
    </div>

    <!-- Podcast widget -->
    <div class="sidebar-widget">
      <h4>The Podcast</h4>
      <a href="#podcast-link" target="_blank" rel="noopener" class="sidebar-link">
        <span class="icon">🎙️</span>
        Meat and the Machine — listen on Spotify
      </a>
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

// ----- Subscribe handler (placeholder) -----
function handleSubscribe(e) {
  e.preventDefault();
  const input = e.target.querySelector('input[type="email"]');
  alert(`Thanks! We'll notify ${input.value} when new posts go up.`);
  input.value = '';
  // TODO: wire to your email list backend / Swarm
}

// ----- Comments -----
const COMMENTS_API = 'https://jamesdillingham-comments.onrender.com';

async function submitComment(btn) {
  const form = btn.closest('.comment-form');
  const body = form.querySelector('textarea').value.trim();
  const name = form.querySelector('input[type="text"]').value.trim();
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
    // Step 1: Save to database
    const res = await fetch(`${COMMENTS_API}/comments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ post_slug: slug, name, email, body })
    });
    const data = await res.json();

    // Step 2: Notify Jim via Formspree from browser
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
    form.querySelector('input[type="text"]').value = '';
    form.querySelector('input[type="email"]').value = '';
    btn.textContent = 'Comment Submitted';
    btn.disabled = false;
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
        <strong style="font-size:0.9rem;">${c.name}</strong>
        <span style="font-size:0.75rem; color:var(--muted); margin-left:0.5rem;">${new Date(c.created_at).toLocaleDateString()}</span>
        <p style="margin-top:0.4rem; font-size:0.95rem;">${c.body}</p>
      </div>
    `).join('');
  } catch (err) {
    console.error('Could not load comments:', err);
  }
}

// ----- Audio player logic -----
// On first click: fetch from ElevenLabs API if no cached file,
// then play and store. On subsequent clicks: play cached audio.
async function handleAudioPlay(postSlug, btn) {
  const audioId = `audio-${postSlug}`;
  let audioEl = document.getElementById(audioId);

  if (audioEl && audioEl.src) {
    // Already loaded — just toggle play/pause
    audioEl.paused ? audioEl.play() : audioEl.pause();
    updateAudioBtn(btn, !audioEl.paused);
    return;
  }

  // Check if cached audio file exists
  const cachedUrl = `posts/audio/${postSlug}.mp3`;
  const exists = await checkFileExists(cachedUrl);

  if (exists) {
    playAudio(audioId, cachedUrl, btn);
  } else {
    // First-ever play: generate via ElevenLabs (server-side endpoint)
    btn.innerHTML = `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="white" stroke-width="2" fill="none"/><text x="6" y="16" fill="white" font-size="8">...</text></svg>`;
    btn.disabled = true;

    try {
      const res = await fetch(`/api/generate-audio?slug=${postSlug}`);
      const data = await res.json();
      if (data.url) {
        playAudio(audioId, data.url, btn);
      }
    } catch (err) {
      console.error('Audio generation failed:', err);
      btn.disabled = false;
      resetAudioBtn(btn);
    }
  }
}

function playAudio(audioId, url, btn) {
  let audioEl = document.getElementById(audioId);
  if (!audioEl) {
    audioEl = document.createElement('audio');
    audioEl.id = audioId;
    btn.closest('.audio-player').appendChild(audioEl);
  }
  audioEl.src = url;
  audioEl.play();
  updateAudioBtn(btn, true);

  audioEl.addEventListener('ended', () => updateAudioBtn(btn, false));
  audioEl.addEventListener('pause', () => updateAudioBtn(btn, false));
}

function updateAudioBtn(btn, playing) {
  btn.disabled = false;
  btn.innerHTML = playing
    ? `<svg viewBox="0 0 24 24"><rect x="6" y="4" width="4" height="16" fill="white"/><rect x="14" y="4" width="4" height="16" fill="white"/></svg>`
    : `<svg viewBox="0 0 24 24"><polygon points="5,3 19,12 5,21" fill="white"/></svg>`;
}

function resetAudioBtn(btn) {
  btn.innerHTML = `<svg viewBox="0 0 24 24"><polygon points="5,3 19,12 5,21" fill="white"/></svg>`;
}

async function checkFileExists(url) {
  try {
    const res = await fetch(url, { method: 'HEAD' });
    return res.ok;
  } catch { return false; }
}
// ----- Event delegation for comment buttons -----
document.addEventListener('click', function(e) {
  if (e.target && e.target.classList.contains('btn') && e.target.closest('.comment-form')) {
    submitComment(e.target);
  }
});
