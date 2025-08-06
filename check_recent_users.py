#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os
from datetime import datetime

def check_recent_users():
    """Sprawdza najnowszych użytkowników w bazie danych"""
    
    db_path = "users.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Baza danych {db_path} nie istnieje")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🕐 Najnowsi użytkownicy (ostatnie 10):")
        cursor.execute('''
            SELECT username, points, first_seen, last_seen 
            FROM users 
            ORDER BY first_seen DESC 
            LIMIT 10
        ''')
        
        recent_users = cursor.fetchall()
        
        if recent_users:
            for i, (username, points, first_seen, last_seen) in enumerate(recent_users, 1):
                print(f"  {i}. {username}: {points} punktów")
                print(f"     Pierwszy raz: {first_seen}")
                print(f"     Ostatnio: {last_seen}")
                print()
        else:
            print("  Brak użytkowników w bazie")
        
        print("🆕 Użytkownicy z dzisiaj:")
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT username, points, first_seen 
            FROM users 
            WHERE DATE(first_seen) = DATE('now')
            ORDER BY first_seen DESC
        ''')
        
        today_users = cursor.fetchall()
        
        if today_users:
            for username, points, first_seen in today_users:
                print(f"  • {username}: {points} punktów (dołączył: {first_seen})")
        else:
            print("  Brak nowych użytkowników dzisiaj")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Błąd: {e}")

if __name__ == "__main__":
    check_recent_users()