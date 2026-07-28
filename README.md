# Daniel Yao Agblevor — HR Systems & Automation

A production-oriented monorepo for a premium consulting website. The public site is a framework-free static application for GitHub Pages. The Flask application provides the API and private administration panel for Render. Public content, leads, and feature state are stored in Supabase Postgres; Supabase Auth secures administration and Supabase Storage holds managed media.

## Architecture

```text
frontend/   Static HTML, CSS, and JavaScript for GitHub Pages
backend/    Flask API and Jinja2 administration panel for Render
```

The two applications are independently deployable. The frontend communicates with the backend only over the configured API origin. Optional public sections are off by default and are fetched only after `/api/features` reports that they are enabled. This is also the failure policy: if feature state is unavailable, optional navigation and content stay hidden while the core page remains readable.

The admin access token is stored in a `Secure`, `HttpOnly`, `SameSite=Strict` cookie on the Render hostname. State-changing requests require a matching CSRF token. JWT verification supports Supabase asymmetric signing keys through the project JWKS, including normal key rotation. Legacy HS256 tokens are verified against the Supabase Auth user endpoint as recommended by Supabase. Browser storage is used only for the public theme preference.

## Local setup

Requirements: Python 3.12 and a static web server. A Node.js toolchain is not required.

1. Copy `.env.example` to `.env` and replace every safe example with local credentials.
2. From `backend/`, create a virtual environment and install `requirements-dev.txt`.
3. Run migrations with `python -m flask --app app:create_app db upgrade`.
4. Create the initial feature flags and singleton profile with `python -m flask --app app:create_app seed-defaults`.
5. Start Flask with `python -m flask --app app:create_app run`.
6. Serve `frontend/` on `http://localhost:5500` with any basic static server.

Local development defaults to SQLite when `DATABASE_URL` is absent. Production fails fast if a required setting is missing. Do not use SQLite or Flask's development server in production.

## Frontend configuration

Set `API_BASE_URL` once in `frontend/assets/js/config.runtime.js`. Keep it as `http://localhost:5000` only for local work; use the exact HTTPS Render backend origin before deployment. The value must not contain a trailing slash.

Before launch, also set an accurate canonical URL, approved social-share metadata/image, and production URLs in `frontend/sitemap.xml`. The committed empty sitemap avoids publishing a fabricated domain.

Static asset changes are cache-busted by updating their query-string version in the HTML or by renaming the changed file. GitHub Pages and the custom domain must use HTTPS.

## Environment variables

| Name | Purpose |
| --- | --- |
| `SECRET_KEY` | Long random Flask signing secret |
| `JWT_SECRET_KEY` | Reserved for a legacy Supabase HS256 project; current verification uses the Auth endpoint |
| `DATABASE_URL` | Supabase Postgres connection string with `sslmode=require` |
| `SUPABASE_URL` | Project URL, without a trailing slash |
| `SUPABASE_PUBLISHABLE_KEY` | Supabase Auth login and token-verification application key |
| `SUPABASE_SECRET_KEY` | Server-only elevated key for media storage; never expose it to either browser app |
| `SUPABASE_MEDIA_BUCKET` | Public Supabase Storage bucket for approved site images |
| `RESEND_API_KEY` | Resend API key |
| `RESEND_FROM_EMAIL` | Verified Resend sender |
| `CONTACT_NOTIFICATION_TO` | Private recipient for inquiry alerts |
| `FRONTEND_URL` | Exact public frontend origin used by CORS |
| `FLASK_ENV` | `development` or `production` |

Secrets must be rotated in Supabase, Resend, and Render first, then replaced in the Render environment. Redeploy and confirm authentication/contact behavior before revoking an overlapping old credential where the provider permits overlap. Never place server credentials in `frontend/`.

Create `SUPABASE_MEDIA_BUCKET` as a public `site-media` bucket with a 5 MB object limit and JPEG, PNG, WebP, and AVIF input types. Reads are public; writes remain backend-only through `SUPABASE_SECRET_KEY`. Do not add anonymous upload policies. The legacy `SUPABASE_ANON_KEY` and `SUPABASE_SERVICE_ROLE_KEY` names remain runtime fallbacks only for a staged key rotation.

## Database and content model

Run `flask db migrate -m "description"` after an intentional model change, inspect the migration, then run `flask db upgrade`. Deployments run committed migrations; they never call `create_all()`.

