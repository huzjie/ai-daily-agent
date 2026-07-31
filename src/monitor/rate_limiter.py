"""
Rate limiter and data cleaner for the monitoring module.

Provides:
- RateLimiter: API rate limit awareness with automatic waiting
- DataCleaner: Automatic cleanup of expired metrics and reports
"""

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .github_client import GitHubAPIClient

logger = logging.getLogger(__name__)

# Default configuration constants
DEFAULT_RETENTION_DAYS = 90
DEFAULT_RATE_LIMIT_THRESHOLD = 100
DEFAULT_BUFFER_SECONDS = 10


class RateLimiter:
    """
    API 速率限制感知器。

    监控 GitHub API 速率限制状态，在剩余请求数低于阈值时
    自动等待直到限制重置。
    """

    def __init__(
        self,
        github_client: "GitHubAPIClient",
        threshold: int = DEFAULT_RATE_LIMIT_THRESHOLD,
        buffer_seconds: int = DEFAULT_BUFFER_SECONDS,
    ):
        """
        Initialize the rate limiter.

        Args:
            github_client: GitHub API client instance for checking limits.
            threshold: Minimum remaining requests before waiting.
            buffer_seconds: Extra seconds to wait after reset time.
        """
        self.github_client = github_client
        self.threshold = threshold
        self.buffer_seconds = buffer_seconds

    def check_and_wait(self) -> None:
        """
        Check rate limit status and wait if necessary.

        Queries the GitHub API rate limit endpoint. If remaining requests
        fall below the threshold, blocks until the limit resets plus a
        buffer period.
        """
        try:
            status = self.github_client.get_rate_limit_status()
        except Exception as e:
            logger.warning(f"Failed to check rate limit: {e}")
            return

        if not status.get("available"):
            logger.debug("Rate limit status unavailable, skipping check")
            return

        remaining = status.get("remaining", 0)
        reset_at = status.get("reset_at", 0)

        if remaining < self.threshold and reset_at > 0:
            now_timestamp = int(datetime.now().timestamp())
            wait_seconds = reset_at - now_timestamp
            if wait_seconds > 0:
                total_wait = wait_seconds + self.buffer_seconds
                logger.warning(
                    f"Rate limit low ({remaining} remaining, "
                    f"threshold={self.threshold}). "
                    f"Waiting {total_wait}s until reset."
                )
                time.sleep(total_wait)
            else:
                logger.info("Rate limit reset time already passed, continuing")

    def get_status(self) -> Dict:
        """
        Get current rate limit status without waiting.

        Returns:
            Dictionary with rate limit information.
        """
        try:
            return self.github_client.get_rate_limit_status()
        except Exception as e:
            logger.warning(f"Failed to get rate limit status: {e}")
            return {"available": False}


class DataCleaner:
    """
    数据清理服务。

    自动清理过期的指标数据和报告文件，保持系统健康。
    清理策略基于可配置的保留天数。
    """

    def __init__(self, config: Dict):
        """
        Initialize the data cleaner.

        Args:
            config: Full application configuration dictionary.
        """
        self.config = config
        self.cleaner_config = config.get("monitor", {}).get("data_cleaner", {})
        self.retention_days: int = self.cleaner_config.get(
            "retention_days", DEFAULT_RETENTION_DAYS
        )
        self.enabled: bool = self.cleaner_config.get("enabled", True)

    def clean_old_metrics(self, metrics_file: str) -> int:
        """
        清理过期的指标数据。

        Reads the metrics history JSON file, removes records older than
        the retention period, and writes back the filtered data.

        Args:
            metrics_file: Path to the metrics_history.json file.

        Returns:
            Number of records removed. Returns 0 on failure.
        """
        if not self.enabled:
            logger.debug("Data cleaner is disabled, skipping cleanup")
            return 0

        try:
            with open(metrics_file, "r", encoding="utf-8") as f:
                history = json.load(f)

            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            original_count = len(history)

            # Filter out expired records
            filtered_history = []
            for record in history:
                try:
                    record_time = datetime.fromisoformat(record["timestamp"])
                    if record_time >= cutoff_date:
                        filtered_history.append(record)
                except (KeyError, ValueError) as e:
                    logger.warning(f"Skipping invalid record: {e}")
                    continue

            removed_count = original_count - len(filtered_history)

            # Write back cleaned data
            with open(metrics_file, "w", encoding="utf-8") as f:
                json.dump(filtered_history, f, ensure_ascii=False, indent=2)

            logger.info(
                f"Cleaned {removed_count} old metrics records "
                f"(retention={self.retention_days} days)"
            )
            return removed_count

        except FileNotFoundError:
            logger.debug(f"Metrics file not found: {metrics_file}")
            return 0
        except Exception as e:
            logger.error(f"Failed to clean metrics: {e}")
            return 0

    def clean_old_reports(self, reports_dir: str) -> int:
        """
        清理过期的报告文件。

        Scans the reports directory for files matching the pattern
        report_*.md and removes those older than the retention period.

        Args:
            reports_dir: Path to the reports directory.

        Returns:
            Number of files removed. Returns 0 on failure.
        """
        if not self.enabled:
            logger.debug("Data cleaner is disabled, skipping cleanup")
            return 0

        try:
            reports_path = Path(reports_dir)
            if not reports_path.exists():
                logger.debug(f"Reports directory not found: {reports_dir}")
                return 0

            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            removed_count = 0

            for report_file in reports_path.glob("report_*.md"):
                try:
                    file_mtime = datetime.fromtimestamp(report_file.stat().st_mtime)
                    if file_mtime < cutoff_date:
                        report_file.unlink()
                        removed_count += 1
                        logger.debug(f"Removed old report: {report_file.name}")
                except Exception as e:
                    logger.warning(f"Failed to remove {report_file}: {e}")

            logger.info(
                f"Cleaned {removed_count} old report files "
                f"(retention={self.retention_days} days)"
            )
            return removed_count

        except Exception as e:
            logger.error(f"Failed to clean reports: {e}")
            return 0
