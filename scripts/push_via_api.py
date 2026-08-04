"""
通过 GitHub Git Data API 推送提交（绕过被阻断的 git 传输协议）。

适用场景：
    某些网络环境下 github.com 的 git 传输协议（443）被重置，
    但 api.github.com 可正常访问。此时 `git push` 不可用，
    可改用 Git Data API 逐层构建 blob → tree → commit → ref。

工作流程：
    1. 读取远端分支当前 HEAD 与其 tree
    2. 将本地指定提交涉及的文件上传为 blob
    3. 以远端 tree 为 base 创建新 tree（支持删除文件）
    4. 创建 commit 并将分支 ref 指向它

用法：
    python scripts/push_via_api.py --repo ai-daily-agent
    python scripts/push_via_api.py --repo ai-daily-agent --rev HEAD --dry-run
"""

import argparse
import base64
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
import yaml

API_ROOT = "https://api.github.com"
TIMEOUT = 60


def run_git(args: List[str], cwd: Path) -> str:
    """执行 git 命令并返回 stdout。"""
    result = subprocess.run(
        ["git"] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} 失败: {result.stderr.strip()}")
    return result.stdout


def load_credentials(config_path: Path) -> Tuple[str, str]:
    """从 config.yaml 读取 GitHub 用户名与 token。"""
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    gh = config.get("github", {})
    username, token = gh.get("username", ""), gh.get("token", "")
    if not username or not token:
        raise SystemExit("config.yaml 缺少 github.username 或 github.token")
    return username, token


def collect_changes(repo_root: Path, rev: str) -> Tuple[Dict[str, str], List[str]]:
    """
    收集指定提交相对其父提交的文件变更。

    Returns:
        (changed, deleted) —— changed 为 {路径: 状态}，deleted 为删除的路径列表。
    """
    raw = run_git(["diff", "--name-status", f"{rev}~1", rev], repo_root)
    changed: Dict[str, str] = {}
    deleted: List[str] = []

    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0].strip()
        # 重命名形如 R100\told\tnew
        if status.startswith("R") and len(parts) >= 3:
            deleted.append(parts[1])
            changed[parts[2]] = "M"
        elif status == "D" and len(parts) >= 2:
            deleted.append(parts[1])
        elif len(parts) >= 2:
            changed[parts[1]] = status

    return changed, deleted


class GitHubPusher:
    """基于 Git Data API 的提交推送器。"""

    def __init__(self, owner: str, repo: str, token: str, branch: str = "main"):
        self.owner = owner
        self.repo = repo
        self.branch = branch
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
        })

    def _url(self, path: str) -> str:
        return f"{API_ROOT}/repos/{self.owner}/{self.repo}{path}"

    def get_head(self) -> Tuple[str, str]:
        """获取远端分支 HEAD commit sha 及其 tree sha。"""
        resp = self.session.get(
            self._url(f"/git/ref/heads/{self.branch}"), timeout=TIMEOUT
        )
        resp.raise_for_status()
        commit_sha = resp.json()["object"]["sha"]

        resp = self.session.get(
            self._url(f"/git/commits/{commit_sha}"), timeout=TIMEOUT
        )
        resp.raise_for_status()
        return commit_sha, resp.json()["tree"]["sha"]

    def create_blob(self, content: bytes) -> str:
        """上传文件内容为 blob，返回 sha。"""
        resp = self.session.post(
            self._url("/git/blobs"),
            json={
                "content": base64.b64encode(content).decode("ascii"),
                "encoding": "base64",
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()["sha"]

    def create_tree(self, base_tree: str, entries: List[Dict]) -> str:
        """基于 base_tree 创建新 tree。"""
        resp = self.session.post(
            self._url("/git/trees"),
            json={"base_tree": base_tree, "tree": entries},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()["sha"]

    def create_commit(self, message: str, tree: str, parent: str) -> str:
        """创建 commit 对象。"""
        resp = self.session.post(
            self._url("/git/commits"),
            json={"message": message, "tree": tree, "parents": [parent]},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()["sha"]

    def update_ref(self, commit_sha: str) -> None:
        """将分支 ref 指向新 commit。"""
        resp = self.session.patch(
            self._url(f"/git/refs/heads/{self.branch}"),
            json={"sha": commit_sha, "force": False},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()


def main() -> int:
    parser = argparse.ArgumentParser(description="通过 GitHub API 推送提交")
    parser.add_argument("--repo", required=True, help="目标仓库名")
    parser.add_argument("--rev", default="HEAD", help="要推送的本地提交")
    parser.add_argument("--branch", default="main", help="目标分支")
    parser.add_argument("--root", default=".", help="本地仓库根目录")
    parser.add_argument("--config", default="config.yaml", help="配置文件")
    parser.add_argument("--dry-run", action="store_true", help="仅预览")
    args = parser.parse_args()

    repo_root = Path(args.root).resolve()
    owner, token = load_credentials(Path(args.config))

    message = run_git(["log", "-1", "--pretty=%B", args.rev], repo_root).strip()
    changed, deleted = collect_changes(repo_root, args.rev)

    print(f"目标: {owner}/{args.repo}@{args.branch}")
    print(f"提交: {message.splitlines()[0]}")
    print(f"变更: {len(changed)} 个文件新增/修改, {len(deleted)} 个删除")
    for path in changed:
        print(f"  + {path}")
    for path in deleted:
        print(f"  - {path}")

    if args.dry_run:
        print("\n[dry-run] 未实际推送")
        return 0

    pusher = GitHubPusher(owner, args.repo, token, args.branch)

    parent_sha, base_tree = pusher.get_head()
    print(f"\n远端 HEAD: {parent_sha[:8]}")

    entries: List[Dict] = []
    for path in changed:
        full = repo_root / path
        if not full.exists():
            print(f"  跳过不存在的文件: {path}")
            continue
        blob_sha = pusher.create_blob(full.read_bytes())
        entries.append({
            "path": path,
            "mode": "100755" if full.stat().st_mode & 0o100 else "100644",
            "type": "blob",
            "sha": blob_sha,
        })
        print(f"  blob {blob_sha[:8]}  {path}")

    for path in deleted:
        entries.append({
            "path": path, "mode": "100644", "type": "blob", "sha": None,
        })

    if not entries:
        print("没有需要推送的内容")
        return 0

    tree_sha = pusher.create_tree(base_tree, entries)
    print(f"tree: {tree_sha[:8]}")

    commit_sha = pusher.create_commit(message, tree_sha, parent_sha)
    print(f"commit: {commit_sha[:8]}")

    pusher.update_ref(commit_sha)
    print(f"\n推送成功 → https://github.com/{owner}/{args.repo}/commit/{commit_sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
