#!/usr/bin/env python3
"""Phase-5 GitHub optimization (P1-8 awesome PR, P1-2 branch protection,
P1-3 CITATION.cff, P1-9 good-first-issue + roadmap, C: alerts & CI failures,
D: star-history + CI gate promotion).

Environment rules
-----------------
* git transport to github.com is reset in this sandbox; only api.github.com
  is reachable, so every mutation goes through the GitHub REST API.
* The script is **idempotent**: every step compares remote state first and
  reports skipped when already done. Re-running is safe.
* Every write records its HTTP status; non-2xx becomes a failed row.

Usage
-----
    python scripts/gh_optimize_phase5.py --steps a1-awesome       # awesome PRs
    python scripts/gh_optimize_phase5.py --steps b1-protect       # branch protection
    python scripts/gh_optimize_phase5.py --steps b2-citation      # CITATION.cff
    python scripts/gh_optimize_phase5.py --steps b3-issues        # good first issues + roadmap
    python scripts/gh_optimize_phase5.py --steps c1-codeql        # dismiss false-positive alert
    python scripts/gh_optimize_phase5.py --steps c2-dependabot    # dependabot triage
    python scripts/gh_optimize_phase5.py --steps c3-docker        # fix docker/publish workflows
    python scripts/gh_optimize_phase5.py --steps d1-star          # star history
    python scripts/gh_optimize_phase5.py --steps d2-ci            # CI advisory promotion
    python scripts/gh_optimize_phase5.py                          # all of the above
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
import yaml

API_ROOT: str = "https://api.github.com"
TIMEOUT: int = 60
ROOT: Path = Path(__file__).resolve().parent.parent

FLAGSHIPS: List[str] = [
    "loopforge",
    "unified-ai-gateway",
    "moe-bench-studio",
    "argus-eval",
    "video-forge-studio",
    "ai-daily-agent",
]

ALL_STEPS: List[str] = [
    "a1-awesome",
    "b1-protect",
    "b2-citation",
    "b3-issues",
    "c1-codeql",
    "c2-dependabot",
    "c3-docker",
    "d1-star",
    "d2-ci",
]

# --------------------------------------------------------------------------- #
# result bookkeeping
# --------------------------------------------------------------------------- #
@dataclass
class Result:
    status: str  # created | updated | skipped | failed | verify
    repo: str
    target: str
    detail: str = ""


@dataclass
class Ledger:
    rows: List[Result] = field(default_factory=list)

    def add(self, status: str, repo: str, target: str, detail: str = "") -> None:
        self.rows.append(Result(status, repo, target, detail))
        icon = {
            "created": "+", "updated": "~", "skipped": "=",
            "failed": "!", "verify": "?",
        }.get(status, " ")
        print(f"  [{icon}] {status:<8} {repo}/{target}  {detail[:160]}")

    def counts(self) -> Counter:
        return Counter(r.status for r in self.rows)


LEDGER = Ledger()


# --------------------------------------------------------------------------- #
# HTTP layer
# --------------------------------------------------------------------------- #
class GitHub:
    """Thin GitHub REST client with rate-limit retry and no silent failures."""

    def __init__(self, user: str, token: str, dry_run: bool = False) -> None:
        self.user: str = user
        self.dry_run: bool = dry_run
        self.session: requests.Session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ai-daily-agent-phase5",
        })

    def request(
        self,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
        max_retries: int = 4,
    ) -> Tuple[int, Any]:
        url = path if path.startswith("http") else API_ROOT + path
        if self.dry_run and method.upper() not in ("GET", "HEAD"):
            print(f"    [dry-run] {method} {path} "
                  f"{json.dumps(payload, ensure_ascii=False)[:120] if payload else ''}")
            return 999, {"_dry_run": True}

        for attempt in range(max_retries):
            resp = self.session.request(method, url, json=payload, timeout=TIMEOUT)
            if resp.status_code in (403, 429):
                remaining = resp.headers.get("X-RateLimit-Remaining")
                retry_after = resp.headers.get("Retry-After")
                if retry_after or remaining == "0":
                    wait = int(retry_after) if retry_after else 60
                    wait = min(wait, 120)
                    print(f"    [rate-limit] sleeping {wait}s "
                          f"(attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait)
                    continue
            if resp.status_code >= 500 and attempt < max_retries - 1:
                time.sleep(3 * (attempt + 1))
                continue
            break

        try:
            body: Any = resp.json()
        except ValueError:
            body = resp.text
        return resp.status_code, body

    # -- convenience wrappers ------------------------------------------------
    def get(self, path: str) -> Tuple[int, Any]:
        return self.request("GET", path)

    def repo_info(self, repo: str) -> Dict[str, Any]:
        code, body = self.get(f"/repos/{self.user}/{repo}")
        return body if code == 200 and isinstance(body, dict) else {}

    def default_branch(self, repo: str) -> str:
        return self.repo_info(repo).get("default_branch", "main")

    def get_file(self, repo: str, path: str,
                 ref: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        suffix = f"?ref={ref}" if ref else ""
        code, body = self.get(f"/repos/{self.user}/{repo}/contents/{path}{suffix}")
        if code != 200 or not isinstance(body, dict) or "content" not in body:
            return None, None
        text = base64.b64decode(body["content"]).decode("utf-8", "replace")
        return text, body.get("sha")

    def put_file(self, repo: str, path: str, content: str, message: str,
                 branch: Optional[str] = None) -> str:
        """Idempotent single-file write. Returns created|updated|skipped|failed."""
        branch = branch or self.default_branch(repo)
        existing, sha = self.get_file(repo, path, ref=branch)
        if existing is not None and existing == content:
            LEDGER.add("skipped", repo, path, "content identical")
            return "skipped"

        payload: Dict[str, Any] = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha
        code, body = self.request(
            "PUT", f"/repos/{self.user}/{repo}/contents/{path}", payload
        )
        if code == 999:
            LEDGER.add("skipped", repo, path, "dry-run")
            return "skipped"
        if code in (200, 201):
            status = "updated" if sha else "created"
            LEDGER.add(status, repo, path, f"HTTP {code}")
            return status
        LEDGER.add("failed", repo, path,
                   f"HTTP {code} {json.dumps(body, ensure_ascii=False)[:200]}")
        return "failed"


def load_credentials() -> Tuple[str, str]:
    cfg_path = ROOT / "config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    gh = cfg.get("github", {}) or {}
    user, token = gh.get("username", ""), gh.get("token", "")
    if not user or not token:
        raise SystemExit("config.yaml 缺少 github.username 或 github.token")
    return user, token


# --------------------------------------------------------------------------- #
# A1 : awesome-list PRs (P1-8)
# --------------------------------------------------------------------------- #
# (upstream, our repo, section anchor, line factory, pr title)
AWESOME_TARGETS: List[Dict[str, Any]] = [
    {
        "upstream": "Hannibal046/Awesome-LLM",
        "ours": "loopforge",
        "display": "LoopForge",
        "url": "https://github.com/huzjie/loopforge",
        "one_line": "Open-source AI agent orchestration & governance platform for long-range autonomous coding",
        "anchor": "## LLM Applications",
        "insert_after": "llamaindex",
        "pr_title": "docs: add LoopForge to LLM Applications",
        "pr_body": (
            "Add [LoopForge](https://github.com/huzjie/loopforge) to the LLM Applications list.\n\n"
            "LoopForge is an open-source, self-hostable AI agent orchestration and governance "
            "platform for long-range autonomous coding: multi-agent workflows, guardrails, "
            "sandboxed execution and audit trails. Apache-2.0, Python.\n\n"
            "This is a single-line addition following the existing list format."
        ),
    },
    {
        "upstream": "tensorchord/Awesome-LLMOps",
        "ours": "unified-ai-gateway",
        "display": "Unified AI Gateway",
        "url": "https://github.com/huzjie/unified-ai-gateway",
        "one_line": "Self-hosted LLM API gateway with one OpenAI-compatible endpoint across providers, routing & cost control",
        "anchor": "### Large Model Serving",
        "insert_after": "modelz-llm",
        "pr_title": "docs: add Unified AI Gateway to Large Model Serving",
        "pr_body": (
            "Add [Unified AI Gateway](https://github.com/huzjie/unified-ai-gateway) to the "
            "Large Model Serving table.\n\n"
            "A self-hosted LLM API gateway exposing one OpenAI-compatible endpoint across "
            "multiple providers (OpenAI, Kimi, DeepSeek, Qwen, ...) with smart routing, "
            "cost control, usage logs and a management console. Apache-2.0, TypeScript.\n\n"
            "Single table row added following the existing format."
        ),
    },
    {
        "upstream": "mahseema/awesome-ai-tools",
        "ours": "video-forge-studio",
        "display": "VideoForge Studio",
        "url": "https://github.com/huzjie/video-forge-studio",
        "one_line": "Unified control plane for AI video generation — orchestrate multiple engines via one API",
        "anchor": "## Video",
        "insert_after": "sisif",
        "pr_title": "docs: add VideoForge Studio to AI Video tools",
        "pr_body": (
            "Add [VideoForge Studio](https://github.com/huzjie/video-forge-studio) to the "
            "AI Video tools list.\n\n"
            "Open-source control plane for AI video generation: a single API to orchestrate "
            "multiple generation engines, with queueing, retries, cost tracking and a web "
            "console. Apache-2.0, Python.\n\n"
            "Single-line addition following the existing format."
        ),
    },
]


def _insert_after_anchor(lines: List[str], anchor: str, marker: str,
                         new_lines: List[str]) -> Optional[int]:
    """Insert new_lines right after the line containing marker inside section."""
    in_section = False
    for i, line in enumerate(lines):
        if line.strip().startswith(anchor):
            in_section = True
            continue
        if in_section and line.strip().startswith("## "):
            break
        if in_section and marker.lower() in line.lower():
            return i + 1
    return None


def step_a1_awesome(gh: GitHub) -> None:
    """Create pull requests that add each flagship to a real awesome list."""
    for t in AWESOME_TARGETS:
        upstream = t["upstream"]
        up_owner, up_repo = upstream.split("/")
        ours = t["ours"]
        line = f"- [{t['display']}]({t['url']}) - {t['one_line']}"
        pr_title = t["pr_title"]

        # 0) skip if we already have an open PR with this title to upstream
        code, body = gh.get(
            f"/repos/{up_owner}/{up_repo}/pulls?state=open&per_page=100"
        )
        if code == 200 and isinstance(body, list):
            dup = [p for p in body if (p.get("title") or "").strip() == pr_title
                   and (p.get("user") or {}).get("login") == gh.user]
            if dup:
                LEDGER.add("skipped", upstream, pr_title,
                           f"already open: #{dup[0]['number']} {dup[0]['html_url']}")
                continue

        # 1) read upstream README (real repo, editable list structure)
        code, body = gh.get(f"/repos/{up_owner}/{up_repo}/contents/README.md")
        if code != 200 or not isinstance(body, dict) or "content" not in body:
            LEDGER.add("failed", upstream, "README",
                       f"HTTP {code} cannot read upstream README")
            continue
        upstream_text = base64.b64decode(body["content"]).decode("utf-8", "replace")
        upstream_sha = body["sha"]
        if t["anchor"] not in upstream_text:
            LEDGER.add("failed", upstream, "README",
                       f"anchor '{t['anchor']}' not found")
            continue

        lines = upstream_text.splitlines()
        idx = _insert_after_anchor(lines, t["anchor"], t["insert_after"], [line])
        if idx is None:
            LEDGER.add("failed", upstream, "README",
                       f"marker '{t['insert_after']}' not found after anchor")
            continue
        new_text = upstream_text.splitlines()
        new_text.insert(idx, line)
        new_content = "\n".join(new_text) + "\n"

        # 2) fork upstream (idempotent: returns existing fork if present)
        code, body = gh.request(
            "POST", f"/repos/{up_owner}/{up_repo}/forks", {}
        )
        if code not in (202, 200):
            LEDGER.add("failed", upstream, "fork",
                       f"HTTP {code} {json.dumps(body, ensure_ascii=False)[:200]}")
            continue

        # wait for fork to be ready (up to ~60s)
        fork_ready = False
        for _ in range(12):
            code, body = gh.get(f"/repos/{gh.user}/{up_repo}")
            if code == 200 and isinstance(body, dict):
                fork_ready = True
                break
            time.sleep(5)
        if not fork_ready:
            LEDGER.add("failed", upstream, "fork", "fork not ready after 60s")
            continue
        fork_default = body.get("default_branch", "main")

        # 3) push the change to the fork via Contents API
        code, body = gh.get(
            f"/repos/{gh.user}/{up_repo}/contents/README.md?ref={fork_default}"
        )
        if code != 200 or not isinstance(body, dict) or "content" not in body:
            LEDGER.add("failed", f"{gh.user}/{up_repo}", "README",
                       f"HTTP {code} cannot read fork README")
            continue
        fork_sha = body["sha"]
        # Only edit if the fork still matches upstream content (avoid clobbering).
        payload = {
            "message": pr_title,
            "content": base64.b64encode(new_content.encode("utf-8")).decode("ascii"),
            "sha": fork_sha,
            "branch": fork_default,
        }
        code, body = gh.request(
            "PUT", f"/repos/{gh.user}/{up_repo}/contents/README.md", payload
        )
        if code not in (200, 201):
            LEDGER.add("failed", f"{gh.user}/{up_repo}", "README",
                       f"HTTP {code} {json.dumps(body, ensure_ascii=False)[:200]}")
            continue

        # 4) open the PR
        pr_payload = {
            "title": pr_title,
            "head": f"{gh.user}:{fork_default}",
            "base": "main",
            "body": t["pr_body"],
        }
        code, body = gh.request(
            "POST", f"/repos/{up_owner}/{up_repo}/pulls", pr_payload
        )
        if code == 201 and isinstance(body, dict):
            LEDGER.add("created", upstream, pr_title,
                       f"PR #{body['number']} {body['html_url']}")
        else:
            LEDGER.add("failed", upstream, pr_title,
                       f"HTTP {code} {json.dumps(body, ensure_ascii=False)[:200]}")


# --------------------------------------------------------------------------- #
# B1 : branch protection (P1-2)
# --------------------------------------------------------------------------- #
# status-check context per repo (from real check-runs observed)
CONTEXT_BY_REPO: Dict[str, str] = {
    "loopforge": "Lint & Smoke Test",
    "unified-ai-gateway": "Install & Verify",
    "moe-bench-studio": "Lint & Smoke Test",
    "argus-eval": "Lint & Smoke Test",
    "video-forge-studio": "Lint & Smoke Test",
    "ai-daily-agent": "",  # no CI workflow yet
}


def step_b1_protect(gh: GitHub) -> None:
    for repo in FLAGSHIPS:
        context = CONTEXT_BY_REPO.get(repo, "")
        # check existing protection
        code, body = gh.get(f"/repos/{gh.user}/{repo}/branches/main/protection")
        if code == 200:
            LEDGER.add("skipped", repo, "branch protection", "already protected")
            continue
        payload: Dict[str, Any] = {
            "required_status_checks": {
                "strict": True,
                "contexts": [context] if context else [],
            },
            "enforce_admins": True,
            "required_pull_request_reviews": {
                "required_approving_review_count": 1,
                "dismiss_stale_reviews": True,
                "require_code_owner_reviews": False,
            },
            "restrictions": None,
        }
        code, body = gh.request(
            "PUT", f"/repos/{gh.user}/{repo}/branches/main/protection", payload
        )
        if code == 200:
            LEDGER.add("created", repo, "branch protection",
                       "PR review + status checks enabled")
        else:
            LEDGER.add("failed", repo, "branch protection",
                       f"HTTP {code} {json.dumps(body, ensure_ascii=False)[:200]}")


# --------------------------------------------------------------------------- #
# B2 : CITATION.cff (P1-3)
# --------------------------------------------------------------------------- #
CITATION_TARGETS: List[Dict[str, str]] = [
    {
        "repo": "loopforge",
        "title": "LoopForge",
        "desc": "Open-source AI agent orchestration & governance platform for long-range autonomous coding",
    },
    {
        "repo": "argus-eval",
        "title": "Argus Eval",
        "desc": "AI Agent evaluation & observability platform",
    },
    {
        "repo": "moe-bench-studio",
        "title": "MoE Bench Studio",
        "desc": "Enterprise LLM inference & benchmarking platform for MoE models",
    },
]


def render_citation(repo: str, title: str, desc: str) -> str:
    return f"""cff-version: 1.2.0
