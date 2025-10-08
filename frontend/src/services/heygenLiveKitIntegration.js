// HeyGen + LiveKit Integration - Latest 2024 Format
import StreamingAvatar, { StreamingEvents } from '@heygen/streaming-avatar';
import LiveKitService from './livekitService.js';

class HeyGenLiveKitIntegration {
  constructor() {
    this.avatar = null;
    this.sessionData = null;
    this.isSessionActive = false;
  }

  // Initialize HeyGen Streaming Avatar SDK
  async initializeAvatar(accessToken) {
    try {
      console.log('🎭 Initializing HeyGen Streaming Avatar...');
      
      this.avatar = new StreamingAvatar({ 
        token: accessToken,
        // Optional: specify server URL if using different region
        // serverUrl: 'https://api.heygen.com'
      });

      // Set up avatar event listeners
      this.setupAvatarEventListeners();

      console.log('✅ HeyGen Avatar initialized successfully');
      return true;
    } catch (error) {
      console.error('❌ Error initializing HeyGen Avatar:', error);
      throw error;
    }
  }

  // Setup avatar event listeners
  setupAvatarEventListeners() {
    if (!this.avatar) return;

    // Avatar ready event
    this.avatar.on(StreamingEvents.AVATAR_START_TALKING, (event) => {
      console.log('🗣️ Avatar started talking:', event);
    });

    this.avatar.on(StreamingEvents.AVATAR_STOP_TALKING, (event) => {
      console.log('🤐 Avatar stopped talking:', event);
    });

    this.avatar.on(StreamingEvents.STREAM_READY, (event) => {
      console.log('📺 Avatar stream ready:', event);
    });

    this.avatar.on(StreamingEvents.STREAM_DISCONNECTED, (event) => {
      console.log('💔 Avatar stream disconnected:', event);
    });
  }

  // Start avatar session with LiveKit integration - CORRECT 2024 FORMAT
  async startAvatarSession(config = {}) {
    try {
      console.log('🚀 Starting HeyGen avatar session with LiveKit...');

      // Default configuration with LiveKit settings
      const sessionConfig = {
        // Avatar configuration
        avatar_id: config.avatarId || 'default_avatar_id',
        quality: config.quality || 'medium', // 'low', 'medium', 'high'
        avatar_name: config.avatarName || 'HeyGen Avatar',
        
        // LiveKit integration settings - KEY PART FOR 2024!
        ...(config.livekitSettings && {
          livekit_url: config.livekitSettings.url,
          livekit_token: config.livekitSettings.token,
          // If using your own LiveKit instance
          use_custom_livekit: true
        }),
        
        // Voice settings (optional)
        voice: config.voice || {
          voice_id: 'default',
          rate: 1.0,
          emotion: 'friendly'
        },

        // Additional settings
        version: 'v2', // Ensure using v2 API
        knowledge_id: config.knowledgeId, // Optional knowledge base
        knowledge_base: config.knowledgeBase, // Optional knowledge base
        disable_idle_timeout: config.disableIdleTimeout || false
      };

      console.log('🔧 Session configuration:', {
        avatar_id: sessionConfig.avatar_id,
        quality: sessionConfig.quality,
        has_livekit_settings: !!config.livekitSettings,
        version: sessionConfig.version
      });

      // Create the session using the new format
      this.sessionData = await this.avatar.createStartAvatar(sessionConfig);
      
      console.log('✅ Avatar session created successfully!');
      console.log('📋 Session data:', {
        session_id: this.sessionData.session_id,
        livekit_url: this.sessionData.livekit_url,
        has_access_token: !!this.sessionData.access_token,
        expires_at: this.sessionData.expires_at
      });

      this.isSessionActive = true;
      return this.sessionData;

    } catch (error) {
      console.error('❌ Failed to start avatar session:', error);
      this.isSessionActive = false;
      throw error;
    }
  }

  // Connect to LiveKit room using your existing service
  async connectToLiveKitRoom(sessionData) {
    try {
      console.log('🔗 Connecting to LiveKit room using existing service...');

      // Setup track callback to handle avatar video/audio
      LiveKitService.setOnTrackCallback((trackEvent) => {
        console.log('📺 Received track from HeyGen avatar:', trackEvent.kind);
        this.handleAvatarTrack(trackEvent);
      });

      // Setup connection state callback
      LiveKitService.setOnConnectionStateChangeCallback((isConnected) => {
        console.log('🔗 LiveKit connection state changed:', isConnected);
      });

      // Setup participant callback
      LiveKitService.setOnParticipantCallback((event, participant) => {
        console.log('👥 Participant event:', event, participant.identity);
      });

      // Connect using your existing service
      await LiveKitService.connectToRoom(sessionData);
      
      console.log('✅ Successfully connected to LiveKit room!');
      return true;

    } catch (error) {
      console.error('❌ Failed to connect to LiveKit room:', error);
      throw error;
    }
  }

  // Handle avatar tracks (video/audio from HeyGen)
  handleAvatarTrack(trackEvent) {
    const { track, kind, participant } = trackEvent;

    console.log('🎬 Handling avatar track:', {
      kind: kind,
      participant: participant.identity,
      trackId: track.sid
    });

    if (kind === 'video') {
      // Attach video track to video element
      const videoElement = document.getElementById('avatar-video');
      if (videoElement) {
        track.attach(videoElement);
        console.log('📺 Avatar video attached to element');
      } else {
        console.warn('⚠️ No video element found with id "avatar-video"');
      }
    } else if (kind === 'audio') {
      // Audio is usually auto-played by LiveKit
      console.log('🔊 Avatar audio track received (auto-playing)');
    }
  }

