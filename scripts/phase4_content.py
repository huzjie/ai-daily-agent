#!/usr/bin/env python3
"""Phase-4 long-form content: VideoForge packaging (P0-7) and profile README (P0-8).

Kept separate from ``gh_optimize_phase4.py`` so the orchestration logic stays
readable. Every factual claim below (engine ids, capabilities, API routes,
compose path, auth flow) was verified against the repository source before
being written — see ``scripts/_phase4_probe*.py``.
"""
from __future__ import annotations

from typing import Any, List

USER = "huzjie"
VFS = "video-forge-studio"

# --------------------------------------------------------------------------- #
# P0-7a : topics / description / homepage
# --------------------------------------------------------------------------- #
VFS_TOPICS: List[str] = [
    # track words
    "video-generation", "ai-video", "text-to-video", "image-to-video",
    # architecture words
    "control-plane", "orchestration", "llm-orchestration", "self-hosted",
    # stack words
    "fastapi", "celery", "python", "rest-api",
]

VFS_DESCRIPTION = (
    "Unified control plane for AI video generation — orchestrate 6 engines "
    "(self-hosted + commercial API) behind one REST API. Celery queues with "
    "retries and quotas, and a built-in Mock engine so the full pipeline and "
    "CI run with zero GPU and zero API keys."
)

VFS_HOMEPAGE = f"https://github.com/{USER}/{VFS}#quickstart"


def step_vfs_meta(gh: Any, ledger: Any) -> None:
    """P0-7: topics (>=8), English description with quantified benefit, homepage."""
    print("\n--- P0-7  video-forge-studio 基础包装：topics / description / homepage ---")

    info = gh.repo_info(VFS)
    current_topics = set(info.get("topics") or [])
    if current_topics >= set(VFS_TOPICS):
        ledger.add("skipped", VFS, "topics", f"已含全部 {len(VFS_TOPICS)} 个 topic")
    else:
        code, body = gh.request("PUT", f"/repos/{gh.user}/{VFS}/topics",
                                {"names": VFS_TOPICS})
        if code == 200:
            ledger.add("updated", VFS, "topics", f"{len(VFS_TOPICS)} 个：{VFS_TOPICS}")
        elif code == 999:
            ledger.add("skipped", VFS, "topics", "dry-run")
        else:
            ledger.add("failed", VFS, "topics", f"HTTP {code} {str(body)[:180]}")

    want = {"description": VFS_DESCRIPTION, "homepage": VFS_HOMEPAGE}
    if (info.get("description") == VFS_DESCRIPTION
            and info.get("homepage") == VFS_HOMEPAGE):
        ledger.add("skipped", VFS, "description/homepage", "已是目标值")
    else:
        code, body = gh.request("PATCH", f"/repos/{gh.user}/{VFS}", want)
        if code == 200:
            ledger.add("updated", VFS, "description/homepage", "英文描述 + homepage")
        elif code == 999:
            ledger.add("skipped", VFS, "description/homepage", "dry-run")
        else:
            ledger.add("failed", VFS, "description/homepage",
                       f"HTTP {code} {str(body)[:180]}")


# --------------------------------------------------------------------------- #
# P0-7b : README rewrite (English-first)
# --------------------------------------------------------------------------- #
# Hard rule from the brief: never put "217 files / 37k lines" above the fold.
# The honest, comparable signal is "51/51 tests passing · 6 engines · 1 API".

