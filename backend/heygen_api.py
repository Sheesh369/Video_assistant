# heygen_api.py - FULLY FIXED V2 WITH PROPER AVATAR SELECTION
import asyncio
import httpx
import os
from dotenv import load_dotenv
import time
import threading

load_dotenv()
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")

# Global session storage
active_sessions = {}

# Persistent HTTP client
_heygen_client = None
_client_lock = threading.Lock()

async def get_heygen_client():
    """Get persistent HTTP client for HeyGen API"""
    global _heygen_client
    
    with _client_lock:
        if _heygen_client is None:
            _heygen_client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=5.0),  # Increased timeout
                limits=httpx.Limits(max_connections=5, max_keepalive_connections=3),
                headers={
                    "X-Api-Key": HEYGEN_API_KEY,
                    "Content-Type": "application/json"
                }
            )
    
    return _heygen_client

async def generate_heygen_token():
    """Generate a HeyGen streaming token for client-side SDK"""
    try:
        print("🔑 Generating HeyGen streaming token...")
        
        client = await get_heygen_client()
        
        response = await client.post(
            "https://api.heygen.com/v1/streaming.create_token"
        )
        
        print(f"Token generation status: {response.status_code}")
        
        if response.status_code == 401:
            raise Exception("Invalid API key - check your HeyGen dashboard")
        elif response.status_code == 403:
            raise Exception("API key valid but no streaming permissions")
        elif response.status_code == 429:
            raise Exception("Rate limited - wait before trying again")
        elif not response.is_success:
            error_text = response.text
            raise Exception(f"Token generation failed: {response.status_code} {error_text}")
        
        result = response.json()
        
        if not result.get("data") or not result["data"].get("token"):
            raise Exception("No token in response")
        
        token_data = result["data"]
        
        print("✅ Token generated successfully")
        
        return {
            "token": token_data["token"],
            "expires": token_data.get("expire_time")
        }
        
    except Exception as e:
        print(f"❌ Token generation failed: {e}")
        raise e

async def get_available_avatars() -> dict:
    """Fetch available avatars from HeyGen account"""
    print("🎭 Fetching available avatars from HeyGen...")
    
    client = await get_heygen_client()
    try:
        response = await client.get("https://api.heygen.com/v1/avatar.list")
        
        response.raise_for_status()
        result = response.json()
        
        if result.get("code") == 100:
            avatars = result.get("data", {}).get("avatars", [])
            print(f"✅ Found {len(avatars)} available avatars")
            
            for avatar in avatars[:10]:
                avatar_id = avatar.get('avatar_id', 'Unknown')
                avatar_name = avatar.get('avatar_name', 'No name')
                print(f"   - {avatar_id} ({avatar_name})")
            
            return {"success": True, "avatars": avatars}
        else:
            print(f"❌ HeyGen avatar list error: {result.get('message')}")
            return {"success": False, "error": result.get('message')}
            
    except Exception as e:
        print(f"❌ Error fetching avatars: {str(e)}")
        return {"success": False, "error": str(e)}

