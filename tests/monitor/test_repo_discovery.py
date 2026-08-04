"""
Tests for the repository discovery service.
"""

import json
from unittest.mock import Mock, patch

import pytest

from src.monitor.github_client import GitHubAPIClient
from src.monitor.models import Repository, RepositoryMetrics
from src.monitor.repo_discovery import RepoDiscoveryService


class TestRepoDiscoveryService:
    """Tests for RepoDiscoveryService."""

    def _make_config(self, username="testuser", prefix="ai-daily-", tracking=None):
        """Helper to build a test config."""
        config = {
            "github": {
                "username": username,
                "token": "test-token",
                "repo_prefix": prefix,
            }
        }
        if tracking is not None:
            config["monitor"] = {"tracking": tracking}
        return config

    def _make_sample_repos(self):
        """Helper to create sample repository list."""
        return [
            Repository(
                name="ai-daily-test-1",
                full_name="testuser/ai-daily-test-1",
                url="https://github.com/testuser/ai-daily-test-1",
                description="Test project 1",
                metrics=RepositoryMetrics(stars=10, forks=2),
                published_at="2026-07-01T00:00:00Z",
            ),
            Repository(
                name="ai-daily-test-2",
                full_name="testuser/ai-daily-test-2",
                url="https://github.com/testuser/ai-daily-test-2",
                description="Test project 2",
                metrics=RepositoryMetrics(stars=5, forks=1),
                published_at="2026-07-02T00:00:00Z",
            ),
        ]

    def test_discover_all_repos(self):
        """Test discovering all repos from GitHub."""
        config = self._make_config()
        mock_client = Mock(spec=GitHubAPIClient)
        sample_repos = self._make_sample_repos()
        mock_client.list_user_repos.return_value = sample_repos

        service = RepoDiscoveryService(mock_client, config)
        result = service.discover_all_repos()

        assert len(result) == 2
        assert result[0].name == "ai-daily-test-1"
        assert result[1].name == "ai-daily-test-2"
        # 默认 all 模式：不把前缀下推到 API 层，全量拉取后本地按规则过滤
        mock_client.list_user_repos.assert_called_once_with(
            owner="testuser",
            prefix="",
        )

    def test_discover_all_repos_empty(self):
        """Test discovering repos when none exist."""
        config = self._make_config()
        mock_client = Mock(spec=GitHubAPIClient)
        mock_client.list_user_repos.return_value = []

        service = RepoDiscoveryService(mock_client, config)
        result = service.discover_all_repos()

        assert result == []

    def test_discover_all_repos_api_failure(self):
        """Test discovering repos when API fails."""
        config = self._make_config()
        mock_client = Mock(spec=GitHubAPIClient)
        mock_client.list_user_repos.side_effect = Exception("API error")

        service = RepoDiscoveryService(mock_client, config)

        with pytest.raises(Exception):
            service.discover_all_repos()

    def test_sync_with_local_new_repos(self):
        """Test sync when GitHub has repos not in local records."""
        config = self._make_config()
        mock_client = Mock(spec=GitHubAPIClient)

        discovered = self._make_sample_repos()
        local = [
            {"name": "ai-daily-test-1", "stars": 10},
            {"name": "ai-daily-old", "stars": 100},
        ]

        service = RepoDiscoveryService(mock_client, config)
        result = service.sync_with_local(discovered, local)

        assert "ai-daily-test-2" in result["only_in_github"]
        assert "ai-daily-old" in result["only_in_local"]
        assert result["synced"] == 1

    def test_sync_with_local_all_synced(self):
        """Test sync when all repos are in both locations."""
        config = self._make_config()
        mock_client = Mock(spec=GitHubAPIClient)

        discovered = self._make_sample_repos()
        local = [
            {"name": "ai-daily-test-1", "stars": 10},
            {"name": "ai-daily-test-2", "stars": 5},
        ]

        service = RepoDiscoveryService(mock_client, config)
        result = service.sync_with_local(discovered, local)

        assert result["only_in_github"] == []
        assert result["only_in_local"] == []
        assert result["synced"] == 2

    def test_sync_with_local_empty_local(self):
        """Test sync when local records are empty."""
        config = self._make_config()
        mock_client = Mock(spec=GitHubAPIClient)

        discovered = self._make_sample_repos()
        local = []

        service = RepoDiscoveryService(mock_client, config)
        result = service.sync_with_local(discovered, local)

        assert len(result["only_in_github"]) == 2
        assert result["only_in_local"] == []
        assert result["synced"] == 0

    def test_load_local_repos_success(self):
        """Test loading local repos from a valid JSON file."""
        config = self._make_config()
        mock_client = Mock(spec=GitHubAPIClient)

        service = RepoDiscoveryService(mock_client, config)

        test_data = [
            {"name": "ai-daily-test-1", "stars": 10},
            {"name": "ai-daily-test-2", "stars": 5},
        ]

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = lambda s: s
            mock_open.return_value.__exit__ = Mock()
            mock_open.return_value.read = Mock()
            with patch("json.load", return_value=test_data):
                result = service.load_local_repos("published_repos.json")
                assert len(result) == 2

    def test_load_local_repos_file_not_found(self):
        """Test loading local repos when file doesn't exist."""
        config = self._make_config()
        mock_client = Mock(spec=GitHubAPIClient)

        service = RepoDiscoveryService(mock_client, config)
        result = service.load_local_repos("nonexistent.json")

        assert result == []

    def test_load_local_repos_invalid_json(self):
        """Test loading local repos with invalid JSON."""
        config = self._make_config()
        mock_client = Mock(spec=GitHubAPIClient)

        service = RepoDiscoveryService(mock_client, config)

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = lambda s: s
            # __exit__ 必须返回 False，否则 Mock() 的真值会吞掉异常，
            # 导致函数走不到 except 分支而隐式返回 None。
            mock_open.return_value.__exit__ = Mock(return_value=False)
            mock_open.return_value.read = Mock()
            with patch("src.monitor.repo_discovery.json.load", side_effect=json.JSONDecodeError("", "", 0)):
                result = service.load_local_repos("bad.json")
                assert result == []

    def test_custom_prefix(self):
        """Test using a custom repo prefix under prefix mode."""
        config = self._make_config(
            prefix="custom-prefix-",
            tracking={"mode": "prefix"},
        )
        mock_client = Mock(spec=GitHubAPIClient)
        mock_client.list_user_repos.return_value = []

        service = RepoDiscoveryService(mock_client, config)
        service.discover_all_repos()

        # 仅 prefix 模式才把前缀下推给 API 层
        mock_client.list_user_repos.assert_called_once_with(
            owner="testuser",
            prefix="custom-prefix-",
        )


