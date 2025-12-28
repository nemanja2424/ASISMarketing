#!/usr/bin/env python3
"""
Test skriptu za Warmup sistem
"""
import sys
from pathlib import Path

# Dodaj project root u path
sys.path.insert(0, str(Path(__file__).parent))

from warmup import WarmupDatabase, WarmupOrchestrator, PersonalityEngine, MessageGenerator, ReportingEngine


def test_database():
    """Test WarmupDatabase"""
    print("\n[TEST] WarmupDatabase")
    
    db = WarmupDatabase()
    
    # Test profil
    profile_id = db.add_profile(
        folder_name="test_profile",
        display_name="Test Profil",
        username="test.user",
        password="xxxx",
        personality={"tone": "friendly", "activity_level": "medium"}
    )
    
    print(f"  ✓ Profile created: {profile_id}")
    
    # Test batch
    batch_id = db.create_warmup_batch(
        batch_name="Test Batch",
        total_profiles=1,
        total_duration_minutes=60
    )
    
    print(f"  ✓ Batch created: {batch_id}")
    
    # Test session
    session_id = db.create_session(
        batch_id=batch_id,
        profile_id=profile_id,
        session_type="engagement",
        start_time=0,
        expected_duration=30,
        actions_planned=15
    )
    
    print(f"  ✓ Session created: {session_id}")
    
    # Test action
    action_id = db.log_action(
        session_id=session_id,
        action_type="like",
        delay_before_sec=5,
        success=True,
        details={"post_id": "123"}
    )
    
    print(f"  ✓ Action logged: {action_id}")
    
    return db, profile_id, batch_id


def test_personality():
    """Test PersonalityEngine"""
    print("\n[TEST] PersonalityEngine")
    
    engine = PersonalityEngine()
    
    # Generiši personality
    personality = engine.generate_personality()
    
    print(f"  ✓ Personality generated:")
    print(f"    - Tone: {personality['tone']}")
    print(f"    - Interests: {', '.join(personality['interests'][:3])}...")
    print(f"    - Activity Level: {personality['activity_level']}")


def test_messages():
    """Test MessageGenerator"""
    print("\n[TEST] MessageGenerator")
    
    personality_engine = PersonalityEngine()
    msg_generator = MessageGenerator(personality_engine)
    
    # Generiši poruke
    message = msg_generator.generate_message(
        trigger="follow",
        context_interests=["fitness", "travel"]
    )
    
    print(f"  ✓ Message generated: '{message}'")
    
    # Generiši DM conversation
    personality1 = personality_engine.generate_personality()
    personality2 = personality_engine.generate_personality()
    
    conversation = msg_generator.generate_dm_conversation(
        personality1,
        personality2,
        trigger="follow"
    )
    
    print(f"  ✓ DM Conversation generated: {len(conversation)} messages")


def test_orchestrator(db, profile_id, batch_id):
    """Test WarmupOrchestrator"""
    print("\n[TEST] WarmupOrchestrator")
    
    orchestrator = WarmupOrchestrator(db=db)
    
    # Test status
    status = orchestrator.get_warmup_status(batch_id)
    
    print(f"  ✓ Warmup Status:")
    print(f"    - Batch: {status['batch_name']}")
    print(f"    - Status: {status['status']}")
    print(f"    - Progress: {status['progress']}")
    
    # Test start
    success = orchestrator.start_warmup_batch(batch_id)
    print(f"  ✓ Batch started: {success}")
    
    # Test pause
    success = orchestrator.pause_warmup_batch(batch_id)
    print(f"  ✓ Batch paused: {success}")
    
    # Test resume
    success = orchestrator.resume_warmup_batch(batch_id)
    print(f"  ✓ Batch resumed: {success}")


def test_reporting(db, batch_id):
    """Test ReportingEngine"""
    print("\n[TEST] ReportingEngine")
    
    reporting = ReportingEngine(db)
    
    # Test batch report
    report = reporting.generate_batch_report(batch_id)
    
    print(f"  ✓ Batch Report generated:")
    print(f"    - Total Profiles: {report['summary']['total_profiles']}")
    print(f"    - Total Actions: {report['summary']['total_actions']}")
    
    # Test dashboard
    dashboard = reporting.generate_dashboard_data(batch_id)
    
    print(f"  ✓ Dashboard data generated:")
    print(f"    - Progress: {dashboard['progress']['percentage']}%")
    print(f"    - Status: {dashboard['status']}")


def main():
    """Pokreni sve testove"""
    print("=" * 50)
    print("WARMUP SYSTEM TESTS")
    print("=" * 50)
    
    try:
        db, profile_id, batch_id = test_database()
        test_personality()
        test_messages()
        test_orchestrator(db, profile_id, batch_id)
        test_reporting(db, batch_id)
        
        print("\n" + "=" * 50)
        print("✓ ALL TESTS PASSED!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
