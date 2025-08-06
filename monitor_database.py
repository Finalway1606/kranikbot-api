#!/usr/bin/env python3
"""
Skrypt do monitorowania zmian w bazie danych użytkowników
Pomaga w debugowaniu problemu z przywracaniem rankingu
"""

import sqlite3
import time
import os
from datetime import datetime

class DatabaseMonitor:
    def __init__(self, db_path="users.db"):
        self.db_path = db_path
        self.last_check = {}
        self.monitoring = True
        
    def get_current_state(self):
        """Pobiera aktualny stan bazy danych"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT username, points FROM users ORDER BY points DESC LIMIT 20')
                return dict(cursor.fetchall())
        except Exception as e:
            print(f"Błąd podczas pobierania stanu bazy: {e}")
            return {}
    
    def check_for_changes(self):
        """Sprawdza czy nastąpiły zmiany w bazie danych"""
        current_state = self.get_current_state()
        
        if not self.last_check:
            self.last_check = current_state
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Rozpoczęto monitorowanie bazy danych")
            return
        
        changes_detected = False
        
        # Sprawdź zmiany w punktach
        for username, points in current_state.items():
            if username in self.last_check:
                old_points = self.last_check[username]
                if old_points != points:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ZMIANA: {username}: {old_points} -> {points} punktów")
                    changes_detected = True
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] NOWY: {username}: {points} punktów")
                changes_detected = True
        
        # Sprawdź usunięte użytkowników
        for username in self.last_check:
            if username not in current_state:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] USUNIĘTY: {username}")
                changes_detected = True
        
        if changes_detected:
            # Sprawdź informacje o pliku
            stat = os.stat(self.db_path)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Plik zmodyfikowany: {datetime.fromtimestamp(stat.st_mtime)}")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Rozmiar pliku: {stat.st_size} bajtów")
        
        self.last_check = current_state
    
    def start_monitoring(self, interval=5):
        """Rozpoczyna monitorowanie z określonym interwałem"""
        print(f"Rozpoczynam monitorowanie bazy danych {self.db_path} co {interval} sekund...")
        print("Naciśnij Ctrl+C aby zatrzymać")
        
        try:
            while self.monitoring:
                self.check_for_changes()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nZatrzymano monitorowanie")
        except Exception as e:
            print(f"Błąd podczas monitorowania: {e}")

if __name__ == "__main__":
    monitor = DatabaseMonitor()
    monitor.start_monitoring()