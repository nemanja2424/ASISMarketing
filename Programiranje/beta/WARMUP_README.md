# Instagram Warmup System 🔥

Kompletan sistem za zagrevanje Instagram profila sa multi-profil podrškom, humanoid ponašanjem i realističnim inter-profil komunikacijama.

## Arhitektura

```
warmup/
├── __init__.py           # Package exports
├── config.json           # Configuration settings
├── database.py           # SQLite persistence layer
├── personality.py        # Profile personality generation
├── messages.py           # Serbian message generation
├── orchestrator.py       # Warmup orchestration
├── reporting.py          # Analytics & reporting
└── logs/                 # Warmup logs
```

## Ključne Komponente

### 1. **WarmupDatabase** (`database.py`)
Upravljač podataka baziran na SQLite sa 8 tabela:
- `my_profiles` - Svi Instagram profili
- `warmup_batches` - Warmup batches
- `warmup_sessions` - Pojedinačne sesije per profil
- `actions` - Sve akcije (like, follow, DM, itd)
- `inter_profile_relationships` - Veze između profila
- `messages` - Sve generiške poruke
- `conversations` - DM razgovori
- `analytics_daily` - Dnevna analitika

**Ključne Metode:**
```python
db = WarmupDatabase()

# Profile management
db.add_profile(profile_id, display_name, category, personality)
db.get_my_profiles()
db.get_profile(profile_id)

# Batch management
db.create_warmup_batch(batch_name, total_duration_minutes, profiles_count)
db.get_batch(batch_id)
db.update_batch_status(batch_id, status)

# Sessions
db.create_session(batch_id, profile_id, session_type, start_time, expected_duration, actions_planned)
db.get_sessions(batch_id)

# Actions
db.log_action(session_id, profile_id, action_type, delay_before_sec, success)
db.get_actions(batch_id)

# Relationships & Messages
db.add_relationship(profile_a_id, profile_b_id, relationship_type, interaction_frequency)
db.create_conversation(profile_a_id, profile_b_id)
db.add_message(conversation_id, from_profile_id, to_profile_id, content, message_type, natural_score)
```

### 2. **PersonalityEngine** (`personality.py`)
Generiše jedinstvene personality-je za profile sa:
- **4 Tone Tipa:** casual, friendly, sporty, formal
- **20+ Interests:** fitness, travel, gaming, tech, food, itd
- **Activity Levels:** light, medium, high
- **Timezone & Sleep Schedule**
- **Emoji Usage:** 20-80% probabilnosti

**Primer:**
```python
pe = PersonalityEngine()
personality = pe.generate_personality()
# Output:
# {
#   'tone': 'friendly',
#   'activity_level': 'medium',
#   'interests': ['fitness', 'travel', 'gaming'],
#   'emoji_usage': 65,
#   'timezone': 'Europe/Belgrade',
#   'sleep_start': 23,
#   'sleep_end': 7
# }
```

### 3. **MessageGenerator** (`messages.py`)
Generiše naturalne srpske poruke sa:
- **8 Tipova Poruka:** greeting, reaction_positive, casual_engagement, itd
- **Emoji Support:** Automatski dodaje emoji na osnovu personality
- **Context-Aware:** Prilagođava se interests i tonalitetu

**Primer:**
```python
mg = MessageGenerator(personality_engine)
context = {
    "trigger": "follow",
    "target_interests": ["fitness"],
    "sentiment": "positive"
}
msg = mg.generate_message(profile_a, profile_b, context)
# Output: "Zdravo! 👋 Odličan profil! 💪"
```

### 4. **WarmupOrchestrator** (`orchestrator.py`)
Upravljač celog warmup procesa:
- **initialize_profiles()** - Učitaj profile iz profiles/ folder
- **generate_warmup_schedule()** - Kreiraj staggered raspored
- **setup_inter_profile_relationships()** - Postavi relacije između profila (30-70% connectivity)
- **generate_inter_profile_messages()** - Generiši DM razgovore
- **Batch Control:** start, pause, resume, cancel

**Primer:**
```python
orchestrator = WarmupOrchestrator()

# Initialize
loaded = orchestrator.initialize_profiles()

# Create warmup
batch_id = orchestrator.db.create_warmup_batch(...)
orchestrator.start_warmup_batch(batch_id)

# Manage
orchestrator.pause_warmup_batch(batch_id)
orchestrator.resume_warmup_batch(batch_id)
```

### 5. **ReportingEngine** (`reporting.py`)
Generiše detaljne izveštaje:
- **Batch Reports** - Statistika per batch
- **Per-Profile Stats** - Success rate, action counts
- **Inter-Profile Analytics** - Interaction tracking
- **CSV/JSON Export** - Za eksterne analize
- **Dashboard Data** - Real-time progress

**Primer:**
```python
reporting = ReportingEngine(db)

# Generate reports
report = reporting.generate_batch_report(batch_id)
csv_path = reporting.export_to_csv(batch_id)
json_path = reporting.export_to_json(batch_id)
dashboard = reporting.generate_dashboard_data(batch_id)
```

