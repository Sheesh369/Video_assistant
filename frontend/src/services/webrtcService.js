// services/webrtcService.js
import heygenService from './heygenService.js';

class WebRTCService {
  constructor() {
    this.peerConnection = null;
    this.isConnected = false;
    this.onTrackCallback = null;
    this.onConnectionStateChangeCallback = null;
  }

  // Set up WebRTC Connection
  async setupConnection(sdpData, iceServers, sessionId) {
    try {
      console.log('🌐 Setting up WebRTC connection...');
      console.log('🔍 SDP Data received:', sdpData);
     
      // Extract the actual SDP string from HeyGen's response
      const sdpOffer = typeof sdpData === 'string' ? sdpData : sdpData.sdp;
     
      if (!sdpOffer) {
        throw new Error('No SDP offer found in response');
      }
     
      console.log('📋 Using SDP offer:', sdpOffer.substring(0, 100) + '...');
     
      const pc = new RTCPeerConnection({
        iceServers: iceServers && iceServers.length > 0 ? iceServers : [
          { urls: 'stun:stun.l.google.com:19302' },
          { urls: 'stun:stun1.l.google.com:19302' }
        ]
      });

      // CRITICAL: Add a receive-only transceiver for video to receive HeyGen's stream
      pc.addTransceiver('video', { direction: 'recvonly' });
      pc.addTransceiver('audio', { direction: 'recvonly' });

      // Handle incoming video/audio streams
      pc.ontrack = (event) => {
        console.log('📺 Received track:', event.track.kind);
        console.log('📺 Streams:', event.streams.length);
       
        if (this.onTrackCallback) {
          this.onTrackCallback(event);
        }
      };

      pc.oniceconnectionstatechange = () => {
        console.log('🧊 ICE connection state:', pc.iceConnectionState);
        if (pc.iceConnectionState === 'connected' || pc.iceConnectionState === 'completed') {
          console.log('✅ WebRTC connection established');
          this.isConnected = true;
        } else if (pc.iceConnectionState === 'disconnected' || pc.iceConnectionState === 'failed') {
          console.log('❌ WebRTC connection lost');
          this.isConnected = false;
        }
        
        if (this.onConnectionStateChangeCallback) {
          this.onConnectionStateChangeCallback(this.isConnected);
        }
      };

      pc.onsignalingstatechange = () => {
        console.log('📡 Signaling state:', pc.signalingState);
      };

      pc.onconnectionstatechange = () => {
        console.log('🔗 Connection state:', pc.connectionState);
        if (pc.connectionState === 'connected') {
          console.log('🎉 Peer connection fully established!');
        }
      };

      // CRITICAL: Wait for ICE gathering to complete
      return new Promise((resolve, reject) => {
        let timeout;
       
        const cleanup = () => {
          if (timeout) clearTimeout(timeout);
          pc.onicegatheringstatechange = null;
        };

        // Set remote description (HeyGen's offer)
        pc.setRemoteDescription(new RTCSessionDescription({
          type: 'offer',
          sdp: sdpOffer
        }))
        .then(() => {
          console.log('✅ Remote description set successfully');
          return pc.createAnswer();
        })
        .then((answer) => {
          console.log('✅ Answer created successfully');
          return pc.setLocalDescription(answer);
        })
        .then(() => {
          console.log('📡 Local description set, waiting for ICE gathering...');
         
          // Check if ICE gathering is already complete
          if (pc.iceGatheringState === 'complete') {
            this.sendAnswerToHeyGen(pc, sessionId, cleanup, resolve, reject);
            return;
          }

          // Wait for ICE gathering to complete
          pc.onicegatheringstatechange = () => {
            console.log('🧊 ICE gathering state:', pc.iceGatheringState);
            if (pc.iceGatheringState === 'complete') {
              this.sendAnswerToHeyGen(pc, sessionId, cleanup, resolve, reject);
            }
          };

          // Timeout after 15 seconds
          timeout = setTimeout(() => {
            console.log('⏰ ICE gathering timeout, sending answer anyway...');
            this.sendAnswerToHeyGen(pc, sessionId, cleanup, resolve, reject);
          }, 15000);
        })
        .catch((error) => {
          console.error('❌ Error in WebRTC setup:', error);
          cleanup();
          reject(error);
        });
      });

    } catch (error) {
      console.error('❌ WebRTC setup error:', error);
      throw error;
    }
  }

  // Send WebRTC Answer to HeyGen
  async sendAnswerToHeyGen(pc, sessionId, cleanup, resolve, reject) {
    cleanup();
    try {
      console.log('📤 Sending WebRTC answer to HeyGen...');
      console.log('📋 Local SDP:', pc.localDescription.sdp.substring(0, 100) + '...');
     
      const result = await heygenService.startSession(sessionId, pc.localDescription.sdp);
      
      if (result.success) {
        console.log('✅ HeyGen session started successfully');
        this.peerConnection = pc;
        resolve(pc);
      } else {
        console.error('❌ Failed to start HeyGen session');
        pc.close();
        reject(new Error('Failed to start session'));
      }
    } catch (error) {
      console.error('❌ Error sending answer to HeyGen:', error);
      pc.close();
      reject(error);
    }
  }

  // Close WebRTC Connection
  closeConnection() {
    if (this.peerConnection) {
      console.log('🔌 Closing WebRTC connection...');
      this.peerConnection.close();
      this.peerConnection = null;
      this.isConnected = false;
      
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

  // Get connection status
  getConnectionStatus() {
    return {
      isConnected: this.isConnected,
      peerConnection: this.peerConnection,
      connectionState: this.peerConnection?.connectionState || 'closed',
      iceConnectionState: this.peerConnection?.iceConnectionState || 'closed'
    };
  }

  // Resume AudioContext for iOS/Safari
  async resumeAudioContext() {
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      if (audioCtx.state === 'suspended') {
        await audioCtx.resume();
        console.log('🔊 AudioContext resumed');
        return true;
      }
      return true;
    } catch (error) {
      console.error('❌ Failed to resume audio:', error);
      return false;
    }
  }
}

// Export singleton instance
export default new WebRTCService();



