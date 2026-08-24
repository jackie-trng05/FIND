/* Shared logic for the FIND Interview microservice frontend. */

const BACKEND_URL = "http://localhost:16014";
const AUTH_API = "http://localhost:16002";
const DASHBOARD_URL = "http://localhost:16001/dashboard";
const LOGIN_URL = "http://localhost:16001/login";

const STATUS_OPTIONS = [
  "Shortlisted",
  "Interview Requested",
  "Interview Scheduled",
  "Interview Completed",
  "Withdrawn",
];

// Skill areas assessed in the interview notes (must match the backend).
const NOTE_SECTIONS = [
  "Technical",
  "Education",
  "Communication",
  "Problem Solving",
  "Professionalism",
];

// Interview status -> badge colour (light backgrounds, matching Applications).
const STATUS_BADGE_CLASS = {
  "shortlisted": "badge-warning",           // light orange
  "interview requested": "badge-warning",   // light orange
  "interview scheduled": "badge-info",      // light blue
  "interview completed": "badge-success",   // light green
  "withdrawn": "badge-danger",              // light red
};

/* ---------- helpers ---------- */

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value == null ? "" : String(value);
  return div.innerHTML;
}

function formatDateTime(value) {
  const parsed = parseDateTime(value);
  if (!parsed) return escapeHtml(value);
  return parsed.toLocaleString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function parseDateTime(value) {
  if (!value) return null;
  const match = String(value).match(
    /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/
  );
  if (!match) return null;
  const [, y, mo, d, h, mi] = match.map(Number);
  return new Date(y, mo - 1, d, h, mi);
}

function statusBadge(status) {
  const key = String(status || "").toLowerCase();
  const cls = STATUS_BADGE_CLASS[key] || "badge-muted";
  return `<span class="badge ${cls}">${escapeHtml(status)}</span>`;
}

/*
 * Interview assessment notes are stored as JSON with the five skill areas.
 * parseNotes accepts either a JSON string or an object and returns a plain
 * object, or null for legacy/empty free-text notes.
 */
function parseNotes(raw) {
  if (!raw) return null;
  if (typeof raw === "object") return raw;
  try {
    const obj = JSON.parse(raw);
    return obj && typeof obj === "object" ? obj : null;
  } catch {
    return null;
  }
}

/* Read-only display of the five note sections (or a hint when empty). */
function notesView(raw) {
  const notes = parseNotes(raw);
  if (!notes) {
    const text = String(raw || "").trim();
    return text
      ? `<p class="meta">${escapeHtml(text)}</p>`
      : `<p class="form-hint">No interview notes yet.</p>`;
  }
  return (
    `<dl class="detail-grid notes-grid">` +
    NOTE_SECTIONS.map(
      (s) =>
        `<dt>${escapeHtml(s)}</dt><dd>${
          escapeHtml(notes[s] || "") || "&mdash;"
        }</dd>`
    ).join("") +
    `</dl>`
  );
}

/* Editable five-section notes form. `idPrefix` keeps ids unique per card. */
function notesForm(raw, idPrefix = "note") {
  const notes = parseNotes(raw) || {};
  return (
    `<div class="notes-form">` +
    NOTE_SECTIONS.map((s) => {
      const id = `${idPrefix}-${s}`;
      return `
        <div class="full">
          <label for="${id}">${escapeHtml(s)}</label>
          <textarea id="${id}" data-note="${s}" rows="2" placeholder="Notes on ${escapeHtml(
        s
      )}">${escapeHtml(notes[s] || "")}</textarea>
          <div class="field-error" data-note-error="${s}"></div>
        </div>`;
    }).join("") +
    `</div>`
  );
}

/* Collect notes from a container; returns { notes, missing[] }. */
function collectNotes(container) {
  const notes = {};
  const missing = [];
  NOTE_SECTIONS.forEach((s) => {
    const el = container.querySelector(`[data-note="${s}"]`);
    const value = el ? el.value.trim() : "";
    notes[s] = value;
    if (!value) missing.push(s);
  });
  return { notes, missing };
}

/* Complete an interview by saving its five-section notes. */
async function completeInterviewWithNotes(id, notes) {
  const resp = await fetch(`${BACKEND_URL}/interviews/${id}/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ interview_notes: notes }),
  });
  const data = await resp.json().catch(() => ({}));
  return { ok: resp.ok, data };
}

/* Whether an interview's scheduled time has already passed. */
function isInterviewPast(value) {
  const dt = parseDateTime(value);
  return Boolean(dt) && dt <= new Date();
}

/* Inline "Thinking…" indicator, consistent with the Job Posting service. */
function thinkingHtml() {
  return `<span class="ai-thinking"><span class="spinner"></span> Thinking…</span>`;
}

/* ---------- auth ---------- */

function redirectLogin() {
  window.location.href = LOGIN_URL;
}

function clearAndLogin() {
  sessionStorage.removeItem("find_token");
  sessionStorage.removeItem("find_user");
  redirectLogin();
}

async function getAuthedUser() {
  const url = new URL(window.location.href);
  const urlToken = url.searchParams.get("token");
  if (urlToken) {
    sessionStorage.setItem("find_token", urlToken);
    url.searchParams.delete("token");
    window.history.replaceState({}, "", url.pathname + url.search + url.hash);
  }

  const token = sessionStorage.getItem("find_token");

  let user = null;
  try {
    user = JSON.parse(sessionStorage.getItem("find_user") || "null");
  } catch {
    user = null;
  }

  try {
    // Auth works via the shared session cookie (shared across localhost ports);
    // a bearer token is still honoured if one was passed in the URL.
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    const resp = await fetch(`${AUTH_API}/api/auth/session`, {
      headers,
      credentials: "include",
    });
    if (!resp.ok) {
      clearAndLogin();
      return null;
    }
    const data = await resp.json();
    user = data.user;
    sessionStorage.setItem("find_user", JSON.stringify(user));
  } catch {
    if (!user) {
      clearAndLogin();
      return null;
    }
  }
  return user;
}

async function logout() {
  const token = sessionStorage.getItem("find_token");
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  await fetch(`${AUTH_API}/api/auth/logout`, {
    method: "POST",
    headers,
    credentials: "include",
  }).catch(() => {});
  clearAndLogin();
}

/* ---------- chrome (nav bars) ---------- */

function renderChrome(user, activePage) {
  const isStaff = user.role === "staff";
  const roleLabel = isStaff ? "Staff" : "Applicant";

  const tabs = [
    { key: "calendar", label: "Interview Calendar", href: "index.html" },
    { key: "list", label: "All Interviews", href: "list.html" },
  ];
  if (isStaff) {
    tabs.push({ key: "applications", label: "To Schedule", href: "applications.html" });
    tabs.push({ key: "to-complete", label: "Interviews To Complete", href: "to-complete.html" });
    tabs.push({ key: "schedule", label: "Schedule Interview", href: "schedule.html" });
  } else {
    tabs.push({ key: "requests", label: "My Requests", href: "requests.html" });
  }

  const tabsHtml = tabs
    .map(
      (t) =>
        `<a href="${t.href}" class="${t.key === activePage ? "active" : ""}">${t.label}</a>`
    )
    .join("");

  return `
    <nav class="navbar">
      <div class="navbar-inner">
        <div class="navbar-left">
          <a class="navbar-brand" href="${DASHBOARD_URL}">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                 stroke-linecap="round" stroke-linejoin="round">
              <circle cx="11" cy="11" r="8"></circle><path d="m21 21-4.3-4.3"></path>
            </svg>
            FIND
          </a>
        </div>
        <div class="navbar-user">
          <a class="btn btn-ghost btn-sm" href="${DASHBOARD_URL}">&#8592; Home</a>
          <span class="user-badge">${roleLabel}</span>
          <span id="nav-name">${escapeHtml(user.first_name)} ${escapeHtml(user.last_name)}</span>
          <button class="btn btn-ghost btn-sm" id="logout-btn" type="button">Log Out</button>
        </div>
      </div>
    </nav>
    <div class="subnav">${tabsHtml}</div>
  `;
}

async function initChrome(activePage, { staffOnly = false, applicantOnly = false } = {}) {
  const user = await getAuthedUser();
  if (!user) return null;

  if (staffOnly && user.role !== "staff") {
    window.location.href = "index.html";
    return null;
  }
  if (applicantOnly && user.role !== "applicant") {
    window.location.href = "index.html";
    return null;
  }

  const chrome = document.getElementById("app-chrome");
  if (chrome) chrome.innerHTML = renderChrome(user, activePage);
  const logoutBtn = document.getElementById("logout-btn");
  if (logoutBtn) logoutBtn.addEventListener("click", logout);

  flushPendingToast();
  return user;
}

/* ---------- toasts ---------- */

// Full-width alert at the top of the page that fades out after a few seconds,
// matching the Job Posting and Applications services.
function showToast(message, type = "success") {
  const shell = document.querySelector("main.app-shell") || document.body;
  let area = document.getElementById("toast-area");
  if (!area) {
    area = document.createElement("div");
    area.id = "toast-area";
    shell.insertBefore(area, shell.firstChild);
  }
  const kind = type === "error" ? "alert-error" : "alert-success";
  const toast = document.createElement("div");
  toast.className = `alert ${kind} toast`;
  toast.textContent = message;
  area.appendChild(toast);
  setTimeout(() => {
    toast.classList.add("toast-hide");
    setTimeout(() => toast.remove(), 400);
  }, 4000);
}

/* Queue a toast to display after a page navigation (e.g. cancel -> list). */
function setPendingToast(message, type = "success") {
  sessionStorage.setItem("find_toast", JSON.stringify({ message, type }));
}

function flushPendingToast() {
  const raw = sessionStorage.getItem("find_toast");
  if (!raw) return;
  sessionStorage.removeItem("find_toast");
  try {
    const t = JSON.parse(raw);
    showToast(t.message, t.type);
  } catch {
    /* ignore malformed toast */
  }
}

/* ---------- data ---------- */

function userFilters(user) {
  return user.role === "staff"
    ? { staff_id: user.user_id }
    : { applicant_id: user.user_id };
}

async function fetchInterviews(user, extra = {}) {
  const params = new URLSearchParams({ ...userFilters(user), ...extra });
  const resp = await fetch(`${BACKEND_URL}/interviews?${params.toString()}`);
  if (!resp.ok) throw new Error("Failed to load interviews.");
  return resp.json();
}

/* Every interview in the system (used by the staff "All Interviews" view). */
async function fetchAllInterviews() {
  const resp = await fetch(`${BACKEND_URL}/interviews`);
  if (!resp.ok) throw new Error("Failed to load interviews.");
  return resp.json();
}

async function fetchInterview(id) {
  const resp = await fetch(`${BACKEND_URL}/interviews/${id}`);
  if (resp.status === 404) return null;
  if (!resp.ok) throw new Error("Failed to load interview.");
  return resp.json();
}

/*
 * Shortlisted applications a staff member still needs to schedule interviews
 * for. Sourced from Student 3's application data via the interview backend;
 * applications that already have an interview request are excluded server-side.
 */
async function fetchSchedulableApplications(user) {
  const params = new URLSearchParams({ staff_id: user.user_id });
  const resp = await fetch(`${BACKEND_URL}/schedulable-applications?${params.toString()}`);
  if (!resp.ok) throw new Error("Failed to load applications to schedule.");
  const data = await resp.json();
  return data.applications || [];
}

/* Belongs-to check so users cannot view others' interviews via URL. */
function ownsInterview(user, interview) {
  if (!interview) return false;
  // Staff can view any interview (the All Interviews list shows them all);
  // applicants may only view interviews for their own application.
  return user.role === "staff"
    ? true
    : Number(interview.applicant_id) === Number(user.user_id);
}

/* ---------- datetime helpers ---------- */

/* Current local time as a value for <input type="datetime-local" min="...">. */
function nowLocalInput() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(
    d.getHours()
  )}:${pad(d.getMinutes())}`;
}

/* "2026-09-10T10:00" (datetime-local) -> "2026-09-10 10:00" (backend). */
function toBackendDateTime(localValue) {
  return String(localValue || "").replace("T", " ").slice(0, 16);
}

/* "2026-09-10 10:00" (backend) -> "2026-09-10T10:00" (datetime-local). */
function toLocalInput(backendValue) {
  return String(backendValue || "").replace(" ", "T").slice(0, 16);
}

function isFutureLocal(localValue) {
  const parsed = parseDateTime(localValue);
  return Boolean(parsed) && parsed > new Date();
}

/* Pull YYYY-MM-DD HH:MM stamps out of the AI's free-text reply. */
function extractSuggestedTimes(text) {
  const div = document.createElement("div");
  div.innerHTML = text;
  const plain = div.textContent || "";
  const matches = plain.match(/\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}/g) || [];
  return [...new Set(matches.map((m) => m.replace("T", " ")))];
}

/*
 * Render only clickable time chips from the AI reply (no raw text). Each chip
 * drops the chosen time into the target datetime-local input, given as either an
 * element id (string) or the element itself.
 */
function renderSuggestions(panel, text, target) {
  const times = extractSuggestedTimes(text);
  panel.innerHTML = "";

  if (!times.length) {
    panel.innerHTML = `<p class="form-hint">No specific times were suggested. Add more detail and try again.</p>`;
    return;
  }

  const wrap = document.createElement("div");
  wrap.className = "suggest-chips";
  wrap.innerHTML =
    `<div class="form-hint">Suggested times — click one to use it:</div>` +
    times
      .map(
        (t) =>
          `<button type="button" class="btn btn-secondary btn-sm suggest-chip" data-dt="${escapeHtml(
            t
          )}">${escapeHtml(t)}</button>`
      )
      .join("");
  panel.appendChild(wrap);

  wrap.querySelectorAll(".suggest-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = typeof target === "string" ? document.getElementById(target) : target;
      if (input) input.value = toLocalInput(btn.dataset.dt);
    });
  });
}

