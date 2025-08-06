#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skrypt do sprawdzenia aktualnych punktów użytkowników
"""

import sqlite3

def check_points():
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        # Sprawdź wszystkich użytkowników z "sniff" w nazwie
        cursor.execute("SELECT username, points FROM users WHERE LOWER(username) LIKE '%sniff%' ORDER BY points DESC")
        sniff_results = cursor.fetchall()
        
        print("🔍 Użytkownicy z 'sniff' w nazwie:")
        if sniff_results:
            for username, points in sniff_results:
                print(f"  {username}: {points} punktów")
        else:
            print("  Brak użytkowników z 'sniff' w nazwie")
        
        # Sprawdź konkretnych użytkowników
        cursor.execute("SELECT username, points FROM users WHERE username IN ('sniffurious', 'omayakaboom', 'Sniffurious') ORDER BY points DESC")
        results = cursor.fetchall()
        
        print("\n🔍 Konkretni użytkownicy:")
        if results:
            for username, points in results:
                print(f"  {username}: {points} punktów")
        else:
            print("  Brak danych dla tych użytkowników")
        
        # Sprawdź top 10 użytkowników
        cursor.execute("SELECT username, points FROM users ORDER BY points DESC LIMIT 10")
        top_users = cursor.fetchall()
        
        print("\n🏆 Top 10 użytkowników:")
        for i, (username, points) in enumerate(top_users, 1):
            print(f"  {i}. {username}: {points} punktów")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Błąd: {e}")

if __name__ == "__main__":
    check_points()