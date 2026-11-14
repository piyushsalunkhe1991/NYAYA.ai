/* NYAYA.ai single-page dashboard (plain JavaScript, no build step). */
const state = { user: null, conv: null, msgs: [], demo: false, lang: 'auto', prefill: '', busy: false };
const NAV = [['dashboard', '🏠', 'Dashboard'], ['chat', '💬', 'AI Legal Chat'], ['documents', '📄', 'Document Analyzer'],
  ['rights', '📚', 'Know Your Rights'], ['cases', '🔍', 'Case Search'], ['history', '🗂️', 'History & Saved'], ['profile', '👤', 'Profile']];

/* ---------------- boot & auth ---------------- */
async function boot() {
  if (store.token) {
    try { state.user = await api('/api/auth/me'); state.lang = state.user.language; renderShell(); return; }
    catch (e) { if (e.code !== 'NETWORK') store.token = null; else { renderAuth(e.message); return; } }
  }
  renderAuth();
}

function renderAuth(notice = '') {
  let mode = 'login';
  const draw = () => {
    $('#root').innerHTML = `<div class="auth-wrap"><div class="auth-card">
      <h2>NYAYA<span style="color:var(--gold)">.ai</span></h2>
      <div class="tabs" style="justify-content:center"><span class="tab ${mode === 'login' ? 'on' : ''}" data-m="login">Log in</span><span class="tab ${mode === 'register' ? 'on' : ''}" data-m="register">Register</span></div>
      <form id="af">
        ${mode === 'register' ? '<label>Full name</label><input id="an" required minlength="2" autocomplete="name">' : ''}
        <label>E-mail</label><input id="ae" type="email" required autocomplete="email">
        <label>Password ${mode === 'register' ? '(min 6 characters)' : ''}</label><input id="ap" type="password" required minlength="${mode === 'register' ? 6 : 1}" autocomplete="${mode === 'login' ? 'current-password' : 'new-password'}">
        <button class="btn btn-navy" style="width:100%;margin-top:1.1rem;justify-content:center" id="ab">${mode === 'login' ? 'Log in' : 'Create account'}</button>
        <div class="err" id="aerr">${esc(notice)}</div>
      </form><p style="text-align:center;font-size:.85rem"><a href="index.html">← Back to home</a></p></div></div>`;
    document.querySelectorAll('[data-m]').forEach(t => t.onclick = () => { mode = t.dataset.m; notice = ''; draw(); });
    $('#af').onsubmit = async ev => {
      ev.preventDefault(); $('#ab').disabled = true; $('#aerr').textContent = '';
      try {
        const body = { email: $('#ae').value, password: $('#ap').value };
        if (mode === 'register') body.name = $('#an').value;
        const r = await api('/api/auth/' + mode, { method: 'POST', body, auth: false });
        store.token = r.token; state.user = r.user; state.lang = r.user.language; renderShell();
      } catch (e) { $('#aerr').textContent = e.message; $('#ab').disabled = false; }
    };
  };
  draw();
}

/* ---------------- shell & routing ---------------- */
function renderShell() {
  const nav = NAV.concat(state.user.is_admin ? [['admin', '🛠️', 'Admin']] : []);
  $('#root').innerHTML = `<div class="shell"><aside class="side" id="side"><a class="logo" href="index.html">NYAYA<span>.ai</span></a>
    ${nav.map(n => `<a class="nv" href="#${n[0]}" data-r="${n[0]}"><span>${n[1]}</span>${n[2]}</a>`).join('')}
    <div class="who"><b>${esc(state.user.name)}</b>${esc(state.user.email)}${state.user.is_admin ? ' <span class="pill gold">Admin</span>' : ''}<br><a href="#" id="lo" style="color:var(--gold2)">Log out</a></div></aside>
    <main class="main"><div class="top"><button class="burger" id="bg">☰</button><b>NYAYA.ai</b></div><div class="view" id="view"></div></main></div>`;
  $('#bg').onclick = () => $('#side').classList.toggle('open');
  $('#lo').onclick = async e => { e.preventDefault(); try { await api('/api/auth/logout', { method: 'POST' }); } catch {} store.token = null; location.hash = ''; location.reload(); };
  route();
}

