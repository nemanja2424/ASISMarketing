"""
PersonalityEngine - Generiše i upravlja personalnostima profila
"""
import random
from typing import Dict, List


class PersonalityEngine:
    """Kreira jedinstvene personality-je za profile"""
    
    TONES = {
        "casual": {
            "emoji_usage": (40, 70),
            "message_style": "opušteno",
            "interests": ["fitness", "travel", "food", "lifestyle", "sport"]
        },
        "friendly": {
            "emoji_usage": (60, 90),
            "message_style": "prijateljski",
            "interests": ["life", "fun", "people", "stories", "lifestyle"]
        },
        "sporty": {
            "emoji_usage": (30, 60),
            "message_style": "motivisujuće",
            "interests": ["fitness", "sports", "gym", "training", "health"]
        },
        "formal": {
            "emoji_usage": (0, 20),
            "message_style": "profesionalno",
            "interests": ["business", "tech", "career", "growth", "innovation"]
        }
    }
    
    INTERESTS = [
        "fitness", "travel", "food", "gaming", "tech",
        "fotografija", "moda", "muzika", "putovanja", "sport",
        "auto", "kulinacija", "lifestyle", "wellness", "zdravlje",
        "umetnost", "kultura", "film", "serije", "glazba",
        "books", "čitanje", "pisanje", "kreativnost"
    ]
    
    ACTIVITY_LEVELS = ["low", "medium", "high"]
    
    def __init__(self):
        """Inicijalizuj personality engine"""
        random.seed()
    
    def generate_personality(self, profile_id: str = None) -> Dict:
        """
        Kreiraj novu personality za profil
        
        Returns:
            Dict sa svim personality atributima
        """
        tone = random.choice(list(self.TONES.keys()))
        tone_config = self.TONES[tone]
        
        personality = {
            "tone": tone,
            "emoji_usage": random.randint(*tone_config['emoji_usage']),
            "interests": random.sample(self.INTERESTS, k=random.randint(2, 4)),
            "activity_level": random.choice(self.ACTIVITY_LEVELS),
            "timezone": "Europe/Belgrade",
            "sleep_start_hour": random.randint(22, 24),
            "sleep_end_hour": random.randint(7, 9),
            "message_style": tone_config['message_style']
        }
        
        return personality
    
    def is_user_active(self, personality: Dict, hour: int) -> bool:
        """
        Proverite da li je korisnik aktivan u zadati sat
        
        Args:
            personality: personality dict
            hour: sat (0-23)
        
        Returns:
            bool - da li je korisnik aktivan
        """
        sleep_start = personality['sleep_start_hour']
        sleep_end = personality['sleep_end_hour']
        
        if sleep_start < sleep_end:
            # Normalno: spava između 23-7
            return not (sleep_start <= hour < sleep_end)
        else:
            # Noću: spava između 23-7 (preko ponoći)
            return not (hour >= sleep_start or hour < sleep_end)
    
    def get_activity_variance(self, activity_level: str) -> tuple:
        """
        Pronađi range akcija za dati activity level
        
        Args:
            activity_level: "low", "medium", "high"
        
        Returns:
            (min_actions, max_actions)
        """
        ranges = {
            "low": (3, 8),
            "medium": (8, 15),
            "high": (15, 25)
        }
        return ranges.get(activity_level, (8, 15))
    
    def get_emoji_list(self) -> List[str]:
        """Vrati listu dostupnih emoji-ja"""
        return [
            '😄', '👍', '❤️', '🔥', '✨', '💪', '🎯',
            '👏', '😍', '🙌', '😂', '👀', '💯', '🚀',
            '⭐', '🎉', '💎', '👑'
        ]
    
    def should_add_emoji(self, emoji_usage_percent: int) -> bool:
        """
        Proceni da li dodati emoji na osnovu personality emoji_usage
        
        Args:
            emoji_usage_percent: procenat (0-100)
        
        Returns:
            bool - da li dodati emoji
        """
        return random.randint(0, 100) < emoji_usage_percent
    
    def get_random_emoji(self) -> str:
        """Vrati random emoji"""
        return random.choice(self.get_emoji_list())
    
    def format_message_by_personality(self, base_message: str, personality: Dict) -> str:
        """
        Formatiraj poruku prema personality
        
        Args:
            base_message: osnovna poruka
            personality: personality dict
        
        Returns:
            Formairana poruka sa emoji-jima ako je potrebno
        """
        if self.should_add_emoji(personality['emoji_usage']):
            emoji = self.get_random_emoji()
            return f"{base_message} {emoji}"
        
        return base_message
    
    def get_typical_interests_by_tone(self, tone: str) -> List[str]:
        """Pronađi tipične interese za dati tone"""
        return self.TONES.get(tone, {}).get('interests', self.INTERESTS)
