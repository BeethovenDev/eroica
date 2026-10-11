"""Symphony No. 3 in E♭ major, Op. 55 (1804) — "Eroica".

The heroic third is EROICA's namesake: the anti-fingerprinting movement. Its
job is to make the profile look like a boring, extremely common browser so that
distinctive hardware, fonts, canvas output and timing noise stop singling you
out from the crowd.
"""

from __future__ import annotations

from eroica.config import Tier
from eroica.symphonies.base import ChromiumFlag, FirefoxPref, Movement

_T = Tier.STANDARD
_S = Tier.STRICT
_P = Tier.PARANOID

__all__ = ["EROICA"]

EROICA = Movement(
    key="eroica",
    roman="III",
    nickname="Eroica",
    title="Symphony No. 3 in E\u266d major",
    opus="Op. 55",
    year=1804,
    signature="E\u266d major",
    summary="Anti-fingerprinting: resist the signals that identify a device.",
    prefs=(
        FirefoxPref("privacy.resistFingerprinting", True, _T,
                    "The core Tor-Browser-derived anti-fingerprinting mode."),
        FirefoxPref("privacy.resistFingerprinting.letterboxing", True, _S,
                    "Round the viewport to a coarse size to defeat window sizing."),
        FirefoxPref("privacy.resistFingerprinting.autoDeclineNoUserInputCanvasPrompts", True, _T),
        FirefoxPref("privacy.resistFingerprinting.randomDataOnCanvasExtract", True, _S),
        FirefoxPref("privacy.fingerprintingProtection", True, _T,
                    "Firefox's newer, per-target fingerprinting protection."),
        FirefoxPref("privacy.trackingprotection.fingerprinting.enabled", True, _T),
        FirefoxPref("privacy.trackingprotection.cryptomining.enabled", True, _T),
        FirefoxPref("privacy.trackingprotection.socialtracking.enabled", True, _T),
        FirefoxPref("privacy.query_stripping.enabled", True, _S,
                    "Strip known tracking parameters (utm_*, fbclid…) from URLs."),
        FirefoxPref("privacy.query_stripping.enabled.pbmode", True, _S),
        FirefoxPref("dom.battery.enabled", False, _T,
                    "A dead giveaway of platform and power state."),
        FirefoxPref("dom.gamepad.enabled", False, _S),
        FirefoxPref("dom.event.clipboardevents.enabled", False, _S),
        FirefoxPref("dom.webaudio.enabled", False, _P,
                    "AudioContext is a strong fingerprint vector, but breaks audio."),
        FirefoxPref("media.navigator.enabled", False, _S,
                    "Hides the list of available media devices."),
        FirefoxPref("device.sensors.enabled", False, _S),
        FirefoxPref("camera.control.face_detection.enabled", False, _S),
        FirefoxPref("geo.enabled", False, _T),
        FirefoxPref("geo.provider.network.url", "", _P),
        FirefoxPref("webgl.disabled", True, _S,
                    "WebGL leaks GPU fingerprints; disable unless you need it."),
        FirefoxPref("webgl.enable-webgl2", False, _P),
        FirefoxPref("privacy.resistFingerprinting.reduceTimerPrecision.microseconds", 100_000, _S,
                    "Coarsen high-resolution timers used to build side channels."),
        FirefoxPref("privacy.resistFingerprinting.block_mozAddonManager", True, _S),
        FirefoxPref("browser.display.use_document_fonts", 0, _P,
                    "Stop sites from probing which fonts you have installed."),
        FirefoxPref("layout.css.font-visibility.private", 1, _S),
    ),
    flags=(
        ChromiumFlag(
            "--disable-features=InterestFeedContentSuggestions,Translate,MediaRouter,"
            "OptimizationHints,CalculateNativeWinOcclusion,AutofillServerCommunication",
            _T,
        ),
        ChromiumFlag(
            "--disable-features=PrivacySandboxAdsAPIs,TopicsAPI,Fledge,AttributionReporting",
            _S,
            "Turn off the advertising cohort/topic APIs.",
        ),
        ChromiumFlag(
            "--disable-blink-features=IdleDetection",
            _P,
        ),
    ),
)
