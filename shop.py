import sqlite3
import threading
import hashlib
import json
from datetime import datetime, timedelta
from database import UserDatabase
from discord_integration import DiscordIntegration

class Shop:
    def __init__(self, db: UserDatabase):
        self.db = db
        self.lock = threading.Lock()
        self.db_path = "shop.db"
        self.discord = DiscordIntegration()
        
        # System monitorowania zmian
        self.last_shop_hash = None
        self.shop_channel_id = 1401909828510679112  # ID kanału do aktualizacji sklepu
        self.last_shop_message_id = None
        
        # Dostępne nagrody w sklepie
        self.rewards = {
            "vip_hour": {
                "name": "VIP na godzinę",
                "price": 800,
                "description": "Status VIP na 1 godzinę",
                "duration_hours": 1
            },
            "stream_title": {
                "name": "Zmiana tytułu streama",
                "price": 1000,
                "description": "Zmiana tytułu streama na 30 minut",
                "duration_hours": 0.5
            },
            "discord_role": {
                "name": "Rola VIP Discord",
                "price": 800,
                "description": "Rola VIP na Discordzie na tydzień",
                "duration_hours": 168  # 7 dni
            },
            "stream_game": {
                "name": "Wybór gry na stream",
                "price": 2000,
                "description": "Wybór gry na cały stream",
                "duration_hours": 4  # Średni czas streama
            },
            "challenge": {
                "name": "Challenge dla streamera",
                "price": 1500,
                "description": "Wymyślenie wyzwania do wykonania w grze",
                "duration_hours": 0.5  # 30 minut na wykonanie
            },
            "dedication": {
                "name": "Dedykacja na streamie",
                "price": 800,
                "description": "Osobista dedykacja/pozdrowienia na żywo",
                "duration_hours": 0.1  # 6 minut na realizację
            },
            "sing_song": {
                "name": "Śpiewanie piosenki",
                "price": 1100,
                "description": "Zaśpiewanie wybranej piosenki na streamie",
                "duration_hours": 0.033  # 2 minuty na realizację
            },
            "custom_command": {
                "name": "Własna komenda",
                "price": 3500,
                "description": "Stworzenie własnej komendy bota na tydzień",
                "duration_hours": 168  # 7 dni
            }
        }
        
        self.init_shop_database()
    
    def get_connection(self):
        """Tworzy nowe połączenie z bazą danych sklepu"""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.execute('PRAGMA journal_mode=WAL')
        return conn
    
    def init_shop_database(self):
        """Inicjalizuje bazę danych sklepu"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS purchases (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        reward_id TEXT NOT NULL,
                        purchase_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1,
                        used BOOLEAN DEFAULT 0
                    )
                ''')
                
                conn.commit()
    
    def get_shop_list(self):
        """Zwraca listę dostępnych nagród"""
        shop_text = "🛒 SKLEP NAGRÓD: "
        for reward_id, reward in self.rewards.items():
            shop_text += f"| {reward['name']}: {reward['price']} pkt "
        
        return shop_text + "| Użyj: !kup <nagroda>"
    
    def buy_reward(self, username, reward_id):
        """Kupuje nagrodę za punkty"""
        
        if reward_id not in self.rewards:
            available = ", ".join(self.rewards.keys())
            return f"❌ @{username}, nieznana nagroda! Dostępne: {available}"
        
        reward = self.rewards[reward_id]
        
        # Specjalne uprawnienia dla właściciela bota
        is_owner = username.lower() == "kranik1606"
        
        # Sprawdź czy użytkownik już ma aktywną nagrodę tego typu (tylko dla zwykłych użytkowników)
        if not is_owner and self.has_active_reward(username, reward_id):
            return f"❌ @{username}, już masz aktywną nagrodę: {reward['name']}!"
        
        if not is_owner:
            # Sprawdź punkty tylko dla zwykłych użytkowników
            user = self.db.get_user(username)
            current_points = user[1]
            
            if current_points < reward['price']:
                return f"❌ @{username}, potrzebujesz {reward['price']} punktów! Masz tylko {current_points}."
            
            # Odejmij punkty tylko zwykłym użytkownikom
            self.db.remove_points(username, reward['price'])
        
        # Dodaj nagrodę do inwentarza
        expires_at = datetime.now() + timedelta(hours=reward['duration_hours'])
        
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO purchases (username, reward_id, expires_at)
                    VALUES (?, ?, ?)
                ''', (username, reward_id, expires_at.isoformat()))
                conn.commit()
        
        # Format czasu zależny od długości trwania nagrody
        if reward['duration_hours'] >= 24:
            time_format = expires_at.strftime('%d.%m %H:%M')  # Data i godzina dla nagród 24h+
        else:
            time_format = expires_at.strftime('%H:%M')  # Tylko godzina dla krótkich nagród
        
        # Automatyczne nadawanie roli Discord - działa dla wszystkich
        if reward_id == 'discord_role':
            print(f"🎭 Próba automatycznego nadania roli Discord dla {username}")
            self.discord.assign_role_async(username, reward['duration_hours'])
        
        # Powiadomienie Discord o zakupie nagrody (tylko dla zwykłych użytkowników)
        if not is_owner:
            self.discord.notify_reward_purchase(
                username, 
                reward['name'], 
                reward['price'], 
                reward['duration_hours']
            )
            
            # Jeśli nagroda wymaga ręcznej akcji (oprócz discord_role), poproś moderatorów
        if reward_id in ['vip_hour', 'stream_title', 'stream_game', 'challenge', 'dedication', 'sing_song', 'custom_command']:
            action_details = self._get_action_details(reward_id, reward)
            action_type = reward_id.split('_')[0] if '_' in reward_id else reward_id
            self.discord.request_manual_action(
                action_type,
                username,
                action_details
            )
        
        if is_owner:
            return f"👑 @{username} (WŁAŚCICIEL) otrzymał: {reward['name']} ZA DARMO! Aktywne do: {time_format}"
        else:
            return f"🎁 @{username} kupił: {reward['name']} za {reward['price']} punktów! Aktywne do: {time_format}"
    
    def has_active_reward(self, username, reward_id):
        """Sprawdza czy użytkownik ma aktywną nagrodę"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM purchases 
                    WHERE username = ? AND reward_id = ? 
                    AND is_active = 1 AND expires_at > ?
                ''', (username, reward_id, datetime.now().isoformat()))
                
                count = cursor.fetchone()[0]
                return count > 0
    
    def get_user_inventory(self, username):
        """Pobiera inwentarz użytkownika"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT reward_id, expires_at, used FROM purchases 
                    WHERE username = ? AND is_active = 1 AND expires_at > ?
                    ORDER BY expires_at ASC
                ''', (username, datetime.now().isoformat()))
                
                active_rewards = cursor.fetchall()
        
        if not active_rewards:
            return f"📦 @{username}, twój inwentarz jest pusty!"
        
        # Skrócona wersja aby nie przekroczyć limitu IRC (512 bajtów)
        inventory_text = f"📦 @{username}: "
        for reward_id, expires_at, used in active_rewards:
            reward_name = self.rewards[reward_id]['name']
            reward_duration = self.rewards[reward_id]['duration_hours']
            expires_datetime = datetime.fromisoformat(expires_at)
            
            # Skrócony format czasu
            if reward_duration >= 24:
                expires_time = expires_datetime.strftime('%d.%m %H:%M')
            else:
                expires_time = expires_datetime.strftime('%H:%M')
            
            # Skrócone nazwy nagród
            short_names = {
                'VIP na godzinę': 'VIP',
                'Zmiana tytułu streama': 'Tytuł',
                'Rola VIP Discord': 'Discord',
                'Wybór gry na stream': 'Gra',
                'Challenge dla streamera': 'Challenge',
                'Dedykacja na streamie': 'Dedykacja',
                'Śpiewanie piosenki': 'Piosenka',
                'Własna komenda': 'Komenda'
            }
            short_name = short_names.get(reward_name, reward_name[:8])
            
            status = "✅" if not used else "🔄"
            inventory_text += f"{status}{short_name}({expires_time}) "
            
            # Sprawdź długość wiadomości (bezpieczny limit ~400 znaków)
            if len(inventory_text) > 400:
                inventory_text += "..."
                break
        
        return inventory_text
    
    def cleanup_expired_rewards(self):
        """Usuwa wygasłe nagrody"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE purchases 
                    SET is_active = 0 
                    WHERE expires_at <= ? AND is_active = 1
                ''', (datetime.now().isoformat(),))
                conn.commit()
    
    def use_reward(self, username, reward_id):
        """Oznacza nagrodę jako użytą"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE purchases 
                    SET used = 1 
                    WHERE username = ? AND reward_id = ? AND is_active = 1 AND expires_at > ?
                ''', (username, reward_id, datetime.now().isoformat()))
                conn.commit()
                
                return cursor.rowcount > 0
    
    def remove_reward(self, target_username, reward_id):
        """Zabiera nagrodę użytkownikowi (tylko dla moderatorów/właściciela)"""
        if reward_id not in self.rewards:
            available = ", ".join(self.rewards.keys())
            return f"❌ Nieznana nagroda! Dostępne: {available}"
        
        reward = self.rewards[reward_id]
        
        # Sprawdź czy użytkownik ma aktywną nagrodę tego typu
        if not self.has_active_reward(target_username, reward_id):
            return f"❌ @{target_username} nie ma aktywnej nagrody: {reward['name']}"
        
        # Usuń nagrodę z inwentarza
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE purchases 
                    SET is_active = 0 
                    WHERE username = ? AND reward_id = ? AND is_active = 1 AND expires_at > ?
                ''', (target_username, reward_id, datetime.now().isoformat()))
                conn.commit()
                
                if cursor.rowcount > 0:
                    return f"🗑️ Zabrano nagrodę: {reward['name']} użytkownikowi @{target_username}"
                else:
                    return f"❌ Nie udało się zabrać nagrody @{target_username}"
    
    def give_reward_as_owner(self, target_username, reward_id):
        """Daje nagrodę użytkownikowi jako właściciel (za darmo)"""
        if reward_id not in self.rewards:
            available = ", ".join(self.rewards.keys())
            return f"❌ Nieznana nagroda! Dostępne: {available}"
        
        reward = self.rewards[reward_id]
        
        # Sprawdź czy użytkownik już ma aktywną nagrodę tego typu
        if self.has_active_reward(target_username, reward_id):
            return f"❌ @{target_username} już ma aktywną nagrodę: {reward['name']}!"
        
        # Dodaj nagrodę do inwentarza (bez odejmowania punktów)
        expires_at = datetime.now() + timedelta(hours=reward['duration_hours'])
        
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO purchases (username, reward_id, expires_at)
                    VALUES (?, ?, ?)
                ''', (target_username, reward_id, expires_at.isoformat()))
                conn.commit()
        
        # Format czasu zależny od długości trwania nagrody
        if reward['duration_hours'] >= 24:
            time_format = expires_at.strftime('%d.%m %H:%M')  # Data i godzina dla nagród 24h+
        else:
            time_format = expires_at.strftime('%H:%M')  # Tylko godzina dla krótkich nagród
        
        # Automatyczne nadawanie roli Discord
        if reward_id == 'discord_role':
            print(f"🎭 Próba automatycznego nadania roli Discord dla {target_username}")
            self.discord.assign_role_async(target_username, reward['duration_hours'])
        
        # Powiadomienie Discord o darowanej nagrodzie
        self.discord.notify_reward_purchase(
            target_username, 
            reward['name'], 
            0,  # Cena 0 - za darmo
            reward['duration_hours']
        )
        
        # Jeśli nagroda wymaga ręcznej akcji (oprócz discord_role), poproś moderatorów
        if reward_id in ['vip_hour', 'stream_title', 'stream_game', 'challenge', 'dedication', 'sing_song', 'custom_command']:
            action_details = self._get_action_details(reward_id, reward)
            action_type = reward_id.split('_')[0] if '_' in reward_id else reward_id
            self.discord.request_manual_action(
                action_type,
                target_username,
                action_details
            )
        
        return f"🎁👑 @{target_username} otrzymał od właściciela: {reward['name']} ZA DARMO! Aktywne do: {time_format}"

    def reset_all_rewards(self):
        """Usuwa wszystkie aktywne nagrody wszystkich użytkowników (tylko dla właściciela)"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Dezaktywuj wszystkie aktywne nagrody
                cursor.execute('''
                    UPDATE purchases 
                    SET is_active = 0 
                    WHERE is_active = 1
                ''')
                affected_rows = cursor.rowcount
                conn.commit()
                
                return affected_rows

    def _get_action_details(self, reward_id, reward):
        """Zwraca szczegóły akcji wymaganej dla danej nagrody"""
        details_map = {
            'vip_hour': f"Nadaj VIP na Twitchu na {reward['duration_hours']} godzin",
            'stream_title': f"Zmień tytuł streama na {reward['duration_hours']} godzin (użytkownik poda nowy tytuł)",
            'discord_role': f"Nadaj specjalną rolę Discord na {reward['duration_hours']} godzin",
            'stream_game': f"Pozwól wybrać grę na stream na {reward['duration_hours']} godzin",
            'challenge': f"Wykonaj wyzwanie wymyślone przez użytkownika w grze (czas: {int(reward['duration_hours']*60)} minut)",
            'dedication': f"Przekaż dedykację/pozdrowienia od użytkownika na żywo (czas: {int(reward['duration_hours']*60)} minut)",
            'sing_song': f"Zaśpiewaj piosenkę wybraną przez użytkownika (czas: {int(reward['duration_hours']*60)} minut)",
            'custom_command': f"Stwórz własną komendę dla użytkownika na {int(reward['duration_hours']/24)} dni"
        }
        return details_map.get(reward_id, f"Realizuj nagrodę: {reward['name']}")

    def get_shop_hash(self):
        """Generuje hash aktualnego stanu sklepu"""
        shop_data = json.dumps(self.rewards, sort_keys=True)
        return hashlib.md5(shop_data.encode()).hexdigest()

    def check_shop_changes(self):
        """Sprawdza czy sklep się zmienił od ostatniego sprawdzenia"""
        current_hash = self.get_shop_hash()
        
        if self.last_shop_hash is None:
            self.last_shop_hash = current_hash
            return False  # Pierwsza inicjalizacja - nie wysyłaj wiadomości
        
        if current_hash != self.last_shop_hash:
            self.last_shop_hash = current_hash
            return True  # Sklep się zmienił
        
        return False  # Brak zmian
    
    def initialize_shop_hash(self):
        """Inicjalizuje hash sklepu bez wysyłania wiadomości na Discord"""
        current_hash = self.get_shop_hash()
        if current_hash is not None:
            self.last_shop_hash = current_hash
            print("ℹ️ Zainicjalizowano hash sklepu bez wysyłania wiadomości")

    def generate_shop_embed_data(self):
        """Generuje dane dla embed Discord z aktualnym sklepem"""
        embed_data = {
            "title": "🛒 SKLEP NAGRÓD",
            "description": "Kup nagrody za punkty aktywności!",
            "color": 0x00ff00,  # Zielony kolor
            "fields": [],
            "footer": {
                "text": f"Ostatnia aktualizacja: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            }
        }
        
        # Dodaj każdą nagrodę jako osobne pole
        for reward_id, reward in self.rewards.items():
            duration_text = ""
            if reward['duration_hours'] >= 24:
                days = int(reward['duration_hours'] / 24)
                duration_text = f" ({days} dni)" if days > 1 else " (1 dzień)"
            elif reward['duration_hours'] >= 1:
                hours = int(reward['duration_hours'])
                duration_text = f" ({hours}h)" if hours > 1 else " (1h)"
            else:
                minutes = int(reward['duration_hours'] * 60)
                duration_text = f" ({minutes} min)"
            
            field_data = {
                "name": f"💎 {reward['name']} - {reward['price']} pkt",
                "value": f"{reward['description']}{duration_text}\n`!kup {reward_id}`",
                "inline": True
            }
            embed_data["fields"].append(field_data)
        
        # Dodaj instrukcje
        embed_data["fields"].append({
            "name": "📋 Jak kupować?",
            "value": "Użyj komendy `!kup <id_nagrody>` na czacie Twitch\nSprawdź swoje punkty: `!punkty`\nSprawdź inwentarz: `!inwentarz`",
            "inline": False
        })
        
        return embed_data

    def update_shop_post_if_changed(self):
        """Aktualizuje post ze sklepem na Discord tylko jeśli coś się zmieniło"""
        if self.check_shop_changes():
            print("🔄 Wykryto zmiany w sklepie - aktualizuję post na Discord...")
            embed_data = self.generate_shop_embed_data()
            
            # Wyślij aktualizację przez Discord integration (asynchronicznie)
            try:
                self.discord.update_shop_post_async(
                    channel_id=self.shop_channel_id,
                    embed_data=embed_data,
                    message_id=self.last_shop_message_id
                )
                print("✅ Rozpoczęto aktualizację postu ze sklepem na Discord")
            except Exception as e:
                print(f"❌ Błąd podczas aktualizacji postu ze sklepem: {e}")
        else:
            print("ℹ️ Brak zmian w sklepie - nie aktualizuję postu")

    def force_update_shop_post(self):
        """Wymusza aktualizację postu ze sklepem na Discord"""
        print("🔄 Wymuszam aktualizację postu ze sklepem na Discord...")
        embed_data = self.generate_shop_embed_data()
        
        try:
            # Uruchom asynchronicznie
            self.discord.update_shop_post_async(
                channel_id=self.shop_channel_id,
                embed_data=embed_data,
                message_id=None  # Wyślij nową wiadomość
            )
            self.last_shop_hash = self.get_shop_hash()  # Zaktualizuj hash
            print("✅ Rozpoczęto wysyłanie postu ze sklepem na Discord")
            return True
        except Exception as e:
            print(f"❌ Błąd podczas wysyłania postu ze sklepem: {e}")
            return False