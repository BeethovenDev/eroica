"""The network layer: SOCKS routing and exit-IP verification.

Browser hardening protects the *profile identity* — what a website sees inside
the browser. The *network identity* (your real IP) is a separate layer that only
Tor or a VPN can provide. This module lives at that seam:

- parses the configured SOCKS proxy (``eroica proxy`` / ``eroica tor``);
- builds the proxy directives that hardening must write into the profile so the
  browser cannot silently bypass the tunnel (DNS stays inside it as well);
- probes what the public internet actually sees through that tunnel
  (``eroica check-ip``) using a minimal, dependency-free SOCKS5 client.

Honesty first: this module does not invent anonymity. It only makes sure that
when you route through a proxy you *know* what the world sees.
"""

from __future__ import annotations

import socket
import ssl
import urllib.request
from contextlib import suppress
from dataclasses import dataclass
from urllib.error import URLError

from eroica import __version__, log
from eroica.config import Config, Tier
from eroica.errors import ConfigError, NetworkError
from eroica.symphonies.base import ChromiumFlag, FirefoxPref

_log = log.get_logger("net")

__all__ = [
    "IP_MIRROR",
    "TOR_DEFAULT",
    "ProbeResult",
    "ProxySetting",
    "parse_proxy",
    "probe_network",
    "proxy_chromium_flags",
    "proxy_firefox_prefs",
]

#: Standard Tor SOCKS endpoint (standalone Tor or Tor Browser).
TOR_DEFAULT = "socks5://127.0.0.1:9050"

#: Plain-text HTTPS echo that answers with the caller's IP address.
IP_MIRROR = "api.ipify.org"

#: Cap on a single probe response, to keep the client trivially bounded.
_MAX_BODY = 1 << 20

_SOCKS_ERRORS = {
    1: "general failure",
    2: "connection not allowed by ruleset",
    3: "network unreachable",
    4: "host unreachable",
    5: "connection refused",
    6: "TTL expired",
    7: "command not supported",
    8: "address type not supported",
}


@dataclass(frozen=True)
class ProxySetting:
    """A parsed SOCKS proxy."""

    scheme: str  # always "socks5" (socks5h is normalised to it)
    host: str
    port: int

    def as_url(self) -> str:
        return f"{self.scheme}://{self.host}:{self.port}"


def parse_proxy(raw: str | None) -> ProxySetting | None:
    """Parse and validate a proxy URL.

    ``None``, empty, ``"off"`` and ``"none"`` all mean "no proxy". Only
    ``socks5://`` is supported (a scheme that inherently routes DNS through the
    proxy, so Tor-style setups never leak hostnames to the ISP).
    """
    if raw is None:
        return None
    value = raw.strip()
    if not value or value.lower() in {"off", "none"}:
        return None
    scheme, _, rest = value.partition("://")
    lscheme = scheme.lower()
    if lscheme == "socks5h":
        lscheme = "socks5"
    if lscheme != "socks5":
        raise ConfigError(f"unsupported proxy scheme {scheme!r}; use socks5://host:port")
    host, _, port_s = rest.partition(":")
    if not host or not port_s.isdigit() or not (0 < int(port_s) < 65536):
        raise ConfigError(f"invalid proxy {value!r}; expected socks5://host:port")
    return ProxySetting(scheme=lscheme, host=host, port=int(port_s))


def proxy_firefox_prefs(proxy: ProxySetting) -> tuple[FirefoxPref, ...]:
    """The ``user.js`` directives that route Firefox through ``proxy``.

    Notably ``network.proxy.socks_remote_dns`` forces DNS into the tunnel and
    ``network.trr.mode = 5`` switches DNS-over-HTTPS off: with a proxy active,
    DoH would otherwise resolve outside the tunnel and defeat the whole point.
    """
    return (
        FirefoxPref("network.proxy.type", 1, Tier.STANDARD,
                    "Manual proxy configuration."),
        FirefoxPref("network.proxy.socks", proxy.host, Tier.STANDARD),
        FirefoxPref("network.proxy.socks_port", proxy.port, Tier.STANDARD),
        FirefoxPref("network.proxy.socks_version", 5, Tier.STANDARD),
        FirefoxPref("network.proxy.socks_remote_dns", True, Tier.STANDARD,
                    "Resolve DNS through the proxy so hostnames stay hidden."),
        FirefoxPref("network.proxy.share_proxy_settings", True, Tier.STANDARD,
                    "Route HTTP and HTTPS through SOCKS as well."),
        FirefoxPref("network.proxy.no_proxies_on", "", Tier.STANDARD),
        FirefoxPref("network.trr.mode", 5, Tier.STANDARD,
                    "DoH is off in proxy mode: DNS must not bypass the tunnel."),
    )


