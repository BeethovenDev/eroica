# Changelog

All notable changes to EROICA are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] — 2026-10-11

### Added

- **The network layer** (`net`): EROICA now orchestrates *where* a hardened
  session exits to the internet, not just *what* it looks like.
  - **`eroica tor [on|off]`** — enable or disable routing through the standard
    Tor SOCKS endpoint (`socks5://127.0.0.1:9050`). `--apply` also re-hardens
    every existing profile against the new routing.
  - **`eroica proxy [socks5://host:port | off]`** — set or clear an arbitrary
    SOCKS5 proxy for all hardened sessions (also available as
    `eroica config set --proxy`).
  - **`eroica check-ip [--expect <ip>]`** — a dependency-free SOCKS5 probe
    (RFC 1928) that reports the machine's direct IP **and** the IP the tunnel
    exits on, and fails (exit 1) when `--expect` does not match or cannot be
    verified. The honest gate before risky research.
- **Proxy-aware hardening.** When a proxy is configured, hardening now:
  - routes all Firefox traffic through SOCKS with `socks_remote_dns` (DNS stays
    inside the tunnel) and disables DoH (`network.trr.mode = 5`) so hostnames
    cannot leak around it;
  - gives Chromium `--proxy-server`, `--host-resolver-rules` (DNS forced through
    the proxy) and `--disable-features=DnsOverHttps`, and drops the DoH
    template that would otherwise bypass the tunnel;
  - records the proxy in profile metadata, and clears it again when the proxy is
    turned off.
- **`launch`/`stealth` use the materialised flags.** Chromium sessions now start
  from the exact argument vector written by the last `harden` run (proxy, DoH,
  UA pins included) with a rebuild fallback for never-hardened profiles, instead
  of re-deriving flags that could drift from the profile's actual state.
- Repeated `user.js` directives are collapsed to their final value (matching how
  Firefox applies the file), keeping emitted profiles clean and deterministic.

### Fixed

- **`check-ip` no longer crashes when the tunnel is down.** Probe failures
  (connection refused, no Tor running) are now reported as
  `reachable: false` with the reason, instead of raising.

### Fixed

- **`stealth` now never gives up silently.** Real-world testing showed that on
  Windows a freshly-closed browser can keep hold of profile files (`cert9.db`,
  IndexedDB sqlite) for longer than the in-process retry budget. When that
  happens, `stealth` now:
  - starts a **detached `purge` worker** that keeps retrying in the background
    for up to 5 minutes and finishes the deletion as soon as the files are
    released (the session command can return immediately);
  - never prints the misleading “profile discarded” summary — the report now
    says exactly what happened (`discarded` / `purge_scheduled` / left behind),
    in both text and `--json` modes.

### Added

- **`eroica purge -b <browser> -p <profile>`**: wait (up to `--timeout`, default
  300 s) until a profile's files are released, then delete it. Used both as the
  `stealth` background worker and standalone.

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

[Unreleased]: https://github.com/BeethovenDev/eroica/compare/v0.2.2...HEAD
[0.2.2]: https://github.com/BeethovenDev/eroica/releases/tag/v0.2.2
[0.2.1]: https://github.com/BeethovenDev/eroica/releases/tag/v0.2.1
[0.2.0]: https://github.com/BeethovenDev/eroica/releases/tag/v0.2.0
[0.1.1]: https://github.com/BeethovenDev/eroica/releases/tag/v0.1.1
[0.1.0]: https://github.com/BeethovenDev/eroica/releases/tag/v0.1.0
