// services/livekitService.js - LiveKit integration for HeyGen
import { 
  Room, 
  RoomEvent, 
  Track, 
  RemoteTrack,
  RemoteVideoTrack,
  RemoteAudioTrack,
  ConnectionState,
  ParticipantEvent,
  TrackPublication 
} from 'livekit-client';

class LiveKitService {
  constructor() {
    this.room = null;
    this.isConnected = false;
    this.onTrackCallback = null;
    this.onConnectionStateChangeCallback = null;
    this.onParticipantCallback = null;
    this.sessionId = null;
  }

  // Connect to LiveKit room using HeyGen session data
  async connectToRoom(sessionData) {
    try {
      console.log('🎭 Connecting to LiveKit room with HeyGen session...');
      console.log('🔍 Session data:', {
        session_id: sessionData.session_id,
        livekit_url: sessionData.livekit_url,
        has_token: !!sessionData.access_token
      });

      if (!sessionData.livekit_url || !sessionData.access_token) {
        throw new Error('Missing LiveKit connection data from HeyGen');
      }

      this.sessionId = sessionData.session_id;

      // Create new room instance with minimal configuration to avoid validation errors
      this.room = new Room({
        // Basic configuration only
        adaptiveStream: true,
        dynacast: true
      });

      // Set up event listeners
      this.setupRoomEventListeners();

      // Connect to the room
      await this.room.connect(sessionData.livekit_url, sessionData.access_token);

      console.log('✅ Successfully connected to LiveKit room');
      console.log('🎬 Room name:', this.room?.name || 'Unknown');
      console.log('👥 Participants:', this.room?.participants?.size || 0);

      this.isConnected = true;

      // Notify connection state change
      if (this.onConnectionStateChangeCallback) {
        this.onConnectionStateChangeCallback(true);
      }

      // Check for participants after a longer delay (HeyGen avatar might need time to process text and join)
      setTimeout(() => {
        const participantCount = this.room?.participants?.size || 0;
        console.log('🔍 Delayed participant check - Count:', participantCount);
        
        if (participantCount > 0) {
          console.log('🎭 HeyGen avatar detected in room!');
          this.room.participants.forEach((participant, identity) => {
            console.log('👤 Participant:', identity, 'isLocal:', participant.isLocal);
            console.log('🏷️ Attributes:', participant.attributes);
            console.log('🎭 Kind:', participant.kind);
          });
        } else {
          console.log('⏳ No participants yet - HeyGen avatar may still be processing text and joining...');
        }
      }, 8000); // Check after 8 seconds to give avatar time to process text

      // Set up continuous participant monitoring
      this.startParticipantMonitoring();

      return true;

    } catch (error) {
      console.error('❌ Failed to connect to LiveKit room:', error);
      this.isConnected = false;
      
      if (this.onConnectionStateChangeCallback) {
        this.onConnectionStateChangeCallback(false);
      }
      
      throw error;
    }
  }

