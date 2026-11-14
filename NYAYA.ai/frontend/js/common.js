/* Shared helpers: API client, safe markdown, small utilities. */
const API_BASE = location.protocol === 'file:' ? 'http://127.0.0.1:8000' : '';
const DISCLAIMER = 'NYAYA.ai gives general legal information, not legal advice. Consult a qualified advocate for your situation.';
const $ = (s, r = document) => r.querySelector(s);

const store = {
  get token() { try { return localStorage.getItem('nyaya_token'); } catch { return null; } },
  set token(v) { try { v ? localStorage.setItem('nyaya_token', v) : localStorage.removeItem('nyaya_token'); } catch {} },
};

/** Call the backend. Throws Error(message) with .code/.status on failure. */
async function api(path, { method = 'GET', body, auth = true } = {}) {
  const headers = {};
  if (auth && store.token) headers.Authorization = 'Bearer ' + store.token;
  let payload;
  if (body instanceof FormData) payload = body;
  else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
  let res;
  try { res = await fetch(API_BASE + path, { method, headers, body: payload }); }
  catch { const e = new Error('Cannot reach the NYAYA.ai backend. Is it running on port 8000?'); e.code = 'NETWORK'; throw e; }
  let data = null;
  try { data = await res.json(); } catch {}
  if (!res.ok) {
    const d = data && data.detail;
    let msg = 'Request failed (' + res.status + ')';
    if (typeof d === 'string') msg = d;
    else if (d && d.message) msg = d.message;
    else if (Array.isArray(d) && d[0] && d[0].msg) msg = d[0].msg.replace(/^Value error, /, '');
    const e = new Error(msg); e.status = res.status; e.code = d && d.code; throw e;
  }
  return data;
}

const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/** Minimal, XSS-safe markdown (escape first, then format). */
function md(src) {
  const inline = t => t
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/`(.+?)`/g, '<code>$1</code>')
    .replace(/(^|[^*])\*([^*\s][^*]*?)\*/g, '$1<em>$2</em>');
  let html = '', list = '';
  const close = () => { if (list) { html += `</${list}>`; list = ''; } };
  for (const raw of esc(src).split('\n')) {
    const l = raw.trimEnd(); let m;
    if ((m = l.match(/^#{1,4}\s+(.*)/))) { close(); html += `<h4>${inline(m[1])}</h4>`; }
    else if ((m = l.match(/^\s*[-*•]\s+(.*)/))) { if (list !== 'ul') { close(); html += '<ul>'; list = 'ul'; } html += `<li>${inline(m[1])}</li>`; }
    else if ((m = l.match(/^\s*\d+[.)]\s+(.*)/))) { if (list !== 'ol') { close(); html += '<ol>'; list = 'ol'; } html += `<li>${inline(m[1])}</li>`; }
    else if ((m = l.match(/^&gt;\s?(.*)/))) { close(); html += `<p>${inline(m[1])}</p>`; }
    else if (!l.trim()) close();
    else { close(); html += `<p>${inline(l)}</p>`; }
  }
  close(); return html;
}

function toast(msg) {
  const t = document.createElement('div'); t.className = 'toast'; t.textContent = msg;
  document.body.appendChild(t); setTimeout(() => t.remove(), 2600);
}
const fmtDate = s => { const d = new Date((s || '').replace(' ', 'T') + 'Z'); return isNaN(d) ? s : d.toLocaleString(); };
