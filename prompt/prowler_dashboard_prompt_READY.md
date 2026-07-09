# Prowler Security Dashboard — Customer Prompt

Ready-to-run version — the CUSTOMIZE FOR ME values below are pre-filled with
the exact values used in the existing demo dashboard (prowler_dashboard.html),
so re-running this in Claude Code with the Prowler MCP server reproduces it 1:1.
Copy everything below the line into Claude Code.

---

Generate a security dashboard for my organization using live data from the
Prowler MCP tools. Build a single self-contained HTML file and open it.

# DATA TO FETCH (in this order, via Prowler MCP)

1. `prowler_app_search_providers` — list every configured provider
2. `prowler_app_get_findings_overview` — total / fail / pass / muted counts
3. `prowler_app_search_security_findings` filtered by severity (one call per
   severity: critical, high, medium, low, informational) — pull at least
   20 of each for the table. Default status is FAIL, keep it that way.
4. Per-provider counts for the filter bar: for EACH connected provider,
   count FAIL, PASS, and per-severity FAIL findings (count-only queries,
   page size 1) so every widget can recompute per selection.
5. For the 10 most critical (or highest-severity) findings, call
   `prowler_hub_get_check_details` for each unique check_id to enrich them
   with `risk`, `remediation.other` step list, and remediation context.

# OUTPUT REQUIREMENTS

- Single HTML file, all CSS + JS embedded inline, zero external libraries
- Open the file when done
- Include a comment block at the top summarising providers found and
  finding counts so the file is self-documenting

# DESIGN SYSTEM — Prowler Cloud visual schema
(tokens from prowler-cloud/prowler `ui/styles/globals.css`, dark theme)

- Font: **Inter** (Google Fonts link as progressive enhancement — the font
  `<link>` is the ONLY allowed external reference; offline it falls back to the
  system stack `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto`)
- Dark theme: background gradient `#000000 → #121110`, cards solid `#0c0a09`
  with 1px `#27272a` border (no glassmorphism), radius 18px
- Brand accents: primary emerald `#6ee7b7` (hover `#99f6e4`), secondary blue `#3c8dff`
- Text: `#ffffff` primary, `#a1a1aa` muted
- Severity colors (Prowler scale): critical `#ff006a`, high `#f77852`,
  medium `#fec94d`, low `#fdfbd4`, informational `#3c8dff`
- Status: pass `#4ade80`, fail `#f43f5e`
- Provider chip colors: aws `#f59e0b`, azure `#38bdf8`, gcp `#ef4444`,
  kubernetes `#4f46e5`, m365 `#4ade80`, github `#e5e5e5`, okta `#3c8dff`;
  default emerald. Dark text on light chips, white on dark chips.
- Primary buttons: solid emerald `#6ee7b7` with black text (Prowler style)
- Animated "LIVE DATA" badge (pulsing emerald dot)
- Hover effects on every card: lift transform, emerald glow, border shift
- Responsive 12-column grid, single-column below 768px
- Use inline SVG for every chart — NO Chart.js, NO d3, NO external JS deps

# HEADER BAR

- The OFFICIAL Prowler wordmark as inline SVG in the top-left (white fill,
  max-height 34px, subtle emerald drop-shadow). Source: `ProwlerExtended` in
  prowler-cloud/prowler `ui/components/icons/prowler/ProwlerIcons.tsx`
  (viewBox 0 0 1233.67 204.4). Title next to it reads just "Security Dashboard"
  — the wordmark already says Prowler.
- Dashboard title + subtitle
- Pulsing "LIVE DATA" badge
- "View on GitHub" button linking to https://github.com/prowler-cloud/prowler
- "Refresh Now" button that clears the localStorage cache
- Countdown timer "Next refresh in HH:MM:SS" ticking down from 24:00:00
- Generated-at timestamp

# PROVIDER FILTER PANEL — directly under the header