const VIEWS = { dashboard: viewDashboard, chat: viewChat, documents: viewDocuments, rights: viewRights, cases: viewCases, history: viewHistory, profile: viewProfile, admin: viewAdmin };
async function route() {
  if (!state.user) return;
  const r = (location.hash.slice(1) || 'dashboard');
  const name = VIEWS[r] ? r : 'dashboard';
  document.querySelectorAll('.nv').forEach(a => a.classList.toggle('on', a.dataset.r === name));
  $('#side').classList.remove('open');
  const v = $('#view'); v.style.animation = 'none'; void v.offsetWidth; v.style.animation = '';
  try { await VIEWS[name](v); } catch (e) { v.innerHTML = `<div class="card err">${esc(e.message)}</div>`; }
}
window.addEventListener('hashchange', route);

const head = (t, p, extra = '') => `<div class="page-h"><div><h1>${t}</h1><p>${p}</p></div>${extra}</div>`;

/* ---------------- dashboard ---------------- */
async function viewDashboard(v) {
  v.innerHTML = head('Welcome, ' + esc(state.user.name.split(' ')[0]), 'Your legal information workspace');
  const s = await api('/api/dashboard/stats');
  v.innerHTML += `<div class="grid" style="margin-bottom:1.2rem">
    ${[['Conversations', s.conversations], ['Saved answers', s.saved_answers], ['Documents analysed', s.documents], ['Searches', s.searches]]
      .map(x => `<div class="card stat"><b>${x[1]}</b><span>${x[0]}</span></div>`).join('')}</div>
    <div class="grid"><div class="card"><h3>Recent conversations</h3><div class="list">${s.recent_conversations.length
      ? s.recent_conversations.map(c => `<div class="row"><span class="clickable" data-c="${c.id}">${esc(c.title)}</span><small>${fmtDate(c.updated_at)}</small></div>`).join('')
      : '<div class="empty">No conversations yet.</div>'}</div></div>
    <div class="card"><h3>Quick actions</h3><p style="margin-bottom:1rem">Start with one of these.</p>
      <a class="btn btn-gold btn-sm" href="#chat">Ask a legal question</a> <a class="btn btn-ghost btn-sm" href="#documents">Analyse a PDF</a> <a class="btn btn-ghost btn-sm" href="#rights">Know your rights</a></div>
    <div class="card"><h3>AI service status</h3><p id="ais">Checking…</p><button class="btn btn-ghost btn-sm" id="aisb">Re-check</button></div></div>`;
  v.querySelectorAll('[data-c]').forEach(e => e.onclick = () => { openConversation(+e.dataset.c); });
  const check = async () => {
    $('#ais').textContent = 'Checking…';
    try {
      const r = await api('/api/ai/status');
      $('#ais').innerHTML = r.available
        ? `<span class="pill good">Connected</span> ${esc(r.base_url)}<br><small>Model: <b>${esc(r.model)}</b> ${r.model_listed === false ? '(not in provider list; fallback will be tried)' : ''}</small>`
        : `<span class="pill bad">Unavailable</span><br><small>${esc(r.error)}</small><br><small>Chat will show an error. You can use the labelled Demo mode.</small>`;
    } catch (e) { $('#ais').innerHTML = `<span class="pill bad">Error</span> ${esc(e.message)}`; }
  };
  $('#aisb').onclick = check; check();
}

/* ---------------- module 1: chat ---------------- */
const SUGGEST = ['What are my rights if police arrest me?', 'My landlord is not returning my security deposit. What can I do?', 'What is the difference between IPC and BNS?', 'मुझे ऑनलाइन ठगी का शिकार होने पर क्या करना चाहिए?'];

async function openConversation(id) {
  const c = await api('/api/history/conversations/' + id);
  state.conv = c.id; state.msgs = c.messages; location.hash = 'chat'; if (($('#msgs'))) viewChat($('#view'));
}

