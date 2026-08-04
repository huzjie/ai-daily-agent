"""
Repository Monitor Module (Refactored).

Tracks GitHub repository metrics and generates enhanced reports.
Integrates GitHubAPIClient, RepoDiscoveryService, ReportGenerator,
RateLimiter, and DataCleaner.

Maintains backward compatibility with the legacy simple report methods
(get_growth_report, generate_summary_dashboard, get_milestone_repos).
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from .github_client import GitHubAPIClient
from .models import MetricsRecord, Repository, RepositoryMetrics
from .rate_limiter import DataCleaner, RateLimiter
from .repo_discovery import RepoDiscoveryService
from .report_generator import ReportGenerator

logger = logging.getLogger(__name__)


class RepoMonitor:
    """
    重构后的仓库监控器。

    整合所有新组件：
    - GitHubAPIClient: GitHub API 抽象层
    - RepoDiscoveryService: 自动仓库发现
    - ReportGenerator: 增强报告生成
    - RateLimiter: 速率限制感知
    - DataCleaner: 数据清理服务

    同时保留向后兼容的简单报告方法。
    """

    def __init__(self, config: Dict):
        """
        Initialize the repository monitor.

        Args:
            config: Full application configuration dictionary.
        """
        self.config = config
        self.monitor_config = config.get("monitor", {})
        self.metrics = self.monitor_config.get("metrics", [])
        self.data_dir = Path(config.get("output_dir", "data")) / "metrics"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize new components
        self.github_client: Optional[GitHubAPIClient] = None
        self.repo_discovery: Optional[RepoDiscoveryService] = None
        self.report_generator = ReportGenerator(config)
        self.rate_limiter: Optional[RateLimiter] = None
        self.data_cleaner = DataCleaner(config)

        # Try to initialize GitHub client (may fail if no auth configured)
        try:
            # 默认走 REST API：config 中已有 token，最可靠；
            # gh CLI 未认证时会走 GraphQL 报字段错误。
            # 需要优先使用 gh CLI 时，设置 monitor.prefer_gh_cli: true。
            prefer_cli = bool(self.monitor_config.get("prefer_gh_cli", False))
            self.github_client = GitHubAPIClient(config, prefer_cli=prefer_cli)
            self.repo_discovery = RepoDiscoveryService(self.github_client, config)
            self.rate_limiter = RateLimiter(self.github_client)
            logger.info(
                f"GitHub client initialized: "
                f"{self.github_client.get_client_type().value}"
            )
        except RuntimeError as e:
            logger.warning(f"GitHub client not available: {e}")

        # Load history
        self.metrics_history_file = self.data_dir / "metrics_history.json"
        self._load_history()

    def _load_history(self) -> None:
        """加载历史指标（兼容新旧格式）"""
        try:
            with open(self.metrics_history_file, "r", encoding="utf-8") as f:
                raw_history = json.load(f)

            # Convert to new data model
            self.history: List[MetricsRecord] = []
            for record in raw_history:
                repos = {}
                for name, metrics_data in record.get("repos", {}).items():
                    repos[name] = RepositoryMetrics.from_dict(metrics_data)
                self.history.append(MetricsRecord(
                    date=record.get("date", ""),
                    timestamp=record.get("timestamp", ""),
                    repos=repos,
                ))
        except (FileNotFoundError, json.JSONDecodeError):
            self.history = []

    def _save_history(self) -> None:
        """保存历史指标"""
        raw_history = [record.to_dict() for record in self.history]
        with open(self.metrics_history_file, "w", encoding="utf-8") as f:
            json.dump(raw_history, f, ensure_ascii=False, indent=2)

    def update_all_metrics(self) -> Dict:
        """
        更新所有仓库的指标。

        流程：
        1. 检查速率限制
        2. 自动发现 GitHub 上的所有仓库
        3. 获取每个仓库的最新指标
        4. 记录到历史
        5. 定期清理过期数据

        Returns:
            Dictionary with repos_discovered and repos_updated counts.
        """
        logger.info("Starting metrics update...")

        # Check if GitHub client is available
        if not self.github_client or not self.repo_discovery:
            logger.warning("GitHub client not available, skipping update")
            return {"repos_discovered": 0, "repos_updated": 0}

        # Check rate limit
        if self.rate_limiter:
            self.rate_limiter.check_and_wait()

        # Auto-discover repos
        discovered_repos = self.repo_discovery.discover_all_repos()

        # Update metrics for each repo
        updated_count = 0
        username = self.config.get("github", {}).get("username", "")
        for repo in discovered_repos:
            metrics = self.github_client.get_repo_metrics(username, repo.name)
            if metrics:
                repo.metrics = metrics
                repo.last_monitored = datetime.now().isoformat()
                updated_count += 1

        # Record metrics
        self.record_metrics_from_repos(discovered_repos)

        # Periodic data cleanup (on Mondays)
        if self._should_clean_data():
            self.data_cleaner.clean_old_metrics(str(self.metrics_history_file))

        logger.info(f"Updated metrics for {updated_count} repos")
        return {
            "repos_discovered": len(discovered_repos),
            "repos_updated": updated_count,
        }

    def record_metrics(self, repos: List[Dict]) -> None:
        """
        记录指标（兼容旧格式：接受 dict 列表）。

        This method maintains backward compatibility with the original
        interface that accepts a list of repo dictionaries.

        Args:
            repos: List of repo dicts with 'name', 'stars', 'forks', etc.
        """
        today = datetime.now().strftime("%Y-%m-%d")

        repos_dict: Dict[str, RepositoryMetrics] = {}
        for repo in repos:
            name = repo.get("name")
            if name:
                repos_dict[name] = RepositoryMetrics(
                    stars=repo.get("stars", 0),
                    forks=repo.get("forks", 0),
                    watchers=repo.get("watchers", 0),
                    issues=repo.get("issues", 0),
                )

        record = MetricsRecord(
            date=today,
            timestamp=datetime.now().isoformat(),
            repos=repos_dict,
        )

        self.history.append(record)
        self._save_history()
        logger.info(f"Recorded metrics for {len(repos)} repos on {today}")

    def record_metrics_from_repos(self, repos: List[Repository]) -> None:
        """
        记录指标（新格式：接受 Repository 对象列表）。

        Args:
            repos: List of Repository objects.
        """
        today = datetime.now().strftime("%Y-%m-%d")

        repos_dict = {repo.name: repo.metrics for repo in repos}

        record = MetricsRecord(
            date=today,
            timestamp=datetime.now().isoformat(),
            repos=repos_dict,
        )

        self.history.append(record)
        self._save_history()
        logger.info(f"Recorded metrics for {len(repos)} repos")

    def generate_report(self, period_days: int = 7) -> str:
        """
        生成增强版报告。

        Args:
            period_days: Number of days to include in the report.

        Returns:
            Markdown-formatted report string.
        """
        # Get current repos if discovery is available
        current_repos: List[Repository] = []
        if self.repo_discovery:
            current_repos = self.repo_discovery.discover_all_repos()

        # Generate enhanced report
        report = self.report_generator.generate_enhanced_report(
            self.history,
            current_repos,
        )

        return self.report_generator.format_markdown_report(report)

    def _should_clean_data(self) -> bool:
        """判断是否应该清理数据（每周一次，周一执行）"""
        today = datetime.now()
        return today.weekday() == 0

    # =========================================================================
    # Backward-compatible legacy methods
    # =========================================================================

    def get_growth_report(self, days: int = 7) -> str:
        """
        生成增长报告（向后兼容）。

        Args:
            days: Number of days to analyze.

        Returns:
            Formatted markdown report string.
        """
        if not self.history:
            return "No metrics data available yet."

        cutoff_date = datetime.now() - timedelta(days=days)
        recent_records = [
            r for r in self.history
            if self._safe_parse_timestamp(r.timestamp) >= cutoff_date
        ]

        if len(recent_records) < 2:
            return "Not enough data points for growth analysis."

        first_record = recent_records[0]
        last_record = recent_records[-1]

        report_lines = [
            f"## 📊 Growth Report - Last {days} Days",
            f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
            "",
            "### Overall Stats",
            "",
        ]

        total_stars_first = sum(m.stars for m in first_record.repos.values())
        total_stars_last = sum(m.stars for m in last_record.repos.values())
        total_forks_first = sum(m.forks for m in first_record.repos.values())
        total_forks_last = sum(m.forks for m in last_record.repos.values())

        stars_growth = total_stars_last - total_stars_first
        forks_growth = total_forks_last - total_forks_first

        report_lines.extend([
            f"- **Total Projects**: {len(last_record.repos)}",
            f"- **Total Stars**: {total_stars_last} "
            f"({'+' if stars_growth >= 0 else ''}{stars_growth})",
            f"- **Total Forks**: {total_forks_last} "
            f"({'+' if forks_growth >= 0 else ''}{forks_growth})",
            "",
            "### Top Growing Repositories",
            "",
        ])

        repo_growth = []
        for repo_name in last_record.repos:
            if repo_name in first_record.repos:
                stars_diff = (
                    last_record.repos[repo_name].stars
                    - first_record.repos[repo_name].stars
                )
                forks_diff = (
                    last_record.repos[repo_name].forks
                    - first_record.repos[repo_name].forks
                )
                repo_growth.append({
                    "name": repo_name,
                    "stars_growth": stars_diff,
                    "forks_growth": forks_diff,
                    "current_stars": last_record.repos[repo_name].stars,
                })

        repo_growth.sort(key=lambda x: x["stars_growth"], reverse=True)

        for repo in repo_growth[:5]:
            report_lines.append(
                f"- **{repo['name']}**: ⭐ {repo['current_stars']} "
                f"(+{repo['stars_growth']} stars, +{repo['forks_growth']} forks)"
            )

        report_lines.extend([
            "",
            "### Daily Metrics",
            "",
            "| Date | Projects | Total Stars | Total Forks |",
            "|------|----------|-------------|-------------|",
        ])

        for record in recent_records[-7:]:
            total_stars = sum(m.stars for m in record.repos.values())
            total_forks = sum(m.forks for m in record.repos.values())
            report_lines.append(
                f"| {record.date} | {len(record.repos)} "
                f"| {total_stars} | {total_forks} |"
            )

        return "\n".join(report_lines)

    def get_milestone_repos(
        self,
        milestones: Optional[List[int]] = None,
    ) -> List[Dict]:
        """
        查找达到 star 里程碑的仓库（向后兼容）。

        Args:
            milestones: List of milestone star counts.

        Returns:
            List of milestone repo dictionaries.
        """
        if milestones is None:
            milestones = self.monitor_config.get("star_milestones", [1, 5, 10, 50, 100])

        if not self.history:
            return []

        latest_record = self.history[-1]
        milestone_repos: List[Dict] = []

        for repo_name, metrics in latest_record.repos.items():
            stars = metrics.stars
            # 取已达成里程碑中的最大值；不能依赖 milestones 的书写顺序，
            # 否则传入 [50, 10] 时会错误地返回 10。
            reached = [m for m in milestones if stars >= m]
            reached_milestone = max(reached) if reached else None
            if reached_milestone is not None:
                milestone_repos.append({
                    "name": repo_name,
                    "stars": stars,
                    "milestone": reached_milestone,
                    "topic": "",
                    "reached_at": latest_record.timestamp,
                })

        return milestone_repos

    def generate_summary_dashboard(self) -> str:
        """生成概览仪表板（向后兼容）"""
        if not self.history:
            return "No metrics data available."

        latest = self.history[-1]
        total_repos = len(latest.repos)
        total_stars = sum(m.stars for m in latest.repos.values())
        total_forks = sum(m.forks for m in latest.repos.values())

        avg_stars = total_stars / total_repos if total_repos > 0 else 0
        avg_forks = total_forks / total_repos if total_repos > 0 else 0

        top_by_stars = sorted(
            latest.repos.items(),
            key=lambda x: x[1].stars,
            reverse=True,
        )[:5]

        dashboard = f"""# 📊 AI Daily Projects Dashboard

