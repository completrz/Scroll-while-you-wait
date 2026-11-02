# Auto-minimize and analytics feature branch

Current production extension is stored as `reels-while-you-wait.zip` on main.
This branch deliberately preserves that ZIP unchanged.

## Auto-minimize
Run `python scripts/build-auto-minimize.py` at the repository root.
This creates `reels-while-you-wait-auto-minimize.zip`; extract it and choose
the nested `reels-while-you-wait` folder in Chrome's **Load unpacked**.
The auto-minimize option is enabled by default; it restores the managed video
window on the next AI response and does not change the three video providers
or eight supported AI sites.

This is an implementation, not proof of compatibility across Chrome versions.
Test overlapping responses, streaming text, manual pause and close, and focus
restoration before replacing a published build.

## Research system (development only)
- `supabase/migrations/001_research_events.sql`: schema with RLS and no
  client access policies. **Not deployed**.
- `analysis/analyze.py`: offline analysis script for a consented CSV export.
- No analytics uploads are present or enabled in the production extension.
- A future user dashboard should work entirely locally without login.
- A future admin dashboard needs secure login, backend validation of opt-in,
  deletion and withdrawal endpoints, throttling, retention rules, and robust
  handling of sessions in which participants never return.

Do not enable ingestion or claim measured productivity benefits until the
research workflow is reviewed and tested.

## Local focus dashboard
The build script now includes a private dashboard opened through the extension popup. Metrics include completed response durations and observed return-to-chat latencies. These are **not** equivalent to productivity gains. The metric currently records a return when the user switches back to the AI tab; users who stay on the AI tab may have no observed return. The collector is an early prototype and needs additional tests for service-worker suspension, absent return events, already-focused tabs, and multiple overlapping sessions. No analytics are uploaded. The dashboard includes local CSV export and deletion.
