"""
批量为 GitHub 仓库设置 topics 标签，提升开源项目可发现性。

背景：
    topics 是 GitHub 项目被检索到的主要入口之一（topic 聚合页、站内搜索
    权重、以及大量第三方 awesome/榜单爬虫的数据来源）。经排查，账号下
    全部仓库 topics 均为空，等同于放弃自然流量入口。

标签策略参考头部项目（LiteLLM / OpenHands / Langfuse 等）的实际用法：
    - 赛道词（llm-gateway / llm-evaluation）保证能被同类检索命中
    - 技术栈词（python / fastapi / typescript）覆盖技术选型检索
    - 场景词（self-hosted / observability）覆盖需求侧检索

用法：
    python scripts/apply_repo_topics.py            # 应用
    python scripts/apply_repo_topics.py --dry-run  # 仅预览
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

import requests
import yaml

# GitHub topics 规则：小写、数字、连字符，单个仓库最多 20 个
REPO_TOPICS: Dict[str, List[str]] = {
    "loopforge": [
        "ai-agent", "autonomous-agents", "multi-agent-systems",
        "agent-orchestration", "code-generation", "ai-coding-assistant",
        "llm", "llmops", "fastapi", "python", "react", "developer-tools",
    ],
    "unified-ai-gateway": [
        "ai-gateway", "llm-gateway", "llm-proxy", "openai-api",
        "openai-compatible", "self-hosted", "load-balancing", "failover",
        "llmops", "typescript", "anthropic", "developer-tools",
    ],
    "moe-bench-studio": [
        "llm", "moe", "mixture-of-experts", "benchmark", "benchmarking",
        "llm-inference", "llm-evaluation", "vllm", "fastapi", "python",
        "evaluation", "performance-testing",
    ],
    "argus-eval": [
        "llm-evaluation", "ai-agent", "observability", "llmops",
        "tracing", "monitoring", "evaluation", "llm", "python",
        "opentelemetry", "developer-tools",
    ],
    "ai-daily-agent": [
        "ai-agent", "autonomous-agents", "automation", "llm",
        "github-api", "devops-automation", "python", "developer-tools",
        "content-automation",
    ],
    "ai-daily-hub": [
        "ai", "awesome-list", "llm", "ai-projects", "daily-updates",
        "open-source",
    ],
    "ai-daily-20260731-gemini-robotics-2-full-body-control": [
        "robotics", "ai", "gemini", "embodied-ai", "robot-control",
        "python", "vla", "toolkit",
    ],
    "ai-daily-20260731-worlddit-robot-world-action-model": [
        "robotics", "world-model", "diffusion-transformer", "embodied-ai",
        "ai", "python", "simulation",
    ],
    "ai-daily-20260731-gpt-5-announcement": [
        "nlp", "text-summarization", "keyword-extraction",
        "sentiment-analysis", "named-entity-recognition", "python", "ai",
    ],
    "ai-daily-20260731-openai-gpt-5-announcement-what-we-know": [
        "ai", "llm", "gpt", "python", "research-notes",
    ],
}

API_ROOT = "https://api.github.com"


def load_credentials(config_path: Path) -> Dict[str, str]:
    """从 config.yaml 读取 GitHub 用户名与 token。"""
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    gh = config.get("github", {})
    username = gh.get("username", "")
    token = gh.get("token", "")
    if not username or not token:
        raise SystemExit("config.yaml 缺少 github.username 或 github.token")
    return {"username": username, "token": token}


def apply_topics(session: requests.Session, owner: str, repo: str,
                 topics: List[str], dry_run: bool) -> bool:
    """
    为单个仓库设置 topics。

    Returns:
        True if applied (or would be applied in dry-run) successfully.
    """
    if dry_run:
        print(f"  [dry-run] {repo}: {', '.join(topics)}")
        return True

    url = f"{API_ROOT}/repos/{owner}/{repo}/topics"
    resp = session.put(url, json={"names": topics}, timeout=30)
    if resp.status_code == 200:
        applied = resp.json().get("names", [])
        print(f"  [ok] {repo}: {len(applied)} topics")
        return True

    print(f"  [fail] {repo}: HTTP {resp.status_code} {resp.text[:120]}")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="批量设置 GitHub 仓库 topics")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径")
    parser.add_argument("--dry-run", action="store_true", help="仅预览不写入")
    args = parser.parse_args()

    creds = load_credentials(Path(args.config))
    owner = creds["username"]

    session = requests.Session()
    session.headers.update({
        "Authorization": f"token {creds['token']}",
        "Accept": "application/vnd.github+json",
    })

    print(f"为 {owner} 的 {len(REPO_TOPICS)} 个仓库设置 topics"
          f"{' (dry-run)' if args.dry_run else ''}...")

    ok = sum(
        apply_topics(session, owner, repo, topics, args.dry_run)
        for repo, topics in REPO_TOPICS.items()
    )

    print(f"\n完成：{ok}/{len(REPO_TOPICS)} 个仓库处理成功")
    return 0 if ok == len(REPO_TOPICS) else 1


if __name__ == "__main__":
    sys.exit(main())
