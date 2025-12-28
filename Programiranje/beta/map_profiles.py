"""
Mapiranje Instagram username-a iz browser profila na warmup profile
"""
import json
from pathlib import Path
import sqlite3
from typing import Dict


def map_browser_profiles_to_warmup():
    """
    Učita display_name-e iz browser profila (profile.json)
    i mapira ih sa profile_id-ima iz warmup batch-a
    """
    print("[🔗] Mapiranje browser profila na warmup profile...\n")
    
    # Učitaj sve browser profile
    profiles_dir = Path("profiles")
    profile_mapping = {}
    
    for profile_folder in profiles_dir.glob("profile_*"):
        if not profile_folder.is_dir():
            continue
            
        profile_json = profile_folder / "profile.json"
        if not profile_json.exists():
            continue
        
        with open(profile_json, 'r') as f:
            profile_data = json.load(f)
        
        profile_id = profile_data["profile_id"]
        display_name = profile_data["metadata"]["display_name"]
        
        profile_mapping[profile_id] = {
            "display_name": display_name,
            "instagram_username": display_name,  # Isti kao display_name
            "folder": str(profile_folder),
            "created_at": profile_data["metadata"]["created_at"]
        }
        
        print(f"✓ {profile_id}")
        print(f"  └─ Instagram: @{display_name}\n")
    
    # Sada ažuriraj warmup bazu sa Instagram usernames
    db = sqlite3.connect("warmup/warmup_data.db")
    cursor = db.cursor()
    
    # Prvo proverite kolone
    cursor.execute("PRAGMA table_info(my_profiles);")
    columns = {col[1] for col in cursor.fetchall()}
    
    # Ako instagram_username kolona ne postoji, dodaj je
    if "instagram_username" not in columns:
        print("[+] Dodavam kolonu 'instagram_username'...")
        cursor.execute("""
            ALTER TABLE my_profiles 
            ADD COLUMN instagram_username TEXT
        """)
    
    # Ažuriraj sve profile
    for profile_id, mapping in profile_mapping.items():
        cursor.execute("""
            UPDATE my_profiles
            SET instagram_username = ?
            WHERE profile_id = ?
        """, (mapping["instagram_username"], profile_id))
        
        print(f"[✓] Ažuriran: {profile_id} → @{mapping['instagram_username']}")
    
    db.commit()
    db.close()
    
    print("\n[✅] Mapiranje završeno!")
    return profile_mapping


if __name__ == "__main__":
    map_browser_profiles_to_warmup()