def proxy_chromium_flags(proxy: ProxySetting) -> tuple[ChromiumFlag, ...]:
    """Chromium launch flags that route every request through ``proxy``.

    ``--host-resolver-rules`` with ``MAP * ~NOTFOUND`` forces the network
    service to resolve names *through* the SOCKS proxy instead of locally, and
    DoH is explicitly disabled — both so DNS cannot leak around the tunnel.
    """
    return (
        ChromiumFlag(f"--proxy-server={proxy.as_url()}", Tier.STANDARD,
                     "Route all traffic through the SOCKS proxy."),
        ChromiumFlag("--host-resolver-rules=MAP * ~NOTFOUND , EXCLUDE localhost",
                     Tier.STANDARD,
                     "Force DNS through the SOCKS proxy; never resolve locally."),
        ChromiumFlag("--disable-features=DnsOverHttps", Tier.STANDARD,
                     "DoH is off in proxy mode: DNS must not bypass the tunnel."),
    )


def probe_network(config: Config, *, timeout: float = 10.0) -> ProbeResult:
    """Ask the public internet what IPs it sees, directly and via the proxy.

    Returns a :class:`ProbeResult`; network hiccups surface as fields rather
    than exceptions, so the CLI can report them honestly.
    """
    proxy = parse_proxy(config.proxy)
    direct = _fetch_direct(timeout=timeout)
    exit_ip: str | None = None
    error: str | None = None
    if proxy is not None:
        exit_ip, error = _fetch_via_proxy(proxy, timeout=timeout)
    reachable = bool(exit_ip) if proxy is not None else bool(direct)
    _log.debug(
        "probe: proxy=%s direct=%s exit=%s reachable=%s error=%s",
        config.proxy, direct, exit_ip, reachable, error,
    )
    return ProbeResult(
        proxy=config.proxy,
        direct_ip=direct,
        exit_ip=exit_ip,
        reachable=reachable,
        error=error,
    )


# --------------------------------------------------------------------------- #
# Internal probe machinery
# --------------------------------------------------------------------------- #
def _recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        chunk = sock.recv(size - len(chunks))
        if not chunk:
            raise NetworkError("proxy closed the connection mid-handshake")
        chunks.extend(chunk)
    return bytes(chunks)


def _socks5_connect(
    proxy: ProxySetting, host: str, port: int, *, timeout: float
) -> socket.socket:
    """Open a raw TCP tunnel to ``host:port`` through a SOCKS5 proxy.

    Implements RFC 1928 with the no-authentication method (standalone Tor,
    Tor Browser and most tunnel endpoints need nothing stronger).
    """
    sock: socket.socket | None = None
    try:
        sock = socket.create_connection((proxy.host, proxy.port), timeout=timeout)
        sock.settimeout(timeout)
        sock.sendall(b"\x05\x01\x00")  # version 5, one offered method: no-auth
        version, method = _recv_exact(sock, 2)
        if version != 0x05:
            raise NetworkError("proxy replied with an unknown SOCKS version")
        if method == 0xFF:
            raise NetworkError(
                "proxy requires authentication; only no-auth SOCKS5 is supported"
            )
        if method != 0x00:
            raise NetworkError(f"proxy refused the negotiation (method {method})")

        host_bytes = host.encode("idna")
        request = (
            b"\x05\x01\x00\x03"
            + bytes([len(host_bytes)])
            + host_bytes
            + port.to_bytes(2, "big")
        )
        sock.sendall(request)
        head = _recv_exact(sock, 4)
        if head[0] != 0x05:
            raise NetworkError("proxy sent an invalid CONNECT reply")
        if head[1] != 0x00:
            reason = _SOCKS_ERRORS.get(head[1], f"code {head[1]}")
            raise NetworkError(f"SOCKS CONNECT to {host}:{port} failed: {reason}")
        atyp = head[3]
        if atyp == 0x01:  # IPv4
            _recv_exact(sock, 6)
        elif atyp == 0x03:  # domain name
            length = _recv_exact(sock, 1)[0]
            _recv_exact(sock, length + 2)
        elif atyp == 0x04:  # IPv6
            _recv_exact(sock, 18)
        else:
            raise NetworkError(f"proxy returned unexpected address type {atyp}")
        return sock
    except NetworkError:
        if sock is not None:
            with suppress(OSError):
                sock.close()
        raise
    except OSError as exc:
        if sock is not None:
            with suppress(OSError):
                sock.close()
        raise NetworkError(f"could not reach proxy {proxy.as_url()}: {exc}") from exc


