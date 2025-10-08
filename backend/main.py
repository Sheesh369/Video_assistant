import asyncio
import sys
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import tempfile
import os
from typing import Optional
import time
import uuid
import threading
import base64

from ai_service import generate_ai_response_fallback
from models import PromptRequest, CreateSessionRequest
from heygen_api import create_heygen_session, update_session_connection_status, generate_heygen_token, send_text_to_heygen, get_heygen_client

# Import knowledge base functions
from knowledge_base import (
    add_file_to_kb,
    add_text_to_kb,
    search_kb,
    get_kb_context_fast,
    get_kb_stats,
    delete_kb_file,
    clear_kb,
    warmup_kb
)

# Import chat history functions
from chat_history import (
    add_user_message,
    add_avatar_message,
    get_chat_history,
    search_chat_history,
    get_chat_stats,
    export_chat_history,
    clear_chat_history,
    delete_message,
    get_conversation_context
)

# Import voice prompt functions
from voice_prompt import (
    handle_audio_transcription,
    handle_realtime_transcription_start,
    handle_realtime_transcription_chunk,
    handle_realtime_transcription_stop,
    get_voice_service_stats,
    validate_audio_format,
    start_voice_service
)

# Set Windows event loop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Load environment variables
load_dotenv()

# FastAPI app init
app = FastAPI()

# Startup event handler
@app.on_event("startup")
async def startup_event():
    """Handle startup optimizations"""
    try:
        await startup_optimizations()
    except Exception as e:
        print(f"⚠️ Startup optimizations failed (non-critical): {e}")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple thread lock for session operations
session_lock = threading.Lock()

# SDK session tracking (frontend-created sessions)
sdk_sessions = {}

# Startup optimizations function
async def startup_optimizations():
    """Run all startup optimizations"""
    try:
        # Initialize voice service
        start_voice_service()
        print(" Voice service initialized")
        
        # Warm up knowledge base
        await warmup_kb()
        print(" Knowledge base warmed up")
        
        # Start background message saver
        asyncio.create_task(save_pending_messages_background())
        print(" Background message saver started")
        
        print(" All optimization services ready!")
        
    except Exception as e:
        print(f"⚠️ Some optimizations failed (non-critical): {e}")

# ENHANCED: Instant interrupt tracking
class InstantResponseTracker:
    def __init__(self):
        self.current_task = None
        self.is_responding = False
        self.response_id = None
        self.start_time = None
        self.pending_messages = {}
        self.interrupt_flag = threading.Event()
        
    def start_response(self, response_id: str = None):
        """Start tracking with instant interrupt capability"""
        self.interrupt_flag.set()
        
        if self.current_task and not self.current_task.done():
            print(f" INSTANT cancel: {self.response_id}")
            self.current_task.cancel()
        
        self.interrupt_flag.clear()
        self.response_id = response_id or str(time.time())
        self.is_responding = True
        self.start_time = time.time()
        
        print(f" Started INSTANT response tracking: {self.response_id}")
        
    def stop_response_instant(self):
        """INSTANT stop - no delays"""
        self.interrupt_flag.set()
        
        if self.current_task and not self.current_task.done():
            print(f" INSTANT task cancel: {self.response_id}")
            self.current_task.cancel()
        
        old_response_id = self.response_id
        self.current_task = None
        self.is_responding = False
        self.response_id = None
        self.start_time = None
        
        print(f"🛑 INSTANT stopped: {old_response_id}")
        return old_response_id
    
    def is_interrupted(self):
        """Check if current response should be interrupted"""
        return self.interrupt_flag.is_set()
    
    def save_pending_message(self, response_id: str, user_msg, full_response: str, metadata: dict, was_interrupted: bool = False):
        """Store message info for later saving"""
        self.pending_messages[response_id] = {
            'user_msg': user_msg,
            'full_response': full_response,
            'metadata': metadata,
            'was_interrupted': was_interrupted,
            'timestamp': time.time()
        }
    
    async def save_all_pending_messages(self):
        """Save all pending messages to chat history"""
        for response_id, msg_data in list(self.pending_messages.items()):
            try:
                msg_data['metadata']['was_interrupted'] = msg_data['was_interrupted']
                await add_avatar_message(msg_data['full_response'], msg_data['metadata'])
                print(f" Saved {'interrupted' if msg_data['was_interrupted'] else 'completed'} message: {response_id}")
                del self.pending_messages[response_id]
            except Exception as e:
                print(f"❌ Failed to save message {response_id}: {e}")

