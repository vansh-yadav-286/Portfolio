'use strict';

// TODO: pull this into a config.json at some point so it's not hardcoded
const CONFIG = {
  name: 'Vansh Yadav',
  email: 'vanshyadavy286@gmail.com',
  linkedin: 'https://www.linkedin.com/in/vanshyadav286/',
  github: 'https://github.com/vansh-yadav-286',
  githubUsername: 'vansh-yadav-286',
  githubCacheTTL: 60 * 60 * 1000, // 1hr cache, see initGithubStats
  roles: [
    'GenAI Engineer',
    'AI Engineer',
    'Prompt Engineer',
    'Python Developer',
    'Cloud & AI Enthusiast'
  ]
};

// wrapper around localStorage so things don't blow up in private
// browsing / safari weirdness. falls back to an in-memory object
const safeStorage = (() => {
  const memoryFallback = {};
  let available = false;
  try {
    const testKey = '__shorya_os_test__';
    window.localStorage.setItem(testKey, '1');
    window.localStorage.removeItem(testKey);
    available = true;
  } catch (e) {
    available = false;
  }

  return {
    get(key) {
      try {
        return available ? window.localStorage.getItem(key) : (memoryFallback[key] ?? null);
      } catch (e) {
        return memoryFallback[key] ?? null;
      }
    },
    set(key, value) {
      try {
        if (available) window.localStorage.setItem(key, value);
        else memoryFallback[key] = value;
      } catch (e) {
        memoryFallback[key] = value;
      }
    }
  };
})();

// certs data - add new ones here, cards render automatically
const certificates = [
  { title: 'Azure Fundamentals', tag: 'Microsoft', logo: 'Logo/Microsoft Logo.jpg', pdf: 'Certification/Azure Fundamental(Az-900).pdf' },
  { title: 'Azure AI Fundamentals', tag: 'Microsoft', logo: 'Logo/Microsoft Logo.jpg', pdf: 'Certification/Ai-900-Certificate.pdf' },
  { title: 'AI Fundamentals', tag: 'IBM', logo: 'Logo/Ibm Logo.jpg', pdf: 'Certification/Artificial Intelligence Fundamentals(IBM).pdf' },
  { title: 'Oracle Cloud Infrastructure AI Foundations Associate', tag: 'OCI', logo: 'Logo/Oracle Logo.jpg', pdf: 'Certification/oracle.pdf' },
  { title: 'Gen AI Engineering Mastermind', tag: 'Outskill', logo: 'Logo/Outskill Logo.jpg', pdf: 'Certification/Outskill_Certificate.pdf' },
  { title: 'Web Development Fundamental', tag: 'IBM', logo: 'Logo/Ibm Logo.jpg', pdf: 'Certification/Web Devlopment Fundamental.pdf' },
  { title: 'Enterprise Design Thinking Practitioner', tag: 'IBM', logo: 'Logo/Ibm Logo.jpg', pdf: 'Certification/EnterpriseDesignThinkingPractitioner.pdf' },
  { title: 'Prompt Engineering', tag: 'IBM', logo: 'Logo/Ibm Logo.jpg', pdf: 'Certification/IBM Prompt Engineering Certificate.pdf' },
  { title: 'Python (Basic) — HackerRank', tag: 'HackerRank', logo: 'Logo/HackerRank Logo.jpg', pdf: 'Certification/python_basic certificate.pdf' },
];

const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const isCoarsePointer = window.matchMedia('(pointer: coarse)').matches;

// ---- small helpers used all over the file ----

function $(sel, ctx = document) { return ctx.querySelector(sel); }
function $$(sel, ctx = document) { return Array.from(ctx.querySelectorAll(sel)); }
function clamp(n, min, max) { return Math.max(min, Math.min(max, n)); }
function lerp(a, b, t) { return a + (b - a) * t; }
function wait(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }

function debounce(fn, ms) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

function showToast(message) {
  const container = $('#toast-container');
  if (!container) return;
  const el = document.createElement('div');
  el.className = 'toast';
  el.textContent = message;
  container.appendChild(el);
  el.addEventListener('animationend', (e) => { if (e.animationName === 'toast-out') el.remove(); });
}

function scrollToSection(id) {
  const target = $(id);
  const navbar = $('#navbar');
  if (!target || !navbar) return;
  const top = target.getBoundingClientRect().top + window.scrollY - navbar.offsetHeight - 16;
  window.scrollTo({ top, behavior: prefersReducedMotion ? 'auto' : 'smooth' });
}

// ---- boot sequence (the fake terminal intro) ----

function typeLine(container, text, speed) {
  return new Promise((resolve) => {
    const p = document.createElement('p');
    container.appendChild(p);
    if (prefersReducedMotion || speed === 0) {
      p.textContent = text;
      resolve();
      return;
    }
    let i = 0;
    const timer = setInterval(() => {
      p.textContent = text.slice(0, i + 1);
      i++;
      if (i >= text.length) { clearInterval(timer); resolve(); }
    }, speed);
  });
}

function setPageInert(isInert) {
  $$('body > *').forEach((el) => {
    if (el.id === 'boot-screen') return;
    if ('inert' in el) el.inert = isInert;
    else el.setAttribute('aria-hidden', isInert ? 'true' : 'false');
  });
}

