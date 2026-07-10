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
6. **Prompt/dashboard sync**: any change to the dashboard's design, widgets,
   data contract, or behavior MUST be mirrored in
   `prompt/prowler_dashboard_prompt.md` (and the READY variant) in the same
   PR — the prompt must always regenerate the current dashboard. Update this
   file too when the design system changes.

## Architecture

- `index.html` — the whole dashboard. Sections in order: header comment
  (machine-owned), CSS, DOM skeleton, `PROWLER_DATA` snapshot (machine-owned),
  trend builder, cache/countdown logic, per-widget renderers, drag-and-drop,
  simulation state, findings table, remediation playbook + PR modal.
- `PROWLER_DATA` keys: `generatedAt`, `providers[]`, `overview{total,fail,pass,muted}`,
  `severityCounts{critical..informational}`,
  `perProvider{alias → {fail,pass,sev{...},estimated}}` (feeds the filter bar),
  `findings[]{sev,provider,service,status,check,resource,region,detail}`,
  `topCritical[]{sev,provider,check,title,resource,region,risk,steps[]}`, `trend[7]`.
  The trend series is derived at runtime by `trendSeries()` — deterministic
  sin+cos backfill anchored at `generatedAt`, ending at the SELECTION's live
  counts, with `TREND_RANGE` (1W/1M/6M/1Y) controlling points and step.
  Default widget order: compliance (ThreatScore), donut, checks, then rows.
- Client state in `localStorage`: `prowler_layout_v1` (widget order + column
  spans; the providers filter panel is widget id `providers`),
  `prowler_cached_data` + `prowler_last_fetch` (24h cache). This is why
  every demo edit is reversible: clearing storage + reloading = canonical state.
  Cache invalidation rule: on load, the cache is used ONLY if its `generatedAt`
  is >= the embedded snapshot's — a newer deployed dashboard always beats a
  stale cache (Chrome shares localStorage across all file:// pages, and Pages
  visitors keep storage across versions). Never remove this guard.
- `PR_DEFAULTS` (between `==PR_DEFAULTS_START/END==` sentinels) holds the
  GitHub repo / branch / labels used by the "Create GitHub PR" modal.
- **Provider filter panel** (`#filterBar`, under the header): hierarchical —
  UNIFORM compact cards per provider TYPE (official badge SVG in
  `PROVIDER_LOGOS`, embedded inline from prowler-cloud/prowler
  `ui/components/icons/providers-badge/`). Every type card opens an
  account-chip POPOVER on click (`OPEN_PTYPE` state; survives re-render;
  closes on outside click; never dimmed) — uniform behavior for single- and
  multi-account types so account tags are always identifiable. The
  `FILTER` Set (account aliases) drives `selectedCounts()` /
  `selectedOverview()`, which EVERY widget reads (never read
  `PROWLER_DATA.severityCounts/overview` directly in a renderer). Findings and
  playbook rows filter on their `provider` field; the trend scales by the
  selection's share of fails; the simulation composes with the filter.
  Selection is session-only — do not persist it.
- Widgets: providers (filter panel), compliance (ThreatScore), donut,
  checks (Checks Summary), sparkline (trend), topcrit (playbook),
  findings (table). All draggable (insertion reorder + FLIP animation) and
  resizable (right-edge bar, 3–12 grid columns, layout persisted).
  New widgets must include BOTH the ⠿ drag handle and the `.resize-h` bar,
  set `data-colspan`, and register {id, col} in WIDGETS.
- **Header honesty rules**: the freshness badge says SNAPSHOT (never "LIVE"),
  flips to amber STALE past 7 days, and opens a provenance popover on click.
  The primary button is "Reset Demo" (clears cache + order + filter + sim —
  it does NOT fetch data; only the refresh script/CI does). The age chip
  counts UP from `generatedAt`. The "View on GitHub" button href must always
  point at the repo's CURRENT home — update it in the same commit whenever the
  repo is renamed or transferred (e.g. to the prowler-cloud org). Keep the customer lockup (ACME by default)
  under the Prowler wordmark — swap its inline SVG when branding for a real
  customer (see "Change branding" playbook).

## Design system (match exactly on any new widget)

Prowler Cloud visual schema — tokens from prowler-cloud/prowler
`ui/styles/globals.css` (dark theme). Do NOT invent colors.

- Font: Inter (Google Fonts `<link>` = the ONLY allowed external reference;
  offline it falls back to the system stack — never add other external refs).
- Dark theme, body gradient `#000000 → #121110`, `background-attachment:fixed`.
- Cards: solid `#0c0a09` bg, 1px `#27272a` border, radius 18px (no glassmorphism).
- Accents: primary emerald `#6ee7b7` (hover `#99f6e4`), secondary blue `#3c8dff`.
  Primary buttons are solid emerald with BLACK text.
- Severity (Prowler scale): critical `#ff006a`, high `#f77852`, medium `#fec94d`,
  low `#fdfbd4`, informational `#3c8dff`. Pass `#4ade80`, fail `#f43f5e`.
- Provider chips: aws `#f59e0b`, azure `#38bdf8`, gcp `#ef4444`, kubernetes
  `#4f46e5`, m365 `#4ade80`, github `#e5e5e5`, okta `#3c8dff`, default emerald.
- Header logo: the OFFICIAL ProwlerExtended wordmark (inline SVG, white fill,
  from `ui/components/icons/prowler/ProwlerIcons.tsx`).
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
