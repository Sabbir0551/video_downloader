import os
from functools import lru_cache
from typing import Dict, List, Optional
from urllib.parse import urlparse
import yaml
from pydantic import BaseModel, Field


class PlatformMetadata(BaseModel):
    id: str
    name: str
    domains: List[str]
    category: str
    tier: str  # supported, best_effort, unsupported_no_video, login_or_paid, defunct
    status: str = "active"  # active, blocked_by_policy, deprecated, defunct
    has_public_video: bool = True
    requires_login: bool = False
    supports_audio_only: bool = True
    max_quality_expected: str = "1080p"  # 4k, 1080p, 720p, none
    per_platform_concurrency: int = 20
    per_platform_rate_limit: str = "60/m"
    notes: Optional[str] = None
    extractor_keys: List[str] = Field(default_factory=list)


class PlatformRegistryData(BaseModel):
    version: str
    last_verified: str
    ytdlp_version: str
    total_platforms: int
    tiers_summary: Dict[str, int]
    platforms: List[PlatformMetadata]


class PlatformRegistry:
    """
    In-memory registry loaded from registry.yaml.
    Provides fast O(1) domain lookup, URL canonicalization, and tier gating.
    """

    def __init__(self, yaml_path: Optional[str] = None):
        if not yaml_path:
            yaml_path = os.path.join(os.path.dirname(__file__), "registry.yaml")
        self.yaml_path = yaml_path
        self._data: Optional[PlatformRegistryData] = None
        self._domain_index: Dict[str, PlatformMetadata] = {}
        self.load()

    def load(self) -> None:
        if not os.path.exists(self.yaml_path):
            raise FileNotFoundError(f"Platform registry YAML not found at {self.yaml_path}")

        with open(self.yaml_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        self._data = PlatformRegistryData(**raw)
        self._domain_index.clear()

        # Build fast domain lookup index
        for platform in self._data.platforms:
            for domain in platform.domains:
                clean_dom = domain.lower().strip()
                self._domain_index[clean_dom] = platform

    @property
    def data(self) -> PlatformRegistryData:
        if not self._data:
            self.load()
        return self._data  # type: ignore

    def get_all(self, tier: Optional[str] = None) -> List[PlatformMetadata]:
        all_platforms = self.data.platforms
        if tier:
            return [p for p in all_platforms if p.tier == tier]
        return all_platforms

    def get_by_id(self, platform_id: str) -> Optional[PlatformMetadata]:
        for p in self.data.platforms:
            if p.id == platform_id:
                return p
        return None

    def find_by_domain(self, domain: str) -> Optional[PlatformMetadata]:
        domain = domain.lower().strip()
        if domain in self._domain_index:
            return self._domain_index[domain]

        # Check subdomains (e.g. m.facebook.com -> facebook.com)
        parts = domain.split(".")
        for i in range(1, len(parts) - 1):
            parent = ".".join(parts[i:])
            if parent in self._domain_index:
                return self._domain_index[parent]

        return None

    def find_by_url(self, url: str) -> Optional[PlatformMetadata]:
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or ""
            return self.find_by_domain(hostname)
        except Exception:
            return None


@lru_cache(maxsize=1)
def get_platform_registry() -> PlatformRegistry:
    return PlatformRegistry()