async function viewChat(v) {
  v.innerHTML = head('AI Legal Chat', 'Ask about Indian law in Hindi or English', '<button class="btn btn-ghost btn-sm" id="nc">+ New chat</button>') +
    `<div class="banner">⚠️ ${DISCLAIMER}</div>
    <div class="chat"><div class="convs" id="convs"></div><div class="pane"><div class="msgs" id="msgs"></div>
    <div class="composer"><div class="opts">
      <label>Language <select id="lang"><option value="auto">Auto</option><option value="en">English</option><option value="hi">हिन्दी</option></select></label>
      <label title="Uses the built-in knowledge base only. NOT AI."><input type="checkbox" id="demo"> Demo mode (no AI)</label></div>
      <div class="in"><textarea id="q" placeholder="Type your legal question… / अपना कानूनी प्रश्न लिखें…"></textarea><button class="btn btn-gold" id="send">Send</button></div></div></div></div>`;
  $('#lang').value = state.lang; $('#demo').checked = state.demo;
  $('#lang').onchange = e => state.lang = e.target.value;
  $('#demo').onchange = e => state.demo = e.target.checked;
  $('#nc').onclick = () => { state.conv = null; state.msgs = []; renderMsgs(); loadConvs(); };
  $('#send').onclick = () => { const t = $('#q').value; $('#q').value = ''; send(t); };
  $('#q').onkeydown = e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); $('#send').click(); } };
  renderMsgs(); loadConvs();
  if (state.prefill) { $('#q').value = state.prefill; state.prefill = ''; $('#q').focus(); }
}

async function loadConvs() {
  const box = $('#convs'); if (!box) return;
  try {
    const h = await api('/api/history');
    box.innerHTML = h.conversations.length ? h.conversations.map(c => `<div class="c ${c.id === state.conv ? 'on' : ''}" data-id="${c.id}" title="${esc(c.title)}">${esc(c.title)}</div>`).join('') : '<div class="empty">No chats yet</div>';
    box.querySelectorAll('.c').forEach(e => e.onclick = () => openConversation(+e.dataset.id));
  } catch {}
}

function renderMsgs(typing = false) {
  const box = $('#msgs'); if (!box) return;
  if (!state.msgs.length && !typing) {
    box.innerHTML = `<div class="empty" style="margin:auto"><h3>How can I help you today?</h3><p>Ask a question about Indian law.</p><div class="chips">${SUGGEST.map(s => `<span class="chip">${esc(s)}</span>`).join('')}</div></div>`;
    box.querySelectorAll('.chip').forEach(c => c.onclick = () => send(c.textContent)); return;
  }
  box.innerHTML = state.msgs.map((m, i) => {
    if (m.role === 'user') return `<div class="m user">${esc(m.content)}</div>`;
    if (m.role === 'error') return `<div class="m ai error"><b>⚠️ ${m.code === 'AI_UNAVAILABLE' ? 'The AI service is unavailable' : 'Error'}</b><p>${esc(m.content)}</p><div class="act"><button class="btn btn-ghost btn-sm" data-retry="${i}">Retry</button>${m.code === 'AI_UNAVAILABLE' ? `<button class="btn btn-navy btn-sm" data-demo="${i}">Use Demo mode (not AI)</button>` : ''}</div></div>`;
    return `<div class="m ai">${m.is_demo ? '<span class="pill gold">DEMO · not AI generated</span>' : ''}${md(m.content)}<div class="act"><button class="btn btn-ghost btn-sm" data-save="${i}">☆ Save answer</button></div></div>`;
  }).join('') + (typing ? '<div class="m ai typing"><span></span><span></span><span></span></div>' : '');
  box.querySelectorAll('[data-save]').forEach(b => b.onclick = () => saveAnswer(+b.dataset.save, b));
  box.querySelectorAll('[data-retry]').forEach(b => b.onclick = () => retry(+b.dataset.retry, false));
  box.querySelectorAll('[data-demo]').forEach(b => b.onclick = () => retry(+b.dataset.demo, true));
  box.scrollTop = box.scrollHeight;
}

function retry(i, demo) {
  const text = state.msgs[i - 1] && state.msgs[i - 1].content;
  state.msgs.splice(i - 1, 2); // remove the failed question + error bubble, then resend
  if (demo) { state.demo = true; const c = $('#demo'); if (c) c.checked = true; }
  send(text);
}

