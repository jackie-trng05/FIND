# Student 1 frontend

Flask app serving the User Profile Customisation UI (`templates/profile.html`) as
an HTMX page shell. The browser calls `student-1-backend` directly (cookie-based
session).

Local dev URL: http://localhost:16004/


## What it does

- Serves `/profile` (and `/`): a page shell with `user-details-panel` and
  `profile-panel` divs that HTMX populates by calling `student-1-backend`
  fragment routes directly once the shared-api session check succeeds.
- Serves the shared CSS from `/css/<file>` via the mounted `shared/css` volume.

## Not yet implemented

- AI resume-autofill review/accept/discard UI (deferred to a separate branch).

See [../README.md](../README.md) for known architectural deviations and testing status.
