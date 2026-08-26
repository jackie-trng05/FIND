/*
 * FIND — shared front-end runtime.
 *
 * A single, shared implementation of the pieces every student front-end needs:
 *   - session auth guard (delegates validation to the shared auth API),
 *   - navbar user/role rendering + logout,
 *   - toast notifications (incl. HTMX `HX-Trigger` events and the ?toast= param),
 *   - a themed confirmation dialog for `htmx:confirm`,
 *   - global HTMX config (cross-origin credentials, 401 -> login, HX-Redirect),
 *   - delegated row-click navigation for `.application-row[data-href]`.
 *
 * Pages configure it with a tiny inline block BEFORE loading this script:
 *
 *   <script>
 *     window.__FIND_CONFIG = {
 *       sharedApiUrl: 'http://localhost:16002',   // required
 *       loginUrl:     'http://localhost:16001/login', // required
 *       logoutUrl:    '...optional, defaults to sharedApiUrl + /api/auth/logout',
 *       homeUrl:      '...optional, where non-authorised roles are sent',
 *       requireRole:  'staff' // optional: redirect users without this role
 *     };
 *   </script>
 *   <script src="/js/find-app.js"></script>
 *
 * Keeping this logic in one shared file means no student folder re-implements
 * authentication or session handling.
 */
