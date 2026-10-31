import ipaddress
import pytest

from app.core.errors import SSRFValidationError
from app.core.ssrf import is_ip_forbidden, validate_url_security


def test_forbidden_ipv4_addresses():
    """Verify private, loopback, link-local, and reserved IPv4 ranges are blocked."""
    forbidden_ips = [
        "127.0.0.1",
        "127.0.1.1",
        "10.0.0.1",
        "10.254.254.254",
        "172.16.0.1",
        "172.31.255.255",
        "192.168.0.1",
        "192.168.1.100",
        "169.254.169.254",  # AWS/GCP/Azure metadata
        "169.254.1.1",
        "100.64.0.1",       # Carrier-grade NAT
        "0.0.0.0",
        "224.0.0.1",        # Multicast
        "255.255.255.255",  # Broadcast
    ]
    for ip_str in forbidden_ips:
        ip_obj = ipaddress.ip_address(ip_str)
        assert is_ip_forbidden(ip_obj) is True, f"Failed to identify {ip_str} as forbidden"


def test_forbidden_ipv6_addresses():
    """Verify IPv6 loopback, link-local, and mapped IPv4 addresses are blocked."""
    forbidden_ipv6 = [
        "::1",
        "::",
        "fe80::1",
        "fc00::1",
        "::ffff:127.0.0.1",
        "::ffff:169.254.169.254",
    ]
    for ip_str in forbidden_ipv6:
        ip_obj = ipaddress.ip_address(ip_str)
        assert is_ip_forbidden(ip_obj) is True, f"Failed to identify IPv6 {ip_str} as forbidden"


def test_public_ip_addresses_allowed():
    """Verify legitimate public IPv4 addresses are permitted."""
    public_ips = [
        "8.8.8.8",
        "1.1.1.1",
        "142.250.190.46",  # Google
        "104.244.42.1",    # Twitter
    ]
    for ip_str in public_ips:
        ip_obj = ipaddress.ip_address(ip_str)
        assert is_ip_forbidden(ip_obj) is False, f"Erroneously identified public IP {ip_str} as forbidden"


def test_validate_url_schemes():
    """Verify non-HTTP schemes are rejected."""
    invalid_schemes = [
        "file:///etc/passwd",
        "ftp://example.com/video.mp4",
        "gopher://example.com",
        "dict://example.com",
        "javascript:alert(1)",
        "data:text/plain;base64,SGVsbG8=",
    ]
    for url in invalid_schemes:
        with pytest.raises(SSRFValidationError):
            validate_url_security(url)


def test_validate_url_direct_private_ip():
    """Verify direct private IP URLs are blocked."""
    blocked_urls = [
        "http://127.0.0.1/admin",
        "http://169.254.169.254/latest/meta-data/",
        "http://192.168.1.1/router",
        "http://10.0.0.5:8080/internal",
        "http://[::1]/",
        "http://localhost:8000/",
        "http://metadata.google.internal/computeMetadata/v1/",
    ]
    for url in blocked_urls:
        with pytest.raises(SSRFValidationError):
            validate_url_security(url)


def test_validate_valid_public_domain(monkeypatch):
    """Verify public URLs resolve and pass validation."""
    # Mock DNS resolution to simulate a public destination without actual network calls
    def mock_resolve(hostname: str):
        return [ipaddress.ip_address("142.250.190.46")]

    monkeypatch.setattr("app.core.ssrf.resolve_hostname_ips", mock_resolve)

    clean_url, host = validate_url_security("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert clean_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert host == "www.youtube.com"


def test_dns_rebinding_to_private_ip(monkeypatch):
    """Verify that if a domain resolves to a private IP, it is blocked immediately."""
    def mock_resolve(hostname: str):
        # Malicious DNS returning private IP
        return [ipaddress.ip_address("192.168.1.50")]

    monkeypatch.setattr("app.core.ssrf.resolve_hostname_ips", mock_resolve)

    with pytest.raises(SSRFValidationError) as exc_info:
        validate_url_security("https://attacker-controlled-domain.com/video")
    assert "resolves to a restricted or private IP destination" in exc_info.value.message


def test_ipv6_edge_cases_6to4_nat64_teredo():
    """Verify IPv6 edge cases including 6to4, NAT64, and Teredo are blocked."""
    edge_cases = [
        "2002:c0a8:0101::1",  # 6to4 embedding 192.168.1.1
        "2002:7f00:0001::",   # 6to4 embedding 127.0.0.1
        "64:ff9b::127.0.0.1", # NAT64 embedding 127.0.0.1
        "64:ff9b::10.0.0.1",  # NAT64 embedding 10.0.0.1
        "2001:0000:4136:e378:8000:63bf:3fff:fdd2", # Teredo
    ]
    for ip_str in edge_cases:
        ip_obj = ipaddress.ip_address(ip_str)
        assert is_ip_forbidden(ip_obj) is True, f"Failed to identify {ip_str} as forbidden"


def test_safe_network_guard_intercepts_dns_rebinding_and_redirects():
    """Verify safe_network_guard raises SSRFValidationError when connection attempts loopback/private."""
    import socket
    from app.core.ssrf import safe_network_guard

    with safe_network_guard():
        # Attempting to resolve loopback host inside guard
        with pytest.raises(SSRFValidationError) as exc:
            socket.getaddrinfo("127.0.0.1", 80)
        assert "SSRF TOCTOU Guard" in exc.value.message

        # Attempting to connect to loopback inside guard
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            with pytest.raises(SSRFValidationError) as exc:
                s.connect(("127.0.0.1", 80))
            assert "SSRF Connection Guard" in exc.value.message
        finally:
            s.close()


