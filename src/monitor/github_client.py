"""
GitHub API client abstraction layer.

Implements the Strategy Pattern for GitHub API access:
- GitHubClientBase: Abstract interface
- GhCliClient: gh CLI implementation
- RestApiClient: REST API implementation
- GitHubAPIClient: Context class that auto-switches between strategies
"""

import json
import logging
import subprocess
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import requests
import requests.exceptions

from .models import APIClientType, Repository, RepositoryMetrics

logger = logging.getLogger(__name__)

# Timeout constants (seconds)
DEFAULT_TIMEOUT = 30
AUTH_TIMEOUT = 10


class GitHubClientBase(ABC):
    """GitHub API 客户端抽象基类"""

    @abstractmethod
    def check_auth(self) -> bool:
        """检查认证状态"""
        pass

    @abstractmethod
    def get_repo_metrics(self, owner: str, repo: str) -> Optional[RepositoryMetrics]:
        """获取单个仓库指标"""
        pass

    @abstractmethod
    def list_user_repos(self, owner: str, prefix: str = "") -> List[Repository]:
        """列出用户的所有仓库（可选前缀过滤）"""
        pass

    @abstractmethod
    def get_rate_limit_status(self) -> Dict:
        """获取 API 速率限制状态"""
        pass


class GhCliClient(GitHubClientBase):
    """
    基于 gh CLI 的 GitHub 客户端实现。

    通过 subprocess 调用 gh 命令行工具与 GitHub API 交互。
    需要系统已安装并认证 gh CLI。
    """

    def __init__(self, config: Dict):
        """
        Initialize the gh CLI client.

        Args:
            config: Application configuration dictionary.
        """
        self.config = config
        self.username = config.get("github", {}).get("username", "")

    def check_auth(self) -> bool:
        """检查 gh CLI 认证状态"""
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=AUTH_TIMEOUT,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            logger.debug(f"gh CLI auth check failed: {e}")
            return False

    def get_repo_metrics(self, owner: str, repo: str) -> Optional[RepositoryMetrics]:
        """通过 gh CLI 获取仓库指标"""
        try:
            cmd = [
                "gh", "repo", "view", f"{owner}/{repo}",
                "--json", "stargazerCount,forkCount,watchers,issues",
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=DEFAULT_TIMEOUT,
            )
            if result.returncode != 0:
                logger.warning(f"gh CLI error for {owner}/{repo}: {result.stderr}")
                return None

            data = json.loads(result.stdout)
            return RepositoryMetrics(
                stars=data.get("stargazerCount", 0),
                forks=data.get("forkCount", 0),
                watchers=data.get("watchers", {}).get("totalCount", 0)
                    if isinstance(data.get("watchers"), dict) else 0,
                issues=data.get("issues", {}).get("totalCount", 0)
                    if isinstance(data.get("issues"), dict) else 0,
                last_updated="",
            )
        except subprocess.TimeoutExpired:
            logger.error(f"gh CLI timeout for {owner}/{repo}")
            return None
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"gh CLI error for {owner}/{repo}: {e}")
            return None

    def list_user_repos(self, owner: str, prefix: str = "") -> List[Repository]:
        """通过 gh CLI 列出用户仓库"""
        repos: List[Repository] = []
        try:
            cmd = [
                "gh", "repo", "list", owner,
                "--limit", "200",
                "--json", "name,fullName,url,description,createdAt,pushedAt,stargazerCount,forkCount,primaryLanguage,isFork,isArchived",
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                logger.warning(f"gh CLI list repos failed: {result.stderr}")
                return []

            data = json.loads(result.stdout)
            for repo_data in data:
                repo_name = repo_data.get("name", "")
                # 仅按调用方显式传入的 prefix 过滤；
                # 不再硬编码 "ai-daily-" 前缀，否则会漏掉旗舰项目。
                # 过滤策略统一由 RepoDiscoveryService 依据配置决定。
                if prefix and not repo_name.startswith(prefix):
                    continue

                repo = Repository(
                    name=repo_name,
                    full_name=repo_data.get("fullName", f"{owner}/{repo_name}"),
                    url=repo_data.get("url", ""),
                    description=repo_data.get("description", "") or "",
                    metrics=RepositoryMetrics(
                        stars=repo_data.get("stargazerCount", 0),
                        forks=repo_data.get("forkCount", 0),
                        watchers=repo_data.get("subscribersCount", 0),
                    ),
                    published_at=repo_data.get("createdAt", ""),
                    language=(repo_data.get("primaryLanguage") or {}).get("name", "")
                        if isinstance(repo_data.get("primaryLanguage"), dict) else "",
                    is_fork=repo_data.get("isFork", False),
                    archived=repo_data.get("isArchived", False),
                    pushed_at=repo_data.get("pushedAt", ""),
                )
                repos.append(repo)

        except subprocess.TimeoutExpired:
            logger.error(f"gh CLI timeout listing repos for {owner}")
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"gh CLI error listing repos for {owner}: {e}")

        return repos

    def get_rate_limit_status(self) -> Dict:
        """gh CLI 不直接支持速率限制查询，返回不可用"""
        return {"available": False}


