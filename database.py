import sqlite3
import os
import shutil
from datetime import datetime, timedelta
import threading
import glob

class UserDatabase:
    def __init__(self, db_path="users.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self.init_database()
    
    def get_connection(self):
        """Tworzy nowe połączenie z bazą danych"""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.execute('PRAGMA journal_mode=DELETE')  # Unikanie problemów z synchronizacją WAL
        conn.execute('PRAGMA synchronous=FULL')     # Pełna synchronizacja dla bezpieczeństwa danych
        return conn
    
    def _ensure_delete_mode(self):
        """Wymusza tryb DELETE i usuwa pliki WAL jeśli istnieją"""
        try:
            # Usuń pliki WAL jeśli istnieją
            wal_file = self.db_path + '-wal'
            shm_file = self.db_path + '-shm'
            
            if os.path.exists(wal_file):
                os.remove(wal_file)
            if os.path.exists(shm_file):
                os.remove(shm_file)
                
            # Wymuszenie trybu DELETE
            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                conn.execute('PRAGMA journal_mode=DELETE')
                conn.execute('PRAGMA synchronous=FULL')
                conn.commit()
        except Exception as e:
            print(f"Ostrzeżenie: Nie można wymusić trybu DELETE: {e}")
    
    def create_backup(self, reason="manual"):
        """Tworzy backup bazy danych z timestampem"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"users_backup_{timestamp}_{reason}.db"
            
            # Kopiuj bazę danych
            shutil.copy2(self.db_path, backup_filename)
            print(f"[BACKUP] Utworzono backup: {backup_filename}")
            
            # Usuń stare backupy (zachowaj tylko 5 najnowszych)
            self._cleanup_old_backups()
            
            return backup_filename
        except Exception as e:
            print(f"[BACKUP] Błąd podczas tworzenia backupu: {e}")
            return None
    
    def _cleanup_old_backups(self):
        """Usuwa stare pliki backup, zachowując tylko 5 najnowszych"""
        try:
            backup_files = [f for f in os.listdir('.') if f.startswith('users_backup_') and f.endswith('.db')]
            backup_files.sort(reverse=True)  # Najnowsze pierwsze
            
            # Usuń pliki starsze niż 5 najnowszych
            for old_backup in backup_files[5:]:
                os.remove(old_backup)
                print(f"[BACKUP] Usunięto stary backup: {old_backup}")
        except Exception as e:
            print(f"[BACKUP] Błąd podczas czyszczenia starych backupów: {e}")
    
    def _check_backup_integrity(self):
        """Sprawdza czy pliki backup nie są nowsze niż aktualna baza (zabezpieczenie przed OneDrive)"""
        try:
            if not os.path.exists(self.db_path):
                return True  # Brak bazy do sprawdzenia
            
            current_mtime = os.path.getmtime(self.db_path)
            backup_files = glob.glob("users_backup_*.db")
            
            suspicious_backups = []
            for backup_file in backup_files:
                backup_mtime = os.path.getmtime(backup_file)
                if backup_mtime > current_mtime:
                    suspicious_backups.append(backup_file)
            
            if suspicious_backups:
                print(f"[BACKUP] ⚠️  OSTRZEŻENIE: Znaleziono backupy nowsze niż aktualna baza!")
                print(f"[BACKUP] To może oznaczać problem z synchronizacją OneDrive.")
                for backup in suspicious_backups:
                    backup_time = datetime.fromtimestamp(os.path.getmtime(backup))
                    print(f"[BACKUP]   - {backup}: {backup_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"[BACKUP] Sprawdź czy OneDrive nie przywraca starszych wersji!")
                return False
            
            return True
        except Exception as e:
            print(f"[BACKUP] Błąd podczas sprawdzania integralności: {e}")
            return True  # Nie blokuj działania bota
    
    def init_database(self):
        """Inicjalizuje bazę danych użytkowników"""
        with self.lock:
            # Sprawdź integralność backupów (zabezpieczenie przed OneDrive)
            self._check_backup_integrity()
            
            # Wymuszenie trybu DELETE i usunięcie plików WAL jeśli istnieją
            self._ensure_delete_mode()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        username TEXT PRIMARY KEY,
                        points INTEGER DEFAULT 0,
                        messages_count INTEGER DEFAULT 0,
                        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        total_time_minutes INTEGER DEFAULT 0,
                        last_daily_bonus TIMESTAMP DEFAULT NULL,
                        first_message_bonus_received BOOLEAN DEFAULT 0
                    )
                ''')
                
                # Dodaj nową kolumnę do istniejących tabel (jeśli nie istnieje)
                try:
                    cursor.execute('''
                        ALTER TABLE users ADD COLUMN first_message_bonus_received BOOLEAN DEFAULT 0
                    ''')
                except sqlite3.OperationalError:
                    # Kolumna już istnieje
                    pass
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS game_stats (
                        username TEXT,
                        game_type TEXT,
                        wins INTEGER DEFAULT 0,
                        losses INTEGER DEFAULT 0,
                        total_played INTEGER DEFAULT 0,
                        PRIMARY KEY (username, game_type)
                    )
                ''')
                
                conn.commit()
    
    def get_total_users_count(self):
        """Zwraca łączną liczbę użytkowników"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT COUNT(*) FROM users')
                result = cursor.fetchone()
                return result[0] if result else 0
    
    def get_total_points_distributed(self):
        """Zwraca łączną liczbę rozdanych punktów"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT SUM(points) FROM users')
                result = cursor.fetchone()
                return result[0] if result and result[0] else 0
    
    def reset_all_points(self):
        """Resetuje punkty wszystkich użytkowników do 0"""
        # Utwórz backup przed resetowaniem
        self.create_backup("reset_all_points")
        
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('UPDATE users SET points = 0')
                affected_rows = cursor.rowcount
                
                print(f"[DB] Zresetowano punkty dla {affected_rows} użytkowników")
                
                conn.commit()
                return affected_rows
    
    def get_user(self, username):
        """Pobiera dane użytkownika"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
                user = cursor.fetchone()
                
                if not user:
                    # Tworzymy nowego użytkownika ze wszystkimi kolumnami
                    cursor.execute('''
                        INSERT INTO users (username, points, messages_count, last_seen, first_seen, total_time_minutes, last_daily_bonus, first_message_bonus_received)
                        VALUES (?, 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0, NULL, 0)
                    ''', (username,))
                    conn.commit()
                    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
                    user = cursor.fetchone()
                
                return user
    
    def add_points(self, username, points, is_follower=True):
        """Dodaje punkty użytkownikowi - tylko dla followerów"""
        if not is_follower:
            return  # Nie dodawaj punktów jeśli nie jest followerem
            
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Sprawdź obecne punkty przed zmianą
                cursor.execute('SELECT points FROM users WHERE username = ?', (username,))
                result = cursor.fetchone()
                old_points = result[0] if result else 0
                
                # Sprawdź czy użytkownik istnieje
                cursor.execute('SELECT username FROM users WHERE username = ?', (username,))
                if not cursor.fetchone():
                    # Utwórz użytkownika ze wszystkimi kolumnami
                    cursor.execute('''
                        INSERT INTO users (username, points, messages_count, last_seen, first_seen, total_time_minutes, last_daily_bonus, first_message_bonus_received)
                        VALUES (?, ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0, NULL, 0)
                    ''', (username, points))
                    print(f"[DB] Nowy użytkownik {username}: 0 -> {points} punktów")
                else:
                    # Zaktualizuj istniejącego użytkownika
                    cursor.execute('''
                        UPDATE users 
                        SET points = points + ?, last_seen = CURRENT_TIMESTAMP
                        WHERE username = ?
                    ''', (points, username))
                    print(f"[DB] Dodano punkty {username}: {old_points} -> {old_points + points} (+{points})")
                
                conn.commit()
    
    def remove_points(self, username, points):
        """Usuwa punkty użytkownikowi (nie może zejść poniżej 0)"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Sprawdź obecne punkty przed zmianą
                cursor.execute('SELECT points FROM users WHERE username = ?', (username,))
                result = cursor.fetchone()
                old_points = result[0] if result else 0
                
                cursor.execute('''
                    UPDATE users 
                    SET points = MAX(0, points - ?), last_seen = CURRENT_TIMESTAMP
                    WHERE username = ?
                ''', (points, username))
                
                new_points = max(0, old_points - points)
                print(f"[DB] Usunięto punkty {username}: {old_points} -> {new_points} (-{points})")
                
                conn.commit()
    
    def add_message(self, username, is_follower=True):
        """Dodaje wiadomość i punkty tylko za pierwszą wiadomość (10 pkt) - tylko dla followerów"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Sprawdź czy użytkownik istnieje i czy już otrzymał bonus za pierwszą wiadomość
                cursor.execute('''
                    SELECT first_message_bonus_received FROM users WHERE username = ?
                ''', (username,))
                result = cursor.fetchone()
                
                if not result:
                    # Nowy użytkownik - daj 10 punktów za pierwszą wiadomość tylko jeśli jest followerem
                    points = 10 if is_follower else 0
                    cursor.execute('''
                        INSERT INTO users (username, points, messages_count, last_seen, first_seen, first_message_bonus_received)
                        VALUES (?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?)
                    ''', (username, points, 1 if is_follower else 0))
                    return points  # Zwróć liczbę punktów za pierwszą wiadomość
                else:
                    # Istniejący użytkownik - tylko zwiększ licznik wiadomości, bez punktów
                    cursor.execute('''
                        UPDATE users 
                        SET messages_count = messages_count + 1, 
                            last_seen = CURRENT_TIMESTAMP
                        WHERE username = ?
                    ''', (username,))
                    return 0  # Brak punktów za kolejne wiadomości
                
                conn.commit()
    
    def get_top_users(self, limit=10):
        """Pobiera ranking użytkowników (bez botów i z punktami > 0)"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Lista botów i użytkowników do wykluczenia z rankingu
                excluded_bots = ['streamelements', 'moobot', 'nightbot', 'fossabot', 'wizebot', 'wuhdo', 'kranik1606', 'kranikbot']
                placeholders = ','.join(['?' for _ in excluded_bots])
                
                cursor.execute(f'''
                    SELECT username, points, messages_count 
                    FROM users 
                    WHERE username NOT IN ({placeholders}) AND points > 0
                    ORDER BY points DESC 
                    LIMIT ?
                ''', (*excluded_bots, limit))
                
                return cursor.fetchall()
    
    def daily_bonus(self, username, is_follower=True):
        """Sprawdza i daje dzienny bonus - tylko dla followerów"""
        if not is_follower:
            return 0  # Nie daj bonusu jeśli nie jest followerem
            
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT last_daily_bonus FROM users WHERE username = ?
                ''', (username,))
                
                result = cursor.fetchone()
                if not result:
                    # Utwórz użytkownika jeśli nie istnieje ze wszystkimi kolumnami
                    cursor.execute('''
                        INSERT INTO users (username, points, messages_count, last_seen, first_seen, total_time_minutes, last_daily_bonus, first_message_bonus_received)
                        VALUES (?, 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0, NULL, 0)
                    ''', (username,))
                    result = (None,)
                
                last_bonus = result[0]
                now = datetime.now()
                
                if not last_bonus or datetime.fromisoformat(last_bonus) < now - timedelta(days=1):
                    # Daj dzienny bonus
                    bonus_points = 50
                    cursor.execute('''
                        UPDATE users 
                        SET points = points + ?, last_daily_bonus = ?
                        WHERE username = ?
                    ''', (bonus_points, now.isoformat(), username))
                    
                    conn.commit()
                    return bonus_points
                
                return 0
    
    def update_game_stats(self, username, game_type, won=False):
        """Aktualizuje statystyki gier"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR IGNORE INTO game_stats (username, game_type, wins, losses, total_played)
                    VALUES (?, ?, 0, 0, 0)
                ''', (username, game_type))
                
                if won:
                    cursor.execute('''
                        UPDATE game_stats 
                        SET wins = wins + 1, total_played = total_played + 1
                        WHERE username = ? AND game_type = ?
                    ''', (username, game_type))
                else:
                    cursor.execute('''
                        UPDATE game_stats 
                        SET losses = losses + 1, total_played = total_played + 1
                        WHERE username = ? AND game_type = ?
                    ''', (username, game_type))
                
                conn.commit()

    def get_all_users_with_points(self):
        """Pobiera wszystkich użytkowników z ich punktami"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT username, points FROM users WHERE points > 0')
                return cursor.fetchall()

    def set_user_points(self, username, points):
        """Ustawia konkretną liczbę punktów użytkownikowi"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Sprawdź obecne punkty przed zmianą
                cursor.execute('SELECT points FROM users WHERE username = ?', (username,))
                result = cursor.fetchone()
                old_points = result[0] if result else 0
                
                cursor.execute('''
                    UPDATE users 
                    SET points = ?, last_seen = CURRENT_TIMESTAMP
                    WHERE username = ?
                ''', (points, username))
                
                print(f"[DB] Ustawiono punkty {username}: {old_points} -> {points}")
                
                conn.commit()

    def get_user_points(self, username):
        """Pobiera punkty użytkownika"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT points FROM users WHERE username = ?', (username,))
                result = cursor.fetchone()
                
                if result:
                    return result[0]
                else:
                    # Jeśli użytkownik nie istnieje, zwróć 0
                    return 0

    def get_daily_stats(self):
        """Pobiera dzienne statystyki bota"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {
                    'new_users': 0,
                    'games_played': 0,
                    'rewards_bought': 0,
                    'points_given': 0,
                    'new_followers': 0,
                    'new_subs': 0
                }
                
                try:
                    # Nowi użytkownicy dzisiaj
                    cursor.execute('''
                        SELECT COUNT(*) FROM users 
                        WHERE DATE(first_seen) = DATE('now')
                    ''')
                    result = cursor.fetchone()
                    stats['new_users'] = result[0] if result else 0
                    
                    # Gry rozegrane dzisiaj (suma wszystkich gier)
                    cursor.execute('''
                        SELECT SUM(total_played) FROM game_stats
                    ''')
                    result = cursor.fetchone()
                    stats['games_played'] = result[0] if result and result[0] else 0
                    
                    # Punkty rozdane dzisiaj (przybliżenie - suma wszystkich punktów)
                    cursor.execute('''
                        SELECT SUM(points) FROM users WHERE points > 0
                    ''')
                    result = cursor.fetchone()
                    stats['points_given'] = result[0] if result and result[0] else 0
                    
                    # Nagrody kupione i nowi followerzy/subskrybenci - na razie 0
                    # (można rozszerzyć gdy będą dostępne dane)
                    stats['rewards_bought'] = 0
                    stats['new_followers'] = 0
                    stats['new_subs'] = 0
                    
                except Exception as e:
                    print(f"[DB] Błąd pobierania dziennych statystyk: {e}")
                
                return stats