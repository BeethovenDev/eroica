"""Symphony No. 5 in C minor, Op. 67 (1808) — "Fate".

The famous four notes are unavoidable; fate knocks. This movement is about what
*you* cannot avoid: the referers, beacons, pings and telemetry that follow you
across the web and back to the vendor. Here we silence as many as we can.
"""

from __future__ import annotations

from eroica.config import Tier
from eroica.symphonies.base import ChromiumFlag, FirefoxPref, Movement

_T = Tier.STANDARD
_S = Tier.STRICT
_P = Tier.PARANOID

__all__ = ["FATE"]

FATE = Movement(
    key="fate",
    roman="V",
    nickname="Fate",
    title="Symphony No. 5 in C minor",
    opus="Op. 67",
    year=1808,
    signature="C minor",
    summary="Suppress trackers, referer leakage, beacons, telemetry and pings.",
    prefs=(
        FirefoxPref("privacy.trackingprotection.enabled", True, _T),
        FirefoxPref("privacy.trackingprotection.pbmode.enabled", True, _T),
        FirefoxPref("privacy.annotate_channels.strict_list.enabled", True, _T),
        FirefoxPref("network.http.referer.XOriginPolicy", 2, _T,
                    "Only send a referer within the same site."),
        FirefoxPref("network.http.referer.XOriginTrimmingPolicy", 2, _T),
        FirefoxPref("network.http.referer.defaultPolicy", 3, _S,
                    "Same-origin referer policy, even for cross-site navigations."),
        FirefoxPref("network.http.referer.defaultPolicy.pbmode", 3, _S),
        FirefoxPref("network.http.referer.trimmingPolicy", 2, _S),
        FirefoxPref("beacon.enabled", False, _T,
                    "Kill navigator.sendBeacon beacons."),
        FirefoxPref("browser.send_pings", False, _T),
        FirefoxPref("browser.send_pings.require_same_host", True, _T),
        FirefoxPref("browser.tabs.sendMessage", False, _T),
        FirefoxPref("dom.reporting.enabled", False, _S,
                    "Turn off the Reporting API (crash/network reports)."),
        FirefoxPref("dom.reporting.featurePolicy.enabled", False, _S),
        FirefoxPref("dom.reporting.header.enabled", False, _S),
        FirefoxPref("browser.ping-centre.telemetry", False, _T),
        FirefoxPref("toolkit.telemetry.enabled", False, _T),
        FirefoxPref("toolkit.telemetry.unified", False, _T),
        FirefoxPref("toolkit.telemetry.archive.enabled", False, _S),
        FirefoxPref("toolkit.telemetry.dap_enabled", False, _S,
                    "Opt out of the newer differential-privacy telemetry."),
        FirefoxPref("toolkit.telemetry.coverage.opt-out", True, _S),
        FirefoxPref("toolkit.coverage.opt-out", True, _S),
        FirefoxPref("toolkit.coverage.endpoint.base", "", _S),
        FirefoxPref("datareporting.healthreport.uploadEnabled", False, _T),
        FirefoxPref("datareporting.policy.dataSubmissionEnabled", False, _T),
        FirefoxPref("browser.newtabpage.activity-stream.feeds.telemetry", False, _T),
        FirefoxPref("browser.newtabpage.activity-stream.telemetry", False, _T),
        FirefoxPref("browser.newtabpage.activity-stream.telemetry.structuredIngestion", False, _T),
        FirefoxPref("security.ssl.require_safe_negotiation", True, _P,
                    "Refuse connections that cannot negotiate safely."),
        FirefoxPref("network.proxy.socks_remote_dns", True, _P,
                    "Resolve DNS through the proxy rather than in the clear."),
        FirefoxPref("browser.uitour.enabled", False, _S),
        FirefoxPref("browser.uitour.url", "", _S),
        FirefoxPref("dom.push.enabled", False, _P),
        FirefoxPref("dom.push.connection.enabled", False, _P),
    ),
    flags=(
        ChromiumFlag("--no-pings", _T),
        ChromiumFlag("--no-crash-upload", _T),
        ChromiumFlag("--disable-breakpad", _T),
        ChromiumFlag("--disable-domain-reliability", _T,
                     "No background domain reputation lookups."),
        ChromiumFlag("--disable-client-side-phishing-detection", _S),
        ChromiumFlag("--disable-component-update", _S),
        ChromiumFlag("--disable-background-networking", _S),
        ChromiumFlag("--disable-component-extensions-with-background-pages", _S),
        ChromiumFlag("--metrics-recording-only", _S),
        ChromiumFlag("--force-webrtc-ip-handling-policy=default_public_interface_only", _S,
                     "Stop WebRTC from revealing local interface IPs."),
        ChromiumFlag("--webrtc-ip-handling-policy=default_public_interface_only", _S),
    ),
)