# Global response tracker
response_tracker = InstantResponseTracker()

# Background task to save pending messages
async def save_pending_messages_background():
    """Background task to save pending messages"""
    while True:
        try:
            await response_tracker.save_all_pending_messages()
            await asyncio.sleep(1)
        except Exception as e:
            print(f"❌ Background message saver error: {e}")
            await asyncio.sleep(5)

# OPTIMIZATION: Cache context
context_cache = {
    "kb_context": "",
    "conversation_context": "",
    "last_updated": 0,
    "cache_duration": 30
}

async def get_cached_context_fast(prompt: str, force_refresh: bool = False) -> tuple[str, str]:
    """ULTRA-FAST: Get context with aggressive caching"""
    global context_cache
    current_time = time.time()
    
    prompt_key = prompt.lower()[:50]
    cache_key = f"kb_context_{hash(prompt_key)}"
    
    if (not force_refresh and
        cache_key in context_cache and
        current_time - context_cache.get(f"{cache_key}_time", 0) < context_cache["cache_duration"]):
        print(f" Using cached context for similar prompt")
        return context_cache[cache_key], context_cache.get("conversation_context", "")
    
    print(f" Fast context refresh for: {prompt[:30]}...")
    
    async def get_kb_task():
        return await get_kb_context_fast(prompt, max_context_length=2000)
    
    async def get_conv_task():
        return get_conversation_context(last_n_messages=3)
    
    kb_context, conversation_context = await asyncio.gather(get_kb_task(), get_conv_task())
    
    context_cache.update({
        cache_key: kb_context,
        f"{cache_key}_time": current_time,
        "conversation_context": conversation_context,
        "last_updated": current_time
    })
    
    print(f" KB context retrieved: {'Yes' if kb_context.strip() else 'No'} ({len(kb_context)} chars)")
    return kb_context, conversation_context

# === MAIN ENDPOINT - AI RESPONSE ONLY ===

@app.post("/send-prompt")
async def send_prompt_with_instant_interrupt(request: PromptRequest):
    """Handle LLM response only - frontend handles HeyGen SDK"""
    prompt = request.prompt
    print(f" Received prompt: {prompt[:50]}...")
    
    # Stop any current response
    if response_tracker.is_responding:
        print(f" INSTANT interrupt before new prompt")
        response_tracker.stop_response_instant()
    
    response_id = str(time.time())
    response_tracker.start_response(response_id)
    
    try:
        # Get context
        kb_context, conversation_context = await get_cached_context_fast(prompt)
        
        # Build enhanced prompt
        if kb_context.strip():
            enhanced_prompt = f"""You are the AI-powered virtual assistant project created by Sash AI. Use the following project information:

PROJECT INFORMATION:
{kb_context}

USER QUESTION: {prompt}

INSTRUCTIONS:
- Answer as the project itself using "I" and "my"
- Base response on PROJECT INFORMATION
- Be conversational and direct
- Keep responses under 150 words"""
        else:
            enhanced_prompt = f"""You are the AI-powered virtual assistant project created by Sash AI.

USER QUESTION: {prompt}

Keep response conversational and under 150 words."""
        
        # Get AI response (frontend handles HeyGen)
        full_ai_response = await generate_ai_response_fallback(enhanced_prompt)
        
        # Check for interrupt
        if response_tracker.is_interrupted():
            raise asyncio.CancelledError()
        
        # Log user message
        user_message = await add_user_message(prompt, {
            "source": "text_input",
            "response_id": response_id
        })
        
        # Log avatar message
        avatar_message = await add_avatar_message(full_ai_response, {
            "heygen_sent": False,
            "used_knowledge_base": bool(kb_context.strip()),
            "context_length": len(kb_context) if kb_context else 0,
            "response_id": response_id,
            "sdk_mode": True
        })
        
        response_tracker.is_responding = False
        
        return {
            "status": "success",
            "response": full_ai_response,
            "heygen_sent": False,
            "used_knowledge_base": bool(kb_context.strip()),
            "context_length": len(kb_context) if kb_context else 0,
            "mode": "sdk_frontend",
            "user_message_id": user_message.id
        }
        
    except asyncio.CancelledError:
        return {
            "status": "interrupted",
            "message": "Response was interrupted",
            "interrupted": True
        }
    except Exception as e:
        print(f"❌ Error in send_prompt: {e}")
        return {"status": "error", "message": str(e)}

