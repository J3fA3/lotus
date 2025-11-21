"""
Test Gemini Integration - Verify Gemini API is working
"""
import asyncio
from dotenv import load_dotenv

load_dotenv()


async def test_gemini():
    """Test Gemini client directly."""
    print("=" * 60)
    print("🧪 TESTING GEMINI INTEGRATION")
    print("=" * 60)
    
    # Test 1: Check environment
    print("\n1️⃣ Environment Variables")
    import os
    api_key = os.getenv("GOOGLE_AI_API_KEY", "")
    print(f"   API Key configured: {bool(api_key)}")
    print(f"   API Key (first 20): {api_key[:20]}..." if api_key else "   No API key")
    print(f"   Model: {os.getenv('GEMINI_MODEL', 'not set')}")
    
    # Test 2: Initialize client
    print("\n2️⃣ Initialize Gemini Client")
    from services.gemini_client import get_gemini_client
    client = get_gemini_client()
    print(f"   Client available: {client.available}")
    print(f"   Model name: {client.model_name}")
    
    if not client.available:
        print("\n❌ Gemini client not available!")
        return False
    
    # Test 3: Simple text generation
    print("\n3️⃣ Test Simple Generation")
    try:
        result = await client.generate(
            prompt="Say 'Hello from Gemini!' in exactly those words.",
            max_tokens=50
        )
        print(f"   Response: {result[:100]}")
        print("   ✅ Text generation works!")
    except Exception as e:
        print(f"   ❌ Text generation failed: {e}")
        return False
    
    # Test 4: Structured output
    print("\n4️⃣ Test Structured Output")
    try:
        from pydantic import BaseModel
        
        class TaskClassification(BaseModel):
            urgency: str  # "high", "medium", "low"
            category: str
            
        result = await client.generate_structured(
            prompt="Classify this task: 'Send urgent email to CEO'. Return urgency (high/medium/low) and category.",
            schema=TaskClassification
        )
        print(f"   Urgency: {result.urgency}")
        print(f"   Category: {result.category}")
        print("   ✅ Structured output works!")
    except Exception as e:
        print(f"   ❌ Structured output failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 5: Usage stats
    print("\n5️⃣ Usage Statistics")
    print(f"   Total requests: {client.usage_stats.total_requests}")
    print(f"   Total cost: ${client.usage_stats.total_cost_usd:.6f}")
    
    print("\n" + "=" * 60)
    print("✅ ALL GEMINI TESTS PASSED!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_gemini())
    exit(0 if success else 1)
