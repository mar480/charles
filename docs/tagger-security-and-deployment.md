# Tagger Security And Deployment

This branch is designed as a tagger-first internal filing tool, not a public anonymous upload service.

## Security controls in the current implementation

- Companies House lookups use `COMPANIES_HOUSE_API_KEY` on the backend only. The browser never receives the key.
- Project data is stored outside the repository in `TAGGER_DATA_DIR` when configured, or the OS-local default data directory otherwise.
- CSV and XLSX imports are restricted to mapped template imports and capped at `2 MB` per file.
- Untagged HTML fixture content is sanitised before it is rendered into the editable template canvas. Script-like tags, inline event handlers, and `javascript:` URLs are stripped.
- The Flask app now applies an optional access-control hook to `/api/tagger/*`.

## Access-control hooks

The first deployment can stay single-user, but the app exposes two simple hooks so it is not hard-wired to anonymous access:

- `TAGGER_ACCESS_TOKEN`
  The API requires `Authorization: Bearer <token>` or `X-Tagger-Token: <token>` on `/api/tagger/*`.
- `TAGGER_ALLOWED_USER`
  The API also checks `X-Forwarded-User` or `X-Remote-User` from the reverse proxy and rejects other users.

These hooks are intentionally basic. They are there so a reverse proxy or future auth layer can be introduced without changing the tagger domain code.

## Reverse proxy and HTTPS expectations

- Terminate TLS at a reverse proxy such as Nginx, Caddy, Apache, or an internal ingress layer.
- Do not expose the Flask development server directly to the internet.
- Forward authenticated identity with `X-Forwarded-User` if you use proxy-managed access control.
- Apply request body limits at the proxy as well as the app layer.
- Restrict the tagger to trusted internal users because draft accounts and imported figures may be sensitive.

## Logging guidance

- Do not log uploaded file contents.
- Do not log fact values or generated iXBRL payloads.
- Do not log Companies House API keys.
- Keep API error logging to route and exception class rather than request payload bodies.

## Environment variables

- `COMPANIES_HOUSE_API_KEY`: required for Companies House profile lookup.
- `TAGGER_DATA_DIR`: optional override for SQLite data and export storage.
- `TAGGER_ACCESS_TOKEN`: optional bearer/token header requirement for tagger API access.
- `TAGGER_ALLOWED_USER`: optional reverse-proxy user allow-list for single-user/internal deployment.

## Storage notes

- SQLite is the current default and is suitable for the first local/internal workflow.
- The storage abstraction remains isolated in `ada/backend/tagger/storage.py` so a later Postgres-backed implementation can replace it without changing the UI flow.
