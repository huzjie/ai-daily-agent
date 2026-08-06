#!/usr/bin/env python3
"""Phase-4 discovery probe (read-only).

Collects everything the Phase-4 optimizer needs to know before writing anything:
token scopes, repo metadata, workflows, root file listings, releases and README
badge lines. Read-only: issues no PUT/POST/PATCH requests at all.
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import requests
import yaml

API_ROOT = "https://api.github.com"
TIMEOUT = 60
ROOT = Path(__file__).resolve().parent.parent

FLAGSHIP: List[str] = [
    "loopforge",
    "unified-ai-gateway",
    "moe-bench-studio",
    "argus-eval",
    "video-forge-studio",
    "ai-daily-agent",
]


def load_token() -> tuple[str, str]:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    gh = cfg.get("github", {}) or {}
    return gh.get("username", "huzjie"), gh.get("token", "")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    user, token = load_token()
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "ai-daily-agent-phase4-probe",
    })

    print("=" * 70)
    print("0. TOKEN SCOPES")
    r = s.get(f"{API_ROOT}/user", timeout=TIMEOUT)
    print(f"  status={r.status_code} login={r.json().get('login')}")
    print(f"  X-OAuth-Scopes: {r.headers.get('X-OAuth-Scopes')}")
    print(f"  rate-remaining: {r.headers.get('X-RateLimit-Remaining')}")

    print("=" * 70)
    print("1. REPOS")
    repos: List[Dict[str, Any]] = []
    page = 1
    while True:
        rr = s.get(f"{API_ROOT}/user/repos",
                   params={"per_page": 100, "page": page, "affiliation": "owner"},
                   timeout=TIMEOUT)
        batch = rr.json()
        if not isinstance(batch, list) or not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    for rp in sorted(repos, key=lambda x: x["name"]):
        print(f"  - {rp['name']:<45} lang={str(rp.get('language')):<12} "
              f"branch={rp.get('default_branch')} "
              f"desc={'Y' if rp.get('description') else 'N'} "
              f"home={'Y' if rp.get('homepage') else 'N'} "
              f"topics={len(rp.get('topics') or [])} "
              f"disc={rp.get('has_discussions')} "
              f"pushed={str(rp.get('pushed_at'))[:10]}")

    print("=" * 70)
    print("2. PER-FLAGSHIP DETAIL")
    for repo in FLAGSHIP:
        print(f"\n### {repo}")
        info = s.get(f"{API_ROOT}/repos/{user}/{repo}", timeout=TIMEOUT).json()
        if "full_name" not in info:
            print(f"  !! not found: {str(info)[:150]}")
            continue
        br = info.get("default_branch", "main")
        print(f"  branch={br} lang={info.get('language')} size={info.get('size')}KB")
        print(f"  desc={info.get('description')}")
        print(f"  homepage={info.get('homepage')}")
        print(f"  topics={info.get('topics')}")
        print(f"  has_discussions={info.get('has_discussions')} "
              f"has_issues={info.get('has_issues')}")

        # languages
        langs = s.get(f"{API_ROOT}/repos/{user}/{repo}/languages", timeout=TIMEOUT).json()
        print(f"  languages={langs}")

        # workflows
        wf = s.get(f"{API_ROOT}/repos/{user}/{repo}/actions/workflows", timeout=TIMEOUT)
        wj = wf.json()
        print(f"  workflows(status={wf.status_code}) count={wj.get('total_count')}")
        for w in wj.get("workflows", []) or []:
            print(f"    * name={w.get('name')!r} path={w.get('path')} state={w.get('state')}")

        # releases + tags
        rel = s.get(f"{API_ROOT}/repos/{user}/{repo}/releases", timeout=TIMEOUT).json()
        print(f"  releases={[x.get('tag_name') for x in rel] if isinstance(rel, list) else rel}")
        tags = s.get(f"{API_ROOT}/repos/{user}/{repo}/tags", timeout=TIMEOUT).json()
        print(f"  tags={[x.get('name') for x in tags] if isinstance(tags, list) else tags}")

        # root tree
        tr = s.get(f"{API_ROOT}/repos/{user}/{repo}/contents/?ref={br}", timeout=TIMEOUT).json()
        if isinstance(tr, list):
            print(f"  root: {[x['name'] for x in tr]}")

        # code scanning default setup
        cs = s.get(f"{API_ROOT}/repos/{user}/{repo}/code-scanning/default-setup",
                   timeout=TIMEOUT)
        print(f"  code-scanning default-setup: {cs.status_code} {cs.text[:200]}")

        # README head (badge lines)
        rd = s.get(f"{API_ROOT}/repos/{user}/{repo}/readme", timeout=TIMEOUT)
        if rd.status_code == 200:
            content = base64.b64decode(rd.json()["content"]).decode("utf-8", "replace")
            head = content.splitlines()[:14]
            print(f"  README bytes={len(content)} first-14-lines:")
            for ln in head:
                print(f"    | {ln[:190]}")
        else:
            print(f"  README: {rd.status_code}")

    print("=" * 70)
    print("3. huzjie/huzjie profile repo")
    pr = s.get(f"{API_ROOT}/repos/{user}/{user}", timeout=TIMEOUT)
    print(f"  status={pr.status_code} {pr.text[:200]}")

    print("=" * 70)
    print("4. .github meta repo contents")
    gh = s.get(f"{API_ROOT}/repos/{user}/.github/contents/", timeout=TIMEOUT)
    if gh.status_code == 200:
        print(f"  {[x['name'] for x in gh.json()]}")
    else:
        print(f"  status={gh.status_code}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