async def create_heygen_session(avatar_id: str, voice_id: str, quality: str = "medium") -> dict:
    """
    Create a new HeyGen streaming session with correct avatar
    FIXED: Properly passes avatar_id and voice_id
    """
    print('=' * 80)
    print(f"🎭 CREATING HEYGEN SESSION")
    print(f"   Avatar ID: {avatar_id}")
    print(f"   Voice ID: {voice_id}")
    print(f"   Quality: {quality}")
    print('=' * 80)
    
    client = await get_heygen_client()
    try:
        # CRITICAL FIX: Use exact field names HeyGen SDK expects
        payload = {
            "quality": quality,
            "avatarName": avatar_id,  # SDK uses avatarName, NOT avatar_name
            "voice": {
                "voiceId": voice_id,  # SDK uses voiceId, NOT voice_id
                "rate": 1.0,
                "emotion": "Friendly"
            },
            "version": "v2",  # Request LiveKit v2
            "video_encoding": "H264"
        }
        
        print("📤 Sending payload to HeyGen:")
        print(f"   {payload}")
        
        response = await client.post(
            "https://api.heygen.com/v1/streaming.new",
            json=payload
        )
        
        print(f"📥 HeyGen response status: {response.status_code}")
        
        response.raise_for_status()
        result = response.json()
        
        print(f"📥 HeyGen response code: {result.get('code')}")
        print(f"📥 HeyGen response message: {result.get('message', 'No message')}")
        
        if result.get("code") == 100:
            session_data = result["data"]
            
            # Extract session info
            session_info = {
                "session_id": session_data["session_id"],
                # LiveKit v2 credentials
                "url": session_data.get("url", ""),
                "access_token": session_data.get("access_token", ""),
                "livekit_agent_token": session_data.get("livekit_agent_token", ""),
                "realtime_endpoint": session_data.get("realtime_endpoint", ""),
                # Session metadata - CRITICAL: Store what we requested
                "avatar_id": avatar_id,  # What we requested
                "voice_id": voice_id,    # What we requested
                "quality": quality,
                "version": "v2",
                "status": "created",
                "ready_for_text": False,
                "livekit_connected": False,
                "created_at": time.time(),
                "sdk_managed": True
            }
            
            # Store session globally
            active_sessions[session_data["session_id"]] = session_info
            
            print('=' * 80)
            print(f"✅ SESSION CREATED SUCCESSFULLY")
            print(f"   Session ID: {session_data['session_id']}")
            print(f"   Avatar: {avatar_id}")
            print(f"   Voice: {voice_id}")
            print(f"   LiveKit URL: {session_info['url'][:50]}..." if session_info['url'] else "   No URL (v1 session)")
            print('=' * 80)
            
            return session_info
        else:
            error_msg = result.get('message', 'Unknown error')
            error_code = result.get('code')
            print(f"❌ HeyGen API error (code {error_code}): {error_msg}")
            
            # Provide helpful error messages
            if error_code == 10003:
                raise Exception(f"Invalid avatar '{avatar_id}'. Please verify this avatar exists in your HeyGen account.")
            elif error_code == 10008:
                raise Exception(f"Insufficient credits or quota exceeded. Check your HeyGen dashboard.")
            elif error_code == 40002:
                raise Exception(f"Invalid voice '{voice_id}'. Please verify this voice ID is correct.")
            else:
                raise Exception(f"HeyGen API error (code {error_code}): {error_msg}")
                
    except httpx.HTTPStatusError as e:
        error_text = e.response.text
        print(f"❌ HTTP error creating HeyGen session: {e.response.status_code}")
        print(f"❌ Response: {error_text}")
        
        try:
            error_json = e.response.json()
            error_code = error_json.get("code")
            error_message = error_json.get("message", "Unknown error")
            
            if error_code == 10003:
                raise Exception(f"Avatar '{avatar_id}' not found in your HeyGen account. Please check available avatars.")
            elif error_code == 10008:
                raise Exception(f"Quota exceeded. Check your HeyGen credits.")
            elif error_code == 40002:
                raise Exception(f"Invalid voice ID '{voice_id}'.")
            else:
                raise Exception(f"HeyGen error {error_code}: {error_message}")
        except:
            raise Exception(f"HTTP {e.response.status_code}: {error_text}")
            
    except Exception as e:
        print(f"❌ Error creating HeyGen session: {str(e)}")
        raise

async def start_heygen_session(session_id: str, sdp_answer: str = None) -> bool:
    """
    Start a HeyGen session (mainly for v1, v2 auto-starts)
    """
    print(f"▶️ Starting session: {session_id}")
    
    if session_id not in active_sessions:
        print(f"❌ Session {session_id} not found")
        return False
    
    session_info = active_sessions[session_id]
    
    # For v2 (LiveKit) sessions, they auto-start
    if session_info.get("version") == "v2" or session_info.get("url"):
        print(f"🔗 LiveKit v2 session - auto-starting")
        
        session_info.update({
            "status": "started",
            "ready_for_text": True,
            "started_at": time.time()
        })
        
        print(f"✅ Session marked as started: {session_id}")
        return True
    
    # For v1 sessions, need to call streaming.start
    print(f"⚠️ V1 session detected, calling streaming.start")
    
    client = await get_heygen_client()
    try:
        payload = {"session_id": session_id}
        if sdp_answer:
            payload["sdp"] = {
                "type": "answer",
                "sdp": sdp_answer
            }
        
        response = await client.post(
            "https://api.heygen.com/v1/streaming.start",
            json=payload
        )
        
        response.raise_for_status()
        result = response.json()
        
        if result.get("code") == 100:
            session_info.update({
                "status": "started",
                "ready_for_text": True,
                "started_at": time.time()
            })
            
            print(f"✅ Session started: {session_id}")
            return True
        else:
            error_msg = result.get('message', 'Unknown error')
            print(f"❌ Failed to start session: {error_msg}")
            return False
            
    except Exception as e:
        print(f"❌ Error starting session: {str(e)}")
        return False

