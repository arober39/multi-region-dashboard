"""
Feature Flag Integration

Provides runtime control over regions and features.
Includes a DEMO_MODE that simulates flags without needing LaunchDarkly.
"""
import os

# Check if we're in demo mode
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"

# Try to import LaunchDarkly (optional dependency)
try:
    import ldclient
    from ldclient import Context
    from ldclient.config import Config
    LD_AVAILABLE = True
except ImportError:
    LD_AVAILABLE = False

# Global LaunchDarkly client
_ld_client = None

# =============================================================
# DEMO MODE FLAGS
# These simulate LaunchDarkly when DEMO_MODE=true
# =============================================================

_demo_flags = {
    "region-us-east-enabled": True,
    "region-eu-west-enabled": True,
    "region-asia-pacific-enabled": True,
    "enable-health-checks": True,
    "enable-load-testing": True,
    "dashboard-refresh-seconds": 30,
}


# =============================================================
# INITIALIZATION
# =============================================================

def init_launchdarkly():
    """Initialize LaunchDarkly client on app startup"""
    global _ld_client
    
    if DEMO_MODE:
        print("🚩 Running in DEMO MODE - using simulated feature flags")
        return
    
    if not LD_AVAILABLE:
        print("⚠️  LaunchDarkly SDK not installed - using demo flags")
        return
        
    sdk_key = os.getenv("LAUNCHDARKLY_SDK_KEY")
    if not sdk_key:
        print("⚠️  LAUNCHDARKLY_SDK_KEY not set - using demo flags")
        return
    
    _ld_client = ldclient.LDClient(Config(sdk_key))
    if _ld_client.is_initialized():
        print("✅ LaunchDarkly client initialized")
    else:
        print("❌ LaunchDarkly client failed to initialize")


def shutdown_launchdarkly():
    """Cleanup on app shutdown"""
    if _ld_client:
        _ld_client.close()
        print("✅ LaunchDarkly client closed")


# =============================================================
# FLAG EVALUATION
# =============================================================

def is_region_enabled(region_id: str, user_key: str = "anonymous") -> bool:
    """Check if a specific region is enabled"""
    flag_key = f"region-{region_id}-enabled"
    
    # Demo mode - use local flags
    if DEMO_MODE or not _ld_client:
        return _demo_flags.get(flag_key, True)
    
    # Real LaunchDarkly evaluation
    context = Context.builder(user_key).build()
    return _ld_client.variation(flag_key, context, True)


def is_feature_enabled(feature: str, user_key: str = "anonymous") -> bool:
    """Check if a feature is enabled (health checks, load testing, etc.)"""
    flag_key = f"enable-{feature.replace('_', '-')}"
    
    if DEMO_MODE or not _ld_client:
        return _demo_flags.get(flag_key, True)
    
    context = Context.builder(user_key).build()
    return _ld_client.variation(flag_key, context, True)


def get_refresh_interval(user_key: str = "anonymous") -> int:
    """Get dashboard auto-refresh interval in seconds"""
    if DEMO_MODE or not _ld_client:
        return _demo_flags.get("dashboard-refresh-seconds", 30)
    
    context = Context.builder(user_key).build()
    return _ld_client.variation("dashboard-refresh-seconds", context, 30)


# =============================================================
# DEMO MODE HELPERS
# =============================================================

def get_demo_flags() -> dict:
    """Get all demo flag values (for displaying in UI)"""
    return _demo_flags.copy()


def toggle_demo_flag(flag_key: str) -> bool:
    """Toggle a boolean flag in demo mode"""
    if flag_key in _demo_flags and isinstance(_demo_flags[flag_key], bool):
        _demo_flags[flag_key] = not _demo_flags[flag_key]
        return True
    return False


# =============================================================
# FEATURE FLAGS WRAPPER
# =============================================================

class FeatureFlags:
    """Wrapper class for feature flag operations."""

    def close(self):
        """Close the feature flags client."""
        shutdown_launchdarkly()


# Global feature flags instance
feature_flags = FeatureFlags()