'use strict';

// Single source of truth for the backend API origin. Every fetch() in
// script.js and admin/admin.js reads this instead of hardcoding a URL.
//
// Development: FastAPI running locally (`uvicorn app.main:app --reload`).
// Production:  the backend's Render URL. This is a plain static site (no
// build step), so there's no env-var injection at build time - update this
// one line after deploying the backend to Render.
const API_BASE_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? 'http://localhost:8000'
  : 'https://portfolio-api-xxxx.onrender.com';