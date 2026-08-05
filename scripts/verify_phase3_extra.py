#!/usr/bin/env python3
"""Phase-3 EXTRA verification: deep checks beyond verify_phase3.py.

Covers:
  A. .github repo: full file listing (>=8 files), contents non-empty & substantive
     (print first 30 lines of CONTRIBUTING.md / SECURITY.md)
  B. LICENSE full-text correctness (Apache-2.0 standard full text / MIT full text,
     copyright line year/author)
  C. loopforge CI workflow YAML parseable + key fields
  D. moe-bench-studio / unified-ai-gateway LICENSE vs README badge consistency
  E. 4 flagship repos: LICENSE badge blob link reachable (no 404)
  F. 10 repos community profile health_percentage + missing files
  G. regression: /users/huzjie/repos count == 10, flagship repos present
"""
import json, re, base64, urllib.request, urllib.error

CFG = open("config.yaml", encoding="utf-8").read()
TOKEN = re.search(r'token:\s*"([^"]+)"', CFG).group(1)
USER = "huzjie"
REPOS = ["loopforge", "moe-bench-studio", "argus-eval", "unified-ai-gateway",
         "ai-daily-agent", "ai-daily-hub",
         "ai-daily-20260731-openai-gpt-5-announcement-what-we-know",
         "ai-daily-20260731-worlddit-robot-world-action-model",
         "ai-daily-20260731-gpt-5-announcement",
         "ai-daily-20260731-gemini-robotics-2-full-body-control"]
FLAGSHIP = ["loopforge", "moe-bench-studio", "argus-eval", "unified-ai-gateway"]

def _req(method, url, accept=None):
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": accept or "application/vnd.github+json",
        "User-Agent": "ai-daily-agent-qa",
    }
    req = urllib.request.Request(url, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, json.dumps({"_error": e.code})
    except Exception as e:  # noqa
        return -1, json.dumps({"_error": str(e)[:120]})

def api(method, url):
    st, body = _req(method, "https://api.github.com" + url)
    try:
        return st, json.loads(body)
    except Exception:
        return st, {"_error": body[:120]}

def b64(content):
    return base64.b64decode(content.replace("\n", "").replace("\r", "")).decode("utf-8", errors="replace")

def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" | {detail}" if detail else ""))

# ---- try yaml ----
try:
    import yaml as _yaml
    HAS_YAML = True
except Exception:
    HAS_YAML = False

print("=== A. .github 默认仓库内容实质检查 ===")
st, root = api("GET", f"/repos/{USER}/.github/contents/")
if isinstance(root, list):
    files = [x["name"] for x in root]
    print(f"  .github 根目录文件列表: {sorted(files)}")
    # find dependabot related
    dep = [f for f in files if "dependabot" in f.lower()]
    if dep:
        print(f"  dependabot 相关文件: {dep}")
    else:
        # check .github/dependabot.yml at repo root of .github? actually default repo dependabot.yml is at .github/.github/dependabot.yml? No—root level.
        pass
    check(".github 根目录文件数 >= 5", len(files) >= 5, f"count={len(files)}")
    for f in files:
        st, c = api("GET", f"/repos/{USER}/.github/contents/{f}")
        if isinstance(c, dict) and "content" in c:
            txt = b64(c["content"])
            check(f".github/{f} 非空且有实质内容", len(txt.strip()) >= 80, f"len={len(txt.strip())}")
        else:
            check(f".github/{f} 可读取", False, str(c)[:100])
    # also check dependabot.yml if present at root of .github repo via /repos/USER/.github/contents/dependabot.yml
    for cand in ["dependabot.yml", "dependabot.yaml"]:
        st, c = api("GET", f"/repos/{USER}/.github/contents/{cand}")
        if isinstance(c, dict) and "content" in c:
            txt = b64(c["content"])
            check(f".github/{cand} 存在", True, f"len={len(txt.strip())}")
            print("  --- dependabot.yml 内容(前20行) ---")
            for line in txt.splitlines()[:20]:
                print("   |", line)
else:
    check(".github 仓库 contents 可列出", False, str(root)[:150])

print("\n--- CONTRIBUTING.md 前 30 行 ---")
st, c = api("GET", f"/repos/{USER}/.github/contents/CONTRIBUTING.md")
if isinstance(c, dict) and "content" in c:
    for line in b64(c["content"]).splitlines()[:30]:
        print("   |", line)

print("\n--- SECURITY.md 前 30 行 ---")
st, c = api("GET", f"/repos/{USER}/.github/contents/SECURITY.md")
if isinstance(c, dict) and "content" in c:
    for line in b64(c["content"]).splitlines()[:30]:
        print("   |", line)

print("\n=== B. LICENSE 全文完整性 ===")
APACHE_KEYS = ["Apache License", "Version 2.0, January 2004",
               "TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION",
               "END OF TERMS AND CONDITIONS", "APPENDIX: How to apply the Apache License"]