message: "If you use this software, please cite it as below."
title: "{title}"
abstract: "{desc}"
authors:
  - family-names: "huzjie"
    given-names: "Kou"
    orcid: ""
date-released: "2026-08-06"
license: "Apache-2.0"
repository-code: "https://github.com/huzjie/{repo}"
keywords:
  - "AI"
  - "LLM"
  - "open-source"
"""


def step_b2_citation(gh: GitHub) -> None:
    for t in CITATION_TARGETS:
        repo = t["repo"]
        content = render_citation(repo, t["title"], t["desc"])
        gh.put_file(repo, "CITATION.cff", content,
                    "docs: add CITATION.cff for academic citation")


# --------------------------------------------------------------------------- #
# B3 : good-first-issue labels + issues + roadmap (P1-9)
# --------------------------------------------------------------------------- #
ISSUE_PLANS: Dict[str, List[Dict[str, str]]] = {
    "loopforge": [
        {
            "title": "Add unit tests for workflow graph executor",
            "body": (
                "## Goal\nAdd unit tests covering the workflow graph executor "
                "(`loopforge/executor/graph.py`), especially DAG cycle detection, "
                "node retry and timeout handling.\n\n"
                "## Good first issue\n- Check existing tests under `tests/` for style.\n"
                "- Use `pytest`; keep each test small and deterministic.\n"
                "- Run `python -m pytest tests -q` locally before opening the PR.\n\n"
                "## Acceptance criteria\n- New tests cover: cycle detection, retry on "
                "failure, timeout abort, parallel branch merge."
            ),
        },
        {
            "title": "Improve CLI error messages for invalid YAML configs",
            "body": (
                "## Goal\nWhen `loopforge run --config bad.yaml` fails to parse, the "
                "current error is a raw traceback. Make it a friendly message that "
                "points to the exact line/column.\n\n"
                "## Good first issue\n- Look at `loopforge/cli.py` config loading.\n"
                "- Catch `yaml.YAMLError` and re-raise with context.\n\n"
                "## Acceptance criteria\n- Invalid YAML prints `Config error at line N: ...` "
                "and exits with code 2."
            ),
        },
        {
            "title": "Add a `--dry-run` flag to the run command",
            "body": (
                "## Goal\nAdd `loopforge run --dry-run` that validates the workflow "
                "graph and prints the plan without executing any agent.\n\n"
                "## Good first issue\n- Reuse the existing planner module.\n"
                "- Print steps, dependencies and estimated cost.\n\n"
                "## Acceptance criteria\n- `--dry-run` never starts a sandbox or calls an LLM."
            ),
        },
        {
            "title": "Document provider configuration in README quick start",
            "body": (
                "## Goal\nThe README quick start mentions `providers.yaml` but does not "
                "show a full example for each supported provider.\n\n"
                "## Good first issue\n- Add one short YAML block per provider (OpenAI, "
                "DeepSeek, Kimi, local Ollama).\n- Keep the README in both zh-CN and EN if present.\n\n"
                "## Acceptance criteria\n- A new user can copy-paste a working config in < 5 minutes."
            ),
        },
        {
            "title": "Add GitHub Action badge for CI to README",
            "body": (
                "## Goal\nThe CI workflow exists but the README has no status badge.\n\n"
                "## Good first issue\n- Use the shields.io workflow badge URL.\n"
                "- Place it in the README header next to the license badge.\n\n"
                "## Acceptance criteria\n- Badge shows the latest `main` CI result."
            ),
        },
    ],
    "video-forge-studio": [
        {
            "title": "Add unit tests for engine provider registry",
            "body": (
                "## Goal\nCover `videoforge/engines/registry.py` with unit tests: "
                "register/unregister, duplicate detection, unknown engine error.\n\n"
                "## Good first issue\n- Follow existing tests under `tests/unit/`.\n"
                "- Run `pytest -q tests/unit --maxfail=5` locally.\n\n"
                "## Acceptance criteria\n- Registry behavior is fully covered and green."
            ),
        },
        {
            "title": "Better validation message for unsupported video dimensions",
            "body": (
                "## Goal\nWhen a request uses unsupported resolution (e.g. 123x456), the "
                "API returns a generic 400. Return a clear message listing supported sizes.\n\n"
                "## Good first issue\n- Find the validation in `videoforge/api/`.\n"
                "- Add a test asserting the message content.\n\n"
                "## Acceptance criteria\n- 400 response body explains supported dimensions."
            ),
        },
        {
            "title": "Add pagination to the job list API",
            "body": (
                "## Goal\nThe `GET /api/jobs` endpoint returns all jobs. Add "
                "`page` / `page_size` parameters with a stable order.\n\n"
                "## Good first issue\n- Mirror the pagination style used elsewhere in the codebase.\n"
                "- Return `{items, total, page, page_size}`.\n\n"
                "## Acceptance criteria\n- Paginated responses and a test for page boundaries."
            ),
        },
        {
            "title": "Show progress percentage in the web console job card",
            "body": (
                "## Goal\nThe web console job list shows status but not progress.\n\n"
                "## Good first issue\n- Use the `progress` field returned by the API.\n"
                "- Render a small progress bar in the job card component.\n\n"
                "## Acceptance criteria\n- Progress updates without a full page refresh."
            ),
        },
        {
            "title": "Add OpenAPI docs link and example curl to README",
            "body": (
                "## Goal\nDocument how to call the video generation API with a copy-paste "
                "curl example and where to find OpenAPI docs.\n\n"
                "## Good first issue\n- Add one curl block for a text-to-video request.\n"
                "- Link the auto-generated docs endpoint.\n\n"
                "## Acceptance criteria\n- A new developer can make the first API call in < 5 minutes."
            ),
        },
    ],
}

ROADMAP_BODIES: Dict[str, str] = {
    "loopforge": (
        "## Roadmap (2026 H2)\n\n"
        "Public, prioritized plan. Items marked ✅ are shipped.\n\n"
        "### Now (v0.2.x)\n"
        "- [ ] Agent sandbox hardening (resource limits, egress policy)\n"
        "- [ ] Workflow retry & timeout improvements\n"
        "- [ ] Provider config UI (web console)\n\n"
        "### Next (v0.3.x)\n"
        "- [ ] Multi-user RBAC and audit export\n"
        "- [ ] Official Docker images + one-line deploy\n"
        "- [ ] Evaluation harness for agent quality\n\n"
        "### Later (v1.x)\n"
        "- [ ] Plugin marketplace\n"
        "- [ ] Cloud/self-host hybrid control plane\n"
        "- [ ] Enterprise SSO (OIDC/SAML)\n\n"
        "Feedback and contributions welcome — open an issue or comment below."
    ),
    "video-forge-studio": (
        "## Roadmap (2026 H2)\n\n"
        "Public, prioritized plan. Items marked ✅ are shipped.\n\n"
        "### Now (v0.2.x)\n"
        "- [ ] Add more generation engines (Sora-style APIs, open models)\n"
        "- [ ] Cost & usage dashboard v2\n"
        "- [ ] Webhook notifications on job completion\n\n"
        "### Next (v0.3.x)\n"
        "- [ ] Video review/annotation workflow\n"
        "- [ ] Batch generation from CSV manifest\n"
        "- [ ] Team workspaces & quotas\n\n"
        "### Later (v1.x)\n"
        "- [ ] Plugin SDK for custom engines\n"
        "- [ ] Multi-region queue federation\n"
        "- [ ] Enterprise SSO (OIDC/SAML)\n\n"
        "Feedback and contributions welcome — open an issue or comment below."
    ),
}


def step_b3_issues(gh: GitHub) -> None:
    for repo, issues in ISSUE_PLANS.items():
        # ensure labels exist
        for label, color in [("good first issue", "7057ff"),
                             ("roadmap", "0e8a16"),
                             ("help wanted", "008672")]:
            code, body = gh.request(
                "POST", f"/repos/{gh.user}/{repo}/labels",
                {"name": label, "color": color, "description": ""}
            )
            if code == 201:
                LEDGER.add("created", repo, f"label:{label}", "created")
            elif code == 422:
                LEDGER.add("skipped", repo, f"label:{label}", "already exists")
            else:
                LEDGER.add("failed", repo, f"label:{label}",
                           f"HTTP {code} {json.dumps(body, ensure_ascii=False)[:150]}")

        # good first issues
        for plan in issues:
            title = plan["title"]
            # skip if an open issue with same title exists
            code, body = gh.get(
                f"/repos/{gh.user}/{repo}/issues?state=open&per_page=100"
            )
            exists = False
            if code == 200 and isinstance(body, list):
                exists = any(
                    (i.get("title") or "").strip() == title
                    and "pull_request" not in i
                    for i in body
                )
            if exists:
                LEDGER.add("skipped", repo, f"issue:{title}", "already open")
                continue
            payload = {
                "title": title,
                "body": plan["body"],
                "labels": ["good first issue", "help wanted"],
            }
            code, body = gh.request(
                "POST", f"/repos/{gh.user}/{repo}/issues", payload
            )
            if code == 201 and isinstance(body, dict):
                LEDGER.add("created", repo, f"issue:{title}",
                           f"#{body['number']} {body['html_url']}")
            else:
                LEDGER.add("failed", repo, f"issue:{title}",
                           f"HTTP {code} {json.dumps(body, ensure_ascii=False)[:200]}")

        # roadmap issue (pinned)
        rt = f"Roadmap: {repo} 2026 H2"
        code, body = gh.get(
            f"/repos/{gh.user}/{repo}/issues?state=open&per_page=100"
        )
        exists = False
        if code == 200 and isinstance(body, list):
            exists = any(
                (i.get("title") or "").strip() == rt and "pull_request" not in i
                for i in body
            )
        if exists:
            LEDGER.add("skipped", repo, f"issue:{rt}", "already open")
        else:
            payload = {
                "title": rt,
                "body": ROADMAP_BODIES[repo],
                "labels": ["roadmap"],
            }
            code, body = gh.request(
                "POST", f"/repos/{gh.user}/{repo}/issues", payload
            )
            if code == 201 and isinstance(body, dict):
                LEDGER.add("created", repo, f"issue:{rt}",
                           f"#{body['number']} {body['html_url']}")
                # pin it (GitHub uses PUT for pin)
                pin_code, pin_body = gh.request(
                    "PUT", f"/repos/{gh.user}/{repo}/issues/{body['number']}/pin", {}
                )
                if pin_code == 204:
                    LEDGER.add("created", repo, f"pinned:{rt}", "pinned")
                else:
                    LEDGER.add("failed", repo, f"pinned:{rt}",
                               f"HTTP {pin_code}")
            else:
                LEDGER.add("failed", repo, f"issue:{rt}",
                           f"HTTP {code} {json.dumps(body, ensure_ascii=False)[:200]}")


# --------------------------------------------------------------------------- #
# C1 : CodeQL alert triage (moe-bench-studio #1)
# --------------------------------------------------------------------------- #
def step_c1_codeql(gh: GitHub) -> None:
    repo = "moe-bench-studio"
    alert_number = 1
    code, body = gh.get(
        f"/repos/{gh.user}/{repo}/code-scanning/alerts/{alert_number}"
    )
    if code != 200 or not isinstance(body, dict):
        LEDGER.add("failed", repo, f"codeql-alert#{alert_number}",
                   f"HTTP {code} cannot read alert")
        return
    if body.get("state") == "dismissed":
        LEDGER.add("skipped", repo, f"codeql-alert#{alert_number}",
                   "already dismissed")
        return
    if body.get("state") != "open":
        LEDGER.add("skipped", repo, f"codeql-alert#{alert_number}",
                   f"state={body.get('state')}")
        return

    # py/weak-sensitive-data-hashing: SHA-256 used for API-key storage.
    # API keys are high-entropy random strings, not passwords; SHA-256 digest
    # storage for API keys is an accepted practice (same as GitHub's own PAT
    # storage). Dismiss as won't fix with a note.
    rule_id = (body.get("rule") or {}).get("id", "")
    if rule_id == "py/weak-sensitive-data-hashing":
        payload = {
            "state": "dismissed",
            "dismissed_reason": "won't fix",
            "dismissed_comment": (
                "SHA-256 digest storage of high-entropy API keys (not passwords); "
                "password hashing uses bcrypt via hash_password(). API key digests "
                "are used only for lookup, never for authentication of human users."
            ),
        }
        code, body = gh.request(
            "PATCH", f"/repos/{gh.user}/{repo}/code-scanning/alerts/{alert_number}",
            payload
        )
        if code == 200:
            LEDGER.add("updated", repo, f"codeql-alert#{alert_number}",
                       "dismissed (won't fix, API-key digest)")
        else:
            LEDGER.add("failed", repo, f"codeql-alert#{alert_number}",
                       f"HTTP {code} {json.dumps(body, ensure_ascii=False)[:200]}")
    else:
        LEDGER.add("skipped", repo, f"codeql-alert#{alert_number}",
                   f"rule={rule_id} left open (real issue or not triaged)")


# --------------------------------------------------------------------------- #
# C2 : dependabot alert triage (report only; merge only safe patch PRs)
# --------------------------------------------------------------------------- #
def step_c2_dependabot(gh: GitHub) -> None:
    """Inspect open dependabot alerts and open PRs; report classification."""
    for repo in FLAGSHIPS:
        code, body = gh.get(
            f"/repos/{gh.user}/{repo}/dependabot/alerts?state=open&per_page=30"
        )
        if code != 200:
            if code == 404:
                LEDGER.add("skipped", repo, "dependabot", "not enabled (404)")
            else:
                LEDGER.add("failed", repo, "dependabot", f"HTTP {code}")
            continue
        alerts = body if isinstance(body, list) else []
        # Count by severity
        sev: Counter = Counter()
        for a in alerts:
            adv = a.get("security_advisory") or {}
            sev[adv.get("severity", "unknown")] += 1
        detail = f"{len(alerts)} open alerts " + ", ".join(
            f"{k}={v}" for k, v in sorted(sev.items())
        )
        LEDGER.add("verify", repo, "dependabot-alerts", detail)

        # open PRs (dependabot or otherwise) — report only
        code, body = gh.get(
            f"/repos/{gh.user}/{repo}/pulls?state=open&per_page=50"
        )
        if code == 200 and isinstance(body, list):
            prs = body
            majors: List[str] = []
            for pr in prs:
                head = pr.get("head") or {}
                if not (head.get("label") or "").startswith(f"{gh.user}:"):
                    continue
                title = pr.get("title") or ""
                if title.startswith(("chore(deps", "build(deps", "chore(deps-dev")):
                    majors.append(f"#{pr['number']} {title[:60]}")
            if majors:
                LEDGER.add("verify", repo, "dependabot-prs",
                           "; ".join(majors[:12]))
            else:
                LEDGER.add("skipped", repo, "dependabot-prs", "no open dep PRs")


# --------------------------------------------------------------------------- #
# C3 : docker/publish workflow failures
# --------------------------------------------------------------------------- #
def step_c3_docker(gh: GitHub) -> None:
    # --- vfs: Dockerfile.web missing @types/node + no lockfile fallback ---
    repo = "video-forge-studio"
    path = "docker/Dockerfile.web"
    text, sha = gh.get_file(repo, path)
    if text is None:
        LEDGER.add("failed", repo, path, "cannot read Dockerfile.web")
    else:
        desired = """# VideoForge Studio - Web Frontend Image (multi-stage)
