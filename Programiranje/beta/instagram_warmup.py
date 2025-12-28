"""
Instagram Warmup Campaign - Lite verzija
Samo generiše warmup podatke bez otvaranja browser-a
"""
import sys
import json
import random
from pathlib import Path
from datetime import datetime
from typing import List

from warmup import WarmupDatabase, WarmupOrchestrator, ReportingEngine


def main():
    """Pokreni warmup sa profilima iz command line argumenta"""
    
    # Učitaj profile iz argumenta
    profile_ids = sys.argv[1:] if len(sys.argv) > 1 else []
    
    print("\n[🔥] Instagram Warmup Campaign - Lite")
    print(f"[📱] Profile: {len(profile_ids)}")
    
    if not profile_ids:
        print("[ERROR] Nema profila za warmup!")
        return
    
    # Validiraj profile ID-eve (ne smeju biti opcije kao --help, -h, itd)
    invalid_ids = [pid for pid in profile_ids if pid.startswith('-') or pid in ['--help', 'help', '']]
    if invalid_ids:
        print(f"[ERROR] Nevalidni profile ID-evi: {invalid_ids}")
        return
    
    # Initialize
    db = WarmupDatabase()
    orchestrator = WarmupOrchestrator(db=db)
    reporting = ReportingEngine(db)
    
    print("[🔧] Inicijalizacija...")
    
    # Kreiraj batch
    batch_name = f"Warmup {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    batch_id = db.create_warmup_batch(
        batch_name=batch_name,
        total_duration_minutes=240,
        profiles_count=len(profile_ids)
    )
    print(f"[✓] Batch kreiran: {batch_id}")
    
    # Generiši raspored
    print("[📅] Generisanje rasporeda...")
    for i, profile_id in enumerate(profile_ids):
        stagger = i * 5
        session_id = db.create_session(
            batch_id=batch_id,
            profile_id=profile_id,
            session_type="engagement",
            start_time=stagger,
            expected_duration=30,
            actions_planned=20
        )
        print(f"  ✓ {profile_id[:12]}: sesija {session_id}")
        
        # Generiši akcije za ovu sesiju
        actions_plan = orchestrator._generate_actions(
            {'personality': {'activity_level': 'medium'}},
            'engagement'
        )
        
        # Sačuvaj akcije u bazu
        cursor = db.connection.cursor()
        likes_count = actions_plan.get('likes', 8)
        follows_count = actions_plan.get('follows', 5)
        saves_count = actions_plan.get('saves', 2)
        
        # Dodaj like akcije
        for j in range(likes_count):
            cursor.execute("""
                INSERT INTO actions (session_id, profile_id, action_type, timestamp, success, delay_before_sec)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id, profile_id, 'like',
                datetime.now().isoformat(),
                0,  # 0 = pending
                random.randint(5, 30)
            ))
        
        # Dodaj follow akcije
        for j in range(follows_count):
            cursor.execute("""
                INSERT INTO actions (session_id, profile_id, action_type, timestamp, success, delay_before_sec)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id, profile_id, 'follow',
                datetime.now().isoformat(),
                0,
                random.randint(30, 60)
            ))
        
        # Dodaj save akcije
        for j in range(saves_count):
            cursor.execute("""
                INSERT INTO actions (session_id, profile_id, action_type, timestamp, success, delay_before_sec)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id, profile_id, 'save',
                datetime.now().isoformat(),
                0,
                random.randint(5, 30)
            ))
        
        db.connection.commit()
    
    # Generiši inter-profil relacije
    print("[🔗] Postavljanje inter-profil relacija...")
    orchestrator.setup_inter_profile_relationships()
    
    # Generiši poruke
    print("[💬] Generisanje poruka...")
    orchestrator.generate_inter_profile_messages(batch_id)
    
    # Startuj batch
    print("[▶] Pokretanje batch-a...")
    orchestrator.start_warmup_batch(batch_id)
    
    # Generiši izveštaje
    print("[📊] Generisanje izveštaja...")
    csv_path = reporting.export_to_csv(batch_id)
    json_path = reporting.export_to_json(batch_id)
    
    print(f"\n[✓] Warmup završen!")
    print(f"  ├─ Batch: {batch_id}")
    print(f"  ├─ Profila: {len(profile_ids)}")
    print(f"  ├─ CSV: {csv_path}")
    print(f"  └─ JSON: {json_path}")
    

if __name__ == "__main__":
    main()