VFS_README_EN = """<div align="center">

# VideoForge Studio

**Unified control plane for AI video generation — orchestrate 6 engines
(self-hosted + commercial API) behind one REST API.**

[![CI](https://github.com/huzjie/video-forge-studio/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/huzjie/video-forge-studio/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-51%2F51%20passing-brightgreen)](https://github.com/huzjie/video-forge-studio/tree/main/tests)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/huzjie/video-forge-studio?display_name=tag)](https://github.com/huzjie/video-forge-studio/releases/latest)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/huzjie/video-forge-studio/badge)](https://scorecard.dev/viewer/?uri=github.com/huzjie/video-forge-studio)
[![Top language](https://img.shields.io/github/languages/top/huzjie/video-forge-studio)](https://github.com/huzjie/video-forge-studio)
[![Last commit](https://img.shields.io/github/last-commit/huzjie/video-forge-studio)](https://github.com/huzjie/video-forge-studio/commits/main)

**51/51 tests passing · 6 engines · 1 API**

[English](README.md) · [简体中文](README.zh-CN.md)

</div>

---

## What it is, in 30 seconds

- **Six engines, one API.** `mock`, `minimax_h3`, `wan`, `cogvideo`, `hunyuan`
  and `openai_compatible` all implement the same `BaseEngine` contract. Switch
  engines with one field in the request body — your application code never
  changes.
- **Production task plane, not a demo script.** Celery + Redis job queues with a
  `queued → running → succeeded / failed / cancelled` state machine, retries with
  backoff, per-user quotas, scheduled cleanup, and an automatic in-process
  fallback when Redis is absent.
- **A Mock engine means no GPU is needed to run CI.** The built-in `mock` engine
  produces a real MP4 container offline, with no API key and no accelerator, so
  the whole path — job → engine → video → evaluation — is exercisable on a
  laptop and inside a CI runner. This is the difference between "clone it and it
  runs" and "clone it and go rent an H100".

---

## Quickstart

Three commands. The default engine is `mock`, so nothing below needs a GPU or an
API key.

```bash
# 1 — boot the stack (Postgres + Redis + API + Celery worker)
VIDEOFORGE_SECRET_KEY=dev-secret docker compose -f docker/docker-compose.yml up -d

# 2 — create a user and export a JWT
curl -s -X POST localhost:8000/api/v1/auth/register -H 'Content-Type: application/json' \\
  -d '{"email":"dev@example.com","username":"dev","password":"devpassword"}' >/dev/null && \\
TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/login \\
  -d 'username=dev&password=devpassword' | jq -r .access_token)

# 3 — submit a generation job and read back the job_id
curl -s -X POST localhost:8000/api/v1/jobs -H "Authorization: Bearer $TOKEN" \\
  -H 'Content-Type: application/json' \\
  -d '{"engine":"mock","prompt":"a paper plane gliding over a neon city at dusk"}' | jq -r .id
```

Poll it with `curl -s localhost:8000/api/v1/jobs/<job_id> -H "Authorization: Bearer $TOKEN"`.
Interactive OpenAPI docs live at <http://localhost:8000/docs>.

---

## Architecture

```mermaid
flowchart LR
    Client["Client<br/>(Web console · CLI · your app)"]
    API["FastAPI<br/>/api/v1"]
    Router["Engine Router<br/>(EngineRegistry)"]

    subgraph Engines["6 Engines — one BaseEngine contract"]
        direction TB
        E1["mock<br/>offline · no GPU"]
        E2["minimax_h3"]
        E3["wan"]
        E4["cogvideo"]
        E5["hunyuan"]
        E6["openai_compatible<br/>self-hosted"]
    end

    Queue["Celery Workers<br/>retry · quota · state machine"]
    Store["Storage<br/>PostgreSQL · Redis · object store"]

    Client -->|REST + JWT| API
    API --> Router
    Router --> Engines
    API --> Queue
    Queue --> Engines
    Queue --> Store
    Engines --> Store
    Store --> API
```

---

## How it compares

> **HunyuanVideo, Wan and CogVideoX are not competitors — they are what
> VideoForge orchestrates.** They are generation models; VideoForge is the
> control plane that schedules them. The projects below are the real
> comparison set.

| Project | Positioning | Deployment shape | Multi-tenancy | Engine coverage |
| --- | --- | --- | --- | --- |
| **VideoForge Studio** | Control plane / integrable infrastructure | REST API service + Celery workers, Docker & K8s | Users, JWT auth, per-user quotas, job isolation | 6 engines: self-hosted + commercial API, one contract |
| **ComfyUI** (★110,000+, 2026-04) | Node-based workflow canvas | Local GUI first | None — single operator | Deep local model graph; no commercial API engines, no queue SLA |
| **Wan2GP** (community scale, 2026) | Single-machine WebUI for 6–10 GB VRAM | One box, one user | None | Runs Wan-family models locally; no REST API, no horizontal scaling |
| **OpenMontage** (★32k, 2026-05) | Agent-orchestrated finished-video production | App that makes one complete video | Not the goal | Optimizes for a finished cut, not for being embedded as infrastructure |
| **browser-use/video-use** (★14k, 2026-05) | Agent driving ffmpeg for post-production | Agent/tool runtime | Not the goal | Post-production only; does not schedule generation engines |

Star counts and dates are as observed in 2026-08; treat them as a snapshot, not
a live figure.

---

## Engine support matrix

All capability values are read from each engine's `EngineCapabilities`
declaration in `src/videoforge/engines/`.

| Engine id | Text-to-video | Image-to-video | Max duration | Resolutions | GPU required |
| --- | :---: | :---: | --- | --- | --- |
| `mock` | ✅ | ❌ | 30 s | 360p / 480p / 720p / 1080p | **No** — offline, no API key |
| `minimax_h3` | ✅ | ❌ | 30 s | 720p / 1080p | No (remote API, `MINIMAX_API_KEY`) |
| `wan` | ✅ | ✅ | 10 s | 480p / 720p | No (remote API, `WAN_API_KEY`) |
| `cogvideo` | ✅ | ❌ | 10 s | 480p / 720p | No (remote API, `COGVIDEO_API_KEY`) |
| `hunyuan` | ✅ | ❌ | 10 s | 720p | No (remote API, `HUNYUAN_API_KEY` + secret) |
| `openai_compatible` | ✅ | ✅ | 60 s | 360p / 720p / 1080p | **Yes, on your endpoint** — point it at any self-hosted OpenAI-shaped video endpoint |

Enable a subset with `VIDEOFORGE_ENGINES=mock,wan`. The default is all six;
engines without credentials simply report `configured: false` on
`GET /api/v1/models/health`.

---

## Beyond generation

- **LLM prompt engineering** — topic → structured script with shots, narration
  and visual prompts; short idea → cinematic English prompt (LLM or an offline
  rule dictionary).
- **Storyboards** — one generation job per shot, with a golden-ratio seed chain
  to keep visual continuity across shots.
- **Rule-based evaluation** — five metrics (structural integrity, motion
  plausibility, prompt adherence, resolution fidelity, duration fidelity),
  weighted into a score with a pass threshold and a persisted Markdown report.
- **Three interfaces** — REST API, React 18 console, and a Typer/Rich CLI
  (`videoforge generate / script / jobs / models / eval / serve`).

---

## Configuration

Every setting is an environment variable prefixed `VIDEOFORGE_`; see
[`.env.example`](.env.example) for the full list.

| Variable | Purpose | Default |
| --- | --- | --- |
| `VIDEOFORGE_SECRET_KEY` | JWT signing key — **required** | none |
| `VIDEOFORGE_ENGINES` | Comma-separated enabled engines | all six |
| `VIDEOFORGE_DB_URL` | SQLAlchemy URL | SQLite file |
| `VIDEOFORGE_CELERY_BROKER_URL` | Redis broker; omit to run inline | none |
| `VIDEOFORGE_OUTPUT_DIR` | Rendered video output directory | `data/outputs` |
| `MINIMAX_API_KEY` / `WAN_API_KEY` / `COGVIDEO_API_KEY` / `HUNYUAN_API_KEY` | Per-engine credentials | empty |

---

## Deployment

- **Docker Compose** — `docker compose -f docker/docker-compose.yml up -d`
  brings up PostgreSQL, Redis, the API, the Celery worker and Nginx.
- **Kubernetes** — manifests for Deployment, Service, HPA, Ingress and PVC live
  in [`k8s/`](k8s/).
- **Observability** — Prometheus metrics and OpenTelemetry SDK wiring are
  included; liveness/readiness probes at `/api/v1/health/live` and
  `/api/v1/health/ready`.

---

## Contributing

Issues and pull requests are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md)
and [SECURITY.md](SECURITY.md). Run the suite locally with:

```bash
pip install -r requirements-dev.txt && pytest -q
```

Licensed under [Apache-2.0](LICENSE).
"""

