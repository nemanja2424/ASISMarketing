# KAMPANJE SISTEM

Novi sistem za kampanje koristi `.py` fajlove umesto `.json` za bolju fleksibilnost i kontrolu.

## Struktura

```
campaigns/
├── __init__.py          # Package init
├── base.py              # BaseCampaign klasa
├── instagram.py         # InstagramCampaign
├── scraping.py          # (budućnost)
└── automation.py        # (budućnost)
```

## Karakteristike

- **Multi-profile pokretanje**: Svaka kampanja može pokrenuti više profila istovremeno
- **Proxy & Fingerprint**: Automatski se koriste svi sačuvani profil podaci
- **Concurrent/Sequential**: Izbor između simultanog i sekvencijalnog pokretanja
- **Geolocation**: Automatski primenjuje geolokalciju i timezone
- **WebRTC Protection**: Automatski isključuje WebRTC leak

## Pokretanje Kampanja

### Instagram - Svi profili istovremeno:
```bash
python3 campaigns/instagram.py
```

### Instagram - Specifični profili:
```bash
python3 campaigns/instagram.py profile_e2b9eaff profile_731f08c5
```

### Iz koda:
```python
from campaigns import InstagramCampaign

campaign = InstagramCampaign(
    profile_ids=["profile_e2b9eaff", "profile_731f08c5"],
    concurrent=True
)
campaign.run()
```

## Kreiraj Novu Kampanju

1. Nasledi `BaseCampaign`:
```python
from campaigns.base import BaseCampaign

class MyCampaign(BaseCampaign):
    def __init__(self, profile_ids=None):
        super().__init__(
            profile_ids=profile_ids or ["profile_abc"],
            url="https://example.com",
            concurrent=True
        )
    
    def execute(self, page, profile_id, ns_data):
        """Custom logic here"""
        print(f"Running on {profile_id}")
        # Scraping, interaction, etc.
```

2. Registruj u `campaigns/__init__.py`

3. Pokreni:
```bash
python3 campaigns/my_campaign.py
```

## Dostupne Kampanje

### InstagramCampaign
- **Opis**: Otvara Instagram.com na svim profilima istovremeno
- **URL**: https://www.instagram.com
- **Features**: Screenshot saving, geolocation, timezone, proxy

## Napomene

- Svaki profil se pokreće sa sopstvenim proxy-jem i fingerprintom
- Browser ostaje otvoren nakon učitavanja (user može da interaktuje)
- Ctrl+C zaustavlja sve profila
- Logovanje pokazuje status svakog profila posebno

## Struktura Izvršavanja

```
Campaign.run()
├── run_concurrent() / run_sequential()
│   └── _launch_profile(profile_id)
│       ├── Load profile.json + namespace.json
│       ├── Setup proxy sa auth
│       ├── Launch Camoufox
│       ├── Set geolocation
│       ├── Set timezone
│       ├── Navigate to URL
│       └── execute() [custom logic]
```

## Budućih Kampanja

- **ScrapingCampaign**: Scrape Instagram followers, posts, etc.
- **AutomationCampaign**: Automatizovane akcije (like, follow, comment)
- **RotationCampaign**: Rotacija kroz profile na određenoj lokaciji
- **ScheduledCampaign**: Kampanja na određeno vreme
