"""
GitHub Publisher Module
Handles creating repos, pushing code, and managing GitHub releases
"""

import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class GitHubPublisher:
    """
    Publish generated projects to GitHub as public repositories.
    Uses git CLI + gh CLI for all operations.
    """

    def __init__(self, config: Dict):
        self.config = config
        self.github_config = config.get('github', {})
        self.username = self.github_config.get('username', '')
        self.repo_prefix = self.github_config.get('repo_prefix', 'ai-daily-')
        self.branch = self.github_config.get('branch', 'main')
        self.published_repos_file = Path(config.get('output_dir', 'data')) / "published_repos.json"
        self._load_published()

    def _load_published(self):
        """Load history of published repos"""
        try:
            with open(self.published_repos_file, 'r', encoding='utf-8') as f:
                self.published = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.published = []

    def _save_published(self):
        """Save published repos history"""
        with open(self.published_repos_file, 'w', encoding='utf-8') as f:
            json.dump(self.published, f, ensure_ascii=False, indent=2)

    def _run_git(self, cmd: str, cwd: str = None) -> Tuple[bool, str]:
        """Run a git command and return (success, output)"""
        try:
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=120
            )
            if result.returncode != 0:
                logger.error(f"Git command failed: {cmd}\n{result.stderr}")
                return False, result.stderr
            return True, result.stdout
        except Exception as e:
            logger.error(f"Error running git command: {e}")
            return False, str(e)

    def _run_gh(self, cmd: str, cwd: str = None) -> Tuple[bool, str]:
        """Run a gh CLI command and return (success, output)"""
        try:
            result = subprocess.run(
                f"gh {cmd}",
                capture_output=True,
                text=True,
                shell=True,
                cwd=cwd,
                timeout=120
            )
            if result.returncode != 0:
                logger.error(f"gh command failed: gh {cmd}\n{result.stderr}")
                return False, result.stderr
            return True, result.stdout
        except Exception as e:
            logger.error(f"Error running gh command: {e}")
            return False, str(e)

    def check_auth(self) -> bool:
        """Check if GitHub authentication is set up"""
        success, output = self._run_gh("auth status")
        if success:
            logger.info("GitHub authentication OK")
            return True
        else:
            logger.error("GitHub authentication failed. Please run: gh auth login")
            return False

    def create_repo(self, project_dir: str, topic: Dict) -> Optional[str]:
        """
        Create a new GitHub repository and push the project
        
        Returns:
            Repository URL if successful, None otherwise
        """
        project_path = Path(project_dir)
        repo_name = project_path.name

        # Check if already published
        for repo in self.published:
            if repo.get('name') == repo_name:
                logger.warning(f"Repository {repo_name} already published")
                return repo.get('url')

        # Ensure git is initialized
        success, _ = self._run_git("git init", cwd=project_dir)
        if not success:
            return None

        # Create repo on GitHub
        description = topic.get('description', '')[:200]
        create_cmd = f'repo create {repo_name} --public --description "{description}" --source {project_dir} --push'
        success, output = self._run_gh(create_cmd, cwd=project_dir)
        
        if not success:
            # If repo already exists, try to push to it
            logger.warning(f"Repo creation failed, trying to push to existing repo: {output}")
            success, _ = self._run_git(f"git remote add origin https://github.com/{self.username}/{repo_name}.git", cwd=project_dir)
            success, output = self._run_git(f"git push -u origin {self.branch}", cwd=project_dir)
            if not success:
                return None

        repo_url = f"https://github.com/{self.username}/{repo_name}"

        # Record the published repo
        self.published.append({
            'name': repo_name,
            'url': repo_url,
            'topic': topic.get('title', ''),
            'tags': topic.get('tags', []),
            'published_at': datetime.now().isoformat(),
            'stars': 0,
            'forks': 0
        })
        self._save_published()

        logger.info(f"Successfully published: {repo_url}")
        return repo_url

    def create_release(self, repo_name: str, tag: str = None, name: str = None) -> Optional[str]:
        """
        Create a GitHub release for a repository
        
        Returns:
            Release URL if successful, None otherwise
        """
        if not tag:
            tag = f"v0.1.0-{datetime.now().strftime('%Y%m%d')}"
        if not name:
            name = f"Initial Release - {datetime.now().strftime('%Y-%m-%d')}"

        release_cmd = f'release create {tag} --title "{name}" --notes "Auto-generated release by AI Daily Agent"'
        success, output = self._run_gh(release_cmd)

        if success:
            logger.info(f"Release created: {tag}")
            return f"https://github.com/{self.username}/{repo_name}/releases/tag/{tag}"
        return None

    def update_hub_repo(self, hub_dir: str) -> Optional[str]:
        """
        Update the master hub repository with links to all daily projects
        
        Returns:
            Hub repo URL if successful, None otherwise
        """
        # Update the hub README with all projects
        self._generate_hub_readme(hub_dir)

        # Commit and push changes
        success, _ = self._run_git("git add .", cwd=hub_dir)
        if not success:
            return None

        commit_msg = f"chore: update projects list - {datetime.now().strftime('%Y-%m-%d')}"
        success, _ = self._run_git(f'git commit -m "{commit_msg}"', cwd=hub_dir)
        if not success:
            return None

        success, _ = self._run_git(f"git push origin {self.branch}", cwd=hub_dir)
        if not success:
            return None

        return f"https://github.com/{self.username}/{self.repo_prefix}hub"

    def _generate_hub_readme(self, hub_dir: str):
        """Generate the hub README with all project links"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        # Build project list from published repos
        projects_list = []
        for repo in reversed(self.published):
            tags_badge = ' '.join([f'`{tag}`' for tag in repo.get('tags', [])])
            projects_list.append(
                f"| {repo.get('published_at', '')[:10]} | "
                f"[{repo['name']}]({repo['url']}) | "
                f"{repo.get('topic', '')} | "
                f"⭐ {repo.get('stars', 0)} | "
                f"{tags_badge} |"
            )

        projects_table = '\n'.join(projects_list)

        readme = f'''# 🤖 AI Daily Projects Hub

<div align="center">

**Daily AI Innovation - One Project Per Day**

![Projects Count](https://img.shields.io/badge/Projects-{len(self.published)}-blue)
![Last Updated](https://img.shields.io/badge/Updated-{date_str}-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

*Building the future of AI, one project at a time 🚀*

</div>

---

## 📋 About

This is the central hub for all AI projects generated by the **AI Daily Agent**. Every day, the agent:

1. 🔍 **Discovers** the hottest AI topics and trends
2. 🛠️ **Generates** a complete, production-ready project
3. 📦 **Publishes** it as a public GitHub repository
4. 📊 **Monitors** engagement and growth

## 🎯 Why?

The goal is to:
- Stay on the cutting edge of AI developments
- Build a portfolio of practical AI solutions
- Demonstrate the power of AI-assisted development
- Create value for the open source community

## 📊 Project Stats

| Metric | Value |
|--------|-------|
| Total Projects | {len(self.published)} |
| Days Active | {len(set(r.get('published_at', '')[:10] for r in self.published))} |
| Total Stars | {sum(r.get('stars', 0) for r in self.published)} |
| Total Forks | {sum(r.get('forks', 0) for r in self.published)} |

## 🗂️ All Projects

| Date | Project | Topic | Stars | Tags |
|------|---------|-------|-------|------|
{projects_table}

## 🏗️ Architecture

Each project follows a consistent structure:

```
ai-daily-YYYYMMDD-{topic}/
├── src/              # Source code
├── tests/            # Test suite
├── docs/             # Documentation
├── .github/          # CI/CD workflows
├── Dockerfile        # Container config
├── README.md         # Full documentation
├── LICENSE           # MIT License
└── requirements.txt  # Dependencies
```

## 🤖 The Agent

This entire system is powered by the **AI Daily Agent**, which:

- Uses **multi-source trend analysis** to identify hot topics
- Generates **production-ready code** with tests, docs, and CI/CD
- Automatically **publishes to GitHub** with proper structure
- **Monitors metrics** and tracks growth over time

Want to learn more? Check out the [agent repository](https://github.com/{self.username}/ai-daily-agent).

## 🤝 Contributing

Each project is independent but contributions are always welcome! Check individual repos for their contribution guidelines.

## 📬 Contact

- **GitHub**: [@{self.username}](https://github.com/{self.username})
- **Issues**: Report on individual project repos

---

<div align="center">

**⭐ Star this repo to follow along with daily AI projects! ⭐**

*Powered by [AI Daily Agent](https://github.com/{self.username}/ai-daily-agent)*

</div>
'''
        readme_path = Path(hub_dir) / "README.md"
        readme_path.write_text(readme, encoding='utf-8')

    def get_repo_metrics(self, repo_name: str) -> Dict:
        """Get metrics for a specific repository"""
        success, output = self._run_gh(f'repo view {self.username}/{repo_name} --json stargazerCount,forkCount,watchers,issues')
        if success:
            try:
                data = json.loads(output)
                return {
                    'stars': data.get('stargazerCount', 0),
                    'forks': data.get('forkCount', 0),
                    'watchers': data.get('watchers', {}).get('totalCount', 0),
                    'issues': data.get('issues', {}).get('totalCount', 0),
                    'fetched_at': datetime.now().isoformat()
                }
            except json.JSONDecodeError:
                pass
        return {}

    def update_metrics(self) -> Dict:
        """Update metrics for all published repos"""
        metrics = {}
        for repo in self.published:
            name = repo.get('name')
            if name:
                repo_metrics = self.get_repo_metrics(name)
                if repo_metrics:
                    repo.update(repo_metrics)
                    metrics[name] = repo_metrics

        self._save_published()
        return metrics
