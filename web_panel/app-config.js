// 🌐 KranikBot Web Panel - Konfiguracja (RENDER_DEPLOY VERSION)
// Ten plik zawiera ustawienia dla różnych środowisk

console.log('🔧 Ładowanie config-new.js - RENDER_DEPLOY VERSION');

const ENVIRONMENTS = {
    // Lokalne środowisko deweloperskie
    local: {
        API_BASE_URL: 'http://localhost:5000/api',
        API_KEY: 'kranikbot-secure-key-2024',
        REFRESH_INTERVAL: 5000,
        DEMO_MODE: false
    },
    
    // Render.com production
    render: {
        API_BASE_URL: 'https://kranikbot-api.onrender.com/api',
        API_KEY: 'kranikbot-secure-key-2024',
        REFRESH_INTERVAL: 10000,
        DEMO_MODE: false
    },
    
    // GitHub Pages z Heroku backend
    github_heroku: {
        API_BASE_URL: 'https://your-app-name.herokuapp.com/api',
        API_KEY: 'kranikbot-secure-key-2024',
        REFRESH_INTERVAL: 10000,
        DEMO_MODE: false
    },
    
    // GitHub Pages z Railway backend
    github_railway: {
        API_BASE_URL: 'https://your-app-name.railway.app/api',
        API_KEY: 'kranikbot-secure-key-2024',
        REFRESH_INTERVAL: 10000,
        DEMO_MODE: false
    },
    
    // Tryb demo (bez backend)
    demo: {
        API_BASE_URL: 'http://localhost:5000/api',
        API_KEY: 'demo_key',
        REFRESH_INTERVAL: 3000,
        DEMO_MODE: true
    }
};

// 🔧 Automatyczne wykrywanie środowiska
function detectEnvironment() {
    const hostname = window.location.hostname;
    
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return 'local';
    } else if (hostname.includes('onrender.com')) {
        return 'render';
    } else if (hostname.includes('github.io')) {
        // Sprawdź czy backend jest dostępny
        return 'github_heroku'; // lub 'github_railway' lub 'demo'
    } else {
        return 'local';
    }
}

// 📝 Eksportuj konfigurację dla aktualnego środowiska
const CURRENT_ENV = detectEnvironment();
const KRANIKBOT_CONFIG = ENVIRONMENTS[CURRENT_ENV];

// 🔍 Debug info
console.log(`🌐 KranikBot Web Panel`);
console.log(`📍 Environment: ${CURRENT_ENV}`);
console.log(`🔗 API URL: ${KRANIKBOT_CONFIG.API_BASE_URL}`);
console.log(`🧪 Demo Mode: ${KRANIKBOT_CONFIG.DEMO_MODE}`);

// Sprawdź czy config.js jest załadowany przed script.js
if (typeof window !== 'undefined') {
    window.KRANIKBOT_CONFIG = KRANIKBOT_CONFIG;
    window.KRANIKBOT_ENV = CURRENT_ENV;
}