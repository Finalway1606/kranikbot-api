#!/usr/bin/env python3
"""
Skrypt do sprawdzania integralności bazy danych i wykrywania problemów
"""

import sqlite3
import os
from datetime import datetime

def check_database_integrity(db_path="users.db"):
    """Sprawdza integralność bazy danych"""
    print(f"=== Sprawdzanie integralności bazy danych: {db_path} ===")
    
    if not os.path.exists(db_path):
        print(f"❌ Plik bazy danych nie istnieje: {db_path}")
        return False
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Sprawdź integralność SQLite
            print("🔍 Sprawdzanie integralności SQLite...")
            cursor.execute('PRAGMA integrity_check')
            integrity_result = cursor.fetchone()[0]
            
            if integrity_result == "ok":
                print("✅ Integralność SQLite: OK")
            else:
                print(f"❌ Integralność SQLite: {integrity_result}")
                return False
            
            # Sprawdź tryb journala
            cursor.execute('PRAGMA journal_mode')
            journal_mode = cursor.fetchone()[0]
            print(f"📝 Tryb journala: {journal_mode}")
            
            # Sprawdź tryb synchronizacji
            cursor.execute('PRAGMA synchronous')
            sync_mode = cursor.fetchone()[0]
            print(f"🔄 Tryb synchronizacji: {sync_mode}")
            
            # Sprawdź strukturę tabeli
            print("🏗️  Sprawdzanie struktury tabeli users...")
            cursor.execute("PRAGMA table_info(users)")
            columns = cursor.fetchall()
            expected_columns = [
                'username', 'points', 'messages_count', 'last_seen', 
                'first_seen', 'total_time_minutes', 'last_daily_bonus', 
                'first_message_bonus_received'
            ]
            
            actual_columns = [col[1] for col in columns]
            for expected_col in expected_columns:
                if expected_col in actual_columns:
                    print(f"✅ Kolumna {expected_col}: OK")
                else:
                    print(f"❌ Brakuje kolumny: {expected_col}")
            
            # Sprawdź liczbę użytkowników
            cursor.execute('SELECT COUNT(*) FROM users')
            user_count = cursor.fetchone()[0]
            print(f"👥 Liczba użytkowników: {user_count}")
            
            # Sprawdź top 10 użytkowników
            print("🏆 Top 10 użytkowników:")
            cursor.execute('SELECT username, points FROM users ORDER BY points DESC LIMIT 10')
            top_users = cursor.fetchall()
            for i, (username, points) in enumerate(top_users, 1):
                print(f"  {i}. {username}: {points} pkt")
            
            # Sprawdź czy są użytkownicy z ujemnymi punktami
            cursor.execute('SELECT COUNT(*) FROM users WHERE points < 0')
            negative_points = cursor.fetchone()[0]
            if negative_points > 0:
                print(f"⚠️  Użytkownicy z ujemnymi punktami: {negative_points}")
            else:
                print("✅ Brak użytkowników z ujemnymi punktami")
            
            # Sprawdź informacje o pliku
            stat = os.stat(db_path)
            print(f"📁 Rozmiar pliku: {stat.st_size} bajtów")
            print(f"📅 Ostatnia modyfikacja: {datetime.fromtimestamp(stat.st_mtime)}")
            
            return True
            
    except Exception as e:
        print(f"❌ Błąd podczas sprawdzania bazy danych: {e}")
        return False

def check_wal_files(db_path="users.db"):
    """Sprawdza czy istnieją pliki WAL"""
    print(f"\n=== Sprawdzanie plików WAL ===")
    
    wal_file = db_path + '-wal'
    shm_file = db_path + '-shm'
    
    if os.path.exists(wal_file):
        stat = os.stat(wal_file)
        print(f"⚠️  Plik WAL istnieje: {wal_file} ({stat.st_size} bajtów)")
    else:
        print(f"✅ Brak pliku WAL: {wal_file}")
    
    if os.path.exists(shm_file):
        stat = os.stat(shm_file)
        print(f"⚠️  Plik SHM istnieje: {shm_file} ({stat.st_size} bajtów)")
    else:
        print(f"✅ Brak pliku SHM: {shm_file}")

def find_all_databases():
    """Znajduje wszystkie pliki bazy danych w bieżącym katalogu"""
    print(f"\n=== Wszystkie pliki bazy danych ===")
    
    db_files = [f for f in os.listdir('.') if f.endswith('.db')]
    for db_file in sorted(db_files):
        stat = os.stat(db_file)
        print(f"📄 {db_file}: {stat.st_size} bajtów, {datetime.fromtimestamp(stat.st_mtime)}")

if __name__ == "__main__":
    # Sprawdź główną bazę danych
    check_database_integrity("users.db")
    
    # Sprawdź pliki WAL
    check_wal_files("users.db")
    
    # Sprawdź bazę sklepu
    if os.path.exists("shop.db"):
        print(f"\n" + "="*50)
        check_database_integrity("shop.db")
        check_wal_files("shop.db")
    
    # Pokaż wszystkie pliki bazy danych
    find_all_databases()
    
    print(f"\n=== Sprawdzanie zakończone ===")