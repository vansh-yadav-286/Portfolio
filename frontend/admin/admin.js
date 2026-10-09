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
  const loaders = { overview: loadOverview, projects: loadProjects, certificates: loadCertificates, hackathons: loadHackathons, experience: loadExperiences, messages: loadMessages, analytics: loadAnalytics, reports: loadReportsDefault };
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

let projectItems = [];

async function loadProjects() {
  const projects = await apiFetch('/api/projects', { auth: false });
  projectItems = projects;
  const tbody = $('#projects-table tbody');
  tbody.innerHTML = '';
  projects.forEach((project, index) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${escapeHtml(project.title)}</td>
      <td>${escapeHtml(project.category || '')}</td>
      <td class="truncate">${escapeHtml(project.technologies || '')}</td>
      <td>${project.featured ? 'Yes' : 'No'}</td>
      <td class="row-actions">
        <button type="button" class="admin-btn" data-up="${index}" ${index === 0 ? 'disabled' : ''} aria-label="Move up">↑</button>
        <button type="button" class="admin-btn" data-down="${index}" ${index === projects.length - 1 ? 'disabled' : ''} aria-label="Move down">↓</button>
      </td>
      <td class="row-actions">
        <button type="button" class="admin-btn" data-edit="${project.id}">Edit</button>
        <button type="button" class="admin-btn admin-btn--danger" data-delete="${project.id}">Delete</button>
      </td>`;
    tbody.appendChild(tr);
  });

  tbody.querySelectorAll('[data-up], [data-down]').forEach((btn) => btn.addEventListener('click', () => {
    const from = Number(btn.dataset.up ?? btn.dataset.down);
    const to = btn.dataset.up !== undefined ? from - 1 : from + 1;
    runListAction(() => moveProject(from, to), 'Order updated', loadProjects);
  }));

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

// Swaps one item with its neighbour, then renumbers display_order so the order is always distinct.
async function moveProject(from, to) {
  if (to < 0 || to >= projectItems.length) return;
  const reordered = projectItems.slice();
  const [moved] = reordered.splice(from, 1);
  reordered.splice(to, 0, moved);
  const changes = reordered
    .map((item, position) => ({ item, position }))
    .filter(({ item, position }) => item.display_order !== position);
  for (const { item, position } of changes) {
    await apiFetch(`/api/projects/${item.id}`, { method: 'PUT', body: { display_order: position } });
  }
}

function initProjectCreate() {
  $('#project-new-btn').addEventListener('click', () => {
    openModal('New Project', PROJECT_FIELDS, { technologies: '', featured: false });
    modalSubmitHandler = async (values) => {
      await apiFetch('/api/projects', { method: 'POST', body: { ...values, display_order: projectItems.length } });
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

let certificateItems = [];

async function loadCertificates() {
  const certificates = await apiFetch('/api/certificates', { auth: false });
  certificateItems = certificates;
  const tbody = $('#certificates-table tbody');
  tbody.innerHTML = '';
  certificates.forEach((cert, index) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${escapeHtml(cert.title)}</td>
      <td>${escapeHtml(cert.issuer)}</td>
      <td>${escapeHtml(cert.credential_id || '')}</td>
      <td class="row-actions">
        <button type="button" class="admin-btn" data-up="${index}" ${index === 0 ? 'disabled' : ''} aria-label="Move up">↑</button>
        <button type="button" class="admin-btn" data-down="${index}" ${index === certificates.length - 1 ? 'disabled' : ''} aria-label="Move down">↓</button>
      </td>
      <td class="row-actions">
        <button type="button" class="admin-btn" data-edit="${cert.id}">Edit</button>
        <button type="button" class="admin-btn admin-btn--danger" data-delete="${cert.id}">Delete</button>
      </td>`;
    tbody.appendChild(tr);
  });

  tbody.querySelectorAll('[data-up], [data-down]').forEach((btn) => btn.addEventListener('click', () => {
    const from = Number(btn.dataset.up ?? btn.dataset.down);
    const to = btn.dataset.up !== undefined ? from - 1 : from + 1;
    runListAction(() => moveCertificate(from, to), 'Order updated', loadCertificates);
  }));

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

