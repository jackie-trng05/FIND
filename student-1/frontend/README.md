# Student 1 frontend

Flask app serving the User Profile Customisation UI (`templates/profile.html`) and
reverse-proxying API calls to the Student 1 backend.

Local dev URL: http://localhost:16004/


## What it does

- Serves `/profile`: create/view/edit/delete profile, update first/last name, and
  (for applicants) upload/view/download/delete resumes.
- Proxies `/api/profiles*`, `/api/resumes*`, `/api/user`, and `/api/auth/logout`
  to `student-1-backend`, forwarding the shared session cookie.
- Serves shared CSS from `/css/<file>` via the mounted `shared/css` volume.

## Not yet implemented

- AI resume-autofill review/accept/discard UI (deferred to a separate branch).

See [../README.md](../README.md) for known architectural deviations and testing status.
