#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skrypt zabezpieczający przed przypadkowym przywróceniem starszych backupów
"""

import os
import sqlite3
from datetime import datetime
import glob

def check_backup_integrity():
    """Sprawdza czy pliki backup nie są nowsze niż aktualna baza"""
    
    current_db = "users.db"
    backup_pattern = "users_backup_*.db"
    
    if not os.path.exists(current_db):
        print("❌ Brak aktualnej bazy danych users.db")
        return False
    
    # Pobierz czas modyfikacji aktualnej bazy
    current_mtime = os.path.getmtime(current_db)
    current_time = datetime.fromtimestamp(current_mtime)
    
    print(f"📅 Aktualna baza danych: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Znajdź wszystkie pliki backup
    backup_files = glob.glob(backup_pattern)
    
    if not backup_files:
        print("✅ Brak plików backup do sprawdzenia")
        return True
    
    suspicious_backups = []
    
    for backup_file in backup_files:
        backup_mtime = os.path.getmtime(backup_file)
        backup_time = datetime.fromtimestamp(backup_mtime)
        
        print(f"📁 Backup {backup_file}: {backup_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Sprawdź czy backup jest nowszy niż aktualna baza
        if backup_mtime > current_mtime:
            suspicious_backups.append((backup_file, backup_time))
    
    if suspicious_backups:
        print("\n⚠️  OSTRZEŻENIE: Znaleziono backupy nowsze niż aktualna baza!")
        print("To może oznaczać problem z synchronizacją OneDrive.")
        
        for backup_file, backup_time in suspicious_backups:
            print(f"   - {backup_file}: {backup_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n💡 Zalecenia:")
        print("1. Sprawdź czy OneDrive nie przywraca starszych wersji")
        print("2. Dodaj pliki *.db do .onedriveignore")
        print("3. Rozważ przeniesienie bota poza folder OneDrive")
        
        return False
    else:
        print("✅ Wszystkie backupy są starsze niż aktualna baza - OK")
        return True

def get_database_stats(db_path):
    """Pobiera statystyki z bazy danych"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Liczba użytkowników
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        # Suma punktów
        cursor.execute("SELECT SUM(points) FROM users")
        total_points = cursor.fetchone()[0] or 0
        
        # Top użytkownik
        cursor.execute("SELECT username, points FROM users ORDER BY points DESC LIMIT 1")
        top_user = cursor.fetchone()
        
        conn.close()
        
        return {
            'user_count': user_count,
            'total_points': total_points,
            'top_user': top_user
        }
    except Exception as e:
        return {'error': str(e)}

def compare_databases():
    """Porównuje aktualną bazę z najnowszym backupem"""
    
    current_db = "users.db"
    backup_files = sorted(glob.glob("users_backup_*.db"), reverse=True)
    
    if not backup_files:
        print("Brak plików backup do porównania")
        return
    
    latest_backup = backup_files[0]
    
    print(f"\n🔍 Porównanie baz danych:")
    print(f"📊 Aktualna: {current_db}")
    print(f"📊 Backup:   {latest_backup}")
    
    current_stats = get_database_stats(current_db)
    backup_stats = get_database_stats(latest_backup)
    
    if 'error' in current_stats:
        print(f"❌ Błąd odczytu aktualnej bazy: {current_stats['error']}")
        return
    
    if 'error' in backup_stats:
        print(f"❌ Błąd odczytu backup: {backup_stats['error']}")
        return
    
    print(f"\n📈 Statystyki:")
    print(f"   Użytkownicy: {current_stats['user_count']} (aktualna) vs {backup_stats['user_count']} (backup)")
    print(f"   Punkty:      {current_stats['total_points']} (aktualna) vs {backup_stats['total_points']} (backup)")
    
    if current_stats['top_user'] and backup_stats['top_user']:
        print(f"   Top user:    {current_stats['top_user'][0]} ({current_stats['top_user'][1]}) vs {backup_stats['top_user'][0]} ({backup_stats['top_user'][1]})")

if __name__ == "__main__":
    print("🛡️  Sprawdzanie integralności backupów...")
    check_backup_integrity()
    compare_databases()