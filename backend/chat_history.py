
## w interruption latest 
# chat_history.py
import json
import os
import uuid
import sqlite3
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path

# Configuration
CHAT_HISTORY_FILE = "chat_history.json"  # Keep for backward compatibility/export
CHAT_DB_FILE = "chat_history.db"
DEFAULT_CONVERSATION_ID = "default_session"

# Global variables for compatibility
chat_sessions = {}
chat_messages = []  # Will be populated from database
current_conversation_id = DEFAULT_CONVERSATION_ID

class ChatMessage:
    """Represents a single chat message"""
    def __init__(self, 
                 message_type: str,  # 'user' or 'avatar'
                 content: str,
                 metadata: Optional[Dict[str, Any]] = None):
        self.id = str(uuid.uuid4())
        self.timestamp = datetime.now().isoformat()
        self.type = message_type
        self.content = content
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "type": self.type,
            "content": self.content,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMessage':
        message = cls(
            message_type=data["type"],
            content=data["content"],
            metadata=data.get("metadata", {})
        )
        message.id = data["id"]
        message.timestamp = data["timestamp"]
        return message

class HybridChatStorage:
    """SQLite + ChromaDB hybrid chat storage"""
    
    def __init__(self, db_path: str = CHAT_DB_FILE):
        self.db_path = db_path
        self.init_db()
        self._kb = None  # Lazy load knowledge base
    
    def init_db(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_indexed BOOLEAN DEFAULT FALSE
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                type TEXT CHECK(type IN ('user', 'avatar')),
                content TEXT NOT NULL,
                timestamp DATETIME,
                metadata TEXT,
                FOREIGN KEY(conversation_id) REFERENCES conversations(id)
            )
        ''')
        
        # Indexes for performance
        conn.execute('CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at)')
        
        conn.commit()
        conn.close()
    
    def ensure_conversation_exists(self, conversation_id: str):
        """Ensure conversation exists in database"""
        conn = sqlite3.connect(self.db_path)
        
        # Check if conversation exists
        exists = conn.execute(
            "SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        
        if not exists:
            # Create conversation
            title = f"Chat Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            conn.execute(
                "INSERT INTO conversations (id, title) VALUES (?, ?)",
                (conversation_id, title)
            )
            conn.commit()
        
        conn.close()
    
    def save_message(self, message: ChatMessage, conversation_id: str = DEFAULT_CONVERSATION_ID):
        """Save message to database"""
        self.ensure_conversation_exists(conversation_id)
        
        conn = sqlite3.connect(self.db_path)
        
        # Insert message
        conn.execute(
            """INSERT INTO messages (id, conversation_id, type, content, timestamp, metadata) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                message.id, 
                conversation_id, 
                message.type, 
                message.content, 
                message.timestamp,
                json.dumps(message.metadata)
            )
        )
        
        # Update conversation timestamp
        conn.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,)
        )
        
        conn.commit()
        conn.close()
    
    def load_messages(self, conversation_id: str = DEFAULT_CONVERSATION_ID, limit: Optional[int] = None) -> List[ChatMessage]:
        """Load messages from database"""
        conn = sqlite3.connect(self.db_path)
        
        query = """SELECT id, type, content, timestamp, metadata 
                   FROM messages 
                   WHERE conversation_id = ? 
                   ORDER BY timestamp ASC"""
        
        if limit:
            query += f" LIMIT {limit}"
        
        rows = conn.execute(query, (conversation_id,)).fetchall()
        conn.close()
        
        messages = []
        for row in rows:
            message = ChatMessage(row[1], row[2], json.loads(row[4] or "{}"))
            message.id = row[0]
            message.timestamp = row[3]
            messages.append(message)
        
        return messages
    
    def get_all_messages_dict(self, conversation_id: str = DEFAULT_CONVERSATION_ID) -> List[Dict[str, Any]]:
        """Get all messages as dictionaries (for compatibility)"""
        messages = self.load_messages(conversation_id)
        return [msg.to_dict() for msg in messages]
    
    def search_messages(self, query: str, conversation_id: str = DEFAULT_CONVERSATION_ID, limit: int = 10) -> List[Dict[str, Any]]:
        """Search messages in database"""
        conn = sqlite3.connect(self.db_path)
        
        rows = conn.execute(
            """SELECT id, type, content, timestamp, metadata 
               FROM messages 
               WHERE conversation_id = ? AND content LIKE ?
               ORDER BY timestamp DESC
               LIMIT ?""",
            (conversation_id, f"%{query}%", limit)
        ).fetchall()
        
        conn.close()
        
        messages = []
        for row in rows:
            message = ChatMessage(row[1], row[2], json.loads(row[4] or "{}"))
            message.id = row[0]
            message.timestamp = row[3]
            messages.append(message.to_dict())
        
        return messages
    
    def get_stats(self, conversation_id: str = DEFAULT_CONVERSATION_ID) -> Dict[str, Any]:
        """Get chat statistics"""
        conn = sqlite3.connect(self.db_path)
        
        # Get message counts
        stats = conn.execute(
            """SELECT 
                COUNT(*) as total_messages,
                SUM(CASE WHEN type = 'user' THEN 1 ELSE 0 END) as user_messages,
                SUM(CASE WHEN type = 'avatar' THEN 1 ELSE 0 END) as avatar_messages,
                MIN(timestamp) as conversation_start,
                MAX(timestamp) as conversation_end
               FROM messages WHERE conversation_id = ?""",
            (conversation_id,)
        ).fetchone()
        
        # Enhanced stats to include interrupt tracking
        voice_kb_stats = conn.execute(
            """SELECT 
                SUM(CASE WHEN type = 'user' AND (
                    json_extract(metadata, '$.voice_used') = 1 OR 
                    json_extract(metadata, '$.voice_used') = true OR
                    json_extract(metadata, '$.source') = 'voice_input'
                ) THEN 1 ELSE 0 END) as voice_messages,
                SUM(CASE WHEN type = 'avatar' AND (
                    json_extract(metadata, '$.used_knowledge_base') = 1 OR
                    json_extract(metadata, '$.used_knowledge_base') = true
                ) THEN 1 ELSE 0 END) as kb_responses,
                SUM(CASE WHEN type = 'avatar' AND (
                    json_extract(metadata, '$.was_interrupted') = 1 OR
                    json_extract(metadata, '$.was_interrupted') = true
                ) THEN 1 ELSE 0 END) as interrupted_responses
               FROM messages WHERE conversation_id = ?""",
            (conversation_id,)
        ).fetchone()
        
        # Get today's messages
        today_count = conn.execute(
            """SELECT COUNT(*) FROM messages 
               WHERE conversation_id = ? 
               AND date(timestamp) = date('now')""",
            (conversation_id,)
        ).fetchone()[0]
        
        conn.close()
        
        return {
            "total_messages": stats[0] or 0,
            "user_messages": stats[1] or 0,
            "avatar_messages": stats[2] or 0,
            "voice_messages": voice_kb_stats[0] or 0,
            "kb_enhanced_responses": voice_kb_stats[1] or 0,
            "interrupted_responses": voice_kb_stats[2] or 0,  # NEW: Track interrupted responses
            "messages_today": today_count or 0,
            "conversation_start": stats[3],
            "conversation_end": stats[4],
            "has_messages": (stats[0] or 0) > 0
        }

# Global storage instance
_storage = HybridChatStorage()

def load_chat_history():
    """Load chat history from database (compatibility function)"""
    global chat_messages
    
    try:
        print("Loading chat history from database...")
        
        # Load messages into global variable for compatibility
        chat_messages = _storage.load_messages(current_conversation_id)
        
        print(f"Loaded {len(chat_messages)} messages from chat history")
        
        # Also try to migrate from old JSON file if it exists
        if os.path.exists(CHAT_HISTORY_FILE) and len(chat_messages) == 0:
            print("Found old JSON chat history, migrating to database...")
            _migrate_from_json()
            chat_messages = _storage.load_messages(current_conversation_id)
        
    except Exception as e:
        print(f"Error loading chat history: {e}")
        chat_messages = []

def _migrate_from_json():
    """Migrate old JSON chat history to database"""
    try:
        with open(CHAT_HISTORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            old_messages = [ChatMessage.from_dict(msg_data) for msg_data in data.get("messages", [])]
        
        for msg in old_messages:
            _storage.save_message(msg, current_conversation_id)
        
        print(f"Migrated {len(old_messages)} messages from JSON to database")
        
        # Backup old file
        backup_file = f"{CHAT_HISTORY_FILE}.backup"
        os.rename(CHAT_HISTORY_FILE, backup_file)
        print(f"Old JSON file backed up as {backup_file}")
        
    except Exception as e:
        print(f"Error migrating from JSON: {e}")

def save_chat_history():
    """Save chat history (compatibility function - now handled automatically)"""
    # Database saves automatically, but we can refresh the global messages
    global chat_messages
    chat_messages = _storage.load_messages(current_conversation_id)
    print(f"Chat history synchronized - {len(chat_messages)} messages")
    return True

async def add_user_message(content: str, metadata: Optional[Dict[str, Any]] = None) -> ChatMessage:
    """Add a user message to chat history"""
    try:
        # Enhance metadata with default values
        if metadata is None:
            metadata = {}
        
        # Enhanced voice detection and metadata
        voice_used = (
            metadata.get("voice_used", False) or 
            metadata.get("source") == "voice_input" or
            metadata.get("input_method") == "voice"
        )
        
        metadata.update({
            "source": metadata.get("source", "text_input"),  # text_input, voice_input
            "session_id": metadata.get("session_id", current_conversation_id),
            "voice_used": voice_used,
            "input_method": metadata.get("input_method", "keyboard"),
            # Additional voice-related metadata
            "voice_language": metadata.get("voice_language"),
            "voice_duration": metadata.get("voice_duration"),
            "transcription_confidence": metadata.get("transcription_confidence"),
            "audio_quality": metadata.get("audio_quality")
        })
        
        message = ChatMessage("user", content, metadata)
        
        # Save to database
        _storage.save_message(message, current_conversation_id)
        
        # Update global list for compatibility
        global chat_messages
        chat_messages.append(message)
        
        # Enhanced logging for voice messages
        voice_indicator = " (voice)" if voice_used else ""
        print(f"Added user message{voice_indicator}: {content[:50]}{'...' if len(content) > 50 else ''}")
        
        return message
        
    except Exception as e:
        print(f"Error adding user message: {e}")
        raise

async def add_avatar_message(content: str, metadata: Optional[Dict[str, Any]] = None) -> ChatMessage:
    """Add an avatar response to chat history"""
    try:
        # Enhance metadata with default values
        if metadata is None:
            metadata = {}
        
        # NEW: Add interrupt tracking to metadata
        metadata.update({
            "avatar_id": metadata.get("avatar_id"),
            "voice_id": metadata.get("voice_id"),
            "session_id": metadata.get("session_id", current_conversation_id),
            "heygen_sent": metadata.get("heygen_sent", False),
            "heygen_sessions_sent": metadata.get("heygen_sessions_sent", 0),
            "used_knowledge_base": metadata.get("used_knowledge_base", False),
            "context_length": metadata.get("context_length", 0),
            "ai_service": metadata.get("ai_service", "openai"),
            "response_time": metadata.get("response_time", 0),
            "first_chunk_latency": metadata.get("first_chunk_latency"),
            # NEW: Interrupt tracking
            "was_interrupted": metadata.get("was_interrupted", False),
            "interrupt_reason": metadata.get("interrupt_reason"),
            "partial_response": metadata.get("partial_response", False),
            # Enhanced voice response metadata
            "voice_generated": metadata.get("voice_generated", False),
            "tts_service": metadata.get("tts_service"),
            "voice_quality": metadata.get("voice_quality"),
            "audio_duration": metadata.get("audio_duration"),
            # Context mode tracking
            "ultra_fast_mode": metadata.get("ultra_fast_mode", False),
            "context_mode": metadata.get("context_mode", False)
        })
        
        message = ChatMessage("avatar", content, metadata)
        
        # Save to database
        _storage.save_message(message, current_conversation_id)
        
        # Update global list for compatibility
        global chat_messages
        chat_messages.append(message)
        
        # Enhanced logging with interrupt status
        kb_indicator = " (KB)" if metadata.get("used_knowledge_base") else ""
        voice_indicator = " (voice)" if metadata.get("voice_generated") else ""
        interrupt_indicator = " [INTERRUPTED]" if metadata.get("was_interrupted") else ""
        
        print(f"Added avatar message{kb_indicator}{voice_indicator}{interrupt_indicator}: {content[:50]}{'...' if len(content) > 50 else ''}")
        
        return message
        
    except Exception as e:
        print(f"Error adding avatar message: {e}")
        raise

# NEW: Function to mark a message as interrupted
async def mark_message_interrupted(message_id: str, interrupt_reason: str = None) -> bool:
    """Mark an existing message as interrupted"""
    try:
        conn = sqlite3.connect(CHAT_DB_FILE)
        
        # Get current metadata
        row = conn.execute(
            "SELECT metadata FROM messages WHERE id = ?",
            (message_id,)
        ).fetchone()
        
        if not row:
            conn.close()
            return False
        
        # Update metadata with interrupt info
        metadata = json.loads(row[0] or "{}")
        metadata.update({
            "was_interrupted": True,
            "interrupt_reason": interrupt_reason,
            "interrupted_at": datetime.now().isoformat()
        })
        
        # Save updated metadata
        conn.execute(
            "UPDATE messages SET metadata = ? WHERE id = ?",
            (json.dumps(metadata), message_id)
        )
        
        conn.commit()
        conn.close()
        
        print(f"Marked message {message_id} as interrupted: {interrupt_reason}")
        
        # Update global chat_messages if needed
        global chat_messages
        for msg in chat_messages:
            if msg.id == message_id:
                msg.metadata.update(metadata)
                break
        
        return True
        
    except Exception as e:
        print(f"Error marking message as interrupted: {e}")
        return False

def get_chat_history(limit: Optional[int] = None, 
                    message_type: Optional[str] = None,
                    session_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get chat history with optional filters"""
    try:
        # Use session_id if provided, otherwise use current conversation
        conversation_id = session_id or current_conversation_id
        
        # Get messages from database
        all_messages = _storage.get_all_messages_dict(conversation_id)
        
        # Filter by message type
        if message_type:
            all_messages = [msg for msg in all_messages if msg['type'] == message_type]
        
        # Apply limit
        if limit:
            all_messages = all_messages[-limit:]
        
        return all_messages
        
    except Exception as e:
        print(f"Error getting chat history: {e}")
        return []

def search_chat_history(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search through chat history"""
    try:
        return _storage.search_messages(query, current_conversation_id, limit)
        
    except Exception as e:
        print(f"Error searching chat history: {e}")
        return []

def get_chat_stats() -> Dict[str, Any]:
    """Get chat history statistics including interrupt tracking"""
    try:
        stats = _storage.get_stats(current_conversation_id)
        
        # Calculate interrupt percentage if there are avatar messages
        if stats["avatar_messages"] > 0:
            stats["interrupt_percentage"] = round(
                (stats["interrupted_responses"] / stats["avatar_messages"]) * 100, 1
            )
        else:
            stats["interrupt_percentage"] = 0
        
        return stats
        
    except Exception as e:
        print(f"Error getting chat stats: {e}")
        return {
            "total_messages": 0,
            "user_messages": 0,
            "avatar_messages": 0,
            "voice_messages": 0,
            "kb_enhanced_responses": 0,
            "interrupted_responses": 0,
            "interrupt_percentage": 0,
            "messages_today": 0,
            "conversation_start": None,
            "conversation_end": None,
            "has_messages": False
        }

def export_chat_history(format_type: str = "json") -> Dict[str, Any]:
    """Export chat history in different formats"""
    try:
        messages = _storage.get_all_messages_dict(current_conversation_id)
        
        if format_type == "json":
            return {
                "success": True,
                "format": "json",
                "data": {
                    "messages": messages,
                    "stats": get_chat_stats(),
                    "exported_at": datetime.now().isoformat()
                }
            }
        
        elif format_type == "txt":
            # Create a readable text transcript with interrupt indicators
            transcript_lines = []
            transcript_lines.append("=== CHAT TRANSCRIPT ===")
            transcript_lines.append(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            transcript_lines.append(f"Total Messages: {len(messages)}")
            
            stats = get_chat_stats()
            if stats["interrupted_responses"] > 0:
                transcript_lines.append(f"Interrupted Responses: {stats['interrupted_responses']} ({stats['interrupt_percentage']}%)")
            
            transcript_lines.append("=" * 50)
            transcript_lines.append("")
            
            for message in messages:
                timestamp = datetime.fromisoformat(message['timestamp']).strftime('%H:%M:%S')
                speaker = "USER" if message['type'] == "user" else "AVATAR"
                
                # Enhanced metadata indicators including interrupts
                indicators = []
                if message['type'] == "user":
                    if (message['metadata'].get("voice_used") or 
                        message['metadata'].get("source") == "voice_input"):
                        indicators.append("(voice)")
                        
                if message['type'] == "avatar":
                    if message['metadata'].get("used_knowledge_base"):
                        indicators.append("(KB)")
                    if message['metadata'].get("voice_generated"):
                        indicators.append("(TTS)")
                    # NEW: Show interrupt status
                    if message['metadata'].get("was_interrupted"):
                        indicators.append("[INTERRUPTED]")
                
                indicator_str = " " + " ".join(indicators) if indicators else ""
                
                transcript_lines.append(f"[{timestamp}] {speaker}{indicator_str}:")
                transcript_lines.append(f"  {message['content']}")
                
                # Show interrupt reason if available
                if message['metadata'].get("was_interrupted") and message['metadata'].get("interrupt_reason"):
                    transcript_lines.append(f"    -> Interrupted: {message['metadata']['interrupt_reason']}")
                
                transcript_lines.append("")
            
            return {
                "success": True,
                "format": "txt",
                "data": "\n".join(transcript_lines)
            }
        
        else:
            return {
                "success": False,
                "error": f"Unsupported format: {format_type}"
            }
            
    except Exception as e:
        print(f"Error exporting chat history: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def delete_message(message_id: str) -> Dict[str, Any]:
    """Delete a specific message from chat history"""
    try:
        global chat_messages
        
        # Delete from database
        deleted = _storage.delete_message(message_id)
        
        if deleted:
            # Update global list
            chat_messages = [msg for msg in chat_messages if msg.id != message_id]
            
            return {
                "success": True,
                "message": "Message deleted successfully"
            }
        else:
            return {
                "success": False,
                "error": "Message not found"
            }
            
    except Exception as e:
        print(f"Error deleting message: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def clear_chat_history() -> Dict[str, Any]:
    """Clear all chat history"""
    try:
        global chat_messages
        
        # Clear from database
        message_count = _storage.clear_conversation(current_conversation_id)
        
        # Clear global list
        chat_messages = []
        
        print(f"Cleared {message_count} messages from chat history")
        
        return {
            "success": True,
            "cleared_messages": message_count,
            "message": f"Cleared {message_count} messages"
        }
        
    except Exception as e:
        print(f"Error clearing chat history: {e}")
        return {
            "success": False,
            "error": str(e)
        }

# NEW: Get interrupt statistics
def get_interrupt_stats(conversation_id: str = None) -> Dict[str, Any]:
    """Get detailed interrupt statistics"""
    try:
        conv_id = conversation_id or current_conversation_id
        messages = _storage.get_all_messages_dict(conv_id)
        
        interrupted_messages = []
        total_avatar_messages = 0
        
        for msg in messages:
            if msg['type'] == 'avatar':
                total_avatar_messages += 1
                if msg['metadata'].get('was_interrupted'):
                    interrupted_messages.append(msg)
        
        # Group by interrupt reason
        interrupt_reasons = {}
        for msg in interrupted_messages:
            reason = msg['metadata'].get('interrupt_reason', 'Unknown')
            interrupt_reasons[reason] = interrupt_reasons.get(reason, 0) + 1
        
        return {
            "total_avatar_messages": total_avatar_messages,
            "interrupted_count": len(interrupted_messages),
            "interrupt_percentage": round((len(interrupted_messages) / max(total_avatar_messages, 1)) * 100, 1),
            "interrupt_reasons": interrupt_reasons,
            "recent_interrupts": interrupted_messages[-5:] if interrupted_messages else []
        }
        
    except Exception as e:
        print(f"Error getting interrupt stats: {e}")
        return {
            "total_avatar_messages": 0,
            "interrupted_count": 0,
            "interrupt_percentage": 0,
            "interrupt_reasons": {},
            "recent_interrupts": []
        }

def get_conversation_context(last_n_messages: int = 10) -> str:
    """Get recent conversation context for AI"""
    try:
        messages = _storage.load_messages(current_conversation_id, limit=last_n_messages)
        
        if not messages:
            return ""
        
        context_lines = []
        context_lines.append("Recent conversation context:")
        
        for message in messages:
            timestamp = datetime.fromisoformat(message.timestamp).strftime('%H:%M')
            speaker = "User" if message.type == "user" else "Assistant"
            
            # Add indicators in context
            indicators = []
            if message.type == "user" and (message.metadata.get("voice_used") or 
                                         message.metadata.get("source") == "voice_input"):
                indicators.append("voice")
                
            if message.type == "avatar":
                if message.metadata.get("was_interrupted"):
                    indicators.append("interrupted")
                if message.metadata.get("used_knowledge_base"):
                    indicators.append("KB")
            
            indicator_str = f" ({', '.join(indicators)})" if indicators else ""
            
            context_lines.append(f"[{timestamp}] {speaker}{indicator_str}: {message.content}")
        
        return "\n".join(context_lines)
        
    except Exception as e:
        print(f"Error getting conversation context: {e}")
        return ""

def set_current_conversation(conversation_id: str):
    """Set the current conversation ID"""
    global current_conversation_id, chat_messages
    current_conversation_id = conversation_id
    
    # Reload messages for new conversation
    chat_messages = _storage.load_messages(conversation_id)
    print(f"Switched to conversation: {conversation_id} ({len(chat_messages)} messages)")

def get_current_conversation_id() -> str:
    """Get current conversation ID"""
    return current_conversation_id

# Initialize chat history on module import
def initialize_chat_history():
    """Initialize chat history system"""
    print("Initializing hybrid chat history system...")
    load_chat_history()
    print(f"Hybrid chat history system ready - {len(chat_messages)} existing messages")
    print(f"Database: {CHAT_DB_FILE}")
    print(f"Current conversation: {current_conversation_id}")

# Auto-initialize when module is imported
initialize_chat_history()