import sqlite3
import os
from datetime import datetime, timedelta
import threading

class UserDatabase:
    def __init__(self, db_path="users.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self.init_database()
    
    def get_connection(self):
        """Tworzy nowe połączenie z bazą danych"""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.execute('PRAGMA journal_mode=WAL')  # Lepsze współbieżne dostępy
        return conn
    
    def init_database(self):
        """Inicjalizuje bazę danych użytkowników"""
        with self.lock:
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
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('UPDATE users SET points = 0')
                affected_rows = cursor.rowcount
                
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
                
                # Sprawdź czy użytkownik istnieje
                cursor.execute('SELECT username FROM users WHERE username = ?', (username,))
                if not cursor.fetchone():
                    # Utwórz użytkownika ze wszystkimi kolumnami
                    cursor.execute('''
                        INSERT INTO users (username, points, messages_count, last_seen, first_seen, total_time_minutes, last_daily_bonus, first_message_bonus_received)
                        VALUES (?, ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0, NULL, 0)
                    ''', (username, points))
                else:
                    # Zaktualizuj istniejącego użytkownika
                    cursor.execute('''
                        UPDATE users 
                        SET points = points + ?, last_seen = CURRENT_TIMESTAMP
                        WHERE username = ?
                    ''', (points, username))
                
                conn.commit()
    
    def remove_points(self, username, points):
        """Usuwa punkty użytkownikowi (nie może zejść poniżej 0)"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE users 
                    SET points = MAX(0, points - ?), last_seen = CURRENT_TIMESTAMP
                    WHERE username = ?
                ''', (points, username))
                
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
                
                cursor.execute('''
                    UPDATE users 
                    SET points = ?, last_seen = CURRENT_TIMESTAMP
                    WHERE username = ?
                ''', (points, username))
                
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