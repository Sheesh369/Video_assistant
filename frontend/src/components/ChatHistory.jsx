// ChatHistory.jsx
import React, { useState, useEffect, useRef } from 'react';

const ChatHistory = ({ 
  isVisible = true, 
  maxHeight = "400px",
  onMessageClick = null,
  refreshTrigger = 0 // Add this to trigger refreshes from parent
}) => {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({});
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [showStats, setShowStats] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [exportFormat, setExportFormat] = useState('json');
  
  const messagesEndRef = useRef(null);
  const chatContainerRef = useRef(null);

  // API helper functions
  const apiCall = async (endpoint, options = {}) => {
    try {
      const response = await fetch(`http://localhost:8000${endpoint}`, {
        headers: { 'Content-Type': 'application/json' },
        ...options
      });
      return await response.json();
    } catch (error) {
      console.error(`API call failed for ${endpoint}:`, error);
      throw error;
    }
  };

  // Load chat history
  const loadChatHistory = async () => {
    setLoading(true);
    try {
      const response = await apiCall('/chat/history');
      if (response.success) {
        setMessages(response.messages || []);
        setStats(response.stats || {});
        console.log(`📜 Loaded ${response.messages?.length || 0} chat messages`);
      }
    } catch (error) {
      console.error('❌ Error loading chat history:', error);
    } finally {
      setLoading(false);
    }
  };

  // Search chat history
  const searchChat = async () => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }

    setIsSearching(true);
    try {
      const response = await apiCall(`/chat/search?query=${encodeURIComponent(searchQuery)}&limit=20`);
      if (response.success) {
        setSearchResults(response.results || []);
        console.log(`🔍 Found ${response.results?.length || 0} matching messages`);
      }
    } catch (error) {
      console.error('❌ Error searching chat:', error);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  // Export chat history
  const exportChat = async () => {
    try {
      const response = await apiCall(`/chat/export?format=${exportFormat}`);
      if (response.success) {
        const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
        
        if (exportFormat === 'json') {
          const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' });
          downloadFile(blob, `chat-history-${timestamp}.json`);
        } else if (exportFormat === 'txt') {
          const blob = new Blob([response.data], { type: 'text/plain' });
          downloadFile(blob, `chat-transcript-${timestamp}.txt`);
        }
        
        console.log(`📥 Exported chat history as ${exportFormat}`);
      }
    } catch (error) {
      console.error('❌ Error exporting chat:', error);
      alert('Error exporting chat history');
    }
  };

  // Clear chat history
  const clearChat = async () => {
    if (!window.confirm('Are you sure you want to clear all chat history? This cannot be undone.')) {
      return;
    }

    try {
      const response = await apiCall('/chat/clear', { method: 'DELETE' });
      if (response.success) {
        setMessages([]);
        setSearchResults([]);
        setStats({});
        console.log('🗑️ Chat history cleared');
      }
    } catch (error) {
      console.error('❌ Error clearing chat:', error);
      alert('Error clearing chat history');
    }
  };

  // Delete specific message
  const deleteMessage = async (messageId) => {
    if (!window.confirm('Delete this message?')) return;

    try {
      const response = await apiCall(`/chat/message/${messageId}`, { method: 'DELETE' });
      if (response.success) {
        await loadChatHistory(); // Refresh
        console.log(`🗑️ Deleted message ${messageId}`);
      }
    } catch (error) {
      console.error('❌ Error deleting message:', error);
    }
  };

  // Download helper
  const downloadFile = (blob, filename) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Format timestamp
  const formatTimestamp = (timestamp) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('en-US', { 
        hour12: false, 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit'
      });
    } catch {
      return timestamp;
    }
  };

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    if (autoScroll && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  // Handle scroll to detect manual scrolling
  const handleScroll = () => {
    if (!chatContainerRef.current) return;
    
    const { scrollTop, scrollHeight, clientHeight } = chatContainerRef.current;
    const isAtBottom = scrollTop + clientHeight >= scrollHeight - 10;
    setAutoScroll(isAtBottom);
  };

  // Load data on mount and refresh trigger
  useEffect(() => {
    loadChatHistory();
  }, [refreshTrigger]);

  // Auto-scroll when new messages arrive
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Search when query changes
  useEffect(() => {
    if (showSearch) {
      const debounceTimer = setTimeout(searchChat, 300);
      return () => clearTimeout(debounceTimer);
    }
  }, [searchQuery, showSearch]);

  if (!isVisible) return null;

  const displayMessages = showSearch && searchQuery ? searchResults : messages;

  return (
    <div style={{
      backgroundColor: '#1a1a1a',
      border: '1px solid #333',
      borderRadius: '12px',
      overflow: 'hidden',
      marginBottom: '1rem'
    }}>
      {/* Header */}
      <div style={{
        padding: '1rem',
        backgroundColor: '#2a2a2a',
        borderBottom: '1px solid #333',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '0.5rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '1.1rem', fontWeight: 'bold', color: '#fff' }}>
            💬 Chat History
          </span>
          {stats.total_messages > 0 && (
            <span style={{
              backgroundColor: '#007bff',
              color: '#fff',
              padding: '0.25rem 0.5rem',
              borderRadius: '12px',
              fontSize: '0.8rem'
            }}>
              {stats.total_messages} messages
            </span>
          )}
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button
            onClick={() => setShowSearch(!showSearch)}
            style={{
              padding: '0.5rem 0.75rem',
              backgroundColor: showSearch ? '#28a745' : '#6c757d',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.8rem'
            }}
          >
            🔍 Search
          </button>
          
          <button
            onClick={() => setShowStats(!showStats)}
            style={{
              padding: '0.5rem 0.75rem',
              backgroundColor: showStats ? '#17a2b8' : '#6c757d',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.8rem'
            }}
          >
            📊 Stats
          </button>

          <button
            onClick={loadChatHistory}
            disabled={loading}
            style={{
              padding: '0.5rem 0.75rem',
              backgroundColor: loading ? '#666' : '#6c757d',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: '0.8rem'
            }}
          >
            {loading ? '⏳' : '🔄'}
          </button>
        </div>
      </div>

      {/* Search Section */}
      {showSearch && (
        <div style={{
          padding: '1rem',
          backgroundColor: '#252525',
          borderBottom: '1px solid #333'
        }}>
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search conversation..."
              style={{
                flex: 1,
                padding: '0.5rem',
                backgroundColor: '#333',
                color: '#fff',
                border: '1px solid #555',
                borderRadius: '6px',
                fontSize: '0.9rem'
              }}
            />
            <button
              onClick={() => setSearchQuery('')}
              style={{
                padding: '0.5rem 0.75rem',
                backgroundColor: '#dc3545',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '0.8rem'
              }}
            >
              ✕
            </button>
          </div>
          
          {searchQuery && (
            <div style={{ fontSize: '0.8rem', color: '#888' }}>
              {isSearching ? 'Searching...' : `Found ${searchResults.length} results`}
            </div>
          )}
        </div>
      )}

      {/* Stats Section */}
      {showStats && stats.total_messages > 0 && (
        <div style={{
          padding: '1rem',
          backgroundColor: '#252525',
          borderBottom: '1px solid #333'
        }}>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
            gap: '0.5rem',
            fontSize: '0.8rem'
          }}>
            <div style={{ color: '#4a9eff' }}>
              👤 User: {stats.user_messages || 0}
            </div>
            <div style={{ color: '#28a745' }}>
              🤖 Avatar: {stats.avatar_messages || 0}
            </div>
            <div style={{ color: '#ffc107' }}>
              🎤 Voice: {stats.voice_messages || 0}
            </div>
            <div style={{ color: '#17a2b8' }}>
              🧠 KB Used: {stats.kb_enhanced_responses || 0}
            </div>
          </div>

          {/* Export Controls */}
          <div style={{
            marginTop: '0.75rem',
            display: 'flex',
            gap: '0.5rem',
            alignItems: 'center',
            flexWrap: 'wrap'
          }}>
            <select
              value={exportFormat}
              onChange={(e) => setExportFormat(e.target.value)}
              style={{
                padding: '0.25rem 0.5rem',
                backgroundColor: '#333',
                color: '#fff',
                border: '1px solid #555',
                borderRadius: '4px',
                fontSize: '0.8rem'
              }}
            >
              <option value="json">JSON</option>
              <option value="txt">Text</option>
            </select>
            
            <button
              onClick={exportChat}
              style={{
                padding: '0.25rem 0.75rem',
                backgroundColor: '#28a745',
                color: '#fff',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.8rem'
              }}
            >
              📥 Export
            </button>
            
            <button
              onClick={clearChat}
              style={{
                padding: '0.25rem 0.75rem',
                backgroundColor: '#dc3545',
                color: '#fff',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.8rem'
              }}
            >
              🗑️ Clear All
            </button>
          </div>
        </div>
      )}

      {/* Messages Container */}
      <div
        ref={chatContainerRef}
        onScroll={handleScroll}
        style={{
          maxHeight: maxHeight,
          overflowY: 'auto',
          padding: '1rem',
          backgroundColor: '#1a1a1a'
        }}
      >
        {loading ? (
          <div style={{
            textAlign: 'center',
            color: '#888',
            padding: '2rem'
          }}>
            <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>⏳</div>
            Loading chat history...
          </div>
        ) : displayMessages.length === 0 ? (
          <div style={{
            textAlign: 'center',
            color: '#888',
            padding: '2rem'
          }}>
            <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>💬</div>
            {showSearch && searchQuery ? 'No messages found' : 'No conversation yet'}
            <br />
            <span style={{ fontSize: '0.9rem' }}>
              {showSearch && searchQuery ? 'Try a different search term' : 'Start chatting with your avatar!'}
            </span>
          </div>
        ) : (
          <>
            {displayMessages.map((message, index) => (
              <ChatMessage
                key={message.id}
                message={message}
                onDelete={deleteMessage}
                onClick={onMessageClick}
                isSearchResult={showSearch && searchQuery}
                searchQuery={searchQuery}
              />
            ))}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Auto-scroll indicator */}
      {!autoScroll && (
        <div style={{
          position: 'absolute',
          bottom: '20px',
          right: '20px',
          backgroundColor: '#007bff',
          color: '#fff',
          padding: '0.5rem 1rem',
          borderRadius: '20px',
          cursor: 'pointer',
          fontSize: '0.8rem',
          boxShadow: '0 2px 8px rgba(0,0,0,0.3)'
        }}
        onClick={scrollToBottom}>
          ↓ New messages
        </div>
      )}
    </div>
  );
};

// Individual message component
const ChatMessage = ({ message, onDelete, onClick, isSearchResult, searchQuery }) => {
  const [showMetadata, setShowMetadata] = useState(false);
  
  const isUser = message.type === 'user';
  const timestamp = formatTimestamp(message.timestamp);
  
  // Highlight search terms
  const highlightText = (text, query) => {
    if (!query || !isSearchResult) return text;
    
    const regex = new RegExp(`(${query})`, 'gi');
    const parts = text.split(regex);
    
    return parts.map((part, index) => 
      regex.test(part) ? (
        <span key={index} style={{ backgroundColor: '#ffc107', color: '#000', padding: '0 2px' }}>
          {part}
        </span>
      ) : part
    );
  };

  return (
    <div
      onClick={() => onClick && onClick(message)}
      style={{
        marginBottom: '1rem',
        cursor: onClick ? 'pointer' : 'default'
      }}
    >
      <div style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        marginBottom: '0.25rem'
      }}>
        <div style={{
          maxWidth: '85%',
          padding: '0.75rem 1rem',
          borderRadius: '12px',
          backgroundColor: isUser ? '#007bff' : '#333',
          color: '#fff',
          position: 'relative'
        }}>
          {/* Message Header */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '0.5rem',
            fontSize: '0.8rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontWeight: 'bold' }}>
                {isUser ? '👤 You' : '🤖 Avatar'}
              </span>
              
              {/* Metadata indicators */}
              {isUser && message.metadata?.voice_used && (
                <span style={{ color: '#28a745' }} title="Voice input">🎤</span>
              )}
              {!isUser && message.metadata?.used_knowledge_base && (
                <span style={{ color: '#ffc107' }} title="Used knowledge base">🧠</span>
              )}
              {!isUser && message.metadata?.heygen_sent && (
                <span style={{ color: '#17a2b8' }} title="Sent to HeyGen">🎭</span>
              )}
            </div>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ color: '#ccc' }}>{timestamp}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowMetadata(!showMetadata);
                }}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#ccc',
                  cursor: 'pointer',
                  fontSize: '0.8rem'
                }}
                title="Show details"
              >
                ⓘ
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(message.id);
                }}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#dc3545',
                  cursor: 'pointer',
                  fontSize: '0.8rem'
                }}
                title="Delete message"
              >
                ✕
              </button>
            </div>
          </div>

          {/* Message Content */}
          <div style={{ 
            fontSize: '0.95rem',
            lineHeight: '1.4',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word'
          }}>
            {highlightText(message.content, searchQuery)}
          </div>

          {/* Metadata Details */}
          {showMetadata && message.metadata && (
            <div style={{
              marginTop: '0.75rem',
              padding: '0.5rem',
              backgroundColor: 'rgba(0,0,0,0.3)',
              borderRadius: '6px',
              fontSize: '0.75rem',
              color: '#ccc'
            }}>
              <div style={{ fontWeight: 'bold', marginBottom: '0.25rem' }}>Message Details:</div>
              
              {/* User message metadata */}
              {isUser && (
                <>
                  <div>Input: {message.metadata.voice_used ? '🎤 Voice' : '⌨️ Keyboard'}</div>
                  {message.metadata.audio_length && (
                    <div>Audio: {Math.round(message.metadata.audio_length / 1024)}KB</div>
                  )}
                </>
              )}
              
              {/* Avatar message metadata */}
              {!isUser && (
                <>
                  {message.metadata.response_time && (
                    <div>Response time: {message.metadata.response_time}ms</div>
                  )}
                  {message.metadata.used_knowledge_base && (
                    <div>KB context: {message.metadata.context_length} chars</div>
                  )}
                  {message.metadata.heygen_sessions_sent && (
                    <div>HeyGen sessions: {message.metadata.heygen_sessions_sent}</div>
                  )}
                </>
              )}
              
              <div style={{ marginTop: '0.25rem', fontSize: '0.7rem', color: '#888' }}>
                ID: {message.id}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Helper function for timestamp formatting
const formatTimestamp = (timestamp) => {
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit',
      second: '2-digit'
    });
  } catch {
    return timestamp;
  }
};

export default ChatHistory;