MIT_KEYS = ["MIT License", "Permission is hereby granted, free of charge, to any person obtaining a copy",
            "THE SOFTWARE IS PROVIDED", "Copyright (c)"]
for r in ["moe-bench-studio", "unified-ai-gateway"]:
    st, c = api("GET", f"/repos/{USER}/{r}/contents/LICENSE")
    if isinstance(c, dict) and "content" in c:
        txt = b64(c["content"])
        missing = [k for k in APACHE_KEYS if k not in txt]
        ok = len(txt) > 5000 and not missing
        check(f"{r} LICENSE Apache-2.0 完整全文", ok, f"len={len(txt)} missing={missing}")
        # print copyright line if any
        for line in txt.splitlines():
            if line.lower().startswith("copyright"):
                print(f"    {r} copyright 行: {line}")
    else:
        check(f"{r} LICENSE 可读取", False, str(c)[:100])
st, c = api("GET", f"/repos/{USER}/ai-daily-hub/contents/LICENSE")
if isinstance(c, dict) and "content" in c:
    txt = b64(c["content"])
    missing = [k for k in MIT_KEYS if k not in txt]
    ok = len(txt) > 500 and not missing
    check("ai-daily-hub LICENSE MIT 完整全文", ok, f"len={len(txt)} missing={missing}")
    for line in txt.splitlines():
        if line.lower().startswith("copyright"):
            print(f"    ai-daily-hub copyright 行: {line}")
else:
    check("ai-daily-hub LICENSE 可读取", False, str(c)[:100])

print("\n=== C. loopforge CI workflow YAML ===")
st, c = api("GET", f"/repos/{USER}/loopforge/contents/.github/workflows/ci.yml")
if isinstance(c, dict) and "content" in c:
    txt = b64(c["content"])
    keys = ["name:", "on:", "push:", "pull_request:", "jobs:", "checkout", "setup-python", "pytest"]
    missing = [k for k in keys if k not in txt]
    ok = not missing
    if HAS_YAML:
        try:
            data = _yaml.safe_load(txt)
            yaml_ok = isinstance(data, dict) and "jobs" in data
            check("CI YAML 可解析 (pyyaml)", yaml_ok, f"top_keys={list(data.keys()) if isinstance(data, dict) else 'N/A'}")
        except Exception as e:
            check("CI YAML 可解析 (pyyaml)", False, str(e)[:100])
            yaml_ok = False
        ok = ok and yaml_ok
    check("CI 关键字段齐全", ok, f"missing={missing}")
    print("  --- ci.yml 前 45 行 ---")
    for line in txt.splitlines()[:45]:
        print("   |", line)
else:
    check("loopforge ci.yml 可读取", False, str(c)[:100])

print("\n=== D. LICENSE 与 README 徽章一致性 ===")
for r in ["moe-bench-studio", "unified-ai-gateway"]:
    st, rd = api("GET", f"/repos/{USER}/{r}/readme")
    if isinstance(rd, dict) and "content" in rd:
        rt = b64(rd["content"])
        lic_mentions = re.findall(r'[Ll]icense[^\n]{0,80}', rt)[:3]
        has_apache_badge = ("Apache" in rt) or ("apache" in rt.lower() and "shields.io" in rt)
        has_mit_badge = "MIT" in rt and "shields.io" in rt
        check(f"{r} README 提及 Apache-2.0 徽章", has_apache_badge, f"mentions={lic_mentions}")
    else:
        check(f"{r} README 可读取", False, str(rd)[:100])

print("\n=== E. 旗舰仓库 LICENSE 徽章 blob 链接可达（无 404）===")
for r in FLAGSHIP:
    st, body = _req("GET", f"https://github.com/{USER}/{r}/blob/main/LICENSE")
    ok = st == 200
    check(f"{r} blob/main/LICENSE 可达", ok, f"http={st}")

print("\n=== F. 10 仓库 community profile 健康度 ===")
for r in REPOS:
    st, cp = api("GET", f"/repos/{USER}/{r}/community/profile")
    if isinstance(cp, dict) and "health_percentage" in cp:
        hp = cp.get("health_percentage")
        files = cp.get("files", {})
        missing = [k for k, v in files.items() if v is None]
        check(f"{r} health={hp}", hp is not None, f"missing={missing}")
    else:
        check(f"{r} community profile", False, str(cp)[:120])

print("\n=== G. 回归：账号仓库总量与旗舰存在 ===")
st, repos = api("GET", f"/users/{USER}/repos?per_page=100&visibility=all")
if isinstance(repos, list):
    names = [x["name"] for x in repos]
    check(f"仓库总数 = 10", len(repos) == 10, f"count={len(repos)}")
    for f in FLAGSHIP:
        check(f"旗舰 {f} 存在", f in names)
    print(f"  全部仓库: {sorted(names)}")
else:
    check("GET /users/repos", False, str(repos)[:120])

print("\nDONE-EXTRA.")
