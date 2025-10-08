import React, { useState } from 'react';

export default function AvatarFetcher() {
  const [avatars, setAvatars] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchAvatars = async () => {
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch('http://localhost:8000/api/avatars/available');
      const data = await response.json();
      
      if (data.success) {
        setAvatars(data.avatars || []);
      } else {
        setError(data.error || 'Failed to fetch avatars');
      }
    } catch (err) {
      setError('Error: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    alert('Copied to clipboard!');
  };

  return (
    <div style={{
      padding: '2rem',
      fontFamily: 'system-ui',
      maxWidth: '1200px',
      margin: '0 auto',
      backgroundColor: '#0f1419',
      color: '#e2e8f0',
      minHeight: '100vh'
    }}>
      <h1 style={{ 
        fontSize: '2rem', 
        marginBottom: '1rem',
        color: '#4299e1'
      }}>
        HeyGen Avatar ID Fetcher
      </h1>
      
      <p style={{ 
        marginBottom: '1.5rem', 
        color: '#a0aec0',
        lineHeight: '1.6'
      }}>
        This tool fetches all available Interactive Avatars from your HeyGen account.
        Use the Avatar IDs from this list in your application.
      </p>

      <button
        onClick={fetchAvatars}
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
          marginBottom: '2rem'
        }}
      >
        {loading ? 'Fetching...' : 'Fetch Available Avatars'}
      </button>

      {error && (
        <div style={{
          padding: '1rem',
          backgroundColor: '#742a2a',
          border: '1px solid #fc8181',
          borderRadius: '8px',
          marginBottom: '1.5rem',
          color: '#feb2b2'
        }}>
          {error}
          {error.includes('403') && (
            <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: '#2d3748', borderRadius: '4px' }}>
              <strong>403 Forbidden Error:</strong> Your HeyGen API key doesn't have permission to access the avatar list.
              <br /><br />
              <strong>Solutions:</strong>
              <ul style={{ marginTop: '0.5rem', paddingLeft: '1.5rem' }}>
                <li>Use the fallback avatars in your main app (Monica, Tyler, Josh)</li>
                <li>Check your HeyGen account permissions</li>
                <li>Try using the public avatar IDs directly</li>
              </ul>
            </div>
          )}
        </div>
      )}

      {avatars.length > 0 && (
        <div>
          <h2 style={{ 
            fontSize: '1.5rem', 
            marginBottom: '1rem',
            color: '#e2e8f0'
          }}>
            Found {avatars.length} Available Avatars
          </h2>

          <div style={{
            display: 'grid',
            gap: '1rem',
            gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))'
          }}>
            {avatars.map((avatar, index) => (
              <div
                key={index}
                style={{
                  padding: '1.5rem',
                  backgroundColor: '#1a202c',
                  border: '1px solid #2d3748',
                  borderRadius: '8px'
                }}
              >
                <div style={{ 
                  fontSize: '1.1rem', 
                  fontWeight: '600',
                  marginBottom: '0.75rem',
                  color: '#4299e1'
                }}>
                  {avatar.avatar_name || 'Unnamed Avatar'}
                </div>

                <div style={{ 
                  marginBottom: '0.5rem',
                  fontSize: '0.9rem'
                }}>
                  <span style={{ color: '#a0aec0' }}>Avatar ID:</span>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    marginTop: '0.25rem'
                  }}>
                    <code style={{
                      flex: 1,
                      padding: '0.5rem',
                      backgroundColor: '#2d3748',
                      borderRadius: '4px',
                      fontSize: '0.85rem',
                      color: '#68d391',
                      wordBreak: 'break-all'
                    }}>
                      {avatar.avatar_id}
                    </code>
                    <button
                      onClick={() => copyToClipboard(avatar.avatar_id)}
                      style={{
                        padding: '0.5rem',
                        backgroundColor: '#2d3748',
                        color: '#4299e1',
                        border: '1px solid #4299e1',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.75rem'
                      }}
                    >
                      Copy
                    </button>
                  </div>
                </div>

                {avatar.preview_video_url && (
                  <div style={{ marginBottom: '0.5rem', fontSize: '0.9rem' }}>
                    <span style={{ color: '#a0aec0' }}>Preview:</span>
                    <a
                      href={avatar.preview_video_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        display: 'block',
                        marginTop: '0.25rem',
                        color: '#4299e1',
                        textDecoration: 'underline',
                        fontSize: '0.85rem'
                      }}
                    >
                      View Video
                    </a>
                  </div>
                )}

                <div style={{
                  marginTop: '0.75rem',
                  paddingTop: '0.75rem',
                  borderTop: '1px solid #2d3748',
                  fontSize: '0.85rem',
                  color: '#a0aec0'
                }}>
                  <div>Gender: {avatar.gender || 'N/A'}</div>
                  <div>Preview Voice: {avatar.preview_voice_id || 'N/A'}</div>
                </div>

                <div style={{
                  marginTop: '1rem',
                  padding: '0.75rem',
                  backgroundColor: '#2d3748',
                  borderRadius: '4px',
                  fontSize: '0.8rem',
                  color: '#cbd5e0'
                }}>
                  <div style={{ fontWeight: '600', marginBottom: '0.5rem' }}>
                    Usage in code:
                  </div>
                  <code style={{ 
                    display: 'block',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-all'
                  }}>
                    {`{\n  id: '${avatar.avatar_id}',\n  name: '${avatar.avatar_name}',\n  voice_id: 'YOUR_VOICE_ID',\n  gender: '${avatar.gender || 'unknown'}'\n}`}
                  </code>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{
        marginTop: '3rem',
        padding: '1.5rem',
        backgroundColor: '#1a202c',
        border: '1px solid #2d3748',
        borderRadius: '8px'
      }}>
        <h3 style={{ 
          fontSize: '1.2rem',
          marginBottom: '1rem',
          color: '#4299e1'
        }}>
          Voice IDs You Provided:
        </h3>
        <div style={{ 
          display: 'grid',
          gap: '0.75rem',
          fontSize: '0.9rem'
        }}>
          <div>
            <strong style={{ color: '#68d391' }}>Annie:</strong> e0e84faea390465896db75a83be45085
            <button
              onClick={() => copyToClipboard('e0e84faea390465896db75a83be45085')}
              style={{
                marginLeft: '0.5rem',
                padding: '0.25rem 0.5rem',
                backgroundColor: '#2d3748',
                color: '#4299e1',
                border: '1px solid #4299e1',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.75rem'
              }}
            >
              Copy
            </button>
          </div>
          <div>
            <strong style={{ color: '#68d391' }}>Brandon:</strong> d08c85e6cff84d78b6dc41d83a2eccce
            <button
              onClick={() => copyToClipboard('d08c85e6cff84d78b6dc41d83a2eccce')}
              style={{
                marginLeft: '0.5rem',
                padding: '0.25rem 0.5rem',
                backgroundColor: '#2d3748',
                color: '#4299e1',
                border: '1px solid #4299e1',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.75rem'
              }}
            >
              Copy
            </button>
          </div>
          <div>
            <strong style={{ color: '#68d391' }}>Rebecca:</strong> cf9c0a84333b48e2a6e09bebf25d42d3
            <button
              onClick={() => copyToClipboard('cf9c0a84333b48e2a6e09bebf25d42d3')}
              style={{
                marginLeft: '0.5rem',
                padding: '0.25rem 0.5rem',
                backgroundColor: '#2d3748',
                color: '#4299e1',
                border: '1px solid #4299e1',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.75rem'
              }}
            >
              Copy
            </button>
          </div>
          <div>
            <strong style={{ color: '#68d391' }}>Daphne:</strong> c1926d821b4d43d6a5f07f2985bb5cd1
            <button
              onClick={() => copyToClipboard('c1926d821b4d43d6a5f07f2985bb5cd1')}
              style={{
                marginLeft: '0.5rem',
                padding: '0.25rem 0.5rem',
                backgroundColor: '#2d3748',
                color: '#4299e1',
                border: '1px solid #4299e1',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.75rem'
              }}
            >
              Copy
            </button>
          </div>
        </div>
        <p style={{
          marginTop: '1rem',
          color: '#a0aec0',
          fontSize: '0.85rem',
          lineHeight: '1.5'
        }}>
          These are voice IDs. Pair them with avatar IDs from the list above.
        </p>
      </div>

      <div style={{
        marginTop: '2rem',
        padding: '1.5rem',
        backgroundColor: '#2d3748',
        borderRadius: '8px',
        fontSize: '0.9rem',
        lineHeight: '1.6',
        color: '#cbd5e0'
      }}>
        <h3 style={{ 
          fontSize: '1.1rem',
          marginBottom: '0.75rem',
          color: '#f6e05e'
        }}>
          📋 Instructions:
        </h3>
        <ol style={{ paddingLeft: '1.5rem' }}>
          <li style={{ marginBottom: '0.5rem' }}>
            Click "Fetch Available Avatars" to see all avatars in your HeyGen account
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            Find the avatar you want to use and copy its Avatar ID
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            Pair it with one of the voice IDs (Annie, Brandon, Rebecca, or Daphne)
          </li>
          <li>
            Update your avatar list in the code with the correct avatar ID and voice ID combination
          </li>
        </ol>
      </div>
    </div>
  );
}
