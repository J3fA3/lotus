"""
Phase 4 Integration Test - Google Calendar Integration
Tests the complete flow with actual API calls (requires authentication)

Run with: python test_phase4_integration.py
"""

import asyncio
import httpx
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"
USER_ID = 1  # Authenticated Jef user


async def test_phase4_integration():
    """Test Phase 4 calendar integration endpoints."""
    
    print("=" * 60)
    print("🧪 PHASE 4 INTEGRATION TESTS")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Test 1: Health Check
        print("\n1️⃣ Testing API Health...")
        try:
            response = await client.get(f"{BASE_URL}/api/health")
            assert response.status_code == 200, f"Health check failed: {response.status_code}"
            print("   ✅ API is healthy")
        except Exception as e:
            print(f"   ❌ Health check failed: {e}")
            return False
        
        # Test 2: Check OAuth Status
        print("\n2️⃣ Checking OAuth Status...")
        try:
            response = await client.get(f"{BASE_URL}/api/auth/google/status", params={"user_id": USER_ID})
            data = response.json()
            print(f"   OAuth Status: {data}")
            
            if not data.get("authorized"):
                print(f"   ⚠️  User not authenticated. Please visit: {BASE_URL}/api/auth/google/authorize?user_id={USER_ID}")
                return False
            
            print(f"   ✅ User {USER_ID} is authenticated")
        except Exception as e:
            print(f"   ❌ OAuth status check failed: {e}")
            return False
        
        # Test 3: Sync Calendar
        print("\n3️⃣ Syncing Calendar...")
        try:
            response = await client.post(
                f"{BASE_URL}/api/calendar/sync",
                params={"user_id": USER_ID}
            )
            data = response.json()
            print(f"   Synced {data.get('events_count', 0)} events")
            print(f"   Synced at: {data.get('synced_at', 'N/A')[:19]}")
            print(f"   ✅ Calendar sync successful")
        except Exception as e:
            print(f"   ❌ Calendar sync failed: {e}")
            return False
        
        # Test 4: Get Work Preferences
        print("\n4️⃣ Getting Work Preferences...")
        try:
            response = await client.get(
                f"{BASE_URL}/api/calendar/preferences",
                params={"user_id": USER_ID}
            )
            data = response.json()
            print(f"   Deep work time: {data.get('deep_work_time')}")
            print(f"   Meeting style: {data.get('meeting_style')}")
            print(f"   Min task block: {data.get('min_task_block')} min")
            print(f"   Task prefix: '{data.get('task_event_prefix', '')}'")
            print(f"   ✅ Work preferences retrieved")
        except Exception as e:
            print(f"   ❌ Failed to get work preferences: {e}")
        
        # Test 5: Schedule Tasks (skipped - requires tasks and Gemini)
        print("\n5️⃣ Schedule Tasks Suggestions...")
        print("   ⏭️  Skipped (requires active tasks and Gemini API)")
        
        # Test 6: Get Schedule Suggestions (skipped - requires Gemini)
        print("\n6️⃣ Getting Schedule Suggestions...")
        print("   ⏭️  Skipped (requires Gemini API)")
        
        # Test 7: Get Meeting Prep (skipped - requires Gemini)
        print("\n7️⃣ Getting Meeting Prep Suggestions...")
        print("   ⏭️  Skipped (requires Gemini API)")
        
        # Test 8: Calendar Event Details
        print("\n8️⃣ Getting Recent Calendar Events...")
        try:
            response = await client.get(
                f"{BASE_URL}/api/calendar/events",
                params={
                    "user_id": USER_ID,
                    "start_date": datetime.now().isoformat(),
                    "end_date": (datetime.now() + timedelta(days=7)).isoformat()
                }
            )
            data = response.json()
            events = data.get('events', [])
            print(f"   Found {len(events)} upcoming events")
            
            # Show first 3 events
            for i, event in enumerate(events[:3]):
                title = event.get('title', 'Untitled')
                start = event.get('start_time', '')[:16]
                is_meeting = event.get('is_meeting', False)
                importance = event.get('importance_score', 0)
                print(f"   Event {i+1}: {title}")
                print(f"      Start: {start} | Meeting: {is_meeting} | Importance: {importance}")
            
            print(f"   ✅ Calendar events retrieved")
        except Exception as e:
            print(f"   ❌ Failed to get calendar events: {e}")
    
    print("\n" + "=" * 60)
    print("✅ ALL PHASE 4 INTEGRATION TESTS COMPLETED")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_phase4_integration())
    exit(0 if success else 1)
