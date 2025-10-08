
# voice_prompt.py - FIXED VERSION with proper audio handling
import asyncio
import io
import os
import tempfile
import base64
from typing import Optional
import openai
from fastapi import UploadFile
import wave

# Initialize OpenAI client
openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class VoiceTranscriptionService:
    """Service for handling real-time voice transcription with OpenAI Whisper"""
    
    def __init__(self):
        self.active_recordings = {}  # Track active recording sessions
        
    async def transcribe_audio_chunk(self, audio_data: bytes, session_id: str = None, audio_format: str = "webm") -> dict:
        """
        Transcribe audio chunk using OpenAI Whisper API
        
        Args:
            audio_data: Raw audio bytes (WebM/WAV format)
            session_id: Optional session ID for tracking
            audio_format: Audio format hint (webm, wav, etc.)
            
        Returns:
            dict: {"success": bool, "text": str, "error": str}
        """
        try:
            print(f"🎤 Transcribing audio chunk ({len(audio_data)} bytes, format: {audio_format})")
            
            # CRITICAL FIX: Lower the minimum audio size threshold
            # Original was 1000 bytes, which was too restrictive
            if len(audio_data) < 500:  # Reduced from 1000 to 500 bytes
                print("⚠️ Audio chunk too small, skipping transcription")
                return {
                    "success": True,
                    "text": "",
                    "session_id": session_id,
                    "audio_length": len(audio_data),
                    "skip_reason": "Audio too small"
                }
            
            # Create temporary file with appropriate extension
            file_extension = f".{audio_format}" if audio_format in ["wav", "webm", "mp3", "m4a"] else ".wav"
            
            print(f"🎵 Creating temp file with extension: {file_extension}")
            
            with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file.flush()
                temp_path = temp_file.name
                
            # Debug: Check if this looks like a WAV file
            if audio_format == "wav" and len(audio_data) > 44:
                header = audio_data[:44]
                if header.startswith(b'RIFF') and b'WAVE' in header:
                    print("✅ Valid WAV header detected")
                    # Extract some WAV info
                    import struct
                    try:
                        channels = struct.unpack('<H', header[22:24])[0]
                        sample_rate = struct.unpack('<I', header[24:28])[0] 
                        print(f"🎵 WAV info: {channels} channels, {sample_rate}Hz")
                    except:
                        pass
                else:
                    print("⚠️ Invalid WAV header - might be corrupted")
                    print(f"🔍 Header bytes: {header[:12].hex()}")
            
            try:
                # CRITICAL FIX: Enhanced transcription parameters for better results
                print(f"📤 Sending {len(audio_data)} bytes to OpenAI Whisper (format: {file_extension})...")
                
                with open(temp_path, "rb") as audio_file:
                    transcript = await openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="verbose_json",  # CHANGED: Use verbose_json for more info
                        language="en",  
                        temperature=0.0,  # Most deterministic results
                        prompt="This is a continuous speech recording. Please transcribe the complete speech accurately without cutting off words."  # IMPROVED: Better prompt
                    )
                
                # CRITICAL FIX: Handle verbose_json response format
                if hasattr(transcript, 'text'):
                    transcribed_text = transcript.text.strip() if transcript.text else ""
                else:
                    transcribed_text = transcript.strip() if transcript else ""
                
                print(f"✅ Transcription result: '{transcribed_text}' (length: {len(transcribed_text)})")
                
                # IMPROVED: Better detection of incomplete transcriptions
                suspicious_results = ["You", "you", ".", "..", "...", "", " ", "Thank you.", "Thanks."]
                if transcribed_text in suspicious_results or len(transcribed_text) <= 3:
                    print("⚠️ WARNING: Suspicious transcription result - possible incomplete audio")
                    print(f"🔍 Audio data first 50 bytes: {audio_data[:50].hex()}")
                    
                    # Try to identify the actual format
                    if audio_data.startswith(b'RIFF'):
                        print("🎵 Audio appears to be WAV/RIFF format")
                    elif audio_data.startswith(b'\x1a\x45\xdf\xa3'):
                        print("🎵 Audio appears to be WebM format") 
                    else:
                        print("🎵 Unknown audio format")
                
                return {
                    "success": True,
                    "text": transcribed_text,
                    "session_id": session_id,
                    "audio_length": len(audio_data),
                    "detected_format": audio_format
                }
                
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            return {
                "success": False,
                "text": "",
                "error": str(e),
                "session_id": session_id
            }
    
    async def transcribe_audio_stream(self, audio_chunks: list, session_id: str = None, audio_format: str = "webm") -> dict:
        """
        Transcribe multiple audio chunks as a stream
        
        Args:
            audio_chunks: List of audio byte chunks
            session_id: Optional session ID for tracking
            
        Returns:
            dict: {"success": bool, "text": str, "partial_texts": list}
        """
        try:
            print(f"🎤 Transcribing {len(audio_chunks)} audio chunks")
            
            if not audio_chunks:
                return {
                    "success": False,
                    "text": "",
                    "error": "No audio chunks provided"
                }
            
            # Combine all chunks into single audio buffer
            combined_audio = b''.join(audio_chunks)
            print(f"🎤 Combined audio size: {len(combined_audio)} bytes")
            
            # CRITICAL FIX: Reduced minimum audio size for stream transcription
            # This was the main cause of cutoff issues
            if len(combined_audio) < 2000:  # Reduced from 5000 to 2000 bytes
                print("⚠️ Combined audio too small for reliable transcription")
                return {
                    "success": True,
                    "text": "",
                    "session_id": session_id,
                    "chunks_processed": len(audio_chunks),
                    "total_audio_length": len(combined_audio),
                    "skip_reason": "Audio too small"
                }
            
            # Transcribe the combined audio
            result = await self.transcribe_audio_chunk(combined_audio, session_id, audio_format)
            
            return {
                "success": result["success"],
                "text": result.get("text", ""),
                "error": result.get("error"),
                "session_id": session_id,
                "chunks_processed": len(audio_chunks),
                "total_audio_length": len(combined_audio)
            }
            
        except Exception as e:
            print(f"❌ Stream transcription error: {e}")
            return {
                "success": False,
                "text": "",
                "error": str(e),
                "session_id": session_id
            }
    
    def start_recording_session(self, session_id: str) -> dict:
        """Start a new recording session"""
        try:
            self.active_recordings[session_id] = {
                "chunks": [],
                "start_time": asyncio.get_event_loop().time(),
                "status": "recording"
            }
            
            print(f"🎤 Started recording session: {session_id}")
            return {
                "success": True,
                "session_id": session_id,
                "status": "recording"
            }
            
        except Exception as e:
            print(f"❌ Error starting recording session: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def add_audio_chunk(self, session_id: str, audio_chunk: bytes) -> dict:
        """Add audio chunk to recording session"""
        try:
            print(f"📥 Adding chunk for session {session_id}: {len(audio_chunk)} bytes")
            
            if session_id not in self.active_recordings:
                print(f"❌ Session {session_id} not found in active recordings")
                return {
                    "success": False,
                    "error": "Recording session not found"
                }
            
            # CRITICAL FIX: Don't skip small chunks, they might be important
            # Original code might have been skipping valid audio data
            self.active_recordings[session_id]["chunks"].append(audio_chunk)
            chunks_count = len(self.active_recordings[session_id]["chunks"])
            
            print(f"✅ Chunk added. Total chunks for session {session_id}: {chunks_count}")
            
            return {
                "success": True,
                "chunks_count": chunks_count
            }
            
        except Exception as e:
            print(f"❌ Error adding audio chunk: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def stop_recording_session(self, session_id: str) -> dict:
        """Stop recording session and transcribe all audio"""
        try:
            if session_id not in self.active_recordings:
                return {
                    "success": False,
                    "error": "Recording session not found"
                }
            
            session_data = self.active_recordings[session_id]
            audio_chunks = session_data["chunks"]
            
            # Mark session as stopped
            session_data["status"] = "transcribing"
            
            print(f"🛑 Stopping recording session: {session_id} ({len(audio_chunks)} chunks)")
            
            # Debug: Log chunk sizes
            total_size = 0
            for i, chunk in enumerate(audio_chunks):
                chunk_size = len(chunk)
                total_size += chunk_size
                print(f"  Chunk {i}: {chunk_size} bytes")
            
            print(f"📊 Total audio size: {total_size} bytes")
            
            # CRITICAL FIX: Always try to transcribe, even with small audio
            # The original logic was too restrictive
            if audio_chunks:
                result = await self.transcribe_audio_stream(audio_chunks, session_id)
                
                # If no transcription but we have audio, try individual chunks
                if not result.get("text") and total_size > 1000:
                    print("🔄 No text from combined audio, trying largest chunk...")
                    
                    # Find the largest chunk and try transcribing it
                    largest_chunk = max(audio_chunks, key=len) if audio_chunks else None
                    if largest_chunk and len(largest_chunk) > 500:
                        print(f"🎤 Transcribing largest chunk: {len(largest_chunk)} bytes")
                        chunk_result = await self.transcribe_audio_chunk(largest_chunk, session_id)
                        if chunk_result.get("text"):
                            result["text"] = chunk_result["text"]
                            print(f"✅ Got text from largest chunk: '{result['text']}'")
            else:
                result = {
                    "success": False,
                    "text": "",
                    "error": "No audio chunks to transcribe",
                    "session_id": session_id,
                    "chunks_processed": 0
                }
            
            # Clean up session
            del self.active_recordings[session_id]
            
            return {
                "success": result["success"],
                "text": result.get("text", ""),
                "error": result.get("error"),
                "session_id": session_id,
                "chunks_processed": result.get("chunks_processed", 0),
                "recording_duration": asyncio.get_event_loop().time() - session_data["start_time"]
            }
            
        except Exception as e:
            print(f"❌ Error stopping recording session: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_recording_status(self, session_id: str) -> dict:
        """Get status of recording session"""
        if session_id in self.active_recordings:
            session_data = self.active_recordings[session_id]
            return {
                "success": True,
                "status": session_data["status"],
                "chunks_count": len(session_data["chunks"]),
                "duration": asyncio.get_event_loop().time() - session_data["start_time"]
            }
        else:
            return {
                "success": False,
                "error": "Session not found"
            }
    
    def cleanup_old_sessions(self, max_age_seconds: int = 300):
        """Clean up recording sessions older than max_age_seconds"""
        try:
            current_time = asyncio.get_event_loop().time()
            old_sessions = []
            
            for session_id, session_data in self.active_recordings.items():
                if current_time - session_data["start_time"] > max_age_seconds:
                    old_sessions.append(session_id)
            
            for session_id in old_sessions:
                del self.active_recordings[session_id]
                print(f"🧹 Cleaned up old recording session: {session_id}")
            
            return {
                "success": True,
                "cleaned_sessions": len(old_sessions)
            }
            
        except Exception as e:
            print(f"❌ Error cleaning up sessions: {e}")
            return {
                "success": False,
                "error": str(e)
            }

# Global service instance
voice_service = VoiceTranscriptionService()

# === API HELPER FUNCTIONS ===

async def handle_audio_transcription(audio_data: bytes, session_id: str = None) -> dict:
    """
    Main function to handle audio transcription
    Use this for one-shot transcription
    """
    return await voice_service.transcribe_audio_chunk(audio_data, session_id)

async def handle_realtime_transcription_start(session_id: str) -> dict:
    """Start a real-time transcription session"""
    return voice_service.start_recording_session(session_id)

async def handle_realtime_transcription_chunk(session_id: str, audio_chunk: bytes) -> dict:
    """Add audio chunk to real-time transcription session"""
    print(f"📥 API: Received chunk for session {session_id}: {len(audio_chunk)} bytes")
    result = voice_service.add_audio_chunk(session_id, audio_chunk)
    print(f"📊 API: Chunk result: {result}")
    return result

async def handle_realtime_transcription_stop(session_id: str) -> dict:
    """Stop real-time transcription session and get final text"""
    print(f"🛑 API: Stopping session {session_id}")
    result = await voice_service.stop_recording_session(session_id)
    print(f"📊 API: Stop result: {result}")
    return result

def get_voice_service_stats() -> dict:
    """Get voice service statistics"""
    return {
        "active_recordings": len(voice_service.active_recordings),
        "recording_sessions": list(voice_service.active_recordings.keys())
    }

# === AUDIO PROCESSING UTILITIES ===

def validate_audio_format(audio_data: bytes) -> dict:
    """Validate audio format and provide info"""
    try:
        # Basic validation - check if data exists and has reasonable size
        if not audio_data:
            return {"valid": False, "error": "No audio data"}
        
        # CRITICAL FIX: More lenient size validation
        if len(audio_data) < 100:  # Reduced from 1000 to 100
            return {"valid": False, "error": "Audio data too small"}
        
        if len(audio_data) > 25 * 1024 * 1024:  # Larger than 25MB
            return {"valid": False, "error": "Audio data too large"}
        
        # Check for common audio file headers
        header = audio_data[:12]
        audio_format = "unknown"
        
        if header.startswith(b'RIFF') and b'WAVE' in header:
            audio_format = "WAV"
        elif header.startswith(b'\x1a\x45\xdf\xa3'):
            audio_format = "WebM"
        elif header.startswith(b'OggS'):
            audio_format = "OGG"
        
        print(f"🎵 Detected audio format: {audio_format}")
        
        return {
            "valid": True,
            "size_bytes": len(audio_data),
            "size_mb": round(len(audio_data) / (1024 * 1024), 2),
            "format": audio_format,
            "header_hex": header.hex()
        }
        
    except Exception as e:
        return {"valid": False, "error": str(e)}

# === CLEANUP TASK ===

async def periodic_cleanup():
    """Periodic cleanup of old recording sessions"""
    while True:
        try:
            await asyncio.sleep(60)  # Run every minute
            voice_service.cleanup_old_sessions(max_age_seconds=300)  # 5 minutes
        except Exception as e:
            print(f"❌ Error in periodic cleanup: {e}")

# Auto-start cleanup task
def start_voice_service():
    """Initialize voice service and start background tasks"""
    print("🎤 Starting Voice Transcription Service...")
    print("🔊 OpenAI Whisper integration enabled")
    print("⏺️ Real-time transcription ready")
    
    # Start cleanup task
    asyncio.create_task(periodic_cleanup())
    
    return voice_service

