# Changelog

All notable changes to EROICA are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.1] — 2026-10-11

### Fixed

- **`stealth` self-destruct on Windows.** A browser that just closed can still
  have a child process holding profile files (e.g. `cert9.db`), which made
  cleanup fail on the first try (`WinError 32`). Profile deletion now retries
  with an exponential backoff; if the profile is truly still in use, the
  command exits non-zero, warns loudly, and tells you the exact
  `eroica remove` command instead of pretending the cleanup happened.
- `eroica remove` benefits from the same retry handling.

## [0.2.0] — 2026-10-11

### Added

- **`eroica stealth`** (alias `anon`): a one-shot, fully hardened, private and
  self-destructing browsing session. Generates a fresh random profile, hardens
  it at `paranoid` by default, launches in private mode, and deletes the
  profile when the browser closes (`--keep` to retain, `--dry-run` to preview).
- Honest session warnings: stealth protects the *profile identity*, not the
  network identity — the endpoint still sees your real IP.

## [0.1.1] — 2026-10-11

### Added

- **Zen Browser** support (Firefox-based): binary detection, profile-root
  resolution and hardened `user.js` generation on its own isolated profiles.

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

[Unreleased]: https://github.com/BeethovenDev/eroica/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/BeethovenDev/eroica/releases/tag/v0.2.1
[0.2.0]: https://github.com/BeethovenDev/eroica/releases/tag/v0.2.0
[0.1.1]: https://github.com/BeethovenDev/eroica/releases/tag/v0.1.1
[0.1.0]: https://github.com/BeethovenDev/eroica/releases/tag/v0.1.0
