#!/usr/bin/env python3
"""
Simple test script to verify which HeyGen avatars are available
Run this to test each avatar before using them in production
"""

import requests
import time
import json

# Configuration
BACKEND_URL = "http://localhost:8000"

# Avatar configurations to test
AVATARS_TO_TEST = [
    # Male avatars
    ("josh_lite3_20230714", "da04d9a268ac468887a68359908e55b7", "Josh"),
    ("Anthony_Chair_Sitting_public", "0009aabefe3a4553bc581d837b6268cb", "Anthony"),
    ("Pedro_Chair_Sitting_public", "e17b99e1b86e47e8b7f4cae0f806aa78", "Pedro"),
    # Female avatars
    ("Alessandra_Chair_Sitting_public", "1edc5e7338eb4e37b26dc8eb3f9b7e9c", "Alessandra"),
    ("Amina_Chair_Sitting_public", "1edc5e7338eb4e37b26dc8eb3f9b7e9c", "Amina"),
    ("Anastasia_Chair_Sitting_public", "1edc5e7338eb4e37b26dc8eb3f9b7e9c", "Anastasia"),
    ("Marianne_Chair_Sitting_public", "1edc5e7338eb4e37b26dc8eb3f9b7e9c", "Marianne"),
    ("Rika_Chair_Sitting_public", "1edc5e7338eb4e37b26dc8eb3f9b7e9c", "Rika"),
]

def test_avatar(avatar_id, voice_id, name):
    """Test if an avatar can be created successfully"""
    print(f"\n🧪 Testing {name}...")
    try:
        # Test session creation
        response = requests.post(
            f"{BACKEND_URL}/create-heygen-session",
            json={"avatar_id": avatar_id, "voice_id": voice_id},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                print(f"✅ {name} - SUCCESS")
                session_id = data.get("session_id")
                
                # Try to close the session
                try:
                    time.sleep(1)
                    close_response = requests.post(
                        f"{BACKEND_URL}/close-heygen-session",
                        json={"session_id": session_id},
                        timeout=10
                    )
                    if close_response.status_code == 200:
                        print(f"   ✅ Session closed successfully")
                    else:
                        print(f"   ⚠️ Session close failed: {close_response.status_code}")
                except Exception as e:
                    print(f"   ⚠️ Session close error: {str(e)}")
                
                return True
            else:
                print(f"❌ {name} - FAILED: {data.get('message', 'Unknown error')}")
                return False
        else:
            print(f"❌ {name} - HTTP {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('message', 'Unknown error')}")
            except:
                print(f"   Error: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"❌ {name} - TIMEOUT")
        return False
    except Exception as e:
        print(f"❌ {name} - ERROR: {str(e)}")
        return False

def main():
    print("🚀 Starting HeyGen Avatar Availability Test")
    print("=" * 60)
    print("⚠️  Make sure your backend is running on http://localhost:8000")
    print("⚠️  Make sure you have valid HeyGen API credentials")
    print("=" * 60)
    
    # Test backend connectivity first
    try:
        response = requests.get(f"{BACKEND_URL}/", timeout=5)
        print("✅ Backend is accessible")
    except Exception as e:
        print(f"❌ Backend not accessible: {str(e)}")
        print("Please start your backend server first!")
        return
    
    results = []
    
    for avatar_id, voice_id, name in AVATARS_TO_TEST:
        success = test_avatar(avatar_id, voice_id, name)
        results.append((name, success))
        time.sleep(2)  # Wait between tests to avoid rate limiting
    
    # Print final results
    print("\n" + "=" * 60)
    print("📊 FINAL RESULTS")
    print("=" * 60)
    
    working = [name for name, success in results if success]
    failed = [name for name, success in results if not success]
    
    print(f"\n✅ Working Avatars ({len(working)}):")
    for name in working:
        print(f"   - {name}")
    
    if failed:
        print(f"\n❌ Failed Avatars ({len(failed)}):")
        for name in failed:
            print(f"   - {name}")
    
    success_rate = len(working) / len(results) * 100
    print(f"\n📈 Success Rate: {len(working)}/{len(results)} ({success_rate:.1f}%)")
    
    if working:
        print(f"\n🎯 Recommended: Use these working avatars in your frontend")
        print("   Remove failed avatars from your configuration to avoid errors")
    
    print(f"\n💡 Tips:")
    print("   - Some avatars may not be available in the free tier")
    print("   - Check your HeyGen dashboard for available avatars")
    print("   - Consider upgrading to paid tier for more avatar access")

if __name__ == "__main__":
    main()