  // Send text to avatar for speech - CORRECT 2024 METHOD
  async sendTextToAvatar(text, options = {}) {
    if (!this.avatar || !this.isSessionActive) {
      throw new Error('Avatar session not active');
    }

    try {
      console.log('💬 Sending text to avatar:', text);

      const speakConfig = {
        text: text,
        task_type: 'talk', // 'talk', 'repeat'
        task_mode: options.taskMode || 'sync', // 'sync' or 'async'
        session_id: this.sessionData?.session_id
      };

      const response = await this.avatar.speak(speakConfig);
      
      console.log('✅ Text sent successfully, task_id:', response.task_id);
      return response;

    } catch (error) {
      console.error('❌ Failed to send text to avatar:', error);
      throw error;
    }
  }

  // Interrupt avatar speech
  async interruptAvatar() {
    if (!this.avatar || !this.isSessionActive) {
      throw new Error('Avatar session not active');
    }

    try {
      await this.avatar.interrupt({
        session_id: this.sessionData?.session_id
      });
      console.log('🛑 Avatar speech interrupted');
    } catch (error) {
      console.error('❌ Failed to interrupt avatar:', error);
      throw error;
    }
  }

  // Start recording (if supported)
  async startRecording() {
    if (!this.avatar || !this.isSessionActive) {
      throw new Error('Avatar session not active');
    }

    try {
      const response = await this.avatar.startVoiceChat({
        session_id: this.sessionData?.session_id
      });
      console.log('🎙️ Voice chat started:', response);
      return response;
    } catch (error) {
      console.error('❌ Failed to start voice chat:', error);
      throw error;
    }
  }

  // Stop recording
  async stopRecording() {
    if (!this.avatar || !this.isSessionActive) {
      throw new Error('Avatar session not active');
    }

    try {
      const response = await this.avatar.closeVoiceChat({
        session_id: this.sessionData?.session_id
      });
      console.log('🛑 Voice chat stopped:', response);
      return response;
    } catch (error) {
      console.error('❌ Failed to stop voice chat:', error);
      throw error;
    }
  }

  // Get session status
  getSessionStatus() {
    return {
      isSessionActive: this.isSessionActive,
      sessionId: this.sessionData?.session_id || null,
      livekitConnected: LiveKitService.getConnectionStatus().isConnected,
      participantCount: LiveKitService.getConnectionStatus().participantCount
    };
  }

  // Close avatar session and disconnect
  async disconnect() {
    try {
      console.log('🔌 Disconnecting HeyGen avatar and LiveKit...');

      // Stop avatar session
      if (this.avatar && this.isSessionActive && this.sessionData?.session_id) {
        await this.avatar.stopAvatar({
          session_id: this.sessionData.session_id
        });
        console.log('🛑 Avatar session stopped');
      }

      // Disconnect from LiveKit
      await LiveKitService.disconnect();

      // Reset state
      this.isSessionActive = false;
      this.sessionData = null;
      this.avatar = null;

      console.log('✅ Successfully disconnected from HeyGen and LiveKit');

    } catch (error) {
      console.error('❌ Error during disconnection:', error);
      throw error;
    }
  }
}

// Usage example with your LiveKit service
async function initializeHeyGenWithLiveKit() {
  const integration = new HeyGenLiveKitIntegration();

  try {
    // 1. Get access token (from your backend)
    const accessToken = await fetch('/api/get-access-token').then(r => r.text());

    // 2. Initialize HeyGen avatar
    await integration.initializeAvatar(accessToken);

    // 3. Start avatar session
    const sessionData = await integration.startAvatarSession({
      avatarId: 'your_avatar_id', // Replace with your avatar ID
      quality: 'medium',
      voice: {
        voice_id: 'default',
        rate: 1.0,
        emotion: 'friendly'
      }
    });

    // 4. Connect to LiveKit room using your service
    await integration.connectToLiveKitRoom(sessionData);

    // 5. Send initial greeting
    await integration.sendTextToAvatar('Hello! I am now connected to the LiveKit room and ready to talk.');

    console.log('🎉 HeyGen + LiveKit integration completed successfully!');
    
    return integration;

  } catch (error) {
    console.error('💥 Integration failed:', error);
    await integration.disconnect();
    throw error;
  }
}

// Export for use
export { HeyGenLiveKitIntegration, initializeHeyGenWithLiveKit };

// React Hook version for React applications
import { useState, useEffect, useCallback } from 'react';

export function useHeyGenLiveKit() {
  const [integration, setIntegration] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [status, setStatus] = useState('disconnected');
  const [error, setError] = useState(null);

  const connect = useCallback(async (config) => {
    try {
      setStatus('connecting');
      setError(null);

      const newIntegration = await initializeHeyGenWithLiveKit();
      setIntegration(newIntegration);
      setIsConnected(true);
      setStatus('connected');

      return newIntegration;
    } catch (err) {
      setError(err.message);
      setStatus('error');
      setIsConnected(false);
      throw err;
    }
  }, []);

  const disconnect = useCallback(async () => {
    if (integration) {
      try {
        await integration.disconnect();
        setIntegration(null);
        setIsConnected(false);
        setStatus('disconnected');
      } catch (err) {
        setError(err.message);
        setStatus('error');
      }
    }
  }, [integration]);

  const sendMessage = useCallback(async (text) => {
    if (integration && isConnected) {
      return await integration.sendTextToAvatar(text);
    }
    throw new Error('Not connected to HeyGen avatar');
  }, [integration, isConnected]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (integration) {
        integration.disconnect().catch(console.error);
      }
    };
  }, [integration]);

  return {
    connect,
    disconnect,
    sendMessage,
    isConnected,
    status,
    error,
    integration
  };
}
