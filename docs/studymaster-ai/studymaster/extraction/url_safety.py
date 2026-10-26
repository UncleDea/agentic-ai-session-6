"""Decide whether a web address is safe to open.

A safe address uses http or https and points only at public internet hosts.
Local, private, and cloud-metadata addresses are rejected before any download.
"""

import ipaddress
import socket
from collections.abc import Callable
from urllib.parse import urlparse

from studymaster.extraction.errors import UnsafeUrlError

Resolver = Callable[[str], list[str]]

_BLOCKED_HOSTS = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
}


def assert_safe_url(url: str, *, resolve: Resolver | None = None) -> str:
    """Return the host when the address is safe.

    Raise UnsafeUrlError when it is not. The resolver is used for host names.
    Tests pass their own resolver so they do not use public DNS.
    """
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeUrlError("This address cannot be opened.")
    if parsed.username or parsed.password:
        raise UnsafeUrlError("This address cannot be opened.")
    host = parsed.hostname
    if not host:
        raise UnsafeUrlError("This address cannot be opened.")
    host = host.lower().rstrip(".")
    if host in _BLOCKED_HOSTS or host.endswith(".localhost"):
        raise UnsafeUrlError("This address cannot be opened.")

    literal = _literal_address(host)
    if literal is not None:
        _reject_blocked(literal)
        return host

    lookup = resolve or resolve_public_host
    try:
        addresses = lookup(host)
    except UnsafeUrlError:
        raise
    except OSError as exc:
        raise UnsafeUrlError("This address cannot be opened.") from exc
    if not addresses:
        raise UnsafeUrlError("This address cannot be opened.")
    for address in addresses:
        _reject_blocked(_parse_ip(address))
    return host


def resolve_public_host(host: str) -> list[str]:
    """Resolve a host name to IP addresses."""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise UnsafeUrlError("This address cannot be opened.") from exc
    return [info[4][0] for info in infos]


def _literal_address(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        pass
    if host.isdigit():
        number = int(host)
        if 0 <= number <= 0xFFFFFFFF:
            return ipaddress.IPv4Address(number)
    return None


def _parse_ip(address: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    try:
        return ipaddress.ip_address(address)
    except ValueError as exc:
        raise UnsafeUrlError("This address cannot be opened.") from exc


def _reject_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        _reject_blocked(ip.ipv4_mapped)
        return
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        raise UnsafeUrlError("This address cannot be opened.")