async function send(text) {
  text = (text || '').trim(); if (!text || state.busy) return;
  state.busy = true; $('#send').disabled = true;
  state.msgs.push({ role: 'user', content: text }); renderMsgs(true);
  try {
    const r = await api('/api/chat', { method: 'POST', body: { message: text, conversation_id: state.conv, language: state.lang, demo: state.demo } });
    state.conv = r.conversation_id;
    state.msgs.push({ id: r.message_id, role: 'assistant', content: r.answer, category: r.category, is_demo: r.demo });
  } catch (e) { state.msgs.push({ role: 'error', content: e.message, code: e.code }); }
  state.busy = false; const b = $('#send'); if (b) b.disabled = false;
  renderMsgs(); loadConvs();
}

async function saveAnswer(i, btn) {
  const m = state.msgs[i]; const q = state.msgs[i - 1];
  try {
    await api('/api/history/save', { method: 'POST', body: { title: (q ? q.content : 'Legal answer').slice(0, 80), content: m.content, category: m.category } });
    btn.textContent = '★ Saved'; btn.disabled = true; toast('Answer saved');
  } catch (e) { toast(e.message); }
}

/* ---------------- module 2: documents ---------------- */
async function viewDocuments(v) {
  v.innerHTML = head('Legal Document Analyzer', 'Upload a PDF to get a plain-language summary') +
    `<div class="banner">Only text-based PDFs (max 10 MB). Scanned/image PDFs are not supported. Document text is sent to the AI service for analysis, so avoid uploading highly sensitive documents.</div>
    <div class="drop" id="drop"><div style="font-size:2rem">📄</div><p><b>Click to choose a PDF</b> or drag and drop it here</p><small id="fn" style="color:var(--muted)"></small>
    <input type="file" id="file" accept="application/pdf,.pdf" hidden></div>
    <p><button class="btn btn-gold" id="go" disabled>Analyse document</button></p><div id="res"></div>`;
  let file = null;
  const pick = f => { file = f; $('#fn').textContent = f ? `${f.name} (${(f.size / 1024).toFixed(0)} KB)` : ''; $('#go').disabled = !f; };
  $('#drop').onclick = () => $('#file').click();
  $('#file').onchange = e => pick(e.target.files[0]);
  $('#drop').ondragover = e => { e.preventDefault(); $('#drop').classList.add('over'); };
  $('#drop').ondragleave = () => $('#drop').classList.remove('over');
  $('#drop').ondrop = e => { e.preventDefault(); $('#drop').classList.remove('over'); pick(e.dataTransfer.files[0]); };
  $('#go').onclick = async () => {
    const fd = new FormData(); fd.append('file', file); $('#go').disabled = true;
    $('#res').innerHTML = '<div class="card typing"><span></span><span></span><span></span> Reading and analysing…</div>';
    try {
      const r = await api('/api/documents/analyze', { method: 'POST', body: fd });
      $('#res').innerHTML = `<div class="card result"><h3>${esc(r.filename)}</h3><p><span class="pill">${r.pages} pages</span> <span class="pill">${r.characters} characters</span> ${r.truncated ? '<span class="pill gold">Only the first part was analysed</span>' : ''}</p>${md(r.analysis)}<p class="banner">${DISCLAIMER}</p></div>`;
    } catch (e) { $('#res').innerHTML = `<div class="card"><b class="err">⚠️ ${esc(e.message)}</b></div>`; }
    $('#go').disabled = false;
  };
}

/* ---------------- module 3: rights ---------------- */
async function viewRights(v) {
  const d = await api('/api/legal/categories');
  v.innerHTML = head('Know Your Rights', 'Simple explanations with Indian legal references') + `<div class="banner">${esc(d.note)}</div>
    <div class="grid">${d.categories.map(c => `<div class="card clickable" data-id="${c.id}"><div class="ic">${c.icon}</div><h3>${c.title}</h3><p style="margin-bottom:.4rem"><small>${c.title_hi}</small></p><p>${esc(c.summary)}</p></div>`).join('')}</div>`;
  v.querySelectorAll('[data-id]').forEach(e => e.onclick = () => showCategory(d.categories.find(c => c.id === e.dataset.id)));
}

