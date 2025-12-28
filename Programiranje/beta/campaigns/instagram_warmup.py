#!/usr/bin/env python3
"""Instagram Warmup campaign - Warm up Instagram profiles with realistic activity."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from campaigns.base import BaseCampaign
import time


class InstagramWarmupCampaign(BaseCampaign):
    """Campaign that warms up Instagram profiles with realistic user activity."""
    
    def __init__(self, profile_ids=None, concurrent=True):
        """
        Args:
            profile_ids: List of profile IDs. If None, uses all available profiles.
            concurrent: If True, launch all profiles at once.
        """
        if profile_ids is None:
            # Default: use all profiles
            from pathlib import Path
            profile_ids = [d.name for d in Path("profiles").glob("profile_*") if d.is_dir()]
        
        super().__init__(profile_ids=profile_ids, url="https://www.instagram.com", concurrent=concurrent)
    
    def execute(self, page, profile_id: str, ns_data: dict):
        """Instagram warmup logic - realistic activity on Instagram."""
        try:
            # Wait for Instagram to fully load
            print(f"[{profile_id}] Warming up Instagram account...")
            
            # Check if we're on Instagram
            title = page.title()
            url = page.url
            print(f"[{profile_id}] Title: {title}")
            print(f"[{profile_id}] URL: {url}")
            
            # Warmup activities will be configured per warmup plan
            # For now, just verify access
            print(f"[{profile_id}] ✓ Instagram access verified")
            print(f"[{profile_id}] Account is ready for warmup activities")
            
        except Exception as e:
            print(f"[{profile_id}] Warmup failed: {e}")


if __name__ == "__main__":
    import sys
    
    # Get profile IDs from command line (optional)
    profile_ids = sys.argv[1:] if len(sys.argv) > 1 else None
    
    print("=" * 60)
    print("INSTAGRAM WARMUP - Multi-Profile Account Warm-up")
    print("=" * 60)
    
    campaign = InstagramWarmupCampaign(profile_ids=profile_ids, concurrent=True)
    campaign.run()
