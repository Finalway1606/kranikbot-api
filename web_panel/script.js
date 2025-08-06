// Konfiguracja - używa config.js
// CONFIG jest dostępny jako window.KRANIKBOT_CONFIG z config.js

// Globalne zmienne
let serverUrl = 'http://localhost:5000';
let apiKey = '';
let autoRefreshInterval = null;
let isConnected = false;

// Inicjalizacja po załadowaniu strony
document.addEventListener('DOMContentLoaded', function() {
    loadSettings();
    initializeApp();
    setupEventListeners();
});

// Inicjalizacja aplikacji
function initializeApp() {
    updateConnectionStatus('connecting', 'Łączenie...');
    checkServerConnection();
    startAutoRefresh();
}

// Konfiguracja event listenerów
function setupEventListeners() {
    // Auto-refresh checkbox
    document.getElementById('autoRefresh').addEventListener('change', function() {
        if (this.checked) {
            startAutoRefresh();
        } else {
            stopAutoRefresh();
        }
    });

    // Refresh interval change
    document.getElementById('refreshInterval').addEventListener('change', function() {
        if (document.getElementById('autoRefresh').checked) {
            startAutoRefresh();
        }
    });

    // Ranking limit change
    const rankingLimit = document.getElementById('rankingLimit');
    if (rankingLimit) {
        rankingLimit.addEventListener('change', function() {
            // Auto-refresh ranking when limit changes
            if (document.getElementById('rankingTab').classList.contains('active')) {
                refreshRanking();
            }
        });
    }
}

// Zarządzanie połączeniem z serwerem
async function checkServerConnection() {
    try {
        const response = await fetch(`${serverUrl}/api/status`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${apiKey}`
            },
            timeout: 5000
        });

        if (response.ok) {
            isConnected = true;
            updateConnectionStatus('connected', 'Połączono');
            await refreshAllData();
        } else {
            throw new Error(`HTTP ${response.status}`);
        }
    } catch (error) {
        isConnected = false;
        updateConnectionStatus('disconnected', 'Brak połączenia');
        console.error('Connection error:', error);
        
        // Fallback - symulacja danych dla demo
        simulateOfflineMode();
    }
}

// Aktualizacja statusu połączenia
function updateConnectionStatus(status, text) {
    const indicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');
    
    indicator.className = `status-indicator ${status}`;
    statusText.textContent = text;
}

// Symulacja trybu offline dla demo
function simulateOfflineMode() {
    addLog('warning', '⚠️ Tryb demo - brak połączenia z serwerem');
    
    // Symulowane dane
    updateBotStatus('twitch', 'offline', null, '00:00:00');
    updateBotStatus('discord', 'offline', null, '00:00:00');
    
    // Symulowane statystyki
    document.getElementById('twitchFollowers').textContent = '1,234';
    document.getElementById('twitchSubs').textContent = '56';
    document.getElementById('twitchVips').textContent = '12';
    document.getElementById('twitchMods').textContent = '8';
    document.getElementById('totalUsers').textContent = '2,345';
    document.getElementById('totalPoints').textContent = '123,456';
    document.getElementById('topUser').textContent = 'KranikUser';
}

// Funkcje kontroli botów
async function startTwitchBot() {
    await executeAction('start_twitch', 'Uruchamianie Twitch Bot...');
}

async function stopTwitchBot() {
    await executeAction('stop_twitch', 'Zatrzymywanie Twitch Bot...');
}

async function restartTwitchBot() {
    await executeAction('restart_twitch', 'Restartowanie Twitch Bot...');
}

async function startDiscordBot() {
    await executeAction('start_discord', 'Uruchamianie Discord Bot...');
}

async function stopDiscordBot() {
    await executeAction('stop_discord', 'Zatrzymywanie Discord Bot...');
}

async function restartDiscordBot() {
    await executeAction('restart_discord', 'Restartowanie Discord Bot...');
}

async function startAllBots() {
    showLoading();
    addLog('info', '🚀 Uruchamianie wszystkich botów...');
    
    try {
        await startTwitchBot();
        await new Promise(resolve => setTimeout(resolve, 1000));
        await startDiscordBot();
        showNotification('success', '✅ Wszystkie boty zostały uruchomione');
    } catch (error) {
        showNotification('error', '❌ Błąd podczas uruchamiania botów');
    } finally {
        hideLoading();
    }
}

async function stopAllBots() {
    showLoading();
    addLog('info', '🛑 Zatrzymywanie wszystkich botów...');
    
    try {
        await stopTwitchBot();
        await new Promise(resolve => setTimeout(resolve, 1000));
        await stopDiscordBot();
        showNotification('success', '✅ Wszystkie boty zostały zatrzymane');
    } catch (error) {
        showNotification('error', '❌ Błąd podczas zatrzymywania botów');
    } finally {
        hideLoading();
    }
}

async function restartAllBots() {
    showLoading();
    addLog('info', '🔄 Restartowanie wszystkich botów...');
    
    try {
        await restartTwitchBot();
        await new Promise(resolve => setTimeout(resolve, 1000));
        await restartDiscordBot();
        showNotification('success', '✅ Wszystkie boty zostały zrestartowane');
    } catch (error) {
        showNotification('error', '❌ Błąd podczas restartowania botów');
    } finally {
        hideLoading();
    }
}

// Wykonywanie akcji na serwerze
async function executeAction(action, message) {
    if (!isConnected) {
        // Symulacja dla trybu demo
        simulateAction(action, message);
        return;
    }

    showLoading();
    addLog('info', message);

    try {
        const response = await fetch(`${serverUrl}/api/action`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${apiKey}`
            },
            body: JSON.stringify({ action: action })
        });

        const result = await response.json();

        if (response.ok) {
            addLog('success', `✅ ${result.message}`);
            showNotification('success', result.message);
            await refreshAllData();
        } else {
            throw new Error(result.error || 'Nieznany błąd');
        }
    } catch (error) {
        addLog('error', `❌ Błąd: ${error.message}`);
        showNotification('error', `Błąd: ${error.message}`);
    } finally {
        hideLoading();
    }
}