- Technology pills, service capabilities, case-study tools, KPI items, credentials, and approach steps use validated JSON arrays/objects.
- `CaseStudy.slug` is unique and supplies the stable share URL at `case-studies/?slug=<slug>`.
- `SiteProfile` is treated as a singleton. `seed-defaults` creates it only when absent; the admin profile endpoint always updates the first record.
- Rich blog content is sanitized against a small allowlist on write and again before modal insertion.
- Feature flags are seeded off. Disabled content endpoints return 404 even when their URL is known.
- Public GET responses currently use conservative no-store caching so administration changes are immediately visible. This may be tuned to a short explicit TTL after observing production traffic.

Supabase free-tier backup and retention behavior can change. Confirm the current project policy, schedule periodic logical exports for important content/leads, and test a restore into a separate project before relying on the process.

## Tests

From `backend/`, run `python -m pytest -q`. Tests use temporary SQLite databases and mock Supabase/email boundaries; they require no production credentials. Coverage includes contact validation, persistence, idempotency, notification failure, rate limiting, admin authorization, CSRF, pagination, filtering, feature enforcement, lead status validation, expired JWTs, and database URL normalization.

Manual public-site checks before launch:

- Verify 320px, mobile, tablet, laptop, and wide layouts with no horizontal scroll.
- Verify keyboard navigation, focus visibility, mobile navigation, slideshow controls, dialog focus restoration, and video facades.
- Verify light/dark initialization and persistence, plus reduced-motion behavior.
- Exercise contact pending, success, validation, rate-limit, server, offline, and retained-input states.
- Test empty/failed API responses, broken media, slow connections, zoom to 200%, and current Chrome, Edge, Firefox, and Safari.
- Run Lighthouse against production-like hosting and investigate material regressions from the target scores in the specification.

## Render deployment

Create a Web Service using the repository and the committed `render.yaml`, or configure it manually:

- Plan: Starter (always on)
- Runtime: Python 3.12
- Root directory: `backend`
- Build command: `pip install -r requirements.txt && flask --app app:create_app db upgrade`
- Start command: `gunicorn --bind 0.0.0.0:$PORT "app:create_app()"`
- Health check: `/health`

Set all variables from `.env.example` in the Render dashboard. `DATABASE_URL` should use the Supabase direct or pooler connection details recommended for the selected network mode and include required SSL configuration. Set `FRONTEND_URL` to the exact GitHub Pages/custom-domain origin—no path and no wildcard. Confirm Resend using a real, approved test inquiry and verify both the stored lead and delivered email.

## GitHub Pages deployment

Publish only `frontend/`, using a Pages workflow that copies that folder to the deployment artifact. If the repository settings support only branch-root or `/docs`, use a workflow rather than moving public files into the repository root. Configure the custom domain in Pages, enforce HTTPS, then set the same exact origin in Render's `FRONTEND_URL`. Verify a browser preflight and a real contact submission from the production origin.

The backend remains on Render and `/admin` is intentionally not linked from the public site, sitemap, or robots file. Its security comes from verified authentication, not obscurity.

## Administration

Create administrators directly in Supabase Auth using email/password. Visit the Render backend `/admin`, sign in, add owner-approved content, and publish it deliberately. Feature sections should be enabled only after their content is complete. The interface supports lead status changes, feature toggles, and CRUD for services, portfolio, case studies, testimonials, blog posts, slideshow images, and structured core content. Images are accepted as JPEG, PNG, WebP, or AVIF up to 5 MB, verified by decoding, stripped of embedded metadata, normalized to WebP, and uploaded only to approved folders in the configured public Supabase bucket. The application stores each managed object path so replaced or deleted profile/slideshow images can be removed from storage.

## Security and operational notes

- The in-memory rate limiter is appropriate only for one always-on Render instance. Limits are not shared across processes or instances and reset on restart. Move to a shared limiter store only after approval if scaling changes.
- Contact storage commits before email delivery. A provider failure returns `202`, preserves the lead, and reports delayed notification without creating duplicates when an idempotency key is supplied.
- The CSP for backend admin pages is set by Flask. GitHub Pages cannot set response headers; configure an equivalent static-site CSP at a custom reverse proxy only if the approved hosting topology later includes one.
- Because full blog content opens in a client-side modal, do not treat it as equivalent to a dedicated indexable article URL. Keep meaningful excerpts in public content and add dedicated pages only with owner approval.
- Dependency versions are pinned. Review and test updates on a maintenance cadence before changing them.

## Launch content

See [CONTENT_CHECKLIST.md](CONTENT_CHECKLIST.md). No KPI, testimonial, client, biography, project outcome, or credential is seeded. This is intentional: public proof must be real and owner-approved.

#   M y W e b s i t e  
 #   M y W e b s i t e  
 