async function runBootSequence() {
  const screen = $('#boot-screen');
  const logEl = $('#boot-log');
  const bar = $('#boot-progress-bar');
  const percentEl = $('#boot-percent');
  const skipBtn = $('#boot-skip');
  if (!screen) return;

  setPageInert(true);

  if (prefersReducedMotion) {
    screen.style.display = 'none';
    setPageInert(false);
    return;
  }

  let skipped = false;
  const skip = () => { skipped = true; };
  if (skipBtn) {
    skipBtn.hidden = false;
    skipBtn.addEventListener('click', skip);
  }
  screen.addEventListener('click', skip);
  window.addEventListener('keydown', skip, { once: true });

  const lines = [
    'Initializing neural core...',
    'Loading language models...',
    'Establishing cloud uplink :: AZURE OK :: OCI OK',
    'Mounting skill modules :: PYTHON :: JAVASCRIPT :: C',
    'Compiling portfolio matrix...',
    'Booting desktop environment...'
  ];

  for (let i = 0; i < lines.length; i++) {
    if (skipped) break;
    await typeLine(logEl, lines[i], 14);
    const pct = Math.round(((i + 1) / lines.length) * 100);
    if (bar) bar.style.width = pct + '%';
    if (percentEl) percentEl.textContent = pct + '%';
    if (!skipped) await wait(120);
  }
  if (!skipped) await wait(300);

  screen.classList.add('is-hidden');
  setPageInert(false);
  setTimeout(() => { screen.style.display = 'none'; }, 700);
}

function initBootRain() {
  const canvas = $('#boot-rain-canvas');
  if (!canvas || prefersReducedMotion) return;
  const ctx = canvas.getContext('2d');
  let w = canvas.width = window.innerWidth;
  let h = canvas.height = window.innerHeight;
  const fontSize = 15;
  let columns = Math.floor(w / fontSize);
  let drops = Array.from({ length: columns }, () => Math.random() * -100);
  const chars = '01AI∑πλ{}<>/';

  const handleResize = debounce(() => {
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
    columns = Math.floor(w / fontSize);
    drops = Array.from({ length: columns }, () => Math.random() * -100);
  }, 150);
  window.addEventListener('resize', handleResize);

  function draw() {
    const boot = $('#boot-screen');
    if (!boot || boot.classList.contains('is-hidden')) return; // stop once boot screen is gone, no point burning cycles

    ctx.fillStyle = 'rgba(6, 8, 20, 0.16)';
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = 'rgba(76, 201, 240, 0.5)';
    ctx.font = fontSize + 'px monospace';
    drops.forEach((y, i) => {
      const char = chars[Math.floor(Math.random() * chars.length)];
      ctx.fillText(char, i * fontSize, y * fontSize);
      if (y * fontSize > h && Math.random() > 0.975) drops[i] = 0;
      else drops[i] += 0.6;
    });
    requestAnimationFrame(draw);
  }
  requestAnimationFrame(draw);
}

// ---- custom cursor, only on devices with a real mouse ----
function initCursor() {
  if (isCoarsePointer || prefersReducedMotion) return;
  const dot = $('#cursor-dot'), ring = $('#cursor-ring'), glow = $('#cursor-glow');
  if (!dot || !ring || !glow) return;
  document.documentElement.classList.add('custom-cursor');
  let mx = innerWidth / 2, my = innerHeight / 2, rx = mx, ry = my, gx = mx, gy = my;

  window.addEventListener('mousemove', (e) => {
    mx = e.clientX; my = e.clientY;
    dot.style.transform = `translate(${mx}px, ${my}px)`;
  });

  (function raf() {
    rx = lerp(rx, mx, 0.22); ry = lerp(ry, my, 0.22);
    gx = lerp(gx, mx, 0.09); gy = lerp(gy, my, 0.09);
    ring.style.transform = `translate(${rx}px, ${ry}px)`;
    glow.style.transform = `translate(${gx}px, ${gy}px)`;
    requestAnimationFrame(raf);
  })();

  const hoverSelector = 'a, button, .tilt, input, textarea, .chip';
  document.addEventListener('mouseover', (e) => { if (e.target.closest(hoverSelector)) document.documentElement.classList.add('cursor-hover'); });
  document.addEventListener('mouseout', (e) => { if (e.target.closest(hoverSelector)) document.documentElement.classList.remove('cursor-hover'); });
}

function initScrollChrome() {
  const progress = $('#scroll-progress');
  const navbar = $('#navbar');
  const backToTop = $('#back-to-top');
  if (!progress || !navbar || !backToTop) return;

  function onScroll() {
    const scrollTop = window.scrollY;
    const max = document.documentElement.scrollHeight - window.innerHeight;
    const pct = max > 0 ? (scrollTop / max) * 100 : 0;
    progress.style.width = pct + '%';
    progress.setAttribute('aria-valuenow', String(Math.round(pct)));
    navbar.classList.toggle('is-scrolled', scrollTop > 12);
    backToTop.classList.toggle('is-visible', scrollTop > 600);
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  backToTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: prefersReducedMotion ? 'auto' : 'smooth' }));
}

function initClock() {
  const el = $('#nav-clock');
  if (!el) return;
  const tick = () => { el.textContent = new Date().toLocaleTimeString('en-GB', { hour12: false }); };
  tick();
  setInterval(tick, 1000);
}