class RestApiClient(GitHubClientBase):
    """
    基于 GitHub REST API 的客户端实现。

    使用 requests 库直接调用 GitHub REST API v3。
    需要有效的 GitHub Personal Access Token。
    """

    def __init__(self, config: Dict):
        """
        Initialize the REST API client.

        Args:
            config: Application configuration dictionary.
        """
        self.config = config
        self.username = config.get("github", {}).get("username", "")
        self.token = config.get("github", {}).get("token", "")
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        })

    def check_auth(self) -> bool:
        """检查 REST API 认证状态"""
        try:
            response = self.session.get(
                f"{self.base_url}/user",
                timeout=AUTH_TIMEOUT,
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def get_repo_metrics(self, owner: str, repo: str) -> Optional[RepositoryMetrics]:
        """通过 REST API 获取仓库指标"""
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}"
            response = self.session.get(url, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()

            data = response.json()
            return RepositoryMetrics(
                stars=data.get("stargazers_count", 0),
                forks=data.get("forks_count", 0),
                watchers=data.get("subscribers_count", 0),
                issues=data.get("open_issues_count", 0),
                last_updated=data.get("updated_at", ""),
            )
        except requests.exceptions.Timeout:
            logger.error(f"REST API timeout for {owner}/{repo}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"REST API error for {owner}/{repo}: {e}")
            return None

    def list_user_repos(self, owner: str, prefix: str = "") -> List[Repository]:
        """通过 REST API 列出用户仓库"""
        repos: List[Repository] = []
        page = 1
        per_page = 100

        while True:
            try:
                url = f"{self.base_url}/users/{owner}/repos"
                params = {"page": page, "per_page": per_page, "type": "owner"}
                response = self.session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
                response.raise_for_status()

                data = response.json()
                if not data:
                    break

                for repo_data in data:
                    repo_name = repo_data.get("name", "")

                    # 仅按调用方显式传入的 prefix 过滤；
                    # 不再硬编码 "ai-daily-" 前缀，否则 loopforge / unified-ai-gateway
                    # 等旗舰项目会被静默丢弃。过滤策略统一交由 RepoDiscoveryService。
                    if prefix and not repo_name.startswith(prefix):
                        continue

                    repo = Repository(
                        name=repo_name,
                        full_name=repo_data.get("full_name", ""),
                        url=repo_data.get("html_url", ""),
                        description=repo_data.get("description", "") or "",
                        metrics=RepositoryMetrics(
                            stars=repo_data.get("stargazers_count", 0),
                            forks=repo_data.get("forks_count", 0),
                            watchers=repo_data.get("subscribers_count", 0),
                            issues=repo_data.get("open_issues_count", 0),
                            last_updated=repo_data.get("updated_at", ""),
                        ),
                        published_at=repo_data.get("created_at", ""),
                        language=repo_data.get("language", "") or "",
                        size_kb=repo_data.get("size", 0),
                        topics=repo_data.get("topics", []) or [],
                        archived=repo_data.get("archived", False),
                        is_fork=repo_data.get("fork", False),
                        homepage=repo_data.get("homepage", "") or "",
                        pushed_at=repo_data.get("pushed_at", ""),
                    )
                    repos.append(repo)

                # If fewer results than per_page, no more pages
                if len(data) < per_page:
                    break

                page += 1

            except requests.exceptions.Timeout:
                logger.error(f"REST API timeout listing repos (page {page})")
                break
            except requests.exceptions.RequestException as e:
                logger.error(f"REST API error listing repos: {e}")
                break

        return repos

    def get_rate_limit_status(self) -> Dict:
        """获取 REST API 速率限制状态"""
        try:
            response = self.session.get(
                f"{self.base_url}/rate_limit",
                timeout=AUTH_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()

            core_limit = data.get("resources", {}).get("core", {})
            return {
                "available": True,
                "limit": core_limit.get("limit", 0),
                "remaining": core_limit.get("remaining", 0),
                "reset_at": core_limit.get("reset", 0),
            }
        except requests.exceptions.RequestException:
            return {"available": False}


class GitHubAPIClient:
    """
    GitHub API 客户端上下文类（策略模式）。

    自动在 gh CLI 和 REST API 之间切换：
    1. 优先尝试 gh CLI（如果 prefer_cli=True）
    2. gh CLI 不可用时 fallback 到 REST API
    3. 如果两者都不可用，抛出 RuntimeError
    """

    def __init__(self, config: Dict, prefer_cli: bool = True):
        """
        Initialize the API client context.

        Args:
            config: Application configuration dictionary.
            prefer_cli: Whether to prefer gh CLI over REST API.
        """
        self.config = config
        self.prefer_cli = prefer_cli
        self.cli_client: Optional[GhCliClient] = None
        self.rest_client: Optional[RestApiClient] = None
        self.active_client: Optional[GitHubClientBase] = None
        self._init_clients()

    def _init_clients(self) -> None:
        """初始化客户端策略，自动选择可用的实现"""
        # Try gh CLI first if preferred
        if self.prefer_cli:
            try:
                self.cli_client = GhCliClient(self.config)
                if self.cli_client.check_auth():
                    self.active_client = self.cli_client
                    logger.info("Using gh CLI client")
                    return
                else:
                    logger.info("gh CLI not authenticated, trying REST API")
            except Exception as e:
                logger.warning(f"gh CLI initialization failed: {e}")

        # Fallback to REST API
        try:
            self.rest_client = RestApiClient(self.config)
            if self.rest_client.check_auth():
                self.active_client = self.rest_client
                logger.info("Using REST API client")
            else:
                logger.error("REST API authentication failed")
                raise RuntimeError("GitHub authentication failed for all clients")
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"REST API initialization failed: {e}")
            raise RuntimeError(f"GitHub client initialization failed: {e}")

    def get_client_type(self) -> APIClientType:
        """获取当前活跃的客户端类型"""
        if isinstance(self.active_client, GhCliClient):
            return APIClientType.GH_CLI
        return APIClientType.REST_API

    def get_repo_metrics(self, owner: str, repo: str) -> Optional[RepositoryMetrics]:
        """
        获取仓库指标（自动使用当前活跃客户端）。

        Args:
            owner: Repository owner (GitHub username or org).
            repo: Repository name.

        Returns:
            RepositoryMetrics on success, None on failure.
        """
        try:
            return self.active_client.get_repo_metrics(owner, repo)
        except Exception as e:
            logger.error(f"Failed to get metrics for {owner}/{repo}: {e}")
            return None

    def list_user_repos(self, owner: str, prefix: str = "") -> List[Repository]:
        """
        列出用户仓库。

        Args:
            owner: GitHub username.
            prefix: Optional prefix filter for repo names.

        Returns:
            List of Repository objects. Empty list on failure.
        """
        try:
            return self.active_client.list_user_repos(owner, prefix)
        except Exception as e:
            logger.error(f"Failed to list repos for {owner}: {e}")
            return []

    def get_rate_limit_status(self) -> Dict:
        """
        获取速率限制状态。

        Returns:
            Dictionary with rate limit info. Always returns a dict.
        """
        try:
            return self.active_client.get_rate_limit_status()
        except Exception as e:
            logger.error(f"Failed to get rate limit status: {e}")
            return {"available": False}
