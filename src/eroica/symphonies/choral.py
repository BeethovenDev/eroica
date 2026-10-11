"""Symphony No. 9 in D minor, Op. 125 (1824) — "Choral".

The finale. Everything up to here happens inside the browser; the ninth movement
finally secures the wire. It forces modern, encrypted transport for both DNS
(DNS-over-HTTPS) and HTTP (ECH / HTTPS-first), and clears the slate for the next
performance — the "Ode to Joy" of an export-ready profile.

The concrete DoH endpoint is injected from your configuration
(:class:`eroica.config.Config`), so this movement only declares the *policy*.
"""

from __future__ import annotations

from eroica.config import Tier
from eroica.symphonies.base import ChromiumFlag, FirefoxPref, Movement

_T = Tier.STANDARD
_S = Tier.STRICT
_P = Tier.PARANOID

__all__ = ["CHORAL"]

CHORAL = Movement(
    key="choral",
    roman="IX",
    nickname="Choral",
    title="Symphony No. 9 in D minor",
    opus="Op. 125",
    year=1824,
    signature="D minor",
    summary="Transport security: encrypted DNS, ECH, OCSP and CRLite.",
    prefs=(
        FirefoxPref("network.trr.mode", 3, _T,
                    "Mode 3 = strict: fail closed if DoH is unavailable."),
        FirefoxPref("network.trr.disable-ECS", True, _T,
                    "Do not leak client subnet to the resolver."),
        FirefoxPref("network.trr.useGET", False, _S),
        FirefoxPref("network.trr.confirmationNS", "skip", _P),
        FirefoxPref("network.dns.echconfig.enabled", True, _S,
                    "Encrypted Client Hello hides the SNI you visit."),
        FirefoxPref("network.dns.http3_echconfig.enabled", True, _S),
        FirefoxPref("network.dns.use_https_rr_as_altsvc", True, _T),
        FirefoxPref("security.tls.enable_0rtt_data", False, _S,
                    "Disable 0-RTT to avoid replay attacks."),
        FirefoxPref("security.OCSP.require", True, _S),
        FirefoxPref("security.pki.crlite_mode", 3, _S,
                    "Use CRLite + OCSP as a fallback."),
        FirefoxPref("security.remote_settings.crlite_filters.enabled", True, _S),
        FirefoxPref("security.cert_pinning.enforcement_level", 2, _S),
        FirefoxPref("network.stricttransportsecurity.preloadlist", True, _T),
        FirefoxPref("security.mixed_content.block_active_content", True, _T),
        FirefoxPref("security.mixed_content.block_display_content", True, _P),
    ),
    flags=(
        ChromiumFlag("--dns-over-https-mode=secure", _T,
                     "Fail closed if DoH is unavailable."),
        ChromiumFlag("--enable-features=EncryptedClientHello", _S,
                     "Enable Encrypted Client Hello."),
        ChromiumFlag("--enable-quic", _S),
    ),
)
