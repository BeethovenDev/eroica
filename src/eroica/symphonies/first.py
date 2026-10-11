"""Symphony No. 1 in C major, Op. 21 (1800) — the foundations.

The first movement establishes the baseline: a profile that starts empty,
stays offline until asked, and does not volunteer information about you to the
browser vendor on every launch.
"""

from __future__ import annotations

from eroica.config import Tier
from eroica.symphonies.base import ChromiumFlag, FirefoxPref, Movement

__all__ = ["FIRST"]

FIRST = Movement(
    key="first",
    roman="I",
    nickname="First",
    title="Symphony No. 1 in C major",
    opus="Op. 21",
    year=1800,
    signature="C major",
    summary="Foundations: quiet startup, no vendor callbacks, sane defaults.",
    prefs=(
        FirefoxPref("browser.privatebrowsing.autostart", True, Tier.STRICT,
                    "Always start in a private session; nothing persists by default."),
        FirefoxPref("browser.startup.page", 0, Tier.STANDARD, "Open a blank page on launch."),
        FirefoxPref("browser.newtabpage.enabled", False, Tier.STANDARD),
        FirefoxPref("browser.startup.homepage_override.mstone", "ignore", Tier.STANDARD),
        FirefoxPref("browser.shell.checkDefaultBrowser", False, Tier.STANDARD),
        FirefoxPref("browser.aboutwelcome.enabled", False, Tier.STANDARD,
                    "Skip the onboarding tour (and its telemetry)."),
        FirefoxPref("browser.discovery.enabled", False, Tier.STANDARD),
        FirefoxPref("browser.newtabpage.activity-stream.showSponsored", False, Tier.STANDARD),
        FirefoxPref("browser.newtabpage.activity-stream.showSponsoredTopSites", False, Tier.STANDARD),
        FirefoxPref("browser.newtabpage.activity-stream.feeds.section.topstories", False, Tier.STANDARD),
        FirefoxPref("browser.newtabpage.activity-stream.feeds.system.topstories", False, Tier.STANDARD),
        FirefoxPref("extensions.getAddons.showPane", False, Tier.STANDARD),
        FirefoxPref("extensions.webservice.discoverURL", "", Tier.STANDARD),
        FirefoxPref("extensions.pocket.enabled", False, Tier.STANDARD),
        FirefoxPref("extensions.htmlaboutaddons.recommendations.enabled", False, Tier.STANDARD),
        FirefoxPref("browser.region.network.url", "", Tier.STANDARD,
                    "Do not phone home to guess your region."),
        FirefoxPref("browser.region.update.enabled", False, Tier.STANDARD),
        FirefoxPref("browser.search.suggest.enabled", False, Tier.STRICT),
        FirefoxPref("browser.urlbar.suggest.searches", False, Tier.STRICT),
        FirefoxPref("browser.urlbar.speculativeConnect.enabled", False, Tier.STANDARD),
        FirefoxPref("browser.urlbar.trimURLs", False, Tier.STANDARD,
                    "Show the full URL so homograph tricks are visible."),
        FirefoxPref("keyword.enabled", False, Tier.PARANOID,
                    "Stop the address bar from turning typos into searches."),
        FirefoxPref("network.prefetch-next", False, Tier.STANDARD),
        FirefoxPref("network.dns.disablePrefetch", True, Tier.STANDARD),
        FirefoxPref("network.dns.disablePrefetchFromHTTPS", True, Tier.STANDARD),
        FirefoxPref("network.predictor.enabled", False, Tier.STANDARD),
        FirefoxPref("network.predictor.enable-prefetch", False, Tier.STANDARD),
        FirefoxPref("network.http.speculative-parallel-limit", 0, Tier.STANDARD),
        FirefoxPref("network.connectivity-service.enabled", False, Tier.STRICT),
        FirefoxPref("network.captive-portal-service.enabled", False, Tier.STRICT),
        FirefoxPref("app.normandy.enabled", False, Tier.STANDARD),
        FirefoxPref("app.shield.optoutstudies.enabled", False, Tier.STANDARD),
        FirefoxPref("browser.tabs.crashReporting.sendReport", False, Tier.STANDARD),
        FirefoxPref("browser.crashReports.unsubmittedCheck.autoSubmit2", False, Tier.STANDARD),
        FirefoxPref("signon.rememberSignons", False, Tier.STRICT),
        FirefoxPref("browser.formfill.enable", False, Tier.STRICT),
        FirefoxPref("identity.fxaccounts.enabled", False, Tier.STRICT,
                    "Do not sign into a Mozilla account from a hardened profile."),
    ),
    flags=(
        ChromiumFlag("--no-first-run", Tier.STANDARD),
        ChromiumFlag("--no-default-browser-check", Tier.STANDARD),
        ChromiumFlag("--disable-sync", Tier.STANDARD),
        ChromiumFlag("--disable-features=ChromeWhatsNewUI", Tier.STANDARD),
        ChromiumFlag("--no-service-autorun", Tier.STRICT),
    ),
)
