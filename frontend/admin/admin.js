'use strict';

const TOKEN_KEY = 'portfolioAdminToken';

function $(sel, ctx = document) { return ctx.querySelector(sel); }
function $$(sel, ctx = document) { return Array.from(ctx.querySelectorAll(sel)); }

// The JWT lives in sessionStorage: it is cleared when the tab closes and is never
// shared with other tabs. The password is never stored in the browser at all.
// Note: any script on this page can still read the token, so keep this page free of third-party scripts.
function getToken() { return sessionStorage.getItem(TOKEN_KEY); }
function setToken(token) { sessionStorage.setItem(TOKEN_KEY, token); }
function clearToken() { sessionStorage.removeItem(TOKEN_KEY); }

function showToast(message) {
  const container = $('#admin-toast-container');
  const el = document.createElement('div');
  el.className = 'admin-toast';
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

// Every call goes through here so the JWT, JSON envelope and 401 handling
// (which force a re-login) are all handled in one place.
async function apiFetch(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined
  });
  let json = null;
  try { json = await res.json(); } catch (e) { /* empty body, e.g. 204-ish */ }

  if (res.status === 401) {
    clearToken();
    showLogin('Your session expired. Please log in again.');
    throw new Error('Unauthorized');
  }
  if (!res.ok || (json && json.success === false)) {
    throw new Error((json && json.message) || `Request failed (HTTP ${res.status})`);
  }
  return json ? json.data : null;
}

// ---- auth ----

function showLogin(notice) {
  $('#admin-app').hidden = true;
  $('#admin-login-view').hidden = false;
  if (notice) showToast(notice);
}

function showApp() {
  $('#admin-login-view').hidden = true;
  $('#admin-app').hidden = false;
}

async function initAuth() {
  const form = $('#admin-login-form');
  const errorEl = $('#admin-login-error');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorEl.textContent = '';
    const data = new FormData(form);
    try {
      const result = await apiFetch('/api/auth/login', {
        auth: false,
        method: 'POST',
        body: { email: String(data.get('email') || ''), password: String(data.get('password') || '') }
      });
      setToken(result.access_token);
      const me = await apiFetch('/api/auth/me');
      if (me.role !== 'admin') {
        clearToken();
        errorEl.textContent = 'This account does not have admin access.';
        return;
      }
      showApp();
      loadView('overview');
    } catch (err) {
      errorEl.textContent = err.message || 'Login failed.';
    }
  });

  $('#admin-logout').addEventListener('click', async () => {
    try { await apiFetch('/api/auth/logout', { method: 'POST' }); } catch (e) { /* ignore */ }
    clearToken();
    showLogin();
  });

  if (getToken()) {
    try {
      const me = await apiFetch('/api/auth/me');
      if (me.role === 'admin') { showApp(); loadView('overview'); return; }
    } catch (e) { /* falls through to login */ }
    clearToken();
  }
  showLogin();
}

// Runs a list action (delete, status change). Failures are shown as a toast
// instead of becoming unhandled promise rejections.
async function runListAction(action, successMessage, reload) {
  try {
    await action();
    showToast(successMessage);
    reload();
  } catch (err) {
    showToast(err.message || 'Something went wrong.');
  }
}

// ---- view switching ----

function initNav() {
  $$('.admin-nav__link').forEach((btn) => {
    btn.addEventListener('click', () => {
      $$('.admin-nav__link').forEach((b) => b.classList.remove('is-active'));
      btn.classList.add('is-active');
      loadView(btn.dataset.view);
    });
  });
}

function loadView(view) {
  $$('[data-view-panel]').forEach((panel) => { panel.hidden = panel.dataset.viewPanel !== view; });
  const loaders = { overview: loadOverview, projects: loadProjects, certificates: loadCertificates, hackathons: loadHackathons, messages: loadMessages, analytics: loadAnalytics };
  (loaders[view] || (() => {}))().catch((err) => showToast(err.message));
}

