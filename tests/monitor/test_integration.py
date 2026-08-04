"""
Integration tests for the monitoring module.

Tests the full workflow: RepoMonitor with all components working together.
Uses mocked GitHub client to avoid real API calls.
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.monitor.github_client import GitHubAPIClient
from src.monitor.models import (
    MetricsRecord,
    Repository,
    RepositoryMetrics,
)
from src.monitor.rate_limiter import DataCleaner, RateLimiter
from src.monitor.repo_discovery import RepoDiscoveryService
from src.monitor.repo_monitor import RepoMonitor


class TestRepoMonitorIntegration:
    """Integration tests for RepoMonitor."""

    def _make_config(self, tmp_dir=None):
        """Helper to build a test config."""
        if tmp_dir is None:
            tmp_dir = tempfile.mkdtemp()
        return {
            "github": {
                "username": "testuser",
                "token": "test-token",
                "repo_prefix": "ai-daily-",
            },
            "output_dir": tmp_dir,
            "monitor": {
                "report": {
                    "period_days": 7,
                    "top_n": 5,
                },
                "data_cleaner": {
                    "retention_days": 90,
                    "enabled": True,
                },
            },
        }

    def _make_sample_repos(self):
        """Helper to create sample repositories."""
        return [
            Repository(
                name="ai-daily-project-a",
                full_name="testuser/ai-daily-project-a",
                url="https://github.com/testuser/ai-daily-project-a",
                description="Project A",
                metrics=RepositoryMetrics(stars=50, forks=10, watchers=5),
                published_at="2026-07-01T00:00:00Z",
            ),
            Repository(
                name="ai-daily-project-b",
                full_name="testuser/ai-daily-project-b",
                url="https://github.com/testuser/ai-daily-project-b",
                description="Project B",
                metrics=RepositoryMetrics(stars=30, forks=5, watchers=2),
                published_at="2026-07-02T00:00:00Z",
            ),
        ]

    def test_init_without_github_auth(self):
        """Test RepoMonitor initializes gracefully without GitHub auth."""
        config = self._make_config()

        with patch("src.monitor.github_client.GhCliClient.check_auth", return_value=False):
            with patch("src.monitor.github_client.RestApiClient.check_auth", return_value=False):
                # Should not raise, just warn
                monitor = RepoMonitor(config)
                assert monitor.github_client is None
                assert monitor.repo_discovery is None

    def test_init_with_github_auth(self):
        """Test RepoMonitor initializes with GitHub auth (REST by default)."""
        config = self._make_config()

        # 默认优先 REST API（config 中已有 token），不依赖 gh CLI 登录态
        with patch("src.monitor.github_client.RestApiClient.check_auth", return_value=True):
            monitor = RepoMonitor(config)
            assert monitor.github_client is not None
            assert monitor.repo_discovery is not None
            assert monitor.report_generator is not None
            assert monitor.rate_limiter is not None
            assert monitor.data_cleaner is not None

    def test_init_prefers_gh_cli_when_configured(self):
        """monitor.prefer_gh_cli 为 true 时应优先使用 gh CLI。"""
        config = self._make_config()
        config.setdefault("monitor", {})["prefer_gh_cli"] = True

        with patch("src.monitor.github_client.GhCliClient.check_auth", return_value=True):
            monitor = RepoMonitor(config)
            assert monitor.github_client is not None
            assert monitor.github_client.get_client_type().value == "gh_cli"

    def test_record_metrics_legacy_format(self):
        """Test recording metrics with legacy dict format."""
        config = self._make_config()
        monitor = RepoMonitor.__new__(RepoMonitor)
        monitor.config = config
        monitor.monitor_config = config.get("monitor", {})
        monitor.metrics = []
        monitor.data_dir = Path(tempfile.mkdtemp())
        monitor.data_dir.mkdir(parents=True, exist_ok=True)
        monitor.metrics_history_file = monitor.data_dir / "metrics_history.json"
        monitor.history = []
        monitor.github_client = None
        monitor.repo_discovery = None
        monitor.report_generator = None
        monitor.rate_limiter = None
        monitor.data_cleaner = DataCleaner(config)

        repos = [
            {"name": "ai-daily-test-1", "stars": 10, "forks": 2, "watchers": 1, "issues": 0},
            {"name": "ai-daily-test-2", "stars": 5, "forks": 1, "watchers": 0, "issues": 0},
        ]

        monitor.record_metrics(repos)

        assert len(monitor.history) == 1
        assert "ai-daily-test-1" in monitor.history[0].repos
        assert monitor.history[0].repos["ai-daily-test-1"].stars == 10

    def test_record_metrics_from_repos(self):
        """Test recording metrics with new Repository objects."""
        config = self._make_config()
        monitor = RepoMonitor.__new__(RepoMonitor)
        monitor.config = config
        monitor.monitor_config = config.get("monitor", {})
        monitor.metrics = []
        monitor.data_dir = Path(tempfile.mkdtemp())
        monitor.data_dir.mkdir(parents=True, exist_ok=True)
        monitor.metrics_history_file = monitor.data_dir / "metrics_history.json"
        monitor.history = []
        monitor.github_client = None
        monitor.repo_discovery = None
        monitor.report_generator = None
        monitor.rate_limiter = None
        monitor.data_cleaner = DataCleaner(config)

        repos = self._make_sample_repos()
        monitor.record_metrics_from_repos(repos)

        assert len(monitor.history) == 1
        assert "ai-daily-project-a" in monitor.history[0].repos
        assert monitor.history[0].repos["ai-daily-project-a"].stars == 50

    def test_update_all_metrics_no_client(self):
        """Test update_all_metrics when GitHub client is not available."""
        config = self._make_config()
        monitor = RepoMonitor.__new__(RepoMonitor)
        monitor.config = config
        monitor.monitor_config = config.get("monitor", {})
        monitor.metrics = []
        monitor.data_dir = Path(tempfile.mkdtemp())
        monitor.data_dir.mkdir(parents=True, exist_ok=True)
        monitor.metrics_history_file = monitor.data_dir / "metrics_history.json"
        monitor.history = []
        monitor.github_client = None
        monitor.repo_discovery = None
        monitor.report_generator = None
        monitor.rate_limiter = None
        monitor.data_cleaner = DataCleaner(config)

        result = monitor.update_all_metrics()
        assert result["repos_discovered"] == 0
        assert result["repos_updated"] == 0

    def test_update_all_metrics_with_client(self):
        """Test update_all_metrics with mocked GitHub client."""
        config = self._make_config()
        monitor = RepoMonitor.__new__(RepoMonitor)
        monitor.config = config
        monitor.monitor_config = config.get("monitor", {})
        monitor.metrics = []
        monitor.data_dir = Path(tempfile.mkdtemp())
        monitor.data_dir.mkdir(parents=True, exist_ok=True)
        monitor.metrics_history_file = monitor.data_dir / "metrics_history.json"
        monitor.history = []
        monitor.github_client = None
        monitor.report_generator = None
        monitor.data_cleaner = DataCleaner(config)

        # Mock the components
        mock_client = Mock(spec=GitHubAPIClient)
        mock_client.get_repo_metrics.return_value = RepositoryMetrics(
            stars=100, forks=20, watchers=5
        )
        mock_client.get_rate_limit_status.return_value = {"available": False}

        mock_discovery = Mock(spec=RepoDiscoveryService)
        mock_discovery.discover_all_repos.return_value = self._make_sample_repos()

        mock_limiter = Mock(spec=RateLimiter)

        monitor.github_client = mock_client
        monitor.repo_discovery = mock_discovery
        monitor.rate_limiter = mock_limiter

        result = monitor.update_all_metrics()

        assert result["repos_discovered"] == 2
        assert result["repos_updated"] == 2
        mock_limiter.check_and_wait.assert_called_once()
        mock_discovery.discover_all_repos.assert_called_once()

    def test_generate_report_no_history(self):
        """Test report generation with no history."""
        config = self._make_config()
        monitor = RepoMonitor.__new__(RepoMonitor)
        monitor.config = config
        monitor.monitor_config = config.get("monitor", {})
        monitor.history = []
        monitor.github_client = None
        monitor.repo_discovery = None
        monitor.data_cleaner = DataCleaner(config)

        from src.monitor.report_generator import ReportGenerator
        monitor.report_generator = ReportGenerator(config)

        report = monitor.generate_report()
        assert "暂无数据" in report

    def test_generate_report_with_history(self):
        """Test report generation with history data."""
        config = self._make_config()
        monitor = RepoMonitor.__new__(RepoMonitor)
        monitor.config = config
        monitor.monitor_config = config.get("monitor", {})
        monitor.data_dir = Path(tempfile.mkdtemp())
        monitor.data_dir.mkdir(parents=True, exist_ok=True)
        monitor.metrics_history_file = monitor.data_dir / "metrics_history.json"

        # Add some history
        now = datetime.now()
        monitor.history = [
            MetricsRecord(
                date=(now - timedelta(days=2)).strftime("%Y-%m-%d"),
                timestamp=(now - timedelta(days=2)).isoformat(),
                repos={
                    "ai-daily-project-a": RepositoryMetrics(stars=40, forks=8),
                    "ai-daily-project-b": RepositoryMetrics(stars=25, forks=4),
                },
            ),
            MetricsRecord(
                date=now.strftime("%Y-%m-%d"),
                timestamp=now.isoformat(),
                repos={
                    "ai-daily-project-a": RepositoryMetrics(stars=50, forks=10),
                    "ai-daily-project-b": RepositoryMetrics(stars=30, forks=5),
                },
            ),
        ]

        monitor.github_client = None
        monitor.repo_discovery = None
        monitor.data_cleaner = DataCleaner(config)

        from src.monitor.report_generator import ReportGenerator
        monitor.report_generator = ReportGenerator(config)

        report = monitor.generate_report()
        assert "AI Daily Agent 监控报告" in report
        assert "ai-daily-project-a" in report

    def test_history_persistence(self):
        """Test that history is saved and loaded correctly."""
        tmp_dir = tempfile.mkdtemp()
        config = self._make_config(tmp_dir)
        metrics_dir = Path(tmp_dir) / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)

        # Create monitor and record metrics
        with patch("src.monitor.github_client.GhCliClient.check_auth", return_value=False):
            with patch("src.monitor.github_client.RestApiClient.check_auth", return_value=False):
                monitor = RepoMonitor(config)

        repos = [
            {"name": "ai-daily-test", "stars": 42, "forks": 5, "watchers": 1, "issues": 0},
        ]
        monitor.record_metrics(repos)

        # Verify file was written
        assert monitor.metrics_history_file.exists()

        # Create new monitor and verify history is loaded
        with patch("src.monitor.github_client.GhCliClient.check_auth", return_value=False):
            with patch("src.monitor.github_client.RestApiClient.check_auth", return_value=False):
                monitor2 = RepoMonitor(config)

        assert len(monitor2.history) == 1
        assert "ai-daily-test" in monitor2.history[0].repos
        assert monitor2.history[0].repos["ai-daily-test"].stars == 42

    def test_backward_compat_get_growth_report(self):
        """Test backward-compatible get_growth_report method."""
        config = self._make_config()
        monitor = RepoMonitor.__new__(RepoMonitor)
        monitor.config = config
        monitor.monitor_config = config.get("monitor", {})

        now = datetime.now()
        monitor.history = [
            MetricsRecord(
                date=(now - timedelta(days=2)).strftime("%Y-%m-%d"),
                timestamp=(now - timedelta(days=2)).isoformat(),
                repos={
                    "repo-a": RepositoryMetrics(stars=10, forks=2),
                    "repo-b": RepositoryMetrics(stars=20, forks=5),
                },
            ),
            MetricsRecord(
                date=now.strftime("%Y-%m-%d"),
                timestamp=now.isoformat(),
                repos={
                    "repo-a": RepositoryMetrics(stars=15, forks=3),
                    "repo-b": RepositoryMetrics(stars=22, forks=6),
                },
            ),
        ]

        report = monitor.get_growth_report(7)
        assert "Growth Report" in report
        assert "repo-a" in report

    def test_backward_compat_generate_summary_dashboard(self):
        """Test backward-compatible generate_summary_dashboard method."""
        config = self._make_config()
        monitor = RepoMonitor.__new__(RepoMonitor)
        monitor.config = config
        monitor.monitor_config = config.get("monitor", {})

        now = datetime.now()
        monitor.history = [
            MetricsRecord(
                date=now.strftime("%Y-%m-%d"),
                timestamp=now.isoformat(),
                repos={
                    "repo-a": RepositoryMetrics(stars=100, forks=20),
                    "repo-b": RepositoryMetrics(stars=50, forks=10),
                },
            ),
        ]

        dashboard = monitor.generate_summary_dashboard()
        assert "AI Daily Projects Dashboard" in dashboard
        assert "repo-a" in dashboard

    def test_backward_compat_get_milestone_repos(self):
        """Test backward-compatible get_milestone_repos method."""
        config = self._make_config()
        monitor = RepoMonitor.__new__(RepoMonitor)
        monitor.config = config
        monitor.monitor_config = config.get("monitor", {})

        now = datetime.now()
        monitor.history = [
            MetricsRecord(
                date=now.strftime("%Y-%m-%d"),
                timestamp=now.isoformat(),
                repos={
                    "repo-a": RepositoryMetrics(stars=50, forks=10),
                    "repo-b": RepositoryMetrics(stars=5, forks=1),
                },
            ),
        ]

        milestones = monitor.get_milestone_repos([50, 10])
        assert len(milestones) == 1
        assert milestones[0]["name"] == "repo-a"
        assert milestones[0]["milestone"] == 50


class TestDataCleanerIntegration:
    """Integration tests for DataCleaner."""

    def test_clean_old_metrics(self):
        """Test cleaning old metrics data."""
        tmp_dir = tempfile.mkdtemp()
        metrics_file = os.path.join(tmp_dir, "metrics_history.json")

        now = datetime.now()
        old_record = {
            "date": (now - timedelta(days=100)).strftime("%Y-%m-%d"),
            "timestamp": (now - timedelta(days=100)).isoformat(),
            "repos": {},
        }
        new_record = {
            "date": now.strftime("%Y-%m-%d"),
            "timestamp": now.isoformat(),
            "repos": {},
        }

        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump([old_record, new_record], f)

        config = {
            "monitor": {
                "data_cleaner": {
                    "retention_days": 90,
                    "enabled": True,
                }
            }
        }

        cleaner = DataCleaner(config)
        removed = cleaner.clean_old_metrics(metrics_file)

        assert removed == 1

        with open(metrics_file, "r", encoding="utf-8") as f:
            remaining = json.load(f)
        assert len(remaining) == 1

    def test_clean_old_metrics_disabled(self):
        """Test that cleaning is skipped when disabled."""
        config = {
            "monitor": {
                "data_cleaner": {
                    "retention_days": 90,
                    "enabled": False,
                }
            }
        }

        cleaner = DataCleaner(config)
        removed = cleaner.clean_old_metrics("nonexistent.json")
        assert removed == 0

    def test_clean_old_reports(self):
        """Test cleaning old report files."""
        tmp_dir = tempfile.mkdtemp()

        # Create old and new report files
        old_report = Path(tmp_dir) / "report_20200101.md"
        old_report.write_text("Old report", encoding="utf-8")

        new_report = Path(tmp_dir) / "report_20260725.md"
        new_report.write_text("New report", encoding="utf-8")

        config = {
            "monitor": {
                "data_cleaner": {
                    "retention_days": 90,
                    "enabled": True,
                }
            }
        }

        cleaner = DataCleaner(config)

        # Set old file mtime to far past
        import os
        old_time = (datetime.now() - timedelta(days=200)).timestamp()
        os.utime(str(old_report), (old_time, old_time))

        removed = cleaner.clean_old_reports(tmp_dir)
        assert removed == 1
        assert not old_report.exists()
        assert new_report.exists()
