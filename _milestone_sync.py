"""
Milestone detection + published_repos sync for AI Daily Agent monitor run.
- Rebuilds data/published_repos.json from live GitHub discovery (source of truth)
- Detects star milestones [1,5,10,50,100] on the latest metrics record
- Logs newly crossed milestones vs previous record
"""
import json
import logging
from datetime import datetime
from pathlib import Path

import yaml

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("milestone_sync")

ROOT = Path(__file__).resolve().parent
cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))

from src.monitor import RepoMonitor
from src.monitor.models import RepositoryMetrics

monitor = RepoMonitor(cfg)

MILESTONES = [1, 5, 10, 50, 100]

# 1) Discover all live repos (full objects w/ metrics)
repos = monitor.repo_discovery.discover_all_repos()
logger.info(f"Discovered {len(repos)} repos from GitHub")

# 2) Rebuild published_repos.json (source of truth = GitHub)
published = []
for r in repos:
    m = r.metrics
    published.append({
        "name": r.name,
        "url": r.url or f"https://github.com/{cfg['github']['username']}/{r.name}",
        "topic": r.description or "",
        "tags": r.topics or [],
        "language": r.language or None,
        "stars": m.stars if m else 0,
        "forks": m.forks if m else 0,
        "watchers": m.watchers if m else 0,
        "open_issues": m.issues if m else 0,
        "size_kb": r.size_kb or 0,
        "created_at": r.published_at or "",
        "updated_at": r.pushed_at or "",
        "pushed_at": r.pushed_at or "",
        "is_fork": r.is_fork,
        "archived": r.archived,
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
    })
published.sort(key=lambda x: x["name"])
(ROOT / "data" / "published_repos.json").write_text(
    json.dumps(published, ensure_ascii=False, indent=2), encoding="utf-8"
)
logger.info(f"Synced published_repos.json with {len(published)} repos")

# 3) Milestone detection vs previous record
history = monitor.history
last = history[-1] if history else None
prev = history[-2] if len(history) >= 2 else None

reached_now = {}   # repo -> highest milestone reached
newly_crossed = []  # (repo, milestone)

for name, m in (last.repos.items() if last else {}):
    stars = m.stars
    reached = [ms for ms in MILESTONES if stars >= ms]
    if reached:
        reached_now[name] = max(reached)
        if prev is not None and name in prev.repos:
            prev_stars = prev.repos[name].stars
            # newly crossed = any milestone between prev_stars (exclusive) and stars (inclusive)
            for ms in reached:
                if stars >= ms > prev_stars:
                    newly_crossed.append((name, ms))
        elif prev is None:
            for ms in reached:
                if stars >= ms > 0:
                    newly_crossed.append((name, ms))

print("\n=== MILESTONE DETECTION ===")
print(f"Repos tracked : {len(last.repos) if last else 0}")
print(f"Milestones     : {MILESTONES}")
print(f"Reached now    : {reached_now if reached_now else 'NONE'}")
print(f"Newly crossed  : {newly_crossed if newly_crossed else 'NONE'}")

# 4) Log milestones to agent.log
for name, ms in newly_crossed:
    logger.info(f"🎉 MILESTONE: {name} reached {ms} stars")

if not reached_now:
    logger.info("No repo has reached any star milestone yet (all 0 stars).")

# 5) Persist a milestone log file
log_path = ROOT / "data" / "logs" / "milestones.json"
try:
    milestone_log = json.loads(log_path.read_text(encoding="utf-8"))
except (FileNotFoundError, json.JSONDecodeError):
    milestone_log = []
entry = {
    "date": datetime.now().strftime("%Y-%m-%d"),
    "timestamp": datetime.now().isoformat(timespec="seconds"),
    "reached": reached_now,
    "newly_crossed": [{"repo": n, "milestone": ms} for n, ms in newly_crossed],
}
milestone_log.append(entry)
log_path.write_text(json.dumps(milestone_log, ensure_ascii=False, indent=2), encoding="utf-8")
logger.info(f"Milestone log appended -> {log_path}")

# Summary for caller
summary = {
    "repos": len(last.repos) if last else 0,
    "total_stars": sum(m.stars for m in last.repos.values()) if last else 0,
    "reached": reached_now,
    "newly_crossed": newly_crossed,
}
print("SUMMARY:" + json.dumps(summary, ensure_ascii=False))