ZH_HEADER = """> **语言 / Language**：[English](README.md) · **简体中文（本页）**
>
> 英文版为主文档，本页为中文副本。

"""


def step_vfs_readme(gh: Any, ledger: Any) -> None:
    """P0-7: English-first README, with the existing Chinese one preserved."""
    print("\n--- P0-7  video-forge-studio README 重写（English-first + 中文副本）---")

    current, _ = gh.get_file(VFS, "README.md")
    zh_existing, _ = gh.get_file(VFS, "README.zh-CN.md")

    # 1) preserve the existing (Chinese) README as README.zh-CN.md
    if zh_existing is not None:
        ledger.add("skipped", VFS, "README.zh-CN.md", "中文副本已存在")
    elif current is None:
        ledger.add("failed", VFS, "README.zh-CN.md", "读取原 README 失败")
    elif "Unified control plane" in current:
        ledger.add("skipped", VFS, "README.zh-CN.md",
                   "原 README 已是英文版，无中文内容可迁移")
    else:
        gh.put_file(
            VFS, "README.zh-CN.md", ZH_HEADER + current,
            "docs(readme): 中文 README 迁移到 README.zh-CN.md（英文版成为主文档）",
        )

    # 2) English-first main README
    gh.put_file(
        VFS, "README.md", VFS_README_EN,
        "docs(readme): 重写为 English-first 首屏\n\n"
        "结构：tagline / 徽章行 / 30 秒三点 / 3 条命令 Quickstart / mermaid 架构图 / "
        "竞品对比表（已声明 HunyuanVideo·Wan·CogVideoX 是编排对象而非竞品）/ "
        "六引擎支持矩阵 / 配置 / 部署 / 贡献。"
        "首屏量化指标改用 51/51 tests · 6 engines · 1 API，不写文件数与代码行数。",
    )


