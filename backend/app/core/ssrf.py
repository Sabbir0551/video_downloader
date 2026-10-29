import ipaddress
import socket
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from app.core.config import settings
from app.core.errors import SSRFValidationError

# Comprehensive list of private, loopback, link-local, and reserved network ranges
FORBIDDEN_NETWORKS: List[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
    # IPv4 Private / Loopback / Link-local / Test / Multicast / Reserved
    ipaddress.ip_network("0.0.0.0/8"),          # Current network (only valid as source)
    ipaddress.ip_network("10.0.0.0/8"),         # Private-Use (RFC 1918)
    ipaddress.ip_network("100.64.0.0/10"),      # Shared Address Space (RFC 6598 - Carrier-grade NAT)
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback (RFC 1122)
    ipaddress.ip_network("169.254.0.0/16"),     # Link-Local / Cloud Metadata (RFC 3927)
    ipaddress.ip_network("172.16.0.0/12"),      # Private-Use (RFC 1918)
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments (RFC 6890)
    ipaddress.ip_network("192.0.2.0/24"),       # Documentation (TEST-NET-1)
    ipaddress.ip_network("192.88.99.0/24"),     # 6to4 Relay Anycast (RFC 7526)
    ipaddress.ip_network("192.168.0.0/16"),     # Private-Use (RFC 1918)
    ipaddress.ip_network("198.18.0.0/15"),      # Benchmarking (RFC 2544)
    ipaddress.ip_network("198.51.100.0/24"),    # Documentation (TEST-NET-2)
    ipaddress.ip_network("203.0.113.0/24"),     # Documentation (TEST-NET-3)
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast (RFC 5771)
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved for future use (RFC 1112)
    ipaddress.ip_network("255.255.255.255/32"), # Limited Broadcast

    # IPv6 Loopback / Link-local / Unique Local / Documentation / IPv4-mapped
    ipaddress.ip_network("::1/128"),            # Loopback
    ipaddress.ip_network("::/128"),             # Unspecified
    ipaddress.ip_network("fc00::/7"),           # Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),          # Link-Local Unicast
    ipaddress.ip_network("2001:db8::/32"),      # Documentation
    ipaddress.ip_network("ff00::/8"),           # Multicast
    ipaddress.ip_network("::ffff:0:0/96"),      # IPv4-mapped IPv6
]


def is_ip_forbidden(ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check if an IP address belongs to any forbidden or private CIDR blocks."""
    # Special case: check IPv4-mapped IPv6 addresses (e.g. ::ffff:127.0.0.1)
    if isinstance(ip_obj, ipaddress.IPv6Address) and ip_obj.ipv4_mapped:
        ip_obj = ip_obj.ipv4_mapped

    for network in FORBIDDEN_NETWORKS:
        if ip_obj in network:
            return True

    # Standard library properties fallback
    if (
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_multicast
        or ip_obj.is_reserved
        or ip_obj.is_unspecified
    ):
        return True

    return False


def resolve_hostname_ips(hostname: str) -> List[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """
    Resolve a hostname into all its assigned IPv4 and IPv6 addresses.
    Returns an empty list or raises SSRFValidationError if resolution fails.
    """
    try:
        # getaddrinfo resolves both A and AAAA records
        addr_info = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
        resolved_ips = []
        for item in addr_info:
            sockaddr = item[4]
            ip_str = sockaddr[0]
            try:
                resolved_ips.append(ipaddress.ip_address(ip_str))
            except ValueError:
                continue
        return resolved_ips
    except socket.gaierror as err:
        raise SSRFValidationError(
            message=f"Unable to resolve host: {hostname}",
            details={"hostname": hostname, "error": str(err)},
        )


def validate_url_security(raw_url: str) -> Tuple[str, str]:
    """
    Validates a URL against SSRF, dangerous protocols, and private destination attacks.

    Returns:
        Tuple of (clean_url, hostname)

    Raises:
        SSRFValidationError: If URL scheme or destination is forbidden.
    """
    if not raw_url or not isinstance(raw_url, str):
        raise SSRFValidationError(message="URL must be a non-empty string.")

    raw_url = raw_url.strip()
    parsed = urlparse(raw_url)

    # 1. Scheme check
    scheme = parsed.scheme.lower()
    if scheme not in settings.ALLOWED_SCHEMES:
        raise SSRFValidationError(
            message=f"Invalid URL protocol '{scheme}'. Only http and https are permitted.",
            details={"allowed_schemes": settings.ALLOWED_SCHEMES},
        )

    # 2. Hostname extraction
    hostname = parsed.hostname
    if not hostname:
        raise SSRFValidationError(message="URL missing valid hostname.")

    hostname_lower = hostname.lower()

    # 3. Denylist check
    if hostname_lower in settings.DENYLISTED_DOMAINS:
        raise SSRFValidationError(
            message=f"Access to host '{hostname}' is denied by security policy.",
            details={"hostname": hostname},
        )

    # 4. Optional Allowlist check
    if settings.ALLOWLISTED_DOMAINS:
        matched = any(
            hostname_lower == domain or hostname_lower.endswith(f".{domain}")
            for domain in settings.ALLOWLISTED_DOMAINS
        )
        if not matched:
            raise SSRFValidationError(
                message=f"Domain '{hostname}' is not in the allowed domain list.",
                details={"hostname": hostname},
            )

    # 5. Check if host is direct IP literal
    try:
        ip_obj = ipaddress.ip_address(hostname_lower)
        if is_ip_forbidden(ip_obj):
            raise SSRFValidationError(
                message="Access to internal, loopback, or private IP addresses is prohibited.",
                details={"ip": str(ip_obj)},
            )
        return raw_url, hostname_lower
    except ValueError:
        # Host is a domain name, proceed with DNS resolution
        pass

    # 6. Resolve domain and check all associated IP addresses
    resolved_ips = resolve_hostname_ips(hostname_lower)
    if not resolved_ips:
        raise SSRFValidationError(
            message=f"Domain '{hostname}' did not resolve to any IP address.",
            details={"hostname": hostname},
        )

    for ip_obj in resolved_ips:
        if is_ip_forbidden(ip_obj):
            raise SSRFValidationError(
                message=f"Domain '{hostname}' resolves to a restricted or private IP destination.",
                details={"hostname": hostname, "restricted_ip": str(ip_obj)},
            )

    return raw_url, hostname_lower