# === SDK SESSION MANAGEMENT ===

@app.post("/heygen/register-sdk-session")
async def register_sdk_session(request: dict):
    """Register a session created by the frontend SDK"""
    try:
        session_id = request.get("session_id")
        if not session_id:
            return {"status": "error", "message": "session_id is required"}
        
        print(f" Registering SDK session: {session_id}")
        
        sdk_sessions[session_id] = {
            "session_id": session_id,
            "status": "active",
            "created_at": time.time(),
            "sdk_created": True
        }
        
        print(f" SDK session registered: {session_id}")
        
        return {
            "status": "success",
            "message": "Session registered successfully",
            "session_id": session_id
        }
        
    except Exception as e:
        print(f"❌ Error registering SDK session: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/heygen/unregister-sdk-session")
async def unregister_sdk_session(request: dict):
    """Unregister a session when closed by the frontend SDK"""
    try:
        session_id = request.get("session_id")
        if not session_id:
            return {"status": "error", "message": "session_id is required"}
        
        print(f"📡 Unregistering SDK session: {session_id}")
        
        if session_id in sdk_sessions:
            del sdk_sessions[session_id]
            print(f"✅ SDK session unregistered: {session_id}")
        else:
            print(f"⚠️ Session {session_id} not found")
        
        return {
            "status": "success",
            "message": "Session unregistered successfully",
            "session_id": session_id
        }
        
    except Exception as e:
        print(f"❌ Error unregistering SDK session: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/heygen/session-health/{session_id}")