function showCategory(c) {
  const m = document.createElement('div'); m.className = 'modal';
  m.innerHTML = `<div class="box"><h2>${c.icon} ${c.title} <small style="font-size:.6em;color:var(--muted)">${c.title_hi}</small></h2><p>${esc(c.summary)}</p>
    <h4>Your rights</h4>${c.rights.map(r => `<p><b>${esc(r.title)}</b><br>${esc(r.explanation)}</p>`).join('')}
    <h4>Legal references</h4><ul>${c.references.map(r => `<li>${esc(r.label)} <small>(${esc(r.note)})</small></li>`).join('')}</ul>
    ${c.helplines.length ? `<h4>Helplines</h4><p>${c.helplines.map(h => `<span class="pill good">${esc(h.name)}: ${esc(h.number)}</span>`).join(' ')}</p>` : ''}
    <h4>Official sources</h4><ul>${c.sources.map(s => `<li><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.name)}</a></li>`).join('')}</ul>
    <p class="banner">${DISCLAIMER}</p><button class="btn btn-gold" id="ask">Ask the AI about this</button> <button class="btn btn-ghost" id="cl">Close</button></div>`;
  document.body.appendChild(m);
  m.onclick = e => { if (e.target === m) m.remove(); };
  $('#cl', m).onclick = () => m.remove();
  $('#ask', m).onclick = () => { state.prefill = `Explain my ${c.title.toLowerCase()} in India in simple language and what I can do if they are violated.`; m.remove(); location.hash = 'chat'; };
}

/* ---------------- module 4: case search ---------------- */
async function viewCases(v) {
  v.innerHTML = head('Legal Case Search', 'Find landmark Supreme Court judgments by topic') +
    `<div class="banner">Results come from a small curated index of landmark judgments (title, court, year). It is not exhaustive. Use the source links to read the actual judgments. Nothing is generated by AI.</div>
    <form id="sf" style="display:flex;gap:.6rem;margin-bottom:1rem"><input id="sq" placeholder="e.g. privacy, arrest, sexual harassment, consumer…" required minlength="2"><button class="btn btn-navy">Search</button></form><div id="sr"></div>`;
  $('#sf').onsubmit = async e => {
    e.preventDefault(); $('#sr').innerHTML = '<div class="empty">Searching…</div>';
    try {
      const r = await api('/api/legal/search?q=' + encodeURIComponent($('#sq').value));
      const ext = `<div class="card" style="margin-top:1rem"><h3>Search all judgments at official sources</h3><ul>${r.external_sources.map(s => `<li><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.name)}</a></li>`).join('')}</ul></div>`;
      $('#sr').innerHTML = (r.results.length
        ? `<div class="grid">${r.results.map(c => `<div class="card"><h3>${esc(c.title)}</h3><p><span class="pill">${esc(c.court)}</span> <span class="pill gold">${c.year}</span></p><p style="margin-top:.6rem"><a href="${esc(c.source_url)}" target="_blank" rel="noopener">🔗 ${esc(c.source_name)}</a></p></div>`).join('')}</div>`
        : `<div class="card"><b>No verified result found.</b><p>${esc(r.notice)}</p></div>`) + ext;
    } catch (err) { $('#sr').innerHTML = `<div class="card err">${esc(err.message)}</div>`; }
  };
}

