"""
Tests for the GitHub API client abstraction layer.
"""

import json
import subprocess
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.monitor.github_client import (
    GhCliClient,
    GitHubAPIClient,
    GitHubClientBase,
    RestApiClient,
)
from src.monitor.models import APIClientType, Repository, RepositoryMetrics


class TestGhCliClient:
    """Tests for GhCliClient implementation."""

    def test_check_auth_success(self):
        """Test successful gh CLI authentication check."""
        config = {"github": {"username": "testuser"}}
        client = GhCliClient(config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            assert client.check_auth() is True
            mock_run.assert_called_once_with(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=10,
            )

    def test_check_auth_failure(self):
        """Test failed gh CLI authentication check."""
        config = {"github": {"username": "testuser"}}
        client = GhCliClient(config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1)
            assert client.check_auth() is False

    def test_check_auth_not_installed(self):
        """Test gh CLI not installed."""
        config = {"github": {"username": "testuser"}}
        client = GhCliClient(config)

        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert client.check_auth() is False

    def test_get_repo_metrics_success(self):
        """Test successful metrics retrieval via gh CLI."""
        config = {"github": {"username": "testuser"}}
        client = GhCliClient(config)

        mock_data = json.dumps({
            "stargazerCount": 42,
            "forkCount": 10,
            "watchers": {"totalCount": 5},
            "issues": {"totalCount": 3},
        })

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=mock_data)
            metrics = client.get_repo_metrics("testuser", "ai-daily-test")

            assert metrics is not None
            assert metrics.stars == 42
            assert metrics.forks == 10
            assert metrics.watchers == 5
            assert metrics.issues == 3

    def test_get_repo_metrics_failure(self):
        """Test metrics retrieval failure."""
        config = {"github": {"username": "testuser"}}
        client = GhCliClient(config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="not found")
            metrics = client.get_repo_metrics("testuser", "nonexistent")
            assert metrics is None

    def test_get_repo_metrics_timeout(self):
        """Test metrics retrieval timeout."""
        config = {"github": {"username": "testuser"}}
        client = GhCliClient(config)

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("gh", 30)):
            metrics = client.get_repo_metrics("testuser", "ai-daily-test")
            assert metrics is None

    def test_get_rate_limit_status(self):
        """Test that gh CLI rate limit returns unavailable."""
        config = {"github": {"username": "testuser"}}
        client = GhCliClient(config)
        assert client.get_rate_limit_status() == {"available": False}

    def test_list_user_repos(self):
        """Test listing user repos via gh CLI."""
        config = {"github": {"username": "testuser"}}
        client = GhCliClient(config)

        mock_data = json.dumps([
            {
                "name": "ai-daily-test-1",
                "fullName": "testuser/ai-daily-test-1",
                "url": "https://github.com/testuser/ai-daily-test-1",
                "description": "Test repo 1",
                "createdAt": "2026-07-01T00:00:00Z",
                "stargazerCount": 10,
                "forkCount": 2,
                "subscribersCount": 1,
            },
            {
                "name": "other-repo",
                "fullName": "testuser/other-repo",
                "url": "https://github.com/testuser/other-repo",
                "description": "Not ai-daily",
                "createdAt": "2026-07-01T00:00:00Z",
                "stargazerCount": 5,
                "forkCount": 1,
                "subscribersCount": 0,
            },
        ])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=mock_data)
            repos = client.list_user_repos("testuser")

            assert len(repos) == 1
            assert repos[0].name == "ai-daily-test-1"