- A panel (own card) titled "Cloud Providers" using the SAME `.widget-title`
  typography as every widget, with "All" / "None" controls and a
  "N/M accounts selected · filters the whole dashboard" note.
- HIERARCHY — provider type → accounts: a responsive grid
  (auto-fill, minmax 250px) of one card per provider TYPE. Each type card has:
  the OFFICIAL provider badge logo as inline SVG (source:
  `ui/components/icons/providers-badge/` in prowler-cloud/prowler — embed the
  SVGs, no external images), the type display name, a "sel/total · N fail"
  meta, and its account chips beneath.
- Clicking a type header toggles ALL of that type's accounts at once;
  clicking an account chip toggles just that account. Deselected chips dim
  to ~40% opacity; fully-deselected type cards dim as a whole.
- (When Prowler provider groups are in use, insert them as an org level
  between type and accounts.)
- The selection filters the ENTIRE dashboard: every widget (checks summary,
  severity donut, ThreatScore, trend, findings table, remediation playbook)
  recomputes from the selected providers only.
- Data contract: `PROWLER_DATA.perProvider` maps alias → {fail, pass,
  sev{critical..informational}, estimated}. All widget math flows through
  `selectedCounts()` / `selectedOverview()`, which sum perProvider over the
  active selection. Each finding carries a `provider` field for row filtering.
