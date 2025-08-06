#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skrypt do sprawdzenia zawartości bazy danych backup
"""

import sqlite3
import os

def check_backup_database():
    backup_file = "users_backup_20250806_004114.db"
    current_file = "users.db"
    
    if not os.path.exists(backup_file):
        print(f"❌ Plik backup {backup_file} nie istnieje")
        return
    
    if not os.path.exists(current_file):
        print(f"❌ Plik bieżącej bazy {current_file} nie istnieje")
        return
    
    print("🔍 Sprawdzam zawartość baz danych...")
    
    # Sprawdź backup
    print(f"\n📁 BACKUP DATABASE ({backup_file}):")
    try:
        conn_backup = sqlite3.connect(backup_file)
        cursor_backup = conn_backup.cursor()
        
        # Sprawdź konkretnych użytkowników
        cursor_backup.execute("SELECT username, points FROM users WHERE username IN ('sniffurious', 'omayakaboom') ORDER BY points DESC")
        backup_results = cursor_backup.fetchall()
        
        if backup_results:
            for username, points in backup_results:
                print(f"  {username}: {points} punktów")
        else:
            print("  Brak danych dla tych użytkowników")
        
        # Sprawdź wszystkich użytkowników w backup
        cursor_backup.execute("SELECT COUNT(*) FROM users")
        total_users = cursor_backup.fetchone()[0]
        print(f"  📊 Łącznie użytkowników w backup: {total_users}")
        
        if total_users > 0:
            cursor_backup.execute("SELECT username, points FROM users ORDER BY points DESC LIMIT 10")
            top_users = cursor_backup.fetchall()
            print("  🏆 Top 10 użytkowników w backup:")
            for username, points in top_users:
                print(f"    {username}: {points} punktów")
        
        conn_backup.close()
    except Exception as e:
        print(f"  ❌ Błąd odczytu backup: {e}")
    
    # Sprawdź bieżącą bazę
    print(f"\n📁 CURRENT DATABASE ({current_file}):")
    try:
        conn_current = sqlite3.connect(current_file)
        cursor_current = conn_current.cursor()
        
        cursor_current.execute("SELECT username, points FROM users WHERE username IN ('sniffurious', 'omayakaboom') ORDER BY points DESC")
        current_results = cursor_current.fetchall()
        
        if current_results:
            for username, points in current_results:
                print(f"  {username}: {points} punktów")
        else:
            print("  Brak danych dla tych użytkowników")
        
        conn_current.close()
    except Exception as e:
        print(f"  ❌ Błąd odczytu bieżącej bazy: {e}")
    
    print("\n✅ Sprawdzenie zakończone")

if __name__ == "__main__":
    check_backup_database()