function initNav() {
  const toggle = $('#mobile-nav-toggle');
  const mobileNav = $('#mobile-nav');
  if (!toggle || !mobileNav) return;

  toggle.addEventListener('click', () => {
    const willOpen = !mobileNav.classList.contains('is-open');
    mobileNav.classList.toggle('is-open', willOpen);
    mobileNav.hidden = !willOpen;
    toggle.setAttribute('aria-expanded', String(willOpen));
  });

  $$('a[href^="#"]').forEach((link) => {
    link.addEventListener('click', (e) => {
      const id = link.getAttribute('href');
      if (!id || id.length < 2 || !$(id)) return;
      e.preventDefault();
      scrollToSection(id);
      if (mobileNav.classList.contains('is-open')) {
        mobileNav.classList.remove('is-open');
        mobileNav.hidden = true;
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  });

  $$('.hero__scroll-hint').forEach((btn) => {
    btn.addEventListener('click', () => scrollToSection(btn.dataset.scrollTarget));
  });
}

function initScrollReveal() {
  const items = $$('.reveal');
  if (prefersReducedMotion || !('IntersectionObserver' in window)) {
    items.forEach((el) => el.classList.add('is-visible'));
    return;
  }
  const io = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15, rootMargin: '0px 0px -60px 0px' });
  items.forEach((el) => io.observe(el));
}

// pauses the orbiting skills rings when scrolled out of view - no reason
// to keep those animations running in the background, was tanking battery
// on my phone when I left the tab open
function initOrbitPause() {
  const orbitSystem = $('#orbit-system');
  if (!orbitSystem || prefersReducedMotion || !('IntersectionObserver' in window)) return;
  const io = new IntersectionObserver(([entry]) => {
    orbitSystem.style.setProperty('--play-state', entry.isIntersecting ? 'running' : 'paused');
  }, { threshold: 0 });
  io.observe(orbitSystem);
}

function initTilt() {
  if (isCoarsePointer || prefersReducedMotion) return;
  $$('.tilt').forEach((card) => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const px = (e.clientX - rect.left) / rect.width;
      const py = (e.clientY - rect.top) / rect.height;
      const rotateX = (0.5 - py) * 10;
      const rotateY = (px - 0.5) * 10;
      card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-4px)`;
      card.style.setProperty('--mx', `${px * 100}%`);
      card.style.setProperty('--my', `${py * 100}%`);
    });
    card.addEventListener('mouseleave', () => { card.style.transform = ''; });
  });
}

function initMagnetic() {
  if (isCoarsePointer || prefersReducedMotion) return;
  $$('.btn').forEach((btn) => {
    btn.addEventListener('mousemove', (e) => {
      const rect = btn.getBoundingClientRect();
      const mx = e.clientX - (rect.left + rect.width / 2);
      const my = e.clientY - (rect.top + rect.height / 2);
      btn.style.transform = `translate(${mx * 0.25}px, ${my * 0.25}px)`;
    });
    btn.addEventListener('mouseleave', () => { btn.style.transform = ''; });
  });
}

function initParallax() {
  if (isCoarsePointer || prefersReducedMotion) return;
  const hero = $('#hero'), inner = $('.hero__inner');
  if (!hero || !inner) return;
  hero.addEventListener('mousemove', (e) => {
    const rect = hero.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width - 0.5;
    const py = (e.clientY - rect.top) / rect.height - 0.5;
    inner.style.transform = `translate(${px * -14}px, ${py * -10}px)`;
  });
  hero.addEventListener('mouseleave', () => { inner.style.transform = ''; });
}

function initRipple() {
  $$('.btn, .filter-btn, .contact-link, .nav__icon-btn').forEach((el) => {
    el.addEventListener('click', (e) => {
      if (prefersReducedMotion) return;
      const rect = el.getBoundingClientRect();
      if (!el.style.position) el.style.position = 'relative';
      if (!el.style.overflow) el.style.overflow = 'hidden';
      const ripple = document.createElement('span');
      ripple.className = 'ripple';
      const size = Math.max(rect.width, rect.height);
      ripple.style.width = ripple.style.height = size + 'px';
      ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
      ripple.style.top = (e.clientY - rect.top - size / 2) + 'px';
      el.appendChild(ripple);
      ripple.addEventListener('animationend', () => ripple.remove());
    });
  });
}

function initNeuralCanvas() {
  const canvas = $('#neural-canvas');
  const hero = $('#hero');
  if (!canvas || !hero) return;
  const ctx = canvas.getContext('2d');
  let w, h, nodes = [];
  const mouse = { x: -9999, y: -9999 };
  let running = true;

  function resize() {
    w = canvas.width = hero.offsetWidth;
    h = canvas.height = hero.offsetHeight;
    const count = prefersReducedMotion ? 0 : clamp(Math.floor((w * h) / 18000), 24, 90);
    nodes = Array.from({ length: count }, () => ({
      x: Math.random() * w, y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.35, vy: (Math.random() - 0.5) * 0.35
    }));
  }
  resize();
  window.addEventListener('resize', debounce(resize, 150));
  hero.addEventListener('mousemove', (e) => {
    const rect = canvas.getBoundingClientRect();
    mouse.x = e.clientX - rect.left; mouse.y = e.clientY - rect.top;
  });
  hero.addEventListener('mouseleave', () => { mouse.x = -9999; mouse.y = -9999; });

  function draw() {
    if (running && !prefersReducedMotion) {
      ctx.clearRect(0, 0, w, h);
      nodes.forEach((n) => {
        n.x += n.vx; n.y += n.vy;
        if (n.x < 0 || n.x > w) n.vx *= -1;
        if (n.y < 0 || n.y > h) n.vy *= -1;
        const dx = n.x - mouse.x, dy = n.y - mouse.y;
        if (Math.sqrt(dx * dx + dy * dy) < 140) { n.x += dx * 0.002; n.y += dy * 0.002; }
      });
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x, dy = nodes[i].y - nodes[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 130) {
            ctx.strokeStyle = `rgba(76, 201, 240, ${(1 - dist / 130) * 0.35})`;
            ctx.lineWidth = 1;
            ctx.beginPath(); ctx.moveTo(nodes[i].x, nodes[i].y); ctx.lineTo(nodes[j].x, nodes[j].y); ctx.stroke();
          }
        }
        ctx.fillStyle = 'rgba(76, 201, 240, 0.8)';
        ctx.beginPath(); ctx.arc(nodes[i].x, nodes[i].y, 1.6, 0, Math.PI * 2); ctx.fill();
      }
    }
    requestAnimationFrame(draw);
  }
  requestAnimationFrame(draw);
  document.addEventListener('visibilitychange', () => { running = !document.hidden; });
}

function typeText(el, text, speed) {
  return new Promise((resolve) => {
    let i = 0;
    const timer = setInterval(() => {
      el.textContent = text.slice(0, i + 1); i++;
      if (i >= text.length) { clearInterval(timer); resolve(); }
    }, speed);
  });
}
function eraseText(el, speed) {
  return new Promise((resolve) => {
    const timer = setInterval(() => {
      el.textContent = el.textContent.slice(0, -1);
      if (el.textContent.length === 0) { clearInterval(timer); resolve(); }
    }, speed);
  });
}
async function initRoleTypewriter() {
  const el = $('#hero-role');
  if (!el) return;
  if (prefersReducedMotion) { el.textContent = CONFIG.roles[0]; return; }
  let i = 0;
  // yeah this is an infinite loop, it's fine - it's just cycling text
  while (true) {
    await typeText(el, CONFIG.roles[i % CONFIG.roles.length], 55);
    await wait(1400);
    await eraseText(el, 28);
    await wait(300);
    i++;
  }
}

// fake terminal in the About section. not a real shell obviously,
// just pattern matching on a handful of commands
function initTerminal() {
  const input = $('#terminal-input');
  const output = $('#terminal-output');
  if (!input || !output) return;

  const commands = {
    help: () => 'Available: whoami, skills, projects, education, hackathons, contact, clear, help',
    whoami: () => `${CONFIG.name} — GenAI Engineer & B.Tech CSE (Generative AI) student at Lovely Professional University.`,
    skills: () => 'Python · JavaScript · C · Generative AI · Prompt Engineering · LLMs · AI Agents · Azure · OCI',
    projects: () => 'Innovative AI · AI Concierge for ET · SplitterEase · Railway Reservation System · Laptop Recovery System — see the Projects section.',
    education: () => 'B.Tech CSE, Generative AI specialization — Lovely Professional University, 2025–2029.',
    hackathons: () => 'ET AI Hackathon · E-Cell IIT Roorkee · ByteXL GenAI Workshop.',
    contact: () => `Email ${CONFIG.email} — full links are in the Contact section below.`,
    clear: () => { output.innerHTML = ''; return null; }
  };

  function print(text, cls) {
    const p = document.createElement('p');
    if (cls) p.className = cls;
    p.textContent = text;
    output.appendChild(p);
  }

  input.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter') return;
    const raw = input.value.trim();
    if (!raw) return;
    print(raw, 't-cmd');
    const lower = raw.toLowerCase();
    if (lower.startsWith('sudo')) {
      // little easter egg, someone always tries sudo
      print('Nice try — guest is not in the sudoers file. This incident will be reported to nobody.', 't-accent');
    } else if (commands[lower]) {
      const result = commands[lower]();
      if (result) print(result, 't-accent');
    } else {
      print(`command not found: ${raw} — type "help"`, 't-accent');
    }
    input.value = '';
    output.scrollTop = output.scrollHeight;
  });
}

// live-ish github stats. hits the unauthenticated API so it's rate
// limited to 60/hr - caching keeps it from getting hammered on repeat
// visits or when I'm demoing this on the same wifi as other people
async function initGithubStats() {
  const username = CONFIG.githubUsername;
  const reposEl = $('#gh-repos'), followersEl = $('#gh-followers'), starsEl = $('#gh-stars');
  const langsEl = $('#gh-langs'), errorEl = $('#gh-error'), avatarEl = $('#gh-avatar');
  const usernameEl = $('#gh-username'), linkEl = $('#gh-profile-link');
  if (!usernameEl || !linkEl) return;
  usernameEl.textContent = '@' + username;
  linkEl.href = CONFIG.github;

  function render(data) {
    reposEl.textContent = data.publicRepos ?? '—';
    followersEl.textContent = data.followers ?? '—';
    starsEl.textContent = data.stars ?? '—';
    if (data.avatarUrl) { avatarEl.src = data.avatarUrl; avatarEl.alt = username; avatarEl.hidden = false; }

    langsEl.innerHTML = '';
    if (!data.languages.length) {
      const p = document.createElement('p');
      p.className = 'gh-error';
      p.textContent = 'No public repositories with a detected language yet.';
      langsEl.appendChild(p);
      return;
    }
    const max = data.languages[0][1];
    data.languages.forEach(([lang, count]) => {
      const row = document.createElement('div'); row.className = 'gh-lang-row';
      const nameEl = document.createElement('span'); nameEl.textContent = lang;
      const track = document.createElement('span'); track.className = 'gh-lang-track';
      const fill = document.createElement('span'); fill.className = 'gh-lang-fill';
      track.appendChild(fill);
      const countEl = document.createElement('span'); countEl.textContent = String(count);
      row.append(nameEl, track, countEl);
      langsEl.appendChild(row);
      requestAnimationFrame(() => { fill.style.width = ((count / max) * 100) + '%'; });
    });
  }

  const cacheKey = `gh-stats-cache:${username}`;
  try {
    const cached = JSON.parse(safeStorage.get(cacheKey) || 'null');
    if (cached && Date.now() - cached.fetchedAt < CONFIG.githubCacheTTL) {
      render(cached.data);
      return;
    }
  } catch (e) {
    // corrupt cache entry, whatever - just fetch fresh
  }

  try {
    const timeoutSignal = () => (typeof AbortSignal.timeout === 'function' ? AbortSignal.timeout(6000) : undefined);

    const [userRes, reposRes] = await Promise.all([
      fetch(`https://api.github.com/users/${username}`, { signal: timeoutSignal() }),
      fetch(`https://api.github.com/users/${username}/repos?per_page=100&sort=updated`, { signal: timeoutSignal() })
    ]);
    if (!userRes.ok) throw new Error('user fetch failed');
    if (!reposRes.ok) throw new Error('repos fetch failed');

    const user = await userRes.json();
    const repos = await reposRes.json();
    if (!Array.isArray(repos)) throw new Error('unexpected repos payload');

    const langCount = {};
    repos.forEach((r) => { if (r.language) langCount[r.language] = (langCount[r.language] || 0) + 1; });
    const languages = Object.entries(langCount).sort((a, b) => b[1] - a[1]).slice(0, 5);

    const data = {
      publicRepos: user.public_repos ?? null,
      followers: user.followers ?? null,
      stars: repos.reduce((sum, r) => sum + (r.stargazers_count || 0), 0),
      avatarUrl: user.avatar_url || null,
      languages
    };

    safeStorage.set(cacheKey, JSON.stringify({ fetchedAt: Date.now(), data }));
    render(data);
  } catch (err) {
    errorEl.hidden = false;
    [reposEl, followersEl, starsEl].forEach((el) => { el.textContent = '—'; });
  }
}

