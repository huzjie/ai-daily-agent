# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Continuous integration hardened: least-privilege `permissions: contents: read`
  on every workflow (OpenSSF Scorecard *Token-Permissions*).

## [v0.1.0] - 2026-08-06

### Added
- Automated pipeline: discover daily AI topics, generate a project, publish to GitHub and monitor metrics.
- GitHub REST API transport layer that works where git push is blocked.
- Repository optimization toolchain (topics, docs, CI, releases).

### Security
- CodeQL static analysis enabled.
- Least-privilege GitHub Actions token permissions on all workflows.

[Unreleased]: https://github.com/huzjie/ai-daily-agent/compare/v0.1.0...HEAD
[v0.1.0]: https://github.com/huzjie/ai-daily-agent/releases/tag/v0.1.0
