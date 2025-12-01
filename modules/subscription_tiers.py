"""
Subscription Tiers and API Key Tier Management - Simplified

Defines subscription tiers with different rate limits and features.
"""

from enum import Enum
from typing import Dict, List


class SubscriptionTier(str, Enum):
    """Subscription tier levels."""
    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class TierLimits:
    """Rate limits and features for a subscription tier."""
    
    def __init__(
        self,
        name: str,
        display_name: str,
        requests_per_hour: int,
        requests_per_day: int,
        requests_per_month: int,
        max_api_keys: int,
        price_monthly: float,
        features: List[str]
    ):
        self.name = name
        self.display_name = display_name
        self.requests_per_hour = requests_per_hour
        self.requests_per_day = requests_per_day
        self.requests_per_month = requests_per_month
        self.max_api_keys = max_api_keys
        self.price_monthly = price_monthly
        self.features = features
    
    def get_rate_limit_per_minute(self) -> int:
        """Calculate requests per minute from hourly limit."""
        return self.requests_per_hour // 60
    
    def is_within_hourly_limit(self, requests: int) -> bool:
        """Check if request count is within hourly limit."""
        return requests < self.requests_per_hour
    
    def is_within_daily_limit(self, requests: int) -> bool:
        """Check if request count is within daily limit."""
        return requests < self.requests_per_day
    
    def is_within_monthly_limit(self, requests: int) -> bool:
        """Check if request count is within monthly limit."""
        return requests < self.requests_per_month


# Tier configurations as simple dicts
TIER_CONFIGS = {
    "free": {
        "display_name": "Free",
        "requests_per_hour": 60,
        "requests_per_day": 1000,
        "requests_per_month": 10000,
        "max_api_keys": 2,
        "price_monthly": 0.0,
        "features": [
            "Basic weather data",
            "7-day forecast",
            "Hourly updates",
            "Community support"
        ]
    },
    "pro": {
        "display_name": "Pro",
        "requests_per_hour": 600,
        "requests_per_day": 10000,
        "requests_per_month": 250000,
        "max_api_keys": 10,
        "price_monthly": 29.0,
        "features": [
            "All Free features",
            "Extended forecasts (16 days)",
            "Pollen & air quality data",
            "Solar & marine weather",
            "Priority support",
            "99.5% uptime SLA"
        ]
    },
    "business": {
        "display_name": "Business",
        "requests_per_hour": 3000,
        "requests_per_day": 50000,
        "requests_per_month": 1000000,
        "max_api_keys": 50,
        "price_monthly": 99.0,
        "features": [
            "All Pro features",
            "Bulk weather API",
            "Historical data access",
            "Advanced analytics",
            "Webhooks for alerts",
            "Custom integrations",
            "Priority support",
            "99.9% uptime SLA"
        ]
    },
    "enterprise": {
        "display_name": "Enterprise",
        "requests_per_hour": 10000,
        "requests_per_day": 200000,
        "requests_per_month": 5000000,
        "max_api_keys": 200,
        "price_monthly": 499.0,
        "features": [
            "All Business features",
            "Dedicated infrastructure",
            "Custom rate limits",
            "White-label options",
            "ML weather insights",
            "Custom models",
            "24/7 phone support",
            "99.99% uptime SLA",
            "Custom contracts"
        ]
    }
}


def get_tier_limits(tier: SubscriptionTier) -> TierLimits:
    """Get tier limits for a subscription tier."""
    tier_key = tier.value if isinstance(tier, SubscriptionTier) else tier
    config = TIER_CONFIGS[tier_key]
    return TierLimits(
        name=tier_key,
        **config
    )


def get_tier_from_string(tier_str: str) -> SubscriptionTier:
    """Convert string to SubscriptionTier enum."""
    try:
        return SubscriptionTier(tier_str.lower())
    except ValueError:
        return SubscriptionTier.FREE


def get_all_tiers() -> Dict:
    """Get all tier information for display."""
    return TIER_CONFIGS.copy()
