// services/heygenService.js - SIMPLIFIED WORKING VERSION

import StreamingAvatar, { AvatarQuality, StreamingEvents } from '@heygen/streaming-avatar';

const BACKEND_URL = 'http://localhost:8000';

class HeyGenService {
  constructor() {
    this.sessionId = null;
    this.avatar = null;
    this.isSDKInitialized = false;
    this.videoElement = null;
    
    this.isAvatarSpeaking = false;
    this.isSessionActive = false;
    this.keepAliveInterval = null;
    this.onStateChangeListeners = new Set();
    
    this.currentAvatarId = null;
    this.currentVoiceId = null;
  }

  // SIMPLIFIED: Let SDK create and manage everything
  async createSessionWithBackend(avatarId, voiceId) {
    console.log('='.repeat(60));
    console.log('🎭 CREATING SESSION WITH:');
    console.log('   Avatar ID:', avatarId);
    console.log('   Voice ID:', voiceId);
    console.log('='.repeat(60));
    
    this.currentAvatarId = avatarId;
    this.currentVoiceId = voiceId;
    
    // Close any existing session
    if (this.isSessionActive && this.sessionId) {
      console.log('🔄 Closing existing session first...');
      await this.closeSession();
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    try {
      // Step 1: Get streaming token
      console.log('📡 Step 1: Getting streaming token...');
      const tokenResponse = await fetch(`${BACKEND_URL}/heygen-token`);
      const tokenData = await tokenResponse.json();
      
      if (tokenData.status !== 'success') {
        throw new Error('Failed to get streaming token');
      }
      console.log('✅ Token received');

      // Step 2: Initialize SDK
      console.log('📡 Step 2: Initializing SDK...');
      await this.initializeSDK(tokenData.token);
      console.log('✅ SDK initialized');

      // Step 3: Create avatar directly with SDK (this is the correct way!)
      console.log('📡 Step 3: Creating avatar with SDK...');
      
      const sessionConfig = {
        avatarName: avatarId,  // CRITICAL: Use avatarName, NOT avatar_id
        quality: AvatarQuality.Medium,
        voice: {
          voiceId: voiceId  // CRITICAL: Use voiceId, NOT voice_id
        }
      };
      
      console.log('📤 Session config:', JSON.stringify(sessionConfig, null, 2));

      const result = await this.avatar.createStartAvatar(sessionConfig);
      
      console.log('📥 Avatar creation result:', result);
      
      this.sessionId = result.session_id;
      this.isSessionActive = true;
      
      // Register with backend for tracking
      console.log('📡 Step 4: Registering with backend...');
      try {
        await fetch(`${BACKEND_URL}/heygen/register-sdk-session`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: this.sessionId,
            avatar_id: avatarId,
            voice_id: voiceId,
            created_at: Date.now() / 1000
          })
        });
        console.log('✅ Registered with backend');
      } catch (error) {
        console.warn('⚠️ Backend registration failed (non-critical):', error);
      }

      console.log('='.repeat(60));
      console.log('✅ SESSION CREATED SUCCESSFULLY');
      console.log('   Session ID:', this.sessionId);
      console.log('   Avatar:', avatarId);
      console.log('   Voice:', voiceId);
      console.log('='.repeat(60));

      // Start keep-alive
      this.startKeepAlive();