function initHackathonAccordion() {
  const toggle = $('#ecell-toggle');
  const panel = $('#ecell-panel');
  if (!toggle || !panel) return;

  $$('.hackathon-card--sub', panel).forEach((card, i) => {
    card.style.setProperty('--sub-stagger', String(i));
  });

  // same inert/aria-hidden trick as the boot screen above
  function setInert(el, isInert) {
    if ('inert' in el) el.inert = isInert;
    el.setAttribute('aria-hidden', String(isInert));
  }

  let open = false;
  setInert(panel, true);

  function setOpen(next) {
    open = next;
    toggle.setAttribute('aria-expanded', String(open));
    toggle.classList.toggle('is-open', open);
    panel.classList.toggle('is-open', open);
    setInert(panel, !open);

    if (prefersReducedMotion) {
      panel.style.maxHeight = open ? 'none' : '0px';
      return;
    }

    if (open) {
      panel.style.maxHeight = panel.scrollHeight + 'px';
    } else {
      // can't transition max-height from "none", so snap to the real
      // height first then collapse it on the next frame
      panel.style.maxHeight = panel.scrollHeight + 'px';
      requestAnimationFrame(() => { panel.style.maxHeight = '0px'; });
    }
  }

  toggle.addEventListener('click', () => setOpen(!open));

  window.addEventListener('resize', debounce(() => {
    if (open) panel.style.maxHeight = panel.scrollHeight + 'px';
  }, 150));
}

