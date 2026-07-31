"""
Data models for the AI Daily Agent monitoring module.

Defines core data structures used across all monitoring components:
- RepositoryMetrics: Individual repo metric snapshot
- Repository: Full repository information
- MetricsRecord: Time-series metrics record
- TrendInsight: Trend analysis result
- MonitorReport: Complete monitoring report
- APIClientType: GitHub API client type enum
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


class APIClientType(Enum):
    """GitHub API 客户端类型"""
    GH_CLI = "gh_cli"
    REST_API = "rest_api"


@dataclass
class RepositoryMetrics:
    """仓库指标快照"""
    stars: int = 0
    forks: int = 0
    watchers: int = 0
    issues: int = 0
    commits: int = 0
    last_updated: str = ""  # ISO 8601

    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "stars": self.stars,
            "forks": self.forks,
            "watchers": self.watchers,
            "issues": self.issues,
            "commits": self.commits,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "RepositoryMetrics":
        """Create a RepositoryMetrics from a dictionary."""
        return cls(
            stars=data.get("stars", 0),
            forks=data.get("forks", 0),
            watchers=data.get("watchers", 0),
            issues=data.get("issues", 0),
            commits=data.get("commits", 0),
            last_updated=data.get("last_updated", ""),
        )


@dataclass
class Repository:
    """GitHub 仓库信息"""
    name: str = ""
    full_name: str = ""
    url: str = ""
    description: str = ""
    topic: str = ""
    tags: List[str] = field(default_factory=list)
    metrics: RepositoryMetrics = field(default_factory=RepositoryMetrics)
    published_at: str = ""  # ISO 8601
    last_monitored: str = ""  # ISO 8601

    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "full_name": self.full_name,
            "url": self.url,
            "description": self.description,
            "topic": self.topic,
            "tags": self.tags,
            "metrics": self.metrics.to_dict(),
            "published_at": self.published_at,
            "last_monitored": self.last_monitored,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Repository":
        """Create a Repository from a dictionary."""
        metrics_data = data.get("metrics", {})
        return cls(
            name=data.get("name", ""),
            full_name=data.get("full_name", ""),
            url=data.get("url", ""),
            description=data.get("description", ""),
            topic=data.get("topic", ""),
            tags=data.get("tags", []),
            metrics=RepositoryMetrics.from_dict(metrics_data),
            published_at=data.get("published_at", ""),
            last_monitored=data.get("last_monitored", ""),
        )


@dataclass
class MetricsRecord:
    """单个时间点的指标记录"""
    date: str = ""  # YYYY-MM-DD
    timestamp: str = ""  # ISO 8601
    repos: Dict[str, RepositoryMetrics] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "date": self.date,
            "timestamp": self.timestamp,
            "repos": {name: m.to_dict() for name, m in self.repos.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "MetricsRecord":
        """Create a MetricsRecord from a dictionary."""
        repos = {}
        for name, metrics_data in data.get("repos", {}).items():
            repos[name] = RepositoryMetrics.from_dict(metrics_data)
        return cls(
            date=data.get("date", ""),
            timestamp=data.get("timestamp", ""),
            repos=repos,
        )


@dataclass
class TrendInsight:
    """趋势洞察"""
    repo_name: str = ""
    metric_type: str = ""  # stars, forks, etc.
    period_days: int = 0
    growth: float = 0.0  # 绝对增长
    growth_rate: float = 0.0  # 百分比增长
    trend: str = ""  # "up", "down", "stable"
    analysis: str = ""  # 文字分析

    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "repo_name": self.repo_name,
            "metric_type": self.metric_type,
            "period_days": self.period_days,
            "growth": self.growth,
            "growth_rate": self.growth_rate,
            "trend": self.trend,
            "analysis": self.analysis,
        }


@dataclass
class MonitorReport:
    """监控报告"""
    generated_at: str = ""
    period_days: int = 0
    summary: Dict = field(default_factory=dict)
    top_repos: List[Dict] = field(default_factory=list)
    insights: List[TrendInsight] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    raw_data: Optional[MetricsRecord] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "generated_at": self.generated_at,
            "period_days": self.period_days,
            "summary": self.summary,
            "top_repos": self.top_repos,
            "insights": [i.to_dict() for i in self.insights],
            "recommendations": self.recommendations,
            "raw_data": self.raw_data.to_dict() if self.raw_data else None,
        }
