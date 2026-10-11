"""Symphony No. 6 in F major, Op. 68 (1808) — "Pastoral".

After the storm comes the calm. This movement is about leaving no trace on the
disk: cookies partitioned per site, storage cleared when the session ends, and
sensitive capabilities (camera, mic, location, notifications) denied by default.
"""

from __future__ import annotations

from eroica.config import Tier
from eroica.symphonies.base import ChromiumFlag, FirefoxPref, Movement

_T = Tier.STANDARD
_S = Tier.STRICT
_P = Tier.PARANOID

__all__ = ["PASTORAL"]

PASTORAL = Movement(
    key="pastoral",
    roman="VI",
    nickname="Pastoral",
    title="Symphony No. 6 in F major",
    opus="Op. 68",
    year=1808,
    signature="F major",
    summary="Storage hygiene: partition cookies, clear state, deny capabilities.",
    prefs=(
        FirefoxPref("privacy.partition.network_state", True, _T,
                    "Partition connection pools and DNS state by top-level site."),
        FirefoxPref("privacy.firstparty.isolate", True, _S,
                    "Total Cookie Protection via full first-party isolation."),
        FirefoxPref("privacy.firstparty.isolate.restrict_opener_access", True, _S),
        FirefoxPref("privacy.firstparty.isolate.use_site", True, _S),
        FirefoxPref("network.cookie.cookieBehavior", 5, _S,
                    "Block cross-site and tracking cookies (behaviour 5)."),
        FirefoxPref("network.cookie.sameSite.noneRequiresSecure", True, _S),
        FirefoxPref("network.cookie.sameSite.laxByDefault", True, _S),
        FirefoxPref("network.cookie.lifetimePolicy", 2, _P,
                    "Session-only cookies; nothing outlives the session."),
        FirefoxPref("privacy.sanitize.sanitizeOnShutdown", True, _S),
        FirefoxPref("privacy.clearOnShutdown.cache", True, _S),
        FirefoxPref("privacy.clearOnShutdown.cookies", True, _S),
        FirefoxPref("privacy.clearOnShutdown.sessions", True, _S),
        FirefoxPref("privacy.clearOnShutdown.history", True, _P),
        FirefoxPref("privacy.clearOnShutdown.offlineApps", True, _S),
        FirefoxPref("privacy.clearOnShutdown.formdata", True, _S),
        FirefoxPref("privacy.clearOnShutdown.downloads", True, _S),
        FirefoxPref("privacy.clearOnShutdown.siteSettings", False, _S,
                    "Keep per-site exceptions so your allowlist survives."),
        FirefoxPref("browser.cache.disk.enable", False, _P),
        FirefoxPref("browser.privatebrowsing.forceMediaMemoryCache", True, _S),
        FirefoxPref("browser.sessionstore.privacy_level", 2, _S),
        FirefoxPref("browser.sessionstore.max_resumed_crashes", 0, _P),
        FirefoxPref("permissions.default.geo", 2, _S, "Deny location by default."),
        FirefoxPref("permissions.default.camera", 2, _S),
        FirefoxPref("permissions.default.microphone", 2, _S),
        FirefoxPref("permissions.default.desktop-notification", 2, _S),
        FirefoxPref("permissions.default.xr", 2, _S),
        FirefoxPref("permissions.default.shortcuts", 2, _S),
        FirefoxPref("permissions.manager.defaultsUrl", "", _S),
        FirefoxPref("privacy.donottrackheader.enabled", True, _T,
                    "Polite signal; modern sites ignore it, but it costs nothing."),
        FirefoxPref("dom.storage_access.auto_grants", False, _P),
    ),
    flags=(
        ChromiumFlag("--disable-features=AutofillEnableAccountWalletStorage", _T),
        ChromiumFlag("--disk-cache-size=1", _S, "Keep an effectively empty disk cache."),
        ChromiumFlag("--media-cache-size=1", _S),
        ChromiumFlag("--disable-features=NetworkTimeServiceQuerying", _P),
    ),
)