function initCertificates() {
  const grid = $('#cert-grid');
  const toggleBtn = $('#cert-toggle');
  const toggleLabel = $('#cert-toggle-label');
  if (!grid || !toggleBtn || !toggleLabel) return;

  const FEATURED_COUNT = 6;
  let expanded = false;

  function renderCard(cert, index) {
    const a = document.createElement('a');
    a.className = 'cert-card glass';
    a.href = cert.pdf;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    a.setAttribute('aria-label', `Open ${cert.title} certificate PDF in a new tab`);

    if (index >= FEATURED_COUNT) {
      a.classList.add('cert-card--extra');
      a.style.setProperty('--stagger', String(index - FEATURED_COUNT));
      a.hidden = true;
    }

    const logo = document.createElement('img');
    logo.className = 'cert-card__logo';
    logo.src = cert.logo;
    logo.alt = `${cert.tag} logo`;
    logo.loading = 'lazy';

    const h3 = document.createElement('h3');
    h3.textContent = cert.title;

    a.append(logo, h3);
    return a;
  }

  certificates.forEach((cert, index) => grid.appendChild(renderCard(cert, index)));

  const hasExtra = certificates.length > FEATURED_COUNT;
  if (!hasExtra) return;

  const extraCards = $$('.cert-card--extra', grid);
  toggleBtn.hidden = false;

  function setExpanded(next) {
    expanded = next;
    toggleBtn.setAttribute('aria-expanded', String(expanded));
    toggleBtn.classList.toggle('is-expanded', expanded);
    toggleLabel.textContent = expanded ? 'Show Less' : 'View All Certificates';

    if (expanded) {
      extraCards.forEach((card) => { card.hidden = false; });
      // force reflow so the fade-in transition actually plays
      void grid.offsetWidth;
      requestAnimationFrame(() => grid.classList.add('is-expanded'));
    } else {
      grid.classList.remove('is-expanded');
      const duration = prefersReducedMotion ? 0 : 500 + extraCards.length * 70 + 60;
      setTimeout(() => { extraCards.forEach((card) => { card.hidden = true; }); }, duration);
    }
  }

  toggleBtn.addEventListener('click', () => setExpanded(!expanded));
}

