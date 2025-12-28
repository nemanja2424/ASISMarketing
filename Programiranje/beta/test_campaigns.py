#!/usr/bin/env python3
"""
Test script - How to run campaigns programmatically.
"""

from campaigns import InstagramCampaign, ScrapingCampaign
from pathlib import Path


def example_instagram():
    """Run Instagram campaign."""
    print("=" * 60)
    print("PRIMER 1: Instagram kampanja (svi profili)")
    print("=" * 60)
    
    # Pronađi sve profila
    profiles = [d.name for d in Path("profiles").glob("profile_*") if d.is_dir()]
    print(f"Dostupni profili: {profiles}\n")
    
    # Kreiraj kampanju
    campaign = InstagramCampaign(profile_ids=profiles, concurrent=True)
    
    print(f"Kampanja postavljena:")
    print(f"  - URL: {campaign.url}")
    print(f"  - Profila: {len(campaign.profile_ids)}")
    print(f"  - Concurrent: {campaign.concurrent}")
    print(f"\nZa pokretanje:")
    print(f"  python3 campaigns/instagram.py")


def example_scraping():
    """Run scraping campaign."""
    print("\n" + "=" * 60)
    print("PRIMER 2: Scraping kampanja")
    print("=" * 60)
    
    profiles = [d.name for d in Path("profiles").glob("profile_*") if d.is_dir()]
    
    # Kreiraj kampanju za Wikipedia
    campaign = ScrapingCampaign(
        profile_ids=profiles,
        url="https://www.wikipedia.org",
        concurrent=False  # Sequential scraping
    )
    
    print(f"Kampanja postavljena:")
    print(f"  - URL: {campaign.url}")
    print(f"  - Profila: {len(campaign.profile_ids)}")
    print(f"  - Concurrent: {campaign.concurrent}")
    print(f"\nZa pokretanje:")
    print(f"  python3 campaigns/scraping.py https://www.wikipedia.org")


def example_custom_campaign():
    """Show how to create custom campaign."""
    print("\n" + "=" * 60)
    print("PRIMER 3: Custom kampanja")
    print("=" * 60)
    
    example_code = '''
from campaigns.base import BaseCampaign

class MyCustomCampaign(BaseCampaign):
    def __init__(self, profile_ids):
        super().__init__(
            profile_ids=profile_ids,
            url="https://example.com",
            concurrent=True
        )
    
    def execute(self, page, profile_id, ns_data):
        """Custom logic for this campaign."""
        print(f"[{profile_id}] Executing custom logic...")
        
        # Interact sa stranicom
        title = page.title()
        print(f"[{profile_id}] Title: {title}")
        
        # Scraping
        links = page.locator("a").count()
        print(f"[{profile_id}] Found {links} links")
        
        # Screenshot
        page.screenshot(path=f"screenshots/{profile_id}.png")


# Run kampanju
profiles = ["profile_e2b9eaff", "profile_731f08c5"]
campaign = MyCustomCampaign(profile_ids=profiles)
campaign.run()
'''
    
    print("Kreiraj novu kampanju:")
    print(example_code)


if __name__ == "__main__":
    example_instagram()
    example_scraping()
    example_custom_campaign()
    
    print("\n" + "=" * 60)
    print("DOSTUPNE KAMPANJE")
    print("=" * 60)
    print("1. InstagramCampaign - Open Instagram.com")
    print("2. ScrapingCampaign - Scrape any website")
    print("3. Custom campaigns - Nasle BaseCampaign")
