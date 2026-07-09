# Prowler Dashboard Demo — Claude Operating Manual

You are working on the Prowler Security Dashboard demo: a single self-contained
HTML file (`index.html`) that presenters customize live in front of customers.
Read this whole file before making any change.

## Golden rules

1. **NEVER commit or push to `main` directly.** All changes go on a feature
   branch (`demo/<short-name>` or `fix/<short-name>`). Promotion to `main`
   happens only via a reviewed PR, after which the change is tagged as a new
   version (`vX.Y`).
2. **`index.html` must stay a single self-contained file.** All CSS and JS
   inline. Zero external libraries, zero CDN links, all charts as inline SVG.
   This is what makes the demo portable and offline-safe — do not break it.
3. **Never edit inside the sentinel blocks by hand:**
   - `<!-- ==PROWLER_HEADER_START== ... ==PROWLER_HEADER_END== -->` and
   - `/* ==PROWLER_DATA_START== */ ... /* ==PROWLER_DATA_END== */`
   are machine-owned; `scripts/refresh_data.py` (and the
   `refresh-data` GitHub Action) rewrite them from the Prowler API. Feature
   code must only READ `PROWLER_DATA`, never redefine it.
4. **Secrets never enter the repo.** The Prowler API key lives only in the
   GitHub Actions secret `PROWLER_API_KEY` and in presenters' local env vars.
5. All renderers must be safe to re-run in place (the simulation toggle,
   table sort/page, tooltips depend on this).

## Architecture

- `index.html` — the whole dashboard. Sections in order: header comment
  (machine-owned), CSS, DOM skeleton, `PROWLER_DATA` snapshot (machine-owned),
  trend builder, cache/countdown logic, per-widget renderers, drag-and-drop,
  simulation state, findings table, remediation playbook + PR modal.
- `PROWLER_DATA` keys: `generatedAt`, `providers[]`, `overview{total,fail,pass,muted}`,
  `severityCounts{critical..informational}`, `findings[]{sev,service,status,check,resource,region,detail}`,
  `topCritical[]{sev,check,title,resource,region,risk,steps[]}`, `trend[7]`.
  A 30-day series `trend30` is derived at runtime by `buildTrend30()` —
  deterministic sin+cos noise anchored at `generatedAt`, ending at live counts.
- Client state in `localStorage`: `prowler_widget_order` (drag order),
  `prowler_cached_data` + `prowler_last_fetch` (24h cache). This is why
  every demo edit is reversible: clearing storage + reloading = canonical state.
  Cache invalidation rule: on load, the cache is used ONLY if its `generatedAt`
  is >= the embedded snapshot's — a newer deployed dashboard always beats a
  stale cache (Chrome shares localStorage across all file:// pages, and Pages
  visitors keep storage across versions). Never remove this guard.
- `PR_DEFAULTS` (between `==PR_DEFAULTS_START/END==` sentinels) holds the
  GitHub repo / branch / labels used by the "Create GitHub PR" modal.

## Design system (match exactly on any new widget)

- Dark theme, body gradient `#0a0e27 → #131830`, `background-attachment:fixed`.
- Glassmorphism cards: `rgba(255,255,255,0.04)` bg, 1px `rgba(255,255,255,0.08)`
  border, `backdrop-filter:blur(20px)`, radius 18px.
- Accents: primary green `#00ff88`, secondary purple `#7c3aed`.
- Severity: critical `#ff3860`, high `#ff8c42`, medium `#ffd93d`,
  low `#3abff8`, informational `#94a3b8`.
- Every widget: `<div class="widget" draggable="true">` + drag handle `⠿` +
  `.widget-title` uppercase label; hover = lift + green glow (comes free from
  the `.widget` class).
- Grid: 12-column, `col-3/4/5/6/7/8/12` span classes, single column <768px.
- Charts: inline SVG only. Reuse existing helpers/patterns (donut, gauge,
  line chart) before inventing new ones.

## Playbooks

### "Add a widget" (most common live-demo request)
1. Create a branch: `git checkout -b demo/<name>`.
2. Add a `<div class="widget" draggable="true">` with drag handle and
   `.widget-title`, in the grid with an appropriate `col-*` class.
3. Write its renderer as a function reading from `PROWLER_DATA` (respect the
   simulation state object if severity counts are involved), call it from the
   main render flow, keep it re-runnable.
4. Register the widget in the drag-order logic (it keys off DOM ids).
5. Open `index.html` in the browser to verify, then show it live.

### "Change branding / customize for an org"
- Swap CSS variables in `:root` for the palette; replace the inline SVG logo
  in the header; update `PR_DEFAULTS` between its sentinels.

### "Refresh data"
- Locally: `PROWLER_API_KEY=pk_... python3 scripts/refresh_data.py`.
- Or run the **Refresh dashboard data** workflow in GitHub Actions (uses the
  repo secret). Never paste an API key into the HTML or commit it.

### "Keep it" (promote a live-demo change)
1. Commit on the feature branch, push, open a PR to `main`.
2. After merge, tag: `git tag vX.Y && git push --tags` — the Pages workflow
   redeploys the canonical site automatically.

### "Discard it"
- `git checkout -- index.html` (uncommitted) or delete the branch. The public
  URL was never affected. Also remind the presenter that visitor-side edits
  (widget order, simulation) reset via the Refresh Now button or
  `localStorage.clear()` + reload.

### "Share a preview mid-demo"
- Push the feature branch; the `preview` workflow publishes it at
  `<pages-url>/preview/<branch-with-dashes>/`. Deleting the branch retires it.

## Verification before any handoff

Open the file in a browser (or headless Chromium) and confirm: no console
errors, all 6 widgets render, drag-and-drop reorders and persists, the
"What if I fix N criticals" simulation toggles and resets, table sorts,
searches and paginates, the playbook accordion expands, and the PR modal
opens with correctly encoded compare URL.
