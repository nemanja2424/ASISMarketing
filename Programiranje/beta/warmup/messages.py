"""
MessageGenerator - Generiše Srpske poruke između profila
"""
import random
from typing import Dict, List, Optional


class MessageGenerator:
    """Generiše prirodne poruke na Srpskom jeziku"""
    
    MESSAGES_DB = {
        "greeting": [
            "Ej! 😄",
            "Zdravo! 👋",
            "Što ima? 😊",
            "Bok! 🙌",
            "Heyyy",
            "Sve OK? 👍"
        ],
        "reaction_positive": [
            "🔥🔥🔥",
            "Odličan sadržaj! 💪",
            "Wow! 😍",
            "❤️❤️",
            "Top! ✨",
            "Sviđa mi se!",
            "Super! 👏"
        ],
        "reaction_fitness": [
            "Sjajan trening! 💪",
            "Respect! 🙏",
            "To! 🔥",
            "Odličan! 💯",
            "Solid! 👊",
            "Go bro! 💪",
            "Amazing gains! 🏆"
        ],
        "reaction_gaming": [
            "Koji move! 🎮",
            "GG! 👑",
            "Pro! 🎯",
            "Hahahaha 😂",
            "Sjajno! 🎪",
            "Crazy play! 🔥",
            "Too good! 💯"
        ],
        "reaction_travel": [
            "Koja lepota! 😍",
            "Dream destination! 🌴",
            "Moram da vidim! 👀",
            "Fakat? 🤩",
            "Prekrasno! ✈️",
            "Gde je ovo? 👀"
        ],
        "reaction_food": [
            "Izgledal je umešno! 😋",
            "Lupit će! 🤤",
            "Moram da se oglasi! 👅",
            "Recept? 👀",
            "Predivno! 🔥"
        ],
        "casual_engagement": [
            "Super! 👍",
            "❤️",
            "😍",
            "🔥",
            "💯",
            "+1",
            "A+"
        ],
        "question": [
            "Gde si to bio? 👀",
            "Kako to radiš? 🤔",
            "Jel to teško? 💭",
            "Pro tip? 👀",
            "Kako si stigao tamo?"
        ],
        "follow_response": [
            "Prati me! 👍",
            "Hvala! ❤️",
            "Let's go! 🚀",
            "Thanks! 🙌",
            "Awesome! 💪"
        ]
    }
    
    def __init__(self, personality_engine=None):
        """
        Inicijalizuj message generator
        
        Args:
            personality_engine: PersonalityEngine instanca (optional)
        """
        self.personality_engine = personality_engine
    
    def generate_message(self, from_profile: Dict, to_profile: Dict,
                        context: Dict) -> str:
        """
        Generiši poruku između dva profila
        
        Args:
            from_profile: Dict sa profile_id, personality, itd
            to_profile: Dict sa profile_id, personality, itd
            context: {
                "trigger": "follow" | "like_post" | "random_dm" | "response",
                "target_interests": ["fitness", "travel"],
                "sentiment": "positive" | "neutral" | "negative"
            }
        
        Returns:
            Generisana poruka na Srpskom
        """
        from_personality = from_profile.get('personality', {})
        trigger = context.get('trigger', 'random_dm')
        target_interests = context.get('target_interests', [])
        
        # Odaberi tip poruke
        if trigger == 'follow':
            msg_type = 'greeting'
        elif trigger == 'like_post':
            # Odaberi na osnovu interests
            if target_interests:
                interest = target_interests[0] if target_interests else 'casual'
                
                if any(x in interest for x in ['fitness', 'gym', 'sport', 'training']):
                    msg_type = 'reaction_fitness'
                elif any(x in interest for x in ['gaming', 'game', 'esports']):
                    msg_type = 'reaction_gaming'
                elif any(x in interest for x in ['travel', 'putovanje']):
                    msg_type = 'reaction_travel'
                elif any(x in interest for x in ['food', 'kulinacija', 'jelo']):
                    msg_type = 'reaction_food'
                else:
                    msg_type = 'reaction_positive'
            else:
                msg_type = 'reaction_positive'
        elif trigger == 'response':
            msg_type = 'follow_response'
        elif trigger == 'question':
            msg_type = 'question'
        else:
            msg_type = 'casual_engagement'
        
        # Odaberi poruku iz baze
        messages = self.MESSAGES_DB.get(msg_type, self.MESSAGES_DB['casual_engagement'])
        base_msg = random.choice(messages)
        
        # Dodaj emoji na osnovu personality
        if self.personality_engine and from_personality:
            emoji_usage = from_personality.get('emoji_usage', 50)
            if random.randint(0, 100) < emoji_usage:
                if '🔥' not in base_msg and '❤️' not in base_msg and not any(ord(c) > 127 for c in base_msg):
                    emoji = self.personality_engine.get_random_emoji()
                    base_msg += ' ' + emoji
        
        return base_msg
    
    def generate_dm_conversation(self, from_profile: Dict, to_profile: Dict,
                                initial_trigger: str = "follow") -> List[Dict]:
        """
        Kreiraj celu konverzaciju između dva profila
        
        Args:
            from_profile: Profil koji inicijatoruje
            to_profile: Profil koji prima poruku
            initial_trigger: Tip inicijalnog triggera
        
        Returns:
            Lista poruka sa timestamp-ima
        """
        conversation = []
        
        # Inicijalna poruka
        initial_msg = self.generate_message(
            from_profile, to_profile,
            {
                "trigger": initial_trigger,
                "target_interests": to_profile.get('personality', {}).get('interests', [])
            }
        )
        
        conversation.append({
            "from_profile_id": from_profile['profile_id'],
            "to_profile_id": to_profile['profile_id'],
            "content": initial_msg,
            "delay_minutes": 0,
            "message_type": initial_trigger
        })
        
        # 60% šansa da će to_profile odgovoriti
        if random.random() < 0.6:
            response_delay = random.randint(5, 120)  # 5 min do 2h
            
            response_msg = self.generate_message(
                to_profile, from_profile,
                {
                    "trigger": "response",
                    "target_interests": from_profile.get('personality', {}).get('interests', [])
                }
            )
            
            conversation.append({
                "from_profile_id": to_profile['profile_id'],
                "to_profile_id": from_profile['profile_id'],
                "content": response_msg,
                "delay_minutes": response_delay,
                "message_type": "response"
            })
        
        return conversation
    
    def get_message_by_type(self, message_type: str) -> str:
        """Preuzmi nasumičnu poruku sa tipa"""
        messages = self.MESSAGES_DB.get(message_type, [])
        if messages:
            return random.choice(messages)
        return "Super! 👍"
    
    def get_all_message_types(self) -> List[str]:
        """Pronađi sve dostupne tipove poruka"""
        return list(self.MESSAGES_DB.keys())
