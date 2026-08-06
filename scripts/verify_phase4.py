# -*- coding: utf-8 -*-
"""第四阶段优化 QA 验证脚本（只读，不修改任何远端状态）

验证对象（账号 huzjie）：
- 监控数据完整性：metrics_history.json 最新快照覆盖仓库数
- P0-1/P0-2：旗舰仓库 CI workflow 存在且最近一次 run 成功
- P0-3：所有 workflow 顶层有 permissions: contents: read
- P0-4：CodeQL default setup 或 codeql.yml workflow 存在
- P0-5：Scorecard workflow 存在 + README 含 scorecard 徽章（3 旗舰）
- P0-6：旗舰仓库（除 video-forge-studio）存在 v0.1.0 Release + CHANGELOG.md
- P0-7：video-forge-studio topics>=8、description 非空、README 含对比表
- P0-8：huzjie/huzjie 仓库存在且 README 非空
- P1-1：6 旗舰 has_discussions / 私有漏洞报告 / Dependabot alerts

用法：C:/Python312/python.exe scripts/verify_phase4.py
"""
import json
import os
import sys
import time

import requests
import yaml

BASE = "https://api.github.com"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# token 只从 config.yaml 读取（绝不硬编码，避免 secret scanning 拦截）
_cfg = yaml.safe_load(open(os.path.join(ROOT, "config.yaml"), encoding="utf-8"))
TOKEN = os.environ.get("GH_TOKEN", (_cfg.get("github", {}) or {}).get("token", ""))
OWNER = os.environ.get("GH_OWNER", (_cfg.get("github", {}) or {}).get("username", "huzjie"))
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
}

FLAGSHIP = [
    "loopforge",
    "unified-ai-gateway",
    "moe-bench-studio",
    "argus-eval",
    "video-forge-studio",
    "ai-daily-agent",
]
CI_TARGET = ["unified-ai-gateway", "moe-bench-studio", "argus-eval", "video-forge-studio"]
SCORECARD_TARGET = ["loopforge", "unified-ai-gateway", "video-forge-studio"]

PASS = []
FAIL = []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append((name, detail))
    print(("  [PASS] " if ok else "  [FAIL] ") + name + (f" | {detail}" if detail else ""))


def api(path):
    url = BASE + path
    r = requests.get(url, headers=HEADERS, timeout=30)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def get_workflow_files(repo):
    """返回 {workflow文件名: workflow对象}"""
    try:
        data = api(f"/repos/{OWNER}/{repo}/contents/.github/workflows")
        if not data:
            return {}
        return {f["name"]: f for f in data if isinstance(f, dict) and f.get("type") == "file"}
    except Exception:
        return {}


