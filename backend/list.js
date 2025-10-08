// HeyGen Avatar List Fetcher
// This code helps you get all available avatars from HeyGen API

const HEYGEN_API_KEY = 'YzEwYzg2ZTBmZGVmNDJmMGJlOGVjZjEzYTEzZDU4NDktMTc1NDM4MjQ4NA=='; // Replace with your actual API key
const HEYGEN_API_BASE = 'https://api.heygen.com/v1';

// Function to fetch avatar list
async function fetchHeyGenAvatars() {
  try {
    console.log('🔍 Fetching HeyGen avatars...');
    
    const response = await fetch(`${HEYGEN_API_BASE}/streaming/avatar.list`, {
      method: 'GET',
      headers: {
        'accept': 'application/json',
        'x-api-key': HEYGEN_API_KEY
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    
    if (data.code === 100) { // Success code
      console.log('✅ Successfully fetched avatars');
      return data.data; // Return the array of avatars
    } else {
      throw new Error(`API error: ${data.message} (Code: ${data.code})`);
    }
  } catch (error) {
    console.error('❌ Error fetching avatars:', error);
    throw error;
  }
}

// Function to format avatars for your React component
function formatAvatarsForReact(avatars) {
  return avatars
    .filter(avatar => avatar.status === 'ACTIVE') // Only active avatars
    .map(avatar => ({
      id: avatar.avatar_id,
      name: avatar.pose_name || `Avatar ${avatar.avatar_id.substring(0, 8)}`,
      description: `${avatar.is_public ? 'Public' : 'Custom'} avatar - ${avatar.default_voice ? 'Voice enabled' : 'No voice'}`,
      isPublic: avatar.is_public,
      preview: avatar.normal_preview,
      voice: avatar.default_voice,
      createdAt: avatar.created_at
    }))
    .sort((a, b) => a.name.localeCompare(b.name)); // Sort alphabetically
}

// Function to generate React component code
function generateAvatarOptionsCode(formattedAvatars) {
  const avatarOptionsCode = formattedAvatars
    .map(avatar => 
      `    { id: '${avatar.id}', name: '${avatar.name}', description: '${avatar.description}' }`
    )
    .join(',\n');
  
  return `// Generated avatar options for your React component
const avatarOptions = [
${avatarOptionsCode}
];`;
}

// Main execution function
async function main() {
  try {
    // Check if API key is set
    if (HEYGEN_API_KEY === 'YOUR_HEYGEN_API_KEY_HERE') {
      console.error('❌ Please set your HeyGen API key in the HEYGEN_API_KEY variable');
      return;
    }

    // Fetch avatars
    const avatars = await fetchHeyGenAvatars();
    console.log(`📊 Found ${avatars.length} total avatars`);

    // Format for React
    const formattedAvatars = formatAvatarsForReact(avatars);
    console.log(`✅ ${formattedAvatars.length} active avatars ready for use`);

    // Display formatted avatars
    console.log('\n📋 Available Avatars:');
    formattedAvatars.forEach((avatar, index) => {
      console.log(`${index + 1}. ${avatar.name}`);
      console.log(`   ID: ${avatar.id}`);
      console.log(`   Type: ${avatar.isPublic ? 'Public' : 'Custom'}`);
      console.log(`   Voice: ${avatar.voice || 'None'}`);
      console.log('');
    });

    // Generate React component code
    const reactCode = generateAvatarOptionsCode(formattedAvatars);
    console.log('\n🔧 React Component Code:');
    console.log(reactCode);

    // Return data for further use
    return {
      raw: avatars,
      formatted: formattedAvatars,
      reactCode: reactCode
    };

  } catch (error) {
    console.error('❌ Failed to fetch avatars:', error.message);
    
    // Provide troubleshooting tips
    console.log('\n🔧 Troubleshooting:');
    console.log('1. Make sure your API key is correct');
    console.log('2. Check if your API key has streaming avatar permissions');
    console.log('3. Verify your account is in good standing');
    console.log('4. Try the request in Postman or curl first');
  }
}

// For Node.js environments
if (typeof window === 'undefined') {
  // Running in Node.js
  main();
}

// For browser environments or React components
async function getAvatarsForReact() {
  try {
    const avatars = await fetchHeyGenAvatars();
    return formatAvatarsForReact(avatars);
  } catch (error) {
    console.error('Error fetching avatars for React:', error);
    return [];
  }
}

// Export functions for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    fetchHeyGenAvatars,
    formatAvatarsForReact,
    generateAvatarOptionsCode,
    getAvatarsForReact,
    main
  };
}