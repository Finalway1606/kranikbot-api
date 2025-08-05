import irc.client
import threading
import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import random
import sys
import os
import asyncio
from dotenv import load_dotenv
import requests
import json
from datetime import datetime, timedelta

# Konfiguracja kodowania dla Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def safe_print(text):
    """Bezpieczne drukowanie z obsługą emoji na Windows"""
    try:
        print(text, flush=True)
    except UnicodeEncodeError:
        # Zamień emoji na tekst jeśli nie można ich wyświetlić
        safe_text = text.encode('ascii', 'replace').decode('ascii')
        print(safe_text, flush=True)
    except Exception as e:
        # Fallback - wydrukuj bez emoji
        try:
            clean_text = ''.join(char for char in text if ord(char) < 128)
            print(f"[LOG] {clean_text}", flush=True)
        except:
            print(f"[LOG] Message encoding error", flush=True)

from reminders import ZBIORKA_MSG, DISCORD_MSG, FOLLOW_MSG, PRIME_MSG, BITS_MSG
from motywacja import MOTYWACYJNE_CYTATY
from database import UserDatabase
from games import MiniGames
from shop import Shop
from discord_integration import DiscordIntegration
from discord_bot import DiscordBot

# Ładowanie zmiennych środowiskowych
load_dotenv()

# === KONFIGURACJA FOLLOWÓW ===
FOLLOW_THANKS_ENABLED = True
FOLLOW_THANKS_MESSAGES = [
    "🎉 Dziękuję za follow, @{username}! Miło Cię widzieć w społeczności! 💜",
    "💜 Witaj w rodzinie, @{username}! Dzięki za follow! 🎉",
    "🔥 @{username} dołączył do nas! Dziękuję za follow! 💜",
    "✨ Nowy follower! Witaj @{username}, dziękuję za wsparcie! 🎉",
    "🎊 @{username} właśnie nas obserwuje! Dzięki za follow! 💜"
]

# === KONFIGURACJA SUBSKRYPCJI ===
SUB_THANKS_ENABLED = True
SUB_THANKS_MESSAGES = [
    "🌟 DZIĘKUJĘ ZA SUB, @{username}! Jesteś niesamowity! 💜✨",
    "🎊 @{username} właśnie zasubskrybował! OGROMNE DZIĘKI! 🔥💜",
    "💎 SUB od @{username}! To znaczy dla mnie bardzo wiele! 🙏💜",
    "🚀 @{username} dołączył do subów! Jesteś wspaniały! 🎉💜",
    "⭐ NOWY SUB! Dziękuję @{username} za niesamowite wsparcie! 💜🎊"
]

# KONFIGURACJA TWITCH
TWITCH_SERVER = "irc.chat.twitch.tv"
TWITCH_PORT = 6667
NICKNAME = os.getenv("TWITCH_NICKNAME", "KranikBot")
TOKEN = os.getenv("TWITCH_TOKEN")
CHANNEL = os.getenv("TWITCH_CHANNEL")

# Dynamiczne listy uprawnień - będą pobierane z Twitch API
# Zamiast hardkodowanych list używamy pustych setów, które będą wypełniane automatycznie

SONG_REQUEST_TIMEOUT = int(os.getenv("SONG_REQUEST_TIMEOUT", "300"))