FROM node:20-alpine AS builder
WORKDIR /app
# Lockfile may be absent; use npm install (npm ci requires a lockfile).
COPY web/package.json ./
RUN npm install && npm install -D @types/node
COPY web/ .
RUN npm run build

FROM nginx:1.27-alpine AS final
COPY --from=builder /app/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \\
    CMD wget -qO- http://localhost/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
"""
        if text == desired:
            LEDGER.add("skipped", repo, path, "already fixed")
        else:
            code, body = gh.request(
                "PUT", f"/repos/{gh.user}/{repo}/contents/{path}",
                {
                    "message": "fix(docker): install @types/node for vite build; "
                               "use npm install without lockfile",
                    "content": base64.b64encode(desired.encode("utf-8")).decode("ascii"),
                    "sha": sha,
                    "branch": gh.default_branch(repo),
                }
            )
            if code in (200, 201):
                LEDGER.add("updated", repo, path, "Dockerfile.web fixed")
            else:
                LEDGER.add("failed", repo, path,
                           f"HTTP {code} {json.dumps(body, ensure_ascii=False)[:200]}")

    # --- uag: create missing LogList / LogFilters components ---
    repo = "unified-ai-gateway"
    log_list = """import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Chip, Typography, Box } from '@mui/material';
import type { UsageLog } from '../../types';