- The trend chart scales its series by the selection's share of total fails.
- The what-if simulation composes with the filter (it zeroes the SELECTION'S
  criticals, and its button label shows the selection's critical count).
- Selection is session-only — never persisted; reload = all providers.

# WIDGETS — each one inside a `<div class="widget" draggable="true">` with a
visible drag handle (⠿) in the top-left corner.

## 1. Checks Summary
- Failed Checks / Passed / Total stat row (numbers reflect the provider
  selection; ±delta badges when the simulation is active)
- Pass-rate bar (emerald gradient, glow)
- Caption: "N of M providers in scope", noting when severity splits are
  partly estimated for small providers

## 2. Severity Breakdown — pure-SVG donut chart
- Donut with one segment per severity, total FAIL count in the center
  (display the true 0 when the selection is empty — guard only the geometry)
- 3px gaps between slices and skip zero-value slices entirely — the pale
  `low` color must read as a deliberate slice on the dark theme, and
  zero-length arcs must not paint cap artifacts
- Legend on the right with counts
- Below the chart: an **"⚡ What if I fix N critical findings?"** button.
  When clicked:
    - Set criticals to 0 in a simulation state object
    - Re-render this widget, the Checks Summary widget, and the ThreatScore
      widget in place (preserve drag order, no full rebuild)
    - Show a "SIMULATED" pill on each affected widget title
    - Show ±delta badges next to Failed Checks and Passed counts
    - Strike-through the Critical row in the donut legend
    - Button flips to "✓ Showing impact · click to reset" with green styling
- Critical count = 0 hides the button entirely

## 3. ThreatScore (radial gauge)
- Pure SVG circular gradient ring (green → purple)
- Center shows the ThreatScore (0–100): a severity-weighted pass ratio that
  is robust at ANY scale (a 12-finding provider or an 11k-finding tenant):
    `weightedFail = critical×25 + high×2.5 + medium×0.5 + low×0.2`
    `score = 100 × passed / (passed + weightedFail)`
  Criticals dominate the denominator so the what-if simulation moves the
  score visibly. When the provider selection is empty, show an em-dash and
  "select at least one provider" — never a phantom 100. Skip drawing the
  progress arc when its length is ~0 (a round line-cap would paint a
  floating dot).
- Below the ring: "PASS/TOTAL passing · X% pass rate"
- When simulation is active, show a `+N.N pts from fixing criticals` delta

## 4. 30-Day Findings Trend — multi-series SVG line chart
- 30 daily data points ending today
- 4 lines: Critical / High / Medium / Low, each in its severity color, with
  a faint area-fill underneath
- Gridlines + Y-axis labels (0 to max rounded to nearest 20) + X-axis date
  labels every 5 days in MM/DD format
- Legend chips above the chart; **clicking a chip toggles that line on/off**
  and the totals in the tooltip recompute
- Hover anywhere on the plot:
    - vertical dashed crosshair snaps to nearest day
    - dots appear on every visible line at that day's value
    - floating tooltip shows full date ("Wed, May 20, 2026"), per-severity
      counts with color swatches, and a Total FAIL row
    - tooltip auto-flips at right/bottom edges to stay in viewport
- Touch support: dragging a finger updates the tooltip
- Data: if Prowler doesn't expose 30-day history, generate a deterministic
  back-trend ending at the live counts using sin+cos noise so the chart
  doesn't look fake-smooth and is stable across reloads

## 5. Findings Table
- Paginated, 20 rows per page
- Sortable columns: Severity, Service, Status, Check ID, Resource, Region
- Severity-coloured badge per row
- Search bar above the table — filters across all columns
- Pagination shows "1–20 of N" + numbered page buttons with ellipsis

## 6. Top 10 Critical Findings · Remediation Playbook
- Accordion list, one card per top finding
- Card header: severity badge + finding title + resource/region/check-id
- Expanded body shows:
    - Risk explanation (red-bordered callout) from Prowler Hub
    - Numbered Remediation Steps as **checkboxes** users can tick off
      (with strike-through when checked)
    - **"📤 Create GitHub PR" button** — opens a MODAL DIALOG (not a direct
      link). Modal contains editable fields, pre-populated for this
      organisation's workflow:
        - Repository (default: `<OWNER>/<REPO>`)
        - Base branch (default: `main`)
        - Head branch (default: `<fix/branch-name>`)
        - Labels (default: `<label1>, <label2>`)
        - PR Title (default: `fix: remediate [check-id] - [title]`)
        - PR Body — markdown textarea pre-filled with:
            `## Remediation: [title]`
            `**Resource:** … **Region:** … **Severity:** … **Check ID:** …`
            `### Risk\n[risk]`
            `### Steps\n- [ ] step 1\n- [ ] step 2 …`
            `---\nGenerated by Prowler MCP Dashboard`
        - Tip box with the three git commands needed before submitting
          (checkout, commit, push)
    - Modal actions: Cancel · 📋 Copy Markdown · Submit to GitHub →
    - Submit opens the new tab to:
        `https://github.com/OWNER/REPO/compare/BASE...HEAD?quick_pull=1&title=…&body=…&labels=…`
        — note: encode branch path segment-by-segment so slashes in
        `fix/branch-name` stay literal (GitHub requires this)
    - Esc / click-backdrop / × button all dismiss

# INTERACTIVITY

- **Drag-and-drop widget reordering** using the HTML5 DnD API:
  on dragstart store index; on drop, swap DOM positions; persist the new
  order to `localStorage` under key `prowler_widget_order`. On page load,
  restore order before rendering.
- **24h caching**: write `prowler_cached_data` + `prowler_last_fetch` ISO
  timestamp to localStorage on first load. On subsequent loads within 24h,
  render from cache and continue the countdown. After 24h, re-fetch from
  MCP. Include `<meta http-equiv="refresh" content="86400">` as a fallback.
  **Cache invalidation**: on load, use the cache ONLY if its `generatedAt` is
  >= the embedded snapshot's — a newer deployed dashboard must always beat a
  stale cache (localStorage is shared across file:// pages and persists for
  returning Pages visitors).
- Manual "Refresh Now" button clears the cache and forces re-fetch.
- All renderers must be safe to re-run in place when state changes
  (simulation toggle, table sort/page, tooltip).

# CUSTOMIZE FOR ME

Before generating, replace these defaults with my organisation's values:

- **GitHub repo:** `acme-cloud-infra/cloud-infrastructure`
- **Default head branch:** `fix/prowler-remediation`
- **Default PR labels:** `Remediation`
