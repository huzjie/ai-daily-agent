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

    def _make_config(self, username="testuser", prefix="ai-daily-"):
        """Helper to build a test config."""
        return {
            "github": {
                "username": username,
                "token": "test-token",
                "repo_prefix": prefix,
            }
        }

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
        mock_client.list_user_repos.assert_called_once_with(
            owner="testuser",
            prefix="ai-daily-",
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
            mock_open.return_value.__exit__ = Mock()
            mock_open.return_value.read = Mock()
            with patch("src.monitor.repo_discovery.json.load", side_effect=json.JSONDecodeError("", "", 0)):
                result = service.load_local_repos("bad.json")
                assert result == []

    def test_custom_prefix(self):
        """Test using a custom repo prefix."""
        config = self._make_config(prefix="custom-prefix-")
        mock_client = Mock(spec=GitHubAPIClient)
        mock_client.list_user_repos.return_value = []

        service = RepoDiscoveryService(mock_client, config)
        service.discover_all_repos()

        mock_client.list_user_repos.assert_called_once_with(
            owner="testuser",
            prefix="custom-prefix-",
        )
