"""
Tests for the enhanced report generator.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from src.monitor.models import MetricsRecord, MonitorReport, Repository, RepositoryMetrics
from src.monitor.report_generator import ReportGenerator


class TestReportGenerator:
    """Tests for ReportGenerator."""

    def _make_config(self, period_days=7, top_n=5):
        """Helper to build a test config."""
        return {
            "monitor": {
                "report": {
                    "period_days": period_days,
                    "top_n": top_n,
                }
            }
        }

    def _make_history(self, num_records=3):
        """Helper to create a history of metrics records."""
        history = []
        base_time = datetime.now() - timedelta(days=num_records)

        for i in range(num_records):
            record_time = base_time + timedelta(days=i)
            repos = {
                "ai-daily-project-a": RepositoryMetrics(
                    stars=10 + i * 5,
                    forks=2 + i,
                    watchers=1,
                    issues=0,
                ),
                "ai-daily-project-b": RepositoryMetrics(
                    stars=20 + i * 2,
                    forks=5 + i,
                    watchers=3,
                    issues=1,
                ),
            }
            history.append(MetricsRecord(
                date=record_time.strftime("%Y-%m-%d"),
                timestamp=record_time.isoformat(),
                repos=repos,
            ))

        return history

    def _make_repos(self):
        """Helper to create current repos list."""
        return [
            Repository(
                name="ai-daily-project-a",
                full_name="user/ai-daily-project-a",
                url="https://github.com/user/ai-daily-project-a",
                description="Project A",
            ),
            Repository(
                name="ai-daily-project-b",
                full_name="user/ai-daily-project-b",
                url="https://github.com/user/ai-daily-project-b",
                description="Project B",
            ),
        ]

    def test_generate_enhanced_report_success(self):
        """Test generating a complete enhanced report."""
        config = self._make_config()
        generator = ReportGenerator(config)

        history = self._make_history(3)
        repos = self._make_repos()

        report = generator.generate_enhanced_report(history, repos)

        assert isinstance(report, MonitorReport)
        assert report.generated_at is not None
        assert report.period_days == 7
        assert len(report.summary) > 0
        assert len(report.top_repos) > 0
        assert len(report.recommendations) > 0

    def test_generate_enhanced_report_empty_history(self):
        """Test generating report with empty history."""
        config = self._make_config()
        generator = ReportGenerator(config)

        report = generator.generate_enhanced_report([], [])

        assert isinstance(report, MonitorReport)
        assert report.summary == {}
        assert report.top_repos == []
        assert report.insights == []
        assert "暂无数据" in report.recommendations

    def test_generate_summary(self):
        """Test summary generation."""
        config = self._make_config()
        generator = ReportGenerator(config)

        record = MetricsRecord(
            date="2026-07-15",
            timestamp="2026-07-15T12:00:00",
            repos={
                "repo-a": RepositoryMetrics(stars=100, forks=20),
                "repo-b": RepositoryMetrics(stars=50, forks=10),
            },
        )
        repos = self._make_repos()

        summary = generator._generate_summary(record, repos)

        assert summary["total_repos"] == 2
        assert summary["total_stars"] == 150
        assert summary["total_forks"] == 30
        assert summary["avg_stars_per_repo"] == 75.0
        assert summary["avg_forks_per_repo"] == 15.0

    def test_generate_top_repos(self):
        """Test Top N repos ranking."""
        config = self._make_config(top_n=2)
        generator = ReportGenerator(config)

        record = MetricsRecord(
            date="2026-07-15",
            timestamp="2026-07-15T12:00:00",
            repos={
                "repo-a": RepositoryMetrics(stars=100, forks=20),
                "repo-b": RepositoryMetrics(stars=50, forks=10),
                "repo-c": RepositoryMetrics(stars=200, forks=30),
            },
        )

        top_repos = generator._generate_top_repos(record, 7)

        assert len(top_repos) == 2
        assert top_repos[0]["name"] == "repo-c"
        assert top_repos[0]["stars"] == 200
        assert top_repos[0]["rank"] == 1
        assert top_repos[1]["name"] == "repo-a"

    def test_generate_insights_with_growth(self):
        """Test trend insights with positive growth."""
        config = self._make_config(period_days=7)
        generator = ReportGenerator(config)

        history = self._make_history(3)
        insights = generator._generate_insights(history, 7)

        assert len(insights) > 0
        for insight in insights:
            assert insight.repo_name != ""
            assert insight.metric_type == "stars"
            assert insight.trend in ["up", "down", "stable"]

    def test_generate_insights_empty_history(self):
        """Test trend insights with insufficient data."""
        config = self._make_config()
        generator = ReportGenerator(config)

        insights = generator._generate_insights([], 7)
        assert insights == []

    def test_generate_insights_single_record(self):
        """Test trend insights with only one record."""
        config = self._make_config()
        generator = ReportGenerator(config)

        history = [
            MetricsRecord(
                date="2026-07-15",
                timestamp="2026-07-15T12:00:00",
                repos={"repo-a": RepositoryMetrics(stars=100)},
            )
        ]

        insights = generator._generate_insights(history, 7)
        assert insights == []

    def test_generate_recommendations_growing(self):
        """Test recommendations with growing projects."""
        config = self._make_config()
        generator = ReportGenerator(config)

        from src.monitor.models import TrendInsight
        insights = [
            TrendInsight(
                repo_name="repo-a",
                metric_type="stars",
                period_days=7,
                growth=10.0,
                growth_rate=0.5,
                trend="up",
                analysis="Stars increased",
            ),
        ]
        repos = self._make_repos()

        recommendations = generator._generate_recommendations(insights, repos)
        assert len(recommendations) > 0
        assert any("增长最快" in r for r in recommendations)

    def test_generate_recommendations_stagnating(self):
        """Test recommendations with stagnating projects."""
        config = self._make_config()
        generator = ReportGenerator(config)

        from src.monitor.models import TrendInsight
        insights = [
            TrendInsight(
                repo_name="repo-a",
                metric_type="stars",
                period_days=7,
                growth=0.0,
                growth_rate=0.0,
                trend="stable",
                analysis="No change",
            ),
            TrendInsight(
                repo_name="repo-b",
                metric_type="stars",
                period_days=7,
                growth=0.0,
                growth_rate=0.0,
                trend="stable",
                analysis="No change",
            ),
        ]
        repos = self._make_repos()

        recommendations = generator._generate_recommendations(insights, repos)
        assert len(recommendations) > 0
        assert any("停滞" in r for r in recommendations)

    def test_generate_recommendations_few_repos(self):
        """Test recommendations with few repos."""
        config = self._make_config()
        generator = ReportGenerator(config)

        insights = []
        repos = [Repository(name="repo-a", full_name="user/repo-a", url="")]

        recommendations = generator._generate_recommendations(insights, repos)
        assert len(recommendations) > 0
        assert any("项目数量较少" in r for r in recommendations)

    def test_format_markdown_report(self):
        """Test Markdown report formatting."""
        config = self._make_config()
        generator = ReportGenerator(config)

        history = self._make_history(3)
        repos = self._make_repos()
        report = generator.generate_enhanced_report(history, repos)

        markdown = generator.format_markdown_report(report)

        assert isinstance(markdown, str)
        assert "# 📊 AI Daily Agent 监控报告" in markdown
        assert "## 📈 总体概览" in markdown
        assert "## 🏆" in markdown
        assert "## 🔍 趋势洞察" in markdown
        assert "## 💡 建议" in markdown

    def test_empty_report(self):
        """Test empty report generation."""
        config = self._make_config()
        generator = ReportGenerator(config)

        report = generator._empty_report()

        assert isinstance(report, MonitorReport)
        assert report.period_days == 0
        assert report.summary == {}
        assert report.top_repos == []
        assert report.insights == []
        assert "暂无数据" in report.recommendations
