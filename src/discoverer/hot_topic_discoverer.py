"""
AI Hot Topic Discoverer
Discover trending AI topics from multiple sources
"""

import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class HotTopic:
    """Represents a trending AI topic"""
    title: str
    description: str
    source: str
    url: str
    keywords: List[str]
    trend_score: float
    timestamp: str
    tags: List[str]


class HotTopicDiscoverer:
    """
    Discover hot AI topics from multiple sources:
    - Web search (via SerpAPI or similar)
    - GitHub trending
    - Hugging Face trending models
    - AI news sites
    """

    def __init__(self, config: Dict):
        self.config = config
        self.sources = config.get('sources', [])
        self.topics_history_file = "data/topics_history.json"
        self._load_history()

    def _load_history(self):
        """Load previous topics to avoid duplicates"""
        try:
            with open(self.topics_history_file, 'r', encoding='utf-8') as f:
                self.history = json.load(f)
        except FileNotFoundError:
            self.history = []

    def _save_history(self):
        """Save topics history"""
        with open(self.topics_history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def discover(self) -> List[HotTopic]:
        """
        Discover hot topics from all enabled sources
        Returns list of HotTopic objects sorted by trend_score
        """
        all_topics = []

        for source in self.sources:
            if not source.get('enabled', False):
                continue

            source_name = source.get('name')
            try:
                if source_name == 'web_search':
                    topics = self._discover_from_web_search(source)
                elif source_name == 'github_trending':
                    topics = self._discover_from_github_trending(source)
                elif source_name == 'huggingface':
                    topics = self._discover_from_huggingface(source)
                else:
                    logger.warning(f"Unknown source: {source_name}")
                    continue

                all_topics.extend(topics)
                logger.info(f"Discovered {len(topics)} topics from {source_name}")
            except Exception as e:
                logger.error(f"Error discovering from {source_name}: {e}")

        # Remove duplicates based on history
        unique_topics = self._remove_duplicates(all_topics)

        # Sort by trend score
        unique_topics.sort(key=lambda x: x.trend_score, reverse=True)

        # Update history
        self.history.extend([asdict(topic) for topic in unique_topics])
        self._save_history()

        return unique_topics

    def _discover_from_web_search(self, source: Dict) -> List[HotTopic]:
        """
        Discover topics from web search
        Note: This is a placeholder. In production, use SerpAPI, Google Custom Search, or similar.
        For demo purposes, we'll use a mock implementation.
        """
        topics = []
        keywords = source.get('keywords', [])
        max_topics = source.get('max_topics', 5)

        # In production, you would:
        # 1. Call SerpAPI or Google Custom Search API
        # 2. Parse results
        # 3. Extract trending AI news

        # Mock implementation for demonstration
        mock_topics = [
            HotTopic(
                title="AI Agent Framework Revolution: AutoGPT 2.0 Released",
                description="The latest version of AutoGPT brings revolutionary multi-agent collaboration capabilities, enabling AI agents to work together on complex tasks.",
                source="web_search",
                url="https://example.com/autogpt-2",
                keywords=["AI Agent", "AutoGPT", "Multi-Agent"],
                trend_score=9.5,
                timestamp=datetime.now().isoformat(),
                tags=["AI Agent", "Automation", "Open Source"]
            ),
            HotTopic(
                title="OpenAI GPT-5 Announcement: What We Know",
                description="OpenAI has hinted at GPT-5 with unprecedented reasoning capabilities and multimodal understanding.",
                source="web_search",
                url="https://example.com/gpt5",
                keywords=["GPT-5", "OpenAI", "LLM"],
                trend_score=9.8,
                timestamp=datetime.now().isoformat(),
                tags=["LLM", "OpenAI", "Breakthrough"]
            ),
            HotTopic(
                title="Stable Diffusion 3.0: Open Source Image Generation",
                description="Stability AI releases SD 3.0 with improved quality and commercial licensing for the open source community.",
                source="web_search",
                url="https://example.com/sd3",
                keywords=["Stable Diffusion", "Image Generation", "Open Source"],
                trend_score=8.7,
                timestamp=datetime.now().isoformat(),
                tags=["Computer Vision", "Generative AI", "Open Source"]
            ),
            HotTopic(
                title="LangChain 1.0: Production-Ready LLM Applications",
                description="LangChain reaches 1.0 milestone with enterprise features, better observability, and improved performance.",
                source="web_search",
                url="https://example.com/langchain-1",
                keywords=["LangChain", "LLM Application", "Framework"],
                trend_score=8.3,
                timestamp=datetime.now().isoformat(),
                tags=["LLM", "Framework", "Production"]
            ),
        ]

        topics.extend(mock_topics[:max_topics])
        return topics

    def _discover_from_github_trending(self, source: Dict) -> List[HotTopic]:
        """
        Discover trending AI repositories on GitHub
        """
        topics = []
        languages = source.get('languages', ['python'])
        since = source.get('since', 'daily')

        try:
            # Fetch GitHub trending page
            url = f"https://github.com/trending/{','.join(languages)}?since={since}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            repo_articles = soup.find_all('article', class_='Box-row')

            for article in repo_articles[:10]:
                try:
                    # Extract repo info
                    h2 = article.find('h2')
                    if not h2:
                        continue

                    repo_link = h2.find('a')
                    if not repo_link:
                        continue

                    repo_path = repo_link.get('href', '').strip('/')
                    if not repo_path:
                        continue

                    # Extract description
                    desc_p = article.find('p', class_='col-9')
                    description = desc_p.get_text().strip() if desc_p else ""

                    # Extract stars
                    stars_span = article.find('span', class_='d-inline-block float-sm-right')
                    stars_text = stars_span.get_text().strip() if stars_span else "0"
                    stars = int(''.join(filter(str.isdigit, stars_text)) or 0)

                    # Check if AI-related
                    ai_keywords = ['ai', 'machine learning', 'deep learning', 'llm', 'gpt', 'neural', 'transformer']
                    repo_lower = (repo_path + ' ' + description).lower()

                    if any(keyword in repo_lower for keyword in ai_keywords):
                        topic = HotTopic(
                            title=f"GitHub Trending: {repo_path}",
                            description=description,
                            source="github_trending",
                            url=f"https://github.com/{repo_path}",
                            keywords=ai_keywords,
                            trend_score=min(10.0, 5.0 + stars / 1000),
                            timestamp=datetime.now().isoformat(),
                            tags=["GitHub", "Trending", "AI"]
                        )
                        topics.append(topic)
                except Exception as e:
                    logger.debug(f"Error parsing GitHub trending repo: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error fetching GitHub trending: {e}")

        return topics

    def _discover_from_huggingface(self, source: Dict) -> List[HotTopic]:
        """
        Discover trending models on Hugging Face
        Note: Placeholder implementation
        """
        topics = []

        # In production, use Hugging Face API:
        # https://huggingface.co/api/models?sort=trending&limit=10

        # Mock implementation
        mock_models = [
            HotTopic(
                title="New Multimodal LLM: Vision-Language Model Breakthrough",
                description="A new vision-language model achieves state-of-the-art performance on multiple benchmarks.",
                source="huggingface",
                url="https://huggingface.co/example/model",
                keywords=["Multimodal", "Vision-Language", "LLM"],
                trend_score=8.5,
                timestamp=datetime.now().isoformat(),
                tags=["Hugging Face", "Multimodal", "Research"]
            ),
        ]

        topics.extend(mock_models)
        return topics

    def _remove_duplicates(self, topics: List[HotTopic]) -> List[HotTopic]:
        """Remove topics that have been discovered before"""
        unique_topics = []
        seen_titles = set()

        for topic in topics:
            # Simple deduplication by title similarity
            title_lower = topic.title.lower()
            is_duplicate = False

            for seen_title in seen_titles:
                # Check for significant overlap
                if title_lower in seen_title or seen_title in title_lower:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_topics.append(topic)
                seen_titles.add(title_lower)

        return unique_topics

    def get_topic_summary(self, topics: List[HotTopic]) -> str:
        """Generate a summary of discovered topics"""
        if not topics:
            return "No hot topics discovered today."

        summary_lines = [
            f"## AI Hot Topics Summary - {datetime.now().strftime('%Y-%m-%d')}\n",
            f"Discovered **{len(topics)}** trending topics:\n"
        ]

        for i, topic in enumerate(topics[:5], 1):
            summary_lines.append(f"{i}. **{topic.title}**")
            summary_lines.append(f"   - Score: {topic.trend_score:.1f}/10")
            summary_lines.append(f"   - Source: {topic.source}")
            summary_lines.append(f"   - Tags: {', '.join(topic.tags)}")
            summary_lines.append("")

        return '\n'.join(summary_lines)