class TestRestApiClient:
    """Tests for RestApiClient implementation."""

    def test_check_auth_success(self):
        """Test successful REST API authentication."""
        config = {"github": {"username": "testuser", "token": "test-token"}}
        client = RestApiClient(config)

        with patch.object(client.session, "get") as mock_get:
            mock_get.return_value = Mock(status_code=200)
            assert client.check_auth() is True

    def test_check_auth_failure(self):
        """Test failed REST API authentication."""
        config = {"github": {"username": "testuser", "token": "bad-token"}}
        client = RestApiClient(config)

        with patch.object(client.session, "get") as mock_get:
            mock_get.return_value = Mock(status_code=401)
            assert client.check_auth() is False

    def test_get_repo_metrics_success(self):
        """Test successful metrics retrieval via REST API."""
        config = {"github": {"username": "testuser", "token": "test-token"}}
        client = RestApiClient(config)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "stargazers_count": 42,
            "forks_count": 10,
            "subscribers_count": 5,
            "open_issues_count": 3,
            "updated_at": "2026-07-15T00:00:00Z",
        }

        with patch.object(client.session, "get", return_value=mock_response):
            metrics = client.get_repo_metrics("testuser", "ai-daily-test")
            assert metrics is not None
            assert metrics.stars == 42
            assert metrics.forks == 10
            assert metrics.watchers == 5
            assert metrics.issues == 3

    def test_get_repo_metrics_timeout(self):
        """Test REST API timeout."""
        import requests

        config = {"github": {"username": "testuser", "token": "test-token"}}
        client = RestApiClient(config)

        with patch.object(
            client.session, "get", side_effect=requests.exceptions.Timeout
        ):
            metrics = client.get_repo_metrics("testuser", "ai-daily-test")
            assert metrics is None

    def test_list_user_repos_with_filter(self):
        """Test listing repos with prefix filter."""
        config = {"github": {"username": "testuser", "token": "test-token"}}
        client = RestApiClient(config)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "name": "ai-daily-test-1",
                "full_name": "testuser/ai-daily-test-1",
                "html_url": "https://github.com/testuser/ai-daily-test-1",
                "description": "Test 1",
                "stargazers_count": 10,
                "forks_count": 2,
                "subscribers_count": 1,
                "open_issues_count": 0,
                "updated_at": "2026-07-15T00:00:00Z",
                "created_at": "2026-07-01T00:00:00Z",
            },
            {
                "name": "ai-daily-test-2",
                "full_name": "testuser/ai-daily-test-2",
                "html_url": "https://github.com/testuser/ai-daily-test-2",
                "description": "Test 2",
                "stargazers_count": 5,
                "forks_count": 1,
                "subscribers_count": 0,
                "open_issues_count": 0,
                "updated_at": "2026-07-15T00:00:00Z",
                "created_at": "2026-07-02T00:00:00Z",
            },
            {
                "name": "other-project",
                "full_name": "testuser/other-project",
                "html_url": "https://github.com/testuser/other-project",
                "description": "Other",
                "stargazers_count": 100,
                "forks_count": 50,
                "subscribers_count": 10,
                "open_issues_count": 5,
                "updated_at": "2026-07-15T00:00:00Z",
                "created_at": "2026-06-01T00:00:00Z",
            },
        ]

        with patch.object(client.session, "get", return_value=mock_response):
            repos = client.list_user_repos("testuser")
            # Should only include ai-daily-* repos
            assert len(repos) == 2
            assert all(r.name.startswith("ai-daily-") for r in repos)

    def test_get_rate_limit_status_success(self):
        """Test successful rate limit status retrieval."""
        config = {"github": {"username": "testuser", "token": "test-token"}}
        client = RestApiClient(config)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resources": {
                "core": {
                    "limit": 5000,
                    "remaining": 4999,
                    "reset": 1689400000,
                }
            }
        }

        with patch.object(client.session, "get", return_value=mock_response):
            status = client.get_rate_limit_status()
            assert status["available"] is True
            assert status["limit"] == 5000
            assert status["remaining"] == 4999


class TestGitHubAPIClient:
    """Tests for GitHubAPIClient context class."""

    def test_init_prefers_cli(self):
        """Test that prefer_cli=True tries gh CLI first."""
        config = {"github": {"username": "testuser", "token": "test-token"}}

        with patch.object(GhCliClient, "check_auth", return_value=True):
            client = GitHubAPIClient(config, prefer_cli=True)
            assert client.get_client_type() == APIClientType.GH_CLI

    def test_init_fallback_to_rest(self):
        """Test fallback to REST API when gh CLI fails."""
        config = {"github": {"username": "testuser", "token": "test-token"}}

        with patch.object(GhCliClient, "check_auth", return_value=False):
            with patch.object(RestApiClient, "check_auth", return_value=True):
                client = GitHubAPIClient(config, prefer_cli=True)
                assert client.get_client_type() == APIClientType.REST_API

    def test_init_rest_only(self):
        """Test initialization with prefer_cli=False."""
        config = {"github": {"username": "testuser", "token": "test-token"}}

        with patch.object(RestApiClient, "check_auth", return_value=True):
            client = GitHubAPIClient(config, prefer_cli=False)
            assert client.get_client_type() == APIClientType.REST_API

    def test_init_all_fail(self):
        """Test RuntimeError when all clients fail."""
        config = {"github": {"username": "testuser", "token": "bad-token"}}

        with patch.object(GhCliClient, "check_auth", return_value=False):
            with patch.object(RestApiClient, "check_auth", return_value=False):
                with pytest.raises(RuntimeError):
                    GitHubAPIClient(config, prefer_cli=True)

    def test_get_repo_metrics_delegates(self):
        """Test that get_repo_metrics delegates to active client."""
        config = {"github": {"username": "testuser", "token": "test-token"}}
        expected_metrics = RepositoryMetrics(stars=10, forks=2)

        with patch.object(RestApiClient, "check_auth", return_value=True):
            with patch.object(
                RestApiClient, "get_repo_metrics", return_value=expected_metrics
            ):
                client = GitHubAPIClient(config, prefer_cli=False)
                result = client.get_repo_metrics("testuser", "ai-daily-test")
                assert result == expected_metrics

    def test_get_repo_metrics_error_handling(self):
        """Test error handling in get_repo_metrics."""
        config = {"github": {"username": "testuser", "token": "test-token"}}

        with patch.object(RestApiClient, "check_auth", return_value=True):
            with patch.object(
                RestApiClient, "get_repo_metrics", side_effect=Exception("API error")
            ):
                client = GitHubAPIClient(config, prefer_cli=False)
                result = client.get_repo_metrics("testuser", "ai-daily-test")
                assert result is None

    def test_list_user_repos_error_handling(self):
        """Test error handling in list_user_repos."""
        config = {"github": {"username": "testuser", "token": "test-token"}}

        with patch.object(RestApiClient, "check_auth", return_value=True):
            with patch.object(
                RestApiClient,
                "list_user_repos",
                side_effect=Exception("API error"),
            ):
                client = GitHubAPIClient(config, prefer_cli=False)
                result = client.list_user_repos("testuser")
                assert result == []