async def send_text_to_heygen(session_id: str, text: str) -> bool:
    """Send text to HeyGen avatar"""
    print(f"💬 Sending text to session {session_id}: {text[:50]}...")
    
    if session_id not in active_sessions:
        print(f"❌ Session {session_id} not found")
        return False
    
    session_info = active_sessions[session_id]
    
    # Clean the text
    cleaned_text = text.strip()
    
    if not cleaned_text or cleaned_text in ["...", "."]:
        print(f"⚠️ Skipping empty/placeholder text")
        return True
    
    if len(cleaned_text) > 500:
        cleaned_text = cleaned_text[:500]
        print(f"⚠️ Text truncated to 500 characters")
    
    client = await get_heygen_client()
    try:
        response = await client.post(
            "https://api.heygen.com/v1/streaming.task",
            json={
                "session_id": session_id,
                "text": cleaned_text,
                "task_type": "repeat"
            }
        )
        
        result = response.json()
        
        if result.get("code") == 100:
            print(f"✅ Text sent successfully")
            return True
        elif result.get("code") == 10002:
            print(f"💔 Session {session_id} is closed/expired")
            if session_id in active_sessions:
                del active_sessions[session_id]
            return False
        else:
            error_msg = result.get('message', 'Unknown error')
            error_code = result.get('code')
            print(f"❌ Task error (code {error_code}): {error_msg}")
            
            if error_code in [10007, 10002]:
                if session_id in active_sessions:
                    del active_sessions[session_id]
            
            return False
            
    except Exception as e:
        print(f"❌ Error sending text: {str(e)}")
        return False

async def close_heygen_session(session_id: str) -> bool:
    """Close a HeyGen session"""
    print(f"🛑 Closing session: {session_id}")
    
    client = await get_heygen_client()
    try:
        response = await client.post(
            "https://api.heygen.com/v1/streaming.stop",
            json={"session_id": session_id}
        )
        
        response.raise_for_status()
        
        if session_id in active_sessions:
            del active_sessions[session_id]
        
        print(f"✅ Session closed: {session_id}")
        return True
        
    except Exception as e:
        print(f"❌ Error closing session: {str(e)}")
        if session_id in active_sessions:
            del active_sessions[session_id]
        return False

async def update_session_connection_status(session_id: str, connected: bool):
    """Update LiveKit connection status"""
    if session_id in active_sessions:
        active_sessions[session_id].update({
            "livekit_connected": connected,
            "ready_for_text": connected,
            "last_connection_update": time.time()
        })
        print(f"🔗 Session {session_id} LiveKit: {'Connected' if connected else 'Disconnected'}")
        return True
    return False

async def validate_heygen_session(session_id: str) -> bool:
    """Validate if session is still alive"""
    if session_id not in active_sessions:
        return False
    
    session_info = active_sessions[session_id]
    
    time_since_start = time.time() - session_info.get("created_at", 0)
    if time_since_start < 120:
        return True
    
    client = await get_heygen_client()
    try:
        response = await client.post(
            "https://api.heygen.com/v1/streaming.task",
            json={
                "session_id": session_id,
                "text": ".",
                "task_type": "repeat"
            },
            timeout=httpx.Timeout(3.0)
        )
        
        result = response.json()
        
        if result.get("code") == 10002:
            print(f"🧹 Removing expired session {session_id}")
            if session_id in active_sessions:
                del active_sessions[session_id]
            return False
        
        return result.get("code") == 100
                
    except Exception:
        if session_id in active_sessions:
            del active_sessions[session_id]
        return False