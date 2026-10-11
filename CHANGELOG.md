# Changelog

All notable changes to EROICA are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-10-11

### Added

- Five hardening **movements**, each named after a Beethoven symphony:
  - **First** (Op. 21) — foundations, quiet startup, no vendor callbacks.
  - **Eroica** (Op. 55) — anti-fingerprinting.
  - **Fate** (Op. 67) — tracking, telemetry and network-callback suppression.
  - **Pastoral** (Op. 68) — storage, cookie and permission hygiene.
  - **Choral** (Op. 125) — transport security (DoH, ECH, CRLite).
- Additive `standard` / `strict` / `paranoid` tiers.
- Isolated profile management with a reproducible `.eroica.json` sidecar.
- Mozilla strategy: idempotent, backed-up `user.js` generation.
- Chromium strategy: curated launch flags with an isolated `--user-data-dir`.
- Deterministic, per-profile User-Agent pinning.
- JSONL audit with drift detection.
- Dependency-free, fully type-annotated implementation and a 77-test suite.

[Unreleased]: https://github.com/BeethovenDev/eroica/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/BeethovenDev/eroica/releases/tag/v0.1.0
