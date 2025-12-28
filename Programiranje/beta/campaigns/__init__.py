"""Campaigns - Multi-profile browser automation routines.

Each campaign can launch multiple profiles and execute specific tasks:
- InstagramWarmupCampaign: Warm up Instagram profiles with realistic activity
- etc.
"""

from campaigns.base import BaseCampaign
from campaigns.instagram_warmup import InstagramWarmupCampaign

__all__ = ["BaseCampaign", "InstagramWarmupCampaign"]
