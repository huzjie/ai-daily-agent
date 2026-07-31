"""
Enhanced report generator for the monitoring module.

Provides trend analysis, Top N rankings, insights, and recommendations
based on metrics history. Generates Markdown-formatted reports.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List

from .models import MetricsRecord, MonitorReport, Repository, TrendInsight

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_PERIOD_DAYS = 7
DEFAULT_TOP_N = 5


class ReportGenerator:
    """
    增强版报告生成器。

    基于历史指标数据和当前仓库列表生成监控报告，包含：
    - 总体摘要
    - Top N 仓库排名
    - 趋势洞察分析
    - 建议与推荐
    - Markdown 格式化输出
    """

    def __init__(self, config: Dict):
        """
        Initialize the report generator.

        Args:
            config: Application configuration dictionary.
        """
        self.config = config
        self.report_config = config.get("monitor", {}).get("report", {})

    def generate_enhanced_report(
        self,
        history: List[MetricsRecord],
        current_repos: List[Repository],
    ) -> MonitorReport:
        """
        生成增强版监控报告。

        Args:
            history: List of historical metrics records (time-series).
            current_repos: List of current repositories from GitHub.

        Returns:
            Complete MonitorReport with all analysis sections.
        """
        if not history:
            return self._empty_report()

        latest_record = history[-1]
        period_days = self.report_config.get("period_days", DEFAULT_PERIOD_DAYS)

        # Generate each section
        summary = self._generate_summary(latest_record, current_repos)
        top_repos = self._generate_top_repos(latest_record, period_days)
        insights = self._generate_insights(history, period_days)
        recommendations = self._generate_recommendations(insights, current_repos)

        report = MonitorReport(
            generated_at=datetime.now().isoformat(),
            period_days=period_days,
            summary=summary,
            top_repos=top_repos,
            insights=insights,
            recommendations=recommendations,
            raw_data=latest_record,
        )

        return report

    def _generate_summary(
        self,
        record: MetricsRecord,
        repos: List[Repository],
    ) -> Dict:
        """生成总体摘要"""
        total_stars = sum(m.stars for m in record.repos.values())
        total_forks = sum(m.forks for m in record.repos.values())
        total_repos = len(record.repos)

        avg_stars = total_stars / total_repos if total_repos > 0 else 0
        avg_forks = total_forks / total_repos if total_repos > 0 else 0

        return {
            "total_repos": total_repos,
            "total_stars": total_stars,
            "total_forks": total_forks,
            "avg_stars_per_repo": round(avg_stars, 2),
            "avg_forks_per_repo": round(avg_forks, 2),
        }

    def _generate_top_repos(
        self,
        record: MetricsRecord,
        period_days: int,
    ) -> List[Dict]:
        """生成 Top N 仓库排名（按 stars 排序）"""
        top_n = self.report_config.get("top_n", DEFAULT_TOP_N)

        sorted_repos = sorted(
            record.repos.items(),
            key=lambda x: x[1].stars,
            reverse=True,
        )[:top_n]

        top_repos: List[Dict] = []
        for rank, (name, metrics) in enumerate(sorted_repos, start=1):
            top_repos.append({
                "name": name,
                "stars": metrics.stars,
                "forks": metrics.forks,
                "rank": rank,
            })

        return top_repos

    def _generate_insights(
        self,
        history: List[MetricsRecord],
        period_days: int,
    ) -> List[TrendInsight]:
        """生成趋势洞察"""
        insights: List[TrendInsight] = []

        if len(history) < 2:
            return insights

        # Get records within the time window
        cutoff_date = datetime.now() - timedelta(days=period_days)
        recent_records: List[MetricsRecord] = []
        for r in history:
            try:
                if datetime.fromisoformat(r.timestamp) >= cutoff_date:
                    recent_records.append(r)
            except (ValueError, TypeError):
                continue

        if len(recent_records) < 2:
            return insights

        first_record = recent_records[0]
        last_record = recent_records[-1]

        # Calculate growth for each repository
        for repo_name, new_metrics in last_record.repos.items():
            if repo_name not in first_record.repos:
                continue

            old_metrics = first_record.repos[repo_name]

            # Stars growth analysis
            stars_growth = new_metrics.stars - old_metrics.stars
            if old_metrics.stars > 0:
                stars_growth_rate = stars_growth / old_metrics.stars
            else:
                stars_growth_rate = 0.0

            if stars_growth > 0:
                trend = "up"
                analysis = (
                    f"Stars 增长 {stars_growth}，"
                    f"增长率 {stars_growth_rate:.1%}"
                )
            elif stars_growth < 0:
                trend = "down"
                analysis = f"Stars 减少 {abs(stars_growth)}"
            else:
                trend = "stable"
                analysis = "Stars 保持稳定"

            insights.append(TrendInsight(
                repo_name=repo_name,
                metric_type="stars",
                period_days=period_days,
                growth=float(stars_growth),
                growth_rate=float(stars_growth_rate),
                trend=trend,
                analysis=analysis,
            ))

        # Sort by growth rate (descending)
        insights.sort(key=lambda x: x.growth_rate, reverse=True)
        return insights

    def _generate_recommendations(
        self,
        insights: List[TrendInsight],
        repos: List[Repository],
    ) -> List[str]:
        """生成建议"""
        recommendations: List[str] = []

        # Growth-based recommendations
        top_growing = [i for i in insights if i.trend == "up"][:3]
        if top_growing:
            names = ", ".join([i.repo_name for i in top_growing])
            recommendations.append(
                f"🔥 增长最快的项目：{names}。建议加强维护和推广。"
            )

        # Stagnation-based recommendations
        stagnating = [i for i in insights if i.trend == "stable" and i.growth == 0]
        if insights and len(stagnating) > len(insights) * 0.5:
            recommendations.append(
                "⚠️ 超过 50% 的项目增长停滞。建议审查项目质量和推广策略。"
            )

        # Repo count-based recommendations
        if len(repos) < 10:
            recommendations.append(
                "💡 当前项目数量较少。建议加快发布频率，建立项目组合。"
            )

        # Default recommendation
        if not recommendations:
            recommendations.append(
                "✅ 项目整体运行良好。继续保持每日发布节奏。"
            )

        return recommendations

    def format_markdown_report(self, report: MonitorReport) -> str:
        """将报告格式化为 Markdown"""
        lines = [
            "# 📊 AI Daily Agent 监控报告",
            "",
            f"**生成时间**: {report.generated_at[:19]}",
            f"**统计周期**: 最近 {report.period_days} 天",
            "",
            "## 📈 总体概览",
            "",
            "| 指标 | 数值 |",
            "|------|------|",
            f"| 项目总数 | {report.summary.get('total_repos', 0)} |",
            f"| 总 Stars | {report.summary.get('total_stars', 0)} |",
            f"| 总 Forks | {report.summary.get('total_forks', 0)} |",
            f"| 平均 Stars/项目 | {report.summary.get('avg_stars_per_repo', 0)} |",
            f"| 平均 Forks/项目 | {report.summary.get('avg_forks_per_repo', 0)} |",
            "",
            f"## 🏆 Top {len(report.top_repos)} 项目",
            "",
        ]

        for repo in report.top_repos:
            lines.append(
                f"{repo['rank']}. **{repo['name']}** - "
                f"⭐ {repo['stars']} | 🍴 {repo['forks']}"
            )

        lines.extend([
            "",
            "## 🔍 趋势洞察",
            "",
        ])

        for insight in report.insights[:10]:
            if insight.trend == "up":
                emoji = "📈"
            elif insight.trend == "down":
                emoji = "📉"
            else:
                emoji = "➡️"
            lines.append(f"- {emoji} **{insight.repo_name}**: {insight.analysis}")

        lines.extend([
            "",
            "## 💡 建议",
            "",
        ])

        for rec in report.recommendations:
            lines.append(f"- {rec}")

        return "\n".join(lines)

    def _empty_report(self) -> MonitorReport:
        """返回空报告"""
        return MonitorReport(
            generated_at=datetime.now().isoformat(),
            period_days=0,
            summary={},
            top_repos=[],
            insights=[],
            recommendations=["暂无数据"],
            raw_data=None,
        )
