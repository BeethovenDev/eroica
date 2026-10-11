# Threat model

Honesty about limits is part of good tooling. This document states what EROICA
defends against, what it explicitly does not, and the assumptions it makes.

## Scope and intent

EROICA is a **defensive privacy** tool. It reduces the passive and active
signals a browser emits, and it isolates browsing into dedicated profiles. It is
designed for OSINT practitioners, journalists, researchers and privacy-conscious
users.

EROICA does **not**:

* bypass authentication, paywalls, CAPTCHAs or access controls;
* provide network anonymity (there is no Tor/I2P integration here);
* hide your IP address from a site you connect to directly;
* protect against a compromised operating system, a hostile root certificate or
  physical access;
* guarantee you cannot be identified by determined, well-resourced adversaries.

## Adversary matrix

| Adversary | Capability | EROICA helps? |
|-----------|-----------|---------------|
| Ad-tech & analytics | Cookies, JS fingerprinting, referers, beacons | **Yes, substantially** |
| Site-level tracking | Cross-site identifiers, storage, canvas/WebGL | **Yes, substantially** |
| ISP / on-path observer | Sees destination IP and SNI | **Partly** — strict DoH + ECH + HTTPS-only reduce leakage, but not the IP |
| Browser vendor telemetry | Background callbacks, crash pings | **Yes** — disabled across the board |
| Network-level correlation | Timing, packet sizes, traffic analysis | **No** — use a VPN/Tor for that |
| Nation-state with global visibility | Everything above, plus correlation | **No** — out of scope by design |

## Assumptions

* You run a supported, reasonably up-to-date browser.
* Your operating system and its DNS stack are not already compromised.
* You understand that a *unique* configuration is itself identifying: EROICA
  deliberately pushes profiles toward common, mainstream fingerprints rather
  than exotic ones.

## Known trade-offs

* **`paranoid` breaks sites.** WebGL, WebAudio and document fonts are disabled;
  single-page apps, maps and some media fail. That is the intended trade-off.
* **Letterboxing changes the viewport.** Page layout is rounded to a coarse
  size, which is visible.
* **Strict DoH fails closed.** If the chosen resolver is unreachable, name
  resolution stops. Switch to another provider or `system` if needed.
* **Pinned User-Agent can drift from the real engine.** A UA far from your
  actual browser version is itself a fingerprint; keep the pool refreshed.

## Non-goals

EROICA will not add features that help evade accountability for abuse, defeat
account security, or obtain unauthorized access. Feature requests in that
direction are declined.

## Reporting

See [`../SECURITY.md`](../SECURITY.md).