// ---- overview / analytics ----

function renderStatCards(container, stats) {
  container.innerHTML = '';
  stats.forEach(({ label, value }) => {
    const card = document.createElement('div');
    card.className = 'admin-stat-card';
    card.innerHTML = `<div class="admin-stat-card__value">${value}</div><div class="admin-stat-card__label">${label}</div>`;
    container.appendChild(card);
  });
}

async function loadOverview() {
  const data = await apiFetch('/api/analytics');
  renderStatCards($('#overview-stats'), [
    { label: 'Total Projects', value: data.total_projects },
    { label: 'Total Certificates', value: data.total_certificates },
    { label: 'Total Messages', value: data.total_messages },
    { label: 'Unread Messages', value: data.unread_messages },
    { label: 'Total Visitors', value: data.total_visitors }
  ]);
}

async function loadAnalytics() {
  const data = await apiFetch('/api/analytics');
  renderStatCards($('#analytics-stats'), [
    { label: 'Total Visitors', value: data.total_visitors },
    { label: 'Unique Sessions', value: data.unique_sessions }
  ]);
  const tbody = $('#top-pages-table tbody');
  tbody.innerHTML = '';
  data.top_pages.forEach((row) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${escapeHtml(row.page)}</td><td>${row.visits}</td>`;
    tbody.appendChild(tr);
  });
}

// Safe for both text and quoted attribute values. innerHTML alone does not encode quotes.
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str == null ? '' : String(str);
  return div.innerHTML.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// ---- generic modal form ----

let modalSubmitHandler = null;

function openModal(title, fields, values = {}) {
  $('#admin-modal-title').textContent = title;
  $('#admin-modal-error').textContent = '';
  const fieldsWrap = $('#admin-modal-fields');
  fieldsWrap.innerHTML = '';

  fields.forEach((field) => {
    const label = document.createElement('label');
    label.className = 'admin-field';
    const span = document.createElement('span');
    span.textContent = field.label;
    label.appendChild(span);

    let input;
    if (field.type === 'textarea') {
      input = document.createElement('textarea');
    } else if (field.type === 'select') {
      input = document.createElement('select');
      field.options.forEach((opt) => {
        const option = document.createElement('option');
        option.value = opt.value;
        option.textContent = opt.label;
        input.appendChild(option);
      });
    } else if (field.type === 'checkbox') {
      input = document.createElement('input');
      input.type = 'checkbox';
      input.checked = !!values[field.name];
    } else {
      input = document.createElement('input');
      input.type = field.type || 'text';
    }
    input.name = field.name;
    if (field.type !== 'checkbox') input.value = values[field.name] ?? '';
    if (field.required) input.required = true;
    label.appendChild(input);
    fieldsWrap.appendChild(label);
  });

  $('#admin-modal-overlay').hidden = false;
  const firstInput = $('input, textarea', fieldsWrap);
  if (firstInput) firstInput.focus();
}

function closeModal() {
  $('#admin-modal-overlay').hidden = true;
  modalSubmitHandler = null;
}

function initModal() {
  $('#admin-modal-cancel').addEventListener('click', closeModal);
  $('#admin-modal-overlay').addEventListener('click', (e) => { if (e.target.id === 'admin-modal-overlay') closeModal(); });
  $('#admin-modal-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!modalSubmitHandler) return;
    const form = e.target;
    const values = {};
    $$('input, textarea, select', form).forEach((input) => {
      values[input.name] = input.type === 'checkbox' ? input.checked : input.value;
    });
    const submitBtn = $('button[type="submit"]', form);
    submitBtn.disabled = true;
    submitBtn.textContent = 'Saving…';
    try {
      await modalSubmitHandler(values);
      closeModal();
    } catch (err) {
      $('#admin-modal-error').textContent = err.message || 'Something went wrong.';
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Save';
    }
  });
}

// ---- projects ----

const PROJECT_FIELDS = [
  { name: 'title', label: 'Title', required: true },
  { name: 'description', label: 'Description', type: 'textarea', required: true },
  { name: 'technologies', label: 'Technologies (comma-separated)' },
  { name: 'category', label: 'Category' },
  { name: 'image_url', label: 'Image URL' },
  { name: 'github_url', label: 'GitHub URL' },
  { name: 'live_url', label: 'Live URL' },
  { name: 'featured', label: 'Featured', type: 'checkbox' }
];

async function loadProjects() {
  const projects = await apiFetch('/api/projects', { auth: false });
  const tbody = $('#projects-table tbody');
  tbody.innerHTML = '';
  projects.forEach((project) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${escapeHtml(project.title)}</td>
      <td>${escapeHtml(project.category || '')}</td>
      <td class="truncate">${escapeHtml(project.technologies || '')}</td>
      <td>${project.featured ? 'Yes' : 'No'}</td>
      <td class="row-actions">
        <button type="button" class="admin-btn" data-edit="${project.id}">Edit</button>
        <button type="button" class="admin-btn admin-btn--danger" data-delete="${project.id}">Delete</button>
      </td>`;
    tbody.appendChild(tr);
  });

  tbody.querySelectorAll('[data-edit]').forEach((btn) => btn.addEventListener('click', () => {
    const project = projects.find((p) => String(p.id) === btn.dataset.edit);
    openModal('Edit Project', PROJECT_FIELDS, project);
    modalSubmitHandler = async (values) => {
      await apiFetch(`/api/projects/${project.id}`, { method: 'PUT', body: values });
      showToast('Project updated');
      loadProjects();
    };
  }));
  tbody.querySelectorAll('[data-delete]').forEach((btn) => btn.addEventListener('click', () => {
    if (!confirm('Delete this project?')) return;
    runListAction(() => apiFetch(`/api/projects/${btn.dataset.delete}`, { method: 'DELETE' }), 'Project deleted', loadProjects);
  }));
}