function initContact() {
  const form = $('#contact-form');
  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      if (typeof form.reportValidity === 'function' && !form.reportValidity()) return;

      const data = new FormData(form);
      const name = data.get('name') || '';
      const message = data.get('message') || '';

      const whatsappNumber = '919456712198';
      const whatsappMessage = encodeURIComponent(`${message}`);
      const whatsappURL = `https://wa.me/${whatsappNumber}?text=${whatsappMessage}`;

      window.open(whatsappURL, '_blank', 'noopener,noreferrer');
      showToast('Opening WhatsApp…');
    });
  }

  const copyBtn = $('#copy-email');
  if (copyBtn) {
    copyBtn.addEventListener('click', async () => {
      const email = copyBtn.dataset.email;
      try {
        await navigator.clipboard.writeText(email);
        showToast('Email copied to clipboard');
      } catch (e) {
        showToast(email);
      }
    });
  }
}

// cmd/ctrl+k palette
function initCommandPalette() {
  const overlay = $('#command-overlay');
  const input = $('#command-input');
  const list = $('#command-list');
  const trigger = $('#command-trigger');
  if (!overlay || !input || !list || !trigger) return;
  let activeIndex = 0, filtered = [];

  const commands = [
    { label: 'Go to About', action: () => scrollToSection('#about') },
    { label: 'Go to Skills', action: () => scrollToSection('#skills') },
    { label: 'Go to Projects', action: () => scrollToSection('#projects') },
    { label: 'Go to Timeline', action: () => scrollToSection('#timeline') },
    { label: 'Go to Hackathons', action: () => scrollToSection('#hackathons') },
    { label: 'Go to Certifications', action: () => scrollToSection('#certifications') },
    { label: 'Go to GitHub stats', action: () => scrollToSection('#github-stats') },
    { label: 'Go to Contact', action: () => scrollToSection('#contact') },
    { label: 'Copy email address', action: () => $('#copy-email')?.click() },
    { label: 'Open GitHub profile', hint: '↗', action: () => window.open(CONFIG.github, '_blank', 'noopener') },
    { label: 'Open LinkedIn profile', hint: '↗', action: () => window.open(CONFIG.linkedin, '_blank', 'noopener') },
    { label: 'Toggle theme', action: () => $('#theme-toggle')?.click() },
    { label: 'Toggle ambient audio', action: () => $('#music-toggle')?.click() },
    { label: 'Show keyboard shortcuts', action: () => showToast('⌘/Ctrl+K palette · Esc close · ↑↓ navigate · try the Konami code') },
    { label: 'sudo make me a sandwich', action: () => showToast('What? Make it yourself.') }
  ];

  function render(query) {
    const q = query.trim().toLowerCase();
    filtered = commands.filter((c) => c.label.toLowerCase().includes(q));
    activeIndex = 0;
    list.innerHTML = '';
    if (!filtered.length) {
      const li = document.createElement('li');
      li.className = 'command-empty';
      li.textContent = 'No matches — try a different search';
      list.appendChild(li);
      return;
    }
    filtered.forEach((cmd, i) => {
      const li = document.createElement('li');
      li.className = 'command-item' + (i === 0 ? ' is-active' : '');
      li.setAttribute('role', 'option');
      const label = document.createElement('span'); label.textContent = cmd.label;
      li.appendChild(label);
      if (cmd.hint) {
        const hint = document.createElement('span'); hint.className = 'command-item__hint'; hint.textContent = cmd.hint;
        li.appendChild(hint);
      }
      li.addEventListener('click', () => runCommand(cmd));
      list.appendChild(li);
    });
  }

  function updateActive() {
    $$('.command-item', list).forEach((el, i) => el.classList.toggle('is-active', i === activeIndex));
    const activeEl = $$('.command-item', list)[activeIndex];
    if (activeEl) activeEl.scrollIntoView({ block: 'nearest' });
  }

  function runCommand(cmd) { closePalette(); setTimeout(() => cmd.action(), 150); }
  function openPalette() { overlay.hidden = false; input.value = ''; render(''); setTimeout(() => input.focus(), 50); }
  function closePalette() { overlay.hidden = true; }

  trigger.addEventListener('click', openPalette);
  overlay.addEventListener('click', (e) => { if (e.target === overlay) closePalette(); });
  input.addEventListener('input', () => render(input.value));
  input.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); activeIndex = Math.min(activeIndex + 1, filtered.length - 1); updateActive(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); activeIndex = Math.max(activeIndex - 1, 0); updateActive(); }
    else if (e.key === 'Enter') { e.preventDefault(); if (filtered[activeIndex]) runCommand(filtered[activeIndex]); }
    else if (e.key === 'Escape') { closePalette(); }
  });

  window.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      overlay.hidden ? openPalette() : closePalette();
    } else if (e.key === 'Escape' && !overlay.hidden) {
      closePalette();
    }
  });
}

