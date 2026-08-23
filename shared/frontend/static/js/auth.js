// Shared auth utility — updates navbar based on login state
(async function() {
  const navAuth = document.getElementById('nav-auth');
  if (!navAuth) return;

  try {
    const resp = await fetch('http://localhost:16002/api/auth/session', {
      credentials: 'include'
    });
    if (!resp.ok) return;
    const { user } = await resp.json();
    if (!user) return;
    navAuth.innerHTML = `
      <span class="user-badge">${user.role === 'staff' ? 'Staff' : 'Applicant'}</span>
      <a href="/dashboard" class="btn btn-secondary btn-sm">${user.first_name}</a>
      <button class="btn btn-ghost btn-sm" onclick="logoutGlobal()">Log Out</button>
    `;
  } catch {}
})();

async function logoutGlobal() {
  await fetch('http://localhost:16002/api/auth/logout', {
    method: 'POST',
    credentials: 'include'
  }).catch(() => {});
  window.location.href = '/login';
}