# --------------------------------------------------------------------------- #
# P0-8 : profile README
# --------------------------------------------------------------------------- #
PROFILE_README = """## Hi, I'm huzjie

I build **control planes for AI infrastructure** — the layer between your
application and the models it depends on. My work starts from one observation:
most AI projects fail in production not because a model is weak, but because
governance, observability and reliability were bolted on afterwards. So I build
systems where those three are **kernel primitives, not plugins**.

Everything here is open source, self-hostable and model-agnostic.

---

### The through-line

Three of these projects are the same idea applied at three layers:

| Layer | Project | The primitive it makes native |
| --- | --- | --- |
| **Text** | `unified-ai-gateway` | One OpenAI-compatible endpoint in front of many LLM providers — routing, quotas and cost become infrastructure concerns. |
| **Video** | `video-forge-studio` | One REST API in front of six video engines — queueing, retries and multi-tenancy become infrastructure concerns. |
| **Agents** | `loopforge` | One governed loop kernel for long-running agents — checkpointing, budget limits and audit become infrastructure concerns. |

The other three close the loop: you cannot govern what you cannot measure, so
`argus-eval` handles evaluation and tracing, `moe-bench-studio` handles model
selection, and `ai-daily-agent` keeps the whole portfolio moving.

---

### Flagship projects

**[unified-ai-gateway](https://github.com/huzjie/unified-ai-gateway)** —
*Control plane for the text layer.*
A self-hosted, OpenAI-compatible gateway with smart routing, load balancing,
failover, rate limiting and cost tracking. Swap providers without touching
application code. `TypeScript · pnpm monorepo`

**[video-forge-studio](https://github.com/huzjie/video-forge-studio)** —
*Control plane for the video layer.*
Six generation engines (self-hosted + commercial API) behind one REST API, with
Celery queues, retries and quotas. A built-in Mock engine means the whole
pipeline and its CI run with **zero GPU and zero API keys**.
`Python · FastAPI · Celery · 51/51 tests`

**[loopforge](https://github.com/huzjie/loopforge)** —
*Governance kernel for long-running coding agents.*
Runs autonomous software-engineering loops over hours to days with checkpoint /
resume, budget guardrails and a full audit trail. Recoverable, governable,
auditable, observable. `Python · FastAPI · React`

**[argus-eval](https://github.com/huzjie/argus-eval)** —
*Evaluation and observability for AI agents.*
Tracing SDK, span and score ingestion, 15+ scorers, dataset management and
experiment comparison, on a self-hosted dashboard. `Python · OpenTelemetry`

**[moe-bench-studio](https://github.com/huzjie/moe-bench-studio)** —
*Inference and benchmarking for trillion-parameter MoE models.*
Ten benchmark suites, multi-engine inference and a quantization planner, so
model selection is a measurement rather than a guess. `Python · FastAPI · vLLM`

**[ai-daily-agent](https://github.com/huzjie/ai-daily-agent)** —
*The automation behind the portfolio.*
Discovers daily AI topics, generates a project, publishes it to GitHub and
monitors the metrics — including a REST-API transport layer that keeps working
in networks where `git push` is blocked. `Python`

---

### Principles

- **Self-hostable by default.** No mandatory SaaS in the critical path.
- **Model-agnostic.** Providers are configuration, never an architectural
  commitment.
- **Runnable on a laptop.** If a newcomer needs a GPU to see it work, the
  packaging is broken — hence offline mock engines and inline queue fallbacks.
- **Governance as a primitive.** Quotas, audit trails and budget limits belong
  in the kernel, not in a wrapper.
"""


