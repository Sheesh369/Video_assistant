
# knowledge_base.py - OPTIMIZED for Ultra-Low Latency Context Retrieval
import os
import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
import logging
from pathlib import Path
import time
import threading

# Document processing imports
import PyPDF2
import docx
import pandas as pd
from openpyxl import load_workbook
import json
import csv
from io import StringIO
import mimetypes

# ChromaDB imports
import chromadb
from chromadb.config import Settings
import numpy as np

# NVIDIA API for embeddings
import requests
import aiohttp

# Text processing
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
import re

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Download required NLTK data (run once)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

class NVIDIAEmbeddingModel:
    """NVIDIA embedding model wrapper - OPTIMIZED with connection pooling"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
        if not self.api_key:
            raise ValueError("NVIDIA_API_KEY environment variable is required")
        
        self.model_name = "nvidia/nv-embedqa-mistral-7b-v2"
        self.base_url = "https://integrate.api.nvidia.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # OPTIMIZATION: Persistent HTTP session
        self._session = None
        self._session_lock = threading.Lock()
    
    def _get_session(self):
        """Get persistent requests session"""
        with self._session_lock:
            if self._session is None:
                self._session = requests.Session()
                self._session.headers.update(self.headers)
                # Configure for faster connections
                adapter = requests.adapters.HTTPAdapter(
                    pool_connections=5,
                    pool_maxsize=10,
                    max_retries=1
                )
                self._session.mount('https://', adapter)
        return self._session
    
    def encode(self, texts: List[str], convert_to_tensor=False, input_type="passage") -> np.ndarray:
        """OPTIMIZED: Encode texts using NVIDIA embedding API (synchronous)"""
        try:
            # OPTIMIZATION: Batch size limit for faster processing
            if len(texts) > 50:
                logger.warning(f"Large batch size ({len(texts)}), consider reducing for faster processing")
            
            payload = {
                "input": texts,
                "model": self.model_name,
                "encoding_format": "float",
                "input_type": input_type
            }
            
            session = self._get_session()
            response = session.post(
                f"{self.base_url}/embeddings",
                json=payload,
                timeout=15  # Reduced timeout
            )
            
            if response.status_code != 200:
                logger.error(f"NVIDIA API error: {response.status_code} - {response.text}")
                raise Exception(f"NVIDIA API error: {response.status_code}")
            
            data = response.json()
            
            # Extract embeddings
            embeddings = []
            for item in data['data']:
                embeddings.append(item['embedding'])
            
            return np.array(embeddings)
            
        except Exception as e:
            logger.error(f"Error encoding texts with NVIDIA model: {e}")
            raise
    
    async def encode_async(self, texts: List[str], input_type="passage") -> np.ndarray:
        """OPTIMIZED: Async encoding with connection pooling"""
        try:
            payload = {
                "input": texts,
                "model": self.model_name,
                "encoding_format": "float",
                "input_type": input_type
            }
            
            # OPTIMIZATION: Use persistent connector
            connector = aiohttp.TCPConnector(
                limit=10,
                limit_per_host=5,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=15)  # Reduced timeout
            ) as session:
                async with session.post(
                    f"{self.base_url}/embeddings",
                    headers=self.headers,
                    json=payload
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"NVIDIA API error: {response.status} - {error_text}")
                        raise Exception(f"NVIDIA API error: {response.status}")
                    
                    data = await response.json()
                    
                    # Extract embeddings
                    embeddings = []
                    for item in data['data']:
                        embeddings.append(item['embedding'])
                    
                    return np.array(embeddings)
                    
        except Exception as e:
            logger.error(f"Error encoding texts with NVIDIA model (async): {e}")
            raise

class KnowledgeBase:
    def __init__(self, 
                 persist_directory: str = "./chroma_db",
                 collection_name: str = "knowledge_base",
                 nvidia_api_key: str = None,
                 chunk_size: int = 800,  # OPTIMIZATION: Smaller chunks for faster processing
                 chunk_overlap: int = 100):  # OPTIMIZATION: Less overlap
        """Initialize the Knowledge Base system - OPTIMIZED for speed"""
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Ensure persist directory exists
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Initialize NVIDIA embedding model
        logger.info(f"Initializing NVIDIA embedding model: nv-embedqa-mistral-7b-v2")
        self.embedding_model = NVIDIAEmbeddingModel(api_key=nvidia_api_key)
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(collection_name)
            logger.info(f"Loaded existing collection: {collection_name}")
        except:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "Knowledge base collection with NVIDIA embeddings"}
            )
            logger.info(f"Created new collection: {collection_name}")
        
        # Supported file types
        self.supported_extensions = {
            '.txt', '.pdf', '.docx', '.doc', '.xlsx', '.xls', '.csv', 
            '.json', '.md', '.html', '.xml', '.py', '.js', '.java', '.cpp', '.c'
        }
        
        # OPTIMIZATION: Cache for frequent searches
        self.search_cache = {}
        self.cache_duration = 60  # 1 minute cache
        self.cache_lock = threading.Lock()

    def _chunk_text_fast(self, text: str, metadata: Dict = None) -> List[Dict]:
        """OPTIMIZED: Fast text chunking with reduced processing"""
        if not text.strip():
            return []
            
        # OPTIMIZATION: Skip complex sentence tokenization for speed
        # Use simple splitting on periods for faster processing
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Simple chunking by character count with sentence awareness
        chunks = []
        words = text.split()
        current_chunk = ""
        current_length = 0
        
        for word in words:
            word_length = len(word) + 1  # +1 for space
            
            if current_length + word_length <= self.chunk_size:
                current_chunk += " " + word if current_chunk else word
                current_length += word_length
            else:
                if current_chunk:
                    chunks.append({
                        'text': current_chunk.strip(),
                        'metadata': metadata or {},
                        'chunk_id': str(uuid.uuid4()),
                        'length': len(current_chunk)
                    })
                
                # Start new chunk
                current_chunk = word
                current_length = word_length
        
        # Add final chunk
        if current_chunk:
            chunks.append({
                'text': current_chunk.strip(),
                'metadata': metadata or {},
                'chunk_id': str(uuid.uuid4()),
                'length': len(current_chunk)
            })
        
        return chunks

    # Keep original chunking method for full accuracy when needed
    def _chunk_text(self, text: str, metadata: Dict = None) -> List[Dict]:
        """Original text chunking method - preserved for accuracy"""
        if not text.strip():
            return []
            
        # Clean text
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Split into sentences for better chunking
        sentences = sent_tokenize(text)
        
        chunks = []
        current_chunk = ""
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            if current_length + sentence_length <= self.chunk_size:
                current_chunk += " " + sentence if current_chunk else sentence
                current_length += sentence_length
            else:
                if current_chunk:
                    chunks.append({
                        'text': current_chunk.strip(),
                        'metadata': metadata or {},
                        'chunk_id': str(uuid.uuid4()),
                        'length': len(current_chunk)
                    })
                
                # Start new chunk with overlap
                if len(sentence) <= self.chunk_size:
                    current_chunk = sentence
                    current_length = sentence_length
                else:
                    # Handle very long sentences
                    words = sentence.split()
                    current_chunk = " ".join(words[:self.chunk_size//10])
                    current_length = len(current_chunk)
        
        # Add final chunk
        if current_chunk:
            chunks.append({
                'text': current_chunk.strip(),
                'metadata': metadata or {},
                'chunk_id': str(uuid.uuid4()),
                'length': len(current_chunk)
            })
        
        return chunks

    # OPTIMIZATION: File processing methods remain the same but with faster chunking by default
    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF {file_path}: {e}")
            return ""

    def _extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            logger.error(f"Error extracting text from DOCX {file_path}: {e}")
            return ""

    def _extract_text_from_excel(self, file_path: str) -> str:
        """Extract text from Excel file"""
        try:
            df = pd.read_excel(file_path, sheet_name=None)
            text = ""
            for sheet_name, sheet_df in df.items():
                text += f"Sheet: {sheet_name}\n"
                text += sheet_df.to_string(index=False) + "\n\n"
            return text
        except Exception as e:
            logger.error(f"Error extracting text from Excel {file_path}: {e}")
            return ""

    def _extract_text_from_csv(self, file_path: str) -> str:
        """Extract text from CSV file"""
        try:
            df = pd.read_csv(file_path)
            return df.to_string(index=False)
        except Exception as e:
            logger.error(f"Error extracting text from CSV {file_path}: {e}")
            return ""

    def _extract_text_from_json(self, file_path: str) -> str:
        """Extract text from JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error extracting text from JSON {file_path}: {e}")
            return ""

    def _extract_text_from_file(self, file_path: str) -> str:
        """Extract text from various file formats"""
        file_extension = Path(file_path).suffix.lower()
        
        if file_extension == '.pdf':
            return self._extract_text_from_pdf(file_path)
        elif file_extension in ['.docx', '.doc']:
            return self._extract_text_from_docx(file_path)
        elif file_extension in ['.xlsx', '.xls']:
            return self._extract_text_from_excel(file_path)
        elif file_extension == '.csv':
            return self._extract_text_from_csv(file_path)
        elif file_extension == '.json':
            return self._extract_text_from_json(file_path)
        elif file_extension in ['.txt', '.md', '.html', '.xml', '.py', '.js', '.java', '.cpp', '.c']:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    return file.read()
            except:
                # Try with different encodings
                for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                    try:
                        with open(file_path, 'r', encoding=encoding) as file:
                            return file.read()
                    except:
                        continue
                logger.error(f"Could not read file {file_path} with any encoding")
                return ""
        else:
            logger.warning(f"Unsupported file type: {file_extension}")
            return ""

    async def add_file(self, file_path: str, metadata: Dict = None) -> Dict:
        """Add a file to the knowledge base - OPTIMIZED with fast chunking"""
        try:
            if not os.path.exists(file_path):
                return {"success": False, "error": "File not found"}
            
            file_extension = Path(file_path).suffix.lower()
            if file_extension not in self.supported_extensions:
                return {"success": False, "error": f"Unsupported file type: {file_extension}"}
            
            # Extract text
            logger.info(f"Processing file: {file_path}")
            text = self._extract_text_from_file(file_path)
            
            if not text.strip():
                return {"success": False, "error": "No text content found in file"}
            
            # Prepare metadata
            file_metadata = {
                "filename": Path(file_path).name,
                "filepath": file_path,
                "file_extension": file_extension,
                "file_size": os.path.getsize(file_path),
                "upload_timestamp": datetime.now().isoformat(),
                "text_length": len(text)
            }
            if metadata:
                file_metadata.update(metadata)
            
            # OPTIMIZATION: Use fast chunking for better performance
            chunks = self._chunk_text_fast(text, file_metadata)
            
            if not chunks:
                return {"success": False, "error": "No chunks generated from file"}
            
            # Generate embeddings using NVIDIA API
            chunk_texts = [chunk['text'] for chunk in chunks]
            logger.info(f"Generating embeddings for {len(chunk_texts)} chunks using NVIDIA model...")
            embeddings = await self.embedding_model.encode_async(chunk_texts, input_type="passage")
            embeddings = embeddings.tolist()
            
            # Prepare data for ChromaDB
            ids = [chunk['chunk_id'] for chunk in chunks]
            metadatas = [chunk['metadata'] for chunk in chunks]
            
            # Add to collection
            self.collection.add(
                embeddings=embeddings,
                documents=chunk_texts,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Successfully added {len(chunks)} chunks from {file_path}")
            
            return {
                "success": True,
                "filename": Path(file_path).name,
                "chunks_count": len(chunks),
                "total_characters": len(text),
                "file_metadata": file_metadata
            }
            
        except Exception as e:
            logger.error(f"Error adding file {file_path}: {e}")
            return {"success": False, "error": str(e)}

    async def add_text(self, text: str, metadata: Dict = None) -> Dict:
        """Add raw text to the knowledge base - OPTIMIZED"""
        try:
            if not text.strip():
                return {"success": False, "error": "Empty text provided"}
            
            # Prepare metadata
            text_metadata = {
                "content_type": "raw_text",
                "upload_timestamp": datetime.now().isoformat(),
                "text_length": len(text)
            }
            if metadata:
                text_metadata.update(metadata)
            
            # OPTIMIZATION: Use fast chunking
            chunks = self._chunk_text_fast(text, text_metadata)
            
            if not chunks:
                return {"success": False, "error": "No chunks generated from text"}
            
            # Generate embeddings using NVIDIA API
            chunk_texts = [chunk['text'] for chunk in chunks]
            logger.info(f"Generating embeddings for {len(chunk_texts)} chunks using NVIDIA model...")
            embeddings = await self.embedding_model.encode_async(chunk_texts, input_type="passage")
            embeddings = embeddings.tolist()
            
            # Prepare data for ChromaDB
            ids = [chunk['chunk_id'] for chunk in chunks]
            metadatas = [chunk['metadata'] for chunk in chunks]
            
            # Add to collection
            self.collection.add(
                embeddings=embeddings,
                documents=chunk_texts,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Successfully added {len(chunks)} chunks from raw text")
            
            return {
                "success": True,
                "chunks_count": len(chunks),
                "total_characters": len(text),
                "metadata": text_metadata
            }
            
        except Exception as e:
            logger.error(f"Error adding text: {e}")
            return {"success": False, "error": str(e)}

    async def search_cached(self, query: str, n_results: int = 5, filter_metadata: Dict = None) -> List[Dict]:
        """OPTIMIZED: Search with caching for repeated queries"""
        # Create cache key
        cache_key = f"{query}_{n_results}_{str(filter_metadata)}"
        current_time = time.time()
        
        with self.cache_lock:
            # Check cache
            if cache_key in self.search_cache:
                cached_result, timestamp = self.search_cache[cache_key]
                if current_time - timestamp < self.cache_duration:
                    logger.info(f"Using cached search result for: {query[:30]}...")
                    return cached_result
        
        # Perform actual search
        results = await self.search(query, n_results, filter_metadata)
        
        # Cache the result
        with self.cache_lock:
            self.search_cache[cache_key] = (results, current_time)
            
            # OPTIMIZATION: Clean old cache entries (keep cache size manageable)
            if len(self.search_cache) > 100:
                # Remove oldest entries
                sorted_items = sorted(self.search_cache.items(), key=lambda x: x[1][1])
                for old_key, _ in sorted_items[:20]:  # Remove 20 oldest
                    del self.search_cache[old_key]
        
        return results

    async def search(self, query: str, n_results: int = 5, filter_metadata: Dict = None) -> List[Dict]:
        """Search the knowledge base - OPTIMIZED"""
        try:
            # OPTIMIZATION: Reduce n_results for faster search when possible
            search_limit = min(n_results, 8)  # Cap at 8 for speed
            
            # Generate query embedding using NVIDIA API
            query_embedding = await self.embedding_model.encode_async([query], input_type="query")
            query_embedding = query_embedding[0].tolist()
            
            # Search in ChromaDB
            search_params = {
                "query_embeddings": [query_embedding],
                "n_results": search_limit
            }
            
            if filter_metadata:
                search_params["where"] = filter_metadata
            
            results = self.collection.query(**search_params)
            
            # Format results
            formatted_results = []
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None,
                    'id': results['ids'][0][i]
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return []

    async def get_context_for_query_fast(self, query: str, max_context_length: int = 2000) -> str:
        """ULTRA-OPTIMIZED: Get relevant context with aggressive length limits for speed"""
        try:
            # OPTIMIZATION: Use cached search and reduce result count
            results = await self.search_cached(query, n_results=3)  # Only top 3 results
            
            if not results:
                return ""
            
            # OPTIMIZATION: Build context more efficiently
            context_parts = []
            current_length = 0
            
            for result in results:
                text = result['text']
                metadata = result['metadata']
                
                # OPTIMIZATION: Shorter source info
                filename = metadata.get('filename', 'Unknown')
                source_info = f"[{filename}]"
                
                # OPTIMIZATION: Aggressive truncation for speed
                max_chunk_length = min(500, max_context_length // 3)  # Max 500 chars per chunk
                
                if len(text) > max_chunk_length:
                    text = text[:max_chunk_length] + "..."
                
                context_entry = f"{source_info} {text}"
                
                # Check length limit
                if current_length + len(context_entry) > max_context_length:
                    break
                
                context_parts.append(context_entry)
                current_length += len(context_entry)
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error getting fast context for query: {e}")
            return ""

    async def get_context_for_query(self, query: str, max_context_length: int = 4000) -> str:
        """Get relevant context for a query - ORIGINAL method preserved"""
        try:
            # Search for relevant documents
            results = await self.search(query, n_results=10)
            
            if not results:
                return ""
            
            # Build context from results
            context_parts = []
            current_length = 0
            
            for result in results:
                text = result['text']
                metadata = result['metadata']
                
                # Create a formatted context entry
                source_info = f"[Source: {metadata.get('filename', 'Unknown')}]"
                context_entry = f"{source_info}\n{text}\n"
                
                # Check if adding this would exceed limit
                if current_length + len(context_entry) > max_context_length:
                    # Try to fit partial content
                    remaining_space = max_context_length - current_length - len(source_info) - 10
                    if remaining_space > 100:  # Only add if we have reasonable space
                        truncated_text = text[:remaining_space] + "..."
                        context_entry = f"{source_info}\n{truncated_text}\n"
                        context_parts.append(context_entry)
                    break
                
                context_parts.append(context_entry)
                current_length += len(context_entry)
            
            return "\n---\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error getting context for query: {e}")
            return ""

    def get_stats(self) -> Dict:
        """Get knowledge base statistics - OPTIMIZED"""
        try:
            count_result = self.collection.count()
            
            # OPTIMIZATION: Get smaller sample for faster stats
            sample_results = self.collection.get(limit=50)  # Reduced from 100
            
            file_types = {}
            total_chars = 0
            filenames = set()
            
            if sample_results and 'metadatas' in sample_results:
                for metadata in sample_results['metadatas']:
                    if 'file_extension' in metadata:
                        ext = metadata['file_extension']
                        file_types[ext] = file_types.get(ext, 0) + 1
                    
                    if 'filename' in metadata:
                        filenames.add(metadata['filename'])
                    
                    if 'text_length' in metadata:
                        total_chars += metadata.get('text_length', 0)
            
            return {
                "total_chunks": count_result,
                "unique_files": len(filenames),
                "file_types": file_types,
                "estimated_total_characters": total_chars,
                "collection_name": self.collection_name,
                "persist_directory": self.persist_directory,
                "embedding_model": "nv-embedqa-mistral-7b-v2",
                "optimization": "fast_mode_enabled"
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"error": str(e)}

    def delete_file_chunks(self, filename: str) -> Dict:
        """Delete all chunks from a specific file"""
        try:
            # Get all chunks from the file
            results = self.collection.get(where={"filename": filename})
            
            if not results['ids']:
                return {"success": False, "error": "No chunks found for this file"}
            
            # Delete the chunks
            self.collection.delete(ids=results['ids'])
            
            # Clear relevant cache entries
            with self.cache_lock:
                keys_to_remove = [k for k in self.search_cache.keys() if filename.lower() in k.lower()]
                for key in keys_to_remove:
                    del self.search_cache[key]
            
            return {
                "success": True,
                "deleted_chunks": len(results['ids']),
                "filename": filename
            }
            
        except Exception as e:
            logger.error(f"Error deleting file chunks: {e}")
            return {"success": False, "error": str(e)}

    def clear_all(self) -> Dict:
        """Clear all data from the knowledge base"""
        try:
            # Delete the collection
            self.client.delete_collection(self.collection_name)
            
            # Recreate the collection
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Knowledge base collection with NVIDIA embeddings"}
            )
            
            # Clear cache
            with self.cache_lock:
                self.search_cache.clear()
            
            return {"success": True, "message": "Knowledge base cleared"}
            
        except Exception as e:
            logger.error(f"Error clearing knowledge base: {e}")
            return {"success": False, "error": str(e)}

# Global knowledge base instance
kb = None

def get_knowledge_base() -> KnowledgeBase:
    """Get or create global knowledge base instance"""
    global kb
    if kb is None:
        kb = KnowledgeBase()
    return kb

# OPTIMIZATION: Fast wrapper functions that use caching and smaller contexts
async def add_file_to_kb(file_path: str, metadata: Dict = None) -> Dict:
    """Add file to knowledge base"""
    kb = get_knowledge_base()
    return await kb.add_file(file_path, metadata)

async def add_text_to_kb(text: str, metadata: Dict = None) -> Dict:
    """Add text to knowledge base"""
    kb = get_knowledge_base()
    return await kb.add_text(text, metadata)

async def search_kb(query: str, n_results: int = 5) -> List[Dict]:
    """Search knowledge base with caching"""
    kb = get_knowledge_base()
    return await kb.search_cached(query, n_results)

async def get_kb_context(query: str, max_context_length: int = 4000) -> str:
    """Get context for query from knowledge base"""
    kb = get_knowledge_base()
    return await kb.get_context_for_query(query, max_context_length)

async def get_kb_context_fast(query: str, max_context_length: int = 2000) -> str:
    """ULTRA-FAST: Get context with aggressive optimizations"""
    kb = get_knowledge_base()
    return await kb.get_context_for_query_fast(query, max_context_length)

def get_kb_stats() -> Dict:
    """Get knowledge base statistics"""
    kb = get_knowledge_base()
    return kb.get_stats()

def delete_kb_file(filename: str) -> Dict:
    """Delete file from knowledge base"""
    kb = get_knowledge_base()
    return kb.delete_file_chunks(filename)

def clear_kb() -> Dict:
    """Clear all knowledge base data"""
    kb = get_knowledge_base()
    return kb.clear_all()

# OPTIMIZATION: Warmup function
async def warmup_kb():
    """Warm up the knowledge base for faster first queries"""
    try:
        kb = get_knowledge_base()
        # Perform a dummy search to warm up embeddings
        await kb.search_cached("test query", n_results=1)
        logger.info("Knowledge base warmed up successfully")
    except Exception as e:
        logger.warning(f"KB warmup failed (non-critical): {e}")