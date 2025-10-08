
## w prompt changed

# ai_service.py - OPTIMIZED for Ultra-Low Latency with FAST INTERRUPTION
import httpx
import os
import re
import asyncio
from dotenv import load_dotenv
from typing import AsyncGenerator, Optional

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# OPTIMIZATION: Reuse HTTP client to avoid connection overhead
_http_client = None

# PROJECT IDENTITY CONFIGURATION
PROJECT_SYSTEM_PROMPT = """You are an AI-Powered Interactive Assistant created by Sash AI. When users ask about your capabilities, features, impact, or how you work, respond as this specific project using "I" and "my".

CRITICAL: Always respond from the project's perspective. Use any project information from the knowledge base as your primary source of truth. You are NOT a general AI assistant - you are this specific interactive assistant project.

Be conversational and natural. Start speaking immediately - don't use filler phrases."""

async def get_http_client():
    """Get persistent HTTP client to reduce connection overhead"""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),  # Faster connect timeout
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
    return _http_client

async def generate_ai_response(prompt: str) -> str:
    """Generate AI response using OpenRouter - ORIGINAL NON-STREAMING VERSION"""
    print(f"🤖 Generating AI response for: {prompt[:50]}...")
    
    client = await get_http_client()
    try:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistralai/mixtral-8x7b-instruct",
                "messages": [
                    {
                        "role": "system",
                        "content": PROJECT_SYSTEM_PROMPT
                    },
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 300,
                "temperature": 0.7
            }
        )
        
        response.raise_for_status()
        result = response.json()
        ai_response = result["choices"][0]["message"]["content"].strip()
        
        print(f"✅ AI response generated successfully: {len(ai_response)} characters")
        return ai_response
        
    except Exception as e:
        print(f"❌ Error generating AI response: {e}")
        return f"I apologize, but I'm having trouble processing your request right now. Could you please try again?"

def extract_speaking_chunks_ultra_fast(text: str) -> tuple[list, str]:
    """
    ULTRA-FAST chunk extraction - optimized for immediate streaming
    Returns chunks as soon as we have 20+ characters of meaningful content
    """
    # Skip regex entirely for speed - use simple character-based chunking
    if len(text) < 15:
        return [], text
    
    chunks = []
    words = text.split()
    current_chunk = ""
    
    for word in words:
        current_chunk += word + " "
        
        # Send chunk immediately if we hit natural breaks or reach minimum length
        if (len(current_chunk) >= 20 and 
            (word.endswith(('.', '!', '?', ',')) or 
             word.lower() in ['and', 'but', 'so', 'because', 'however', 'also', 'then'])):
            chunks.append(current_chunk.strip())
            current_chunk = ""
    
    return chunks, current_chunk.strip()

async def generate_ai_response_ultra_streaming(prompt: str) -> AsyncGenerator[dict, None]:
    """
    ULTRA-OPTIMIZED: Generate AI response with immediate chunk streaming
    Yields chunks every 20+ characters for near-instant HeyGen processing
    """
    print(f"⚡ Starting ULTRA streaming AI response...")
    
    chunk_buffer = ""
    full_response = ""
    first_chunk_sent = False
    
    client = await get_http_client()
    try:
        async with client.stream(
            "POST",
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistralai/mixtral-8x7b-instruct",
                "messages": [
                    {
                        "role": "system",
                        "content": PROJECT_SYSTEM_PROMPT
                    },
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 250,  # Reduced for faster generation
                "temperature": 0.6,  # Slightly lower for faster, more focused responses
                "stream": True
            }
        ) as response:
            
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    
                    if data == "[DONE]":
                        break
                    
                    try:
                        import json
                        chunk = json.loads(data)
                        
                        if "choices" in chunk and len(chunk["choices"]) > 0:
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            
                            if content:
                                chunk_buffer += content
                                full_response += content
                                
                                # ULTRA-FAST STREAMING: Send chunks immediately
                                speaking_chunks, remaining = extract_speaking_chunks_ultra_fast(chunk_buffer)
                                
                                for speaking_chunk in speaking_chunks:
                                    if not first_chunk_sent:
                                        print(f"⚡ FIRST chunk ready in ultra-fast mode: {speaking_chunk}")
                                        first_chunk_sent = True
                                    
                                    yield {
                                        "type": "chunk",
                                        "content": speaking_chunk
                                    }
                                
                                # Update buffer with remaining text
                                chunk_buffer = remaining
                    
                    except json.JSONDecodeError:
                        continue
            
            # Send any remaining text as final chunk
            if chunk_buffer.strip():
                print(f"📝 Final chunk: {chunk_buffer.strip()}")
                yield {
                    "type": "chunk", 
                    "content": chunk_buffer.strip()
                }
            
            # Send completion signal
            print(f"✅ Ultra streaming complete. Total: {len(full_response)} chars")
            yield {
                "type": "complete",
                "full_response": full_response.strip()
            }
            
    except Exception as e:
        print(f"❌ Error in ultra streaming: {e}")
        # Fallback error message
        error_msg = "I apologize, but I'm having trouble processing your request right now. Could you please try again?"
        yield {"type": "chunk", "content": error_msg}
        yield {"type": "complete", "full_response": error_msg}