def step_profile(gh: Any, ledger: Any) -> None:
    """P0-8: create huzjie/huzjie and write the profile README."""
    print("\n--- P0-8  建立 huzjie/huzjie Profile README ---")

    code, _ = gh.get(f"/repos/{gh.user}/{gh.user}")
    if code == 200:
        ledger.add("skipped", gh.user, "(repo)", "同名 profile 仓库已存在")
    else:
        ccode, cbody = gh.request("POST", "/user/repos", {
            "name": gh.user,
            "description": "Control planes for AI infrastructure — profile README",
            "private": False,
            "auto_init": True,
            "has_issues": False,
            "has_projects": False,
            "has_wiki": False,
        })
        if ccode in (200, 201):
            ledger.add("created", gh.user, "(repo)", "profile 仓库创建成功")
            import time
            time.sleep(3)  # let the auto-init commit land before writing
        elif ccode == 999:
            ledger.add("skipped", gh.user, "(repo)", "dry-run")
            return
        else:
            # double-check: a 422 may simply mean it already exists
            vcode, _ = gh.get(f"/repos/{gh.user}/{gh.user}")
            if vcode == 200:
                ledger.add("skipped", gh.user, "(repo)", "创建返回非 2xx，但 GET 确认存在")
            else:
                ledger.add("failed", gh.user, "(repo)",
                           f"HTTP {ccode} {str(cbody)[:200]}")
                return

    gh.put_file(
        gh.user, "README.md", PROFILE_README,
        "docs: Profile README —— 把 11 个散仓库串成 AI 基础设施控制平面产品矩阵叙事",
    )