*Last updated: {latest.timestamp[:10]}*

## 🎯 Overview

| Metric | Value |
|--------|-------|
| **Total Projects** | {total_repos} |
| **Total Stars** | {total_stars} |
| **Total Forks** | {total_forks} |
| **Avg Stars/Repo** | {avg_stars:.1f} |
| **Avg Forks/Repo** | {avg_forks:.1f} |

## 🏆 Top Repositories

"""
        for i, (name, metrics) in enumerate(top_by_stars, 1):
            dashboard += f"{i}. **{name}** - ⭐ {metrics.stars} | 🍴 {metrics.forks}\n"

        # Growth trend
        if len(self.history) >= 2:
            prev = self.history[-2]
            prev_stars = sum(m.stars for m in prev.repos.values())
            stars_change = total_stars - prev_stars
            if stars_change > 0:
                trend_emoji = "📈"
            elif stars_change < 0:
                trend_emoji = "📉"
            else:
                trend_emoji = "➡️"
            dashboard += f"## {trend_emoji} Daily Growth\n\n"
            dashboard += (
                f"Stars change: "
                f"{'+' if stars_change >= 0 else ''}{stars_change}\n"
            )

        return dashboard

    @staticmethod
    def _safe_parse_timestamp(timestamp: str) -> datetime:
        """Safely parse an ISO 8601 timestamp, returning epoch on failure."""
        try:
            return datetime.fromisoformat(timestamp)
        except (ValueError, TypeError):
            return datetime.min
