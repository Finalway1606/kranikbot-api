#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from database import UserDatabase

def clear_testuser_points():
    """Czyści punkty użytkownika testuser"""
    
    db = UserDatabase()
    
    # Sprawdź obecne punkty
    current_points = db.get_user_points('testuser')
    print(f"Obecne punkty testuser: {current_points}")
    
    if current_points > 0:
        # Wyczyść punkty (ustaw na 0)
        db.set_user_points('testuser', 0)
        print(f"✅ Punkty testuser zostały wyczyszczone: {current_points} -> 0")
    else:
        print("ℹ️ testuser już ma 0 punktów")
    
    # Sprawdź ponownie
    new_points = db.get_user_points('testuser')
    print(f"Nowe punkty testuser: {new_points}")

if __name__ == "__main__":
    clear_testuser_points()