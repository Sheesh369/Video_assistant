// export default VoicePrompt;

// remove debug info 

// VoicePrompt.jsx - FIXED VERSION with better audio handling
import React, { useState, useRef, useEffect } from 'react';

const VoicePrompt = ({ 
  onTranscriptionUpdate, 
  disabled = false,
  className = "",
  style = {} 
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [audioLevel, setAudioLevel] = useState(0);
  const [sessionId, setSessionId] = useState(null);
  
  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const animationFrameRef = useRef(null);
  const chunksRef = useRef([]);

  // Audio level monitoring
  const updateAudioLevel = () => {
    if (!analyserRef.current) return;
    
    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteFrequencyData(dataArray);
    
    // Calculate average audio level
    const average = dataArray.reduce((sum, value) => sum + value, 0) / dataArray.length;
    const normalizedLevel = average / 255;
    
    setAudioLevel(normalizedLevel);
    
    if (isRecording) {
      animationFrameRef.current = requestAnimationFrame(updateAudioLevel);
    }
  };

  // Initialize audio context and analyzer
  const setupAudioAnalysis = (stream) => {
    try {
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
      analyserRef.current = audioContextRef.current.createAnalyser();
      analyserRef.current.fftSize = 256;
      
      const source = audioContextRef.current.createMediaStreamSource(stream);
      source.connect(analyserRef.current);
      
      updateAudioLevel();
    } catch (error) {
      console.error('❌ Error setting up audio analysis:', error);
    }
  };

  // CRITICAL FIX: Improved audio conversion function
  const convertToWav = async (webmBlob) => {
    return new Promise((resolve) => {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const reader = new FileReader();
      
      reader.onload = async () => {
        try {
          console.log('🔄 Decoding WebM audio...');
          const arrayBuffer = reader.result;
          const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
          
          console.log(`🎵 Audio decoded: ${audioBuffer.duration.toFixed(2)}s, ${audioBuffer.sampleRate}Hz, ${audioBuffer.numberOfChannels} channels`);
          
          // CRITICAL: Don't skip very short audio - it might contain speech!
          if (audioBuffer.duration < 0.5) {
            console.log('⚠️ Short audio clip, but proceeding with conversion...');
          }
          
          // Convert to WAV
          const wavBuffer = audioBufferToWav(audioBuffer);
          const wavBlob = new Blob([wavBuffer], { type: 'audio/wav' });
          
          console.log(`✅ WAV conversion complete: ${wavBlob.size} bytes`);
          resolve(wavBlob);
        } catch (error) {
          console.error('❌ Audio decoding/conversion error:', error);
          console.log('🔄 Using original WebM blob as fallback');
          resolve(webmBlob); // Fallback to original
        }
      };
      
      reader.onerror = () => {
        console.error('❌ FileReader error');
        console.log('🔄 Using original WebM blob as fallback');
        resolve(webmBlob); // Fallback
      };
      
      reader.readAsArrayBuffer(webmBlob);
    });
  };

  // Convert AudioBuffer to WAV format
  const audioBufferToWav = (audioBuffer) => {
    const length = audioBuffer.length;
    const sampleRate = audioBuffer.sampleRate;
    const numberOfChannels = audioBuffer.numberOfChannels;
    
    // Create WAV buffer
    const buffer = new ArrayBuffer(44 + length * numberOfChannels * 2);
    const view = new DataView(buffer);
    
    // WAV header
    const writeString = (offset, string) => {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    };
    
    writeString(0, 'RIFF');
    view.setUint32(4, 36 + length * numberOfChannels * 2, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); // PCM format
    view.setUint16(22, numberOfChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * numberOfChannels * 2, true);
    view.setUint16(32, numberOfChannels * 2, true);
    view.setUint16(34, 16, true); // 16-bit samples
    writeString(36, 'data');
    view.setUint32(40, length * numberOfChannels * 2, true);
    
    // Convert audio data to 16-bit PCM
    let offset = 44;
    for (let i = 0; i < length; i++) {
      for (let channel = 0; channel < numberOfChannels; channel++) {
        const channelData = audioBuffer.getChannelData(channel);
        const sample = Math.max(-1, Math.min(1, channelData[i]));
        view.setInt16(offset, sample * 0x7FFF, true);
        offset += 2;
      }
    }
    
    return buffer;
  };

  // Start recording
  const startRecording = async () => {
    try {
      setError(null);
      setIsProcessing(true);
      
      console.log('🎤 Requesting microphone access...');
      
      // CRITICAL FIX: Better audio constraints for consistent recording
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 44100,
          channelCount: 1,    // Mono audio for consistency
          latency: 0.01,
          volume: 1.0
        }
      });
      
      streamRef.current = stream;
      chunksRef.current = [];
      
      // Setup audio level monitoring
      setupAudioAnalysis(stream);
      
      // Start recording session on backend FIRST
      console.log('🎤 Creating backend recording session...');
      const response = await fetch('http://localhost:8000/voice/start-recording', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      const sessionData = await response.json();
      
      if (sessionData.status !== 'success') {
        throw new Error('Failed to create recording session: ' + sessionData.error);
      }
      
      const newSessionId = sessionData.session_id;
      setSessionId(newSessionId);
      console.log('✅ Recording session created:', newSessionId);
      
      // Setup MediaRecorder with optimal settings
      let mimeType = 'audio/webm;codecs=opus';
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = 'audio/webm';
        if (!MediaRecorder.isTypeSupported(mimeType)) {
          mimeType = 'audio/wav';
        }
      }
      
      console.log('🎤 Using MIME type:', mimeType);
      
      mediaRecorderRef.current = new MediaRecorder(stream, {
        mimeType: mimeType,
        audioBitsPerSecond: 128000  // Good quality but not excessive
      });
      
      // CRITICAL FIX: Better chunk handling
      mediaRecorderRef.current.ondataavailable = async (event) => {
        if (event.data.size > 0) {
          console.log(`🎤 Received audio chunk: ${event.data.size} bytes`);
          chunksRef.current.push(event.data);
          
          try {
            // Convert to WAV for better Whisper compatibility
            const wavBlob = await convertToWav(event.data);
            console.log(`🎵 Converted to WAV: ${wavBlob.size} bytes`);
            
            const reader = new FileReader();
            reader.onloadend = async () => {
              try {
                const base64Audio = reader.result.split(',')[1];
                
                console.log(`📤 Sending WAV chunk for session: ${newSessionId}`);
                
                const transcriptionResponse = await fetch('http://localhost:8000/voice/add-chunk', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    session_id: newSessionId,
                    audio_data: base64Audio,
                    format: 'wav'
                  })
                });
                
                const result = await transcriptionResponse.json();
                console.log(`📊 Chunk processed: ${result.status}, chunks: ${result.chunks_count}`);
                
              } catch (error) {
                console.error('❌ Chunk processing error:', error);
              }
            };
            reader.readAsDataURL(wavBlob);
            
          } catch (error) {
            console.error('❌ Audio conversion failed, using original:', error);
            
            // Fallback to original WebM
            const reader = new FileReader();
            reader.onloadend = async () => {
              const base64Audio = reader.result.split(',')[1];
              
              const transcriptionResponse = await fetch('http://localhost:8000/voice/add-chunk', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  session_id: newSessionId,
                  audio_data: base64Audio,
                  format: 'webm'
                })
              });
              
              const result = await transcriptionResponse.json();
              console.log(`📊 Chunk processed (fallback): ${result.status}`);
            };
            reader.readAsDataURL(event.data);
          }
        } else {
          console.warn('⚠️ Received empty audio chunk');
        }
      };
      
      mediaRecorderRef.current.onerror = (event) => {
        console.error('❌ MediaRecorder error:', event.error);
        setError('Recording error: ' + event.error);
      };
      
      // CRITICAL FIX: Use longer chunks to capture complete phrases
      // This prevents cutting off in the middle of words
      mediaRecorderRef.current.start(5000); // 5 seconds instead of 3
      setIsRecording(true);
      setIsProcessing(false);
      
      console.log('🎤 Recording started with session:', newSessionId);
      
    } catch (error) {
      console.error('❌ Error starting recording:', error);
      setError('Failed to start recording: ' + error.message);
      setIsProcessing(false);
    }
  };

  // Stop recording
  const stopRecording = async () => {
    try {
      setIsProcessing(true);
      console.log('🎤 Stopping recording...');
      
      // Stop MediaRecorder - this will trigger final ondataavailable
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop();
        
        // CRITICAL FIX: Wait a moment for final chunk to be processed
        await new Promise(resolve => setTimeout(resolve, 500));
      }
      
      // Stop all tracks
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      
      // Stop audio analysis
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      
      if (audioContextRef.current) {
        await audioContextRef.current.close();
      }
      
      // CRITICAL FIX: Wait a bit longer before getting final transcription
      // This ensures all chunks are processed
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Get final transcription from backend
      if (sessionId) {
        console.log('🎤 Getting final transcription for session:', sessionId);
        
        const response = await fetch('http://localhost:8000/voice/stop-recording', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
          console.log('✅ Final transcription result:', result);
          
          if (result.text && result.text.trim()) {
            onTranscriptionUpdate(result.text.trim(), true); // true = final
            console.log('📝 Final transcription:', result.text.trim());
          } else {
            console.warn('⚠️ No final transcription text received');
            
            // FALLBACK: If no final text, try to get something from chunks
            if (chunksRef.current.length > 0) {
              console.log('🔄 Attempting fallback transcription from stored chunks...');
              
              // Try to transcribe the largest chunk as a last resort
              const sortedChunks = [...chunksRef.current].sort((a, b) => b.size - a.size);
              if (sortedChunks[0] && sortedChunks[0].size > 1000) {
                console.log('🎤 Transcribing largest chunk as fallback...');
                
                try {
                  const wavBlob = await convertToWav(sortedChunks[0]);
                  const reader = new FileReader();
                  reader.onloadend = async () => {
                    const base64Audio = reader.result.split(',')[1];
                    
                    const fallbackResponse = await fetch('http://localhost:8000/voice/transcribe', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({
                        audio_data: base64Audio,
                        format: 'wav'
                      })
                    });
                    
                    const fallbackResult = await fallbackResponse.json();
                    if (fallbackResult.text && fallbackResult.text.trim()) {
                      onTranscriptionUpdate(fallbackResult.text.trim(), true);
                      console.log('✅ Fallback transcription successful:', fallbackResult.text.trim());
                    }
                  };
                  reader.readAsDataURL(wavBlob);
                } catch (fallbackError) {
                  console.error('❌ Fallback transcription failed:', fallbackError);
                }
              }
            }
          }
        } else {
          console.error('❌ Failed to get final transcription:', result);
          setError('Transcription failed: ' + (result.error || 'Unknown error'));
        }
      }
      
      // Reset states
      setIsRecording(false);
      setIsProcessing(false);
      setAudioLevel(0);
      setSessionId(null);
      chunksRef.current = [];
      
    } catch (error) {
      console.error('❌ Error stopping recording:', error);
      setError('Failed to stop recording: ' + error.message);
      setIsProcessing(false);
      setIsRecording(false);
    }
  };

  // Toggle recording
  const toggleRecording = () => {
    if (disabled) return;
    
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  // Error auto-clear
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  return (
    <div 
      className={className}
      style={{
        position: 'relative',
        display: 'inline-flex',
        alignItems: 'center',
        ...style
      }}
    >
      {/* Mic Button */}
      <button
        onClick={toggleRecording}
        disabled={disabled || isProcessing}
        style={{
          width: '44px',
          height: '44px',
          borderRadius: '8px',
          border: 'none',
          backgroundColor: 
            disabled || isProcessing ? '#666' :
            isRecording ? '#dc3545' : '#28a745',
          color: '#fff',
          cursor: 
            disabled || isProcessing ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '1.2rem',
          transition: 'all 0.2s ease',
          transform: isRecording ? 'scale(1.1)' : 'scale(1)',
          boxShadow: isRecording ? '0 0 20px rgba(220, 53, 69, 0.6)' : 'none',
          position: 'relative',
          overflow: 'hidden'
        }}
        title={
          disabled ? 'Voice input disabled' :
          isProcessing ? 'Processing...' :
          isRecording ? 'Click to stop recording' : 'Click to start voice input'
        }
      >
        {isProcessing ? (
          <div 
            style={{
              width: '16px',
              height: '16px',
              border: '2px solid #fff',
              borderTop: '2px solid transparent',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite'
            }}
          />
        ) : isRecording ? (
          '⏹️'
        ) : (
          '🎤'
        )}
        
        {/* Audio level indicator */}
        {isRecording && (
          <div
            style={{
              position: 'absolute',
              bottom: '2px',
              left: '50%',
              transform: 'translateX(-50%)',
              width: `${Math.max(20, audioLevel * 100)}%`,
              height: '3px',
              backgroundColor: '#fff',
              borderRadius: '2px',
              opacity: 0.8,
              transition: 'width 0.1s ease'
            }}
          />
        )}
      </button>

      {/* Recording Status Indicator */}
      {isRecording && (
        <div
          style={{
            position: 'absolute',
            top: '-8px',
            right: '-8px',
            width: '12px',
            height: '12px',
            backgroundColor: '#dc3545',
            borderRadius: '50%',
            animation: 'pulse 1.5s ease-in-out infinite'
          }}
        />
      )}

      {/* Error Tooltip */}
      {error && (
        <div
          style={{
            position: 'absolute',
            bottom: '100%',
            left: '50%',
            transform: 'translateX(-50%)',
            backgroundColor: '#dc3545',
            color: '#fff',
            padding: '0.5rem',
            borderRadius: '4px',
            fontSize: '0.8rem',
            whiteSpace: 'nowrap',
            marginBottom: '5px',
            zIndex: 1000,
            maxWidth: '200px',
            textAlign: 'center'
          }}
        >
          {error}
          <div
            style={{
              position: 'absolute',
              top: '100%',
              left: '50%',
              transform: 'translateX(-50%)',
              width: 0,
              height: 0,
              borderLeft: '5px solid transparent',
              borderRight: '5px solid transparent',
              borderTop: '5px solid #dc3545'
            }}
          />
        </div>
      )}

      {/* CSS Animations */}
      <style jsx>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  );
};

export default VoicePrompt;