(function () {
    "use strict";

    var cfg = window.__FIND_CONFIG || {};
    var SHARED_API_URL = cfg.sharedApiUrl;
    var LOGIN_URL = cfg.loginUrl;
    var LOGOUT_URL = cfg.logoutUrl || (SHARED_API_URL ? SHARED_API_URL + "/api/auth/logout" : null);
    var HOME_URL = cfg.homeUrl || "/";
    var REQUIRE_ROLE = cfg.requireRole || null;

    if (!SHARED_API_URL || !LOGIN_URL) {
        console.error("find-app.js: window.__FIND_CONFIG.sharedApiUrl and .loginUrl are required.");
        return;
    }

    window.__findLoginUrl = LOGIN_URL;
    window.__findLogoutUrl = LOGOUT_URL;

    /* ---- Ensure required DOM exists ------------------------------------ */
    function ensureEl(id, build) {
        var el = document.getElementById(id);
        if (el) return el;
        el = build();
        document.body.appendChild(el);
        return el;
    }

    function ensureToastArea() {
        return ensureEl("toast-area", function () {
            var d = document.createElement("div");
            d.id = "toast-area";
            d.style.cssText = "position:fixed;top:1rem;right:1rem;z-index:2000;";
            return d;
        });
    }

    var confirmOverlay = document.getElementById("confirm-modal");
    if (!confirmOverlay) {
        confirmOverlay = document.createElement("div");
        confirmOverlay.id = "confirm-modal";
        confirmOverlay.className = "modal-overlay";
        confirmOverlay.hidden = true;
        confirmOverlay.innerHTML =
            '<div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="confirm-title">' +
            '<h3 class="modal-title" id="confirm-title">Please confirm</h3>' +
            '<p class="modal-message" id="confirm-message"></p>' +
            '<div class="modal-actions">' +
            '<button type="button" class="btn btn-secondary" id="confirm-cancel">Cancel</button>' +
            '<button type="button" class="btn btn-danger" id="confirm-ok">Confirm</button>' +
            "</div></div>";
        document.body.appendChild(confirmOverlay);
    }

    /* ---- Themed confirmation modal ------------------------------------- */
    var message = document.getElementById("confirm-message");
    var okBtn = document.getElementById("confirm-ok");
    var cancelBtn = document.getElementById("confirm-cancel");
    var pending = null;

    function closeConfirm() { confirmOverlay.hidden = true; pending = null; }

    cancelBtn.addEventListener("click", closeConfirm);
    confirmOverlay.addEventListener("click", function (e) { if (e.target === confirmOverlay) closeConfirm(); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !confirmOverlay.hidden) closeConfirm(); });
    okBtn.addEventListener("click", function () {
        var run = pending;
        closeConfirm();
        if (run) run();
    });

    document.body.addEventListener("htmx:confirm", function (e) {
        if (!e.detail.question) return;
        e.preventDefault();
        message.textContent = e.detail.question;
        var q = e.detail.question.toLowerCase();
        var isDelete = q.indexOf("delete") !== -1;
        var isWithdraw = q.indexOf("withdraw") !== -1;
        okBtn.className = (isDelete || isWithdraw) ? "btn btn-danger" : "btn btn-primary";
        okBtn.textContent = isDelete ? "Delete" : (isWithdraw ? "Withdraw" : "Confirm");
        pending = function () { e.detail.issueRequest(true); };
        confirmOverlay.hidden = false;
    });

    /* ---- Toast notifications ------------------------------------------- */
    function showToast(text, kind) {
        var area = ensureToastArea();
        var div = document.createElement("div");
        div.className = kind === "error" ? "alert alert-error toast" : "alert alert-success toast";
        div.textContent = text;
        area.appendChild(div);
        setTimeout(function () {
            div.classList.add("toast-hide");
            setTimeout(function () { div.remove(); }, 400);
        }, 4000);
    }
    window.showToast = showToast;

    // Show toast from ?toast= query param (used after a redirect post-action).
    var params = new URLSearchParams(window.location.search);
    var toastMsg = params.get("toast");
    if (toastMsg) {
        showToast(toastMsg, "success");
        params.delete("toast");
        var clean = window.location.pathname + (params.toString() ? "?" + params.toString() : "");
        window.history.replaceState({}, "", clean);
    }

    document.body.addEventListener("showToast", function (e) {
        showToast((e.detail && e.detail.value) || "Done", "success");
    });
    document.body.addEventListener("showErrorToast", function (e) {
        showToast((e.detail && e.detail.value) || "Something went wrong.", "error");
    });

    /* ---- Global HTMX config -------------------------------------------- */
    if (window.htmx) {
        window.htmx.config.withCredentials = true;
    }
    document.body.addEventListener("htmx:responseError", function (e) {
        if (e.detail && e.detail.xhr && e.detail.xhr.status === 401) {
            window.location.href = LOGIN_URL;
        }
    });
    // Normalise HX-Redirect (handles cross-origin redirect targets).
    document.body.addEventListener("htmx:beforeOnLoad", function (e) {
        var xhr = e.detail && e.detail.xhr;
        if (xhr && xhr.getResponseHeader) {
            var redirect = xhr.getResponseHeader("HX-Redirect");
            if (redirect) window.location.href = redirect;
        }
    });

    /* ---- Delegated row-click navigation -------------------------------- */
    document.body.addEventListener("click", function (e) {
        var row = e.target.closest(".application-row");
        if (!row || !row.dataset.href) return;
        if (e.target.closest("button, a, select, input, textarea, .cell-interactive")) return;
        window.location.href = row.dataset.href;
    });

    /* ---- Navbar user + role rendering ---------------------------------- */
    function applyUser(user) {
        var nameEl = document.getElementById("nav-user-name") || document.getElementById("user-name");
        var badgeEl = document.getElementById("nav-role-badge") || document.getElementById("user-role-badge");
        var logoutBtn = document.getElementById("nav-logout-btn");
        if (nameEl) nameEl.textContent = user.first_name + " " + user.last_name;
        if (badgeEl) badgeEl.textContent = user.role === "staff" ? "Staff" : "Applicant";
        if (logoutBtn) logoutBtn.style.display = "";
        document.body.classList.remove("role-staff", "role-applicant");
        document.body.classList.add("role-" + (user.role === "staff" ? "staff" : "applicant"));
    }

    /* ---- Session auth guard -------------------------------------------- */
    fetch(SHARED_API_URL + "/api/auth/session", { credentials: "include" })
        .then(function (resp) {
            if (!resp.ok) { window.location.href = LOGIN_URL; return null; }
            return resp.json();
        })
        .then(function (data) {
            if (!data || !data.user) return;
            var user = data.user;
            if (REQUIRE_ROLE && user.role !== REQUIRE_ROLE) {
                window.location.href = HOME_URL;
                return;
            }
            applyUser(user);
            window.__findUser = user;
            var wrapper = document.getElementById("page-wrapper");
            if (wrapper) wrapper.style.display = "";
            document.body.dispatchEvent(new Event("authReady"));
        })
        .catch(function () { window.location.href = LOGIN_URL; });

    /* ---- Global logout ------------------------------------------------- */
    window.handleLogout = function () {
        fetch(window.__findLogoutUrl, { method: "POST", credentials: "include" })
            .catch(function () {})
            .then(function () { window.location.href = window.__findLoginUrl; });
    };
})();