      return {
        success: true,
        sessionId: this.sessionId,
        avatarId: avatarId,
        voiceId: voiceId
      };

    } catch (error) {
      console.error('='.repeat(60));
      console.error('❌ SESSION CREATION FAILED');
      console.error('   Error:', error.message);
      console.error('   Stack:', error.stack);
      console.error('='.repeat(60));
      throw error;
    }
  }

  // Initialize SDK
  async initializeSDK(accessToken) {
    console.log('🎭 Initializing HeyGen SDK...');
    
    // Clean up old avatar if exists
    if (this.avatar) {
      try {
        await this.avatar.stopAvatar();
      } catch (e) {
        console.log('⚠️ Error stopping old avatar:', e);
      }
    }
    
    this.avatar = new StreamingAvatar({ 
      token: accessToken
    });

    // Setup event listeners
    this.avatar.on(StreamingEvents.AVATAR_START_TALKING, (event) => {
      console.log('🗣️ Avatar started talking');
      this.isAvatarSpeaking = true;
      this.notifyStateChange('avatar_speaking', true);
    });

    this.avatar.on(StreamingEvents.AVATAR_STOP_TALKING, (event) => {
      console.log('🤐 Avatar stopped talking');
      this.isAvatarSpeaking = false;
      this.notifyStateChange('avatar_speaking', false);
    });

    this.avatar.on(StreamingEvents.STREAM_READY, (event) => {
      console.log('📺 Avatar stream ready');
      this.attachAvatarStream(event);
    });

    this.avatar.on(StreamingEvents.STREAM_DISCONNECTED, (event) => {
      console.log('💔 Avatar stream disconnected');
      this.handleSessionDisconnect();
    });

    this.isSDKInitialized = true;
    console.log('✅ SDK initialized and ready');
  }

  // Send prompt
  async sendPrompt(prompt) {
    if (!this.avatar || !this.isSDKInitialized) {
      throw new Error('SDK not initialized');
    }

    if (!this.isSessionActive) {
      throw new Error('Session is not active');
    }

    console.log('🧠 Processing prompt:', prompt.substring(0, 50));
    
    try {
      // Get LLM response from backend
      const llmResponse = await fetch(`${BACKEND_URL}/send-prompt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt })
      });

      const llmData = await llmResponse.json();
      
      console.log('🔍 LLM Response Data:', llmData);
      
      if (llmData.status !== 'success') {
        throw new Error(llmData.message || 'LLM response failed');
      }

      console.log('✅ LLM response received:', llmData.response?.substring(0, 100) + '...');
      
      // Send to avatar via SDK
      console.log('🎭 Sending to avatar...');
      console.log('📤 Avatar speak config:', {
        text: llmData.response?.substring(0, 100) + '...',
        task_type: 'talk',
        session_id: this.sessionId
      });
      
      await this.avatar.speak({
        text: llmData.response,
        task_type: 'talk',
        session_id: this.sessionId
      });
      
      console.log('✅ Text sent to avatar');
      
      return {
        success: true,
        response: llmData.response,
        heygen_sent: true,
        used_knowledge_base: llmData.used_knowledge_base,
        mode: llmData.mode
      };
      
    } catch (error) {
      console.error('❌ Error in sendPrompt:', error);
      throw error;
    }
  }

  // Interrupt avatar
  async interruptAvatar() {
    if (!this.avatar || !this.isSDKInitialized) {
      return false;
    }

    try {
      console.log('🛑 Interrupting...');
      
      if (typeof this.avatar.interrupt === 'function') {
        await this.avatar.interrupt();
        this.isAvatarSpeaking = false;
        this.notifyStateChange('avatar_speaking', false);
        return true;
      }
      
      return false;
      
    } catch (error) {
      console.error('❌ Error interrupting:', error);
      this.isAvatarSpeaking = false;
      this.notifyStateChange('avatar_speaking', false);
      return false;
    }
  }

  // Keep-alive
  startKeepAlive() {
    if (this.keepAliveInterval) {
      clearInterval(this.keepAliveInterval);
    }

    console.log('💓 Starting keep-alive...');
    
    this.keepAliveInterval = setInterval(async () => {
      if (!this.isSessionActive || !this.avatar || this.isAvatarSpeaking) {
        return;
      }

      try {
        await this.avatar.speak({
          text: ' ',
          task_type: 'talk',
          task_mode: 'async',
          session_id: this.sessionId
        }).catch(() => {});
      } catch (error) {
        // Ignore keep-alive errors
      }
    }, 30000);
  }

  stopKeepAlive() {
    if (this.keepAliveInterval) {
      clearInterval(this.keepAliveInterval);
      this.keepAliveInterval = null;
    }
  }

  // Close session
  async closeSession() {
    if (!this.sessionId) return { success: true };

    try {
      console.log('🛑 Closing session...');
      
      this.stopKeepAlive();
      
      if (this.avatar && this.isSDKInitialized) {
        await this.avatar.stopAvatar();
      }
      
      await fetch(`${BACKEND_URL}/heygen/unregister-sdk-session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: this.sessionId })
      });
      
      this.sessionId = null;
      this.isSessionActive = false;
      this.isAvatarSpeaking = false;
      this.currentAvatarId = null;
      this.currentVoiceId = null;
      
      if (this.videoElement) {
        this.videoElement.srcObject = null;
      }
      
      console.log('✅ Session closed');
      return { success: true };
      
    } catch (error) {
      console.error('❌ Error closing session:', error);
      throw error;
    }
  }

  // Attach stream to video
  attachAvatarStream(event) {
    const videoElement = this.videoElement;
    
    if (!videoElement) {
      console.warn('⚠️ No video element');
      return;
    }

    console.log('🎬 Attaching stream to video element');
    console.log('Event detail:', event?.detail);
    
    let stream = null;
    
    // Try multiple sources for the stream
    if (event?.detail?.stream) {
      stream = event.detail.stream;
      console.log('✅ Got stream from event.detail.stream');
    } else if (event?.detail?.mediaStream) {
      stream = event.detail.mediaStream;
      console.log('✅ Got stream from event.detail.mediaStream');
    } else if (event?.stream) {
      stream = event.stream;
      console.log('✅ Got stream from event.stream');
    } else if (this.avatar?.mediaStream) {
      stream = this.avatar.mediaStream;
      console.log('✅ Got stream from avatar.mediaStream');
    }
    
    if (stream) {
      console.log('📺 Setting video srcObject');
      console.log('Stream tracks:', stream.getTracks().map(t => `${t.kind}: ${t.label}`));
      
      videoElement.srcObject = stream;
      
      // Force play
      videoElement.play().catch(err => {
        console.log('⚠️ Autoplay blocked, enabling muted autoplay');
        videoElement.muted = true;
        return videoElement.play();
      }).then(() => {
        console.log('✅ Video is playing');
      }).catch(err => {
        console.error('❌ Failed to play video:', err);
      });
    } else {
      console.error('❌ No stream found in any source');
      
      // Try to get stream directly from avatar after a delay
      setTimeout(() => {
        if (this.avatar?.mediaStream && !videoElement.srcObject) {
          console.log('🔄 Retry: Attaching stream from avatar');
          videoElement.srcObject = this.avatar.mediaStream;
          videoElement.muted = true;
          videoElement.play();
        }
      }, 2000);
    }
  }

  // Handle disconnection
  handleSessionDisconnect() {
    console.log('💔 Session disconnected');
    this.isSessionActive = false;
    this.notifyStateChange('session_disconnected', true);
  }

  // State management
  isSpeaking() {
    return this.isAvatarSpeaking;
  }

  isSessionAlive() {
    return this.sessionId && 
           this.avatar && 
           this.isSDKInitialized && 
           this.isSessionActive;
  }

  getCurrentAvatar() {
    return {
      avatarId: this.currentAvatarId,
      voiceId: this.currentVoiceId
    };
  }

  notifyStateChange(event, data) {
    this.onStateChangeListeners.forEach(callback => {
      try {
        callback(event, data);
      } catch (error) {
        console.error('Error in listener:', error);
      }
    });
  }

  onStateChange(callback) {
    this.onStateChangeListeners.add(callback);
    return () => this.onStateChangeListeners.delete(callback);
  }

  getSessionStatus() {
    return {
      sessionId: this.sessionId,
      isActive: this.isSessionActive,
      isSpeaking: this.isAvatarSpeaking,
      hasAvatar: !!this.avatar,
      isSDKInitialized: this.isSDKInitialized,
      isAlive: this.isSessionAlive(),
      hasKeepAlive: !!this.keepAliveInterval,
      currentAvatar: this.currentAvatarId,
      currentVoice: this.currentVoiceId,
      // Debug info
      hasMediaStream: !!this.avatar?.mediaStream,
      videoElementHasSource: !!this.videoElement?.srcObject,
      videoElementExists: !!this.videoElement
    };
  }

  // Debug method to manually retry stream attachment
  async retryStreamAttachment() {
    console.log('🔄 Manual retry of stream attachment...');
    
    if (!this.videoElement) {
      console.error('❌ No video element available');
      return false;
    }
    
    if (!this.avatar) {
      console.error('❌ No avatar instance');
      return false;
    }
    
    console.log('Avatar mediaStream:', this.avatar.mediaStream);
    
    if (this.avatar.mediaStream) {
      this.videoElement.srcObject = this.avatar.mediaStream;
      this.videoElement.muted = true;
      
      try {
        await this.videoElement.play();
        console.log('✅ Stream attached and playing');
        return true;
      } catch (error) {
        console.error('❌ Failed to play:', error);
        return false;
      }
    } else {
      console.error('❌ Avatar has no mediaStream');
      return false;
    }
  }
}

// Export singleton and make available for debugging
const heygenServiceInstance = new HeyGenService();
if (typeof window !== 'undefined') {
  window.heygenService = heygenServiceInstance;
}

export default heygenServiceInstance;