<div align="center">

# EROICA

**Browser privacy hardening for OSINT and everyday anonymity.**

*Named after Beethoven's Symphony No. 3 in E♭ major, Op. 55 — the "Eroica" — the work that rewrote the rules of the form.*

[![CI](https://github.com/BeethovenDev/eroica/actions/workflows/ci.yml/badge.svg)](https://github.com/BeethovenDev/eroica/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)](#philosophy)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

</div>

---

EROICA turns an ordinary browser into a quieter, harder-to-fingerprint one. It
does so by composing independent **movements**, each addressing a single
concern — foundations, anti-fingerprinting, tracker suppression, storage
hygiene and transport security — and applying them to an **isolated profile**
that never touches your everyday browsing.

It is dependency-free (Python standard library only), cross-platform
(Windows · macOS · Linux) and understands both **Mozilla** (Firefox, LibreWolf,
Waterfox, Zen) and **Chromium** (Chrome, Chromium, Brave, Edge, Vivaldi)
families.

> **What this is.** A defensive privacy tool for investigators, journalists and
> anyone who would rather not be tracked. **What this is not.** An anonymity
> network, and not a way past authentication, paywalls, CAPTCHAs or access
> controls. Read the [threat model](docs/THREAT_MODEL.md) before relying on it.

## Why "Eroica"?

Beethoven's Third Symphony was longer, stranger and more ambitious than anything
that came before it; contemporaries thought it had gone too far. The same
spirit applies here: browsers ship a generous default attack surface, and EROICA
is unapologetic about shrinking it. Each hardening theme is named after a
movement of the symphonic repertoire — the *First* lays the foundation, the
*Eroica* fights fingerprinting, *Fate* silences the pings you cannot avoid, the
*Pastoral* clears the state behind you, and the *Choral* seals the wire.

## Install

EROICA targets **Python 3.10+** and has **no runtime dependencies**.

```bash
# from source (recommended while the project is young)
git clone https://github.com/BeethovenDev/eroica.git
cd eroica
python -m pip install -e .
```

Verify your environment and see which browsers EROICA can see:

```bash
eroica doctor
```

## Quick start

```bash
# 1. Create an isolated, hardened profile for OSINT work
eroica new --browser firefox --profile osint-1 --tier strict

# 2. Launch a hardened session (opens in its own profile directory)
eroica launch --browser firefox --profile osint-1 https://example.com

# 3. Later, check the profile has not drifted
eroica audit --browser firefox --profile osint-1
```

That is the whole loop: **create → launch → audit**.

### Throwaway sessions (`stealth`)

When a lookup should leave no trace in this machine — a fresh identity, a clean
session, nothing carried over — use `stealth`:

```bash
# A brand-new random profile, hardened at paranoid, opened in a private window.
# The profile is deleted the moment the browser closes.
eroica stealth https://example.com

# Keep the profile for later inspection instead of deleting it.
eroica stealth --keep --browser brave

# Preview exactly what would run, without touching disk.
eroica stealth --dry-run --browser zen
```

- Every run generates a **new random profile** — nothing is reused, so sessions
  are not correlated with each other.
- Hardening runs at `paranoid` by default (`--tier` to override), the browser
  opens in private mode on that isolated profile.
- On exit the profile is **discarded** unless you pass `--keep`. Windows browsers
  occasionally keep files locked for a few seconds after closing; `stealth`
  waits them out in-process, and if the browser is *still* releasing files it
  schedules a detached `purge` worker that finishes the deletion in the
  background — the self-destruct never silently fails.
- **Honest limit:** `stealth` protects your *identity inside the site* — not
  your network identity. The endpoint still sees your real IP; pair it with a
  VPN or Tor if that matters.

### Routing through a proxy (the network layer)

Hardening alone cannot hide your IP — that needs a network you trust. EROICA
doesn't pretend otherwise; it *orchestrates* the tunnel and verifies the exit:

```bash
# Route every hardened session through the Tor SOCKS endpoint
eroica tor on

# ...and confirm what the public internet actually sees
eroica check-ip

# A gate before risky research: fail loudly unless this exit IP appears
eroica check-ip --expect 185.220.101.4 ; echo $?

# Or point at any SOCKS5 endpoint (e.g. a VPN on a static IP)
eroica proxy socks5://10.0.0.5:1080
eroica proxy off
```

- When a proxy is configured, hardening forces **all** traffic and **DNS**
  through it: for Firefox that means `socks_remote_dns` + DoH off, for Chromium
  `--proxy-server` + `--host-resolver-rules` + DoH off — a hostname can no
  longer leak straight to your ISP's resolver.
- `tor on --apply` (or `proxy ...` plus a re-`harden`) applies routing to every
  existing profile; `eroica audit` stays the source of truth.
- **Honest limit:** `check-ip` verifies the network path — it does not make the
  path. Keep Tor (or your VPN) running; if it drops, `check-ip` says
  `reachable: false` instead of guessing. Tor circuits rotate constantly, so
  `--expect` is for *stable* exit IPs (VPNs), not Tor.

## The five movements

| # | Movement | Opus | Concern | Highlights |
|---|----------|------|---------|------------|
| I | **First** — C major | Op. 21 | Foundations | Quiet startup, no vendor callbacks, no prefetch/predictor, address-bar honesty |
| III | **Eroica** — E♭ major | Op. 55 | Anti-fingerprinting | `resistFingerprinting` + letterboxing, canvas/WebGL/timer hardening, query stripping |
| V | **Fate** — C minor | Op. 67 | Tracking & telemetry | Referer trimming, beacons off, telemetry off, WebRTC IP leak guard |
| VI | **Pastoral** — F major | Op. 68 | Storage hygiene | Cookie partitioning, clear-on-shutdown, deny camera/mic/location by default |
| IX | **Choral** — D minor | Op. 125 | Transport security | Strict DNS-over-HTTPS, Encrypted Client Hello, 0-RTT off, CRLite |

Inspect them from the CLI:

```bash
eroica symphonies --tier strict
```

## Tiers

Hardening is *additive*: a higher tier is a strict superset of the lower ones.
Every setting declares the minimum tier at which it applies.

| Tier | For whom | Character |
|------|----------|-----------|
| `standard` | Everyday users | Sane, low-friction; almost nothing breaks |
| `strict` *(default)* | OSINT & journalists | Aggressive; a few sites may need exceptions |
| `paranoid` | High-risk research | Maximum; expect breakage and manual tuning |

```bash
eroica new -b brave -p research --tier paranoid
eroica harden -b brave -p research --tier strict   # re-tune later
```

## Commands

| Command | Description |
|---------|-------------|
| `eroica doctor` | Environment and browser detection |
| `eroica symphonies` | List movements and the settings active at a tier |
| `eroica new` | Create **and** harden a new isolated profile |
| `eroica profiles` | List existing profiles |
| `eroica harden` | (Re)apply hardening; `--dry-run` prints the `user.js` |
| `eroica audit` | Detect drift; exits non-zero if unhealthy |
| `eroica launch` | Launch the browser in its hardened profile |
| `eroica stealth` | Throwaway, anonymous-profile session; self-destructs on exit |
| `eroica purge` | Wait for a locked profile to be released, then delete it |
| `eroica tor` | Route hardened sessions through the Tor SOCKS endpoint |
| `eroica proxy` | Set or clear the SOCKS proxy used by all hardened sessions |
| `eroica check-ip` | Report the IP the internet sees, directly and via the proxy |
| `eroica config` | Show or update global configuration |
| `eroica remove` | Delete a profile |

Add `--json` to any command for machine-readable output on stdout (logs always
go to stderr, so pipes stay clean).

```bash
eroica doctor --json | jq '.browsers[] | select(.installed)'
```

## How it works

```
                    ┌─────────────────────────────┐
   symphonies/      │  I · III · V · VI · IX      │   each movement = one theme
                    └──────────────┬──────────────┘
                                   │  tier filters settings
                    ┌──────────────▼──────────────┐
   hardening.py     │  resolve plan (prefs/flags) │   + DoH endpoint, + pinned UA, + SOCKS proxy
                    └───────┬───────────────┬─────┘
                            │               │
              Mozilla family│               │Chromium family
                    ┌───────▼──────┐ ┌──────▼───────────────┐
                    │  user.js     │ │  launch flags +       │
                    │  (prefs)     │ │  isolated user-data   │
                    └──────────────┘ └──────────────────────┘
```

* **Mozilla** — EROICA writes a `user.js` into the profile. Its output lives
  inside clearly marked `BEGIN`/`END` comments so any manual prefs you add are
  preserved; the previous file is backed up before the first overwrite.
* **Chromium** — privacy is mostly compile-time, so EROICA curates launch flags
  and records them alongside the isolated `--user-data-dir`. `eroica launch`
  then starts the browser with exactly those flags.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the module map.

## Philosophy

* **Boring is anonymous.** A User-Agent that changes every request is its own
  fingerprint. EROICA pins one mainstream UA per profile, deterministically
  derived from the profile name.
* **Routing is separate from hardening.** EROICA can route a session through
  Tor or any SOCKS5 proxy, but it never claims that makes you anonymous — it
  verifies the exit (`check-ip`) and says "unreachable" when it cannot.
* **Fail closed, but say so.** Strict DoH and HTTPS-only mode fail closed; the
  audit and `--dry-run` exist so you always know what changed.
* **No hidden magic.** Every setting is in a readable movement module with a
  comment explaining *why*. There are no dependencies to trust.
* **Reverse nothing.** EROICA never touches authentication, cookies belonging
  to other profiles, or access controls.

## Configuration

Stored as JSON under your platform config directory (`eroica doctor` shows the
exact path).

```bash
eroica config show
eroica config set --tier strict --doh quad9 --ua-mode consistent
```

Available DoH providers: `mullvad` (default), `quad9`, `cloudflare`, `google`,
and `system` (leave the resolver untouched).

## Contributing

Contributions are welcome — especially new movements, browser support and
regression tests. Start with [`CONTRIBUTING.md`](CONTRIBUTING.md) and the
[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## Security

Please report vulnerabilities privately; see [`SECURITY.md`](SECURITY.md).

## License

[MIT](LICENSE) © 2026 The EROICA Authors.

---

<div align="center">
<sub>“From the heart, may it go to the heart.” — Ludwig van Beethoven</sub>
</div>
