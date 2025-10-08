// app.jsx - FINAL FIXED VERSION with Working Avatars

import React, { useState, useEffect, useRef } from 'react';
import KnowledgeBase from './components/knowledge_base.jsx';
import VoicePrompt from './components/VoicePrompt.jsx';
import ChatHistory from './components/ChatHistory.jsx';
import AvatarFetcher from './components/AvatarFetcher.jsx';
import heygenService from './services/heygenService.js';

export default function HeyGenAvatarClient() {
  // WORKING AVATARS (verified public avatars that should work)
  const workingAvatars = [
    // Male avatars (verified working)
    { id: 'josh_lite3_20230714', name: 'Josh', voice_id: 'da04d9a268ac468887a68359908e55b7', gender: 'male', description: 'Professional executive consultant' },
    { id: 'Anthony_Chair_Sitting_public', name: 'Anthony', voice_id: '0009aabefe3a4553bc581d837b6268cb', gender: 'male', description: 'Corporate senior advisor' },
    { id: 'Pedro_Chair_Sitting_public', name: 'Pedro', voice_id: 'e17b99e1b86e47e8b7f4cae0f806aa78', gender: 'male', description: 'Technical solutions architect' },
    
    // Female avatars (verified working)
    { id: 'Alessandra_Chair_Sitting_public', name: 'Alessandra', voice_id: '1edc5e7338eb4e37b26dc8eb3f9b7e9c', gender: 'female', description: 'Executive business strategist' },
    { id: 'Amina_Chair_Sitting_public', name: 'Amina', voice_id: '1edc5e7338eb4e37b26dc8eb3f9b7e9c', gender: 'female', description: 'Client relations specialist' },
    { id: 'Anastasia_Chair_Sitting_public', name: 'Anastasia', voice_id: '1edc5e7338eb4e37b26dc8eb3f9b7e9c', gender: 'female', description: 'Operations and process expert' },
    { id: 'Marianne_Chair_Sitting_public', name: 'Marianne', voice_id: '1edc5e7338eb4e37b26dc8eb3f9b7e9c', gender: 'female', description: 'Senior advisor' },
    { id: 'Rika_Chair_Sitting_public', name: 'Rika', voice_id: '1edc5e7338eb4e37b26dc8eb3f9b7e9c', gender: 'female', description: 'Specialist' }
  ];

  const [avatarId, setAvatarId] = useState(workingAvatars[0].id);
  const [voiceId, setVoiceId] = useState(workingAvatars[0].voice_id);
  const [heygenConnected, setHeygenConnected] = useState(false);
  const [activeSessions, setActiveSessions] = useState(0);
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [lastResponse, setLastResponse] = useState(null);
  const [chatRefreshTrigger, setChatRefreshTrigger] = useState(0);
  const [isAvatarSpeaking, setIsAvatarSpeaking] = useState(false);
  const [sessionAge, setSessionAge] = useState(0);
  const [isVoiceMode, setIsVoiceMode] = useState(false);
  const [transcriptionBuffer, setTranscriptionBuffer] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [showAvatarFetcher, setShowAvatarFetcher] = useState(false);
  
  const videoRef = useRef(null);

  // Filter avatars by category
  const filteredAvatars = selectedCategory === 'all' 
    ? workingAvatars 
    : workingAvatars.filter(a => a.gender === selectedCategory);

  // Get selected avatar details
  const currentSelectedAvatar = workingAvatars.find(a => a.id === avatarId);

  // Listen to avatar state changes
  useEffect(() => {
    const unsubscribe = heygenService.onStateChange((event, data) => {
      if (event === 'avatar_speaking') {
        setIsAvatarSpeaking(data);
      }
    });
    return unsubscribe;
  }, []);

  // Safety timeout for stuck speaking state
  useEffect(() => {
    if (isAvatarSpeaking) {
      const timeout = setTimeout(() => {
        setIsAvatarSpeaking(false);
      }, 60000);
      return () => clearTimeout(timeout);
    }
  }, [isAvatarSpeaking]);

  // Track session age
  useEffect(() => {
    if (heygenConnected) {
      const interval = setInterval(() => {
        setSessionAge(prev => prev + 1);
      }, 1000);
      return () => clearInterval(interval);
    } else {
      setSessionAge(0);
    }
  }, [heygenConnected]);

  // Auto-refresh session at 9 minutes
  useEffect(() => {
    if (!sessionId || !heygenConnected) return;

    const refreshTimeout = setTimeout(async () => {
      console.log('Session approaching timeout, refreshing...');
      
      try {
        await closeHeyGenSession();
        await new Promise(resolve => setTimeout(resolve, 1000));
        await createHeyGenSession();
      } catch (error) {
        console.error('Failed to refresh session:', error);
        alert('Session refresh failed. Please restart manually.');
      }
    }, 9 * 60 * 1000);

    return () => clearTimeout(refreshTimeout);
  }, [sessionId, heygenConnected]);

  // Handle avatar selection change
  const handleAvatarChange = (e) => {
    if (heygenConnected) {
      alert('Please end the current session before changing avatars');
      return;
    }
    
    const selectedId = e.target.value;
    const selectedAvatar = workingAvatars.find(a => a.id === selectedId);
    
    console.log('Avatar changed to:', selectedAvatar?.name);
    console.log('Avatar ID:', selectedId);
    console.log('Voice ID:', selectedAvatar?.voice_id);
    
    setAvatarId(selectedId);
    setVoiceId(selectedAvatar?.voice_id || voiceId);
  };

  // Create session
  const createHeyGenSession = async () => {
    setLoading(true);
    try {
      const currentAvatar = workingAvatars.find(avatar => avatar.id === avatarId);
      const currentVoiceId = currentAvatar?.voice_id || voiceId;
      
      console.log('Creating session with:');
      console.log('Avatar ID:', avatarId);
      console.log('Voice ID:', currentVoiceId);
      console.log('Avatar Name:', currentAvatar?.name);
      
      const sessionData = await heygenService.createSessionWithBackend(avatarId, currentVoiceId);
      
      if (sessionData.success) {
        setSessionId(sessionData.sessionId);
        setHeygenConnected(true);
        await fetchActiveSessions();
        console.log('Session created with avatar:', avatarId);
      } else {
        throw new Error('Failed to create session');
      }
    } catch (error) {
      console.error('Error creating session:', error);
      alert('Error creating session: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  // Close session
  const closeHeyGenSession = async () => {
    try {
      await heygenService.closeSession();
      
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
      
      setSessionId(null);
      setHeygenConnected(false);
      setIsAvatarSpeaking(false);
      await fetchActiveSessions();
    } catch (error) {
      console.error('Error closing session:', error);
    }
  };

  // Fetch active sessions
  const fetchActiveSessions = async () => {
    try {
      const response = await fetch('http://localhost:8000/active-sessions');
      const data = await response.json();
      setActiveSessions(data.active_sessions || 0);
    } catch (error) {
      console.error('Error fetching active sessions:', error);
    }
  };

  // Send prompt
  const sendPrompt = async () => {
    if (!prompt.trim() || loading) return;

    setLoading(true);
    
    try {
      const result = await heygenService.sendPrompt(prompt);
      
      setLastResponse({
        query: prompt,
        response: result.response,
        used_knowledge_base: result.used_knowledge_base,
        context_length: result.context_length,
        timestamp: new Date().toLocaleTimeString(),
        interrupted: result.interrupted || false
      });
      
      setChatRefreshTrigger(prev => prev + 1);
      
      setPrompt('');
      setTranscriptionBuffer('');
      setIsVoiceMode(false);
      
    } catch (error) {
      console.error('Error sending prompt:', error);
      alert('Error: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  // Interrupt avatar
  const interruptAvatar = async () => {
    setLoading(false);
    
    try {
      await heygenService.interruptAvatar();
    } catch (error) {
      console.error('Error interrupting:', error);
    }
  };

  // Pass video ref
  useEffect(() => {
    if (videoRef.current) {
      heygenService.videoElement = videoRef.current;
    }
  }, []);

  // Handle Enter key
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !loading && prompt.trim()) {
      sendPrompt();
    }
  };

  // Global ESC key handler
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && (isAvatarSpeaking || loading)) {
        interruptAvatar();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isAvatarSpeaking, loading]);

  // Handle voice transcription
  const handleTranscriptionUpdate = async (text, isFinal = false) => {
    if (isFinal) {
      setPrompt(text);
      setTranscriptionBuffer('');
      setIsVoiceMode(false);
      setTimeout(() => sendPrompt(), 100);
    } else {
      setTranscriptionBuffer(text);
      setPrompt(text);
    }
  };

  // Show Avatar Fetcher if requested
  if (showAvatarFetcher) {
    return (
      <div>
        <button
          onClick={() => setShowAvatarFetcher(false)}
          style={{
            position: 'fixed',
            top: '1rem',
            left: '1rem',
            zIndex: 1000,
            padding: '0.5rem 1rem',
            backgroundColor: '#3182ce',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          ← Back to Main App
        </button>
        <AvatarFetcher />
      </div>
    );
  }

  return (
    <div style={{
      padding: '2rem',
      fontFamily: 'system-ui',
      maxWidth: '1400px',
      margin: '0 auto',
      backgroundColor: '#0f1419',
      color: '#e2e8f0',
      minHeight: '100vh'
    }}>
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <button
            onClick={() => setShowAvatarFetcher(true)}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#38a169',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.9rem',
              fontWeight: '500'
            }}
          >
            🎭 Avatar Fetcher Tool
          </button>
          <div></div>
        </div>
        <h1 style={{
          fontSize: '2.5rem',
          fontWeight: '700',
          background: 'linear-gradient(135deg, #4299e1 0%, #3182ce 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent'
        }}>
          AI Avatar Assistant 
        </h1>
        <p style={{ color: '#a0aec0', marginTop: '0.5rem' }}>
          Powered by HeyGen LiveKit
        </p>
      </div>

      {/* Avatar Selection */}
      <div style={{ marginBottom: '2rem' }}>
        {/* Category Filter */}
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
            Filter by Gender:
          </label>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {['all', 'male', 'female'].map(cat => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                disabled={heygenConnected}
                style={{
                  padding: '0.5rem 1rem',
                  backgroundColor: selectedCategory === cat ? '#3182ce' : '#2d3748',
                  color: '#e2e8f0',
                  border: selectedCategory === cat ? '2px solid #4299e1' : '1px solid #4a5568',
                  borderRadius: '8px',
                  cursor: heygenConnected ? 'not-allowed' : 'pointer',
                  fontWeight: selectedCategory === cat ? '600' : '400',
                  textTransform: 'capitalize',
                  opacity: heygenConnected ? 0.5 : 1
                }}
              >
                {cat} ({cat === 'all' ? workingAvatars.length : workingAvatars.filter(a => a.gender === cat).length})
              </button>
            ))}
          </div>
        </div>

        {/* Avatar Dropdown */}
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
            Select Avatar:
          </label>
          <select
            value={avatarId}
            onChange={handleAvatarChange}
            disabled={heygenConnected}
            style={{
              width: '100%',
              padding: '0.75rem',
              backgroundColor: '#2d3748',
              color: '#e2e8f0',
              border: '1px solid #4a5568',
              borderRadius: '8px',
              fontSize: '1rem',
              cursor: heygenConnected ? 'not-allowed' : 'pointer',
              opacity: heygenConnected ? 0.6 : 1
            }}
          >
            {filteredAvatars.map(avatar => (
              <option key={avatar.id} value={avatar.id}>
                {avatar.name} - {avatar.description}
              </option>
            ))}
          </select>
        </div>

        {/* Selected Avatar Info */}
        {currentSelectedAvatar && (
          <div style={{
            padding: '1rem',
            backgroundColor: '#1a202c',
            borderRadius: '8px',
            border: '1px solid #2d3748',
            marginBottom: '1rem'
          }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '0.9rem' }}>
              <div>
                <span style={{ color: '#a0aec0' }}>Avatar: </span>
                <span style={{ fontWeight: '500' }}>{currentSelectedAvatar.name}</span>
              </div>
              <div>
                <span style={{ color: '#a0aec0' }}>Gender: </span>
                <span style={{ fontWeight: '500', textTransform: 'capitalize' }}>{currentSelectedAvatar.gender}</span>
              </div>
              <div style={{ gridColumn: '1 / -1' }}>
                <span style={{ color: '#a0aec0' }}>Description: </span>
                <span style={{ fontWeight: '500' }}>{currentSelectedAvatar.description}</span>
              </div>
              <div style={{ gridColumn: '1 / -1', fontSize: '0.75rem' }}>
                <span style={{ color: '#718096' }}>Avatar ID: </span>
                <span style={{ fontFamily: 'monospace', color: '#4299e1' }}>{avatarId}</span>
              </div>
              <div style={{ gridColumn: '1 / -1', fontSize: '0.75rem' }}>
                <span style={{ color: '#718096' }}>Voice ID: </span>
                <span style={{ fontFamily: 'monospace', color: '#4299e1' }}>{voiceId}</span>
              </div>
            </div>
          </div>
        )}

        {/* Session Control */}
        {!heygenConnected ? (
          <button
            onClick={createHeyGenSession}
            disabled={loading}
            style={{
              padding: '0.75rem 2rem',
              backgroundColor: loading ? '#4a5568' : '#3182ce',
              color: '#fff',
              border: 'none',
              borderRadius: '8px',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: '1rem',
              fontWeight: '600',
              width: '100%'
            }}
          >
            {loading ? 'Connecting...' : `Start Session with ${currentSelectedAvatar?.name || 'Avatar'}`}
          </button>
        ) : (
          <button
            onClick={closeHeyGenSession}
            style={{
              padding: '0.75rem 2rem',
              backgroundColor: '#e53e3e',
              color: '#fff',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '1rem',
              fontWeight: '600',
              width: '100%'
            }}
          >
            End Session
          </button>
        )}

        {/* Video Container */}
        <div style={{
          width: '100%',
          maxWidth: '95vw',
          aspectRatio: '16/9',
          backgroundColor: '#1a202c',
          borderRadius: '12px',
          marginTop: '1rem',
          position: 'relative',
          overflow: 'hidden'
        }}>
          <video
            ref={videoRef}
            autoPlay
            playsInline
            style={{
              width: '100%',
              height: '100%',
              borderRadius: '12px',
              objectFit: 'cover',
              backgroundColor: '#1a202c'
            }}
          />
          
          {isAvatarSpeaking && (
            <div style={{
              position: 'absolute',
              top: '20px',
              right: '20px',
              padding: '0.5rem 1rem',
              backgroundColor: 'rgba(72, 187, 120, 0.9)',
              color: '#fff',
              borderRadius: '20px',
              fontSize: '0.85rem',
              fontWeight: '600',
              backdropFilter: 'blur(10px)'
            }}>
              Speaking...
            </div>
          )}

          {heygenConnected && currentSelectedAvatar && (
            <div style={{
              position: 'absolute',
              top: '20px',
              left: '20px',
              padding: '0.5rem 1rem',
              backgroundColor: 'rgba(49, 130, 206, 0.9)',
              color: '#fff',
              borderRadius: '20px',
              fontSize: '0.85rem',
              fontWeight: '600'
            }}>
              {currentSelectedAvatar.name}
            </div>
          )}
        </div>
      </div>

      {/* Chat Input */}
      <div style={{ marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.3rem', marginBottom: '1rem' }}>Chat</h2>
        
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder={isAvatarSpeaking ? "Avatar is speaking..." : "Enter your message..."}
            style={{
              flex: 1,
              padding: '1rem',
              borderRadius: '8px',
              border: '1px solid #4a5568',
              backgroundColor: '#2d3748',
              color: '#e2e8f0',
              fontSize: '1rem'
            }}
          />
          
          <button
            onClick={sendPrompt}
            disabled={!prompt.trim() || loading}
            style={{
              padding: '1rem 1.5rem',
              backgroundColor: (!prompt.trim() || loading) ? '#4a5568' : '#3182ce',
              color: '#fff',
              border: 'none',
              borderRadius: '8px',
              cursor: (prompt.trim() && !loading) ? 'pointer' : 'not-allowed',
              fontWeight: '600'
            }}
          >
            {loading ? 'Sending...' : 'Send'}
          </button>

          <button
            onClick={interruptAvatar}
            disabled={!isAvatarSpeaking && !loading}
            style={{
              padding: '1rem 1.5rem',
              backgroundColor: (isAvatarSpeaking || loading) ? '#2d3748' : '#1a202c',
              color: (isAvatarSpeaking || loading) ? '#f56565' : '#4a5568',
              border: `2px solid ${(isAvatarSpeaking || loading) ? '#f56565' : '#2d3748'}`,
              borderRadius: '8px',
              cursor: (isAvatarSpeaking || loading) ? 'pointer' : 'not-allowed',
              fontWeight: '600'
            }}
          >
            Stop
          </button>
        </div>
      </div>

      {/* Voice Input */}
      <VoicePrompt
        onTranscriptionUpdate={handleTranscriptionUpdate}
        isVoiceMode={isVoiceMode}
        setIsVoiceMode={setIsVoiceMode}
        transcriptionBuffer={transcriptionBuffer}
      />

      {/* Knowledge Base */}
      <KnowledgeBase />

      {/* Chat History */}
      <ChatHistory
        refreshTrigger={chatRefreshTrigger}
        onMessageClick={(message) => {
          if (message.type === 'user' && !isAvatarSpeaking) {
            setPrompt(message.content);
          }
        }}
      />
    </div>
  );
}