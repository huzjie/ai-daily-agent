#!/usr/bin/env python3
"""Phase-4 discovery probe #5 (read-only): VideoForge ground truth for the README.

Pulls the engine registry, API router, compose file and existing README so the
rewritten README quotes real endpoints/engine names instead of invented ones.
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
REPO = "video-forge-studio"


def load_creds() -> tuple[str, str]:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    gh = cfg.get("github", {}) or {}
    return gh.get("username", "huzjie"), gh.get("token", "")


def show(s: requests.Session, user: str, path: str, head: int = 0) -> None:
    r = s.get(f"{API_ROOT}/repos/{user}/{REPO}/contents/{path}", timeout=TIMEOUT)
    print(f"\n===== {path}  (status={r.status_code})")
    if r.status_code != 200:
        return
    j = r.json()
    if isinstance(j, list):
        print(f"  dir: {[x['name'] for x in j]}")
        return
    txt = base64.b64decode(j["content"]).decode("utf-8", "replace")
    lines = txt.splitlines()
    if head:
        lines = lines[:head]
    for ln in lines:
        print(f"  {ln[:170]}")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    user, token = load_creds()
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "ai-daily-agent-phase4-probe5",
    })

    show(s, user, "src/videoforge/engines/registry.py", head=120)
    show(s, user, "src/videoforge/engines/base.py", head=90)
    show(s, user, "src/videoforge/engines/mock.py", head=50)
    show(s, user, "src/videoforge/api", head=0)
    show(s, user, "docker/docker-compose.yml", head=80)
    show(s, user, "README.md", head=0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
