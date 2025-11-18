"""
Quick test script to diagnose assistant API issues
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

async def test_assistant():
    """Test the assistant processing."""
    print("🧪 Testing Assistant API...")
    
    try:
        # Import after adding to path
        from agents.orchestrator import process_assistant_message
        print("✓ Imported orchestrator")
        
        # Create a test database session
        engine = create_async_engine(
            "sqlite+aiosqlite:///./tasks.db",
            echo=False
        )
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        print("✓ Database engine created")
        
        async with async_session() as db:
            print("\n📨 Processing test message...")
            result = await process_assistant_message(
                content="Show me my tasks for today",
                source_type="manual",
                session_id="test-session",
                db=db
            )
            
            print("\n✅ Success!")
            print(f"Request type: {result.get('request_type')}")
            print(f"Recommended action: {result.get('recommended_action')}")
            print(f"Proposed tasks: {len(result.get('proposed_tasks', []))}")
            
            return True
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_assistant())
    sys.exit(0 if success else 1)
