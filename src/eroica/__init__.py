"""EROICA — privacy hardening for any browser.

EROICA turns an ordinary browser profile into a quieter, harder-to-fingerprint
one. It does this by composing independent *movements* (the ``symphonies``
package), each of which contributes browser settings for a single concern:

* **First** — foundations, profile isolation and a sane baseline.
* **Eroica** — anti-fingerprinting (the heroic third).
* **Fate** — tracking, telemetry and network-callback suppression.
* **Pastoral** — storage, cookie and history hygiene.
* **Choral** — transport security and the closing "Ode to Joy" export.

The name is an homage to Beethoven's Symphony No. 3 in E♭ major, Op. 55
("Eroica"), the work that tore up the rulebook of what a symphony could be —
much as a hardened profile tears up the default attack surface of a browser.

Scope
-----
EROICA is a *defensive privacy* tool. It reduces passive and active
fingerprinting, tracking and telemetry. It is **not** an anonymity network and
it does **not** bypass authentication, paywalls, CAPTCHAs or access controls.
See ``docs/THREAT_MODEL.md`` for the honest limits of what this can and cannot
protect against.
"""

from __future__ import annotations

__all__ = ["__version__", "BANNER"]

__version__ = "0.1.1"

BANNER = r"""
  ___ ___  ___ ___ ___   _
 | __| _ \/ _ \_ _/ __| /_\
 | _||   / (_) | | (__ / _ \
 |___|_|_\\___/___\___/_/ \_\   privacy hardening for any browser
""".strip("\n")
