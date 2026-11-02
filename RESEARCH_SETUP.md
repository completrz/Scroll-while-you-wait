# Research deployment checklist (NOT YET READY FOR PRODUCTION)

The local user dashboard works without accounts. Research uploads are OFF by
default. Do not enable uploads until the entire checklist is complete.

1. Create a Supabase project and apply migrations in order.
2. Enable Supabase anonymous authentication for consenting participants.
3. Deploy the Cloudflare Worker at `backend/worker.js`. Store Supabase keys
   as encrypted Cloudflare Worker secrets; NEVER put the service-role key
   in the extension or in browser JavaScript.
4. Add participant-level persistent opt-in records **server-side**. Require
   that consent record for *each* ingestion, instead of trusting the current
   client-provided `consented` flag.
5. Add rate limiting and durable deduplication, plus strict allowed origins.
6. Add authenticated consent withdrawal, participant deletion, and retention
   expiration jobs. Verify a deletion removes stored rows and prevents
   further uploads.
7. Configure the extension's optional host permissions and research UI.
   Explicitly ask the participant before sending anything. Local dashboard
   must continue to work when consent is denied or withdrawn.
8. Separate admin authorization from participant authorization and implement
   audit logging, CSV export, aggregation endpoints, and an authenticated
   administrator dashboard. Never expose the Supabase service-role key
   through the admin website.
9. Deploy a public privacy policy and update Chrome Web Store disclosures.
10. Obtain explicit go-live approval and perform real-browser tests.

Until those are complete, leave `ENABLE_INGESTION` unset. The Worker
returns HTTP 503 and the extension does not upload any analytics.

## Study design

Randomize eligible responses within participant only after informed consent.
Keep assignments, manual overrides, actual exposure, and non-return events
so that the primary analysis can use intention-to-treat. Prefer comparing
return-to-chat latency distributions within participants, or a pre-defined
restricted-window return indicator with missing/censored follow-up.
Participant responses are clustered; do not treat them as independent users.

Personal dashboards report observed return-to-chat, NOT demonstrated
productivity improvement. Recording a tab activation is only a proxy for
returning to work. No conversation contents or URLs should be transmitted.

## Current implementation status (development branch)

- Local personal dashboard, weekly metrics, consent-gated local A/B experiment,
  CSV export, and auto-minimize are bundled by GitHub Actions.
- Database migrations 001 and 002 are committed, not applied anywhere.
- A disabled Cloudflare Worker prototype exposes `POST /consent`,
  `POST /ingest`, and `DELETE /withdraw`. It checks a Supabase Auth
  bearer token and a server-side consent record; withdrawal attempts to
  erase all participant event rows.
- The administrator dashboard is currently an offline CSV viewer. It is
  **not** a deployed authenticated website. No research data is uploaded.
- The user extension does not yet contain login, server upload or
  withdrawal UI. Building the complete hosted flow depends on a user-owned
  Supabase project and deployed endpoint, plus browser/penetration testing.

## Cloud setup required before any live research

1. Create a Supabase project and save project URL and anon/public key.
2. Apply migrations `001_research_events.sql` then `002_consent_admin.sql`.
3. In Supabase Auth, configure the participant authentication method.
   Set up your own admin Auth user and add its UUID to `research_admins`
   via a trusted administrator connection.
4. Create a Cloudflare Worker, bind `SUPABASE_URL`, `SUPABASE_ANON_KEY`
   and `SUPABASE_SERVICE_ROLE_KEY` as encrypted secrets.
5. Keep `ENABLE_INGESTION` unset until rate limiting, request origin policy,
   endpoint integration, account and deletion tests, disclosure, and
   explicit production authorization have all been completed.

Do not commit API secrets or provide a service-role key to a browser.
Do not collect study data from users based solely on the local A/B checkbox.
