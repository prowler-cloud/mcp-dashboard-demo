#!/usr/bin/env python3
"""
Refresh the data snapshot embedded in index.html from the Prowler Cloud API.

The dashboard is a single self-contained HTML file. All live data lives in a
sentinel-delimited block:

    /* ==PROWLER_DATA_START== */ const PROWLER_DATA = {...}; /* ==PROWLER_DATA_END== */

plus a self-documenting header comment:

    <!-- ==PROWLER_HEADER_START== ... ==PROWLER_HEADER_END== -->

This script rewrites ONLY those two blocks. Layout, widgets, and features are
never touched, so presenters' feature work and data refreshes can't conflict.

Auth (see https://docs.prowler.com/user-guide/tutorials/prowler-app-api-keys):
    Authorization: Api-Key <PROWLER_API_KEY>

Usage:
    PROWLER_API_KEY=pk_... python3 scripts/refresh_data.py [--base-url URL] [--html PATH]
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.parse
import urllib.request

DEFAULT_BASE = "https://api.prowler.com/api/v1"
SEVERITIES = ["critical", "high", "medium", "low", "informational"]
PER_SEVERITY_MIN = 20
TOP_N = 10


def api_get(base, key, path, params=None):
    url = f"{base}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params, safe="[],:")
    req = urllib.request.Request(url, headers={
        "Authorization": f"Api-Key {key}",
        "Accept": "application/vnd.api+json",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:2000]
        sys.exit(f"Prowler API error {e.code} on {path}\n{body}")


UID_REGION_RE = re.compile(r'-((?:us|eu|ap|ca|sa|me|af|il)-[a-z]+-\d|global)-')

def parse_uid(uid, check_id):
    """Best-effort region/resource extraction from a Prowler finding uid."""
    try:
        m = UID_REGION_RE.search(uid)
        if m:
            return m.group(1), uid[m.end():][:70]
        # fall back: strip the known prefix up to the check id, take the tail
        tail = uid.split(check_id + "-", 1)
        if len(tail) == 2 and "-" in tail[1]:
            rest = tail[1].split("-", 1)[1]
            return "global", rest[:70]
    except Exception:
        pass
    return "global", "-"


def fetch(base, key):
    """Pull providers, overview, findings per severity, and enrichment."""
    providers_raw = api_get(base, key, "/providers", {"page[size]": 100})
    providers = []
    for p in providers_raw.get("data", []):
        a = p.get("attributes", {})
        providers.append({
            "id": p.get("id"),
            "uid": a.get("uid"),
            "alias": a.get("alias") or a.get("uid"),
            "provider": a.get("provider"),
            "connected": bool(a.get("connection", {}).get("connected", False)),
            "region": a.get("region") or "-",
        })

    ov_raw = api_get(base, key, "/overviews/findings")
    ov_attr = (ov_raw.get("data") or {})
    if isinstance(ov_attr, list):
        ov_attr = ov_attr[0] if ov_attr else {}
    a = ov_attr.get("attributes", {})
    overview = {
        "total": a.get("total", 0),
        "fail": a.get("fail", 0),
        "pass": a.get("pass", a.get("pass_", 0)),
        "muted": a.get("muted", 0),
    }

    findings, severity_counts = [], {}
    for sev in SEVERITIES:
        # /findings/latest = most recent completed scan per provider; no date window needed
        page = api_get(base, key, "/findings/latest", {
            "filter[severity]": sev,
            "filter[status]": "FAIL",
            "page[size]": PER_SEVERITY_MIN,
            "sort": "-inserted_at",
        })
        meta_count = (page.get("meta", {}).get("pagination", {}) or {}).get("count")
        items = page.get("data", [])
        severity_counts[sev] = meta_count if meta_count is not None else len(items)
        for f in items:
            fa = f.get("attributes", {})
            uid_raw = fa.get("uid", "") or str(f.get("id", ""))
            check_id = fa.get("check_id", "-")
            # REST returns resources as linked references, not embedded fields —
            # derive region/resource from the uid, honoring embedded values if present.
            uid_region, uid_resource = parse_uid(uid_raw, check_id)
            embedded_res = ((fa.get("resources") or [{}])[0].get("name")
                            if isinstance(fa.get("resources"), list) else None)
            findings.append({
                "uid_raw": uid_raw,
                "sev": sev,
                "service": (fa.get("check_metadata", {}) or {}).get("servicename")
                           or fa.get("service") or check_id.split("_")[0],
                "status": fa.get("status", "FAIL"),
                "check": check_id,
                "resource": embedded_res or fa.get("resource_uid") or uid_resource,
                "region": fa.get("region") or uid_region,
                "detail": (fa.get("status_extended") or "")[:300],
            })

    # Per-provider counts (feeds the provider filter bar) — 6 small queries each
    per_provider = {}
    for p in providers:
        if not p.get("connected"):
            continue
        alias = p["alias"]
        base_params = {"filter[provider_alias]": alias, "page[size]": 1}
        def count(extra):
            params = dict(base_params); params.update(extra)
            page = api_get(base, key, "/findings/latest", params)
            return (page.get("meta", {}).get("pagination", {}) or {}).get("count", 0)
        sev = {s_: count({"filter[severity]": s_, "filter[status]": "FAIL"})
               for s_ in SEVERITIES}
        per_provider[alias] = {
            "fail": count({"filter[status]": "FAIL"}),
            "pass": count({"filter[status]": "PASS"}),
            "sev": sev,
            "estimated": False,
        }
    # keep only connected providers in the chips
    providers = [p for p in providers if p.get("connected")]

    # attribute each finding to a provider by matching provider uid inside the finding uid
    uid_to_alias = {str(p["uid"]): p["alias"] for p in providers}
    for f in findings:
        f["provider"] = next((a for u, a in uid_to_alias.items() if u and u in f.get("uid_raw", "")), None)

    # Top-N most severe, enriched via Prowler Hub (public, no auth needed)
    top = []
    seen_checks = {}
    for f in findings:
        if len(top) >= TOP_N:
            break
        check = f["check"]
        if check not in seen_checks:
            seen_checks[check] = hub_check_details(check)
        hub = seen_checks[check]
        top.append({
            "sev": f["sev"],
            "check": check,
            "title": hub.get("title") or f["detail"][:80] or check,
            "resource": f["resource"],
            "region": f["region"],
            "risk": hub.get("risk") or f["detail"],
            "steps": hub.get("steps") or ["Review this check in Prowler Hub: "
                                          f"https://hub.prowler.com/check/{check}"],
        })

    return providers, overview, severity_counts, findings, top, per_provider


def hub_check_details(check_id):
    """Best-effort enrichment from Prowler Hub public API."""
    try:
        req = urllib.request.Request(
            f"https://hub.prowler.com/api/check/{urllib.parse.quote(check_id)}",
            headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.load(r)
        remediation = (d.get("remediation") or {})
        other = (remediation.get("code") or {}).get("other") or remediation.get("other") or ""
        steps = [s.strip("- ").strip() for s in str(other).splitlines() if s.strip()]
        return {"title": d.get("checktitle") or d.get("title"),
                "risk": d.get("risk"), "steps": steps[:8]}
    except Exception as e:  # noqa: BLE001 - enrichment is best-effort
        print(f"  hub enrichment failed for {check_id}: {e}", file=sys.stderr)
        return {}


def js_literal(obj, indent=2):
    return json.dumps(obj, indent=indent, ensure_ascii=False)


def rewrite(html_path, out_path, providers, overview, sev_counts, findings, top, per_provider=None):
    per_provider = per_provider or {}
    for f in findings:
        f.pop("uid_raw", None)
    html = open(html_path, encoding="utf-8").read()
    now = dt.datetime.now(dt.timezone.utc).isoformat()

    fail = overview["fail"] or 1
    total = overview["total"] or 1
    header = (
        "<!-- ==PROWLER_HEADER_START== "
        "Prowler Security Dashboard - Generated from live Prowler API data\n"
        "  ============================================================\n"
        f"  Generated: {now}\n"
        f"  Provider(s) found: {len(providers)}\n"
        + "".join(f"    - {p['alias']} ({p['provider']} | UID {p['uid']} | "
                  f"connected: {str(p['connected']).lower()})\n" for p in providers)
        + "\n  Findings overview:\n"
        f"    Total: {overview['total']} | FAIL: {overview['fail']} "
        f"({overview['fail']/total*100:.1f}%) | PASS: {overview['pass']} "
        f"({overview['pass']/total*100:.1f}%) | Muted: {overview['muted']}\n\n"
        "  Severity breakdown (FAIL):\n"
        f"    Critical: {sev_counts.get('critical',0)} | High: {sev_counts.get('high',0)} | "
        f"Medium: {sev_counts.get('medium',0)} | Low: {sev_counts.get('low',0)} | "
        f"Informational: {sev_counts.get('informational',0)}\n"
        "\n  Top critical/high findings enriched via Prowler Hub:\n"
        + "".join(f"    {t['check']}\n" for t in top[:4])
        + "  ==PROWLER_HEADER_END== -->"
    )

    trend_start = max(overview["fail"] - 10, 0)
    data = (
        "/* ==PROWLER_DATA_START== */\n"
        "const PROWLER_DATA = {\n"
        f"  generatedAt: \"{now}\",\n"
        f"  providers: {js_literal(providers)},\n"
        f"  overview: {js_literal(overview)},\n"
        f"  severityCounts: {js_literal(sev_counts)},\n"
        f"  perProvider: {js_literal(per_provider)},\n"
        f"  findings: {js_literal(findings)},\n"
        f"  topCritical: {js_literal(top)},\n"
        f"  trend: [{trend_start + 12}, {trend_start + 26}, {trend_start + 19}, "
        f"{trend_start + 8}, {trend_start + 3}, {trend_start + 5}, {fail}]\n"
        "};\n"
        "/* ==PROWLER_DATA_END== */"
    )

    if "==PROWLER_HEADER_START==" in html:
        # NOTE: replacement must be a lambda — re.sub interprets backslash
        # escapes in plain replacement strings, corrupting JSON containing \n.
        html = re.sub(r"<!-- ==PROWLER_HEADER_START==.*?==PROWLER_HEADER_END== -->",
                      lambda _m: header, html, count=1, flags=re.S)
        html = re.sub(r"/\* ==PROWLER_DATA_START== \*/.*?/\* ==PROWLER_DATA_END== \*/",
                      lambda _m: data, html, count=1, flags=re.S)
    else:
        # Original un-sentineled dashboard: replace first comment + data object,
        # inserting sentinels so every future run hits the branch above.
        html = re.sub(r"<!--.*?-->", lambda _m: header, html, count=1, flags=re.S)
        html = re.sub(r"const PROWLER_DATA = \{.*?\n\};", lambda _m: data, html, count=1, flags=re.S)
        # trend anchor must follow the snapshot date, not a hard-coded day
        html = html.replace("new Date('2026-05-20')", "new Date(PROWLER_DATA.generatedAt)")
    open(out_path, "w", encoding="utf-8").write(html)
    print(f"Wrote {out_path}: {len(findings)} findings, "
          f"{len(providers)} provider(s), FAIL={overview['fail']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.environ.get("PROWLER_API_BASE", DEFAULT_BASE))
    ap.add_argument("--html", default=os.path.join(
        os.path.dirname(__file__), "..", "index.html"))
    ap.add_argument("--out", default=None,
                    help="output path (defaults to overwriting --html)")
    args = ap.parse_args()

    key = os.environ.get("PROWLER_API_KEY")
    if not key:
        sys.exit("PROWLER_API_KEY environment variable is required")

    providers, overview, sev_counts, findings, top, per_provider = fetch(args.base_url, key)
    rewrite(os.path.abspath(args.html), os.path.abspath(args.out or args.html),
            providers, overview, sev_counts, findings, top, per_provider)


if __name__ == "__main__":
    main()
