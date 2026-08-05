#!/usr/bin/env python3
"""Phase-3 verification: verify LICENSE / .github default health repo / CI / FUNDING on GitHub.

Reads token from config.yaml. Reports PASS/FAIL per check.
"""
import json, re, urllib.request, urllib.error, sys

CFG = open("config.yaml", encoding="utf-8").read()
TOKEN = re.search(r'token:\s*"([^"]+)"', CFG).group(1)
USER = "huzjie"

def _req(method, url):
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "ai-daily-agent",
    }
    req = urllib.request.Request(url, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode()
    except urllib.error.HTTPError as e:
        return json.dumps({"_error": e.code})

def api(method, url):
    return json.loads(_req(method, "https://api.github.com" + url))

def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" | {detail}" if detail else ""))

REPOS = ["loopforge", "moe-bench-studio", "argus-eval", "unified-ai-gateway",
         "ai-daily-agent", "ai-daily-hub",
         "ai-daily-20260731-openai-gpt-5-announcement-what-we-know",
         "ai-daily-20260731-worlddit-robot-world-action-model",
         "ai-daily-20260731-gpt-5-announcement",
         "ai-daily-20260731-gemini-robotics-2-full-body-control"]

print("=== 1. .github 默认社区健康仓库 ===")
gh_repo = api("GET", f"/repos/{USER}/.github")
if isinstance(gh_repo, dict) and "name" in gh_repo:
    check(".github 仓库存在", True)
    for f in ["CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md",
              "FUNDING.yml", "PULL_REQUEST_TEMPLATE.md",
              "ISSUE_TEMPLATE/bug_report.md", "ISSUE_TEMPLATE/feature_request.md"]:
        c = api("GET", f"/repos/{USER}/.github/contents/{f}")
        check(f".github/{f}", isinstance(c, dict) and "content" in c)
else:
    check(".github 仓库存在", False, str(gh_repo)[:120])

print("\n=== 2. LICENSE 补全（API license 识别）===")
for r in REPOS:
    info = api("GET", f"/repos/{USER}/{r}")
    lic = (info or {}).get("license")
    spdx = lic.get("spdx_id") if lic else None
    ok = spdx in ("Apache-2.0", "MIT")
    check(f"{r} license={spdx}", ok)

print("\n=== 3. loopforge CI workflow ===")
wf = api("GET", f"/repos/{USER}/loopforge/contents/.github/workflows/ci.yml")
check("loopforge/.github/workflows/ci.yml", isinstance(wf, dict) and "content" in wf)

print("\n=== 4. 旗舰仓库 FUNDING.yml ===")
for r in ["loopforge", "moe-bench-studio", "argus-eval", "unified-ai-gateway"]:
    f = api("GET", f"/repos/{USER}/{r}/contents/.github/FUNDING.yml")
    check(f"{r}/.github/FUNDING.yml", isinstance(f, dict) and "content" in f)

print("\n=== 5. 仓库基础属性 ===")
for r in REPOS:
    info = api("GET", f"/repos/{USER}/{r}")
    if isinstance(info, dict):
        check(f"{r}", not info.get("archived", False),
              f"stars={info.get('stargazers_count',0)} forks={info.get('forks_count',0)} "
              f"watchers={info.get('watchers_count',0)} issues={info.get('open_issues_count',0)} "
              f"desc_ok={bool(info.get('description'))} topics={len(info.get('topics',[]))}")

print("\nDONE.")
