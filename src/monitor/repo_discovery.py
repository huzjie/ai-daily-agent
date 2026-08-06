"""
Repository discovery service.

Automatically discovers tracked repositories from GitHub
and synchronizes with local published_repos.json.

追踪范围由 config.monitor.tracking 配置驱动，支持三种模式：
- all       : 追踪账号下全部仓库（默认，推荐 —— 不会漏掉旗舰项目）
- prefix    : 仅追踪 github.repo_prefix 前缀的仓库（旧行为）
- whitelist : 仅追踪 tracking.include 显式列出的仓库

无论哪种模式，均可通过 tracking.exclude / exclude_forks /
exclude_archived 做进一步排除。
"""

import fnmatch
import json
import logging
from pathlib import Path
from typing import Dict, List

from .github_client import GitHubAPIClient
from .models import Repository

logger = logging.getLogger(__name__)

# 追踪模式
MODE_ALL = "all"
MODE_PREFIX = "prefix"
MODE_WHITELIST = "whitelist"

VALID_MODES = {MODE_ALL, MODE_PREFIX, MODE_WHITELIST}


class RepoDiscoveryService:
    """
    自动发现 GitHub 上需要追踪的仓库。

    通过 GitHub API 客户端获取用户的所有仓库，
    再按配置的追踪策略过滤，并与本地记录同步。
    """

    def __init__(self, github_client: GitHubAPIClient, config: Dict):
        """
        Initialize the discovery service.

        Args:
            github_client: GitHub API client instance.
            config: Application configuration dictionary.
        """
        self.github_client = github_client
        self.config = config
        self.username = config.get("github", {}).get("username", "")
        self.repo_prefix = config.get("github", {}).get("repo_prefix", "ai-daily-")

        tracking = (config.get("monitor", {}) or {}).get("tracking", {}) or {}
        mode = str(tracking.get("mode", MODE_ALL)).lower().strip()
        if mode not in VALID_MODES:
            logger.warning(
                f"Unknown tracking mode '{mode}', falling back to '{MODE_ALL}'"
            )
            mode = MODE_ALL
        self.mode = mode
        self.include: List[str] = list(tracking.get("include", []) or [])
        self.exclude: List[str] = list(tracking.get("exclude", []) or [])
        self.exclude_forks: bool = bool(tracking.get("exclude_forks", True))
        self.exclude_archived: bool = bool(tracking.get("exclude_archived", False))
        self.exclude_meta: bool = bool(tracking.get("exclude_meta", False))

    def discover_all_repos(self) -> List[Repository]:
        """
        从 GitHub 发现所有需要追踪的仓库。

        Returns:
            List of discovered Repository objects.
        """
        logger.info(
            f"Discovering repos for user: {self.username} (mode={self.mode})"
        )

        # prefix 模式才把前缀下推给 API 层；其余模式一律全量拉取后本地过滤，
        # 避免旗舰项目在 API 层就被丢弃。
        api_prefix = self.repo_prefix if self.mode == MODE_PREFIX else ""

        raw_repos = self.github_client.list_user_repos(
            owner=self.username,
            prefix=api_prefix,
        )

        repos = [r for r in raw_repos if self._should_track(r)]

        skipped = len(raw_repos) - len(repos)
        logger.info(
            f"Discovered {len(repos)} repos from GitHub "
            f"(fetched {len(raw_repos)}, skipped {skipped})"
        )
        return repos

    def _should_track(self, repo: Repository) -> bool:
        """
        判断单个仓库是否应纳入追踪范围。

        Args:
            repo: Repository object to evaluate.

        Returns:
            True if the repo should be tracked.
        """
        name = repo.name
        if not name:
            return False

        # 1) 硬性排除
        if self.exclude_forks and repo.is_fork:
            logger.debug(f"Skip fork: {name}")
            return False
        if self.exclude_archived and repo.archived:
            logger.debug(f"Skip archived: {name}")
            return False
        # 账号级元仓库（如 .github 默认社区健康文件仓库），非项目
        if self.exclude_meta and name == ".github":
            logger.debug(f"Skip meta repo: {name}")
            return False
        # 同名 profile README 仓库（如 huzjie/huzjie），非项目仓库
        if self.exclude_meta and name == self.username:
            logger.debug(f"Skip profile repo: {name}")
            return False
        if self._match_any(name, self.exclude):
            logger.debug(f"Skip by exclude rule: {name}")
            return False

        # 2) 白名单命中即追踪（可跨模式补充）
        if self._match_any(name, self.include):
            return True

        # 3) 按模式判定
        if self.mode == MODE_ALL:
            return True
        if self.mode == MODE_PREFIX:
            return name.startswith(self.repo_prefix)
        # whitelist 模式下未命中 include 则不追踪
        return False

    @staticmethod
    def _match_any(name: str, patterns: List[str]) -> bool:
        """
        判断仓库名是否匹配任一模式（支持 fnmatch 通配符）。

        Args:
            name: Repository name.
            patterns: List of glob-style patterns or exact names.

        Returns:
            True if name matches any pattern.
        """
        for pattern in patterns:
            if not pattern:
                continue
            if name == pattern or fnmatch.fnmatch(name, pattern):
                return True
        return False

    def sync_with_local(
        self,
        discovered_repos: List[Repository],
        local_repos: List[Dict],
    ) -> Dict:
        """
        同步 GitHub 发现的仓库与本地记录。

        Compares discovered repos from GitHub with local published_repos.json
        to identify differences and missing repos.

        Args:
            discovered_repos: List of repositories discovered from GitHub.
            local_repos: List of local repository records from published_repos.json.

        Returns:
            Dictionary with sync results:
            - only_in_github: Repos on GitHub but not in local records.
            - only_in_local: Repos in local records but not on GitHub.
            - synced: Count of repos present in both.
        """
        discovered_names = {repo.name for repo in discovered_repos}
        local_names = {repo.get("name") for repo in local_repos}

        # Find differences
        only_in_github = discovered_names - local_names
        only_in_local = local_names - discovered_names
        synced = discovered_names & local_names

        result = {
            "only_in_github": list(only_in_github),
            "only_in_local": list(only_in_local),
            "synced": len(synced),
        }

        logger.info(
            f"Sync results: {len(only_in_github)} only on GitHub, "
            f"{len(only_in_local)} only in local, "
            f"{len(synced)} synced"
        )
        return result

    def load_local_repos(self, published_repos_file: str) -> List[Dict]:
        """
        Load local published repositories from JSON file.

        Args:
            published_repos_file: Path to published_repos.json.

        Returns:
            List of repository dictionaries. Empty list on failure.
        """
        try:
            with open(published_repos_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                logger.warning(f"Unexpected format in {published_repos_file}")
                return []
        except FileNotFoundError:
            logger.debug(f"Local repos file not found: {published_repos_file}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse {published_repos_file}: {e}")
            return []