function initProjectCreate() {
  $('#project-new-btn').addEventListener('click', () => {
    openModal('New Project', PROJECT_FIELDS, { technologies: '', featured: false });
    modalSubmitHandler = async (values) => {
      await apiFetch('/api/projects', { method: 'POST', body: values });
      showToast('Project created');
      loadProjects();
    };
  });
}

// ---- certificates ----

const CERTIFICATE_FIELDS = [
  { name: 'title', label: 'Title', required: true },
  { name: 'issuer', label: 'Issuer', required: true },
  { name: 'issue_date', label: 'Issue Date', type: 'date' },
  { name: 'credential_id', label: 'Credential ID' },
  { name: 'credential_url', label: 'Credential URL' },
  { name: 'image_url', label: 'Image / Logo URL' },
  { name: 'pdf_url', label: 'PDF URL' }
];

async function loadCertificates() {
  const certificates = await apiFetch('/api/certificates', { auth: false });
  const tbody = $('#certificates-table tbody');
  tbody.innerHTML = '';
  certificates.forEach((cert) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${escapeHtml(cert.title)}</td>
      <td>${escapeHtml(cert.issuer)}</td>
      <td>${escapeHtml(cert.credential_id || '')}</td>
      <td class="row-actions">
        <button type="button" class="admin-btn" data-edit="${cert.id}">Edit</button>
        <button type="button" class="admin-btn admin-btn--danger" data-delete="${cert.id}">Delete</button>
      </td>`;
    tbody.appendChild(tr);
  });

  tbody.querySelectorAll('[data-edit]').forEach((btn) => btn.addEventListener('click', () => {
    const cert = certificates.find((c) => String(c.id) === btn.dataset.edit);
    openModal('Edit Certificate', CERTIFICATE_FIELDS, cert);
    modalSubmitHandler = async (values) => {
      if (!values.issue_date) values.issue_date = null;
      await apiFetch(`/api/certificates/${cert.id}`, { method: 'PUT', body: values });
      showToast('Certificate updated');
      loadCertificates();
    };
  }));
  tbody.querySelectorAll('[data-delete]').forEach((btn) => btn.addEventListener('click', () => {
    if (!confirm('Delete this certificate?')) return;
    runListAction(() => apiFetch(`/api/certificates/${btn.dataset.delete}`, { method: 'DELETE' }), 'Certificate deleted', loadCertificates);
  }));
}

function initCertificateCreate() {
  $('#certificate-new-btn').addEventListener('click', () => {
    openModal('New Certificate', CERTIFICATE_FIELDS, {});
    modalSubmitHandler = async (values) => {
      if (!values.issue_date) values.issue_date = null;
      await apiFetch('/api/certificates', { method: 'POST', body: values });
      showToast('Certificate created');
      loadCertificates();
    };
  });
}

// ---- workshops & hackathons ----

const HACKATHON_ICONS = ['bolt', 'layers', 'clock', 'trophy', 'book', 'code', 'globe', 'users'];
const HACKATHON_FIELDS = [
  { name: 'title', label: 'Title', required: true },
  { name: 'type', label: 'Type', type: 'select', required: true,
    options: [{ value: 'hackathon', label: 'Hackathon' }, { value: 'workshop', label: 'Workshop' }] },
  { name: 'description', label: 'Description', type: 'textarea' },
  { name: 'organizer', label: 'Organizer' },
  { name: 'date', label: 'Date', type: 'date' },
  { name: 'location', label: 'Location' },
  { name: 'icon', label: 'Icon', type: 'select',
    options: [{ value: '', label: 'None' }].concat(HACKATHON_ICONS.map((i) => ({ value: i, label: i }))) },
  { name: 'image_url', label: 'Image URL (optional)' },
  { name: 'certificate_url', label: 'Certificate URL' },
  { name: 'event_url', label: 'Event URL' },
  { name: 'subitems', label: 'Grouped sub-items (JSON list: [{"title": "...", "certificate_url": "..."}])', type: 'textarea' },
  { name: 'display_order', label: 'Display order (lower shows first)', type: 'number' },
  { name: 'is_visible', label: 'Visible on the public site', type: 'checkbox' }
];

let hackathonItems = [];

// Same rule as the backend: http(s) links or relative paths only.
function isAllowedUrl(value) {
  if (!value) return true;
  if (value.startsWith('//')) return false;
  if (/^[a-z][a-z0-9+.-]*:/i.test(value)) return /^https?:\/\//i.test(value);
  return true;
}

// Turns the modal's text values into the API payload, or throws a message for the form.
function buildHackathonPayload(values) {
  const text = (v) => { const t = String(v ?? '').trim(); return t === '' ? null : t; };
  const title = text(values.title);
  if (!title) throw new Error('Title is required.');
  if (title.length > 200) throw new Error('Title must be 200 characters or fewer.');
  if (!['hackathon', 'workshop'].includes(values.type)) throw new Error('Choose a type.');
  const description = text(values.description) || '';
  if (description.length > 2000) throw new Error('Description must be 2000 characters or fewer.');

  for (const name of ['image_url', 'certificate_url', 'event_url']) {
    const url = text(values[name]);
    if (url && !isAllowedUrl(url)) throw new Error('Links must start with https://, http://, or be a relative path such as "assets/file.pdf".');
  }

  let subitems = null;
  const rawSub = text(values.subitems);
  if (rawSub) {
    let parsed;
    try { parsed = JSON.parse(rawSub); } catch (e) { throw new Error('Sub-items must be valid JSON, e.g. [{"title": "...", "certificate_url": "..."}].'); }
    if (!Array.isArray(parsed)) throw new Error('Sub-items must be a JSON list.');
    if (parsed.length > 20) throw new Error('At most 20 sub-items are allowed.');
    subitems = parsed.map((s) => {
      if (!s || typeof s !== 'object' || !text(s.title)) throw new Error('Each sub-item needs a title.');
      if (s.certificate_url && !isAllowedUrl(String(s.certificate_url))) throw new Error('Sub-item links must be https:// links or relative paths.');
      return { title: String(s.title).trim(), certificate_url: text(s.certificate_url) };
    });
  }

  const order = Number(values.display_order === '' || values.display_order == null ? 0 : values.display_order);
  if (!Number.isInteger(order) || order < 0 || order > 100000) throw new Error('Display order must be a whole number from 0 to 100000.');
  if (values.date && !/^\d{4}-\d{2}-\d{2}$/.test(values.date)) throw new Error('Date must be a valid date.');

  return {
    title,
    type: values.type,
    description,
    organizer: text(values.organizer),
    date: text(values.date),
    location: text(values.location),
    icon: text(values.icon),
    image_url: text(values.image_url),
    certificate_url: text(values.certificate_url),
    event_url: text(values.event_url),
    subitems,
    display_order: order,
    is_visible: !!values.is_visible
  };
}

function hackathonFormValues(item) {
  return {
    ...item,
    date: item.date || '',
    icon: item.icon || '',
    subitems: item.subitems ? JSON.stringify(item.subitems, null, 2) : ''
  };
}

async function loadHackathons() {
  const tbody = $('#hackathons-table tbody');
  tbody.innerHTML = '<tr><td colspan="6" style="color:var(--muted)">Loading…</td></tr>';
  let items;
  try {
    items = await apiFetch('/api/hackathons/manage');
  } catch (err) {
    tbody.innerHTML = '';
    const tr = document.createElement('tr');
    tr.innerHTML = `<td colspan="6" class="admin-error">${escapeHtml(err.message)}</td>`;
    tbody.appendChild(tr);
    throw err;
  }
  hackathonItems = items;
  tbody.innerHTML = '';
  if (items.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" style="color:var(--muted)">No workshops or hackathons yet.</td></tr>';
    return;
  }

  items.forEach((item, index) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${escapeHtml(item.title)}</td>
      <td>${escapeHtml(item.type)}</td>
      <td>${escapeHtml(item.organizer || '')}</td>
      <td><input type="checkbox" data-visible="${item.id}" ${item.is_visible ? 'checked' : ''} aria-label="Visible on site: ${escapeHtml(item.title)}" /></td>
      <td class="row-actions">
        <button type="button" class="admin-btn" data-up="${index}" ${index === 0 ? 'disabled' : ''} aria-label="Move up">↑</button>
        <button type="button" class="admin-btn" data-down="${index}" ${index === items.length - 1 ? 'disabled' : ''} aria-label="Move down">↓</button>
      </td>
      <td class="row-actions">
        <button type="button" class="admin-btn" data-edit="${item.id}">Edit</button>
        <button type="button" class="admin-btn admin-btn--danger" data-delete="${item.id}">Delete</button>
      </td>`;
    tbody.appendChild(tr);
  });

  tbody.querySelectorAll('[data-visible]').forEach((box) => box.addEventListener('change', () => {
    runListAction(
      () => apiFetch(`/api/hackathons/${box.dataset.visible}`, { method: 'PUT', body: { is_visible: box.checked } }),
      box.checked ? 'Shown on the site' : 'Hidden from the site',
      loadHackathons
    );
  }));

  tbody.querySelectorAll('[data-up], [data-down]').forEach((btn) => btn.addEventListener('click', () => {
    const from = Number(btn.dataset.up ?? btn.dataset.down);
    const to = btn.dataset.up !== undefined ? from - 1 : from + 1;
    runListAction(() => moveHackathon(from, to), 'Order updated', loadHackathons);
  }));

  tbody.querySelectorAll('[data-edit]').forEach((btn) => btn.addEventListener('click', () => {
    const item = items.find((i) => String(i.id) === btn.dataset.edit);
    openModal('Edit Workshop / Hackathon', HACKATHON_FIELDS, hackathonFormValues(item));
    modalSubmitHandler = async (values) => {
      await apiFetch(`/api/hackathons/${item.id}`, { method: 'PUT', body: buildHackathonPayload(values) });
      showToast('Workshop / hackathon updated');
      loadHackathons();
    };
  }));

  tbody.querySelectorAll('[data-delete]').forEach((btn) => btn.addEventListener('click', () => {
    if (!confirm('Delete this workshop or hackathon? This cannot be undone.')) return;
    runListAction(() => apiFetch(`/api/hackathons/${btn.dataset.delete}`, { method: 'DELETE' }), 'Workshop / hackathon deleted', loadHackathons);
  }));
}

