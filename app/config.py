"""
Configuration & Region Registry

Each region maps to an Aiven PostgreSQL service.
The DSN (connection string) comes from environment variables.
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class RegionConfig:
    """Configuration for a single database region"""
    name: str           # Human-readable name
    role: str           # PRIMARY or REPLICA
    env_key: str        # Environment variable for connection string
    color: str          # UI color for the region card
    
    @property
    def dsn(self) -> Optional[str]:
        """Get connection string from environment variable"""
        return os.getenv(self.env_key)


# =============================================================
# REGION REGISTRY
# Add your Aiven PostgreSQL regions here
# =============================================================

REGIONS: dict[str, RegionConfig] = {
    "us-east": RegionConfig(
        name="US East (Virginia)",
        role="PRIMARY",
        env_key="AIVEN_PG_US_EAST",
        color="#10b981",  # Emerald green
    ),
    "eu-west": RegionConfig(
        name="EU West (Ireland)", 
        role="REPLICA",
        env_key="AIVEN_PG_EU_WEST",
        color="#3b82f6",  # Blue
    ),
    "asia-pacific": RegionConfig(
        name="Asia Pacific (Singapore)",
        role="REPLICA", 
        env_key="AIVEN_PG_ASIA_PACIFIC",
        color="#f59e0b",  # Amber
    ),
}


# =============================================================
# DEFAULT SETTINGS
# =============================================================

DEFAULTS = {
    "connection_timeout": 10.0,      # Seconds to wait for connection
    "query_timeout": 5.0,            # Seconds to wait for query
    "load_test_concurrent": 10,      # Number of concurrent connections in load test
    "latency_iterations": 5,         # Number of pings to average
    "refresh_seconds": 30,           # Dashboard auto-refresh interval
}