"""
AI Daily Agent - Monitoring Module

Provides GitHub repository monitoring with automatic discovery,
enhanced reporting, rate limiting, and data cleanup.
"""

from .models import (
    APIClientType,
    MetricsRecord,
    MonitorReport,
    Repository,
    RepositoryMetrics,
    TrendInsight,
)
from .github_client import GitHubAPIClient, GhCliClient, RestApiClient
from .repo_discovery import RepoDiscoveryService
from .report_generator import ReportGenerator
from .rate_limiter import DataCleaner, RateLimiter
from .repo_monitor import RepoMonitor

__all__ = [
    "APIClientType",
    "MetricsRecord",
    "MonitorReport",
    "Repository",
    "RepositoryMetrics",
    "TrendInsight",
    "GitHubAPIClient",
    "GhCliClient",
    "RestApiClient",
    "RepoDiscoveryService",
    "ReportGenerator",
    "DataCleaner",
    "RateLimiter",
    "RepoMonitor",
]