// Swaps one item with its neighbour, then renumbers display_order so the order is always distinct.
async function moveCertificate(from, to) {
  if (to < 0 || to >= certificateItems.length) return;
  const reordered = certificateItems.slice();
  const [moved] = reordered.splice(from, 1);
  reordered.splice(to, 0, moved);
  const changes = reordered
    .map((item, position) => ({ item, position }))
    .filter(({ item, position }) => item.display_order !== position);
  for (const { item, position } of changes) {
    await apiFetch(`/api/certificates/${item.id}`, { method: 'PUT', body: { display_order: position } });
  }
}

function initCertificateCreate() {
  $('#certificate-new-btn').addEventListener('click', () => {
    openModal('New Certificate', CERTIFICATE_FIELDS, {});
    modalSubmitHandler = async (values) => {
      if (!values.issue_date) values.issue_date = null;
      await apiFetch('/api/certificates', { method: 'POST', body: { ...values, display_order: certificateItems.length } });
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

// ---- experience ----

const EXPERIENCE_FIELDS = [
  { name: 'title', label: 'Title', required: true },
  { name: 'organization', label: 'Organization', required: true },
  { name: 'experience_type', label: 'Type (e.g. Internship, Community Service)', required: true },
  { name: 'start_date', label: 'Start Date', type: 'date' },
  { name: 'end_date', label: 'End Date', type: 'date' },
  { name: 'is_current', label: 'Current / Present', type: 'checkbox' },
  { name: 'description', label: 'Description', type: 'textarea', required: true },
  { name: 'link_url', label: 'Link URL (optional)' },
  { name: 'display_order', label: 'Display order (lower shows first)', type: 'number' }
];

let experienceItems = [];

// Turns the modal's values into the API payload, or throws a message for the form.
function buildExperiencePayload(values) {
  const text = (v) => { const t = String(v ?? '').trim(); return t === '' ? null : t; };
  const required = (name, label, max) => {
    const value = text(values[name]);
    if (!value) throw new Error(`${label} is required.`);
    if (value.length > max) throw new Error(`${label} must be ${max} characters or fewer.`);
    return value;
  };
  const dateOrNull = (name, label) => {
    const value = text(values[name]);
    if (value && !/^\d{4}-\d{2}-\d{2}$/.test(value)) throw new Error(`${label} must be a valid date.`);
    return value;
  };

  const title = required('title', 'Title', 200);
  const organization = required('organization', 'Organization', 200);
  const experienceType = required('experience_type', 'Type', 100);
  const description = required('description', 'Description', 2000);

  const startDate = dateOrNull('start_date', 'Start date');
  const endDate = dateOrNull('end_date', 'End date');
  if (startDate && endDate && endDate < startDate) throw new Error('End date cannot be before the start date.');

  const linkUrl = text(values.link_url);
  if (linkUrl && !isAllowedUrl(linkUrl)) throw new Error('Link must start with https://, http://, or be a relative path.');

  const order = Number(values.display_order === '' || values.display_order == null ? 0 : values.display_order);
  if (!Number.isInteger(order) || order < 0 || order > 100000) throw new Error('Display order must be a whole number from 0 to 100000.');

  return {
    title,
    organization,
    experience_type: experienceType,
    start_date: startDate,
    end_date: endDate,
    is_current: !!values.is_current,
    description,
    link_url: linkUrl,
    display_order: order
  };
}

// Converts an API item into modal values: nulls become empty inputs so no value is lost or shown as "null".
function experienceFormValues(item) {
  return {
    ...item,
    start_date: item.start_date || '',
    end_date: item.end_date || '',
    link_url: item.link_url || '',
    display_order: item.display_order ?? 0
  };
}

async function loadExperiences() {
  const tbody = $('#experience-table tbody');
  tbody.innerHTML = '<tr><td colspan="6" style="color:var(--muted)">Loading…</td></tr>';
  let items;
  try {
    items = await apiFetch('/api/experiences');
  } catch (err) {
    tbody.innerHTML = '';
    const tr = document.createElement('tr');
    tr.innerHTML = `<td colspan="6" class="admin-error">${escapeHtml(err.message)}</td>`;
    tbody.appendChild(tr);
    throw err;
  }
  experienceItems = items;
  tbody.innerHTML = '';
  if (items.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" style="color:var(--muted)">No experience entries yet.</td></tr>';
    return;
  }

  items.forEach((item) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${escapeHtml(item.title)}</td>
      <td>${escapeHtml(item.organization)}</td>
      <td>${escapeHtml(item.experience_type)}</td>
      <td>${item.is_current ? 'Yes' : 'No'}</td>
      <td>${item.display_order}</td>
      <td class="row-actions">
        <button type="button" class="admin-btn" data-edit="${item.id}">Edit</button>
        <button type="button" class="admin-btn admin-btn--danger" data-delete="${item.id}">Delete</button>
      </td>`;
    tbody.appendChild(tr);
  });

  tbody.querySelectorAll('[data-edit]').forEach((btn) => btn.addEventListener('click', () => {
    const item = items.find((i) => String(i.id) === btn.dataset.edit);
    openModal('Edit Experience', EXPERIENCE_FIELDS, experienceFormValues(item));
    modalSubmitHandler = async (values) => {
      await apiFetch(`/api/experiences/${item.id}`, { method: 'PUT', body: buildExperiencePayload(values) });
      showToast('Experience updated');
      loadExperiences();
    };
  }));

  tbody.querySelectorAll('[data-delete]').forEach((btn) => btn.addEventListener('click', () => {
    if (!confirm('Delete this experience entry? This cannot be undone.')) return;
    runListAction(() => apiFetch(`/api/experiences/${btn.dataset.delete}`, { method: 'DELETE' }), 'Experience deleted', loadExperiences);
  }));
}

function initExperienceCreate() {
  $('#experience-new-btn').addEventListener('click', () => {
    openModal('New Experience', EXPERIENCE_FIELDS, { is_current: false, display_order: experienceItems.length });
    modalSubmitHandler = async (values) => {
      await apiFetch('/api/experiences', { method: 'POST', body: buildExperiencePayload(values) });
      showToast('Experience created');
      loadExperiences();
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

// ---- user activity & reports ----

function val(id) {
  const el = document.getElementById(id);
  return el ? el.value.trim() : '';
}

// Dates come from <input type="date"> as "YYYY-MM-DD"; pin them to the start/end
// of that day in UTC so a "to" filter includes the whole day it names.
function dateFromVal(id) {
  const v = val(id);
  return v ? `${v}T00:00:00Z` : '';
}
function dateToVal(id) {
  const v = val(id);
  return v ? `${v}T23:59:59Z` : '';
}

function buildQuery(params) {
  const usp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== '' && v !== undefined && v !== null) usp.set(k, v); });
  return usp.toString();
}

function statusPill(status) {
  return `<span class="status-pill status-pill--${escapeHtml(status)}">${escapeHtml(status)}</span>`;
}

function formatDateTime(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString();
}

function renderPagination(container, { page, pageSize, total, onPageChange }) {
  container.innerHTML = '';
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const prev = document.createElement('button');
  prev.type = 'button'; prev.className = 'admin-btn'; prev.textContent = '← Prev';
  prev.disabled = page <= 1;
  prev.addEventListener('click', () => onPageChange(page - 1));
  const info = document.createElement('span');
  info.textContent = `Page ${page} of ${totalPages} · ${total} total`;
  const next = document.createElement('button');
  next.type = 'button'; next.className = 'admin-btn'; next.textContent = 'Next →';
  next.disabled = page >= totalPages;
  next.addEventListener('click', () => onPageChange(page + 1));
  container.append(prev, info, next);
}

// Downloads a CSV via fetch (not a plain link) because the export endpoint
// needs the admin's bearer token, which a navigable <a href> can't send.
async function exportCsv(report, params) {
  const token = getToken();
  const query = buildQuery({ report, ...params });
  try {
    const res = await fetch(`${API_BASE_URL}/api/admin/reports/export?${query}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    });
    if (!res.ok) {
      let message = `Export failed (HTTP ${res.status})`;
      try { const json = await res.json(); if (json && json.message) message = json.message; } catch (e) { /* non-JSON error body */ }
      throw new Error(message);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${report}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch (err) {
    showToast(err.message || 'Export failed.');
  }
}

function loadReportsDefault() {
  $$('.admin-subnav__link').forEach((b) => b.classList.toggle('is-active', b.dataset.subview === 'reports-overview'));
  $$('[data-subview-panel]').forEach((panel) => { panel.hidden = panel.dataset.subviewPanel !== 'reports-overview'; });
  return loadReportsOverview();
}

function initReportsSubnav() {
  $$('.admin-subnav__link').forEach((btn) => {
    btn.addEventListener('click', () => {
      $$('.admin-subnav__link').forEach((b) => b.classList.remove('is-active'));
      btn.classList.add('is-active');
      $$('[data-subview-panel]').forEach((panel) => { panel.hidden = panel.dataset.subviewPanel !== btn.dataset.subview; });
      loadReportsSubview(btn.dataset.subview);
    });
  });
}

function loadReportsSubview(subview) {
  const loaders = {
    'reports-overview': loadReportsOverview,
    'reports-users': loadReportsUsers,
    'reports-signups': loadReportsSignups,
    'reports-logins': loadReportsLogins,
    'reports-failed': loadReportsFailed,
    'reports-visits': loadReportsVisits,
    'reports-timeline': () => loadReportsTimeline(1)
  };
  const fn = loaders[subview] || (() => Promise.resolve());
  Promise.resolve(fn()).catch((err) => showToast(err.message));
}

// ---- reports: overview ----

function periodDateParams() {
  const period = val('reports-overview-period');
  const params = { period };
  if (period === 'custom') {
    params.date_from = dateFromVal('reports-overview-from');
    params.date_to = dateToVal('reports-overview-to');
  }
  return params;
}

function renderBars(container, breakdown) {
  container.innerHTML = '';
  const max = Math.max(1, ...Object.values(breakdown));
  Object.entries(breakdown).forEach(([label, value]) => {
    const pct = Math.round((value / max) * 100);
    const row = document.createElement('div');
    row.className = 'reports-bar-row';
    row.innerHTML = `
      <span class="reports-bar-row__label">${escapeHtml(label === 'password' ? 'Email/Password' : label)}</span>
      <span class="reports-bar-row__track"><span class="reports-bar-row__fill" style="width:${pct}%"></span></span>
      <span class="reports-bar-row__value">${value}</span>`;
    container.appendChild(row);
  });
}

async function loadReportsOverview() {
  const errEl = $('#reports-overview-error');
  errEl.textContent = '';
  let data;
  try {
    data = await apiFetch(`/api/admin/reports/overview?${buildQuery(periodDateParams())}`);
  } catch (err) {
    errEl.textContent = err.message;
    return;
  }
  renderStatCards($('#reports-overview-stats'), [
    { label: 'Total Registered Users', value: data.total_users },
    { label: 'New Signups Today', value: data.signups_today },
    { label: 'New Signups (7d)', value: data.signups_last_7_days },
    { label: 'New Signups (30d)', value: data.signups_last_30_days },
    { label: 'Successful Logins Today', value: data.logins_success_today },
    { label: 'Failed Logins Today', value: data.logins_failed_today },
    { label: 'Active Sessions (est.)', value: data.active_sessions_estimate },
    { label: 'Total Page Views', value: data.total_page_views },
    { label: 'Unique Visitors Today', value: data.unique_visitors_today },
    { label: 'Total Unique Visitors', value: data.total_unique_visitors },
    { label: `Signups (${data.period.name})`, value: data.period.signups },
    { label: `Logins OK (${data.period.name})`, value: data.period.logins_success },
    { label: `Logins Failed (${data.period.name})`, value: data.period.logins_failed },
    { label: `Page Views (${data.period.name})`, value: data.period.page_views },
    { label: `Unique Visitors (${data.period.name})`, value: data.period.unique_visitors }
  ]);
  renderBars($('#reports-chart-registrations'), data.registrations_by_provider);
  renderBars($('#reports-chart-logins'), data.logins_by_provider);
  $('#reports-overview-note').textContent = data.active_sessions_note;
}

function initReportsOverviewControls() {
  const periodSelect = $('#reports-overview-period');
  periodSelect.addEventListener('change', () => {
    $$('.reports-custom-range').forEach((el) => { el.hidden = periodSelect.value !== 'custom'; });
  });
  $('#reports-overview-apply').addEventListener('click', () => loadReportsOverview().catch((err) => showToast(err.message)));
}

// ---- reports: registered users (+ detail drawer) ----

const reportsUsersState = { page: 1, pageSize: 25, items: [] };

function reportsUsersFilters() {
  return {
    q: val('reports-users-q'),
    provider: val('reports-users-provider'),
    status: val('reports-users-status'),
    verified: val('reports-users-verified'),
    date_from: dateFromVal('reports-users-from'),
    date_to: dateToVal('reports-users-to')
  };
}

async function loadReportsUsers(page = reportsUsersState.page) {
  reportsUsersState.page = page;
  const query = buildQuery({ ...reportsUsersFilters(), page, page_size: reportsUsersState.pageSize });
  const data = await apiFetch(`/api/admin/reports/users?${query}`);
  reportsUsersState.items = data.items;

  const tbody = $('#reports-users-table tbody');
  tbody.innerHTML = '';
  if (data.items.length === 0) {
    tbody.innerHTML = '<tr><td colspan="9" style="color:var(--muted)">No users match these filters.</td></tr>';
  }
  data.items.forEach((u) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><button type="button" class="reports-row-link" data-open-user="${u.id}">${escapeHtml(u.name)}</button></td>
      <td>${escapeHtml(u.email)}</td>
      <td>${formatDateTime(u.created_at)}</td>
      <td>${escapeHtml(u.registration_method)}</td>
      <td>${statusPill(u.is_active ? 'active' : 'disabled')}</td>
      <td>${u.email_verified ? 'Yes' : 'No'}</td>
      <td>${formatDateTime(u.last_login)}</td>
      <td>${u.login_count}</td>
      <td class="row-actions"><button type="button" class="admin-btn" data-open-user="${u.id}">View</button></td>`;
    tbody.appendChild(tr);
  });
  tbody.querySelectorAll('[data-open-user]').forEach((btn) => btn.addEventListener('click', () => {
    const user = reportsUsersState.items.find((u) => u.id === Number(btn.dataset.openUser));
    if (user) openUserDrawer(user);
  }));

  renderPagination($('#reports-users-pagination'), {
    page: data.page, pageSize: data.page_size, total: data.total,
    onPageChange: (p) => loadReportsUsers(p).catch((err) => showToast(err.message))
  });
}

let reportsDrawerUser = null;

function openUserDrawer(user) {
  reportsDrawerUser = user;
  $('#reports-user-drawer-title').textContent = user.name;
  $('#reports-user-drawer-fields').innerHTML = `
    <dt>Email</dt><dd>${escapeHtml(user.email)}</dd>
    <dt>User ID</dt><dd>${user.id}</dd>
    <dt>Registered</dt><dd>${formatDateTime(user.created_at)}</dd>
    <dt>Registration method</dt><dd>${escapeHtml(user.registration_method)}</dd>
    <dt>Email verified</dt><dd>${user.email_verified ? 'Yes' : 'No'}</dd>
    <dt>Account status</dt><dd>${statusPill(user.is_active ? 'active' : 'disabled')}</dd>
    <dt>Last login</dt><dd>${formatDateTime(user.last_login)}</dd>
    <dt>Successful logins</dt><dd>${user.login_count}</dd>
    <dt>Last recorded activity</dt><dd>${formatDateTime(user.last_activity)}</dd>`;
  const toggleBtn = $('#reports-user-drawer-toggle-status');
  toggleBtn.textContent = user.is_active ? 'Disable account' : 'Re-enable account';
  toggleBtn.className = user.is_active ? 'admin-btn admin-btn--danger' : 'admin-btn admin-btn--primary';
  $('#reports-user-drawer').hidden = false;
}

function closeUserDrawer() {
  $('#reports-user-drawer').hidden = true;
  reportsDrawerUser = null;
}

function initUserDrawer() {
  $('#reports-user-drawer-close').addEventListener('click', closeUserDrawer);
  $('#reports-user-drawer').addEventListener('click', (e) => { if (e.target.id === 'reports-user-drawer') closeUserDrawer(); });

  $('#reports-user-drawer-toggle-status').addEventListener('click', async () => {
    if (!reportsDrawerUser) return;
    const newStatus = !reportsDrawerUser.is_active;
    try {
      await apiFetch(`/api/admin/reports/users/${reportsDrawerUser.id}/status`, { method: 'PATCH', body: { is_active: newStatus } });
      showToast(newStatus ? 'Account re-enabled' : 'Account disabled');
      closeUserDrawer();
      loadReportsUsers().catch((err) => showToast(err.message));
    } catch (err) {
      showToast(err.message);
    }
  });

  $('#reports-user-drawer-timeline').addEventListener('click', () => {
    if (!reportsDrawerUser) return;
    const id = reportsDrawerUser.id;
    closeUserDrawer();
    $$('.admin-subnav__link').forEach((b) => b.classList.toggle('is-active', b.dataset.subview === 'reports-timeline'));
    $$('[data-subview-panel]').forEach((panel) => { panel.hidden = panel.dataset.subviewPanel !== 'reports-timeline'; });
    $('#reports-timeline-user-id').value = id;
    loadReportsTimeline(1).catch((err) => showToast(err.message));
  });
}

// ---- reports: signup history ----

const reportsSignupsState = { page: 1, pageSize: 25 };

function reportsSignupsFilters() {
  return {
    method: val('reports-signups-method'),
    status: val('reports-signups-status'),
    q: val('reports-signups-q'),
    date_from: dateFromVal('reports-signups-from'),
    date_to: dateToVal('reports-signups-to')
  };
}

async function loadReportsSignups(page = reportsSignupsState.page) {
  reportsSignupsState.page = page;
  const query = buildQuery({ ...reportsSignupsFilters(), page, page_size: reportsSignupsState.pageSize });
  const data = await apiFetch(`/api/admin/reports/signups?${query}`);
  const tbody = $('#reports-signups-table tbody');
  tbody.innerHTML = '';
  if (data.items.length === 0) tbody.innerHTML = '<tr><td colspan="5" style="color:var(--muted)">No signup events match these filters.</td></tr>';
  data.items.forEach((e) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${formatDateTime(e.created_at)}</td>
      <td>${escapeHtml(e.email || '—')}</td>
      <td>${escapeHtml(e.method)}</td>
      <td>${statusPill(e.status)}</td>
      <td>${escapeHtml(e.reason || '—')}</td>`;
    tbody.appendChild(tr);
  });
  renderPagination($('#reports-signups-pagination'), {
    page: data.page, pageSize: data.page_size, total: data.total,
    onPageChange: (p) => loadReportsSignups(p).catch((err) => showToast(err.message))
  });
}

// ---- reports: login history (logins + logouts) ----

const reportsLoginsState = { page: 1, pageSize: 25 };

function reportsLoginsFilters() {
  return {
    event_type: val('reports-logins-event_type'),
    method: val('reports-logins-method'),
    status: val('reports-logins-status'),
    q: val('reports-logins-q'),
    date_from: dateFromVal('reports-logins-from'),
    date_to: dateToVal('reports-logins-to')
  };
}

async function loadReportsLogins(page = reportsLoginsState.page) {
  reportsLoginsState.page = page;
  const query = buildQuery({ ...reportsLoginsFilters(), page, page_size: reportsLoginsState.pageSize });
  const data = await apiFetch(`/api/admin/reports/auth-events?${query}`);
  const tbody = $('#reports-logins-table tbody');
  tbody.innerHTML = '';
  if (data.items.length === 0) tbody.innerHTML = '<tr><td colspan="7" style="color:var(--muted)">No events match these filters.</td></tr>';
  data.items.forEach((e) => {
    const browserOs = [e.browser, e.os].filter(Boolean).join(' / ') || '—';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${formatDateTime(e.created_at)}</td>
      <td>${escapeHtml(e.email || '—')}</td>
      <td>${escapeHtml(e.event_type)}</td>
      <td>${escapeHtml(e.method)}</td>
      <td>${statusPill(e.status)}</td>
      <td>${escapeHtml(e.reason || '—')}</td>
      <td>${escapeHtml(browserOs)}</td>`;
    tbody.appendChild(tr);
  });
  renderPagination($('#reports-logins-pagination'), {
    page: data.page, pageSize: data.page_size, total: data.total,
    onPageChange: (p) => loadReportsLogins(p).catch((err) => showToast(err.message))
  });
}

// ---- reports: failed login attempts ----

const reportsFailedState = { page: 1, pageSize: 25 };

function reportsFailedFilters() {
  return {
    method: val('reports-failed-method'),
    q: val('reports-failed-q'),
    date_from: dateFromVal('reports-failed-from'),
    date_to: dateToVal('reports-failed-to')
  };
}

async function loadReportsFailed(page = reportsFailedState.page) {
  reportsFailedState.page = page;
  const query = buildQuery({ ...reportsFailedFilters(), page, page_size: reportsFailedState.pageSize });
  const data = await apiFetch(`/api/admin/reports/failed-logins?${query}`);
  const tbody = $('#reports-failed-table tbody');
  tbody.innerHTML = '';
  if (data.items.length === 0) tbody.innerHTML = '<tr><td colspan="5" style="color:var(--muted)">No failed login attempts match these filters.</td></tr>';
  data.items.forEach((e) => {
    const browserOs = [e.browser, e.os].filter(Boolean).join(' / ') || '—';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${formatDateTime(e.created_at)}</td>
      <td>${escapeHtml(e.email || '—')}</td>
      <td>${escapeHtml(e.method)}</td>
      <td>${escapeHtml(e.reason || '—')}</td>
      <td>${escapeHtml(browserOs)}</td>`;
    tbody.appendChild(tr);
  });
  renderPagination($('#reports-failed-pagination'), {
    page: data.page, pageSize: data.page_size, total: data.total,
    onPageChange: (p) => loadReportsFailed(p).catch((err) => showToast(err.message))
  });
}

// ---- reports: visitor analytics ----

const reportsVisitsState = { page: 1, pageSize: 25 };

function reportsVisitsFilters() {
  return {
    page_filter: val('reports-visits-page_filter'),
    session_id: val('reports-visits-session_id'),
    date_from: dateFromVal('reports-visits-from'),
    date_to: dateToVal('reports-visits-to')
  };
}

async function loadReportsVisits(page = reportsVisitsState.page) {
  reportsVisitsState.page = page;
  const query = buildQuery({ ...reportsVisitsFilters(), page, page_size: reportsVisitsState.pageSize });
  const data = await apiFetch(`/api/admin/reports/visits?${query}`);
  const tbody = $('#reports-visits-table tbody');
  tbody.innerHTML = '';
  if (data.items.length === 0) tbody.innerHTML = '<tr><td colspan="5" style="color:var(--muted)">No visits match these filters.</td></tr>';
  data.items.forEach((v) => {
    const browserOs = [v.browser, v.os].filter(Boolean).join(' / ') || '—';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${formatDateTime(v.visited_at)}</td>
      <td class="truncate" title="${escapeHtml(v.page)}">${escapeHtml(v.page)}</td>
      <td class="truncate" title="${escapeHtml(v.referrer || '')}">${escapeHtml(v.referrer || '—')}</td>
      <td>${escapeHtml(browserOs)}</td>
      <td>${v.is_returning_visit ? 'Yes' : 'No'}</td>`;
    tbody.appendChild(tr);
  });
  renderPagination($('#reports-visits-pagination'), {
    page: data.page, pageSize: data.page_size, total: data.total,
    onPageChange: (p) => loadReportsVisits(p).catch((err) => showToast(err.message))
  });
}

// ---- reports: user activity timeline ----

const reportsTimelineState = { page: 1, pageSize: 25 };

function reportsTimelineFilters() {
  return {
    event_type: val('reports-timeline-event_type'),
    date_from: dateFromVal('reports-timeline-from'),
    date_to: dateToVal('reports-timeline-to')
  };
}

function describeTimelineEvent(e) {
  const methodLabel = e.method === 'password' ? 'email/password' : e.method;
  if (e.event_type === 'account_created') return `Account created via ${methodLabel}`;
  if (e.event_type === 'signup') return `Signed up via ${methodLabel} (${e.status})`;
  if (e.event_type === 'login') return `Logged in via ${methodLabel} (${e.status}${e.reason ? ', ' + e.reason : ''})`;
  if (e.event_type === 'logout') return `Logged out (${methodLabel})`;
  return `${e.event_type} (${e.status})`;
}

async function loadReportsTimeline(page = reportsTimelineState.page) {
  const userId = val('reports-timeline-user-id');
  const header = $('#reports-timeline-header');
  const list = $('#reports-timeline-list');
  if (!userId) {
    header.innerHTML = '';
    list.innerHTML = '<li class="reports-note">Enter a user ID above, or open a user from Registered Users.</li>';
    $('#reports-timeline-pagination').innerHTML = '';
    return;
  }
  reportsTimelineState.page = page;
  const query = buildQuery({ ...reportsTimelineFilters(), page, page_size: reportsTimelineState.pageSize });
  let data;
  try {
    data = await apiFetch(`/api/admin/reports/users/${userId}/activity?${query}`);
  } catch (err) {
    header.innerHTML = `<p class="admin-error">${escapeHtml(err.message)}</p>`;
    list.innerHTML = '';
    $('#reports-timeline-pagination').innerHTML = '';
    return;
  }
  header.innerHTML = `<h3>${escapeHtml(data.user.name)} <span style="color:var(--muted);font-size:0.8em">${escapeHtml(data.user.email)}</span></h3>`;
  list.innerHTML = '';
  if (data.items.length === 0) {
    list.innerHTML = `<li class="reports-note">${escapeHtml(data.note || 'No activity recorded.')}</li>`;
  }
  data.items.forEach((e) => {
    const li = document.createElement('li');
    li.className = 'reports-timeline__item';
    const dotClass = e.status === 'failure' ? 'reports-timeline__dot--failure' : 'reports-timeline__dot--success';
    li.innerHTML = `
      <span class="reports-timeline__dot ${dotClass}"></span>
      <span>
        <div>${escapeHtml(describeTimelineEvent(e))}</div>
        <div class="reports-timeline__time">${formatDateTime(e.created_at)}</div>
      </span>`;
    list.appendChild(li);
  });
  renderPagination($('#reports-timeline-pagination'), {
    page, pageSize: reportsTimelineState.pageSize, total: data.total,
    onPageChange: (p) => loadReportsTimeline(p).catch((err) => showToast(err.message))
  });
}

function initReportsControls() {
  initReportsOverviewControls();

  $('#reports-users-apply').addEventListener('click', () => loadReportsUsers(1).catch((err) => showToast(err.message)));
  $('#reports-users-export').addEventListener('click', () => exportCsv('users', reportsUsersFilters()));

  $('#reports-signups-apply').addEventListener('click', () => loadReportsSignups(1).catch((err) => showToast(err.message)));
  $('#reports-signups-export').addEventListener('click', () => exportCsv('signups', reportsSignupsFilters()));

  $('#reports-logins-apply').addEventListener('click', () => loadReportsLogins(1).catch((err) => showToast(err.message)));
  $('#reports-logins-export').addEventListener('click', () => exportCsv('auth-events', reportsLoginsFilters()));

  $('#reports-failed-apply').addEventListener('click', () => loadReportsFailed(1).catch((err) => showToast(err.message)));
  $('#reports-failed-export').addEventListener('click', () => exportCsv('failed-logins', reportsFailedFilters()));

  $('#reports-visits-apply').addEventListener('click', () => loadReportsVisits(1).catch((err) => showToast(err.message)));
  $('#reports-visits-export').addEventListener('click', () => exportCsv('visits', reportsVisitsFilters()));

  $('#reports-timeline-load').addEventListener('click', () => loadReportsTimeline(1).catch((err) => showToast(err.message)));

  initUserDrawer();
}

// ---- boot ----

document.addEventListener('DOMContentLoaded', () => {
  initNav();
  initModal();
  initProjectCreate();
  initCertificateCreate();
  initHackathonCreate();
  initExperienceCreate();
  initReportsSubnav();
  initReportsControls();
  initAuth();
});
