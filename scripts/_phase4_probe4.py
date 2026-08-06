#!/usr/bin/env python3
"""Phase-4 discovery probe #4 (read-only): dump every workflow file.

P0-3 requires adding a top-level `permissions: contents: read` to all workflows.
Blindly injecting it would BREAK workflows that legitimately need write scopes
(release creation, GHCR pushes, SARIF upload). So every file is inspected first.
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

import requests
import yaml

API_ROOT = "https://api.github.com"
TIMEOUT = 60
ROOT = Path(__file__).resolve().parent.parent

TARGETS = ["loopforge", "unified-ai-gateway", "moe-bench-studio",
           "argus-eval", "video-forge-studio", "ai-daily-agent"]


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
        "User-Agent": "ai-daily-agent-phase4-probe4",
    })

    for repo in TARGETS:
        print("=" * 70)
        print(f"REPO {repo}")
        r = s.get(f"{API_ROOT}/repos/{user}/{repo}/contents/.github/workflows",
                  timeout=TIMEOUT)
        if r.status_code != 200 or not isinstance(r.json(), list):
            print(f"  no workflows dir ({r.status_code})")
            continue
        for entry in r.json():
            path = entry["path"]
            cr = s.get(f"{API_ROOT}/repos/{user}/{repo}/contents/{path}", timeout=TIMEOUT)
            if cr.status_code != 200:
                continue
            txt = base64.b64decode(cr.json()["content"]).decode("utf-8", "replace")
            lines = txt.splitlines()
            # detect top-level permissions (column 0 key)
            has_top_perm = any(ln.startswith("permissions:") for ln in lines)
            has_job_perm = any(ln.strip().startswith("permissions:") for ln in lines) \
                and not has_top_perm
            print(f"\n--- {path}  ({len(txt)}B) top_permissions={has_top_perm} "
                  f"job_permissions_only={has_job_perm}")
            for i, ln in enumerate(lines, 1):
                print(f"  {i:>3}| {ln[:160]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
