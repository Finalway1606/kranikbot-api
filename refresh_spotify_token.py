#!/usr/bin/env python3
"""
Skrypt do ręcznego odświeżenia tokenu Spotify
"""

import os
import json
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

# Załaduj zmienne środowiskowe
load_dotenv()

def refresh_spotify_token():
    """Odświeża token Spotify"""
    
    # Pobierz konfigurację Spotify
    spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID")
    spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    spotify_redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
    
    if not spotify_client_id or not spotify_client_secret:
        print("❌ Brak konfiguracji Spotify w pliku .env")
        return False
    
    print(f"🔧 Konfiguracja Spotify:")
    print(f"   Client ID: {spotify_client_id}")
    print(f"   Redirect URI: {spotify_redirect_uri}")
    
    # Inicjalizuj SpotifyOAuth
    sp_oauth = SpotifyOAuth(
        client_id=spotify_client_id,
        client_secret=spotify_client_secret,
        redirect_uri=spotify_redirect_uri,
        scope="user-modify-playback-state user-read-playback-state",
        open_browser=True
    )
    
    try:
        # Sprawdź czy istnieje cache
        cache_file = ".cache"
        if os.path.exists(cache_file):
            print(f"📁 Znaleziono plik cache: {cache_file}")
            
            # Wczytaj obecny token
            with open(cache_file, 'r') as f:
                token_info = json.load(f)
            
            print(f"🔍 Obecny token:")
            print(f"   Expires at: {token_info.get('expires_at', 'N/A')}")
            print(f"   Has refresh token: {'refresh_token' in token_info}")
            
            # Sprawdź czy token wygasł
            if sp_oauth.is_token_expired(token_info):
                print(f"⏰ Token wygasł - próbuję odświeżyć...")
                
                if 'refresh_token' in token_info:
                    # Odśwież token
                    new_token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
                    print(f"✅ Token odświeżony pomyślnie!")
                    print(f"   Nowy expires_at: {new_token_info.get('expires_at', 'N/A')}")
                    
                    # Testuj nowy token
                    sp = spotipy.Spotify(auth=new_token_info['access_token'])
                    user = sp.current_user()
                    print(f"🎵 Połączono z kontem Spotify: {user['display_name']}")
                    
                    return True
                else:
                    print(f"❌ Brak refresh_token - wymagana ponowna autoryzacja")
                    return False
            else:
                print(f"✅ Token jest aktualny")
                
                # Testuj obecny token
                sp = spotipy.Spotify(auth=token_info['access_token'])
                user = sp.current_user()
                print(f"🎵 Połączono z kontem Spotify: {user['display_name']}")
                
                return True
        else:
            print(f"❌ Brak pliku cache - wymagana autoryzacja")
            
            # Rozpocznij nową autoryzację
            print(f"🔑 Rozpoczynam autoryzację Spotify...")
            auth_url = sp_oauth.get_authorize_url()
            print(f"🌐 Otwórz w przeglądarce: {auth_url}")
            
            # Pobierz token
            token_info = sp_oauth.get_access_token()
            if token_info:
                print(f"✅ Autoryzacja zakończona pomyślnie!")
                
                # Testuj token
                sp = spotipy.Spotify(auth=token_info['access_token'])
                user = sp.current_user()
                print(f"🎵 Połączono z kontem Spotify: {user['display_name']}")
                
                return True
            else:
                print(f"❌ Nie udało się uzyskać tokenu")
                return False
                
    except Exception as e:
        print(f"❌ Błąd podczas odświeżania tokenu: {e}")
        return False

if __name__ == "__main__":
    print(f"🎵 Spotify Token Refresh Tool")
    print(f"=" * 40)
    
    success = refresh_spotify_token()
    
    if success:
        print(f"\n✅ Token Spotify został pomyślnie odświeżony!")
        print(f"🤖 Możesz teraz uruchomić bota ponownie")
    else:
        print(f"\n❌ Nie udało się odświeżyć tokenu Spotify")
        print(f"🔧 Sprawdź konfigurację w pliku .env")