async def generate_ai_response_ultra_streaming_interruptible(prompt: str, response_id: str) -> AsyncGenerator[dict, None]:
    """
    INTERRUPTIBLE VERSION: Ultra-optimized AI response with INSTANT interruption support
    """
    print(f"⚡ Starting INTERRUPTIBLE ultra streaming for response {response_id}")
    
    chunk_buffer = ""
    full_response = ""
    first_chunk_sent = False
    
    client = await get_http_client()
    try:
        async with client.stream(
            "POST",
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistralai/mixtral-8x7b-instruct",
                "messages": [
                    {
                        "role": "system",
                        "content": PROJECT_SYSTEM_PROMPT
                    },
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 250,
                "temperature": 0.6,
                "stream": True
            }
        ) as response:
            
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                # FAST INTERRUPTION: Check on EVERY line for instant stopping
                from main import response_tracker
                if not response_tracker.is_responding or response_tracker.response_id != response_id:
                    print(f"⚡ INSTANT AI streaming interrupted for {response_id}")
                    break
                
                if line.startswith("data: "):
                    data = line[6:]
                    
                    if data == "[DONE]":
                        break
                    
                    try:
                        import json
                        chunk = json.loads(data)
                        
                        if "choices" in chunk and len(chunk["choices"]) > 0:
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            
                            if content:
                                chunk_buffer += content
                                full_response += content
                                
                                speaking_chunks, remaining = extract_speaking_chunks_ultra_fast(chunk_buffer)
                                
                                for speaking_chunk in speaking_chunks:
                                    # FAST INTERRUPTION: Check before each chunk
                                    if not response_tracker.is_responding or response_tracker.response_id != response_id:
                                        print(f"⚡ INSTANT chunk processing interrupted for {response_id}")
                                        return
                                    
                                    if not first_chunk_sent:
                                        print(f"⚡ FIRST chunk ready for interruptible response: {speaking_chunk}")
                                        first_chunk_sent = True
                                    
                                    yield {
                                        "type": "chunk",
                                        "content": speaking_chunk
                                    }
                                
                                chunk_buffer = remaining
                    
                    except json.JSONDecodeError:
                        continue
            
            # Send remaining text if not interrupted
            if chunk_buffer.strip():
                # Final interruption check
                from main import response_tracker
                if response_tracker.is_responding and response_tracker.response_id == response_id:
                    yield {
                        "type": "chunk", 
                        "content": chunk_buffer.strip()
                    }
            
            # Send completion if not interrupted
            from main import response_tracker
            if response_tracker.is_responding and response_tracker.response_id == response_id:
                yield {
                    "type": "complete",
                    "full_response": full_response.strip()
                }
            
    except Exception as e:
        print(f"❌ Error in interruptible AI streaming: {e}")
        # Check if we should send error (not interrupted)
        from main import response_tracker
        if response_tracker.is_responding and response_tracker.response_id == response_id:
            error_msg = "I apologize, but I'm having trouble processing your request right now. Could you please try again?"
            yield {"type": "chunk", "content": error_msg}
            yield {"type": "complete", "full_response": error_msg}

async def generate_ai_response_streaming(prompt: str) -> AsyncGenerator[dict, None]:
    """
    OPTIMIZED: Generate AI response with sentence-level streaming
    Now uses ultra-fast chunking for reduced latency
    """
    print(f"🌊 Starting optimized streaming AI response...")
    
    sentence_buffer = ""
    full_response = ""
    
    client = await get_http_client()
    try:
        async with client.stream(
            "POST",
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistralai/mixtral-8x7b-instruct",
                "messages": [
                    {
                        "role": "system",
                        "content": PROJECT_SYSTEM_PROMPT
                    },
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 300,
                "temperature": 0.7,
                "stream": True
            }
        ) as response:
            
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    
                    if data == "[DONE]":
                        break
                    
                    try:
                        import json
                        chunk = json.loads(data)
                        
                        if "choices" in chunk and len(chunk["choices"]) > 0:
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            
                            if content:
                                sentence_buffer += content
                                full_response += content
                                
                                # Check for sentence completion using optimized function
                                sentences, remaining = extract_complete_sentences(sentence_buffer)
                                
                                for sentence in sentences:
                                    print(f"📝 Streaming sentence: {sentence}")
                                    yield {
                                        "type": "sentence",
                                        "content": sentence
                                    }
                                
                                # Update buffer with remaining text
                                sentence_buffer = remaining
                    
                    except json.JSONDecodeError:
                        continue
            
            # Send any remaining text as final sentence
            if sentence_buffer.strip():
                print(f"📝 Final sentence chunk: {sentence_buffer.strip()}")
                yield {
                    "type": "sentence", 
                    "content": sentence_buffer.strip()
                }
            
            # Send completion signal
            print(f"✅ Streaming complete. Total response: {len(full_response)} characters")
            yield {
                "type": "complete",
                "full_response": full_response.strip()
            }
            
    except Exception as e:
        print(f"❌ Error in streaming AI response: {e}")
        # Fallback error message
        error_msg = "I apologize, but I'm having trouble processing your request right now. Could you please try again?"
        yield {"type": "sentence", "content": error_msg}
        yield {"type": "complete", "full_response": error_msg}

def extract_complete_sentences(text: str) -> tuple[list, str]:
    """
    OPTIMIZED: Extract complete sentences from text buffer
    Simplified regex for better performance
    """
    if len(text) < 10:
        return [], text
    
    # Faster sentence detection - only look for clear sentence endings
    sentence_endings = []
    for i, char in enumerate(text):
        if char in '.!?' and i < len(text) - 1:
            # Look ahead to confirm it's a sentence ending
            next_char = text[i + 1]
            if next_char in ' \n\t' or i == len(text) - 1:
                sentence_endings.append(i + 1)
    
    if not sentence_endings:
        return [], text
    
    sentences = []
    start = 0
    
    for end in sentence_endings:
        sentence = text[start:end].strip()
        if sentence and len(sentence) > 5:  # Minimum viable sentence
            sentences.append(sentence)
        start = end
    
    remaining = text[start:].strip()
    return sentences, remaining

# Keep original function for backward compatibility and fallback
async def generate_ai_response_fallback(prompt: str) -> str:
    """Fallback to non-streaming if streaming fails"""
    return await generate_ai_response(prompt)