  // Set up room event listeners
  setupRoomEventListeners() {
    if (!this.room) return;

    // Handle connection state changes
    this.room.on(RoomEvent.ConnectionStateChanged, (state) => {
      console.log('🔗 LiveKit connection state changed:', state);
      
      const isConnected = state === ConnectionState.Connected;
      this.isConnected = isConnected;
      
      if (this.onConnectionStateChangeCallback) {
        this.onConnectionStateChangeCallback(isConnected);
      }
    });

    // Handle participant connections
    this.room.on(RoomEvent.ParticipantConnected, (participant) => {
      console.log('👋 Participant connected:', participant.identity);
      console.log('🎭 Participant details:', {
        identity: participant.identity,
        isLocal: participant.isLocal,
        trackCount: participant.trackPublications?.size || 0,
        connectionQuality: participant.connectionQuality,
        attributes: participant.attributes,
        kind: participant.kind
      });
      
      // Check if this is an avatar worker (HeyGen avatar)
      const isAvatarWorker = participant.attributes && 
        (participant.attributes['lk.publish_on_behalf'] !== undefined ||
         participant.identity.includes('avatar') ||
         participant.identity.includes('heygen'));
      
      if (isAvatarWorker) {
        console.log('🎭 HeyGen Avatar Worker detected!', {
          identity: participant.identity,
          attributes: participant.attributes,
          publishOnBehalf: participant.attributes['lk.publish_on_behalf']
        });
      }
      
      if (this.onParticipantCallback) {
        this.onParticipantCallback('connected', participant);
      }

      // Subscribe to participant's tracks
      participant.trackPublications.forEach((publication) => {
        console.log('📺 Existing track publication:', publication.kind, 'subscribed:', publication.isSubscribed);
        if (publication.isSubscribed && publication.track) {
          this.handleTrack(publication.track, participant);
        }
      });

      // Listen for new track publications
      participant.on(ParticipantEvent.TrackSubscribed, (track, publication) => {
        console.log('📺 Track subscribed:', track.kind, 'from', participant.identity);
        this.handleTrack(track, participant);
      });
    });

    // Handle participant disconnections
    this.room.on(RoomEvent.ParticipantDisconnected, (participant) => {
      console.log('👋 Participant disconnected:', participant.identity);
      
      if (this.onParticipantCallback) {
        this.onParticipantCallback('disconnected', participant);
      }
    });

    // Handle track publications
    this.room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
      console.log('📺 New track subscribed:', track.kind, 'from', participant.identity);
      this.handleTrack(track, participant);
    });

    // Handle track unpublications
    this.room.on(RoomEvent.TrackUnsubscribed, (track, publication, participant) => {
      console.log('📺 Track unsubscribed:', track.kind, 'from', participant.identity);
    });

    // Handle disconnection
    this.room.on(RoomEvent.Disconnected, (reason) => {
      console.log('💔 Disconnected from LiveKit room:', reason);
      this.isConnected = false;
      
      if (this.onConnectionStateChangeCallback) {
        this.onConnectionStateChangeCallback(false);
      }
    });

    // Handle errors
    this.room.on(RoomEvent.ConnectionError, (error) => {
      console.error('❌ LiveKit connection error:', error);
      this.isConnected = false;
      
      if (this.onConnectionStateChangeCallback) {
        this.onConnectionStateChangeCallback(false);
      }
    });
  }

  // Handle incoming tracks (video/audio from HeyGen avatar)
  handleTrack(track, participant) {
    console.log('🎬 Handling track:', track.kind, 'from', participant.identity);
    console.log('🎭 Track details:', {
      kind: track.kind,
      id: track.sid,
      enabled: track.isEnabled,
      participant: participant.identity,
      isLocal: participant.isLocal
    });

    if (this.onTrackCallback) {
      // Create a compatible event object similar to WebRTC ontrack event
      const trackEvent = {
        track: track,
        streams: [track.mediaStream],
        participant: participant,
        kind: track.kind
      };
      
      console.log('📤 Calling onTrackCallback with track event');
      this.onTrackCallback(trackEvent);
    } else {
      console.log('⚠️ No onTrackCallback set - track will not be displayed');
    }

    // Auto-attach video tracks to elements
    if (track instanceof RemoteVideoTrack) {
      console.log('📺 Remote video track received - should display avatar');
      // The track will be attached via the callback
    } else if (track instanceof RemoteAudioTrack) {
      console.log('🔊 Remote audio track received - should play audio');
      // Audio tracks are usually auto-played
    }
  }

  // Start continuous participant monitoring
  startParticipantMonitoring() {
    if (!this.room) return;
    
    console.log('👀 Starting continuous participant monitoring...');
    
           // Check every 5 seconds for new participants (less frequent but longer monitoring)
           this.participantMonitorInterval = setInterval(() => {
             if (!this.room || !this.isConnected) {
               this.stopParticipantMonitoring();
               return;
             }
             
             const participantCount = this.room.participants?.size || 0;
             console.log('🔍 Participant monitor check - Count:', participantCount);
             
             if (participantCount > 0) {
               console.log('🎭 Participants detected!');
               this.room.participants.forEach((participant, identity) => {
                 console.log('👤 Participant:', identity, 'isLocal:', participant.isLocal);
                 console.log('📺 Track count:', participant.trackPublications?.size || 0);
                 console.log('🏷️ Attributes:', participant.attributes);
                 console.log('🎭 Kind:', participant.kind);
                 
                 // Check if this is an avatar worker
                 const isAvatarWorker = participant.attributes && 
                   (participant.attributes['lk.publish_on_behalf'] !== undefined ||
                    identity.includes('avatar') ||
                    identity.includes('heygen'));
                 
                 if (isAvatarWorker) {
                   console.log('🎭 HeyGen Avatar Worker found in monitoring!', {
                     identity: identity,
                     attributes: participant.attributes,
                     publishOnBehalf: participant.attributes['lk.publish_on_behalf']
                   });
                 }
               });
               
               // Stop monitoring once we have participants
               this.stopParticipantMonitoring();
             }
           }, 5000);
    
    // Stop monitoring after 120 seconds (extended for simple approach)
    setTimeout(() => {
      this.stopParticipantMonitoring();
    }, 120000);
  }
  
  // Stop participant monitoring
  stopParticipantMonitoring() {
    if (this.participantMonitorInterval) {
      clearInterval(this.participantMonitorInterval);
      this.participantMonitorInterval = null;
      console.log('🛑 Stopped participant monitoring');
    }
  }

  // Disconnect from the room
  async disconnect() {
    if (this.room) {
      console.log('🔌 Disconnecting from LiveKit room...');
      
      // Stop monitoring
      this.stopParticipantMonitoring();
      
      try {
        await this.room.disconnect();
        console.log('✅ Successfully disconnected from LiveKit room');
      } catch (error) {
        console.error('❌ Error disconnecting from LiveKit room:', error);
      }
      
      this.room = null;
      this.isConnected = false;
      this.sessionId = null;
      
      if (this.onConnectionStateChangeCallback) {
        this.onConnectionStateChangeCallback(false);
      }
    }
  }

  // Set callback for receiving video/audio tracks
  setOnTrackCallback(callback) {
    this.onTrackCallback = callback;
  }

  // Set callback for connection state changes
  setOnConnectionStateChangeCallback(callback) {
    this.onConnectionStateChangeCallback = callback;
  }

  // Set callback for participant events
  setOnParticipantCallback(callback) {
    this.onParticipantCallback = callback;
  }

  // Get connection status
  getConnectionStatus() {
    return {
      isConnected: this.isConnected,
      room: this.room,
      roomName: this.room?.name || null,
      participantCount: this.room?.participants.size || 0,
      connectionState: this.room?.state || 'disconnected',
      sessionId: this.sessionId
    };
  }

  // Get room participants
  getParticipants() {
    if (!this.room || !this.room.participants) return [];
    
    return Array.from(this.room.participants.values()).map(participant => ({
      identity: participant.identity,
      isLocal: participant.isLocal,
      trackCount: participant.trackPublications?.size || 0,
      connectionQuality: participant.connectionQuality
    }));
  }

  // Enable/disable audio (for local participant)
  async setAudioEnabled(enabled) {
    if (!this.room || !this.room.localParticipant) return false;
    
    try {
      await this.room.localParticipant.setMicrophoneEnabled(enabled);
      console.log(`🎤 Microphone ${enabled ? 'enabled' : 'disabled'}`);
      return true;
    } catch (error) {
      console.error('❌ Failed to toggle microphone:', error);
      return false;
    }
  }

  // Enable/disable video (for local participant)
  async setVideoEnabled(enabled) {
    if (!this.room || !this.room.localParticipant) return false;
    
    try {
      await this.room.localParticipant.setCameraEnabled(enabled);
      console.log(`📹 Camera ${enabled ? 'enabled' : 'disabled'}`);
      return true;
    } catch (error) {
      console.error('❌ Failed to toggle camera:', error);
      return false;
    }
  }

  // Get connection quality
  getConnectionQuality() {
    if (!this.room || !this.room.participants) return null;
    
    const participants = Array.from(this.room.participants.values());
    const qualities = participants.map(p => p.connectionQuality);
    
    return {
      local: this.room.localParticipant?.connectionQuality || 'unknown',
      remote: qualities.length > 0 ? qualities : ['unknown']
    };
  }
}

// Export singleton instance
export default new LiveKitService();
