"""
WarmupDatabase - SQLite baza za čuvanje svih warmup podataka
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any


class WarmupDatabase:
    """SQLite baza za warmup sistem"""
    
    def __init__(self, db_path: str = "warmup/warmup_data.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self.connection = None
        self._init_db()
    
    def _get_connection(self):
        """Pronađi aktivnu konekciju ili kreiraj novu"""
        if self.connection is None:
            self.connection = sqlite3.connect(str(self.db_path))
            self.connection.row_factory = sqlite3.Row
        return self.connection
    
    def _init_db(self):
        """Inicijalizuj bazu sa svim tabelama"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # my_profiles - moji profili
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS my_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                category TEXT,
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                personality TEXT,
                related_profiles TEXT,
                metadata TEXT,
                UNIQUE(profile_id)
            )
        ''')
        
        # warmup_batches - batch-evi zagrevanja
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS warmup_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_name TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                total_duration_minutes INTEGER,
                status TEXT DEFAULT 'pending',
                profiles_count INTEGER,
                config TEXT,
                notes TEXT
            )
        ''')
        
        # warmup_sessions - sesije zagrevanja po profilu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS warmup_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL,
                profile_id TEXT NOT NULL,
                session_type TEXT,
                start_time REAL,
                actual_start_time DATETIME,
                expected_duration INTEGER,
                actual_duration INTEGER,
                status TEXT DEFAULT 'pending',
                actions_planned TEXT,
                actions_completed TEXT,
                intensity_level REAL,
                notes TEXT,
                FOREIGN KEY (batch_id) REFERENCES warmup_batches(id),
                FOREIGN KEY (profile_id) REFERENCES my_profiles(profile_id)
            )
        ''')
        
        # actions - sve akcije tokom warmup-a
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                profile_id TEXT NOT NULL,
                action_type TEXT,
                target_profile_id TEXT,
                target_post_id TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN,
                delay_before_sec INTEGER,
                duration_sec INTEGER,
                metadata TEXT,
                FOREIGN KEY (session_id) REFERENCES warmup_sessions(id)
            )
        ''')
        
        # inter_profile_relationships - relacije između mojih profila
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inter_profile_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_a_id TEXT NOT NULL,
                profile_b_id TEXT NOT NULL,
                relationship_type TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                a_follows_b BOOLEAN DEFAULT 0,
                b_follows_a BOOLEAN DEFAULT 0,
                interaction_frequency TEXT,
                last_interaction DATETIME,
                notes TEXT,
                UNIQUE(profile_a_id, profile_b_id),
                FOREIGN KEY (profile_a_id) REFERENCES my_profiles(profile_id),
                FOREIGN KEY (profile_b_id) REFERENCES my_profiles(profile_id)
            )
        ''')
        
        # messages - DM poruke između profila
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                from_profile_id TEXT NOT NULL,
                to_profile_id TEXT NOT NULL,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                read BOOLEAN DEFAULT 0,
                message_type TEXT,
                natural_score INTEGER,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        ''')
        
        # conversations - razgovori između profila
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_a_id TEXT NOT NULL,
                profile_b_id TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_message_at DATETIME,
                message_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                conversation_theme TEXT,
                UNIQUE(profile_a_id, profile_b_id),
                FOREIGN KEY (profile_a_id) REFERENCES my_profiles(profile_id),
                FOREIGN KEY (profile_b_id) REFERENCES my_profiles(profile_id)
            )
        ''')
        
        # analytics_daily - dnevna statistika
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL,
                profile_id TEXT NOT NULL,
                date DATE,
                actions_count INTEGER DEFAULT 0,
                likes_given INTEGER DEFAULT 0,
                follows_given INTEGER DEFAULT 0,
                messages_sent INTEGER DEFAULT 0,
                new_followers INTEGER DEFAULT 0,
                new_following INTEGER DEFAULT 0,
                session_count INTEGER DEFAULT 0,
                risk_score INTEGER DEFAULT 0,
                UNIQUE(batch_id, profile_id, date),
                FOREIGN KEY (batch_id) REFERENCES warmup_batches(id),
                FOREIGN KEY (profile_id) REFERENCES my_profiles(profile_id)
            )
        ''')
        
        conn.commit()
    
    # ========== PROFILE METHODS ==========
    
    def add_profile(self, profile_id: str, display_name: str, category: str = None, 
                   personality: Dict = None, related_profiles: List[str] = None) -> int:
        """Dodaj novi profil"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO my_profiles 
            (profile_id, display_name, category, personality, related_profiles)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            profile_id,
            display_name,
            category,
            json.dumps(personality) if personality else None,
            json.dumps(related_profiles) if related_profiles else None
        ))
        
        conn.commit()
        return cursor.lastrowid
    
    def get_my_profiles(self, is_active: bool = True) -> List[Dict]:
        """Preuzmi sve moje profile"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM my_profiles'
        params = []
        
        if is_active is not None:
            query += ' WHERE is_active = ?'
            params.append(1 if is_active else 0)
        
        cursor.execute(query, params)
        
        profiles = []
        for row in cursor.fetchall():
            profile = dict(row)
            if profile['personality']:
                profile['personality'] = json.loads(profile['personality'])
            if profile['related_profiles']:
                profile['related_profiles'] = json.loads(profile['related_profiles'])
            profiles.append(profile)
        
        return profiles
    
    def get_profile(self, profile_id: str) -> Optional[Dict]:
        """Preuzmi jedan profil"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM my_profiles WHERE profile_id = ?', (profile_id,))
        row = cursor.fetchone()
        
        if row:
            profile = dict(row)
            if profile['personality']:
                profile['personality'] = json.loads(profile['personality'])
            if profile['related_profiles']:
                profile['related_profiles'] = json.loads(profile['related_profiles'])
            return profile
        
        return None
    
    # ========== WARMUP BATCH METHODS ==========
    
    def create_warmup_batch(self, batch_name: str, total_duration_minutes: int,
                           profiles_count: int, config: Dict = None) -> int:
        """Kreiraj novi warmup batch"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO warmup_batches 
            (batch_name, total_duration_minutes, profiles_count, config, status)
            VALUES (?, ?, ?, ?, 'pending')
        ''', (
            batch_name,
            total_duration_minutes,
            profiles_count,
            json.dumps(config) if config else None
        ))
        
        conn.commit()
        return cursor.lastrowid
    
    def get_batch(self, batch_id: int) -> Optional[Dict]:
        """Preuzmi jedan batch"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM warmup_batches WHERE id = ?', (batch_id,))
        row = cursor.fetchone()
        
        if row:
            batch = dict(row)
            if batch['config']:
                batch['config'] = json.loads(batch['config'])
            return batch
        
        return None
    
    def update_batch_status(self, batch_id: int, status: str):
        """Ažuriraj status batch-a"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('UPDATE warmup_batches SET status = ? WHERE id = ?', (status, batch_id))
        conn.commit()
    
    # ========== SESSION METHODS ==========
    
    def create_session(self, batch_id: int, profile_id: str, session_type: str,
                      start_time: float, expected_duration: int, actions_planned: Dict) -> int:
        """Kreiraj novu warmup sesiju"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO warmup_sessions
            (batch_id, profile_id, session_type, start_time, expected_duration, actions_planned, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
        ''', (
            batch_id,
            profile_id,
            session_type,
            start_time,
            expected_duration,
            json.dumps(actions_planned)
        ))
        
        conn.commit()
        return cursor.lastrowid
    
    def get_sessions(self, batch_id: int, status: str = None) -> List[Dict]:
        """Preuzmi sve sesije za jedan batch"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM warmup_sessions WHERE batch_id = ?'
        params = [batch_id]
        
        if status:
            query += ' AND status = ?'
            params.append(status)
        
        cursor.execute(query, params)
        
        sessions = []
        for row in cursor.fetchall():
            session = dict(row)
            if session['actions_planned']:
                session['actions_planned'] = json.loads(session['actions_planned'])
            if session['actions_completed']:
                session['actions_completed'] = json.loads(session['actions_completed'])
            sessions.append(session)
        
        return sessions
    
    def update_session_status(self, session_id: int, status: str, actual_start: datetime = None,
                             actual_duration: int = None, actions_completed: Dict = None):
        """Ažuriraj status sesije"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE warmup_sessions
            SET status = ?, actual_start_time = ?, actual_duration = ?, actions_completed = ?
            WHERE id = ?
        ''', (
            status,
            actual_start,
            actual_duration,
            json.dumps(actions_completed) if actions_completed else None,
            session_id
        ))
        
        conn.commit()
    
    # ========== ACTION METHODS ==========
    
    def log_action(self, session_id: int, profile_id: str, action_type: str,
                  success: bool, delay_before_sec: int = 0, duration_sec: int = 0,
                  target_profile_id: str = None, target_post_id: str = None) -> int:
        """Zabelezi akciju"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO actions
            (session_id, profile_id, action_type, target_profile_id, target_post_id,
             success, delay_before_sec, duration_sec)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            profile_id,
            action_type,
            target_profile_id,
            target_post_id,
            success,
            delay_before_sec,
            duration_sec
        ))
        
        conn.commit()
        return cursor.lastrowid
    
    def get_actions(self, batch_id: int = None, session_id: int = None,
                   profile_id: str = None) -> List[Dict]:
        """Preuzmi akcije"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT a.* FROM actions a
            LEFT JOIN warmup_sessions ws ON a.session_id = ws.id
            WHERE 1=1
        '''
        params = []
        
        if batch_id:
            query += ' AND ws.batch_id = ?'
            params.append(batch_id)
        if session_id:
            query += ' AND a.session_id = ?'
            params.append(session_id)
        if profile_id:
            query += ' AND a.profile_id = ?'
            params.append(profile_id)
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    # ========== RELATIONSHIP METHODS ==========
    
    def add_relationship(self, profile_a_id: str, profile_b_id: str,
                        relationship_type: str, interaction_frequency: str = "rare"):
        """Dodaj relaciju između profila"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO inter_profile_relationships
            (profile_a_id, profile_b_id, relationship_type, interaction_frequency)
            VALUES (?, ?, ?, ?)
        ''', (profile_a_id, profile_b_id, relationship_type, interaction_frequency))
        
        conn.commit()
    
    def get_relationships(self, profile_id: str = None) -> List[Dict]:
        """Preuzmi relacije"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if profile_id:
            cursor.execute('''
                SELECT * FROM inter_profile_relationships
                WHERE profile_a_id = ? OR profile_b_id = ?
            ''', (profile_id, profile_id))
        else:
            cursor.execute('SELECT * FROM inter_profile_relationships')
        
        return [dict(row) for row in cursor.fetchall()]
    
    # ========== MESSAGE METHODS ==========
    
    def create_conversation(self, profile_a_id: str, profile_b_id: str,
                           conversation_theme: str = None) -> int:
        """Kreiraj razgovor između dva profila"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO conversations
            (profile_a_id, profile_b_id, conversation_theme)
            VALUES (?, ?, ?)
        ''', (profile_a_id, profile_b_id, conversation_theme))
        
        conn.commit()
        
        cursor.execute(
            'SELECT id FROM conversations WHERE profile_a_id = ? AND profile_b_id = ?',
            (profile_a_id, profile_b_id)
        )
        return cursor.fetchone()[0]
    
    def add_message(self, conversation_id: int, from_profile_id: str,
                   to_profile_id: str, content: str, message_type: str = "text",
                   natural_score: int = 80) -> int:
        """Dodaj poruku u razgovor"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO messages
            (conversation_id, from_profile_id, to_profile_id, content, message_type, natural_score)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (conversation_id, from_profile_id, to_profile_id, content, message_type, natural_score))
        
        # Ažuriraj conversation metadata
        cursor.execute('''
            UPDATE conversations
            SET last_message_at = CURRENT_TIMESTAMP,
                message_count = message_count + 1
            WHERE id = ?
        ''', (conversation_id,))
        
        conn.commit()
        return cursor.lastrowid
    
    def get_messages(self, conversation_id: int) -> List[Dict]:
        """Preuzmi poruke iz razgovora"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC',
            (conversation_id,)
        )
        
        return [dict(row) for row in cursor.fetchall()]
    
    # ========== ANALYTICS METHODS ==========
    
    def log_daily_analytics(self, batch_id: int, profile_id: str, date: str,
                           actions_count: int = 0, likes_given: int = 0,
                           follows_given: int = 0, messages_sent: int = 0):
        """Zabelezi dnevnu statistiku"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO analytics_daily
            (batch_id, profile_id, date, actions_count, likes_given, follows_given, messages_sent)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (batch_id, profile_id, date, actions_count, likes_given, follows_given, messages_sent))
        
        conn.commit()
    
    def get_analytics(self, batch_id: int, profile_id: str = None) -> List[Dict]:
        """Preuzmi analitiku"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if profile_id:
            cursor.execute(
                'SELECT * FROM analytics_daily WHERE batch_id = ? AND profile_id = ? ORDER BY date DESC',
                (batch_id, profile_id)
            )
        else:
            cursor.execute(
                'SELECT * FROM analytics_daily WHERE batch_id = ? ORDER BY date DESC',
                (batch_id,)
            )
        
        return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        """Zatvori bazu"""
        if self.connection:
            self.connection.close()
            self.connection = None
