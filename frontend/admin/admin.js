'use strict';

const TOKEN_KEY = 'portfolioAdminToken';

function $(sel, ctx = document) { return ctx.querySelector(sel); }
function $$(sel, ctx = document) { return Array.from(ctx.querySelectorAll(sel)); }

function getToken() { return localStorage.getItem(TOKEN_KEY); }
function setToken(token) { localStorage.setItem(TOKEN_KEY, token); }
function clearToken() { localStorage.removeItem(TOKEN_KEY); }

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
  const loaders = { overview: loadOverview, projects: loadProjects, certificates: loadCertificates, messages: loadMessages, analytics: loadAnalytics };
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
    $$('input, textarea', form).forEach((input) => {
      values[input.name] = input.type === 'checkbox' ? input.checked : input.value;
    });
    try {
      await modalSubmitHandler(values);
      closeModal();
    } catch (err) {
      $('#admin-modal-error').textContent = err.message || 'Something went wrong.';
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
  tbody.querySelectorAll('[data-delete]').forEach((btn) => btn.addEventListener('click', async () => {
    if (!confirm('Delete this project?')) return;
    await apiFetch(`/api/projects/${btn.dataset.delete}`, { method: 'DELETE' });
    showToast('Project deleted');
    loadProjects();
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
  tbody.querySelectorAll('[data-delete]').forEach((btn) => btn.addEventListener('click', async () => {
    if (!confirm('Delete this certificate?')) return;
    await apiFetch(`/api/certificates/${btn.dataset.delete}`, { method: 'DELETE' });
    showToast('Certificate deleted');
    loadCertificates();
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

  tbody.querySelectorAll('[data-status]').forEach((select) => select.addEventListener('change', async () => {
    await apiFetch(`/api/contact/${select.dataset.status}`, { method: 'PATCH', body: { status: select.value } });
    showToast('Message updated');
    loadMessages();
  }));
  tbody.querySelectorAll('[data-delete]').forEach((btn) => btn.addEventListener('click', async () => {
    if (!confirm('Delete this message?')) return;
    await apiFetch(`/api/contact/${btn.dataset.delete}`, { method: 'DELETE' });
    showToast('Message deleted');
    loadMessages();
  }));
}

// ---- boot ----

document.addEventListener('DOMContentLoaded', () => {
  initNav();
  initModal();
  initProjectCreate();
  initCertificateCreate();
  initAuth();
});