// Swaps one item with its neighbour, then renumbers display_order so the order is always distinct.
async function moveHackathon(from, to) {
  if (to < 0 || to >= hackathonItems.length) return;
  const reordered = hackathonItems.slice();
  const [moved] = reordered.splice(from, 1);
  reordered.splice(to, 0, moved);
  const changes = reordered
    .map((item, position) => ({ item, position }))
    .filter(({ item, position }) => item.display_order !== position);
  for (const { item, position } of changes) {
    await apiFetch(`/api/hackathons/${item.id}`, { method: 'PUT', body: { display_order: position } });
  }
}

function initHackathonCreate() {
  $('#hackathon-new-btn').addEventListener('click', () => {
    openModal('New Workshop / Hackathon', HACKATHON_FIELDS, { type: 'workshop', is_visible: true, display_order: hackathonItems.length });
    modalSubmitHandler = async (values) => {
      await apiFetch('/api/hackathons', { method: 'POST', body: buildHackathonPayload(values) });
      showToast('Workshop / hackathon created');
      loadHackathons();
    };
  });
}

// ---- contact messages ----

async function loadMessages() {
  const messages = await apiFetch('/api/contact');
  const tbody = $('#messages-table tbody');
  tbody.innerHTML = '';
  messages.forEach((msg) => {
    const tr = document.createElement('tr');
    const date = new Date(msg.created_at).toLocaleString();
    tr.innerHTML = `
      <td>${escapeHtml(msg.name)}<br><span style="color:var(--muted);font-size:0.8em">${escapeHtml(msg.email)}</span></td>
      <td>${escapeHtml(msg.subject)}</td>
      <td class="truncate" title="${escapeHtml(msg.message)}">${escapeHtml(msg.message)}</td>
      <td><span class="status-pill status-pill--${msg.status}">${msg.status}</span></td>
      <td>${date}</td>
      <td class="row-actions">
        <select data-status="${msg.id}">
          <option value="unread" ${msg.status === 'unread' ? 'selected' : ''}>Unread</option>
          <option value="read" ${msg.status === 'read' ? 'selected' : ''}>Read</option>
          <option value="replied" ${msg.status === 'replied' ? 'selected' : ''}>Replied</option>
          <option value="archived" ${msg.status === 'archived' ? 'selected' : ''}>Archived</option>
        </select>
        <button type="button" class="admin-btn admin-btn--danger" data-delete="${msg.id}">Delete</button>
      </td>`;
    tbody.appendChild(tr);
  });

  tbody.querySelectorAll('[data-status]').forEach((select) => select.addEventListener('change', () => {
    runListAction(
      () => apiFetch(`/api/contact/${select.dataset.status}`, { method: 'PATCH', body: { status: select.value } }),
      'Message updated', loadMessages
    );
  }));
  tbody.querySelectorAll('[data-delete]').forEach((btn) => btn.addEventListener('click', () => {
    if (!confirm('Delete this message?')) return;
    runListAction(() => apiFetch(`/api/contact/${btn.dataset.delete}`, { method: 'DELETE' }), 'Message deleted', loadMessages);
  }));
}

// ---- boot ----

document.addEventListener('DOMContentLoaded', () => {
  initNav();
  initModal();
  initProjectCreate();
  initCertificateCreate();
  initHackathonCreate();
  initAuth();
});