async def check_session_health(session_id: str):
    """Check if a HeyGen session is still alive"""
    try:
        if session_id not in sdk_sessions:
            return {
                "status": "not_found",
                "alive": False,
                "message": "Session not found"
            }
        
        session_info = sdk_sessions[session_id]
        age = time.time() - session_info.get("created_at", 0)
        
        return {
            "status": "success",
            "alive": True,
            "session_id": session_id,
            "age_seconds": round(age),
            "age_minutes": round(age / 60, 1),
            "sdk_created": True
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/active-sessions")
async def get_active_sessions():
    """Get list of active SDK sessions"""
    with session_lock:
        sessions_data = [
            {
                "session_id": sid,
                "status": info.get("status", "unknown"),
                "age_seconds": round(time.time() - info.get("created_at", time.time())),
                "sdk_created": True
            }
            for sid, info in sdk_sessions.items()
        ]
        
    return {
        "active_sessions": len(sessions_data),
        "sessions": sessions_data
    }

@app.get("/heygen-token")
async def get_heygen_token():
    """Generate a HeyGen streaming token for client-side SDK"""
    try:
        token_data = await generate_heygen_token()
        
        return {
            "status": "success",
            "token": token_data["token"],
            "expires": token_data.get("expires")
        }
        
    except Exception as e:
        print(f"❌ Error generating HeyGen token: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/send-text-to-heygen")
async def send_text_to_heygen_endpoint(request: dict):
    """Send text to HeyGen avatar via backend API"""
    try:
        session_id = request.get("session_id")
        text = request.get("text")
        
        if not session_id or not text:
            return {"status": "error", "message": "session_id and text are required"}
        
        print(f" Sending text to HeyGen session {session_id}: {text[:50]}...")
        
        # Check if this is an SDK session first
        if session_id in sdk_sessions:
            print(f" Found session in SDK sessions, using direct API call")
            # For SDK sessions, we need to use the HeyGen API directly
            client = await get_heygen_client()
            try:
                response = await client.post(
                    "https://api.heygen.com/v1/streaming.task",
                    json={
                        "session_id": session_id,
                        "text": text,
                        "task_type": "repeat"
                    }
                )
                
                result = response.json()
                
                if result.get("code") == 100:
                    print(f"✅ Text sent successfully via direct API")
                    success = True
                else:
                    print(f"❌ Direct API failed: {result.get('message')}")
                    success = False
                    
            except Exception as e:
                print(f"❌ Direct API error: {e}")
                success = False
        else:
            # Use the regular send_text_to_heygen function
            success = await send_text_to_heygen(session_id, text)
        
        if success:
            return {
                "status": "success",
                "message": "Text sent to HeyGen successfully",
                "session_id": session_id
            }
        else:
            return {
                "status": "error",
                "message": "Failed to send text to HeyGen",
                "session_id": session_id
            }
        
    except Exception as e:
        print(f"❌ Error sending text to HeyGen: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/heygen/update-connection-status")
async def update_connection_status(request: dict):
    """
    Frontend reports LiveKit connection status (v2 feature)
    This allows backend to track when frontend SDK successfully connects
    """
    try:
        session_id = request.get("session_id")
        connected = request.get("connected", False)
        
        if not session_id:
            return {"status": "error", "message": "session_id is required"}
        
        print(f"🔗 Updating connection status for session {session_id}: {'Connected' if connected else 'Disconnected'}")
        
        success = await update_session_connection_status(session_id, connected)
        
        if success:
            return {
                "status": "success",
                "session_id": session_id,
                "connected": connected,
                "message": f"Connection status updated to {'connected' if connected else 'disconnected'}"
            }
        else:
            return {
                "status": "error",
                "message": f"Session {session_id} not found",
                "session_id": session_id
            }
        
    except Exception as e:
        print(f"❌ Error updating connection status: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/create-heygen-session")
async def create_session_endpoint_v2(request: CreateSessionRequest):
    """
    Create a new HeyGen streaming session with LiveKit v2 support
    
    This endpoint now explicitly requests v2 (LiveKit) sessions
    """
    try:
        # Pass quality parameter (optional, defaults to "medium" in heygen_api.py)
        quality = getattr(request, 'quality', "medium")
        
        session_info = await create_heygen_session(
            request.avatar_id, 
            request.voice_id,
            quality=quality
        )
        
        return {
            "status": "success",
            "session_id": session_info["session_id"],
            # v2 LiveKit connection information
            "url": session_info.get("url", ""),  # LiveKit server URL
            "access_token": session_info.get("access_token", ""),  # Client token
            "livekit_agent_token": session_info.get("livekit_agent_token", ""),  # Agent token
            "realtime_endpoint": session_info.get("realtime_endpoint", ""),  # Realtime API
            # Session metadata
            "version": session_info.get("version", "v2"),
            "avatar_id": session_info.get("avatar_id"),
            "voice_id": session_info.get("voice_id"),
            "quality": session_info.get("quality", quality),
            # Legacy fields (for backward compatibility, but not used in v2)
            "sdp": session_info.get("sdp", {}),
            "ice_servers": session_info.get("ice_servers", [])
        }
        
    except Exception as e:
        print(f"❌ Error in create_session_endpoint_v2: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/avatars/free")
async def get_free_avatars():
    """Get list of available free avatars"""
    try:
        # Try to fetch from HeyGen API first
        from heygen_api import get_available_avatars
        
        result = await get_available_avatars()
        
        if result.get("success") and result.get("avatars"):
            # Transform to our format
            formatted_avatars = []
            for avatar in result["avatars"]:
                formatted_avatars.append({
                    "id": avatar.get("avatar_id"),
                    "name": avatar.get("avatar_name", avatar.get("avatar_id", "Unknown")),
                    "voice_id": avatar.get("preview_voice_id", "1edc5e7338eb4e37b26dc8eb3f9b7e9c"),
                    "gender": avatar.get("gender", "unknown"),
                    "description": f"HeyGen {avatar.get('gender', 'Avatar')} Avatar",
                    "category": avatar.get("gender", "unknown")
                })
            
            print(f"✅ Fetched {len(formatted_avatars)} avatars from HeyGen API")
            return formatted_avatars
        
    except Exception as e:
        print(f"⚠️ Failed to fetch avatars from API: {e}")
    
    # Fallback to hardcoded avatars
    from models import get_all_avatars
    fallback_avatars = get_all_avatars()
    print(f"📋 Using fallback avatars: {len(fallback_avatars)}")
    return fallback_avatars

@app.get("/api/avatars/available")
async def get_available_avatars_endpoint():
    """Get raw list of all available avatars from HeyGen"""
    try:
        from heygen_api import get_available_avatars
        
        result = await get_available_avatars()
        
        if result.get("success"):
            return {
                "success": True,
                "avatars": result.get("avatars", []),
                "count": len(result.get("avatars", []))
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Failed to fetch avatars"),
                "avatars": []
            }
        
    except Exception as e:
        print(f"❌ Error fetching available avatars: {e}")
        return {
            "success": False,
            "error": str(e),
            "avatars": []
        }

# === INTERRUPT ENDPOINTS ===

@app.post("/interrupt-response")
async def interrupt_current_response():
    """INSTANT response interruption"""
    try:
        stopped_response_id = response_tracker.stop_response_instant()
        await response_tracker.save_all_pending_messages()
        
        return {
            "status": "success",
            "message": "Response interrupted instantly",
            "interrupted_response_id": stopped_response_id,
            "instant": True
        }
        
    except Exception as e:
        print(f"❌ Error in instant interrupt: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/response-status")
async def get_response_status():
    """Get current response status"""
    try:
        is_responding = response_tracker.is_responding
        current_id = response_tracker.response_id
        duration = None
        
        if is_responding and response_tracker.start_time:
            duration = time.time() - response_tracker.start_time
        
        return {
            "status": "success",
            "is_responding": is_responding,
            "response_id": current_id,
            "duration_seconds": duration,
            "can_interrupt": is_responding,
            "pending_messages": len(response_tracker.pending_messages)
        }
    except Exception as e:
        print(f"❌ Error getting response status: {e}")
        return {"status": "error", "message": str(e)}

# === VOICE ENDPOINTS ===

@app.post("/voice/transcribe")
async def transcribe_audio_endpoint(request: dict):
    """One-shot audio transcription"""
    try:
        audio_data_b64 = request.get("audio_data", "")
        audio_format = request.get("format", "webm")
        
        if not audio_data_b64:
            return {"status": "error", "message": "No audio data provided"}
        
        try:
            audio_bytes = base64.b64decode(audio_data_b64)
        except Exception as e:
            return {"status": "error", "message": f"Invalid base64 audio data: {e}"}
        
        validation = validate_audio_format(audio_bytes)
        if not validation["valid"]:
            return {"status": "error", "message": f"Invalid audio: {validation['error']}"}
        
        print(f" Transcribing audio: {len(audio_bytes)} bytes")
        
        result = await handle_audio_transcription(audio_bytes, audio_format=audio_format)
        
        if result["success"]:
            return {
                "status": "success",
                "text": result.get("text", ""),
                "audio_length": result.get("audio_length", 0)
            }
        else:
            return {
                "status": "error",
                "message": result.get("error", "Transcription failed")
            }
            
    except Exception as e:
        print(f"❌ Error in transcribe_audio_endpoint: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/voice/start-recording")
async def start_voice_recording():
    """Start a real-time voice recording session"""
    try:
        session_id = str(uuid.uuid4())
        result = await handle_realtime_transcription_start(session_id)
        
        if result["success"]:
            return {
                "status": "success",
                "session_id": session_id,
                "recording_status": result.get("status", "recording")
            }
        else:
            return {
                "status": "error",
                "message": result.get("error", "Failed to start recording")
            }
            
    except Exception as e:
        print(f"❌ Error in start_voice_recording: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/voice/add-chunk")
async def add_voice_chunk(request: dict):
    """Add audio chunk to recording session"""
    try:
        session_id = request.get("session_id", "")
        audio_data_b64 = request.get("audio_data", "")
        
        if not session_id or not audio_data_b64:
            return {"status": "error", "message": "Missing session_id or audio_data"}
        
        try:
            audio_bytes = base64.b64decode(audio_data_b64)
        except Exception as e:
            return {"status": "error", "message": f"Invalid base64 audio data: {e}"}
        
        result = await handle_realtime_transcription_chunk(session_id, audio_bytes)
        
        if result["success"]:
            return {
                "status": "success",
                "chunks_count": result.get("chunks_count", 0),
                "session_id": session_id
            }
        else:
            return {
                "status": "error",
                "message": result.get("error", "Failed to add chunk")
            }
            
    except Exception as e:
        print(f"❌ Error in add_voice_chunk: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/voice/stop-recording")
async def stop_voice_recording_with_interrupt(request: dict):
    """Stop recording and process with instant interrupt capability"""
    session_id = request.get("session_id", "")
    
    if not session_id:
        return {"status": "error", "message": "Missing session_id"}
    
    try:
        print(f"🎤 Stopping voice recording: {session_id}")
        
        if response_tracker.is_responding:
            print(f"⚡ INSTANT interrupt before voice processing")
            response_tracker.stop_response_instant()
        
        result = await handle_realtime_transcription_stop(session_id)
        
        if not result["success"]:
            return {
                "status": "error",
                "message": result.get("error", "Failed to stop recording")
            }
        
        transcribed_text = result.get("text", "").strip()
        
        if not transcribed_text:
            return {
                "status": "success",
                "text": "",
                "message": "No speech detected",
                "chunks_processed": result.get("chunks_processed", 0)
            }
        
        print(f"🎤 Voice transcription: '{transcribed_text}'")
        
        voice_request = PromptRequest(prompt=transcribed_text)
        response = await send_prompt_with_instant_interrupt(voice_request)
        
        response.update({
            "text": transcribed_text,
            "chunks_processed": result.get("chunks_processed", 0),
            "recording_duration": result.get("recording_duration", 0),
            "voice_input": True
        })
        
        return response
        
    except Exception as e:
        print(f"❌ Error in voice processing: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/voice/stats")
async def get_voice_stats():
    """Get voice service statistics"""
    try:
        stats = get_voice_service_stats()
        return {
            "status": "success",
            "voice_stats": stats
        }
    except Exception as e:
        print(f"❌ Error getting voice stats: {e}")
        return {"status": "error", "message": str(e)}

# === KNOWLEDGE BASE ENDPOINTS ===

@app.post("/kb/upload-file")
async def upload_file_to_kb(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None)
):
    """Upload a file to the knowledge base"""
    try:
        print(f" Uploading file to KB: {file.filename}")
        
        file_metadata = {}
        if metadata:
            import json
            try:
                file_metadata = json.loads(metadata)
            except:
                file_metadata = {"description": metadata}
        
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, file.filename)
        
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        try:
            result = await add_file_to_kb(temp_path, file_metadata)
            
            global context_cache
            context_cache["last_updated"] = 0
            
            return JSONResponse(content=result)
        finally:
            try:
                os.remove(temp_path)
            except:
                pass
                
    except Exception as e:
        print(f"❌ Error uploading file to KB: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.post("/kb/add-text")
async def add_text_to_kb_endpoint(request: dict):
    """Add raw text to the knowledge base"""
    try:
        text = request.get("text", "")
        metadata = request.get("metadata", {})
        
        if not text.strip():
            return {"success": False, "error": "No text provided"}
        
        result = await add_text_to_kb(text, metadata)
        
        global context_cache
        context_cache["last_updated"] = 0
        
        return result
        
    except Exception as e:
        print(f"❌ Error adding text to KB: {e}")
        return {"success": False, "error": str(e)}

@app.get("/kb/search")
async def search_kb_endpoint(query: str, limit: int = 5):
    """Search the knowledge base"""
    try:
        if not query.strip():
            return {"success": False, "error": "No search query provided"}
        
        results = await search_kb(query, n_results=limit)
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        print(f"❌ Error searching KB: {e}")
        return {"success": False, "error": str(e)}

@app.get("/kb/stats")
async def get_kb_stats_endpoint():
    """Get knowledge base statistics"""
    try:
        stats = get_kb_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        print(f"❌ Error getting KB stats: {e}")
        return {"success": False, "error": str(e)}

@app.delete("/kb/file/{filename}")
async def delete_file_from_kb(filename: str):
    """Delete a file from the knowledge base"""
    try:
        result = delete_kb_file(filename)
        
        global context_cache
        context_cache["last_updated"] = 0
        
        return result
    except Exception as e:
        print(f"❌ Error deleting file from KB: {e}")
        return {"success": False, "error": str(e)}

@app.delete("/kb/clear")
async def clear_kb_endpoint():
    """Clear all data from the knowledge base"""
    try:
        result = clear_kb()
        
        global context_cache
        context_cache = {
            "kb_context": "",
            "conversation_context": "",
            "last_updated": 0,
            "cache_duration": 30
        }
        
        return result
    except Exception as e:
        print(f"❌ Error clearing KB: {e}")
        return {"success": False, "error": str(e)}

@app.get("/kb/files")
async def list_kb_files():
    """List all files in the knowledge base"""
    try:
        from knowledge_base import get_knowledge_base
        kb = get_knowledge_base()
        
        all_docs = kb.collection.get(limit=1000)
        
        files_info = {}
        if all_docs and 'metadatas' in all_docs:
            for metadata in all_docs['metadatas']:
                filename = metadata.get('filename', 'Unknown')
                if filename != 'Unknown':
                    if filename not in files_info:
                        files_info[filename] = {
                            'filename': filename,
                            'file_extension': metadata.get('file_extension', ''),
                            'file_size': metadata.get('file_size', 0),
                            'upload_timestamp': metadata.get('upload_timestamp', ''),
                            'chunks_count': 0,
                            'total_characters': metadata.get('text_length', 0)
                        }
                    files_info[filename]['chunks_count'] += 1
        
        return {
            "success": True,
            "files": list(files_info.values()),
            "total_files": len(files_info)
        }
        
    except Exception as e:
        print(f"❌ Error listing KB files: {e}")
        return {"success": False, "error": str(e)}

# === CHAT HISTORY ENDPOINTS ===

@app.get("/chat/history")
async def get_chat_history_endpoint(
    limit: Optional[int] = None,
    message_type: Optional[str] = None,
    session_id: Optional[str] = None
):
    """Get chat history with optional filters"""
    try:
        messages = get_chat_history(limit=limit, message_type=message_type, session_id=session_id)
        stats = get_chat_stats()
        
        return {
            "success": True,
            "messages": messages,
            "stats": stats,
            "filters_applied": {
                "limit": limit,
                "message_type": message_type,
                "session_id": session_id
            }
        }
        
    except Exception as e:
        print(f"❌ Error getting chat history: {e}")
        return {"success": False, "error": str(e)}

@app.get("/chat/search")
async def search_chat_endpoint(query: str, limit: int = 10):
    """Search through chat history"""
    try:
        if not query.strip():
            return {"success": False, "error": "No search query provided"}
        
        results = search_chat_history(query, limit)
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        print(f"❌ Error searching chat history: {e}")
        return {"success": False, "error": str(e)}

@app.get("/chat/stats")
async def get_chat_stats_endpoint():
    """Get chat history statistics"""
    try:
        stats = get_chat_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        print(f"❌ Error getting chat stats: {e}")
        return {"success": False, "error": str(e)}

@app.get("/chat/export")
async def export_chat_endpoint(format: str = "json"):
    """Export chat history"""
    try:
        result = export_chat_history(format)
        return result
    except Exception as e:
        print(f"❌ Error exporting chat: {e}")
        return {"success": False, "error": str(e)}

@app.delete("/chat/clear")
async def clear_chat_endpoint():
    """Clear all chat history"""
    try:
        result = clear_chat_history()
        
        global context_cache
        context_cache["conversation_context"] = ""
        context_cache["last_updated"] = 0
        
        return result
    except Exception as e:
        print(f"❌ Error clearing chat: {e}")
        return {"success": False, "error": str(e)}

@app.delete("/chat/message/{message_id}")
async def delete_chat_message_endpoint(message_id: str):
    """Delete a specific message from chat history"""
    try:
        result = delete_message(message_id)
        
        global context_cache
        context_cache["conversation_context"] = ""
        context_cache["last_updated"] = 0
        
        return result
    except Exception as e:
        print(f"❌ Error deleting message: {e}")
        return {"success": False, "error": str(e)}

# === HEALTH & PERFORMANCE ENDPOINTS ===

@app.get("/health")
async def health_check():
    """Enhanced health check endpoint"""
    try:
        kb_stats = get_kb_stats()
        chat_stats = get_chat_stats()
        voice_stats = get_voice_service_stats()
        
        with session_lock:
            active_session_count = len(sdk_sessions)
        
        return {
            "status": "healthy",
            "knowledge_base": {
                "available": True,
                "stats": kb_stats
            },
            "chat_history": {
                "available": True,
                "stats": chat_stats
            },
            "voice_service": {
                "available": True,
                "stats": voice_stats
            },
            "active_sessions": active_session_count,
            "interruption_support": {
                "enabled": True,
                "instant_mode": True,
                "current_response_active": response_tracker.is_responding,
                "response_id": response_tracker.response_id
            },
            "sdk_mode": {
                "enabled": True,
                "frontend_handles_heygen": True,
                "backend_provides_ai_only": True
            },
            "optimizations": {
                "context_caching": True,
                "parallel_processing": True,
                "instant_interruption": True,
                "voice_transcription": True
            }
        }
    except Exception as e:
        with session_lock:
            active_session_count = len(sdk_sessions)
        
        return {
            "status": "partial",
            "knowledge_base": {"available": False, "error": str(e)},
            "chat_history": {"available": False, "error": str(e)},
            "voice_service": {"available": False, "error": str(e)},
            "active_sessions": active_session_count,
            "interruption_support": {"enabled": False, "error": str(e)}
        }

@app.get("/performance/stats")
async def get_performance_stats():
    """Get detailed performance statistics"""
    try:
        kb_stats = get_kb_stats()
        chat_stats = get_chat_stats()
        voice_stats = get_voice_service_stats()
        
        with session_lock:
            session_count = len(sdk_sessions)
            session_details = []
            current_time = time.time()
            
            for session_id, session_info in sdk_sessions.items():
                age = current_time - session_info.get("created_at", current_time)
                session_details.append({
                    "session_id": session_id,
                    "age_seconds": round(age),
                    "status": session_info.get("status", "unknown"),
                    "sdk_created": True
                })
        
        global context_cache
        cache_age = time.time() - context_cache["last_updated"]
        
        return {
            "status": "success",
            "performance": {
                "active_sessions": session_count,
                "session_details": session_details,
                "context_cache_age": round(cache_age),
                "context_cache_valid": cache_age < context_cache["cache_duration"],
                "kb_stats": kb_stats,
                "chat_stats": chat_stats,
                "voice_stats": voice_stats,
                "response_tracker": {
                    "is_responding": response_tracker.is_responding,
                    "current_response_id": response_tracker.response_id,
                    "response_duration": time.time() - response_tracker.start_time if response_tracker.start_time else None,
                    "pending_messages": len(response_tracker.pending_messages)
                }
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/performance/clear-cache")
async def clear_performance_cache():
    """Clear all performance caches for fresh responses"""
    try:
        global context_cache
        context_cache = {
            "kb_context": "",
            "conversation_context": "",
            "last_updated": 0,
            "cache_duration": 30
        }
        
        try:
            from knowledge_base import get_knowledge_base
            kb = get_knowledge_base()
            with kb.cache_lock:
                kb.search_cache.clear()
        except:
            pass
        
        return {
            "status": "success",
            "message": "All caches cleared",
            "cache_reset": True
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/test/latency")
async def test_latency(request: dict):
    """Test endpoint to measure latency improvements"""
    test_prompt = request.get("prompt", "Hello, how are you?")
    
    start_time = time.time()
    
    try:
        fake_request = PromptRequest(prompt=test_prompt)
        result = await send_prompt_with_instant_interrupt(fake_request)
        
        total_time = round((time.time() - start_time) * 1000)
        
        return {
            "status": "success",
            "test_results": {
                "total_latency_ms": total_time,
                "mode_used": result.get("mode", "sdk_frontend"),
                "heygen_handled_by": "frontend_sdk",
                "interruption_enabled": True,
                "instant_mode": True
            },
            "test_prompt": test_prompt
        }
        
    except Exception as e:
        total_time = round((time.time() - start_time) * 1000)
        return {
            "status": "error",
            "message": str(e),
            "total_latency_ms": total_time
        }

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚀 HeyGen SDK Mode FastAPI Server Starting...")
    print("=" * 60)
    print("📡 Frontend handles HeyGen via SDK")
    print("🧠 Backend provides AI responses only")
    print("⚡ INSTANT INTERRUPTION MODE ENABLED")
    print("💾 Enhanced message saving")
    print("🎤 Voice prompt support")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        loop="asyncio",
        workers=1,
        access_log=False,
        log_level="warning"
    )