/* ---------------- module 5: history & profile ---------------- */
async function viewHistory(v) {
  const h = await api('/api/history'); let tab = 'conversations';
  const draw = () => {
    const rows = {
      conversations: () => h.conversations.map(c => `<div class="row"><span class="clickable" data-open="${c.id}">${esc(c.title)}</span><span><small>${fmtDate(c.updated_at)}</small> <button class="btn btn-ghost btn-sm" data-delc="${c.id}">Delete</button></span></div>`),
      saved: () => h.saved.map(s => `<div class="row"><span class="clickable" data-view="${s.id}">⭐ ${esc(s.title)}</span><span><small>${fmtDate(s.created_at)}</small> <button class="btn btn-ghost btn-sm" data-dels="${s.id}">Delete</button></span></div>`),
      documents: () => h.documents.map(d => `<div class="row"><span class="clickable" data-doc="${d.id}">📄 ${esc(d.filename)} <small>(${d.pages} pages)</small></span><small>${fmtDate(d.created_at)}</small></div>`),
      searches: () => h.searches.map(s => `<div class="row"><span>🔍 ${esc(s.query)}</span><small>${fmtDate(s.created_at)}</small></div>`),
    }[tab]();
    $('#hl').innerHTML = rows.length ? rows.join('') : '<div class="empty">Nothing here yet.</div>';
    document.querySelectorAll('.tab').forEach(t => t.classList.toggle('on', t.dataset.t === tab));
    v.querySelectorAll('[data-open]').forEach(e => e.onclick = () => openConversation(+e.dataset.open));
    v.querySelectorAll('[data-delc]').forEach(e => e.onclick = async () => { await api('/api/history/conversations/' + e.dataset.delc, { method: 'DELETE' }); h.conversations = h.conversations.filter(c => c.id != e.dataset.delc); if (state.conv == e.dataset.delc) { state.conv = null; state.msgs = []; } draw(); });
    v.querySelectorAll('[data-dels]').forEach(e => e.onclick = async () => { await api('/api/history/saved/' + e.dataset.dels, { method: 'DELETE' }); h.saved = h.saved.filter(c => c.id != e.dataset.dels); draw(); });
    v.querySelectorAll('[data-view]').forEach(e => e.onclick = () => { const s = h.saved.find(x => x.id == e.dataset.view); popup(s.title, s.content); });
    v.querySelectorAll('[data-doc]').forEach(e => e.onclick = () => { const d = h.documents.find(x => x.id == e.dataset.doc); popup(d.filename, d.analysis); });
  };
  v.innerHTML = head('History & Saved', 'Your recent activity') +
    `<div class="tabs">${[['conversations', 'Conversations'], ['saved', 'Saved answers'], ['documents', 'Document analyses'], ['searches', 'Search history']].map(t => `<span class="tab" data-t="${t[0]}">${t[1]}</span>`).join('')}</div><div class="card list" id="hl"></div>`;
  v.querySelectorAll('.tab').forEach(t => t.onclick = () => { tab = t.dataset.t; draw(); });
  draw();
}

function popup(title, content) {
  const m = document.createElement('div'); m.className = 'modal';
  m.innerHTML = `<div class="box"><h3>${esc(title)}</h3>${md(content)}<button class="btn btn-ghost" id="pc">Close</button></div>`;
  document.body.appendChild(m); m.onclick = e => { if (e.target === m) m.remove(); }; $('#pc', m).onclick = () => m.remove();
}

async function viewProfile(v) {
  const u = state.user;
  v.innerHTML = head('Profile settings', 'Manage your account') + `<div class="card" style="max-width:520px"><form id="pf">
    <label>Name</label><input id="pn" value="${esc(u.name)}" required minlength="2">
    <label>E-mail</label><input value="${esc(u.email)}" disabled>
    <label>Preferred answer language</label><select id="pl"><option value="auto">Auto-detect</option><option value="en">English</option><option value="hi">हिन्दी</option></select>
    <button class="btn btn-navy" style="margin-top:1rem">Save changes</button> <span id="pm" class="ok"></span></form></div>`;
  $('#pl').value = u.language;
  $('#pf').onsubmit = async e => {
    e.preventDefault();
    try { state.user = await api('/api/auth/me', { method: 'PATCH', body: { name: $('#pn').value, language: $('#pl').value } }); state.lang = state.user.language; $('#pm').textContent = 'Saved ✓'; }
    catch (err) { $('#pm').innerHTML = `<span class="err">${esc(err.message)}</span>`; }
  };
}

/* ---------------- module 6: admin ---------------- */
async function viewAdmin(v) {
  if (!state.user.is_admin) { v.innerHTML = '<div class="card err">Admin access required.</div>'; return; }
  const s = await api('/api/admin/stats'); const max = Math.max(1, ...s.top_categories.map(c => c.count));
  v.innerHTML = head('Admin dashboard', 'Platform-wide usage') + `<div class="grid" style="margin-bottom:1.2rem">
    ${[['Registered users', s.total_users], ['Conversations', s.total_conversations], ['Questions asked', s.total_messages], ['Documents analysed', s.documents_analyzed]].map(x => `<div class="card stat"><b>${x[1]}</b><span>${x[0]}</span></div>`).join('')}</div>
    <div class="card"><h3>Most searched legal categories</h3>${s.top_categories.length ? s.top_categories.map(c => `<div style="margin:.7rem 0"><div style="display:flex;justify-content:space-between"><span>${esc(c.title)}</span><b>${c.count}</b></div><div class="bar"><i style="width:${c.count / max * 100}%"></i></div></div>`).join('') : '<div class="empty">No data yet.</div>'}</div>`;
}

boot();
