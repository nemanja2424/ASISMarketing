"""
WarmupOrchestrator - Upravlja čitavim warmup procesom
"""
import random
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

from warmup.database import WarmupDatabase
from warmup.personality import PersonalityEngine
from warmup.messages import MessageGenerator


class WarmupOrchestrator:
    """
    Upravlja kompletnim warmup procesom:
    - Kreiraj i rasporedi warmup plan
    - Generiši personality-je
    - Upravljaj inter-profile interakcijama
    - Loguj sve u bazu
    """
    
    def __init__(self, config: Dict = None, db: WarmupDatabase = None):
        """
        Inicijalizuj orchestrator
        
        Args:
            config: Warmup config dict
            db: WarmupDatabase instanca
        """
        self.config = config or self._load_default_config()
        self.db = db or WarmupDatabase()
        self.personality_engine = PersonalityEngine()
        self.message_generator = MessageGenerator(self.personality_engine)
    
    def _load_default_config(self) -> Dict:
        """Učitaj default konfiguraciju"""
        config_path = Path("warmup/config.json")
        
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)
        
        # Default config
        return {
            "name": "Default Warmup",
            "total_profiles": 15,
            "total_duration_minutes": 240,
            "intensity_level": "medium",
            "rules": {
                "action_delay_sec": [15, 45],
                "session_duration_min": 20,
                "session_duration_max": 50,
                "timezone": "Europe/Belgrade"
            },
            "action_limits": {
                "likes_per_session": [8, 15],
                "follows_per_session": [3, 7],
                "saves_per_session": [1, 4],
                "dms_per_session": [0, 2]
            }
        }
    
    def initialize_profiles(self) -> None:
        """
        Inicijalizuj profile iz profiles/ foldera
        """
        profiles_dir = Path("profiles")
        
        if not profiles_dir.exists():
            print("[ERROR] profiles/ folder ne postoji!")
            return
        
        print("[*] Inicijalizujem profile...")
        
        for profile_dir in profiles_dir.glob("profile_*"):
            profile_id = profile_dir.name
            profile_json = profile_dir / "profile.json"
            
            if not profile_json.exists():
                continue
            
            try:
                with open(profile_json) as f:
                    profile_data = json.load(f)
                
                display_name = profile_data.get("metadata", {}).get("display_name", profile_id)
                category = profile_data.get("metadata", {}).get("category", "Bez kategorije")
                
                # Generiši personality
                personality = self.personality_engine.generate_personality(profile_id)
                
                # Pronađi related profiles (iz config-a)
                related = self._select_related_profiles(profile_id)
                
                # Dodaj u bazu
                self.db.add_profile(
                    profile_id=profile_id,
                    display_name=display_name,
                    category=category,
                    personality=personality,
                    related_profiles=related
                )
                
                print(f"[+] Dodat profil: {display_name} ({profile_id[:8]}...)")
            
            except Exception as e:
                print(f"[-] Greška pri učitavanju {profile_id}: {e}")
    
    def _select_related_profiles(self, source_profile_id: str) -> List[str]:
        """
        Odaberi sa kojim profilima se može ovaj profil komunicirati
        Minimalno 1, maksimalno 50% ostalih profila
        """
        all_profiles = self.db.get_my_profiles()
        other_profiles = [p for p in all_profiles if p['profile_id'] != source_profile_id]
        
        if not other_profiles:
            return []
        
        # 30-70% šansa da će biti povezan
        num_related = random.randint(max(1, len(other_profiles) // 4), 
                                    max(1, len(other_profiles) // 2))
        
        related = random.sample(other_profiles, min(num_related, len(other_profiles)))
        
        return [p['profile_id'] for p in related]
    
    def generate_warmup_schedule(self, batch_name: str = None) -> int:
        """
        Kreiraj detaljan plan za sve profile
        
        Args:
            batch_name: Naziv batch-a
        
        Returns:
            batch_id
        """
        batch_name = batch_name or f"Batch {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        profiles = self.db.get_my_profiles()
        if not profiles:
            print("[ERROR] Nema profile za zagrevanje!")
            return None
        
        total_duration = self.config['total_duration_minutes']
        
        print(f"\n[*] Generijem warmup plan za {len(profiles)} profila ({total_duration} min)...")
        
        # Kreiraj batch
        batch_id = self.db.create_warmup_batch(
            batch_name=batch_name,
            total_duration_minutes=total_duration,
            profiles_count=len(profiles),
            config=self.config
        )
        
        # Rasporedi profila
        schedule = []
        stagger_interval = total_duration / len(profiles)
        
        for i, profile in enumerate(profiles):
            start_time = i * stagger_interval
            duration = random.randint(
                self.config['rules']['session_duration_min'],
                self.config['rules']['session_duration_max']
            )
            
            session_type = random.choice(['follower_hunt', 'engagement', 'explore', 'balanced'])
            
            # Generiši akcije
            actions = self._generate_actions(profile, session_type)
            
            # Kreiraj sesiju
            session_id = self.db.create_session(
                batch_id=batch_id,
                profile_id=profile['profile_id'],
                session_type=session_type,
                start_time=start_time,
                expected_duration=duration,
                actions_planned=actions
            )
            
            schedule.append({
                "session_id": session_id,
                "profile_id": profile['profile_id'],
                "display_name": profile['display_name'],
                "start_time": start_time,
                "duration": duration,
                "session_type": session_type,
                "actions": actions
            })
            
            print(f"[+] {profile['display_name']}: Start {start_time:.0f}min, "
                  f"Duration {duration}min, Type: {session_type}")
        
        print(f"\n[✓] Warmup plan kreiran! Batch ID: {batch_id}")
        return batch_id
    
    def _generate_actions(self, profile: Dict, session_type: str) -> Dict:
        """Generiši akcije za sesiju"""
        activity_level = profile.get('personality', {}).get('activity_level', 'medium')
        
        # Base na activity level
        base_actions = {
            'low': {
                'likes': random.randint(3, 8),
                'follows': random.randint(1, 3),
                'saves': random.randint(0, 2)
            },
            'medium': {
                'likes': random.randint(8, 15),
                'follows': random.randint(3, 7),
                'saves': random.randint(1, 4)
            },
            'high': {
                'likes': random.randint(15, 25),
                'follows': random.randint(5, 10),
                'saves': random.randint(2, 5)
            }
        }
        
        actions = base_actions.get(activity_level, base_actions['medium']).copy()
        actions['dms'] = random.randint(0, 2)
        actions['scrolls'] = random.randint(10, 50)
        
        return actions
    
    def setup_inter_profile_relationships(self) -> None:
        """Setup relacije između profila"""
        print("\n[*] Postavljam inter-profile relacije...")
        
        profiles = self.db.get_my_profiles()
        
        for profile_a in profiles:
            related_profiles = profile_a.get('related_profiles', [])
            
            # Ako je None ili empty, preskočiti
            if not related_profiles:
                continue
            
            # Ako je JSON string, parsiraj
            if isinstance(related_profiles, str):
                try:
                    related_profiles = json.loads(related_profiles)
                except:
                    related_profiles = []
            
            for profile_b_id in related_profiles:
                profile_b = self.db.get_profile(profile_b_id)
                if not profile_b:
                    continue
                
                # Odaberi tip relacije
                relationship_type = random.choice(['friends', 'acquaintances'])
                
                # Odaberi interaction frequency
                interaction_freq = random.choice(['rare', 'occasional', 'frequent'])
                
                # Odaberi ko koga prati
                a_follows_b = random.random() < 0.7
                b_follows_a = random.random() < (0.7 if a_follows_b else 0.3)
                
                # Dodaj relaciju
                self.db.add_relationship(
                    profile_a['profile_id'],
                    profile_b_id,
                    relationship_type,
                    interaction_freq
                )
                
                print(f"[+] {profile_a['display_name']} <-> {profile_b['display_name']}: "
                      f"{relationship_type} ({interaction_freq})")
    
    def generate_inter_profile_messages(self, batch_id: int) -> None:
        """
        Generiši poruke između profila za ovaj batch
        """
        print("\n[*] Generijem poruke između profila...")
        
        profiles = self.db.get_my_profiles()
        relationships = self.db.get_relationships()
        
        message_count = 0
        
        for rel in relationships[:len(relationships) // 3]:  # 1/3 relacija će imati poruke
            profile_a = self.db.get_profile(rel['profile_a_id'])
            profile_b = self.db.get_profile(rel['profile_b_id'])
            
            if not profile_a or not profile_b:
                continue
            
            # Kreiraj konverzaciju
            conversation_id = self.db.create_conversation(
                profile_a['profile_id'],
                profile_b['profile_id'],
                conversation_theme=random.choice(profile_a.get('personality', {}).get('interests', ['general']))
            )
            
            # Generiši poruke
            trigger = random.choice(['follow', 'like_post', 'random_dm'])
            messages = self.message_generator.generate_dm_conversation(
                profile_a, profile_b, trigger
            )
            
            for msg in messages:
                self.db.add_message(
                    conversation_id=conversation_id,
                    from_profile_id=msg['from_profile_id'],
                    to_profile_id=msg['to_profile_id'],
                    content=msg['content'],
                    message_type=msg['message_type'],
                    natural_score=random.randint(75, 95)
                )
                message_count += 1
        
        print(f"[✓] Generiše {message_count} poruka")
    
    def get_warmup_status(self, batch_id: int) -> Dict:
        """Pronađi status warmup batch-a"""
        batch = self.db.get_batch(batch_id)
        sessions = self.db.get_sessions(batch_id)
        actions = self.db.get_actions(batch_id)
        
        completed = len([s for s in sessions if s['status'] == 'completed'])
        
        return {
            "batch_id": batch_id,
            "batch_name": batch['batch_name'],
            "status": batch['status'],
            "progress": f"{completed}/{len(sessions)}",
            "total_actions": len(actions),
            "created_at": batch['created_at']
        }
    
    def start_warmup_batch(self, batch_id: int) -> bool:
        """
        Kreni sa izvršavanjem warmup batch-a
        
        Args:
            batch_id: ID batch-a za pokretanje
        
        Returns:
            True ako je batch uspešno pokrenut
        """
        batch = self.db.get_batch(batch_id)
        
        if not batch:
            print(f"[ERROR] Batch {batch_id} nije pronađen!")
            return False
        
        if batch['status'] != 'pending':
            print(f"[ERROR] Batch {batch_id} nije u pending statusu!")
            return False
        
        # Ažuriraj batch status
        self.db.update_batch_status(batch_id, 'running')
        
        print(f"[✓] Warmup batch {batch_id} ({batch['batch_name']}) je startovan!")
        return True
    
    def pause_warmup_batch(self, batch_id: int) -> bool:
        """Pauzira batch i sve njegove sesije"""
        batch = self.db.get_batch(batch_id)
        
        if not batch:
            return False
        
        self.db.update_batch_status(batch_id, 'paused')
        self.db.update_batch_status(batch_id, 'paused')
        
        print(f"[⏸] Warmup batch {batch_id} je pauziran!")
        return True
    
    def resume_warmup_batch(self, batch_id: int) -> bool:
        """Nastavi batch i njegove sesije"""
        batch = self.db.get_batch(batch_id)
        
        if not batch:
            return False
        
        self.db.update_batch_status(batch_id, 'running')
        
        print(f"[▶] Warmup batch {batch_id} je nastavljan!")
        return True
    
    def cancel_warmup_batch(self, batch_id: int) -> bool:
        """Otkaži batch i sve preostale sesije"""
        batch = self.db.get_batch(batch_id)
        
        if not batch:
            return False
        
        self.db.update_batch_status(batch_id, 'cancelled')
        
        print(f"[✗] Warmup batch {batch_id} je otkazan!")
        return True
    
    def get_next_session(self, batch_id: int) -> Optional[Dict]:
        """
        Pronađi sledeću pending sesiju za izvršavanje
        
        Returns:
            Session dict ili None
        """
        sessions = self.db.get_sessions(batch_id)
        
        # Sortiraj po start_time i pronađi prvu pending
        for session in sorted(sessions, key=lambda s: s['start_time']):
            if session['status'] == 'pending':
                return session
        
        return None