class TestTrackingStrategy:
    """追踪范围策略测试（回归保护：旗舰项目不得被漏采）。"""

    def _make_repos(self):
        """构造混合仓库列表：含旗舰项目、日更项目、fork、归档。"""
        return [
            Repository(name="loopforge"),
            Repository(name="unified-ai-gateway"),
            Repository(name="ai-daily-20260731-gpt-5"),
            Repository(name="ai-daily-hub"),
            Repository(name="some-fork", is_fork=True),
            Repository(name="old-thing", archived=True),
            Repository(name="_stale-experiment"),
        ]

    def _make_service(self, tracking):
        config = {
            "github": {
                "username": "testuser",
                "token": "t",
                "repo_prefix": "ai-daily-",
            },
            "monitor": {"tracking": tracking},
        }
        mock_client = Mock(spec=GitHubAPIClient)
        mock_client.list_user_repos.return_value = self._make_repos()
        return RepoDiscoveryService(mock_client, config)

    def test_mode_all_includes_flagship_repos(self):
        """all 模式必须覆盖不带 ai-daily- 前缀的旗舰项目。"""
        service = self._make_service({"mode": "all"})
        names = {r.name for r in service.discover_all_repos()}

        # 这是本次修复的核心断言
        assert "loopforge" in names
        assert "unified-ai-gateway" in names
        assert "ai-daily-hub" in names
        # 默认排除 fork
        assert "some-fork" not in names

    def test_mode_prefix_keeps_legacy_behavior(self):
        """prefix 模式保持旧行为，仅追踪指定前缀。"""
        service = self._make_service({"mode": "prefix"})
        names = {r.name for r in service.discover_all_repos()}

        assert names == {"ai-daily-20260731-gpt-5", "ai-daily-hub"}

    def test_include_overrides_prefix_mode(self):
        """include 白名单可跨模式强制纳入。"""
        service = self._make_service({
            "mode": "prefix",
            "include": ["loopforge"],
        })
        names = {r.name for r in service.discover_all_repos()}

        assert "loopforge" in names
        assert "unified-ai-gateway" not in names

    def test_exclude_supports_wildcard(self):
        """exclude 支持通配符，且优先级高于 include。"""
        service = self._make_service({
            "mode": "all",
            "exclude": ["_stale-*"],
        })
        names = {r.name for r in service.discover_all_repos()}

        assert "_stale-experiment" not in names
        assert "loopforge" in names

    def test_exclude_archived_flag(self):
        """exclude_archived 开启后归档仓库不再计入。"""
        service = self._make_service({
            "mode": "all",
            "exclude_archived": True,
        })
        names = {r.name for r in service.discover_all_repos()}

        assert "old-thing" not in names

    def test_whitelist_mode(self):
        """whitelist 模式仅追踪显式列出的仓库。"""
        service = self._make_service({
            "mode": "whitelist",
            "include": ["loopforge", "ai-daily-hub"],
        })
        names = {r.name for r in service.discover_all_repos()}

        assert names == {"loopforge", "ai-daily-hub"}

    def test_invalid_mode_falls_back_to_all(self):
        """非法模式回退到 all，避免静默漏采。"""
        service = self._make_service({"mode": "bogus"})
        names = {r.name for r in service.discover_all_repos()}

        assert service.mode == "all"
        assert "loopforge" in names
