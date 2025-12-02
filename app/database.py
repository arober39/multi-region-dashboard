"""
Database Connection Management

Provides async PostgreSQL connections using asyncpg.
Handles connection pooling and health metrics for multi-region setup.
"""
import asyncio
import time
from dataclasses import dataclass
from typing import Optional

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False

from app.config import REGIONS, DEFAULTS


# =============================================================
# DATA CLASSES
# =============================================================

@dataclass
class ConnectionResult:
    """Result from a connection test"""
    success: bool
    latency_ms: float = 0.0
    server_ip: str = ""
    server_port: int = 0
    backend_pid: int = 0
    database: str = ""
    pg_version: str = ""
    error: str = ""


@dataclass
class HealthMetrics:
    """Health metrics from a database"""
    cache_hit_ratio: float = 0.0
    active_connections: int = 0
    max_connections: int = 0
    db_size_mb: float = 0.0


@dataclass
class LoadTestResult:
    """Results from a concurrent load test"""
    concurrent: int
    min_ms: float
    max_ms: float
    avg_ms: float
    results: list[float]


# =============================================================
# DATABASE MANAGER
# =============================================================

class DatabaseManager:
    """
    Manages database connection pools for all regions.
    """

    def __init__(self):
        self._pools: dict[str, asyncpg.Pool] = {}

    async def initialize(self):
        """Initialize connection pools for all configured regions."""
        if not ASYNCPG_AVAILABLE:
            print("⚠️  asyncpg not available - database connections disabled")
            return

        for region_id, config in REGIONS.items():
            if config.dsn:
                try:
                    pool = await asyncpg.create_pool(
                        config.dsn,
                        min_size=1,
                        max_size=10,
                        command_timeout=DEFAULTS["query_timeout"]
                    )
                    self._pools[region_id] = pool
                    print(f"✅ Connected to {config.name}")
                except Exception as e:
                    print(f"❌ Failed to connect to {config.name}: {e}")
            else:
                print(f"⚠️  No DSN configured for {config.name}")

    async def close(self):
        """Close all connection pools."""
        for region_id, pool in self._pools.items():
            await pool.close()
            print(f"✅ Closed pool for {REGIONS[region_id].name}")
        self._pools.clear()

    def get_pool(self, region_id: str) -> Optional[asyncpg.Pool]:
        """Get the connection pool for a region."""
        return self._pools.get(region_id)


# Global database manager instance
db_manager = DatabaseManager()


# =============================================================
# CONNECTION TESTING
# =============================================================

async def test_connection(region_id: str) -> ConnectionResult:
    """
    Test connection to a specific region and measure latency.
    """
    pool = db_manager.get_pool(region_id)

    if not pool:
        return ConnectionResult(
            success=False,
            error="No connection pool available"
        )

    try:
        start = time.perf_counter()

        async with pool.acquire() as conn:
            # Get connection info
            row = await conn.fetchrow("""
                SELECT
                    inet_server_addr() as server_ip,
                    inet_server_port() as server_port,
                    pg_backend_pid() as backend_pid,
                    current_database() as database,
                    version() as pg_version
            """)

            latency_ms = (time.perf_counter() - start) * 1000

            return ConnectionResult(
                success=True,
                latency_ms=round(latency_ms, 2),
                server_ip=str(row['server_ip']) if row['server_ip'] else "",
                server_port=row['server_port'] or 0,
                backend_pid=row['backend_pid'] or 0,
                database=row['database'] or "",
                pg_version=row['pg_version'] or ""
            )

    except Exception as e:
        return ConnectionResult(
            success=False,
            error=str(e)
        )


# =============================================================
# HEALTH METRICS
# =============================================================

async def get_health_metrics(region_id: str) -> Optional[HealthMetrics]:
    """
    Fetch health metrics from a database.
    """
    pool = db_manager.get_pool(region_id)

    if not pool:
        return None

    try:
        async with pool.acquire() as conn:
            # Cache hit ratio
            cache_row = await conn.fetchrow("""
                SELECT
                    CASE
                        WHEN blks_hit + blks_read = 0 THEN 0
                        ELSE round(100.0 * blks_hit / (blks_hit + blks_read), 2)
                    END as cache_hit_ratio
                FROM pg_stat_database
                WHERE datname = current_database()
            """)

            # Connection counts
            conn_row = await conn.fetchrow("""
                SELECT
                    (SELECT count(*) FROM pg_stat_activity) as active_connections,
                    (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') as max_connections
            """)

            # Database size
            size_row = await conn.fetchrow("""
                SELECT pg_database_size(current_database()) / 1024.0 / 1024.0 as db_size_mb
            """)

            return HealthMetrics(
                cache_hit_ratio=float(cache_row['cache_hit_ratio'] or 0),
                active_connections=conn_row['active_connections'] or 0,
                max_connections=conn_row['max_connections'] or 0,
                db_size_mb=round(float(size_row['db_size_mb'] or 0), 2)
            )

    except Exception as e:
        print(f"Error fetching health metrics: {e}")
        return None


# =============================================================
# LOAD TESTING
# =============================================================

async def run_load_test(region_id: str, concurrent: int = 10) -> Optional[LoadTestResult]:
    """
    Run concurrent connection tests to measure performance under load.
    """
    pool = db_manager.get_pool(region_id)

    if not pool:
        return None

    async def single_query():
        """Execute a single query and return latency in ms."""
        start = time.perf_counter()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return (time.perf_counter() - start) * 1000

    try:
        # Run concurrent queries
        tasks = [single_query() for _ in range(concurrent)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_results = [r for r in results if isinstance(r, (int, float))]

        if not valid_results:
            return None

        return LoadTestResult(
            concurrent=concurrent,
            min_ms=round(min(valid_results), 2),
            max_ms=round(max(valid_results), 2),
            avg_ms=round(sum(valid_results) / len(valid_results), 2),
            results=[round(r, 2) for r in valid_results]
        )

    except Exception as e:
        print(f"Error in load test: {e}")
        return None
