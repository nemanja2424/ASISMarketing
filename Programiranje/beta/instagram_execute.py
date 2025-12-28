"""
Instagram Warmup Execution - Simulacija ljudskog ponašanja
Čita plan iz warmup batch-a i izvršava akcije na human-like način
"""
import sys
import json
import random
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Force flush stdout
sys.stdout = open(sys.stdout.fileno(), mode='w', buffering=1)

from warmup import WarmupDatabase, WarmupOrchestrator
from BW_Controller.run_profile import run_profile_process


class InstagramHumanExecutor:
    """Izvršava warmup plan na huma ničan način sa browser automatijom"""
    
    def __init__(self, batch_id: int):
        self.batch_id = batch_id
        self.db = WarmupDatabase()
        self.orchestrator = WarmupOrchestrator(db=self.db)
        
    def execute_batch(self):
        """Pokreni batch execution sa humanoid ponašanjem"""
        print(f"\n[🤖] Instagram Warmup Executor")
        print(f"[📌] Batch ID: {self.batch_id}")
        
        # Učitaj batch direktno iz baze sa korektnom kolenom
        cursor = self.db.connection.cursor()
        cursor.execute("""
            SELECT id, batch_name, total_duration_minutes, status
            FROM warmup_batches
            WHERE id = ?
        """, (self.batch_id,))
        batch_row = cursor.fetchone()
        
        if not batch_row:
            print(f"[❌] Batch {self.batch_id} nije pronađen!")
            return False
        
        batch_id_actual, batch_name, duration, status = batch_row
        print(f"[📋] Batch: {batch_name}")
        
        # Učitaj sve sesije za ovaj batch
        cursor.execute("""
            SELECT id, profile_id, start_time, expected_duration, actions_planned
            FROM warmup_sessions 
            WHERE batch_id = ? 
            ORDER BY start_time ASC
        """, (self.batch_id,))
        sessions = cursor.fetchall()
        
        if not sessions:
            print("[❌] Nema sesija za ovaj batch!")
            return False
        
        print(f"[📱] Sesije: {len(sessions)}")
        
        # Učitaj poruke
        cursor.execute("""
            SELECT id, from_profile_id, to_profile_id, content, message_type
            FROM messages
            LIMIT 20
        """)
        messages = cursor.fetchall()
        print(f"[💬] Poruke za slanje: {len(messages)}")
        
        # Za svaku sesiju, pokreni profil i simuliraj akcije
        for session in sessions:
            session_id, profile_id, start_time_min, duration, actions_planned = session
            # Konvertuј actions_planned u int ako je string
            try:
                actions_planned = int(actions_planned) if isinstance(actions_planned, str) else actions_planned
            except (ValueError, TypeError):
                actions_planned = 20  # Default
            
            self._execute_session(
                session_id=session_id,
                profile_id=profile_id,
                start_delay_min=int(start_time_min) if start_time_min else 0,
                duration_min=int(duration) if duration else 30,
                actions_planned=actions_planned
            )
        
        print(f"\n[✅] Batch {self.batch_id} izvršavanje završeno!")
        return True
    
    def _execute_session(self, session_id: int, profile_id: str, 
                         start_delay_min: int, duration_min: int, 
                         actions_planned: int):
        """Izvrši jednu sesiju sa humanoid ponašanjem u browser-u"""
        print(f"\n[▶️] Pokretanje sesije: {session_id}")
        print(f"    └─ Profil: {profile_id}")
        print(f"    └─ Čekanje: {start_delay_min} min | Trajanje: {duration_min} min | Akcije: {actions_planned}")
        
        # Čekaj pre nego što počneš (stagger effect)
        if start_delay_min > 0:
            print(f"[⏳] Čekanje {start_delay_min} minuta pre nego što počnemo...")
            self._human_delay(start_delay_min * 60)
        
        print(f"[🌐] Otvaranje profila u browser-u...")
        
        # Pokreni profil kroz browser sa timeout-om
        try:
            # Puna putanja do profil.json
            profile_path = f"profiles/{profile_id}/profile.json"
            
            # Compute timeout (duration_min * 60 sekundi, maksimalno 300 sekundi = 5 minuta)
            timeout_sec = min(duration_min * 60, 300)
            
            # Učitaj akcije iz baze
            cursor = self.db.connection.cursor()
            cursor.execute("""
                SELECT id, action_type, delay_before_sec
                FROM actions
                WHERE session_id = ? AND success = 0
                ORDER BY delay_before_sec ASC
            """, (session_id,))
            actions = cursor.fetchall()
            
            if actions:
                print(f"[📋] Akcije za izvršenje: {len(actions)}")
                for action_id, action_type, delay_sec in actions[:5]:  # Prikaži prvih 5
                    print(f"    - {action_type}")
            else:
                print(f"[⚠️] Nema akcija za ovu sesiju")
            
            # Pokreni kao subprocess sa timeout-om
            cmd = [sys.executable, "BW_Controller/run_profile.py", profile_path]
            
            try:
                # Pokreni proces sa output capture
                result = subprocess.run(
                    cmd, 
                    timeout=timeout_sec, 
                    cwd=str(Path.cwd()),
                    capture_output=False  # Prikaži output kao što se dešava
                )
                print(f"[✓] Profil {profile_id} je završio sesiju")
                
                # Označi akcije kao izvršene
                cursor.execute("""
                    UPDATE actions
                    SET success = 1
                    WHERE session_id = ?
                """, (session_id,))
                self.db.connection.commit()
                
            except subprocess.TimeoutExpired:
                print(f"[⏱️] Timeout nakon {timeout_sec}s - sesija završena")
                # Označi delom izvršene akcije
                cursor.execute("""
                    UPDATE actions
                    SET success = 1
                    WHERE session_id = ? AND success = 0
                    LIMIT 5
                """, (session_id,))
                self.db.connection.commit()
        except Exception as e:
            print(f"[⚠️] Greška pri pokretanju profila: {e}")
        
        # Ažurira status sesije
        self.db.update_session_status(session_id, "completed")
        print(f"[✓] Sesija {session_id} završena!")
    
    def _simulate_action(self, profile_id: str, action_type: str, session_id: int = -1):
        """Simuliraj akciju u bazi (logging)"""
        # Log akciju u bazu
        cursor = self.db.connection.cursor()
        cursor.execute("""
            INSERT INTO actions (
                session_id, profile_id, action_type, 
                timestamp, success, delay_before_sec
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            profile_id,
            action_type,
            datetime.now().isoformat(),
            True,
            random.randint(5, 15)
        ))
        self.db.connection.commit()
    
    def _human_delay(self, seconds: int):
        """Čekaj sa human-like varijacijom"""
        variation = random.randint(-5, 5)
        actual_wait = max(1, seconds + variation)
        
        # Prikaži countdown
        mins = actual_wait // 60
        secs = actual_wait % 60
        print(f"[⏳] Čekanje: {mins}m {secs}s")
        
        # Simuliraj čekanje sa periodičnim ispisima
        start = time.time()
        while time.time() - start < actual_wait:
            elapsed = time.time() - start
            remaining = actual_wait - elapsed
            if remaining > 0 and int(remaining) % 30 == 0:
                print(f"    └─ Još: {int(remaining)}s")
            time.sleep(1)


def main():
    """Glavna funkcija"""
    if len(sys.argv) < 2:
        print("[❌] Korišćenje: python instagram_execute.py <batch_id>")
        return
    
    batch_id = int(sys.argv[1])
    
    executor = InstagramHumanExecutor(batch_id)
    executor.execute_batch()


if __name__ == "__main__":
    main()