def _fetch_via_proxy(
    proxy: ProxySetting, *, timeout: float
) -> tuple[str | None, str | None]:
    """Return ``(exit_ip, error)`` seen through ``proxy``.

    Any network hiccup (proxy down, tunnel refused, TLS failure) is converted
    into ``(None, message)`` so :func:`probe_network` can report it honestly.
    """
    sock: socket.socket | None = None
    try:
        sock = _socks5_connect(proxy, IP_MIRROR, 443, timeout=timeout)
        context = ssl.create_default_context()
        tls = context.wrap_socket(sock, server_hostname=IP_MIRROR)
        tls.settimeout(timeout)
        request = (
            f"GET / HTTP/1.1\r\n"
            f"Host: {IP_MIRROR}\r\n"
            f"User-Agent: eroica/{__version__}\r\n"
            "Accept: text/plain\r\n"
            "Connection: close\r\n\r\n"
        )
        tls.sendall(request.encode("ascii"))
        raw = bytearray()
        while len(raw) <= _MAX_BODY:
            chunk = tls.recv(65536)
            if not chunk:
                break
            raw.extend(chunk)
        tls.close()
        head, sep, body = bytes(raw).partition(b"\r\n\r\n")
        if not sep:
            return None, "mirror sent a malformed HTTP response"
        tokens = head.split(b" ", 2)
        if len(tokens) < 2 or tokens[1] != b"200":
            status = tokens[1].decode("ascii", "replace") if len(tokens) > 1 else "?"
            return None, f"mirror returned HTTP {status}"
        ip = body.decode("utf-8", "replace").strip()
        return ip or None, None
    except NetworkError as exc:
        return None, str(exc)
    except OSError as exc:
        return None, str(exc)
    finally:
        if sock is not None:
            with suppress(OSError):  # pragma: no cover - already closed by TLS
                sock.close()


def _fetch_direct(*, timeout: float) -> str | None:
    """The machine's own public IP, bypassing any environment proxies."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f"https://{IP_MIRROR}/", timeout=timeout) as response:
            if response.status != 200:
                return None
            body = response.read(_MAX_BODY).decode("utf-8", "replace").strip()
            return body or None
    except (URLError, OSError, ValueError) as exc:
        _log.debug("direct probe failed: %s", exc)
        return None


@dataclass
class ProbeResult:
    """What the public internet sees, from the machine and from the proxy."""

    #: The configured proxy URL, or ``None`` when traffic is direct.
    proxy: str | None
    #: The machine's own public IP (no proxy). ``None`` when unreachable.
    direct_ip: str | None
    #: The IP the proxy exits on (``None`` without a proxy or unreachable).
    exit_ip: str | None
    #: ``True`` when the relevant path (proxy or direct) was reachable.
    reachable: bool
    #: A human-readable probe error, when one of the probes failed.
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "proxy": self.proxy,
            "direct_ip": self.direct_ip,
            "exit_ip": self.exit_ip,
            "reachable": self.reachable,
            "error": self.error,
        }