# Prowler Security Dashboard — Live Demo Kit

A fully self-contained, AI-customizable security dashboard built from live
[Prowler](https://github.com/prowler-cloud/prowler) data. One repo, three uses:

1. **Canonical hosted demo** — GitHub Pages serves `index.html` from `main`.
   Always shows the latest blessed version (git tags = versions).
2. **Live-demo sandbox for presenters** — change anything with Claude during a
   customer call; keep it (PR → merge → tag) or discard it (delete branch).
   The public URL is never affected by work in progress.
3. **Self-service template for customers** — anyone with a Prowler account can
   regenerate this dashboard against *their own* findings with the prompt in
   [`prompt/prowler_dashboard_prompt.md`](prompt/prowler_dashboard_prompt.md).

---

## For presenters (5-minute setup)

1. Get access to this repo and clone it.
2. Open the folder with [Claude Code](https://docs.claude.com/en/docs/claude-code)
   (or a Claude Cowork session with the repo connected). Claude reads
   `CLAUDE.md` automatically and knows the design system, the playbooks, and
   the guardrails.
3. During a demo, just ask: *"add a widget showing findings by AWS service"*,
   *"rebrand this for ACME Corp"*, *"toggle off the trend chart"* — Claude
   edits your local `index.html`; refresh the browser to show it live.
   No build step, no dependencies, works offline.
4. Afterwards, tell Claude **"keep it"** (opens a PR; merge + tag publishes a
   new canonical version) or **"discard it"** (nothing ever left your laptop).
5. Need a shareable URL mid-call? Push your branch — it auto-publishes under
   `/preview/<branch>/` and disappears when the branch is deleted.

Data refreshes: run the **Refresh dashboard data** workflow (Actions tab), or
locally `PROWLER_API_KEY=pk_... python3 scripts/refresh_data.py`. The API key
lives only in the repo secret / your env — never in the code.

## For customers — build YOUR dashboard in ~5 minutes

1. In [Prowler Cloud](https://cloud.prowler.com), create an API key
   (Profile → Account → Create API Key).
2. Connect the Prowler MCP server to your AI tool
   ([docs](https://docs.prowler.com/getting-started/basic-usage/prowler-mcp)) —
   for Claude Code:

   ```bash
   claude mcp add prowler --transport http https://mcp.prowler.com/mcp \
     --header "Authorization: Bearer YOUR_API_KEY"
   ```

3. Paste the contents of
   [`prompt/prowler_dashboard_prompt.md`](prompt/prowler_dashboard_prompt.md)
   into your AI tool, filling in the **CUSTOMIZE FOR ME** section.
4. Claude fetches your providers and findings via MCP and generates your own
   single-file dashboard. Iterate from there — it's yours.

Your API key never leaves your machine and is never sent to this repo.

## Repository layout

| Path | Purpose |
|---|---|
| `index.html` | The entire dashboard (single self-contained file) |
| `CLAUDE.md` | Operating manual Claude reads automatically (design system + playbooks) |
| `prompt/` | The generation prompt (template + ready-to-run demo version) |
| `scripts/refresh_data.py` | Rewrites the embedded data snapshot from the Prowler API |
| `.github/workflows/` | Pages deploy, scheduled data refresh, branch previews |

## Versioning & reset model

- `main` + git tags (`v1.0`, `v1.1`, …) are the source of truth; GitHub Pages
  redeploys on every merge to `main`.
- Presenter changes live on branches; visitor-side changes (widget order,
  what-if simulation) live in the visitor's `localStorage` and reset with the
  **Refresh Now** button or a hard reload.
- Rollback = `git revert` or re-deploying a previous tag.

## One-time repo setup (admin)

1. Create the GitHub repo and push this folder.
2. Settings → Pages → Source: **GitHub Actions**.
3. Settings → Secrets and variables → Actions → new secret
   `PROWLER_API_KEY` with a dedicated demo-account key.
4. Run the **Refresh dashboard data** workflow once, then check the Pages URL.
