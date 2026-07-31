"""
AI Daily Agent - Main Orchestrator
Coordinates the full pipeline: discover → generate → publish → monitor
"""

import json
import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List

import yaml

from src.discoverer.hot_topic_discoverer import HotTopicDiscoverer
from src.generator.project_generator import ProjectGenerator
from src.publisher.github_publisher import GitHubPublisher
from src.monitor import RepoMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('data/logs/agent.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("ai_daily_agent")


class AIDailyAgent:
    """
    Main orchestrator for the AI Daily Agent.
    
    Pipeline:
    1. Discover hot AI topics
    2. Generate a complete project solution
    3. Publish to GitHub as a public repo
    4. Monitor and report on metrics
    """

    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.discoverer = HotTopicDiscoverer(self.config)
        self.generator = ProjectGenerator(self.config)
        self.publisher = GitHubPublisher(self.config)
        self.monitor = RepoMonitor(self.config)

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def run_daily_pipeline(self, custom_topic: Optional[str] = None) -> Dict:
        """
        Run the full daily pipeline.
        
        Args:
            custom_topic: If provided, use this topic instead of auto-discovered ones
            
        Returns:
            Summary of what was done
        """
        logger.info("=" * 60)
        logger.info(f"🚀 AI Daily Agent - Starting pipeline at {datetime.now()}")
        logger.info("=" * 60)

        result = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'status': 'success',
            'steps': {}
        }

        try:
            # Step 1: Discover topics
            logger.info("\n📡 Step 1: Discovering hot AI topics...")
            if custom_topic:
                topic = self._build_custom_topic(custom_topic)
                topics = [topic]
                logger.info(f"Using custom topic: {custom_topic}")
            else:
                topics = self.discoverer.discover()
                logger.info(f"Discovered {len(topics)} topics")

            if not topics:
                logger.warning("No topics discovered. Aborting pipeline.")
                result['status'] = 'failed'
                result['error'] = 'No topics discovered'
                return result

            result['steps']['discover'] = {
                'topics_found': len(topics),
                'top_topic': topics[0].title
            }

            # Step 2: Generate project for the top topic
            logger.info(f"\n🛠️ Step 2: Generating project for: {topics[0].title}")
            topic_dict = {
                'title': topics[0].title,
                'description': topics[0].description,
                'source': topics[0].source,
                'url': topics[0].url,
                'keywords': topics[0].keywords,
                'tags': topics[0].tags,
                'slug': self._slugify(topics[0].title),
                'trend_score': topics[0].trend_score
            }
            project_dir = self.generator.generate_project(topic_dict)
            logger.info(f"Project generated at: {project_dir}")

            result['steps']['generate'] = {
                'project_dir': project_dir,
                'topic': topics[0].title
            }

            # Step 3: Publish to GitHub
            logger.info("\n📦 Step 3: Publishing to GitHub...")
            if self.publisher.check_auth():
                repo_url = self.publisher.create_repo(project_dir, topic_dict)
                if repo_url:
                    logger.info(f"✅ Published: {repo_url}")
                    result['steps']['publish'] = {
                        'repo_url': repo_url,
                        'status': 'success'
                    }
                    
                    # Update hub repo
                    hub_dir = self._get_hub_dir()
                    if hub_dir and Path(hub_dir).exists():
                        self.publisher.update_hub_repo(hub_dir)
                        logger.info("Hub repo updated")
                else:
                    logger.error("Failed to publish to GitHub")
                    result['steps']['publish'] = {'status': 'failed'}
            else:
                logger.warning("GitHub auth not configured. Skipping publish step.")
                result['steps']['publish'] = {'status': 'skipped', 'reason': 'no auth'}

            # Step 4: Monitor metrics
            logger.info("\n📊 Step 4: Updating metrics...")
            updated_metrics = self.publisher.update_metrics()
            self.monitor.record_metrics(list(self.publisher.published))
            logger.info("Metrics updated")

            result['steps']['monitor'] = {
                'repos_tracked': len(updated_metrics)
            }

            # Summary
            logger.info("\n" + "=" * 60)
            logger.info("✅ Pipeline completed successfully!")
            logger.info("=" * 60)
            logger.info(f"\n📋 Summary:")
            logger.info(f"   Topic: {topics[0].title}")
            logger.info(f"   Project: {Path(project_dir).name}")
            if 'publish' in result['steps'] and result['steps']['publish'].get('status') == 'success':
                logger.info(f"   URL: {result['steps']['publish']['repo_url']}")
            logger.info("")

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            result['status'] = 'failed'
            result['error'] = str(e)

        return result

    def run_monitor_only(self) -> Dict:
        """
        Run only the monitoring step - update metrics and generate report.
        
        Uses the new enhanced monitoring pipeline:
        1. Auto-discover repos from GitHub
        2. Update all metrics
        3. Generate enhanced report with trends and insights
        """
        logger.info("📊 Running monitor-only pipeline...")

        # Try new enhanced monitoring first
        update_result = self.monitor.update_all_metrics()

        # Generate enhanced report
        enhanced_report = self.monitor.generate_report(period_days=7)

        # Also generate legacy reports for backward compatibility
        legacy_dashboard = self.monitor.generate_summary_dashboard()
        legacy_growth = self.monitor.get_growth_report(7)

        # Save report
        report_file = self.config.get('output_dir', 'data') + f"/reports/report_{datetime.now().strftime('%Y%m%d')}.md"
        Path(report_file).parent.mkdir(parents=True, exist_ok=True)
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(enhanced_report)
            f.write("\n\n---\n\n")
            f.write(legacy_dashboard)
            f.write("\n\n")
            f.write(legacy_growth)

        logger.info(f"Report saved to: {report_file}")
        return {
            'status': 'success',
            'repos_discovered': update_result.get('repos_discovered', 0),
            'repos_updated': update_result.get('repos_updated', 0),
            'report_file': report_file,
        }

    def _build_custom_topic(self, custom_topic: str) -> 'HotTopic':
        """Build a topic object from a custom user-provided topic string"""
        from src.discoverer.hot_topic_discoverer import HotTopic
        return HotTopic(
            title=custom_topic,
            description=f"Custom topic: {custom_topic}",
            source="custom",
            url="",
            keywords=custom_topic.split(),
            trend_score=10.0,
            timestamp=datetime.now().isoformat(),
            tags=["Custom", "User-Defined"]
        )

    def _slugify(self, text: str) -> str:
        """Convert text to slug"""
        import re
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s-]', '', text)
        text = re.sub(r'\s+', '-', text)
        text = re.sub(r'-+', '-', text)
        return text.strip('-')[:50]

    def _get_hub_dir(self) -> Optional[str]:
        """Get the hub directory path"""
        hub_dir = Path(self.config.get('output_dir', 'data')) / "hub"
        return str(hub_dir) if hub_dir.exists() else None


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="AI Daily Agent - Generate daily AI projects")
    parser.add_argument('--config', default='config.yaml', help='Config file path')
    parser.add_argument('--topic', type=str, help='Custom topic (skip auto-discovery)')
    parser.add_argument('--monitor-only', action='store_true', help='Only run metrics monitoring')
    parser.add_argument('--report', action='store_true', help='Generate metrics report')

    args = parser.parse_args()

    # Ensure data directories exist
    Path('data/logs').mkdir(parents=True, exist_ok=True)
    Path('data/projects').mkdir(parents=True, exist_ok=True)
    Path('data/metrics').mkdir(parents=True, exist_ok=True)
    Path('data/reports').mkdir(parents=True, exist_ok=True)

    agent = AIDailyAgent(config_path=args.config)

    if args.monitor_only or args.report:
        result = agent.run_monitor_only()
    else:
        result = agent.run_daily_pipeline(custom_topic=args.topic)

    # Output result as JSON
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
