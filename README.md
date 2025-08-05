# 🚂 KranikBot Railway Deployment

Backend API dla KranikBot Web Panel hostowany na Railway.app

## 🚀 Funkcje

- **🌐 Web API**: RESTful API do kontroli botów
- **🤖 Bot Management**: Uruchamianie/zatrzymywanie botów Twitch i Discord
- **📊 Monitoring**: Status i statystyki w czasie rzeczywistym
- **🔒 Bezpieczeństwo**: Autoryzacja przez API key

## 📁 Struktura

```
├── web_api_server.py      # Główny serwer API
├── testBot.py             # Bot Twitch
├── discord_bot_standalone.py  # Bot Discord
├── database.py            # Obsługa bazy danych
├── web_panel/             # Pliki frontend
├── requirements.txt       # Zależności Python
├── Procfile              # Konfiguracja Railway
└── runtime.txt           # Wersja Python
```

## 🔧 Deployment na Railway

1. **Fork/Upload** tego repozytorium na GitHub
2. **Połącz** Railway z GitHub
3. **Deploy** z tego repozytorium
4. **Ustaw zmienne środowiskowe** (opcjonalnie)

## 🌐 Endpoints

- `GET /` - Strona główna
- `GET /web` - Web Panel
- `GET /api/status` - Status API
- `GET /api/bots/status` - Status botów
- `POST /api/action` - Akcje na botach

## 🔑 API Key

Domyślny klucz: `kranikbot_2025_secure_key`

**⚠️ W produkcji ustaw zmienną środowiskową `API_KEY`**

## 🎯 Użycie

Po deployment URL będzie dostępny pod:
- **API**: `https://twoja-app.railway.app/api/status`
- **Web Panel**: `https://twoja-app.railway.app/web`

---

**🤖 KranikBot - Profesjonalne zarządzanie botami**