// this is NOT hooked up to a real model, just keyword matching.
// good enough for a portfolio gimmick, don't judge me
function initAIWidget() {
  const toggle = $('#ai-widget-toggle');
  const panel = $('#ai-widget-panel');
  const closeBtn = $('#ai-widget-close');
  const form = $('#ai-widget-form');
  const input = $('#ai-widget-input');
  const messages = $('#ai-widget-messages');
  if (!toggle || !panel || !closeBtn || !form || !input || !messages) return;

  function open() { panel.hidden = false; toggle.setAttribute('aria-expanded', 'true'); setTimeout(() => input.focus(), 50); }
  function close() { panel.hidden = true; toggle.setAttribute('aria-expanded', 'false'); }
  toggle.addEventListener('click', () => (panel.hidden ? open() : close()));
  closeBtn.addEventListener('click', close);

  function addMessage(text, who) {
    const div = document.createElement('div');
    div.className = 'ai-msg ai-msg--' + who;
    div.textContent = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div;
  }

  function reply(query) {
    const q = query.toLowerCase();
    if (/skill|know|tech|stack/.test(q)) return 'Python, JavaScript, C, plus Generative AI, prompt engineering, LLMs and AI agents — with Azure and OCI on the cloud side.';
    if (/project|built|build|made/.test(q)) return 'Five shipped projects, from Innovative AI and SplitterEase to a C-based Railway Reservation System. Check the Projects section for details.';
    if (/contact|email|reach|hire/.test(q)) return 'Best reached by email — see the Contact section, or use the command palette (Ctrl K) to copy the address directly.';
    if (/educat|study|college|university|lpu/.test(q)) return 'B.Tech CSE, specializing in Generative AI, at Lovely Professional University (2025–2029).';
    if (/hackathon/.test(q)) return 'ET AI Hackathon, E-Cell IIT Roorkee, and ByteXL GenAI Workshop.';
    if (/cert/.test(q)) return 'AZ-900, AI-900, OCI AI Foundations Associate, IBM Intro to AI, Enterprise Design Thinking, and Python (Basic) on HackerRank.';
    if (/hi|hello|hey/.test(q)) return "Hey! I'm a scripted demo, but I know this portfolio well — ask about skills, projects, education or contact.";
    return "I'm a rule-based demo, so I don't have an answer for that one — try skills, projects, education, hackathons or contact.";
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const val = input.value.trim();
    if (!val) return;
    addMessage(val, 'user');
    input.value = '';
    const typing = addMessage('', 'bot');
    typing.classList.add('ai-msg--typing');
    typing.innerHTML = '<span></span><span></span><span></span>';
    setTimeout(() => {
      typing.classList.remove('ai-msg--typing');
      typing.textContent = reply(val);
      messages.scrollTop = messages.scrollHeight;
    }, 500 + Math.random() * 400);
  });
}

function initTheme() {
  const toggle = $('#theme-toggle');
  if (!toggle) return;
  const html = document.documentElement;
  const moon = toggle.querySelector('.icon-moon'), sun = toggle.querySelector('.icon-sun');
  if (!moon || !sun) return;

  function setTheme(mode) {
    html.setAttribute('data-theme', mode);
    toggle.setAttribute('aria-pressed', String(mode === 'light'));
    moon.hidden = mode === 'light';
    sun.hidden = mode !== 'light';
    safeStorage.set('shorya-os-theme', mode);
  }

  const stored = safeStorage.get('shorya-os-theme');
  if (stored === 'light' || stored === 'dark') {
    setTheme(stored);
  } else {
    // no saved preference yet, go with the OS setting instead of just
    // always dumping people into dark mode
    const osPrefersLight = window.matchMedia('(prefers-color-scheme: light)').matches;
    setTheme(osPrefersLight ? 'light' : 'dark');
  }

  toggle.addEventListener('click', () => setTheme(html.getAttribute('data-theme') === 'light' ? 'dark' : 'light'));
}

// ambient background drone using raw Web Audio oscillators, no mp3 needed
function initMusicToggle() {
  const btn = $('#music-toggle');
  if (!btn) return;
  const onIcon = btn.querySelector('.icon-sound-on'), offIcon = btn.querySelector('.icon-sound-off');
  if (!onIcon || !offIcon) return;
  let ctx, nodes = [], playing = false;

  function updateIcons() {
    onIcon.hidden = !playing;
    offIcon.hidden = playing;
    btn.setAttribute('aria-pressed', String(playing));
  }
  updateIcons();

  function start() {
    try {
      if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)();
      if (ctx.state === 'suspended') ctx.resume();
      const master = ctx.createGain();
      master.gain.value = 0;
      master.connect(ctx.destination);
      master.gain.linearRampToValueAtTime(0.05, ctx.currentTime + 1.2);

      [110, 164.81, 220].forEach((freq, i) => {
        const osc = ctx.createOscillator();
        osc.type = 'sine'; osc.frequency.value = freq;
        const gain = ctx.createGain(); gain.gain.value = 0.5 / (i + 1);
        const lfo = ctx.createOscillator(); lfo.frequency.value = 0.05 + i * 0.02;
        const lfoGain = ctx.createGain(); lfoGain.gain.value = 40;
        lfo.connect(lfoGain); lfoGain.connect(osc.frequency);
        osc.connect(gain); gain.connect(master);
        osc.start(); lfo.start();
        nodes.push(osc, lfo);
      });
      nodes.push(master);
      playing = true;
    } catch (e) {
      showToast('Ambient audio isn\u2019t available in this browser');
      playing = false;
    }
  }

  function stop() {
    if (!ctx) return;
    const master = nodes[nodes.length - 1];
    if (master && master.gain) master.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.6);
    const toStop = nodes.slice();
    setTimeout(() => { toStop.forEach((n) => { if (n.stop) { try { n.stop(); } catch (e) {} } }); }, 700);
    nodes = [];
    playing = false;
  }

  btn.addEventListener('click', () => { playing ? stop() : start(); updateIcons(); });
}

// konami code easter egg
function initDevMode() {
  const sequence = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'b', 'a'];
  let pos = 0;
  window.addEventListener('keydown', (e) => {
    const key = e.key.length === 1 ? e.key.toLowerCase() : e.key;
    if (key === sequence[pos]) {
      pos++;
      if (pos === sequence.length) { pos = 0; unlockDevMode(); }
    } else {
      pos = key === sequence[0] ? 1 : 0;
    }
  });
}

