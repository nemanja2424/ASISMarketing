"""
Instagram Warmup Campaign - Multi-profil zagrevanje

Zagrevanje profila sa humanoid ponašanjem, inter-profil komunikacijom i realističnim aktivnostima.
"""
import sys
from pathlib import Path

# Dodaj project root u path
sys.path.insert(0, str(Path(__file__).parent.parent))

from instagram_warmup import InstagramWarmupCampaign


def main():
    """Pokreni warmup kampanju"""
    campaign = InstagramWarmupCampaign()
    campaign.setup()
    
    # Za standalone pokretanje
    print("\n[🔥] Instagram Warmup Campaign")
    print("Koristi campaign.run_campaign(['profile_1', 'profile_2', ...])")


if __name__ == "__main__":
    main()
