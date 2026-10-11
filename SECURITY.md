# Security Policy

## Supported versions

EROICA is pre-1.0. Security fixes are applied to the latest release and to
`main`.

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅        |

## Reporting a vulnerability

Please **do not** open a public issue for security problems. Instead, use
GitHub's private vulnerability reporting:

> **Security** tab → **Report a vulnerability**

Please include:

* a description of the issue and its impact;
* reproduction steps or a proof of concept;
* the affected version, OS and browser;
* any suggested remediation.

You can expect an acknowledgement within a few days. Coordinated disclosure is
appreciated; we will credit reporters unless you prefer otherwise.

## Scope

In scope:

* Any way EROICA could write outside its own profile or config directories.
* Path traversal or arbitrary file write via profile names, config or flags.
* Injection into generated `user.js` or launch arguments.
* Silent weakening of the hardening the user requested.

Out of scope (see the [threat model](docs/THREAT_MODEL.md)):

* Defeating network-level adversaries, IP correlation or traffic analysis.
* Sites breaking because of the `paranoid` tier — that is expected.
* Anything requiring an already-compromised operating system.

## Design guarantees

* **No network access.** EROICA makes no outbound requests of its own.
* **No dependencies.** The standard library is the entire supply chain.
* **No privilege escalation.** It is an unprivileged, per-user tool.
* **Isolation by default.** Hardening targets dedicated profiles under EROICA's
  data directory, not your everyday browser profile.

## Contact

Maintainer: [@BeethovenDev](https://github.com/BeethovenDev).