function unlockDevMode() {
  showToast('Developer mode unlocked');
  const banner = document.createElement('div');
  banner.className = 'devmode-banner';
  const h2 = document.createElement('h2'); h2.textContent = '[ DEVELOPER MODE :: UNLOCKED ]';
  const p = document.createElement('p');
  p.textContent = "You found the secret input. Since you're clearly the kind of person who tries konami codes on portfolio sites: this whole thing is vanilla HTML/CSS/JS, no frameworks, built section by section — view-source and take whatever's useful.";
  const btn = document.createElement('button');
  btn.className = 'btn btn--ghost'; btn.type = 'button';
  const span = document.createElement('span'); span.textContent = 'Close';
  btn.appendChild(span);
  btn.addEventListener('click', () => banner.remove());
  banner.append(h2, p, btn);
  document.body.appendChild(banner);
}

function initProjectFilter() {
  const buttons = $$('.filter-btn');
  const cards = $$('.project-card');
  const emptyState = $('#project-empty-state');
  if (!buttons.length || !emptyState) return;

  buttons.forEach((btn) => {
    btn.addEventListener('click', () => {
      buttons.forEach((b) => b.classList.remove('is-active'));
      btn.classList.add('is-active');
      const filter = btn.dataset.filter;
      let visible = 0;
      cards.forEach((card) => {
        const tags = card.dataset.tags.split(',');
        const show = filter === 'all' || tags.includes(filter);
        card.classList.toggle('is-hidden', !show);
        if (show) visible++;
      });
      emptyState.hidden = visible !== 0;
    });
  });
}

// draggable "window" popup for project details, kind of a desktop-app feel
function initProjectModal() {
  const overlay = $('#project-overlay');
  const win = $('#project-window');
  const titlebar = $('#project-window-titlebar');
  const closeBtn = $('#project-window-close');
  const cards = $$('.project-card');
  if (!overlay || !win || !titlebar || !closeBtn) return;

  function openModal(card) {
    $('#pw-badge').textContent = card.dataset.badge || '';
    $('#pw-title').textContent = card.dataset.title || '';
    $('#project-window-title').textContent = (card.dataset.title || 'project').toLowerCase().replace(/\s+/g, '-') + '.exe';
    $('#pw-desc').textContent = card.dataset.description || '';
    $('#pw-tech').textContent = card.dataset.tech || '';

    const featuresWrap = $('#pw-features-wrap');
    const featuresList = $('#pw-features');
    featuresList.innerHTML = '';
    if (card.dataset.features) {
      card.dataset.features.split(',').forEach((f) => {
        const li = document.createElement('li'); li.textContent = f.trim(); featuresList.appendChild(li);
      });
      featuresWrap.hidden = false;
    } else {
      featuresWrap.hidden = true;
    }

    win.style.transform = '';
    curX = 0; curY = 0;
    overlay.hidden = false;
    closeBtn.focus();
  }
  function closeModal() { overlay.hidden = true; }

  cards.forEach((card) => {
    card.addEventListener('click', () => openModal(card));
    card.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openModal(card); } });
  });
  closeBtn.addEventListener('click', closeModal);
  overlay.addEventListener('click', (e) => { if (e.target === overlay) closeModal(); });
  window.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !overlay.hidden) closeModal(); });

  let dragging = false, startX = 0, startY = 0, curX = 0, curY = 0;
  titlebar.addEventListener('mousedown', (e) => {
    if (isCoarsePointer) return;
    dragging = true; startX = e.clientX - curX; startY = e.clientY - curY;
    titlebar.style.cursor = 'grabbing';
  });
  window.addEventListener('mousemove', (e) => {
    if (!dragging) return;
    const rect = win.getBoundingClientRect();
    // keep the window from being dragged fully off-screen with no way back
    const minX = -rect.left + curX + 20;
    const maxX = window.innerWidth - (rect.right - curX) - 20;
    const minY = -rect.top + curY + 20;
    const maxY = window.innerHeight - (rect.bottom - curY) - 20;
    curX = clamp(e.clientX - startX, minX, maxX);
    curY = clamp(e.clientY - startY, minY, maxY);
    win.style.transform = `translate(${curX}px, ${curY}px)`;
  });
  window.addEventListener('mouseup', () => { dragging = false; titlebar.style.cursor = ''; });
}

// ---- boot it up ----
document.addEventListener('DOMContentLoaded', () => {
  document.body.style.overflow = 'hidden';
  const yearEl = $('#footer-year');
  if (yearEl) yearEl.textContent = String(new Date().getFullYear());

  // wrapping each init in try/catch so one broken module doesn't take
  // the whole page down with it - learned that one the hard way
  const modules = [
    initCursor, initScrollChrome, initClock, initNav, initScrollReveal,
    initOrbitPause, initTilt, initMagnetic, initParallax, initRipple,
    initNeuralCanvas, initBootRain, initRoleTypewriter, initTerminal,
    initHackathonAccordion,
    initGithubStats, initCertificates, initContact, initCommandPalette, initAIWidget,
    initTheme, initMusicToggle, initDevMode, initProjectFilter, initProjectModal
  ];
  modules.forEach((fn) => {
    try { fn(); }
    catch (err) { console.error(`[VANSH_OS] ${fn.name} failed to initialize:`, err); }
  });

  runBootSequence().then(() => { document.body.style.overflow = ''; });
});
