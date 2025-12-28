"""
ReportingEngine - Generiše izveštaje i analitiku
"""
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from warmup.database import WarmupDatabase


class ReportingEngine:
    """Generiše detaljne izveštaje sa statistikom"""
    
    def __init__(self, db: WarmupDatabase):
        """
        Inicijalizuj reporting engine
        
        Args:
            db: WarmupDatabase instanca
        """
        self.db = db
        self.reports_dir = Path("warmup/reports")
        self.reports_dir.mkdir(exist_ok=True)
    
    def generate_batch_report(self, batch_id: int) -> Dict:
        """
        Generiši detaljni izveštaj za jedan warmup batch
        
        Args:
            batch_id: ID batch-a
        
        Returns:
            Dict sa kompletnim izveštajem
        """
        batch = self.db.get_batch(batch_id)
        sessions = self.db.get_sessions(batch_id)
        actions = self.db.get_actions(batch_id)
        
        if not batch or not sessions:
            return None
        
        report = {
            "batch_id": batch_id,
            "batch_name": batch['batch_name'],
            "created_at": batch['created_at'],
            "duration_minutes": batch['total_duration_minutes'],
            "status": batch['status'],
            "generated_at": datetime.now().isoformat(),
            
            "summary": {
                "total_profiles": len(sessions),
                "completed_sessions": len([s for s in sessions if s['status'] == 'completed']),
                "running_sessions": len([s for s in sessions if s['status'] == 'running']),
                "pending_sessions": len([s for s in sessions if s['status'] == 'pending']),
                "failed_sessions": len([s for s in sessions if s['status'] == 'failed']),
                "total_actions": len(actions),
                "actions_by_type": self._count_actions_by_type(actions),
                "total_duration_actual_minutes": self._calc_total_duration(sessions)
            },
            
            "per_profile_stats": self._generate_per_profile_stats(sessions, actions),
            
            "inter_profile_interactions": self._generate_interactions_report(batch_id),
            
            "messages_report": self._generate_messages_report(batch_id)
        }
        
        return report
    
    def _count_actions_by_type(self, actions: List[Dict]) -> Dict:
        """Prebrojij akcije po tipu"""
        counts = {}
        
        for action in actions:
            action_type = action['action_type']
            counts[action_type] = counts.get(action_type, 0) + 1
        
        return counts
    
    def _calc_total_duration(self, sessions: List[Dict]) -> int:
        """Izračunaj ukupno trajanje svih sesija"""
        total = 0
        
        for session in sessions:
            if session['actual_duration']:
                total += session['actual_duration']
        
        return total
    
    def _generate_per_profile_stats(self, sessions: List[Dict], actions: List[Dict]) -> List[Dict]:
        """Generiši statistiku po profilu"""
        stats = []
        
        for session in sessions:
            profile = self.db.get_profile(session['profile_id'])
            session_actions = [a for a in actions if a['session_id'] == session['id']]
            
            stats.append({
                "profile_id": session['profile_id'],
                "display_name": profile['display_name'] if profile else session['profile_id'],
                "session_type": session['session_type'],
                "status": session['status'],
                "expected_duration": session['expected_duration'],
                "actual_duration": session['actual_duration'],
                "actions_planned": session['actions_planned'],
                "actions_completed": session['actions_completed'],
                "total_actions_executed": len(session_actions),
                "actions_breakdown": {
                    "likes": len([a for a in session_actions if a['action_type'] == 'like']),
                    "follows": len([a for a in session_actions if a['action_type'] == 'follow']),
                    "unfollows": len([a for a in session_actions if a['action_type'] == 'unfollow']),
                    "saves": len([a for a in session_actions if a['action_type'] == 'save']),
                    "dms": len([a for a in session_actions if a['action_type'] == 'dm']),
                    "scrolls": len([a for a in session_actions if a['action_type'] == 'scroll']),
                    "visits": len([a for a in session_actions if a['action_type'] == 'visit'])
                },
                "success_rate": len([a for a in session_actions if a['success']]) / max(len(session_actions), 1) * 100,
                "average_action_delay": self._calc_avg_delay(session_actions)
            })
        
        return stats
    
    def _calc_avg_delay(self, actions: List[Dict]) -> float:
        """Izračunaj prosečan delay između akcija"""
        if not actions:
            return 0
        
        total_delay = sum(a['delay_before_sec'] or 0 for a in actions)
        return total_delay / len(actions)
    
    def _generate_interactions_report(self, batch_id: int) -> List[Dict]:
        """Generiši izveštaj o inter-profile interakcijama"""
        relationships = self.db.get_relationships()
        report = []
        
        for rel in relationships:
            profile_a = self.db.get_profile(rel['profile_a_id'])
            profile_b = self.db.get_profile(rel['profile_b_id'])
            
            if not profile_a or not profile_b:
                continue
            
            report.append({
                "profile_a": {
                    "id": rel['profile_a_id'],
                    "display_name": profile_a['display_name']
                },
                "profile_b": {
                    "id": rel['profile_b_id'],
                    "display_name": profile_b['display_name']
                },
                "relationship_type": rel['relationship_type'],
                "interaction_frequency": rel['interaction_frequency'],
                "a_follows_b": rel['a_follows_b'],
                "b_follows_a": rel['b_follows_a'],
                "last_interaction": rel['last_interaction']
            })
        
        return report
    
    def _generate_messages_report(self, batch_id: int) -> Dict:
        """Generiši izveštaj o porukama"""
        conversations = []
        
        # Pronađi sve conversations
        all_relationships = self.db.get_relationships()
        
        for rel in all_relationships:
            # Pronađi conversation za ovu relaciju
            messages = self.db.get_messages(
                self._get_conversation_id(rel['profile_a_id'], rel['profile_b_id'])
            ) if self._get_conversation_id(rel['profile_a_id'], rel['profile_b_id']) else []
            
            if messages:
                profile_a = self.db.get_profile(rel['profile_a_id'])
                profile_b = self.db.get_profile(rel['profile_b_id'])
                
                conversations.append({
                    "profile_a_name": profile_a['display_name'] if profile_a else rel['profile_a_id'],
                    "profile_b_name": profile_b['display_name'] if profile_b else rel['profile_b_id'],
                    "message_count": len(messages),
                    "sample_messages": [
                        {
                            "from": m['from_profile_id'][:8],
                            "content": m['content'][:50],
                            "natural_score": m['natural_score']
                        }
                        for m in messages[:3]
                    ]
                })
        
        return {
            "total_conversations": len(conversations),
            "conversations": conversations
        }
    
    def _get_conversation_id(self, profile_a_id: str, profile_b_id: str) -> Optional[int]:
        """Pronađi conversation ID za dva profila"""
        # Ovo bi trebalo optimizovati sa query u bazi
        # Za sada samo vraćamo None
        return None
    
    def export_to_csv(self, batch_id: int, filepath: str = None) -> str:
        """
        Eksportuj rezultate u CSV
        
        Args:
            batch_id: ID batch-a
            filepath: Put do fajla (ako nije specificiran, kreiraj novi)
        
        Returns:
            Putanja do kreiranog fajla
        """
        report = self.generate_batch_report(batch_id)
        
        if not report:
            print("[ERROR] Batch nije pronađen!")
            return None
        
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = self.reports_dir / f"warmup_batch_{batch_id}_{timestamp}.csv"
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow(['WARMUP REPORT'])
            writer.writerow(['Batch Name', report['batch_name']])
            writer.writerow(['Created', report['created_at']])
            writer.writerow(['Total Duration (min)', report['duration_minutes']])
            writer.writerow(['Status', report['status']])
            writer.writerow([])
            
            # Summary
            writer.writerow(['SUMMARY'])
            writer.writerow(['Total Profiles', report['summary']['total_profiles']])
            writer.writerow(['Completed Sessions', report['summary']['completed_sessions']])
            writer.writerow(['Running Sessions', report['summary']['running_sessions']])
            writer.writerow(['Pending Sessions', report['summary']['pending_sessions']])
            writer.writerow(['Failed Sessions', report['summary']['failed_sessions']])
            writer.writerow(['Total Actions', report['summary']['total_actions']])
            writer.writerow(['Total Duration (actual)', report['summary']['total_duration_actual_minutes']])
            writer.writerow([])
            
            # Actions breakdown
            writer.writerow(['ACTIONS BREAKDOWN'])
            for action_type, count in report['summary']['actions_by_type'].items():
                writer.writerow([action_type.capitalize(), count])
            writer.writerow([])
            
            # Per profile stats
            writer.writerow(['PER PROFILE STATISTICS'])
            writer.writerow([
                'Profile ID', 'Display Name', 'Session Type', 'Status',
                'Expected Duration (min)', 'Actual Duration (min)', 'Total Actions',
                'Likes', 'Follows', 'Saves', 'DMs', 'Success Rate (%)'
            ])
            
            for profile_stat in report['per_profile_stats']:
                writer.writerow([
                    profile_stat['profile_id'],
                    profile_stat['display_name'],
                    profile_stat['session_type'],
                    profile_stat['status'],
                    profile_stat['expected_duration'],
                    profile_stat['actual_duration'],
                    profile_stat['total_actions_executed'],
                    profile_stat['actions_breakdown']['likes'],
                    profile_stat['actions_breakdown']['follows'],
                    profile_stat['actions_breakdown']['saves'],
                    profile_stat['actions_breakdown']['dms'],
                    f"{profile_stat['success_rate']:.1f}%"
                ])
        
        print(f"[✓] Izveštaj exportan: {filepath}")
        return str(filepath)
    
    def export_to_json(self, batch_id: int, filepath: str = None) -> str:
        """Eksportuj u JSON"""
        report = self.generate_batch_report(batch_id)
        
        if not report:
            print("[ERROR] Batch nije pronađen!")
            return None
        
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = self.reports_dir / f"warmup_batch_{batch_id}_{timestamp}.json"
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"[✓] JSON izveštaj exportan: {filepath}")
        return str(filepath)
    
    def generate_dashboard_data(self, batch_id: int) -> Dict:
        """Generiši JSON za real-time dashboard"""
        batch = self.db.get_batch(batch_id)
        sessions = self.db.get_sessions(batch_id)
        
        if not batch:
            return None
        
        completed = len([s for s in sessions if s['status'] == 'completed'])
        running = len([s for s in sessions if s['status'] == 'running'])
        
        return {
            "batch_id": batch_id,
            "batch_name": batch['batch_name'],
            "timestamp": datetime.now().isoformat(),
            "progress": {
                "completed": completed,
                "running": running,
                "total": len(sessions),
                "percentage": int((completed + running) / len(sessions) * 100) if sessions else 0
            },
            "status": batch['status'],
            "created_at": batch['created_at'],
            "estimated_completion": self._estimate_completion(sessions, batch)
        }
    
    def _estimate_completion(self, sessions: List[Dict], batch: Dict) -> str:
        """Estimiraj vreme završetka"""
        if not sessions:
            return "N/A"
        
        last_session = max(sessions, key=lambda s: s['start_time'])
        estimated_end = last_session['start_time'] + (last_session['expected_duration'] or 30)
        
        return f"~{estimated_end:.0f} min"