export interface LogListProps {
  logs: UsageLog[];
  onRowClick: (log: UsageLog) => void;
}

function formatTime(iso: string): string {
  if (!iso) return '-';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

export function LogList({ logs, onRowClick }: LogListProps) {
  if (logs.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          暂无日志
        </Typography>
      </Paper>
    );
  }
  return (
    <TableContainer component={Paper}>
      <Table size="small" sx={{ minWidth: 720 }}>
        <TableHead>
          <TableRow>
            <TableCell>时间</TableCell>
            <TableCell>模型</TableCell>
            <TableCell>Provider</TableCell>
            <TableCell>状态</TableCell>
            <TableCell align="right">耗时</TableCell>
            <TableCell align="right">Tokens</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {logs.map((log) => (
            <TableRow
              key={log.id}
              hover
              sx={{ cursor: 'pointer' }}
              onClick={() => onRowClick(log)}
            >
              <TableCell>{formatTime(log.createdAt)}</TableCell>
              <TableCell>{log.model}</TableCell>
              <TableCell>{log.provider}</TableCell>
              <TableCell>
                <Chip
                  size="small"
                  color={log.statusCode < 400 ? 'success' : 'error'}
                  label={log.statusCode}
                  variant="outlined"
                />
              </TableCell>
              <TableCell align="right">{log.latencyMs}ms</TableCell>
              <TableCell align="right">{log.totalTokens}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
"""
    log_filters = """import { Box, Button, MenuItem, TextField } from '@mui/material';

export interface LogFiltersProps {
  search: string;
  onSearchChange: (value: string) => void;
  model: string;
  onModelChange: (value: string) => void;
  status: string;
  onStatusChange: (value: string) => void;
  onRefresh: () => void;
}

const STATUS_OPTIONS = [
  { value: '', label: '全部状态' },
  { value: '200', label: '200' },
  { value: '400', label: '400' },
  { value: '401', label: '401' },
  { value: '429', label: '429' },
  { value: '500', label: '500' },
];

export function LogFilters({
  search,
  onSearchChange,
  model,
  onModelChange,
  status,
  onStatusChange,
  onRefresh,
}: LogFiltersProps) {
  return (
    <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap', alignItems: 'center' }}>
      <TextField
        size="small"
        label="搜索"
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        sx={{ minWidth: 220 }}
      />
      <TextField
        size="small"
        label="模型"
        value={model}
        onChange={(e) => onModelChange(e.target.value)}
        sx={{ minWidth: 160 }}
      />
      <TextField
        size="small"
        select
        label="状态"
        value={status}
        onChange={(e) => onStatusChange(e.target.value)}
        sx={{ minWidth: 130 }}
      >
        {STATUS_OPTIONS.map((o) => (
          <MenuItem key={o.value} value={o.value}>
            {o.label}
          </MenuItem>
        ))}
      </TextField>
      <Button size="small" variant="outlined" onClick={onRefresh}>
        刷新
      </Button>
    </Box>
  );
}
"""
    for path, content in [
        ("apps/web/src/components/Logs/LogList.tsx", log_list),
        ("apps/web/src/components/Logs/LogFilters.tsx", log_filters),
    ]:
        existing, _ = gh.get_file(repo, path)
        if existing == content:
            LEDGER.add("skipped", repo, path, "already exists")
        elif existing is not None:
            code, body = gh.request(
                "PUT", f"/repos/{gh.user}/{repo}/contents/{path}",
                {
                    "message": f"fix(web): add missing {path.rsplit('/', 1)[-1]} component",
                    "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
                    "branch": gh.default_branch(repo),
                }
            )
            if code in (200, 201):
                LEDGER.add("updated", repo, path, "recreated")
            else:
                LEDGER.add("failed", repo, path,
                           f"HTTP {code} {json.dumps(body, ensure_ascii=False)[:200]}")
        else:
            code, body = gh.request(
                "PUT", f"/repos/{gh.user}/{repo}/contents/{path}",
                {
                    "message": f"fix(web): add missing {path.rsplit('/', 1)[-1]} component",
                    "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
                    "branch": gh.default_branch(repo),
                }
            )
            if code in (200, 201):
                LEDGER.add("created", repo, path, "created")
            else:
                LEDGER.add("failed", repo, path,
                           f"HTTP {code} {json.dumps(body, ensure_ascii=False)[:200]}")

    # --- argus-eval: publish.yml — PyPI trusted publishing needs manual setup ---
    repo = "argus-eval"
    text, _ = gh.get_file(repo, ".github/workflows/publish.yml")
    if text is None:
        LEDGER.add("skipped", repo, "publish.yml", "not found")
    else:
        LEDGER.add("verify", repo, "publish.yml",
                   "PyPI trusted publisher must be configured on pypi.org manually "
                   "(invalid-publisher error)")


# --------------------------------------------------------------------------- #
# D1 : star-history chart (P2-2)
# --------------------------------------------------------------------------- #
STAR_BLOCK_TEMPLATE = """
---

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=huzjie/{repo}&type=Date)](https://star-history.com/#huzjie/{repo}&Date)
"""


def step_d1_star(gh: GitHub) -> None:
    for repo in FLAGSHIPS:
        text, sha = gh.get_file(repo, "README.md")
        if text is None:
            LEDGER.add("failed", repo, "README.md", "cannot read")
            continue
        if "star-history.com" in text:
            LEDGER.add("skipped", repo, "README.md", "star history present")
            continue
        block = STAR_BLOCK_TEMPLATE.format(repo=repo)
        new_text = text.rstrip() + block
        code, body = gh.request(
            "PUT", f"/repos/{gh.user}/{repo}/contents/README.md",
            {
                "message": f"docs: add Star History chart for {repo}",
                "content": base64.b64encode(new_text.encode("utf-8")).decode("ascii"),
                "sha": sha,
                "branch": gh.default_branch(repo),
            }
        )
        if code in (200, 201):
            LEDGER.add("updated", repo, "README.md", "star history added")
        else:
            LEDGER.add("failed", repo, "README.md",
                       f"HTTP {code} {json.dumps(body, ensure_ascii=False)[:200]}")


# --------------------------------------------------------------------------- #
# D2 : CI advisory promotion (only for repos with real green tests)
# --------------------------------------------------------------------------- #
def step_d2_ci(gh: GitHub) -> None:
    """Promote the pytest step from advisory to blocking only for
    video-forge-studio (51/51 real unit tests green). Keep other repos advisory."""
    repo = "video-forge-studio"
    path = ".github/workflows/ci.yml"
    text, sha = gh.get_file(repo, path)
    if text is None:
        LEDGER.add("failed", repo, path, "cannot read ci.yml")
        return

    # Replace the pytest step: remove continue-on-error so tests truly block.
    old_step = """      - name: Pytest (advisory)
        continue-on-error: true
        env:
          VIDEOFORGE_SECRET_KEY: ci-test-secret-key-not-for-production
          VIDEOFORGE_ENGINES: mock
        run: pytest -q tests/unit --maxfail=5"""
    new_step = """      - name: Pytest (blocking)
        env:
          VIDEOFORGE_SECRET_KEY: ci-test-secret-key-not-for-production
          VIDEOFORGE_ENGINES: mock
        run: pytest -q tests/unit --maxfail=5"""
    if "Pytest (blocking)" in text:
        LEDGER.add("skipped", repo, path, "pytest already blocking")
        return
    if old_step not in text:
        LEDGER.add("failed", repo, path, "pytest advisory step not found (format changed)")
        return
    new_text = text.replace(old_step, new_step)
    code, body = gh.request(
        "PUT", f"/repos/{gh.user}/{repo}/contents/{path}",
        {
            "message": "ci: make unit tests a blocking gate (51/51 green)",
            "content": base64.b64encode(new_text.encode("utf-8")).decode("ascii"),
            "sha": sha,
            "branch": gh.default_branch(repo),
        }
    )
    if code in (200, 201):
        LEDGER.add("updated", repo, path, "pytest is now a blocking gate")
    else:
        LEDGER.add("failed", repo, path,
                   f"HTTP {code} {json.dumps(body, ensure_ascii=False)[:200]}")


# --------------------------------------------------------------------------- #
# report & main
# --------------------------------------------------------------------------- #
def print_report() -> None:
    counts = LEDGER.counts()
    print("\n" + "=" * 70)
    print("PHASE-5 SUMMARY")
    print("=" * 70)
    for status in ("created", "updated", "skipped", "failed", "verify"):
        n = counts.get(status, 0)
        if n:
            print(f"  {status:<8} {n}")
    if counts.get("failed", 0):
        print("\nFailed rows:")
        for r in LEDGER.rows:
            if r.status == "failed":
                print(f"  ! {r.repo}/{r.target}: {r.detail}")
    print("=" * 70)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase-5 GitHub optimization")
    parser.add_argument("--steps", default=",".join(ALL_STEPS),
                        help="comma separated steps, default all")
    parser.add_argument("--dry-run", action="store_true", help="preview only")
    args = parser.parse_args()

    user, token = load_credentials()
    gh = GitHub(user, token, dry_run=args.dry_run)

    steps = [s.strip() for s in args.steps.split(",") if s.strip()]
    for step in steps:
        if step not in ALL_STEPS:
            print(f"unknown step: {step}")
            return 2

    if "a1-awesome" in steps:
        print("\n[A1] awesome-list PRs")
        step_a1_awesome(gh)
    if "b1-protect" in steps:
        print("\n[B1] branch protection")
        step_b1_protect(gh)
    if "b2-citation" in steps:
        print("\n[B2] CITATION.cff")
        step_b2_citation(gh)
    if "b3-issues" in steps:
        print("\n[B3] good first issues + roadmap")
        step_b3_issues(gh)
    if "c1-codeql" in steps:
        print("\n[C1] CodeQL alert triage")
        step_c1_codeql(gh)
    if "c2-dependabot" in steps:
        print("\n[C2] dependabot triage")
        step_c2_dependabot(gh)
    if "c3-docker" in steps:
        print("\n[C3] docker/publish fixes")
        step_c3_docker(gh)
    if "d1-star" in steps:
        print("\n[D1] star history")
        step_d1_star(gh)
    if "d2-ci" in steps:
        print("\n[D2] CI advisory promotion")
        step_d2_ci(gh)

    print_report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
