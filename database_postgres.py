import os
import psycopg2
import sqlite3
import threading
from datetime import datetime
import shutil
import glob

class UserDatabase:
    def __init__(self, db_path="users.db"):
        self.lock = threading.Lock()
        
        # Sprawdź czy jest dostępna PostgreSQL (dla Render)
        database_url = os.getenv('DATABASE_URL')
        
        if database_url:
            # Użyj PostgreSQL na Render
            self.use_postgres = True
            self.database_url = database_url
            print(f"[DB] Używam PostgreSQL: {database_url[:20]}...")
        else:
            # Użyj SQLite lokalnie
            self.use_postgres = False
            self.db_path = db_path
            print(f"[DB] Używam SQLite: {db_path}")
        
        self.init_database()
    
    def get_connection(self):
        """Zwraca połączenie z bazą danych"""
        if self.use_postgres:
            return psycopg2.connect(self.database_url)
        else:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            conn.execute('PRAGMA journal_mode=DELETE')
            conn.execute('PRAGMA synchronous=FULL')
            return conn
    
    def init_database(self):
        """Inicjalizuje bazę danych"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.use_postgres:
                    # PostgreSQL schema
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS users (
                            username VARCHAR(255) PRIMARY KEY,
                            points INTEGER DEFAULT 0,
                            messages_count INTEGER DEFAULT 0,
                            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            total_time_minutes INTEGER DEFAULT 0,
                            last_daily_bonus TIMESTAMP DEFAULT NULL,
                            first_message_bonus_received BOOLEAN DEFAULT FALSE
                        )
                    ''')
                    
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS game_stats (
                            username VARCHAR(255),
                            game_type VARCHAR(255),
                            wins INTEGER DEFAULT 0,
                            losses INTEGER DEFAULT 0,
                            total_played INTEGER DEFAULT 0,
                            PRIMARY KEY (username, game_type)
                        )
                    ''')
                else:
                    # SQLite schema (jak wcześniej)
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
                print(f"[DB] Baza danych zainicjalizowana ({'PostgreSQL' if self.use_postgres else 'SQLite'})")
    
    def add_points(self, username, points, is_follower=True):
        """Dodaje punkty użytkownikowi"""
        if not is_follower:
            return
            
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.use_postgres:
                    # PostgreSQL syntax
                    cursor.execute('SELECT points FROM users WHERE username = %s', (username,))
                    result = cursor.fetchone()
                    old_points = result[0] if result else 0
                    
                    cursor.execute('SELECT username FROM users WHERE username = %s', (username,))
                    if not cursor.fetchone():
                        cursor.execute('''
                            INSERT INTO users (username, points, messages_count, last_seen, first_seen, total_time_minutes, last_daily_bonus, first_message_bonus_received)
                            VALUES (%s, %s, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0, NULL, FALSE)
                        ''', (username, points))
                        print(f"[DB] Nowy użytkownik {username}: 0 -> {points} punktów")
                    else:
                        cursor.execute('''
                            UPDATE users 
                            SET points = points + %s, last_seen = CURRENT_TIMESTAMP
                            WHERE username = %s
                        ''', (points, username))
                        print(f"[DB] Dodano punkty {username}: {old_points} -> {old_points + points} (+{points})")
                else:
                    # SQLite syntax (jak wcześniej)
                    cursor.execute('SELECT points FROM users WHERE username = ?', (username,))
                    result = cursor.fetchone()
                    old_points = result[0] if result else 0
                    
                    cursor.execute('SELECT username FROM users WHERE username = ?', (username,))
                    if not cursor.fetchone():
                        cursor.execute('''
                            INSERT INTO users (username, points, messages_count, last_seen, first_seen, total_time_minutes, last_daily_bonus, first_message_bonus_received)
                            VALUES (?, ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0, NULL, 0)
                        ''', (username, points))
                        print(f"[DB] Nowy użytkownik {username}: 0 -> {points} punktów")
                    else:
                        cursor.execute('''
                            UPDATE users 
                            SET points = points + ?, last_seen = CURRENT_TIMESTAMP
                            WHERE username = ?
                        ''', (points, username))
                        print(f"[DB] Dodano punkty {username}: {old_points} -> {old_points + points} (+{points})")
                
                conn.commit()
    
    def get_top_users(self, limit=10):
        """Pobiera top użytkowników"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.use_postgres:
                    cursor.execute('''
                        SELECT username, points FROM users 
                        WHERE username NOT LIKE '%bot%' 
                        ORDER BY points DESC 
                        LIMIT %s
                    ''', (limit,))
                else:
                    cursor.execute('''
                        SELECT username, points FROM users 
                        WHERE username NOT LIKE '%bot%' 
                        ORDER BY points DESC 
                        LIMIT ?
                    ''', (limit,))
                
                return cursor.fetchall()
    
    def get_user_points(self, username):
        """Pobiera punkty użytkownika"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.use_postgres:
                    cursor.execute('SELECT points FROM users WHERE username = %s', (username,))
                else:
                    cursor.execute('SELECT points FROM users WHERE username = ?', (username,))
                
                result = cursor.fetchone()
                return result[0] if result else 0
    
    def set_user_points(self, username, points):
        """Ustawia punkty użytkownika"""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.use_postgres:
                    cursor.execute('SELECT points FROM users WHERE username = %s', (username,))
                    result = cursor.fetchone()
                    old_points = result[0] if result else 0
                    
                    cursor.execute('''
                        INSERT INTO users (username, points, messages_count, last_seen, first_seen, total_time_minutes, last_daily_bonus, first_message_bonus_received)
                        VALUES (%s, %s, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0, NULL, FALSE)
                        ON CONFLICT (username) DO UPDATE SET
                        points = EXCLUDED.points,
                        last_seen = CURRENT_TIMESTAMP
                    ''', (username, points))
                else:
                    cursor.execute('SELECT points FROM users WHERE username = ?', (username,))
                    result = cursor.fetchone()
                    old_points = result[0] if result else 0
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO users (username, points, messages_count, last_seen, first_seen, total_time_minutes, last_daily_bonus, first_message_bonus_received)
                        VALUES (?, ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0, NULL, 0)
                    ''', (username, points))
                
                print(f"[DB] Ustawiono punkty {username}: {old_points} -> {points}")
                conn.commit()