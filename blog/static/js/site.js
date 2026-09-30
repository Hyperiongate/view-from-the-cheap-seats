/* ============================================================================
   static/js/site.js — loads and posts comments under a blog post
   View from the Cheap Seats — jamesdillingham.com

   CHANGE NOTES
     2026-09-30  Site rebuild. Replaces the comment code in js/components.js.
                 Talks to this site's own server (/api/comments) instead of
                 the separate jamesdillingham-comments service; the server
                 does the spam check and emails Jim. Comments appear right
                 away. The post is identified by the page, not the URL, which
                 fixes comments from the home page landing under "index".
   ============================================================================ */

(function () {
  'use strict';

  var section = document.getElementById('comments');
  if (!section) return;
  var slug = section.getAttribute('data-post-slug');
  var list = document.getElementById('comments-list');
  var form = document.getElementById('comment-form');
  var btn = document.getElementById('comment-btn');
  var msg = document.getElementById('comment-message');

  function formatDate(iso) {
    var d = new Date(iso);
    if (isNaN(d)) return '';
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  function commentEl(c) {
    var wrap = document.createElement('div');
    wrap.className = 'comment';
    var name = document.createElement('strong');
    name.className = 'comment-name';
    name.textContent = c.name;
    var date = document.createElement('span');
    date.className = 'comment-date';
    date.textContent = formatDate(c.created_at);
    var body = document.createElement('p');
    body.className = 'comment-body';
    body.textContent = c.body;
    wrap.appendChild(name);
    wrap.appendChild(date);
    wrap.appendChild(body);
    return wrap;
  }

  function showEmpty() {
    list.innerHTML = '';
    var p = document.createElement('p');
    p.className = 'comments-empty';
    p.textContent = 'No comments yet. Be the first.';
    list.appendChild(p);
  }

  function load() {
    fetch('/api/comments/' + encodeURIComponent(slug))
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (data) {
        var comments = data.comments || [];
        if (!comments.length) { showEmpty(); return; }
        list.innerHTML = '';
        comments.forEach(function (c) { list.appendChild(commentEl(c)); });
      })
      .catch(function (err) {
        console.error('Could not load comments:', err);
        list.innerHTML = '';
      });
  }

  function setMessage(text, kind) {
    msg.textContent = text;
    msg.className = 'form-message ' + (kind || '');
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var body = form.elements.body.value.trim();
    var name = form.elements.name.value.trim();
    if (!body || !name) {
      setMessage('Please enter your name and a comment.', 'err');
      return;
    }
    btn.disabled = true;
    btn.textContent = 'Posting...';
    setMessage('');
    fetch('/api/comments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        post_slug: slug,
        name: name,
        email: form.elements.email.value.trim(),
        body: body,
        website: form.elements.website.value
      })
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        if (!res.ok || !res.data.ok) {
          setMessage(res.data.error || 'Something went wrong. Please try again.', 'err');
          return;
        }
        form.elements.body.value = '';
        setMessage(res.data.message || 'Thanks — your comment is posted.', 'ok');
        if (res.data.comment) {
          var empty = list.querySelector('.comments-empty');
          if (empty) empty.remove();
          list.appendChild(commentEl(res.data.comment));
        }
      })
      .catch(function () {
        setMessage('Something went wrong. Please try again.', 'err');
      })
      .then(function () {
        btn.disabled = false;
        btn.textContent = 'Post Comment';
      });
  });

  load();
})();

/* I did no harm and this file is not truncated. */