// Symulacja akcji dla trybu demo
function simulateAction(action, message) {
    showLoading();
    addLog('info', `[DEMO] ${message}`);

    setTimeout(() => {
        const isStart = action.includes('start');
        const isStop = action.includes('stop');
        const isRestart = action.includes('restart');
        const botType = action.includes('twitch') ? 'twitch' : 'discord';

        if (isStart) {
            updateBotStatus(botType, 'online', Math.floor(Math.random() * 10000), '00:00:01');
            addLog('success', `✅ [DEMO] ${botType.toUpperCase()} Bot uruchomiony`);
            showNotification('success', `${botType.toUpperCase()} Bot uruchomiony (demo)`);
        } else if (isStop) {
            updateBotStatus(botType, 'offline', null, '00:00:00');
            addLog('success', `✅ [DEMO] ${botType.toUpperCase()} Bot zatrzymany`);
            showNotification('success', `${botType.toUpperCase()} Bot zatrzymany (demo)`);
        } else if (isRestart) {
            updateBotStatus(botType, 'starting', null, '00:00:00');
            addLog('info', `🔄 [DEMO] ${botType.toUpperCase()} Bot restartowanie...`);
            
            setTimeout(() => {
                updateBotStatus(botType, 'online', Math.floor(Math.random() * 10000), '00:00:01');
                addLog('success', `✅ [DEMO] ${botType.toUpperCase()} Bot zrestartowany`);
                showNotification('success', `${botType.toUpperCase()} Bot zrestartowany (demo)`);
            }, 2000);
        }

        hideLoading();
    }, 1000);
}

// Aktualizacja statusu bota
function updateBotStatus(botType, status, pid, uptime) {
    const statusElement = document.getElementById(`${botType}Status`);
    const pidElement = document.getElementById(`${botType}Pid`);
    const uptimeElement = document.getElementById(`${botType}Uptime`);

    // Aktualizuj status
    const statusDot = statusElement.querySelector('.status-dot');
    const statusText = statusElement.querySelector('span:last-child');

    statusDot.className = `status-dot ${status}`;
    
    switch (status) {
        case 'online':
            statusText.textContent = 'Online';
            break;
        case 'offline':
            statusText.textContent = 'Offline';
            break;
        case 'starting':
            statusText.textContent = 'Uruchamianie...';
            break;
        default:
            statusText.textContent = 'Nieznany';
    }

    // Aktualizuj PID i uptime
    pidElement.textContent = pid || '-';
    uptimeElement.textContent = uptime || '-';
}

