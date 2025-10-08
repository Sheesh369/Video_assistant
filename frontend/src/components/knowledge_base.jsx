import React, { useState, useEffect } from 'react';
import { Upload, Search, Database, FileText, Trash2, BarChart3, X, CheckCircle, AlertCircle, Loader } from 'lucide-react';

const BACKEND_URL = 'http://localhost:8000';

export default function KnowledgeBase() {
  // States
  const [files, setFiles] = useState([]);
  const [stats, setStats] = useState({});
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [textInput, setTextInput] = useState('');
  const [textMetadata, setTextMetadata] = useState('');
  const [activeTab, setActiveTab] = useState('upload'); // upload, search, manage, stats
  const [notification, setNotification] = useState(null);

  // Load initial data
  useEffect(() => {
    fetchFiles();
    fetchStats();
  }, []);

  // Show notification
  const showNotification = (message, type = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 5000);
  };

  // Fetch files
  const fetchFiles = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/kb/files`);
      const data = await response.json();
      if (data.success) {
        setFiles(data.files || []);
      }
    } catch (error) {
      console.error('Error fetching files:', error);
    }
  };

  // Fetch stats
  const fetchStats = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/kb/stats`);
      const data = await response.json();
      if (data.success) {
        setStats(data.stats || {});
      }
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  // Upload file
  const uploadFile = async () => {
    if (!selectedFile) {
      showNotification('Please select a file', 'error');
      return;
    }

    setUploadLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('metadata', JSON.stringify({
        description: `Uploaded ${selectedFile.name}`,
        upload_source: 'web_ui'
      }));

      const response = await fetch(`${BACKEND_URL}/kb/upload-file`, {
        method: 'POST',
        body: formData
      });

      const data = await response.json();
      if (data.success) {
        showNotification(`Successfully uploaded ${data.filename} with ${data.chunks_count} chunks`);
        setSelectedFile(null);
        fetchFiles();
        fetchStats();
      } else {
        showNotification(`Upload failed: ${data.error}`, 'error');
      }
    } catch (error) {
      showNotification(`Upload error: ${error.message}`, 'error');
    } finally {
      setUploadLoading(false);
    }
  };

  // Add text
  const addText = async () => {
    if (!textInput.trim()) {
      showNotification('Please enter some text', 'error');
      return;
    }

    setUploadLoading(true);
    try {
      const metadata = {
        source: 'manual_text_input',
        upload_source: 'web_ui'
      };

      if (textMetadata.trim()) {
        try {
          const parsedMeta = JSON.parse(textMetadata);
          Object.assign(metadata, parsedMeta);
        } catch {
          metadata.description = textMetadata;
        }
      }

      const response = await fetch(`${BACKEND_URL}/kb/add-text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: textInput,
          metadata
        })
      });

      const data = await response.json();
      if (data.success) {
        showNotification(`Successfully added text with ${data.chunks_count} chunks`);
        setTextInput('');
        setTextMetadata('');
        fetchStats();
      } else {
        showNotification(`Failed to add text: ${data.error}`, 'error');
      }
    } catch (error) {
      showNotification(`Error adding text: ${error.message}`, 'error');
    } finally {
      setUploadLoading(false);
    }
  };

  // Search knowledge base
  const searchKB = async () => {
    if (!searchQuery.trim()) {
      showNotification('Please enter a search query', 'error');
      return;
    }

    setSearchLoading(true);
    try {
      const response = await fetch(
        `${BACKEND_URL}/kb/search?query=${encodeURIComponent(searchQuery)}&limit=10`
      );
      const data = await response.json();
      
      if (data.success) {
        setSearchResults(data.results || []);
        showNotification(`Found ${data.count} results`);
      } else {
        showNotification(`Search failed: ${data.error}`, 'error');
      }
    } catch (error) {
      showNotification(`Search error: ${error.message}`, 'error');
    } finally {
      setSearchLoading(false);
    }
  };

  // Delete file
  const deleteFile = async (filename) => {
    if (!confirm(`Are you sure you want to delete "${filename}"?`)) return;

    try {
      const response = await fetch(`${BACKEND_URL}/kb/file/${encodeURIComponent(filename)}`, {
        method: 'DELETE'
      });
      const data = await response.json();
      
      if (data.success) {
        showNotification(`Deleted ${data.deleted_chunks} chunks from ${filename}`);
        fetchFiles();
        fetchStats();
      } else {
        showNotification(`Delete failed: ${data.error}`, 'error');
      }
    } catch (error) {
      showNotification(`Delete error: ${error.message}`, 'error');
    }
  };

  // Clear all data
  const clearAll = async () => {
    if (!confirm('Are you sure you want to clear ALL knowledge base data? This cannot be undone!')) return;

    try {
      const response = await fetch(`${BACKEND_URL}/kb/clear`, {
        method: 'DELETE'
      });
      const data = await response.json();
      
      if (data.success) {
        showNotification('Knowledge base cleared successfully');
        fetchFiles();
        fetchStats();
        setSearchResults([]);
      } else {
        showNotification(`Clear failed: ${data.error}`, 'error');
      }
    } catch (error) {
      showNotification(`Clear error: ${error.message}`, 'error');
    }
  };

  // Format file size
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Format date
  const formatDate = (isoString) => {
    try {
      return new Date(isoString).toLocaleString();
    } catch {
      return 'Unknown';
    }
  };

  const tabStyle = (isActive) => ({
    padding: '0.75rem 1.5rem',
    backgroundColor: isActive ? '#007bff' : 'transparent',
    color: isActive ? '#fff' : '#888',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '0.9rem',
    fontWeight: 'bold',
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    transition: 'all 0.2s'
  });

  return (
    <div style={{
      backgroundColor: '#1a1a1a',
      borderRadius: '12px',
      border: '1px solid #333',
      overflow: 'hidden',
      margin: '1rem 0'
    }}>
      {/* Header */}
      <div style={{
        backgroundColor: '#0a0a0a',
        padding: '1rem 1.5rem',
        borderBottom: '1px solid #333',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Database size={24} color="#4a9eff" />
          <h2 style={{ fontSize: '1.3rem', margin: 0, color: '#fff' }}>Knowledge Base</h2>
        </div>
        <div style={{ fontSize: '0.9rem', color: '#888' }}>
          {stats.total_chunks || 0} chunks • {stats.unique_files || 0} files
        </div>
      </div>

      {/* Notification */}
      {notification && (
        <div style={{
          padding: '1rem 1.5rem',
          backgroundColor: notification.type === 'success' ? '#155724' : '#721c24',
          color: '#fff',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          {notification.type === 'success' ? 
            <CheckCircle size={16} /> : 
            <AlertCircle size={16} />
          }
          <span>{notification.message}</span>
          <button
            onClick={() => setNotification(null)}
            style={{
              marginLeft: 'auto',
              background: 'none',
              border: 'none',
              color: '#fff',
              cursor: 'pointer',
              padding: '0.25rem'
            }}
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* Tabs */}
      <div style={{
        display: 'flex',
        gap: '0.5rem',
        padding: '1rem 1.5rem',
        borderBottom: '1px solid #333',
        backgroundColor: '#161616'
      }}>
        <button
          onClick={() => setActiveTab('upload')}
          style={tabStyle(activeTab === 'upload')}
        >
          <Upload size={16} />
          Upload
        </button>
        <button
          onClick={() => setActiveTab('search')}
          style={tabStyle(activeTab === 'search')}
        >
          <Search size={16} />
          Search
        </button>
        <button
          onClick={() => setActiveTab('manage')}
          style={tabStyle(activeTab === 'manage')}
        >
          <FileText size={16} />
          Manage
        </button>
        <button
          onClick={() => setActiveTab('stats')}
          style={tabStyle(activeTab === 'stats')}
        >
          <BarChart3 size={16} />
          Stats
        </button>
      </div>

      {/* Tab Content */}
      <div style={{ padding: '1.5rem' }}>
        
        {/* Upload Tab */}
        {activeTab === 'upload' && (
          <div>
            <div style={{ marginBottom: '2rem' }}>
              <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: '#fff' }}>Upload File</h3>
              <div style={{ 
                border: '2px dashed #444',
                borderRadius: '8px',
                padding: '2rem',
                textAlign: 'center',
                marginBottom: '1rem',
                backgroundColor: selectedFile ? '#0f2027' : '#0a0a0a'
              }}>
                <input
                  type="file"
                  onChange={(e) => setSelectedFile(e.target.files[0])}
                  accept=".txt,.pdf,.docx,.xlsx,.csv,.json,.md,.html,.py,.js"
                  style={{
                    width: '100%',
                    padding: '1rem',
                    backgroundColor: 'transparent',
                    border: 'none',
                    color: '#fff',
                    fontSize: '1rem'
                  }}
                />
                {selectedFile && (
                  <div style={{ marginTop: '1rem', color: '#4a9eff' }}>
                    Selected: {selectedFile.name} ({formatFileSize(selectedFile.size)})
                  </div>
                )}
              </div>
              <button
                onClick={uploadFile}
                disabled={!selectedFile || uploadLoading}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  backgroundColor: (!selectedFile || uploadLoading) ? '#666' : '#28a745',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: (!selectedFile || uploadLoading) ? 'not-allowed' : 'pointer',
                  fontSize: '1rem',
                  fontWeight: 'bold',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem'
                }}
              >
                {uploadLoading ? <Loader className="animate-spin" size={16} /> : <Upload size={16} />}
                {uploadLoading ? 'Uploading...' : 'Upload File'}
              </button>
            </div>

            <div>
              <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: '#fff' }}>Add Text</h3>
              <textarea
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="Paste or type your text content here..."
                style={{
                  width: '100%',
                  minHeight: '120px',
                  padding: '1rem',
                  backgroundColor: '#222',
                  color: '#fff',
                  border: '1px solid #444',
                  borderRadius: '8px',
                  fontSize: '0.9rem',
                  fontFamily: 'monospace',
                  resize: 'vertical',
                  marginBottom: '1rem'
                }}
              />
              <input
                type="text"
                value={textMetadata}
                onChange={(e) => setTextMetadata(e.target.value)}
                placeholder="Optional: Add metadata (JSON or simple description)"
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  backgroundColor: '#222',
                  color: '#fff',
                  border: '1px solid #444',
                  borderRadius: '8px',
                  fontSize: '0.9rem',
                  marginBottom: '1rem'
                }}
              />
              <button
                onClick={addText}
                disabled={!textInput.trim() || uploadLoading}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  backgroundColor: (!textInput.trim() || uploadLoading) ? '#666' : '#007bff',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: (!textInput.trim() || uploadLoading) ? 'not-allowed' : 'pointer',
                  fontSize: '1rem',
                  fontWeight: 'bold',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem'
                }}
              >
                {uploadLoading ? <Loader className="animate-spin" size={16} /> : <FileText size={16} />}
                {uploadLoading ? 'Adding...' : 'Add Text'}
              </button>
            </div>
          </div>
        )}

        {/* Search Tab */}
        {activeTab === 'search' && (
          <div>
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && searchKB()}
                placeholder="Search your knowledge base..."
                style={{
                  flex: 1,
                  padding: '0.75rem',
                  backgroundColor: '#222',
                  color: '#fff',
                  border: '1px solid #444',
                  borderRadius: '8px',
                  fontSize: '1rem'
                }}
              />
              <button
                onClick={searchKB}
                disabled={!searchQuery.trim() || searchLoading}
                style={{
                  padding: '0.75rem 1.5rem',
                  backgroundColor: (!searchQuery.trim() || searchLoading) ? '#666' : '#007bff',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: (!searchQuery.trim() || searchLoading) ? 'not-allowed' : 'pointer',
                  fontSize: '1rem',
                  fontWeight: 'bold',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}
              >
                {searchLoading ? <Loader className="animate-spin" size={16} /> : <Search size={16} />}
                Search
              </button>
            </div>

            {searchResults.length > 0 && (
              <div>
                <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: '#fff' }}>
                  Search Results ({searchResults.length})
                </h3>
                <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                  {searchResults.map((result, index) => (
                    <div key={result.id || index} style={{
                      backgroundColor: '#222',
                      border: '1px solid #333',
                      borderRadius: '8px',
                      padding: '1rem',
                      marginBottom: '1rem'
                    }}>
                      <div style={{ fontSize: '0.8rem', color: '#888', marginBottom: '0.5rem' }}>
                        Source: {result.metadata?.filename || result.metadata?.source || 'Unknown'} 
                        {result.distance && ` • Similarity: ${(1 - result.distance).toFixed(3)}`}
                      </div>
                      <div style={{ color: '#fff', lineHeight: '1.5', fontSize: '0.9rem' }}>
                        {result.text}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Manage Tab */}
        {activeTab === 'manage' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h3 style={{ fontSize: '1.1rem', margin: 0, color: '#fff' }}>
                Manage Files ({files.length})
              </h3>
              {files.length > 0 && (
                <button
                  onClick={clearAll}
                  style={{
                    padding: '0.5rem 1rem',
                    backgroundColor: '#dc3545',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontSize: '0.9rem',
                    fontWeight: 'bold',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem'
                  }}
                >
                  <Trash2 size={14} />
                  Clear All
                </button>
              )}
            </div>

            {files.length === 0 ? (
              <div style={{
                textAlign: 'center',
                padding: '3rem',
                color: '#888'
              }}>
                <FileText size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
                <div>No files uploaded yet</div>
                <div style={{ fontSize: '0.8rem', marginTop: '0.5rem' }}>
                  Upload files in the Upload tab to get started
                </div>
              </div>
            ) : (
              <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                {files.map((file, index) => (
                  <div key={index} style={{
                    backgroundColor: '#222',
                    border: '1px solid #333',
                    borderRadius: '8px',
                    padding: '1rem',
                    marginBottom: '1rem',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ color: '#fff', fontWeight: 'bold', marginBottom: '0.5rem' }}>
                        {file.filename}
                      </div>
                      <div style={{ fontSize: '0.8rem', color: '#888' }}>
                        {file.chunks_count} chunks • {formatFileSize(file.file_size)} • {formatDate(file.upload_timestamp)}
                      </div>
                    </div>
                    <button
                      onClick={() => deleteFile(file.filename)}
                      style={{
                        padding: '0.5rem',
                        backgroundColor: '#dc3545',
                        color: '#fff',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.25rem'
                      }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Stats Tab */}
        {activeTab === 'stats' && (
          <div>
            <h3 style={{ fontSize: '1.1rem', marginBottom: '1.5rem', color: '#fff' }}>
              Knowledge Base Statistics
            </h3>
            
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '1rem',
              marginBottom: '2rem'
            }}>
              <div style={{
                backgroundColor: '#222',
                border: '1px solid #333',
                borderRadius: '8px',
                padding: '1.5rem',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#4a9eff', marginBottom: '0.5rem' }}>
                  {stats.total_chunks || 0}
                </div>
                <div style={{ color: '#888' }}>Total Chunks</div>
              </div>

              <div style={{
                backgroundColor: '#222',
                border: '1px solid #333',
                borderRadius: '8px',
                padding: '1.5rem',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#28a745', marginBottom: '0.5rem' }}>
                  {stats.unique_files || 0}
                </div>
                <div style={{ color: '#888' }}>Unique Files</div>
              </div>

              <div style={{
                backgroundColor: '#222',
                border: '1px solid #333',
                borderRadius: '8px',
                padding: '1.5rem',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#ffc107', marginBottom: '0.5rem' }}>
                  {stats.estimated_total_characters ? formatFileSize(stats.estimated_total_characters) : '0 B'}
                </div>
                <div style={{ color: '#888' }}>Total Content</div>
              </div>
            </div>

            {stats.file_types && Object.keys(stats.file_types).length > 0 && (
              <div style={{
                backgroundColor: '#222',
                border: '1px solid #333',
                borderRadius: '8px',
                padding: '1.5rem'
              }}>
                <h4 style={{ margin: '0 0 1rem 0', color: '#fff' }}>File Types</h4>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  {Object.entries(stats.file_types).map(([type, count]) => (
                    <div key={type} style={{
                      backgroundColor: '#333',
                      color: '#fff',
                      padding: '0.5rem 1rem',
                      borderRadius: '20px',
                      fontSize: '0.9rem'
                    }}>
                      {type}: {count}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}