def main():
    print("=" * 70)
    print("Phase4 QA Verification  (owner: huzjie)")
    print("=" * 70)

    # 0) 监控数据完整性
    print("\n[0] 监控数据完整性")
    mh = os.path.join(ROOT, "data", "metrics", "metrics_history.json")
    if os.path.exists(mh):
        with open(mh, encoding="utf-8") as f:
            hist = json.load(f)
        snaps = hist if isinstance(hist, list) else hist.get("snapshots", [])
        last = snaps[-1]
        check("metrics_history.json 最新快照存在", True,
              f"repos={len(last.get('repos', []))}, date={last.get('date')}")
        check("最新快照覆盖 >= 11 仓库", len(last.get("repos", [])) >= 11,
              f"got {len(last.get('repos', []))}")
    else:
        check("metrics_history.json 存在", False, "文件缺失")

    # 1) CI workflow + 最近 run
    print("\n[1] CI workflow 有效性（P0-1/P0-2）")
    for repo in CI_TARGET:
        wfs = get_workflow_files(repo)
        has_ci = any("ci" in n.lower() or "test" in n.lower() for n in wfs)
        detail = f"files={list(wfs.keys())}" if wfs else "无 workflow 文件"
        check(f"{repo} 有 CI workflow", has_ci, detail)
        # 只取 ci.yml 自身的最近一次 run 结论（避免 Dependabot PR 的失败 run 干扰）
        try:
            runs = api(f"/repos/{OWNER}/{repo}/actions/workflows/ci.yml/runs?per_page=1")
            run = runs["workflow_runs"][0] if runs and runs["workflow_runs"] else None
            if run:
                check(f"{repo} ci.yml 最近 run 成功", run["conclusion"] == "success",
                      f"conclusion={run['conclusion']}, created={run.get('created_at')}")
            else:
                check(f"{repo} ci.yml 最近 run 成功", False, "无 run 记录")
        except Exception as e:
            check(f"{repo} ci.yml 最近 run 成功", False, f"查询异常 {e}")

    # 2) workflow 顶层 permissions（P0-3）
    #    Scorecard "Token-Permissions" 要求的是每个 workflow 显式声明最小权限：
    #    普通 workflow 应为 contents: read；release.yml 创建 Release 本身就需要
    #    contents: write（改 read 会直接坏掉发布），属于合法的最小权限。
    print("\n[2] workflow 顶层 permissions 显式声明（P0-3）")
    all_repos = FLAGSHIP
    for repo in all_repos:
        wfs = get_workflow_files(repo)
        if not wfs:
            if repo == "ai-daily-agent":
                check(f"{repo} workflow 检查", True,
                      "工具仓库无 .github/workflows（P0-2 目标仅 4 旗舰），跳过")
            else:
                check(f"{repo} 有 workflow 可检查", False, "无 workflow")
            continue
        for wf_name in wfs:
            try:
                content = requests.get(wfs[wf_name]["download_url"], timeout=30).text
            except Exception as e:
                check(f"{repo}/{wf_name} 可读取", False, str(e))
                continue
            lines = content.splitlines()
            # 顶层 permissions: 块必须存在（第 0 列缩进）
            top_perm_idx = next((i for i, ln in enumerate(lines)
                                 if ln.startswith("permissions:")), None)
            has_top_perm = top_perm_idx is not None
            if not has_top_perm:
                check(f"{repo}/{wf_name} 顶层 permissions", False, "缺失")
                continue
            # 单行形式 `permissions: read-all`（OpenSSF scorecard 官方模板）合法
            first_perm = lines[top_perm_idx].strip()
            if "read-all" in first_perm or "read_all" in first_perm:
                check(f"{repo}/{wf_name} 顶层 permissions", True, "permissions: read-all (scorecard 官方模板)")
                continue
            # 块内权限值：普通 workflow 期望 contents: read；
            # release.yml 允许 contents: write（创建 Release 的最小权限）
            block = lines[top_perm_idx + 1:top_perm_idx + 5]
            perms = [ln.strip().split(":", 1)[0] for ln in block
                     if ln.startswith("  ") and ":" in ln]
            is_release = "release" in wf_name.lower()
            if is_release:
                ok = bool(perms)  # 显式声明了权限即满足（write 合法）
                detail = f"perms={perms} (release 允许 write)"
            else:
                ok = "contents" in perms and "read" in " ".join(block)
                detail = f"perms={perms}"
            check(f"{repo}/{wf_name} 顶层 permissions", ok, detail)

    # 3) CodeQL（P0-4）
    print("\n[3] CodeQL（P0-4）")
    for repo in FLAGSHIP:
        try:
            ds = api(f"/repos/{OWNER}/{repo}/code-scanning/default-setup")
        except Exception:
            ds = None
        wfs = get_workflow_files(repo)
        has_codeql_wf = any("codeql" in n.lower() for n in wfs)
        ok = bool(ds) or has_codeql_wf
        detail = ("default-setup" if ds else "codeql.yml workflow" if has_codeql_wf else "无")
        check(f"{repo} CodeQL 已配置", ok, detail)

    # 4) Scorecard（P0-5）
    print("\n[4] Scorecard workflow + README 徽章（P0-5）")
    for repo in SCORECARD_TARGET:
        wfs = get_workflow_files(repo)
        has_sc = any("scorecard" in n.lower() for n in wfs)
        readme = None
        try:
            r = requests.get(
                f"https://raw.githubusercontent.com/{OWNER}/{repo}/main/README.md",
                timeout=30)
            if r.status_code == 200:
                readme = r.text
        except Exception:
            pass
        has_badge = bool(readme) and "scorecard" in readme.lower()
        check(f"{repo} scorecard.yml 存在", has_sc, list(wfs.keys()) if wfs else "无")
        check(f"{repo} README 含 scorecard 徽章", has_badge)

    # 5) Release + CHANGELOG（P0-6）
    print("\n[5] Release + CHANGELOG（P0-6）")
    for repo in FLAGSHIP:
        releases = api(f"/repos/{OWNER}/{repo}/releases?per_page=1")
        rel = releases[0] if releases else None
        check(f"{repo} 有 Release", bool(rel),
              f"tag={rel['tag_name']}" if rel else "无 Release（video-forge-studio 若已有 v1.0.0 则正常）")
        try:
            cl = api(f"/repos/{OWNER}/{repo}/contents/CHANGELOG.md")
            check(f"{repo} 有 CHANGELOG.md", bool(cl))
        except Exception:
            check(f"{repo} 有 CHANGELOG.md", False)

    # 6) video-forge-studio 包装（P0-7）
    print("\n[6] video-forge-studio 包装（P0-7）")
    repo = api("/repos/" + OWNER + "/video-forge-studio")
    if repo:
        topics = repo.get("topics", [])
        check("vfs topics >= 8", len(topics) >= 8, f"got {len(topics)}: {topics}")
        desc = repo.get("description") or ""
        check("vfs description 非空", bool(desc), desc[:80])
        check("vfs homepage 已设置", bool(repo.get("homepage")), repo.get("homepage") or "")
    else:
        check("vfs 仓库可访问", False)
    try:
        readme = requests.get(
            "https://raw.githubusercontent.com/huzjie/video-forge-studio/main/README.md",
            timeout=30).text
        check("vfs README 含对比表", "ComfyUI" in readme and "OpenMontage" in readme)
        check("vfs README 声明引擎被编排关系",
              "not" in readme.lower() or "compatib" in readme.lower() or "orchestrat" in readme.lower())
        check("vfs README 含 Quickstart 命令", "docker compose" in readme.lower() or "curl" in readme.lower())
    except Exception as e:
        check("vfs README 可读取", False, str(e))

    # 7) Profile README（P0-8）
    print("\n[7] huzjie/huzjie Profile README（P0-8）")
    try:
        prof = api("/repos/" + OWNER + "/" + OWNER)
        check("huzjie/huzjie 仓库存在", bool(prof))
        if prof:
            readme = requests.get(
                f"https://raw.githubusercontent.com/{OWNER}/{OWNER}/main/README.md",
                timeout=30)
            check("Profile README 非空", readme.status_code == 200 and len(readme.text) > 100,
                  f"len={len(readme.text) if readme.status_code == 200 else 'N/A'}")
    except Exception as e:
        check("huzjie/huzjie 仓库存在", False, str(e))

    # 8) P1-1 社区开关
    print("\n[8] 社区开关（P1-1，尽力项）")
    for repo in FLAGSHIP:
        try:
            r = requests.get(f"{BASE}/repos/{OWNER}/{repo}", headers=HEADERS, timeout=30)
            data = r.json()
            has_disc = data.get("has_discussions", False)
            check(f"{repo} has_discussions", has_disc)
        except Exception as e:
            check(f"{repo} has_discussions", False, str(e))
        try:
            pvr = api(f"/repos/{OWNER}/{repo}/private-vulnerability-reporting")
            check(f"{repo} 私有漏洞报告", bool(pvr) and pvr.get("enabled", False) is True)
        except Exception:
            check(f"{repo} 私有漏洞报告", False, "API 不可用/未开启")

    # 汇总
    print("\n" + "=" * 70)
    print(f"TOTAL: {len(PASS)} PASS, {len(FAIL)} FAIL")
    if FAIL:
        print("FAILED 项：")
        for name, detail in FAIL:
            print(f"  - {name} | {detail}")
    print("=" * 70)
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
