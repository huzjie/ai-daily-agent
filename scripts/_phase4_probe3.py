#!/usr/bin/env python3
"""Phase-4 discovery probe #3 (read-only): CI failure root-cause + VFS engine facts.

Two goals:
  1. Find which *step* fails in every red CI run, so the replacement workflow is
     provably green instead of optimistically green.
  2. Enumerate the real VideoForge engine adapters / test counts, so the rewritten
     README states facts rather than marketing fiction.
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path
from typing import Any, Dict, List

import requests
import yaml

API_ROOT = "https://api.github.com"
TIMEOUT = 60
ROOT = Path(__file__).resolve().parent.parent

TARGETS = ["loopforge", "unified-ai-gateway", "moe-bench-studio",
           "argus-eval", "video-forge-studio"]


def load_creds() -> tuple[str, str]:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    gh = cfg.get("github", {}) or {}
    return gh.get("username", "huzjie"), gh.get("token", "")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    user, token = load_creds()
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "ai-daily-agent-phase4-probe3",
    })

    print("=" * 70)
    print("A. WHY EACH CI RUN FAILED (failed step names)")
    for repo in TARGETS:
        print(f"\n### {repo}")
        runs = s.get(f"{API_ROOT}/repos/{user}/{repo}/actions/runs",
                     params={"per_page": 20, "branch": "main"}, timeout=TIMEOUT).json()
        ci_runs = [r for r in (runs.get("workflow_runs") or [])
                   if r.get("path", "").endswith("ci.yml")]
        if not ci_runs:
            print("  (no ci.yml run on main)")
            continue
        run = ci_runs[0]
        print(f"  run #{run['id']} conclusion={run.get('conclusion')} at={run.get('created_at')}")
        jobs = s.get(f"{API_ROOT}/repos/{user}/{repo}/actions/runs/{run['id']}/jobs",
                     timeout=TIMEOUT).json()
        for j in jobs.get("jobs", []) or []:
            print(f"   job {j.get('name')!r}: {j.get('conclusion')}")
            for st in j.get("steps", []) or []:
                mark = "  <<< FAILED" if st.get("conclusion") == "failure" else ""
                if st.get("conclusion") in ("failure", "skipped") or mark:
                    print(f"      step {st.get('number')}. {st.get('name')!r} "
                          f"-> {st.get('conclusion')}{mark}")

    print("\n" + "=" * 70)
    print("B. VFS ENGINE ADAPTERS (facts for README matrix)")
    for p in ["src/videoforge", "src/videoforge/engines", "src/videoforge/adapters",
              "src/videoforge/providers", "tests/unit", "tests/api", "tests/integration"]:
        r = s.get(f"{API_ROOT}/repos/{user}/video-forge-studio/contents/{p}", timeout=TIMEOUT)
        if r.status_code == 200 and isinstance(r.json(), list):
            print(f"  {p}/ -> {[x['name'] for x in r.json()]}")
        else:
            print(f"  {p}/ -> {r.status_code}")

    print("\n" + "=" * 70)
    print("C. VFS README full text (preserve true facts)")
    rd = s.get(f"{API_ROOT}/repos/{user}/video-forge-studio/readme", timeout=TIMEOUT)
    if rd.status_code == 200:
        txt = base64.b64decode(rd.json()["content"]).decode("utf-8", "replace")
        print(txt)

    print("\n" + "=" * 70)
    print("D. VFS CHANGELOG head + release body")
    r = s.get(f"{API_ROOT}/repos/{user}/video-forge-studio/contents/CHANGELOG.md",
              timeout=TIMEOUT)
    if r.status_code == 200:
        txt = base64.b64decode(r.json()["content"]).decode("utf-8", "replace")
        print("\n".join(txt.splitlines()[:40]))

    return 0


if __name__ == "__main__":
    sys.exit(main())
