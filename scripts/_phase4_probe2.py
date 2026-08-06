#!/usr/bin/env python3
"""Phase-4 discovery probe #2 (read-only): workflow run health + test stack facts.

Answers the two questions Phase-4 planning depends on:
  1. Are the existing CI badges green, red, or "no runs"? (P0-1)
  2. What is each repo's real test entrypoint, so the new CI cannot go red? (P0-2)
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

TARGETS = ["loopforge", "unified-ai-gateway", "moe-bench-studio",
           "argus-eval", "video-forge-studio"]

# files that reveal the real test/lint entrypoint
PEEK: Dict[str, List[str]] = {
    "loopforge": [".github/workflows/ci.yml", "pyproject.toml", "requirements-dev.txt"],
    "unified-ai-gateway": [".github/workflows/ci.yml", "package.json", ".nvmrc"],
    "moe-bench-studio": [".github/workflows/ci.yml", "pyproject.toml", "requirements-dev.txt"],
    "argus-eval": [".github/workflows/ci.yml", "pyproject.toml"],
    "video-forge-studio": [".github/workflows/ci.yml", "pyproject.toml",
                           "requirements.txt", "requirements-dev.txt"],
}


def load_creds() -> tuple[str, str]:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    gh = cfg.get("github", {}) or {}
    return gh.get("username", "huzjie"), gh.get("token", "")


def get_text(s: requests.Session, user: str, repo: str, path: str) -> str | None:
    r = s.get(f"{API_ROOT}/repos/{user}/{repo}/contents/{path}", timeout=TIMEOUT)
    if r.status_code != 200:
        return None
    j = r.json()
    if isinstance(j, dict) and j.get("content"):
        return base64.b64decode(j["content"]).decode("utf-8", "replace")
    return None


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    user, token = load_creds()
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "ai-daily-agent-phase4-probe2",
    })

    print("=" * 70)
    print("A. WORKFLOW RUN HEALTH  (the real P0-1 question)")
    for repo in TARGETS:
        print(f"\n### {repo}")
        runs = s.get(f"{API_ROOT}/repos/{user}/{repo}/actions/runs",
                     params={"per_page": 10}, timeout=TIMEOUT).json()
        total = runs.get("total_count", 0)
        print(f"  total_runs={total}")
        for r in (runs.get("workflow_runs") or [])[:8]:
            print(f"    - {r.get('name')!r} path={r.get('path')} "
                  f"status={r.get('status')} conclusion={r.get('conclusion')} "
                  f"branch={r.get('head_branch')} at={str(r.get('created_at'))[:19]}")
        if total == 0:
            print("    >>> NO RUNS AT ALL -> shields badge renders 'no status' (grey/broken)")

    print("\n" + "=" * 70)
    print("B. TEST / LINT ENTRYPOINT FACTS")
    for repo in TARGETS:
        print(f"\n### {repo}")
        for path in PEEK.get(repo, []):
            txt = get_text(s, user, repo, path)
            if txt is None:
                print(f"  -- {path}: MISSING")
                continue
            print(f"  -- {path} ({len(txt)} bytes)")
            if path.endswith("package.json"):
                try:
                    pj = json.loads(txt)
                    print(f"     name={pj.get('name')} pm={pj.get('packageManager')}")
                    print(f"     scripts={json.dumps(pj.get('scripts', {}), ensure_ascii=False)[:600]}")
                    print(f"     engines={pj.get('engines')}")
                except Exception as exc:  # noqa: BLE001
                    print(f"     (parse failed: {exc})")
            else:
                for ln in txt.splitlines()[:60]:
                    print(f"     | {ln[:170]}")

    print("\n" + "=" * 70)
    print("C. tests/ directory presence")
    for repo in TARGETS:
        r = s.get(f"{API_ROOT}/repos/{user}/{repo}/contents/tests", timeout=TIMEOUT)
        if r.status_code == 200 and isinstance(r.json(), list):
            names = [x["name"] for x in r.json()]
            print(f"  {repo}: tests/ -> {len(names)} entries {names[:12]}")
        else:
            print(f"  {repo}: tests/ -> {r.status_code}")

    print("\n" + "=" * 70)
    print("D. huzjie/huzjie profile repo + vfs src layout")
    pr = s.get(f"{API_ROOT}/repos/{user}/{user}", timeout=TIMEOUT)
    print(f"  huzjie/huzjie: status={pr.status_code}")
    for p in ["src", "docker", "scripts"]:
        r = s.get(f"{API_ROOT}/repos/{user}/video-forge-studio/contents/{p}", timeout=TIMEOUT)
        if r.status_code == 200 and isinstance(r.json(), list):
            print(f"  vfs {p}/ -> {[x['name'] for x in r.json()][:25]}")
    txt = get_text(s, user, "video-forge-studio", "docker-compose.yml")
    print(f"  vfs docker-compose.yml at root: {'YES' if txt else 'NO'}")
    for cand in ["docker/docker-compose.yml", "docker/compose.yml"]:
        t2 = get_text(s, user, "video-forge-studio", cand)
        print(f"  vfs {cand}: {'YES' if t2 else 'NO'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
