// KranikBot Web Panel Configuration for GitHub Pages
window.KRANIKBOT_CONFIG = {
    // GitHub Pages configuration (connected to Render API)
    API_BASE_URL: 'https://kranikbot-api.onrender.com',
    API_KEY: 'kranikbot-secure-key-2024',
    DEMO_MODE: false,
    
    // Environment detection
    ENVIRONMENT: 'github_pages',
    
    // Demo data for GitHub Pages
    DEMO_DATA: {
        twitch_bot: {
            status: 'running',
            uptime: '2h 15m',
            last_restart: '2025-01-05 18:30:00'
        },
        discord_bot: {
            status: 'running', 
            uptime: '1h 45m',
            last_restart: '2025-01-05 19:00:00'
        },
        stats: {
            total_messages: 1247,
            commands_executed: 89,
            users_helped: 23,
            uptime_hours: 156
        }
    }
};

console.log('🌐 KranikBot Web Panel - GitHub Pages Mode');
console.log('📊 Demo mode enabled - showing sample data');