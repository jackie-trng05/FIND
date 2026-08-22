// Shared auth utility — updates navbar based on login state
(function() {
  const user = JSON.parse(sessionStorage.getItem('find_user') || 'null');
  const navAuth = document.getElementById('nav-auth');
  if (!navAuth) return;

  if (user) {
    navAuth.innerHTML = `
      <span class="user-badge">${user.role === 'staff' ? 'Staff' : 'Applicant'}</span>
      <a href="/dashboard" class="btn btn-secondary btn-sm">${user.first_name}</a>
      <button class="btn btn-ghost btn-sm" onclick="logoutGlobal()">Log Out</button>
    `;
  }
})();

async function logoutGlobal() {
  const token = sessionStorage.getItem('find_token');
  if (token) {
    await fetch('http://localhost:16002/api/auth/logout', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    }).catch(() => {});
  }
  sessionStorage.removeItem('find_token');
  sessionStorage.removeItem('find_user');
  window.location.href = '/login';
}