class TwitchBot:
    def __init__(self):
        # Sprawdzenie czy wszystkie wymagane zmienne są ustawione
        if not TOKEN:
            raise ValueError("TWITCH_TOKEN nie jest ustawiony w pliku .env")
        if not CHANNEL:
            raise ValueError("TWITCH_CHANNEL nie jest ustawiony w pliku .env")
        
        # Inicjalizacja IRC połączenia
        self.reactor = irc.client.Reactor()
        self.connection = self.reactor.server().connect(TWITCH_SERVER, TWITCH_PORT, NICKNAME, password=TOKEN)
        self.connection.add_global_handler("welcome", self.on_connect)
        self.connection.add_global_handler("pubmsg", self.on_message)
        self.connection.add_global_handler("usernotice", self.on_usernotice)

        # Spotify konfiguracja z zmiennych środowiskowych
        spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID")
        spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        spotify_redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
        
        # Zawsze inicjalizuj podstawowe atrybuty Spotify
        self.pending_song_requests = {}
        self.last_request_time = {}
        self.spotify_enabled = False
        self.sp = None
        self.token_info = None
        self.sp_oauth = None
        
        if not spotify_client_id or not spotify_client_secret:
            safe_print(f"⚠️ Brak konfiguracji Spotify - moduł będzie wyłączony")
        else:
            try:
                self.sp_oauth = SpotifyOAuth(
                    client_id=spotify_client_id,
                    client_secret=spotify_client_secret,
                    redirect_uri=spotify_redirect_uri,
                    scope="user-modify-playback-state user-read-playback-state",
                    open_browser=True
                )
                
                # Inicjalizacja Spotify z lepszą obsługą tokenów
                token_info = self.sp_oauth.get_cached_token()
                if token_info:
                    safe_print(f"✅ Znaleziono zapisane tokeny Spotify")
                    self.token_info = token_info
                    self.sp = spotipy.Spotify(auth=token_info['access_token'])
                    self.spotify_enabled = True
                else:
                    safe_print(f"🔑 Rozpoczynam autoryzację Spotify...")
                    safe_print(f"📱 Otworzę przeglądarkę - zaloguj się i autoryzuj aplikację")
                    # Używamy get_cached_token zamiast deprecated get_access_token
                    auth_url = self.sp_oauth.get_authorize_url()
                    safe_print(f"🌐 Jeśli przeglądarka się nie otworzy, idź na: {auth_url}")
                    
                    # Pobieramy token bez deprecated parametru
                    token_info = self.sp_oauth.get_access_token()
                    if token_info:
                        self.token_info = token_info
                        self.sp = spotipy.Spotify(auth=token_info['access_token'])
                        self.spotify_enabled = True
                        safe_print(f"✅ Autoryzacja Spotify zakończona pomyślnie!")
                    else:
                        raise Exception("Nie udało się uzyskać tokenu Spotify")
                        
            except Exception as e:
                safe_print(f"❌ Błąd autoryzacji Spotify: {e}")
                safe_print(f"⚠️ Moduł Spotify będzie wyłączony")
                self.spotify_enabled = False
                self.sp = None
                self.token_info = None
        
        # Follow tracking
        self.follow_thanks_enabled = FOLLOW_THANKS_ENABLED
        self.last_followers = set()
        self.check_followers_thread = None
        
        # Subscription tracking
        self.sub_thanks_enabled = SUB_THANKS_ENABLED
        self.last_subscribers = set()
        self.check_subscribers_thread = None
        
        # Dynamiczne listy uprawnień
        self.moderators = set()
        self.vips = set()
        self.subscribers = set()
        self.trusted_users = {"kranik1606"}  # Właściciel zawsze ma uprawnienia
        self.subs_no_limit = {"kranik1606"}  # Właściciel zawsze ma unlimited
        self.allowed_skip = {"kranik1606"}   # Właściciel zawsze może skipować
        
        # Sprawdź konfigurację Twitch API
        if not os.getenv('TWITCH_CLIENT_ID') or not os.getenv('TWITCH_ACCESS_TOKEN'):
            safe_print(f"⚠️  Brak konfiguracji Twitch API - funkcje followów i subów wyłączone")
            safe_print(f"📖 Zobacz plik TWITCH_API_SETUP.md dla instrukcji")
            self.follow_thanks_enabled = False
            self.sub_thanks_enabled = False
        else:
            # Uruchom pierwsze pobieranie uprawnień
            self.update_permissions_on_startup()
        
        # Uruchom sprawdzanie followów i subów
        if self.follow_thanks_enabled:
            self.start_follow_checker()
        if self.sub_thanks_enabled:
            self.start_subscription_checker()
        
        # Inicjalizacja systemu gier i bazy danych
        self.db = UserDatabase()
        self.games = MiniGames(self.db, self)
        self.shop = Shop(self.db)
        self.discord = DiscordIntegration()
        safe_print(f"🎮 System gier i punktów zainicjalizowany!")
        safe_print(f"🛒 Sklep nagród zainicjalizowany!")
        safe_print(f"🔗 Integracja Discord zainicjalizowana!")
        
        # Inicjalizacja hash bez wysyłania wiadomości na Discord
        self.discord.initialize_leaderboard_hash(self.db)
        self.shop.initialize_shop_hash()
        safe_print(f"🔧 Zainicjalizowano hash rankingu i sklepu bez wysyłania wiadomości")
        
        # Inicjalizacja Discord bot z slash commands
        self.discord_bot = DiscordBot(self.db, self.discord, self.shop)
        if self.discord_bot.start_bot():
            safe_print(f"🤖 Discord bot z slash commands uruchomiony!")
        else:
            safe_print(f"⚠️ Discord bot z slash commands nie został uruchomiony")
        
        # Uruchom monitor statusu streama
        self.start_stream_monitor()
        
        # Uruchom dzienne statystyki Discord
        self.start_daily_stats()
        
        # Uruchom sprawdzanie timeout quizu
        self.start_quiz_timeout_checker()
        
        # Uruchom automatyczne aktualizacje Discord
        self.start_leaderboard_updater()
        
        # Uruchom monitor zmian w sklepie
        self.start_shop_monitor()

    def get_channel_name(self):
        """Zwraca poprawny format nazwy kanału z # na początku"""
        return CHANNEL if CHANNEL.startswith('#') else f"#{CHANNEL}"

    def ensure_token_valid(self):
        """Sprawdza i odświeża token Spotify jeśli to konieczne"""
        if not self.spotify_enabled or not self.token_info:
            return False
            
        try:
            if self.sp_oauth.is_token_expired(self.token_info):
                safe_print(f"🔄 Odświeżam token Spotify...")
                self.token_info = self.sp_oauth.refresh_access_token(self.token_info['refresh_token'])
                self.sp = spotipy.Spotify(auth=self.token_info['access_token'])
                safe_print(f"✅ Token Spotify odświeżony")
            return True
        except Exception as e:
            safe_print(f"❌ Błąd odświeżania tokenu Spotify: {e}")
            self.spotify_enabled = False
            return False

    def on_connect(self, connection, event):
        safe_print(f"✅ Połączono z Twitch IRC!")
        
        # Pobierz poprawny format nazwy kanału
        channel_name = self.get_channel_name()
        safe_print(f"🔗 Próbuję dołączyć do kanału: {channel_name}")
        
        # Żądaj capabilities aby otrzymywać tagi z USERNOTICE
        connection.cap("REQ", ":twitch.tv/tags")
        connection.cap("REQ", ":twitch.tv/commands")
        connection.join(channel_name)
        
        safe_print(f"📝 Wysyłam wiadomość powitalną...")
        # Wyślij wiadomość powitalną
        connection.privmsg(channel_name, "Robocik wbija bez pytania 🤖")
        safe_print(f"✅ Bot gotowy do pracy na kanale {channel_name}!")
        
        self.start_reminder()  # URUCHAMIAMY PRZYPOMNIENIA PO POŁĄCZENIU

    def on_message(self, connection, event):
        username = event.source.split("!")[0].lower()
        message = event.arguments[0].strip()
        channel_name = self.get_channel_name()
        
        # Ignoruj własne wiadomości bota
        if username == "kranikbot":
            return
        
        # Używamy dynamicznych list uprawnień zamiast hardkodowanych

        # Sprawdź czy użytkownik jest followerem
        is_follower = self.is_follower(username)
        
        # Dodaj punkty tylko za pierwszą wiadomość (10 pkt) - tylko dla followerów
        first_message_points = self.db.add_message(username, is_follower)
        if first_message_points > 0:
            connection.privmsg(channel_name, f"🎉 Witaj @{username}! Otrzymujesz {first_message_points} punktów za pierwszą wiadomość! Kolejne punkty zdobywasz grając w minigry.")
        elif not is_follower and first_message_points == 0:
            # Sprawdź czy to nowy użytkownik bez follow
            user = self.db.get_user(username)
            if user and user[2] == 1:  # messages_count == 1 (pierwsza wiadomość)
                connection.privmsg(channel_name, f"👋 Witaj @{username}! Aby zdobywać punkty, musisz zostać followerem kanału!")
        
        # Sprawdź codzienny bonus - tylko dla followerów
        if is_follower:
            bonus_msg = self.games.check_daily_bonus(username)
            if bonus_msg:
                connection.privmsg(channel_name, bonus_msg)

        # === KOMENDY GIER I PUNKTÓW ===
        if message == "!roll":
            result = self.games.roll_dice(username)
            connection.privmsg(channel_name, result)
            return

        elif message.startswith("!coinflip"):
            parts = message.split()
            choice = parts[1] if len(parts) > 1 else None
            result = self.games.coin_flip(username, choice)
            connection.privmsg(channel_name, result)
            return

        elif message.startswith("!roulette "):
            bet = message[len("!roulette "):].strip()
            result = self.games.roulette(username, bet)
            connection.privmsg(channel_name, result)
            return

        elif message == "!quiz":
            result = self.games.start_quiz()
            connection.privmsg(channel_name, result)
            return

        elif message.startswith("!answer "):
            answer = message[len("!answer "):].strip()
            result = self.games.answer_quiz(username, answer)
            connection.privmsg(channel_name, result)
            return

        elif message == "!daily":
            is_follower = self.is_follower(username)
            if not is_follower:
                connection.privmsg(channel_name, f"❌ @{username}, musisz być followerem kanału aby otrzymać dzienny bonus!")
                return
                
            success, bonus = self.db.daily_bonus(username, is_follower)
            if success and bonus > 0:
                result = f"🎁 @{username} otrzymał dzienny bonus: +{bonus} punktów!"
            else:
                result = f"❌ @{username}, już odebrałeś dzienny bonus! Spróbuj jutro."
            connection.privmsg(channel_name, result)
            return

        elif message == "!points":
            result = self.games.get_user_stats(username)
            connection.privmsg(channel_name, result)
            return

        elif message == "!top":
            result = self.games.get_leaderboard()
            connection.privmsg(channel_name, result)
            return

        elif message.startswith("!give "):
            parts = message.split()
            if len(parts) >= 3:
                to_user = parts[1].lstrip('@')
                points = parts[2]
                is_mod = username in self.trusted_users
                result = self.games.give_points(username, to_user, points, is_mod)
                connection.privmsg(channel_name, result)
            else:
                connection.privmsg(channel_name, f"@{username}, użyj: !give @user <punkty>")
            return

        # === KOMENDY SKLEPU ===
        elif message == "!shop":
            result = self.shop.get_shop_list()
            connection.privmsg(channel_name, result)
            return

        elif message.startswith("!kup "):
            reward_id = message[len("!kup "):].strip()
            result = self.shop.buy_reward(username, reward_id)
            connection.privmsg(channel_name, result)
            return

        elif message == "!inventory":
            result = self.shop.get_user_inventory(username)
            connection.privmsg(channel_name, result)
            return

        elif message.startswith("!daj "):
            if username.lower() == "kranik1606":  # Tylko właściciel
                parts = message[len("!daj "):].strip().split()
                if len(parts) >= 2:
                    target_user = parts[0].lstrip('@')
                    reward_id = parts[1]
                    result = self.shop.give_reward_as_owner(target_user, reward_id)
                    connection.privmsg(channel_name, result)
                else:
                    connection.privmsg(channel_name, f"@{username}, użyj: !daj @user <nagroda>")
            else:
                connection.privmsg(channel_name, f"❌ @{username}, tylko właściciel może dawać nagrody za darmo.")
            return

        elif message.startswith("!zabierz "):
            # Sprawdź uprawnienia - tylko właściciel i moderatorzy
            is_owner = username.lower() == "kranik1606"
            is_mod = username in self.trusted_users
            
            if not (is_owner or is_mod):
                connection.privmsg(channel_name, f"❌ @{username}, brak uprawnień do zabierania nagród.")
                return
            
            parts = message.split()
            if len(parts) >= 3:
                target_user = parts[1].lstrip('@')
                reward_id = parts[2]
                result = self.shop.remove_reward(target_user, reward_id)
                connection.privmsg(channel_name, f"🔨 @{username}: {result}")
            else:
                connection.privmsg(channel_name, f"@{username}, użyj: !zabierz @user <nagroda>")
            return

        elif message == "!resetall":
            if username.lower() == "kranik1606":  # Tylko właściciel
                # Resetuj wszystkie nagrody
                rewards_reset = self.shop.reset_all_rewards()
                # Resetuj wszystkie punkty
                points_reset = self.games.reset_all_points()
                
                connection.privmsg(channel_name, f"🔥 @{username} zresetował WSZYSTKO! Usunięto {rewards_reset} nagród i zresetowano punkty {points_reset} użytkowników.")
            else:
                connection.privmsg(channel_name, f"❌ @{username}, tylko właściciel może użyć tej komendy.")
            return

        # === KOMENDY SPOTIFY ===

        elif message == "!spotifyoff":
            if username in self.trusted_users:
                self.spotify_enabled = False
                connection.privmsg(channel_name, f"🔇 @{username} wyłączył moduł Spotify.")
            else:
                connection.privmsg(channel_name, f"❌ @{username}, brak uprawnień do wyłączenia Spotify.")
            return

        elif message == "!spotifyon":
            if username in self.trusted_users:
                self.spotify_enabled = True
                connection.privmsg(channel_name, f"🎵 @{username} ponownie włączył moduł Spotify.")
            else:
                connection.privmsg(channel_name, f"❌ @{username}, brak uprawnień do włączenia Spotify.")
            return

        elif message.startswith("!sr "):
            if not self.spotify_enabled:
                connection.privmsg(channel_name, f"❌ @{username}, moduł Spotify jest obecnie wyłączony.")
                return

            now = time.time()
            last_time = self.last_request_time.get(username, 0)

            if username not in self.subs_no_limit:
                remaining = int(SONG_REQUEST_TIMEOUT - (now - last_time))
                if now - last_time < SONG_REQUEST_TIMEOUT:
                    minutes = remaining // 60
                    seconds = remaining % 60
                    connection.privmsg(channel_name, f"❌ @{username}, możesz dodać kolejną piosenkę za {minutes}m {seconds}s.")
                    return

            song_name = message[len("!sr "):].strip()
            if not song_name:
                connection.privmsg(channel_name, f"@{username}, podaj tytuł piosenki po komendzie !sr")
                return

            try:
                if not self.ensure_token_valid():
                    connection.privmsg(channel_name, f"❌ @{username}, problem z autoryzacją Spotify.")
                    return
                    
                results = self.sp.search(q=song_name, limit=3, type='track')
                tracks = results.get('tracks', {}).get('items', [])
                if not tracks:
                    connection.privmsg(channel_name, f"❌ @{username}, nie znalazłem żadnych wyników dla \"{song_name}\".")
                    return

                self.pending_song_requests[username] = tracks
                connection.privmsg(channel_name, f"@{username}, wybierz piosenkę wpisując !select <numer>:")
                for i, track in enumerate(tracks, 1):
                    artists = ", ".join(artist['name'] for artist in track['artists'])
                    connection.privmsg(channel_name, f"{i}. {track['name']} - {artists}")

            except Exception as e:
                safe_print(f"Spotify error:", e)
                connection.privmsg(channel_name, f"❌ @{username}, wystąpił błąd podczas wyszukiwania piosenki.")

        elif message.startswith("!select "):
            if not self.spotify_enabled:
                connection.privmsg(channel_name, f"❌ @{username}, moduł Spotify jest obecnie wyłączony.")
                return

            if username not in self.pending_song_requests:
                connection.privmsg(channel_name, f"@{username}, nie masz żadnych oczekujących propozycji.")
                return
            try:
                choice = int(message[len("!select "):].strip())
                tracks = self.pending_song_requests[username]
                if choice < 1 or choice > len(tracks):
                    connection.privmsg(channel_name, f"@{username}, wybierz numer od 1 do {len(tracks)}.")
                    return
                track = tracks[choice - 1]
                if not self.ensure_token_valid():
                    connection.privmsg(channel_name, f"❌ @{username}, problem z autoryzacją Spotify.")
                    return
                    
                self.sp.add_to_queue(track['uri'])
                artists = ", ".join(artist['name'] for artist in track['artists'])
                connection.privmsg(channel_name, f"🎶 @{username}, dodano: \"{track['name']}\" - {artists}")
                self.last_request_time[username] = time.time()
                del self.pending_song_requests[username]
            except Exception as e:
                safe_print(f"Spotify error:", e)
                connection.privmsg(channel_name, f"❌ @{username}, błąd przy dodawaniu piosenki.")

        elif message == "!ply":
            if not self.spotify_enabled:
                connection.privmsg(channel_name, f"❌ @{username}, moduł Spotify jest obecnie wyłączony.")
                return

            if not self.ensure_token_valid():
                connection.privmsg(channel_name, f"❌ @{username}, problem z autoryzacją Spotify.")
                return
                
            if self.start_playback():
                connection.privmsg(channel_name, f"▶️ @{username}, rozpocząłem odtwarzanie na Spotify!")
            else:
                connection.privmsg(channel_name, f"❌ @{username}, nie udało się rozpocząć odtwarzania.")

        elif message == "!skip":
            if not self.spotify_enabled:
                connection.privmsg(channel_name, f"❌ @{username}, moduł Spotify jest obecnie wyłączony.")
                return

            if username not in self.allowed_skip:
                connection.privmsg(channel_name, f"❌ @{username}, nie masz uprawnień do użycia tej komendy.")
                return
            try:
                if not self.ensure_token_valid():
                    connection.privmsg(channel_name, f"❌ @{username}, problem z autoryzacją Spotify.")
                    return
                    
                self.sp.next_track()
                connection.privmsg(channel_name, f"⏭️ @{username} pominął aktualną piosenkę.")
            except Exception as e:
                safe_print(f"Spotify skip error:", e)
                connection.privmsg(channel_name, f"❌ @{username}, nie udało się pominąć piosenki.")

        elif message == "!currentsong":
            if not self.spotify_enabled:
                connection.privmsg(channel_name, f"❌ @{username}, moduł Spotify jest obecnie wyłączony.")
                return

            try:
                if not self.ensure_token_valid():
                    connection.privmsg(channel_name, f"❌ @{username}, problem z autoryzacją Spotify.")
                    return
                    
                playback = self.sp.current_playback()
                if playback and playback.get('item'):
                    track = playback['item']
                    artists = ", ".join(artist['name'] for artist in track['artists'])
                    connection.privmsg(channel_name, f"🎵 Teraz gra: \"{track['name']}\" - {artists}")
                else:
                    connection.privmsg(channel_name, "❌ Nie ma aktualnie odtwarzanej piosenki.")
            except Exception as e:
                safe_print(f"Spotify error:", e)
                connection.privmsg(channel_name, "❌ Błąd przy pobieraniu informacji o piosence.")

        elif message == "!help":
            help_msg1 = (
                "🎵 Spotify: !sr <tytuł> | !select <numer> | !currentsong"
            )
            help_msg2 = (
                "🎮 Gry: !roll | !coinflip <orzeł/reszka> | !roulette <liczba/kolor> | !quiz | !answer <odpowiedź>"
            )
            help_msg3 = (
                "💰 Punkty: !points | !top | !daily | !give @user <punkty> | !motywacja"
            )
            help_msg4 = (
                "🛒 Sklep: !shop | !kup <nagroda> | !inventory"
            )
            connection.privmsg(channel_name, help_msg1)
            connection.privmsg(channel_name, help_msg2)
            connection.privmsg(channel_name, help_msg3)
            connection.privmsg(channel_name, help_msg4)

        # === KOMENDY FOLLOWÓW ===
        elif message == "!followsoff":
            if username in self.trusted_users:
                self.follow_thanks_enabled = False
                connection.privmsg(channel_name, f"🔇 @{username} wyłączył automatyczne dziękowanie za followy.")
            else:
                connection.privmsg(channel_name, f"❌ @{username}, brak uprawnień do wyłączenia followów.")
            return

        elif message == "!followson":
            if username in self.trusted_users:
                if not os.getenv('TWITCH_CLIENT_ID') or not os.getenv('TWITCH_ACCESS_TOKEN'):
                    connection.privmsg(channel_name, f"❌ @{username}, brak konfiguracji Twitch API. Zobacz TWITCH_API_SETUP.md")
                    return
                    
                self.follow_thanks_enabled = True
                if not self.check_followers_thread or not self.check_followers_thread.is_alive():
                    self.start_follow_checker()
                connection.privmsg(channel_name, f"💜 @{username} włączył automatyczne dziękowanie za followy.")
            else:
                connection.privmsg(channel_name, f"❌ @{username}, brak uprawnień do włączenia followów.")
            return

        # === KOMENDY SUBSKRYPCJI ===
        elif message == "!subsoff":
            if username in self.trusted_users:
                self.sub_thanks_enabled = False
                connection.privmsg(channel_name, f"🔇 @{username} wyłączył automatyczne dziękowanie za suby.")
            else:
                connection.privmsg(channel_name, f"❌ @{username}, brak uprawnień do wyłączenia subów.")
            return

        elif message == "!subson":
            if username in self.trusted_users:
                if not os.getenv('TWITCH_CLIENT_ID') or not os.getenv('TWITCH_ACCESS_TOKEN'):
                    connection.privmsg(channel_name, f"❌ @{username}, brak konfiguracji Twitch API. Zobacz TWITCH_API_SETUP.md")
                    return
                    
                self.sub_thanks_enabled = True
                if not self.check_subscribers_thread or not self.check_subscribers_thread.is_alive():
                    self.start_subscription_checker()
                connection.privmsg(channel_name, f"🌟 @{username} włączył automatyczne dziękowanie za suby.")
            else:
                connection.privmsg(channel_name, f"❌ @{username}, brak uprawnień do włączenia subów.")
            return

        elif message == "!subs":
            if not os.getenv('TWITCH_CLIENT_ID') or not os.getenv('TWITCH_ACCESS_TOKEN'):
                connection.privmsg(channel_name, f"❌ @{username}, brak konfiguracji Twitch API.")
                return
                
            try:
                subscribers = self.get_twitch_subscribers()
                if subscribers:
                    sub_count = len(subscribers)
                    if sub_count > 0:
                        # Pokaż tylko pierwszych 10 subskrybentów, żeby nie spamować chatu
                        display_subs = subscribers[:10]
                        subs_text = ", ".join(display_subs)
                        if sub_count > 10:
                            connection.privmsg(channel_name, f"🌟 Subskrybenci ({sub_count}): {subs_text} i {sub_count - 10} więcej...")
                        else:
                            connection.privmsg(channel_name, f"🌟 Subskrybenci ({sub_count}): {subs_text}")
                    else:
                        connection.privmsg(channel_name, "📊 Brak subskrybentów.")
                else:
                    connection.privmsg(channel_name, f"❌ @{username}, nie udało się pobrać listy subskrybentów.")
            except Exception as e:
                safe_print(f"❌ Błąd komendy !subs: {e}")
                connection.privmsg(channel_name, f"❌ @{username}, błąd przy pobieraniu subskrybentów.")
            return

        # === KOMENDY MODYFIKACJI KANAŁU ===
        elif message.startswith("!settitle "):
            if username in self.trusted_users or username.lower() == "kranik1606":
                new_title = message[len("!settitle "):].strip()
                if new_title:
                    connection.privmsg(channel_name, f"📝 @{username}, zmieniam tytuł streama...")
                    success = self.modify_channel_info(title=new_title)
                    if success:
                        connection.privmsg(channel_name, f"✅ @{username}, tytuł streama został zmieniony na: {new_title}")
                    else:
                        connection.privmsg(channel_name, f"❌ @{username}, nie udało się zmienić tytułu streama.")
                else:
                    connection.privmsg(channel_name, f"@{username}, użyj: !settitle <nowy tytuł>")
            else:
                connection.privmsg(channel_name, f"❌ @{username}, nie masz uprawnień do zmiany tytułu.")
            return

        elif message.startswith("!setgame "):
            if username in self.trusted_users or username.lower() == "kranik1606":
                new_game = message[len("!setgame "):].strip()
                if new_game:
                    connection.privmsg(channel_name, f"🎮 @{username}, zmieniam kategorię streama...")
                    success = self.modify_channel_info(game_name=new_game)
                    if success:
                        connection.privmsg(channel_name, f"✅ @{username}, kategoria streama została zmieniona na: {new_game}")
                    else:
                        connection.privmsg(channel_name, f"❌ @{username}, nie udało się zmienić kategorii streama.")
                else:
                    connection.privmsg(channel_name, f"@{username}, użyj: !setgame <nazwa gry>")
            else:
                connection.privmsg(channel_name, f"❌ @{username}, nie masz uprawnień do zmiany kategorii.")
            return

        elif message.startswith("!setstream "):
            if username in self.trusted_users or username.lower() == "kranik1606":
                # Format: !setstream "tytuł" "gra"
                parts = message[len("!setstream "):].strip()
                
                # Parsuj argumenty w cudzysłowach
                import re
                matches = re.findall(r'"([^"]*)"', parts)
                
                if len(matches) >= 2:
                    new_title = matches[0]
                    new_game = matches[1]
                    connection.privmsg(channel_name, f"🔄 @{username}, zmieniam tytuł i kategorię streama...")
                    success = self.modify_channel_info(title=new_title, game_name=new_game)
                    if success:
                        connection.privmsg(channel_name, f"✅ @{username}, stream zaktualizowany!")
                        connection.privmsg(channel_name, f"📝 Tytuł: {new_title}")
                        connection.privmsg(channel_name, f"🎮 Kategoria: {new_game}")
                    else:
                        connection.privmsg(channel_name, f"❌ @{username}, nie udało się zaktualizować streama.")
                else:
                    connection.privmsg(channel_name, f'@{username}, użyj: !setstream "tytuł" "gra"')
            else:
                connection.privmsg(channel_name, f"❌ @{username}, nie masz uprawnień do zmiany streama.")
            return

        elif message == "!motywacja":
            quote = random.choice(MOTYWACYJNE_CYTATY)
            connection.privmsg(channel_name, f"💪 {quote}")

        elif message.startswith("!clear_discord "):
            # Sprawdź uprawnienia - tylko właściciel
            is_owner = username.lower() == "kranik1606"
            
            if not is_owner:
                connection.privmsg(channel_name, f"❌ @{username}, tylko właściciel kanału może czyścić kanały Discord.")
                return
            
            parts = message.split()
            if len(parts) >= 2:
                channel_id = parts[1]
                
                # Sprawdź czy Discord bot jest skonfigurowany
                if not self.discord.bot_enabled:
                    connection.privmsg(channel_name, f"❌ @{username}, Discord bot nie jest skonfigurowany.")
                    return
                
                connection.privmsg(channel_name, f"🧹 @{username}, rozpoczynam czyszczenie kanału Discord (ID: {channel_id})...")
                
                # Uruchom czyszczenie w osobnym wątku
                def clear_channel_thread():
                    try:
                        import asyncio
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        success = loop.run_until_complete(
                            self.discord.clear_discord_channel(channel_id, username)
                        )
                        loop.close()
                        
                        if success:
                            self.connection.privmsg(channel_name, f"✅ @{username}, czyszczenie kanału Discord zakończone!")
                        else:
                            self.connection.privmsg(channel_name, f"❌ @{username}, wystąpił błąd podczas czyszczenia kanału.")
                    except Exception as e:
                        safe_print(f"❌ Błąd czyszczenia kanału Discord: {e}")
                        self.connection.privmsg(channel_name, f"❌ @{username}, błąd podczas czyszczenia: {str(e)}")
                
                threading.Thread(target=clear_channel_thread, daemon=True).start()
            else:
                connection.privmsg(channel_name, f"@{username}, użyj: !clear_discord <channel_id>")
            return

        elif message == "!clear_points":
            if username in self.trusted_users:
                connection.privmsg(channel_name, f"🧹 @{username}, rozpoczynam czyszczenie punktów użytkownikom bez follow...")
                cleared_count = self.clear_non_followers_points()
                connection.privmsg(channel_name, f"✅ @{username}, wyczyszczono punkty {cleared_count} użytkownikom.")
            else:
                connection.privmsg(channel_name, f"❌ @{username}, nie masz uprawnień do czyszczenia punktów.")

        elif message.startswith("!checkfollow "):
            if username in self.trusted_users or username.lower() == "kranik1606":
                target_user = message[len("!checkfollow "):].strip().lstrip('@').lower()
                if target_user:
                    is_follower = self.is_follower(target_user)
                    status = "✅ TAK" if is_follower else "❌ NIE"
                    connection.privmsg(channel_name, f"🔍 @{username}, użytkownik {target_user} ma follow: {status}")
                else:
                    connection.privmsg(channel_name, f"@{username}, użyj: !checkfollow <username>")
            else:
                connection.privmsg(channel_name, f"❌ @{username}, nie masz uprawnień do sprawdzania followów.")

        elif message.startswith("!rc "):
            # Komenda rekomendacji - tylko dla właściciela i moderatorów
            if username in self.trusted_users or username.lower() == "kranik1606":
                target_user = message[len("!rc "):].strip().lstrip('@')
                if target_user:
                    # Link do profilu na Twitchu
                    profile_link = f"https://twitch.tv/{target_user}"
                    
                    # Lista fajnych opisów zachęcających do sprawdzenia profilu z linkiem
                    recommend_messages = [
                        f"🌟 Hej czat! Sprawdźcie profil {target_user} na Twitchu! 🔥 Warto rzucić okiem na jego content! 👀 {profile_link}",
                        f"💎 {target_user} ma naprawdę ciekawy profil! Polecam zajrzeć i może dać follow! 🚀✨ {profile_link}",
                        f"🎯 Czat, koniecznie sprawdźcie {target_user}! Jego treści są naprawdę warte uwagi! 💜🔥 {profile_link}",
                        f"⭐ {target_user} robi świetne rzeczy na Twitchu! Zdecydowanie warto go obserwować! 🎮💫 {profile_link}",
                        f"🚀 Polecam wszystkim profil {target_user}! Naprawdę fajny content czeka na Was! 🌟👑 {profile_link}",
                        f"💫 {target_user} zasługuje na więcej uwagi! Sprawdźcie jego kanał - nie pożałujecie! 🔥💜 {profile_link}",
                        f"🎊 Hej społeczność! {target_user} ma super profil na Twitchu! Dajcie mu szansę! ✨🎯 {profile_link}"
                    ]
                    
                    recommendation = random.choice(recommend_messages)
                    connection.privmsg(channel_name, recommendation)
                    safe_print(f"📢 {username} polecił profil: {target_user} ({profile_link})")
                else:
                    connection.privmsg(channel_name, f"@{username}, użyj: !rc @username")
            else:
                connection.privmsg(channel_name, f"❌ @{username}, nie masz uprawnień do polecania profili.")

        elif message == "!update_shop":
            if username in self.trusted_users or username.lower() == "kranik1606":
                connection.privmsg(channel_name, f"🛒 @{username}, wymuszam aktualizację sklepu Discord...")
                try:
                    self.shop.force_update_shop_post()
                    connection.privmsg(channel_name, f"✅ @{username}, sklep Discord został zaktualizowany!")
                except Exception as e:
                    safe_print(f"❌ Błąd aktualizacji sklepu: {e}")
                    connection.privmsg(channel_name, f"❌ @{username}, błąd podczas aktualizacji sklepu.")
            else:
                connection.privmsg(channel_name, f"❌ @{username}, nie masz uprawnień do aktualizacji sklepu.")



        elif message == "!shutdown":
            if username in self.trusted_users:
                connection.privmsg(channel_name, "Robocik się odmeldowuje! 🤖👋")
                self.connection.quit("Shutdown by command")
                sys.exit(0)
            else:
                connection.privmsg(channel_name, f"❌ @{username}, nie masz uprawnień do wyłączenia bota.")

    # === METODY OBSŁUGI FOLLOWÓW ===
    def start_follow_checker(self):
        """Uruchamia wątek sprawdzający nowych followerów"""
        def follow_checker_loop():
            # Pobierz początkową listę followerów
            initial_followers = self.get_twitch_followers()
            if initial_followers:
                self.last_followers = set(initial_followers)
                safe_print(f"📊 Załadowano {len(self.last_followers)} followerów")
            
            while self.follow_thanks_enabled:
                try:
                    time.sleep(15)  # Sprawdzaj co 15 sekund
                    self.check_new_followers()
                except Exception as e:
                    safe_print(f"❌ Błąd sprawdzania followów: {e}")
                    time.sleep(60)  # Czekaj dłużej przy błędzie

        self.check_followers_thread = threading.Thread(target=follow_checker_loop, daemon=True)
        self.check_followers_thread.start()
        safe_print(f"🔄 Uruchomiono sprawdzanie followów")

    def check_new_followers(self):
        """Sprawdza nowych followerów i dziękuje im"""
        current_followers = self.get_twitch_followers()
        if not current_followers:
            return

        current_set = set(current_followers)
        new_followers = current_set - self.last_followers
        
        for follower in new_followers:
            self.thank_for_follow(follower)
            time.sleep(2)  # Odstęp między podziękowaniami
        
        self.last_followers = current_set

    def get_twitch_followers(self):
        """Pobiera listę followerów z Twitch API z paginacją"""
        try:
            # Używamy Twitch Helix API
            headers = {
                'Client-ID': os.getenv('TWITCH_CLIENT_ID'),
                'Authorization': f'Bearer {os.getenv("TWITCH_ACCESS_TOKEN")}'
            }
            
            # Najpierw pobierz ID kanału
            user_url = f"https://api.twitch.tv/helix/users?login={CHANNEL.lstrip('#')}"
            user_response = requests.get(user_url, headers=headers)
            
            if user_response.status_code != 200:
                safe_print(f"❌ Błąd pobierania danych użytkownika: {user_response.status_code}")
                return None
                
            user_data = user_response.json()
            if not user_data.get('data'):
                safe_print(f"❌ Nie znaleziono danych użytkownika")
                return None
                
            broadcaster_id = user_data['data'][0]['id']
            
            # Pobierz wszystkich followerów z paginacją
            all_followers = []
            cursor = None
            
            while True:
                # Buduj URL z cursorem jeśli istnieje
                followers_url = f"https://api.twitch.tv/helix/channels/followers?broadcaster_id={broadcaster_id}&first=100"
                if cursor:
                    followers_url += f"&after={cursor}"
                
                followers_response = requests.get(followers_url, headers=headers)
                
                if followers_response.status_code != 200:
                    safe_print(f"❌ Błąd pobierania followerów: {followers_response.status_code}")
                    return None
                    
                followers_data = followers_response.json()
                page_followers = [follower['user_name'].lower() for follower in followers_data.get('data', [])]
                all_followers.extend(page_followers)
                
                # Sprawdź czy są kolejne strony
                pagination = followers_data.get('pagination', {})
                cursor = pagination.get('cursor')
                
                if not cursor:
                    break  # Brak kolejnych stron
                    
                # Dodaj małe opóźnienie między requestami
                time.sleep(0.1)
            
            safe_print(f"📊 Pobrano {len(all_followers)} followerów (wszystkich)")
            return all_followers
            
        except Exception as e:
            safe_print(f"❌ Błąd API Twitch: {e}")
            return None

    def thank_for_follow(self, username):
        """Dziękuje za follow"""
        if not self.follow_thanks_enabled:
            return
            
        try:
            message = random.choice(FOLLOW_THANKS_MESSAGES).format(username=username)
            channel_name = self.get_channel_name()
            self.connection.privmsg(channel_name, message)
            # Powiadomienie Discord o nowym followerze
            self.discord.notify_new_follower(username)
            safe_print(f"💜 Podziękowano za follow: {username}")
        except Exception as e:
            safe_print(f"❌ Błąd dziękowania za follow: {e}")

    # === METODY OBSŁUGI SUBSKRYPCJI ===
    def start_subscription_checker(self):
        """Uruchamia wątek sprawdzający nowych subskrybentów"""
        def subscription_checker_loop():
            # Pobierz początkową listę subskrybentów
            initial_subscribers = self.get_twitch_subscribers()
            if initial_subscribers:
                self.last_subscribers = set(initial_subscribers)
                safe_print(f"📊 Załadowano {len(self.last_subscribers)} subskrybentów")
            
            while self.sub_thanks_enabled:
                try:
                    time.sleep(15)  # Sprawdzaj co 15 sekund
                    self.check_new_subscribers()
                except Exception as e:
                    safe_print(f"❌ Błąd sprawdzania subskrypcji: {e}")
                    time.sleep(60)  # Czekaj dłużej przy błędzie

        self.check_subscribers_thread = threading.Thread(target=subscription_checker_loop, daemon=True)
        self.check_subscribers_thread.start()
        safe_print(f"🔄 Uruchomiono sprawdzanie subskrypcji")

    def check_new_subscribers(self):
        """Sprawdza nowych subskrybentów i dziękuje im"""
        current_subscribers = self.get_twitch_subscribers()
        if not current_subscribers:
            return

        current_set = set(current_subscribers)
        new_subscribers = current_set - self.last_subscribers
        
        for subscriber in new_subscribers:
            self.thank_for_subscription(subscriber)
            time.sleep(2)  # Odstęp między podziękowaniami
        
        self.last_subscribers = current_set

    def get_twitch_subscribers(self):
        """Pobiera listę subskrybentów z Twitch API z paginacją"""
        try:
            # Używamy Twitch Helix API
            headers = {
                'Client-ID': os.getenv('TWITCH_CLIENT_ID'),
                'Authorization': f'Bearer {os.getenv("TWITCH_ACCESS_TOKEN")}'
            }
            
            # Najpierw pobierz ID kanału
            user_url = f"https://api.twitch.tv/helix/users?login={CHANNEL.lstrip('#')}"
            user_response = requests.get(user_url, headers=headers)
            
            if user_response.status_code != 200:
                safe_print(f"❌ Błąd pobierania danych użytkownika: {user_response.status_code}")
                return None
                
            user_data = user_response.json()
            if not user_data.get('data'):
                safe_print(f"❌ Nie znaleziono danych użytkownika")
                return None
                
            broadcaster_id = user_data['data'][0]['id']
            
            # Pobierz wszystkich subskrybentów z paginacją
            all_subscribers = []
            cursor = None
            
            while True:
                # Buduj URL z cursorem jeśli istnieje
                subscribers_url = f"https://api.twitch.tv/helix/subscriptions?broadcaster_id={broadcaster_id}&first=100"
                if cursor:
                    subscribers_url += f"&after={cursor}"
                
                subscribers_response = requests.get(subscribers_url, headers=headers)
                
                if subscribers_response.status_code != 200:
                    safe_print(f"❌ Błąd pobierania subskrybentów: {subscribers_response.status_code}")
                    return None
                    
                subscribers_data = subscribers_response.json()
                page_subscribers = [sub['user_name'].lower() for sub in subscribers_data.get('data', [])]
                all_subscribers.extend(page_subscribers)
                
                # Sprawdź czy są kolejne strony
                pagination = subscribers_data.get('pagination', {})
                cursor = pagination.get('cursor')
                
                if not cursor:
                    break  # Brak kolejnych stron
                    
                # Dodaj małe opóźnienie między requestami
                time.sleep(0.1)
            
            safe_print(f"📊 Pobrano {len(all_subscribers)} subskrybentów (wszystkich)")
            return all_subscribers
            
        except Exception as e:
            safe_print(f"❌ Błąd API Twitch (subskrypcje): {e}")
            return None

    def thank_for_subscription(self, username):
        """Dziękuje za subskrypcję"""
        if not self.sub_thanks_enabled:
            return
            
        try:
            message = random.choice(SUB_THANKS_MESSAGES).format(username=username)
            channel_name = self.get_channel_name()
            self.connection.privmsg(channel_name, message)
            # Powiadomienie Discord o nowym subskrybencie
            self.discord.notify_new_subscriber(username)
            safe_print(f"🌟 Podziękowano za sub: {username}")
        except Exception as e:
            safe_print(f"❌ Błąd dziękowania za sub: {e}")

    # === METODY OBSŁUGI UPRAWNIEŃ ===
    def update_permissions_on_startup(self):
        """Uruchamia pierwsze pobieranie uprawnień w osobnym wątku"""
        def permissions_updater():
            try:
                safe_print(f"🔄 Pobieranie uprawnień z Twitch API...")
                self.fetch_moderators()
                self.fetch_vips()
                self.fetch_subscribers_for_permissions()
                self.update_permission_lists()
                safe_print(f"✅ Uprawnienia zaktualizowane!")
                
                # Uruchom cykliczne odświeżanie co 5 minut
                while True:
                    time.sleep(300)  # 5 minut
                    try:
                        self.fetch_moderators()
                        self.fetch_vips()
                        self.fetch_subscribers_for_permissions()
                        self.update_permission_lists()
                        # Wyczyść punkty użytkownikom bez follow
                        self.clear_non_followers_points()
                        safe_print(f"🔄 Uprawnienia odświeżone")
                    except Exception as e:
                        safe_print(f"❌ Błąd odświeżania uprawnień: {e}")
                        
            except Exception as e:
                safe_print(f"❌ Błąd inicjalizacji uprawnień: {e}")
        
        permissions_thread = threading.Thread(target=permissions_updater, daemon=True)
        permissions_thread.start()

    def fetch_moderators(self):
        """Pobiera listę moderatorów z Twitch API"""
        try:
            headers = {
                'Client-ID': os.getenv('TWITCH_CLIENT_ID'),
                'Authorization': f'Bearer {os.getenv("TWITCH_ACCESS_TOKEN")}'
            }
            
            # Pobierz ID kanału
            user_url = f"https://api.twitch.tv/helix/users?login={CHANNEL.lstrip('#')}"
            user_response = requests.get(user_url, headers=headers)
            
            if user_response.status_code != 200:
                safe_print(f"❌ Błąd pobierania danych użytkownika dla moderatorów: {user_response.status_code}")
                return
                
            user_data = user_response.json()
            if not user_data.get('data'):
                safe_print(f"❌ Nie znaleziono danych użytkownika dla moderatorów")
                return
                
            broadcaster_id = user_data['data'][0]['id']
            
            # Pobierz moderatorów
            moderators_url = f"https://api.twitch.tv/helix/moderation/moderators?broadcaster_id={broadcaster_id}&first=100"
            moderators_response = requests.get(moderators_url, headers=headers)
            
            if moderators_response.status_code == 200:
                moderators_data = moderators_response.json()
                moderators = [mod['user_name'].lower() for mod in moderators_data.get('data', [])]
                self.moderators = set(moderators)
                safe_print(f"📋 Pobrano {len(self.moderators)} moderatorów")
            else:
                safe_print(f"❌ Błąd pobierania moderatorów: {moderators_response.status_code}")
                
        except Exception as e:
            safe_print(f"❌ Błąd API moderatorów: {e}")

    def fetch_vips(self):
        """Pobiera listę VIP-ów z Twitch API"""
        try:
            headers = {
                'Client-ID': os.getenv('TWITCH_CLIENT_ID'),
                'Authorization': f'Bearer {os.getenv("TWITCH_ACCESS_TOKEN")}'
            }
            
            # Pobierz ID kanału
            user_url = f"https://api.twitch.tv/helix/users?login={CHANNEL.lstrip('#')}"
            user_response = requests.get(user_url, headers=headers)
            
            if user_response.status_code != 200:
                safe_print(f"❌ Błąd pobierania danych użytkownika dla VIP: {user_response.status_code}")
                return
                
            user_data = user_response.json()
            if not user_data.get('data'):
                safe_print(f"❌ Nie znaleziono danych użytkownika dla VIP")
                return
                
            broadcaster_id = user_data['data'][0]['id']
            
            # Pobierz VIP-ów
            vips_url = f"https://api.twitch.tv/helix/channels/vips?broadcaster_id={broadcaster_id}&first=100"
            vips_response = requests.get(vips_url, headers=headers)
            
            if vips_response.status_code == 200:
                vips_data = vips_response.json()
                vips = [vip['user_name'].lower() for vip in vips_data.get('data', [])]
                self.vips = set(vips)
                safe_print(f"⭐ Pobrano {len(self.vips)} VIP-ów")
            else:
                safe_print(f"❌ Błąd pobierania VIP-ów: {vips_response.status_code}")
                
        except Exception as e:
            safe_print(f"❌ Błąd API VIP-ów: {e}")

    def fetch_subscribers_for_permissions(self):
        """Pobiera listę subskrybentów dla uprawnień (używa istniejącą funkcję)"""
        try:
            subscribers = self.get_twitch_subscribers()
            if subscribers:
                self.subscribers = set(subscribers)
                safe_print(f"🌟 Pobrano {len(self.subscribers)} subskrybentów dla uprawnień")
        except Exception as e:
            safe_print(f"❌ Błąd pobierania subskrybentów dla uprawnień: {e}")

    def update_permission_lists(self):
        """Aktualizuje wszystkie listy uprawnień na podstawie pobranych danych"""
        # Trusted users = moderatorzy + VIP + właściciel
        self.trusted_users = self.moderators | self.vips | {"kranik1606"}
        
        # Subs no limit = subskrybenci + VIP + właściciel  
        self.subs_no_limit = self.subscribers | self.vips | {"kranik1606"}
        
        # Allowed skip = moderatorzy + VIP + właściciel
        self.allowed_skip = self.moderators | self.vips | {"kranik1606"}
        
        safe_print(f"🔧 Zaktualizowano uprawnienia:")
        safe_print(f"   👑 Trusted users: {len(self.trusted_users)}")
        safe_print(f"   🎵 Subs no limit: {len(self.subs_no_limit)}")
        safe_print(f"   ⏭️ Allowed skip: {len(self.allowed_skip)}")

    def is_follower(self, username):
        """Sprawdza czy użytkownik jest followerem"""
        return username.lower() in self.last_followers or username.lower() == "kranik1606"

    def clear_non_followers_points(self):
        """Czyści punkty użytkownikom, którzy nie są followerami"""
        try:
            # Pobierz wszystkich użytkowników z bazy danych
            all_users = self.db.get_all_users_with_points()
            cleared_count = 0
            
            for user in all_users:
                username = user[0]  # Pierwsza kolumna to username
                current_points = user[1]  # Druga kolumna to points
                
                # Sprawdź czy użytkownik jest followerem (pomijaj właściciela)
                if not self.is_follower(username) and username.lower() != "kranik1606":
                    if current_points > 0:
                        # Wyczyść punkty
                        self.db.set_user_points(username, 0)
                        cleared_count += 1
                        safe_print(f"🧹 Wyczyszczono punkty użytkownika: {username} ({current_points} pkt)")
            
            safe_print(f"✅ Wyczyszczono punkty {cleared_count} użytkownikom bez follow")
            return cleared_count
            
        except Exception as e:
            safe_print(f"❌ Błąd czyszczenia punktów: {e}")
            return 0

    def get_channel_info(self, username):
        """Pobiera informacje o kanale z Twitch API (tytuł i grę)"""
        try:
            headers = {
                'Client-ID': os.getenv('TWITCH_CLIENT_ID'),
                'Authorization': f'Bearer {os.getenv("TWITCH_ACCESS_TOKEN")}'
            }
            
            # Pobierz ID użytkownika
            user_url = f"https://api.twitch.tv/helix/users?login={username}"
            user_response = requests.get(user_url, headers=headers)
            
            if user_response.status_code != 200:
                safe_print(f"❌ Błąd pobierania danych użytkownika {username}: {user_response.status_code}")
                return None
                
            user_data = user_response.json()
            if not user_data.get('data'):
                safe_print(f"❌ Nie znaleziono użytkownika {username}")
                return None
                
            user_id = user_data['data'][0]['id']
            
            # Pobierz informacje o kanale
            channel_url = f"https://api.twitch.tv/helix/channels?broadcaster_id={user_id}"
            channel_response = requests.get(channel_url, headers=headers)
            
            if channel_response.status_code == 200:
                channel_data = channel_response.json()
                if channel_data.get('data'):
                    channel_info = channel_data['data'][0]
                    return {
                        'game_name': channel_info.get('game_name', 'Nieznana gra'),
                        'title': channel_info.get('title', 'Brak tytułu')
                    }
            else:
                safe_print(f"❌ Błąd pobierania informacji o kanale {username}: {channel_response.status_code}")
                return None
                
        except Exception as e:
            safe_print(f"❌ Błąd API kanału dla {username}: {e}")
            return None

    def modify_channel_info(self, title=None, game_name=None):
        """Modyfikuje informacje o kanale (tytuł i/lub grę)"""
        try:
            headers = {
                'Client-ID': os.getenv('TWITCH_CLIENT_ID'),
                'Authorization': f'Bearer {os.getenv("TWITCH_ACCESS_TOKEN")}',
                'Content-Type': 'application/json'
            }
            
            # Pobierz ID użytkownika
            user_url = f"https://api.twitch.tv/helix/users?login={CHANNEL.lstrip('#')}"
            user_response = requests.get(user_url, headers=headers)
            
            if user_response.status_code != 200:
                safe_print(f"❌ Błąd pobierania danych użytkownika: {user_response.status_code}")
                return False
                
            user_data = user_response.json()
            if not user_data.get('data'):
                safe_print(f"❌ Nie znaleziono użytkownika")
                return False
                
            user_id = user_data['data'][0]['id']
            
            # Przygotuj dane do modyfikacji
            modify_data = {}
            if title is not None:
                modify_data['title'] = title
            if game_name is not None:
                # Znajdź ID gry
                game_id = self.get_game_id(game_name)
                if game_id:
                    modify_data['game_id'] = game_id
                else:
                    safe_print(f"❌ Nie znaleziono gry: {game_name}")
                    return False
            
            if not modify_data:
                safe_print(f"❌ Brak danych do modyfikacji")
                return False
            
            # Modyfikuj kanał
            channel_url = f"https://api.twitch.tv/helix/channels?broadcaster_id={user_id}"
            response = requests.patch(channel_url, headers=headers, json=modify_data)
            
            if response.status_code == 204:
                safe_print(f"✅ Pomyślnie zaktualizowano kanał")
                if title:
                    safe_print(f"📝 Nowy tytuł: {title}")
                if game_name:
                    safe_print(f"🎮 Nowa gra: {game_name}")
                return True
            else:
                safe_print(f"❌ Błąd modyfikacji kanału: {response.status_code}")
                safe_print(f"❌ Odpowiedź: {response.text}")
                return False
                
        except Exception as e:
            safe_print(f"❌ Błąd modyfikacji kanału: {e}")
            return False

    def get_game_id(self, game_name):
        """Pobiera ID gry na podstawie nazwy"""
        try:
            headers = {
                'Client-ID': os.getenv('TWITCH_CLIENT_ID'),
                'Authorization': f'Bearer {os.getenv("TWITCH_ACCESS_TOKEN")}'
            }
            
            # Szukaj gry
            game_url = f"https://api.twitch.tv/helix/games?name={requests.utils.quote(game_name)}"
            response = requests.get(game_url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('data'):
                    return data['data'][0]['id']
            
            safe_print(f"❌ Nie znaleziono gry: {game_name}")
            return None
            
        except Exception as e:
            safe_print(f"❌ Błąd pobierania ID gry: {e}")
            return None

    def on_usernotice(self, connection, event):
        """Obsługuje USERNOTICE wiadomości (rajdy, suby, etc.)"""
        try:
            # Parsuj tagi z wiadomości
            tags = {}
            if hasattr(event, 'tags'):
                for tag in event.tags:
                    if '=' in tag:
                        key, value = tag.split('=', 1)
                        tags[key] = value
            
            # Sprawdź czy to rajd
            msg_id = tags.get('msg-id', '')
            if msg_id == 'raid':
                raider_name = tags.get('msg-param-displayName', tags.get('display-name', 'Nieznany'))
                viewer_count = tags.get('msg-param-viewerCount', '0')
                
                safe_print(f"🚀 Wykryto rajd od {raider_name} z {viewer_count} widzami!")
                
                # Pobierz informacje o kanale rajdera
                channel_info = self.get_channel_info(raider_name.lower())
                
                # Przygotuj wiadomość o rajdzie
                raid_message = f"🚀 RAJD! {raider_name} zrajdował nas z {viewer_count} widzami! "
                raid_message += f"Koniecznie sprawdźcie jego kanał: twitch.tv/{raider_name.lower()} "
                
                if channel_info and channel_info['game_name'] != 'Nieznana gra':
                    raid_message += f"- ostatnio grał w: {channel_info['game_name']} 🎮"
                else:
                    raid_message += "🎮"
                
                # Wyślij wiadomość na chat
                connection.privmsg(channel_name, raid_message)
                
                # Dodatkowa wiadomość z polecajką
                recommendation = f"💜 Polecam gorąco kanał {raider_name}! Warto go obserwować! 🌟"
                connection.privmsg(channel_name, recommendation)
                
        except Exception as e:
            safe_print(f"❌ Błąd obsługi USERNOTICE: {e}")

    def start_playback(self):
        try:
            devices = self.sp.devices()
            if devices['devices']:
                device_id = devices['devices'][0]['id']
                self.sp.start_playback(device_id=device_id)
                return True
            else:
                safe_print(f"Brak aktywnych urządzeń Spotify.")
                return False
        except Exception as e:
            safe_print(f"Spotify playback error:", e)
            return False

    def start_reminder(self):
        def reminder_loop():
            # Opóźnienie pierwszego przypomnienia o 15 sekund
            time.sleep(15)
            
            while True:
                channel_name = self.get_channel_name()
                self.connection.privmsg(channel_name, ZBIORKA_MSG)
                time.sleep(15)
                self.connection.privmsg(channel_name, FOLLOW_MSG)
                time.sleep(600)
                self.connection.privmsg(channel_name, DISCORD_MSG)
                time.sleep(900)
                self.connection.privmsg(channel_name, PRIME_MSG)
                time.sleep(0)
                self.connection.privmsg(channel_name, BITS_MSG)
                time.sleep(1800)

        thread = threading.Thread(target=reminder_loop, daemon=True)
        thread.start()

    # === MONITOROWANIE STATUSU STREAMA ===
    def start_stream_monitor(self):
        """Uruchamia monitorowanie statusu streama"""
        def stream_monitor_loop():
            last_status = None
            first_check = True
            while True:
                try:
                    current_status = self.check_stream_status()
                    safe_print(f"📺 Status streama: {current_status} (poprzedni: {last_status}, pierwszy: {first_check})")
                    
                    if current_status != last_status:
                        if current_status:
                            # Stream się rozpoczął
                            safe_print(f"🔴 Wykryto rozpoczęcie streama!")
                            channel_info = self.get_channel_info(CHANNEL.lstrip('#'))
                            title = channel_info.get('title', '') if channel_info else ''
                            game = channel_info.get('game_name', '') if channel_info else ''
                            self.discord.notify_stream_status(True, title, game)
                            safe_print(f"🔴 Stream LIVE - powiadomienie Discord wysłane")
                        elif not first_check:
                            # Stream się zakończył (ale nie przy pierwszym sprawdzeniu)
                            safe_print(f"⚫ Wykryto zakończenie streama!")
                            self.discord.notify_stream_status(False)
                            safe_print(f"⚫ Stream OFFLINE - powiadomienie Discord wysłane")
                        else:
                            safe_print(f"⚫ Stream offline przy pierwszym sprawdzeniu - pomijam powiadomienie")
                        last_status = current_status
                        first_check = False
                    time.sleep(60)  # Sprawdzaj co minutę
                except Exception as e:
                    safe_print(f"❌ Błąd monitorowania streama: {e}")
                    time.sleep(60)
        
        monitor_thread = threading.Thread(target=stream_monitor_loop, daemon=True)
        monitor_thread.start()
        safe_print(f"📺 Monitor statusu streama uruchomiony")

    def check_stream_status(self):
        """Sprawdza czy stream jest live"""
        try:
            headers = {
                'Client-ID': os.getenv('TWITCH_CLIENT_ID'),
                'Authorization': f'Bearer {os.getenv("TWITCH_ACCESS_TOKEN")}'
            }
            
            # Sprawdź status streama
            stream_url = f"https://api.twitch.tv/helix/streams?user_login={CHANNEL.lstrip('#')}"
            response = requests.get(stream_url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                is_live = len(data.get('data', [])) > 0
                safe_print(f"🔍 API Twitch: kanał {CHANNEL.lstrip('#')} - {'LIVE' if is_live else 'OFFLINE'}")
                return is_live  # True jeśli stream jest live
            else:
                safe_print(f"❌ Błąd sprawdzania statusu streama: {response.status_code}")
                return None
                
        except Exception as e:
            safe_print(f"❌ Błąd API statusu streama: {e}")
            return None

    def start_daily_stats(self):
        """Uruchamia wysyłanie dziennych statystyk Discord"""
        def daily_stats_loop():
            while True:
                try:
                    # Czekaj do 20:00 każdego dnia
                    now = datetime.now()
                    target_time = now.replace(hour=20, minute=0, second=0, microsecond=0)
                    
                    # Jeśli już minęła 20:00 dzisiaj, ustaw na jutro
                    if now >= target_time:
                        target_time += timedelta(days=1)
                    
                    # Oblicz czas do czekania
                    wait_seconds = (target_time - now).total_seconds()
                    safe_print(f"📊 Następne statystyki Discord o {target_time.strftime('%Y-%m-%d %H:%M')}")
                    
                    time.sleep(wait_seconds)
                    
                    # Wyślij statystyki
                    self.discord.send_daily_stats()
                    safe_print(f"📊 Dzienne statystyki Discord wysłane")
                    
                except Exception as e:
                    safe_print(f"❌ Błąd wysyłania dziennych statystyk: {e}")
                    time.sleep(3600)  # Spróbuj ponownie za godzinę
        
        stats_thread = threading.Thread(target=daily_stats_loop, daemon=True)
        stats_thread.start()
        safe_print(f"📊 Harmonogram dziennych statystyk Discord uruchomiony")

    def start_quiz_timeout_checker(self):
        """Uruchamia sprawdzanie timeout quizu co 5 sekund"""
        def quiz_timeout_loop():
            while True:
                try:
                    quiz_timeout_msg = self.games.check_quiz_timeout()
                    if quiz_timeout_msg:
                        channel_name = self.get_channel_name()
                        self.connection.privmsg(channel_name, quiz_timeout_msg)
                    time.sleep(5)  # Sprawdzaj co 5 sekund
                except Exception as e:
                    safe_print(f"❌ Błąd sprawdzania timeout quizu: {e}")
                    time.sleep(5)
        
        quiz_thread = threading.Thread(target=quiz_timeout_loop, daemon=True)
        quiz_thread.start()
        safe_print(f"❓ Monitor timeout quizu uruchomiony")

    def start_leaderboard_updater(self):
        """Uruchamia automatyczne sprawdzanie zmian w rankingu Discord co 30 minut"""
        def leaderboard_updater_loop():
            # Pierwsze uruchomienie po 60 sekundach
            time.sleep(60)
            
            while True:
                try:
                    safe_print(f"🏆 Sprawdzam zmiany w rankingu...")
                    self.discord.update_leaderboard_if_changed(self.db)
                    
                    # Sprawdzaj co 30 minut
                    time.sleep(1800)
                    
                except Exception as e:
                    safe_print(f"❌ Błąd sprawdzania rankingu Discord: {e}")
                    time.sleep(1800)  # Spróbuj ponownie za 30 minut
        
        leaderboard_thread = threading.Thread(target=leaderboard_updater_loop, daemon=True)
        leaderboard_thread.start()
        safe_print(f"🏆 Automatyczne sprawdzanie zmian w rankingu Discord uruchomione")

    def start_shop_monitor(self):
        """Uruchamia monitorowanie zmian w sklepie i automatyczne aktualizacje Discord"""
        def shop_monitor_loop():
            # Pierwsze uruchomienie po 30 sekundach
            time.sleep(30)
            
            while True:
                try:
                    safe_print(f"🛒 Sprawdzam zmiany w sklepie...")
                    self.shop.update_shop_post_if_changed()
                    
                    # Sprawdzaj co 5 minut
                    time.sleep(300)
                    
                except Exception as e:
                    safe_print(f"❌ Błąd monitorowania sklepu: {e}")
                    time.sleep(300)  # Spróbuj ponownie za 5 minut
        
        shop_thread = threading.Thread(target=shop_monitor_loop, daemon=True)
        shop_thread.start()
        safe_print(f"🛒 Monitor zmian w sklepie uruchomiony")

    def run(self):
        self.reactor.process_forever()

if __name__ == "__main__":
    bot = TwitchBot()
    safe_print(f"Bot wystartował!")
    bot.run()