/* ---------- confirm dialog ---------- */

function confirmDialog({
  title = "Are you sure?",
  message = "",
  confirmText = "Confirm",
  cancelText = "Cancel",
  danger = false,
} = {}) {
  return new Promise((resolve) => {
    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.innerHTML = `
      <div class="modal" role="dialog" aria-modal="true">
        <h3 class="modal-title">${escapeHtml(title)}</h3>
        ${message ? `<p class="modal-message">${escapeHtml(message)}</p>` : ""}
        <div class="modal-actions">
          <button type="button" class="btn btn-secondary" data-role="cancel">${escapeHtml(cancelText)}</button>
          <button type="button" class="btn ${danger ? "btn-danger" : "btn-primary"}" data-role="confirm">${escapeHtml(confirmText)}</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);

    const close = (result) => {
      overlay.remove();
      document.removeEventListener("keydown", onKey);
      resolve(result);
    };
    function onKey(e) {
      if (e.key === "Escape") close(false);
    }

    overlay.querySelector('[data-role="cancel"]').addEventListener("click", () => close(false));
    overlay.querySelector('[data-role="confirm"]').addEventListener("click", () => close(true));
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) close(false);
    });
    document.addEventListener("keydown", onKey);
    requestAnimationFrame(() => overlay.classList.add("show"));
  });
}