## Konfiguracija

Fajl: `warmup/config.json`

```json
{
  "default_batch_settings": {
    "total_profiles": 15,
    "total_duration_minutes": 240,
    "session_duration_min": 20,
    "session_duration_max": 50
  },
  "action_limits": {
    "light_activity": {
      "likes_min": 8,
      "likes_max": 15,
      "follows_min": 3,
      "follows_max": 7
    },
    "medium_activity": { ... },
    "high_activity": { ... }
  },
  "timing_settings": {
    "action_delay_min_sec": 2,
    "action_delay_max_sec": 8,
    "dm_response_delay_min_sec": 60,
    "dm_response_delay_max_sec": 300
  }
}
```

## Korišćenje

### Osnovna Upotreba
```python
from warmup import WarmupDatabase, WarmupOrchestrator, ReportingEngine

# Setup
db = WarmupDatabase()
orchestrator = WarmupOrchestrator(db=db)
reporting = ReportingEngine(db)

# Create warmup batch
batch_id = db.create_warmup_batch(
    batch_name="My Warmup",
    total_duration_minutes=240,
    profiles_count=15
)

# Generate schedule & relationships
orchestrator.generate_warmup_schedule()
orchestrator.setup_inter_profile_relationships()
orchestrator.generate_inter_profile_messages()

# Start warmup
orchestrator.start_warmup_batch(batch_id)

# Generate reports
report = reporting.generate_batch_report(batch_id)
reporting.export_to_csv(batch_id)
reporting.export_to_json(batch_id)
```

### Sa Instagram Warmup Campaign
```python
from instagram_warmup import InstagramWarmupCampaign

campaign = InstagramWarmupCampaign()
campaign.setup()

# Run with selected profiles
campaign.run_campaign([
    "profile_1",
    "profile_2",
    "profile_3"
])

# Control
campaign.pause_campaign()
campaign.resume_campaign()
campaign.cancel_campaign()
```

## Database Schema

### warmup_batches
```
id (PK)
batch_name
total_duration_minutes
profiles_count
config (JSON)
status (pending | running | paused | completed | cancelled)
created_at
```

### warmup_sessions
```
id (PK)
batch_id (FK)
profile_id (FK)
session_type (engagement | hashtag_exploration | explore_feed)
start_time
actual_start_time
expected_duration
actual_duration
status (pending | running | completed | paused | cancelled | failed)
actions_planned
actions_completed
```

### actions
```
id (PK)
session_id (FK)
profile_id (FK)
action_type (like | follow | unfollow | save | dm | scroll | visit)
target_profile_id
delay_before_sec
executed_at
success
details (JSON)
```

### inter_profile_relationships
```
id (PK)
profile_a_id (FK)
profile_b_id (FK)
relationship_type (mutual_interest | follow_back | passive)
interaction_frequency (low | medium | high)
a_follows_b
b_follows_a
last_interaction
```

## Personalnost Sistema

Svaki profil ima unikatan personality koji definiše:

1. **Tone** (20-80% emoji usage):
   - `casual` (70%): "Jao šta je ovo! 😂😂"
   - `friendly` (60%): "Zdravo! 👋 Odličan profil! 💪"
   - `sporty` (55%): "Sjajan trening! 🔥💪"
   - `formal` (30%): "Odličan sadržaj. Pratim!"

2. **Activity Levels:**
   - `light`: 8-15 likes, 3-7 follows per session
   - `medium`: 15-30 likes, 7-15 follows per session
   - `high`: 30-50 likes, 15-25 follows per session

3. **Interests:** Nasumično odabrani iz 20+ opcija za authentic ponašanje

4. **Timezone & Sleep:** Za realistično vremensko raspoređivanje akcija

## Bezbednost & Praktike

- ✅ Staggered profile execution (ne sve odjednom)
- ✅ Realistic delays između akcija (2-8 sec)
- ✅ Random action patterns (ne mechanical)
- ✅ Inter-profile interactions (3D ponašanje)
- ✅ Natural message generation (Serbian, emojis)
- ✅ Activity rate limits (max 200 actions/hour)
- ✅ Rest periods između batches-a

## Testiranje

```bash
# Pokreni sve testove
python test_warmup.py

# Ili koristi Python snippet
python -c "from warmup import *; print('✓ All systems working')"
```

## Status

- ✅ WarmupDatabase - Fully implemented
- ✅ PersonalityEngine - Fully implemented
- ✅ MessageGenerator - Fully implemented
- ✅ WarmupOrchestrator - Fully implemented
- ✅ ReportingEngine - Fully implemented
- 🔄 Browser action integration (in progress)
- 🔄 Real-time scheduling (planned)
- 🔄 GUI dashboard (planned)

## Logging

Logs se čuvaju u `warmup/logs/` sa:
- Batch creation/status events
- Session execution timing
- Action success/failure tracking
- Performance metrics

---

**Last Updated:** 2024  
**Version:** 1.0  
**Language:** Python 3.10+
