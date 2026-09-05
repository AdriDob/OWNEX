"""Premium module — feature gates for OWNEX open-core."""

from core.premium.gates import (
    get_tier,
    is_premium,
    requires_tier,
    tier_status,
)

__all__ = ["requires_tier", "get_tier", "is_premium", "tier_status"]
