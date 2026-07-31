"""
Repository discovery service.

Automatically discovers ai-daily-* repositories from GitHub
and synchronizes with local published_repos.json.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List

from .github_client import GitHubAPIClient
from .models import Repository

logger = logging.getLogger(__name__)


class RepoDiscoveryService:
    """
    自动发现 GitHub 上的 ai-daily-* 仓库。

    通过 GitHub API 客户端获取用户的所有仓库，
    过滤出 ai-daily-* 前缀的仓库，并与本地记录同步。
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

    def discover_all_repos(self) -> List[Repository]:
        """
        从 GitHub 发现所有 ai-daily-* 仓库。

        Returns:
            List of discovered Repository objects.
        """
        logger.info(f"Discovering repos for user: {self.username}")

        repos = self.github_client.list_user_repos(
            owner=self.username,
            prefix=self.repo_prefix,
        )

        logger.info(f"Discovered {len(repos)} repos from GitHub")
        return repos

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
