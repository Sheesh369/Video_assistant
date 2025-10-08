"""
Test script to discover which HeyGen avatars work with your API key
Run this to find out which avatars you can actually use
"""
import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")

# Common free/public avatars to test
TEST_AVATARS = [
    # Public avatars that are commonly available
    {"id": "Kristin_public_3_20240108", "name": "Kristin", "voice": "1e0813c944f84495a4107e7bf87d44c1"},
    {"id": "Tyler-incasualsuit-20220721", "name": "Tyler", "voice": "1bd001e7e50f421d891986aad5158bc8"},
    {"id": "josh_lite3_20230714", "name": "Josh Lite", "voice": "da04d9a268ac468887a68359908e55b7"},
    {"id": "Angela-inblackskirt-20221021", "name": "Angela", "voice": "1e0813c944f84495a4107e7bf87d44c1"},
    {"id": "Wayne_20240711", "name": "Wayne", "voice": "1bd001e7e50f421d891986aad5158bc8"},
    
    # Try the ones you mentioned
    {"id": "Anthony_Chair_Sitting_public", "name": "Anthony", "voice": "0009aabefe3a4553bc581d837b6268cb"},
    {"id": "Pedro_Chair_Sitting_public", "name": "Pedro", "voice": "e17b99e1b86e47e8b7f4cae0f806aa78"},
    {"id": "Alessandra_Chair_Sitting_public", "name": "Alessandra", "voice": "1edc5e7338eb4e37b26dc8eb3f9b7e9c"},
    {"id": "Amina_Chair_Sitting_public", "name": "Amina", "voice": "1edc5e7338eb4e37b26dc8eb3f9b7e9c"},
    {"id": "Anastasia_Chair_Sitting_public", "name": "Anastasia", "voice": "1edc5e7338eb4e37b26dc8eb3f9b7e9c"},
]

async def test_avatar(client, avatar_id, voice_id, avatar_name):
    """Test if an avatar can be used with your API key"""
    try:
        print(f"\n{'='*60}")
        print(f"Testing: {avatar_name} ({avatar_id})")
        print(f"Voice: {voice_id}")
        print(f"{'='*60}")
        
        # Try to create a session with this avatar
        response = await client.post(
            "https://api.heygen.com/v1/streaming.new",
            json={
                "quality": "low",  # Use low quality for testing
                "avatar_name": avatar_id,
                "voice": {
                    "voice_id": voice_id
                },
                "version": "v2"
            },
            timeout=10.0
        )
        
        result = response.json()
        
        if result.get("code") == 100:
            session_id = result["data"]["session_id"]
            print(f"✅ SUCCESS! Avatar works!")
            print(f"   Session ID: {session_id}")
            
            # Clean up - close the session
            try:
                await client.post(
                    "https://api.heygen.com/v1/streaming.stop",
                    json={"session_id": session_id},
                    timeout=5.0
                )
                print(f"   Session closed")
            except:
                pass
            
            return {
                "success": True,
                "avatar_id": avatar_id,
                "voice_id": voice_id,
                "name": avatar_name
            }
        else:
            error_code = result.get("code")
            error_msg = result.get("message", "Unknown error")
            print(f"❌ FAILED: {error_msg} (code: {error_code})")
            
            if error_code == 10003:
                print(f"   Reason: Avatar not available on your plan")
            elif error_code == 10008:
                print(f"   Reason: Quota exceeded or insufficient credits")
            elif error_code == 40002:
                print(f"   Reason: Invalid voice ID")
            
            return None
            
    except httpx.TimeoutException:
        print(f"⏱️ TIMEOUT: Request took too long")
        return None
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return None

async def main():
    """Main test function"""
    print("="*60)
    print("HEYGEN AVATAR COMPATIBILITY TEST")
    print("="*60)
    print(f"API Key: {HEYGEN_API_KEY[:20]}...")
    print("="*60)
    
    if not HEYGEN_API_KEY:
        print("❌ ERROR: No HEYGEN_API_KEY found in .env file")
        return
    
    # Create HTTP client
    client = httpx.AsyncClient(
        headers={
            "X-Api-Key": HEYGEN_API_KEY,
            "Content-Type": "application/json"
        },
        timeout=httpx.Timeout(15.0)
    )
    
    working_avatars = []
    
    try:
        # Test each avatar
        for avatar in TEST_AVATARS:
            result = await test_avatar(
                client,
                avatar["id"],
                avatar["voice"],
                avatar["name"]
            )
            
            if result:
                working_avatars.append(result)
            
            # Small delay between tests
            await asyncio.sleep(1)
        
        # Print summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Total avatars tested: {len(TEST_AVATARS)}")
        print(f"Working avatars: {len(working_avatars)}")
        print("="*60)
        
        if working_avatars:
            print("\n✅ AVATARS THAT WORK WITH YOUR API KEY:")
            print("="*60)
            for avatar in working_avatars:
                print(f"\nName: {avatar['name']}")
                print(f"Avatar ID: {avatar['avatar_id']}")
                print(f"Voice ID: {avatar['voice_id']}")
                print("-"*60)
            
            # Generate code snippet
            print("\n" + "="*60)
            print("CODE TO USE IN YOUR APP:")
            print("="*60)
            print("\nconst workingAvatars = [")
            for avatar in working_avatars:
                print(f"  {{ id: '{avatar['avatar_id']}', name: '{avatar['name']}', voice_id: '{avatar['voice_id']}' }},")
            print("];")
        else:
            print("\n❌ NO WORKING AVATARS FOUND")
            print("\nPossible reasons:")
            print("1. Your HeyGen plan doesn't include streaming avatars")
            print("2. You've exceeded your quota")
            print("3. Your API key doesn't have streaming permissions")
            print("\nCheck your HeyGen dashboard at: https://app.heygen.com")
        
    finally:
        await client.aclose()

if __name__ == "__main__":
    asyncio.run(main())