// Odświeżanie danych
async function refreshAllData() {
    await Promise.all([
        refreshBotStatus(),
        refreshStats()
    ]);
    
    document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
}

async function refreshBotStatus() {
    if (!isConnected) return;

    try {
        const response = await fetch(`${serverUrl}/api/bots/status`, {
            headers: {
                'Authorization': `Bearer ${apiKey}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            updateBotStatus('twitch', data.twitch.status, data.twitch.pid, data.twitch.uptime);
            updateBotStatus('discord', data.discord.status, data.discord.pid, data.discord.uptime);
        }
    } catch (error) {
        console.error('Error refreshing bot status:', error);
    }
}

async function refreshStats() {
    if (!isConnected) return;

    try {
        const response = await fetch(`${serverUrl}/api/stats`, {
            headers: {
                'Authorization': `Bearer ${apiKey}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            
            // Aktualizuj statystyki Twitch
            document.getElementById('twitchFollowers').textContent = data.twitch.followers || 'N/A';
            document.getElementById('twitchSubs').textContent = data.twitch.subscribers || 'N/A';
            
            // Aktualizuj liczby VIPów i moderatorów
            const vipCount = Array.isArray(data.twitch.vips) ? data.twitch.vips.length : (data.twitch.vips || 0);
            const modCount = Array.isArray(data.twitch.moderators) ? data.twitch.moderators.length : (data.twitch.moderators || 0);
            
            document.getElementById('twitchVips').textContent = vipCount;
            document.getElementById('twitchMods').textContent = modCount;
            
            // Aktualizuj listy VIPów i moderatorów
            updateUserList('vipList', data.twitch.vips, 'vip');
            updateUserList('modList', data.twitch.moderators, 'mod');
            
            // Aktualizuj statystyki bazy danych
            document.getElementById('totalUsers').textContent = data.database.total_users || 'N/A';
            document.getElementById('totalPoints').textContent = data.database.total_points || 'N/A';
            document.getElementById('topUser').textContent = data.database.top_user || 'N/A';
        }
    } catch (error) {
        console.error('Error refreshing stats:', error);
    }
}

// Funkcja do aktualizacji list użytkowników (VIPy, moderatorzy)
function updateUserList(elementId, users, type) {
    const listElement = document.getElementById(elementId);
    
    if (!listElement) return;
    
    if (!users || !Array.isArray(users) || users.length === 0) {
        listElement.innerHTML = '<div class="no-users">Brak użytkowników</div>';
        return;
    }
    
    const badgeClass = type === 'vip' ? 'vip-badge' : 'mod-badge';
    const icon = type === 'vip' ? '💎' : '🛡️';
    
    listElement.innerHTML = users.map(user => `
        <div class="user-item">
            <span class="badge ${badgeClass}">${icon}</span>
            <span class="username">${user}</span>
        </div>
    `).join('');
}

function refreshStatus() {
    addLog('info', '🔄 Odświeżanie statusu...');
    checkServerConnection();
}

// Auto-refresh
function startAutoRefresh() {
    stopAutoRefresh();
    
    const interval = parseInt(document.getElementById('refreshInterval').value) * 1000;
    autoRefreshInterval = setInterval(() => {
        if (isConnected) {
            refreshAllData();
        } else {
            checkServerConnection();
        }
    }, interval);
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

// Zarządzanie zakładkami
function showTab(tabName) {
    // Ukryj wszystkie zakładki
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(tab => tab.classList.remove('active'));

    // Usuń aktywną klasę z przycisków
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(btn => btn.classList.remove('active'));

    // Pokaż wybraną zakładkę
    document.getElementById(`${tabName}Tab`).classList.add('active');
    
    // Dodaj aktywną klasę do przycisku
    event.target.classList.add('active');

    // Specjalne akcje dla konkretnych zakładek
    if (tabName === 'logs') {
        refreshLogs();
    } else if (tabName === 'ranking') {
        refreshRanking();
    }
}

// Funkcje zarządzania punktami użytkowników
async function addUserPoints() {
    const username = document.getElementById('addPointsUsername').value.trim();
    const points = parseInt(document.getElementById('addPointsAmount').value);
    
    if (!username) {
        showNotification('error', '❌ Wprowadź nazwę użytkownika');
        return;
    }
    
    if (!points || points <= 0) {
        showNotification('error', '❌ Wprowadź prawidłową liczbę punktów');
        return;
    }
    
    if (!isConnected) {
        showNotification('warning', '⚠️ Brak połączenia z serwerem');
        return;
    }
    
    showLoading();
    addLog('info', `💰 Dodawanie ${points} punktów użytkownikowi ${username}...`);
    
    try {
        const response = await fetch(`${serverUrl}/api/users/points/add`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${apiKey}`
            },
            body: JSON.stringify({
                username: username,
                points: points
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showNotification('success', `✅ ${result.message}`);
            addLog('success', `✅ ${result.message} (łącznie: ${result.total_points})`);
            
            // Wyczyść formularz
            document.getElementById('addPointsUsername').value = '';
            document.getElementById('addPointsAmount').value = '';
            
            // Odśwież statystyki
            await refreshAllData();
        } else {
            throw new Error(result.error || 'Nieznany błąd');
        }
    } catch (error) {
        showNotification('error', `❌ Błąd: ${error.message}`);
        addLog('error', `❌ Błąd dodawania punktów: ${error.message}`);
    } finally {
        hideLoading();
    }
}

async function removeUserPoints() {
    const username = document.getElementById('removePointsUsername').value.trim();
    const points = parseInt(document.getElementById('removePointsAmount').value) || 0;
    
    if (!username) {
        showNotification('error', '❌ Wprowadź nazwę użytkownika');
        return;
    }
    
    if (!isConnected) {
        showNotification('warning', '⚠️ Brak połączenia z serwerem');
        return;
    }
    
    const action = points === 0 ? 'wszystkich punktów' : `${points} punktów`;
    
    showLoading();
    addLog('info', `💸 Usuwanie ${action} użytkownikowi ${username}...`);
    
    try {
        const response = await fetch(`${serverUrl}/api/users/points/remove`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${apiKey}`
            },
            body: JSON.stringify({
                username: username,
                points: points
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showNotification('success', `✅ ${result.message}`);
            addLog('success', `✅ ${result.message} (pozostało: ${result.total_points})`);
            
            // Wyczyść formularz
            document.getElementById('removePointsUsername').value = '';
            document.getElementById('removePointsAmount').value = '';
            
            // Odśwież statystyki
            await refreshAllData();
        } else {
            throw new Error(result.error || 'Nieznany błąd');
        }
    } catch (error) {
        showNotification('error', `❌ Błąd: ${error.message}`);
        addLog('error', `❌ Błąd usuwania punktów: ${error.message}`);
    } finally {
        hideLoading();
    }
}

async function searchUser() {
    const username = document.getElementById('userSearch').value.trim();
    const resultDiv = document.getElementById('userSearchResult');
    
    if (!username) {
        showNotification('error', '❌ Wprowadź nazwę użytkownika');
        return;
    }
    
    if (!isConnected) {
        resultDiv.innerHTML = '<div class="loading">⚠️ Brak połączenia z serwerem</div>';
        return;
    }
    
    resultDiv.innerHTML = '<div class="loading">🔍 Szukanie...</div>';
    
    try {
        // Symulacja wyszukiwania - w rzeczywistości potrzebowałby endpoint do wyszukiwania
        // Na razie pokażemy przykładowe dane
        setTimeout(() => {
            resultDiv.innerHTML = `
                <div class="user-info">
                    <h4>👤 ${username}</h4>
                    <div class="stat-row">
                        <span>💰 Punkty:</span>
                        <span>1,234</span>
                    </div>
                    <div class="stat-row">
                        <span>💬 Wiadomości:</span>
                        <span>567</span>
                    </div>
                    <div class="stat-row">
                        <span>📅 Ostatnio widziany:</span>
                        <span>2024-01-15 14:30</span>
                    </div>
                    <div class="stat-row">
                        <span>👥 Status:</span>
                        <span>Follower</span>
                    </div>
                </div>
            `;
        }, 1000);
        
    } catch (error) {
        resultDiv.innerHTML = `<div class="loading">❌ Błąd wyszukiwania: ${error.message}</div>`;
    }
}

// Zarządzanie logami
function addLog(type, message) {
    const logsContent = document.getElementById('logsContent');
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${type}`;
    
    const time = new Date().toLocaleTimeString();
    logEntry.innerHTML = `
        <span class="log-time">[${time}]</span>
        <span class="log-message">${message}</span>
    `;
    
    logsContent.appendChild(logEntry);
    logsContent.scrollTop = logsContent.scrollHeight;

    // Ogranicz liczbę logów do 100
    const logs = logsContent.querySelectorAll('.log-entry');
    if (logs.length > 100) {
        logs[0].remove();
    }
}

function clearLogs() {
    document.getElementById('logsContent').innerHTML = '';
    addLog('info', '🗑️ Logi zostały wyczyszczone');
}

function refreshLogs() {
    addLog('info', '🔄 Odświeżanie logów...');
    // W rzeczywistej implementacji tutaj byłoby pobieranie logów z serwera
}

// Zarządzanie ustawieniami
function loadSettings() {
    // Użyj window.KRANIKBOT_CONFIG z config.js jako domyślne wartości
    const config = window.KRANIKBOT_CONFIG || {
        API_BASE_URL: 'http://localhost:5000/api',
        API_KEY: 'kranikbot-secure-key-2024'
    };
    const defaultUrl = config.API_BASE_URL.replace('/api', '');
    const defaultApiKey = config.API_KEY;
    
    const savedUrl = localStorage.getItem('kranikbot_server_url') || defaultUrl;
    const savedApiKey = localStorage.getItem('kranikbot_api_key') || defaultApiKey;
    const savedRefreshInterval = localStorage.getItem('kranikbot_refresh_interval') || '5';
    const savedAutoRefresh = localStorage.getItem('kranikbot_auto_refresh');

    serverUrl = savedUrl;
    document.getElementById('serverUrl').value = savedUrl;

    apiKey = savedApiKey;
    document.getElementById('apiKey').value = savedApiKey;

    document.getElementById('refreshInterval').value = savedRefreshInterval;

    if (savedAutoRefresh !== null) {
        document.getElementById('autoRefresh').checked = savedAutoRefresh === 'true';
    } else {
        document.getElementById('autoRefresh').checked = true; // domyślnie włączone
    }
}

function saveSettings() {
    serverUrl = document.getElementById('serverUrl').value;
    apiKey = document.getElementById('apiKey').value;
    const refreshInterval = document.getElementById('refreshInterval').value;
    const autoRefresh = document.getElementById('autoRefresh').checked;

    localStorage.setItem('kranikbot_server_url', serverUrl);
    localStorage.setItem('kranikbot_api_key', apiKey);
    localStorage.setItem('kranikbot_refresh_interval', refreshInterval);
    localStorage.setItem('kranikbot_auto_refresh', autoRefresh.toString());

    showNotification('success', '💾 Ustawienia zostały zapisane');
    addLog('success', '💾 Ustawienia zostały zapisane');

    // Sprawdź połączenie z nowym URL
    checkServerConnection();
    
    // Restart auto-refresh z nowym interwałem
    if (autoRefresh) {
        startAutoRefresh();
    }
}

// UI Helper functions
function showLoading() {
    document.getElementById('loadingOverlay').classList.add('show');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('show');
}

function showNotification(type, message) {
    const container = document.getElementById('notificationContainer');
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    container.appendChild(notification);
    
    // Auto-remove po 5 sekundach
    setTimeout(() => {
        notification.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 5000);
    
    // Kliknięcie usuwa notyfikację
    notification.addEventListener('click', () => {
        notification.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    });
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl + R - Refresh
    if (e.ctrlKey && e.key === 'r') {
        e.preventDefault();
        refreshStatus();
    }
    
    // Ctrl + 1-3 - Switch tabs
    if (e.ctrlKey && e.key >= '1' && e.key <= '3') {
        e.preventDefault();
        const tabs = ['stats', 'logs', 'settings'];
        const tabIndex = parseInt(e.key) - 1;
        if (tabs[tabIndex]) {
            showTab(tabs[tabIndex]);
        }
    }
});

// 🔒 Funkcja wylogowania
function logout() {
    if (confirm('Czy na pewno chcesz się wylogować?')) {
        // Usuń dane autoryzacji
        localStorage.removeItem('kranikbot_auth');
        sessionStorage.removeItem('kranikbot_auth');
        
        // Przekieruj do strony logowania
        window.location.href = 'login.html';
    }
}

// Funkcje rankingu
async function refreshRanking() {
    const rankingContent = document.getElementById('rankingContent');
    const rankingLastUpdate = document.getElementById('rankingLastUpdate');
    const limit = document.getElementById('rankingLimit').value;
    
    if (!isConnected) {
        showNotification('warning', '⚠️ Brak połączenia z serwerem');
        return;
    }
    
    // Pokaż komunikat o odświeżaniu
    rankingContent.innerHTML = '<div class="loading">🔄 Odświeżanie rankingu...</div>';
    addLog('info', '🏆 Odświeżanie rankingu użytkowników...');
    
    try {
        const response = await fetch(`${serverUrl}/api/users/ranking?limit=${limit}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${apiKey}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            
            if (data.success && data.ranking && data.ranking.length > 0) {
                // Pokaż komunikat sukcesu
                const successMessage = document.createElement('div');
                successMessage.className = 'ranking-success';
                successMessage.textContent = `✅ Ranking odświeżony pomyślnie! Znaleziono ${data.ranking.length} użytkowników.`;
                
                // Utwórz tabelę rankingu
                const tableHTML = `
                    <table class="ranking-table">
                        <thead>
                            <tr>
                                <th>Pozycja</th>
                                <th>Użytkownik</th>
                                <th>Punkty</th>
                                <th>Wiadomości</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.ranking.map(user => {
                                let positionClass = 'ranking-position';
                                if (user.position === 1) positionClass += ' top-1';
                                else if (user.position === 2) positionClass += ' top-2';
                                else if (user.position === 3) positionClass += ' top-3';
                                
                                return `
                                    <tr>
                                        <td class="${positionClass}">${user.position}</td>
                                        <td class="ranking-username">${user.username}</td>
                                        <td class="ranking-points">${user.points.toLocaleString()}</td>
                                        <td class="ranking-messages">${user.messages}</td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                `;
                
                rankingContent.innerHTML = '';
                rankingContent.appendChild(successMessage);
                rankingContent.innerHTML += tableHTML;
                
                // Usuń komunikat sukcesu po 3 sekundach
                setTimeout(() => {
                    if (successMessage.parentNode) {
                        successMessage.remove();
                    }
                }, 3000);
                
                // Aktualizuj czas ostatniego odświeżenia
                rankingLastUpdate.textContent = new Date().toLocaleTimeString();
                
                showNotification('success', `✅ Ranking odświeżony! Pokazano top ${data.ranking.length} użytkowników`);
                addLog('success', `✅ Ranking odświeżony pomyślnie (${data.ranking.length} użytkowników)`);
                
            } else {
                rankingContent.innerHTML = '<div class="ranking-empty">📭 Brak użytkowników w rankingu</div>';
                showNotification('info', 'ℹ️ Brak użytkowników w rankingu');
                addLog('info', 'ℹ️ Ranking jest pusty');
            }
        } else {
            throw new Error(`HTTP ${response.status}`);
        }
        
    } catch (error) {
        rankingContent.innerHTML = `<div class="ranking-empty">❌ Błąd ładowania rankingu: ${error.message}</div>`;
        showNotification('error', `❌ Błąd odświeżania rankingu: ${error.message}`);
        addLog('error', `❌ Błąd odświeżania rankingu: ${error.message}`);
    }
}

// Inicjalizacja logów
addLog('info', '🚀 Web Panel KranikBot uruchomiony');
addLog('info', '🔗 Sprawdzanie połączenia z serwerem...');