#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌐 KranikBot Web API Server
Backend API dla web-based panelu kontrolnego
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import subprocess
import psutil
import time
import os
import sys
import sqlite3
import threading
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Umożliwia CORS dla wszystkich domen

# Konfiguracja
API_KEY = os.getenv('API_KEY', 'kranikbot-secure-key-2024')
BOT_SCRIPT = "testBot.py"
DISCORD_BOT_SCRIPT = "discord_bot_standalone.py"
DB_PATH = "users.db"

# Globalne zmienne stanu
bot_processes = {
    'twitch': {'process': None, 'pid': None, 'start_time': None, 'status': 'offline'},
    'discord': {'process': None, 'pid': None, 'start_time': None, 'status': 'offline'}
}

def safe_print(text):
    """Bezpieczne wyświetlanie tekstu z obsługą UTF-8"""
    try:
        print(text)
        logger.info(text)
    except UnicodeEncodeError:
        safe_text = text.encode('ascii', 'replace').decode('ascii')
        print(safe_text)
        logger.info(safe_text)

def check_auth(request):
    """Sprawdza autoryzację API"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return False
    
    token = auth_header.split(' ')[1]
    return token == API_KEY

def find_python_executable():
    """Znajduje python.exe w systemie"""
    python_executable = sys.executable
    
    if python_executable.endswith('.exe') and 'python' not in python_executable.lower():
        # Jesteśmy w .exe - znajdź python.exe
        import shutil
        python_executable = shutil.which('python')
        if not python_executable:
            python_executable = shutil.which('python3')
        
        if not python_executable:
            # Sprawdź standardowe lokalizacje
            possible_paths = [
                r'C:\Python\python.exe',
                r'C:\Python39\python.exe',
                r'C:\Python310\python.exe',
                r'C:\Python311\python.exe',
                r'C:\Python312\python.exe',
                r'C:\Python313\python.exe',
                f'C:\\Users\\{os.getenv("USERNAME")}\\AppData\\Local\\Programs\\Python\\Python39\\python.exe',
                f'C:\\Users\\{os.getenv("USERNAME")}\\AppData\\Local\\Programs\\Python\\Python310\\python.exe',
                f'C:\\Users\\{os.getenv("USERNAME")}\\AppData\\Local\\Programs\\Python\\Python311\\python.exe',
                f'C:\\Users\\{os.getenv("USERNAME")}\\AppData\\Local\\Programs\\Python\\Python312\\python.exe',
                f'C:\\Users\\{os.getenv("USERNAME")}\\AppData\\Local\\Programs\\Python\\Python313\\python.exe',
                f'C:\\Users\\{os.getenv("USERNAME")}\\AppData\\Local\\Microsoft\\WindowsApps\\python.exe'
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    python_executable = path
                    break
            else:
                raise Exception("Nie można znaleźć python.exe!")
    
    return python_executable

def detect_existing_bot(script_name):
    """Wykrywa istniejący proces bota"""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and len(cmdline) >= 2:
                    if ('python' in cmdline[0].lower() and script_name in ' '.join(cmdline)):
                        return {
                            'pid': proc.info['pid'],
                            'start_time': datetime.fromtimestamp(proc.info['create_time'])
                        }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        safe_print(f"❌ Błąd wykrywania bota: {e}")
    return None

def get_bot_uptime(start_time):
    """Oblicza uptime bota"""
    if not start_time:
        return "00:00:00"
    
    uptime = datetime.now() - start_time
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def start_bot(bot_type):
    """Uruchamia bota"""
    script_name = BOT_SCRIPT if bot_type == 'twitch' else DISCORD_BOT_SCRIPT
    
    # Sprawdź czy bot już działa
    existing = detect_existing_bot(script_name)
    if existing:
        bot_processes[bot_type]['pid'] = existing['pid']
        bot_processes[bot_type]['start_time'] = existing['start_time']
        bot_processes[bot_type]['status'] = 'online'
        return {'success': True, 'message': f'{bot_type.title()} bot już działa (PID: {existing["pid"]})'}
    
    try:
        # Sprawdź czy plik istnieje
        if not os.path.exists(script_name):
            return {'success': False, 'error': f'Plik bota nie istnieje: {script_name}'}
        
        # Znajdź python.exe
        python_executable = find_python_executable()
        
        # Uruchom bota
        command = [python_executable, script_name]
        process = subprocess.Popen(
            command,
            cwd=os.getcwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Sprawdź czy proces się uruchomił
        time.sleep(2)
        if process.poll() is None:
            bot_processes[bot_type]['process'] = process
            bot_processes[bot_type]['pid'] = process.pid
            bot_processes[bot_type]['start_time'] = datetime.now()
            bot_processes[bot_type]['status'] = 'online'
            
            safe_print(f"✅ {bot_type.title()} bot uruchomiony (PID: {process.pid})")
            return {'success': True, 'message': f'{bot_type.title()} bot uruchomiony pomyślnie'}
        else:
            stdout, stderr = process.communicate()
            error_msg = stderr if stderr else stdout
            return {'success': False, 'error': f'Bot zakończył się z błędem: {error_msg[:500]}'}
            
    except Exception as e:
        safe_print(f"❌ Błąd uruchamiania {bot_type} bota: {e}")
        return {'success': False, 'error': str(e)}

def stop_bot(bot_type):
    """Zatrzymuje bota"""
    try:
        bot_info = bot_processes[bot_type]
        
        if bot_info['status'] == 'offline':
            return {'success': False, 'error': f'{bot_type.title()} bot nie działa'}
        
        # Zatrzymaj przez PID
        if bot_info['pid']:
            try:
                process = psutil.Process(bot_info['pid'])
                process.terminate()
                process.wait(timeout=10)
                safe_print(f"✅ {bot_type.title()} bot zatrzymany (PID: {bot_info['pid']})")
            except psutil.NoSuchProcess:
                safe_print(f"⚠️ Proces {bot_type} bota już nie istnieje")
            except psutil.TimeoutExpired:
                process.kill()
                safe_print(f"⚠️ Wymuszono zamknięcie {bot_type} bota")
        
        # Zatrzymaj przez subprocess
        elif bot_info['process']:
            bot_info['process'].terminate()
            bot_info['process'].wait(timeout=10)
            safe_print(f"✅ {bot_type.title()} bot zatrzymany przez subprocess")
        
        # Resetuj stan
        bot_processes[bot_type] = {
            'process': None, 'pid': None, 'start_time': None, 'status': 'offline'
        }
        
        return {'success': True, 'message': f'{bot_type.title()} bot zatrzymany pomyślnie'}
        
    except Exception as e:
        safe_print(f"❌ Błąd zatrzymywania {bot_type} bota: {e}")
        return {'success': False, 'error': str(e)}

def restart_bot(bot_type):
    """Restartuje bota"""
    safe_print(f"🔄 Restartowanie {bot_type} bota...")
    
    # Zatrzymaj
    stop_result = stop_bot(bot_type)
    if not stop_result['success'] and 'nie działa' not in stop_result['error']:
        return stop_result
    
    # Poczekaj
    time.sleep(2)
    
    # Uruchom
    return start_bot(bot_type)

def get_database_stats():
    """Pobiera statystyki z bazy danych"""
    try:
        if not os.path.exists(DB_PATH):
            return {'total_users': 0, 'total_points': 0, 'top_user': 'Brak danych'}
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Łączna liczba użytkowników
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        # Łączne punkty
        cursor.execute("SELECT SUM(points) FROM users")
        total_points_result = cursor.fetchone()[0]
        total_points = total_points_result if total_points_result else 0
        
        # Top użytkownik
        cursor.execute("SELECT username FROM users ORDER BY points DESC LIMIT 1")
        top_user_result = cursor.fetchone()
        top_user = top_user_result[0] if top_user_result else 'Brak danych'
        
        conn.close()
        
        return {
            'total_users': total_users,
            'total_points': total_points,
            'top_user': top_user
        }
        
    except Exception as e:
        safe_print(f"❌ Błąd pobierania statystyk bazy danych: {e}")
        return {'total_users': 'Błąd', 'total_points': 'Błąd', 'top_user': 'Błąd'}

def monitor_bots():
    """Monitoruje status botów w tle"""
    while True:
        try:
            for bot_type in ['twitch', 'discord']:
                bot_info = bot_processes[bot_type]
                
                if bot_info['status'] == 'online':
                    # Sprawdź czy proces nadal działa
                    is_alive = False
                    
                    if bot_info['pid']:
                        try:
                            process = psutil.Process(bot_info['pid'])
                            is_alive = process.is_running()
                        except psutil.NoSuchProcess:
                            pass
                    
                    elif bot_info['process']:
                        is_alive = bot_info['process'].poll() is None
                    
                    if not is_alive:
                        safe_print(f"⚠️ {bot_type.title()} bot przestał działać")
                        bot_processes[bot_type] = {
                            'process': None, 'pid': None, 'start_time': None, 'status': 'offline'
                        }
                
                elif bot_info['status'] == 'offline':
                    # Sprawdź czy bot został uruchomiony zewnętrznie
                    script_name = BOT_SCRIPT if bot_type == 'twitch' else DISCORD_BOT_SCRIPT
                    existing = detect_existing_bot(script_name)
                    
                    if existing:
                        safe_print(f"✅ Wykryto zewnętrzny {bot_type} bot (PID: {existing['pid']})")
                        bot_processes[bot_type]['pid'] = existing['pid']
                        bot_processes[bot_type]['start_time'] = existing['start_time']
                        bot_processes[bot_type]['status'] = 'online'
            
            time.sleep(5)  # Sprawdzaj co 5 sekund
            
        except Exception as e:
            safe_print(f"❌ Błąd monitorowania: {e}")
            time.sleep(10)

# API Endpoints

@app.route('/api/status', methods=['GET'])
def api_status():
    """Status API"""
    return jsonify({
        'status': 'online',
        'message': 'KranikBot Web API działa',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/bots/status', methods=['GET'])
def api_bots_status():
    """Status botów"""
    if not check_auth(request):
        return jsonify({'error': 'Unauthorized'}), 401
    
    result = {}
    for bot_type in ['twitch', 'discord']:
        bot_info = bot_processes[bot_type]
        result[bot_type] = {
            'status': bot_info['status'],
            'pid': bot_info['pid'],
            'uptime': get_bot_uptime(bot_info['start_time'])
        }
    
    return jsonify(result)

@app.route('/api/action', methods=['POST'])
def api_action():
    """Wykonuje akcje na botach"""
    if not check_auth(request):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    action = data.get('action')
    
    if not action:
        return jsonify({'error': 'Brak akcji'}), 400
    
    # Parsuj akcję
    if action == 'start_twitch':
        result = start_bot('twitch')
    elif action == 'stop_twitch':
        result = stop_bot('twitch')
    elif action == 'restart_twitch':
        result = restart_bot('twitch')
    elif action == 'start_discord':
        result = start_bot('discord')
    elif action == 'stop_discord':
        result = stop_bot('discord')
    elif action == 'restart_discord':
        result = restart_bot('discord')
    else:
        return jsonify({'error': 'Nieznana akcja'}), 400
    
    if result['success']:
        return jsonify({'message': result['message']})
    else:
        return jsonify({'error': result['error']}), 500

@app.route('/api/stats', methods=['GET'])
def api_stats():
    """Statystyki systemu"""
    if not check_auth(request):
        return jsonify({'error': 'Unauthorized'}), 401
    
    db_stats = get_database_stats()
    
    return jsonify({
        'twitch': {
            'followers': 'N/A',  # Wymagałoby integracji z Twitch API
            'subscribers': 'N/A',
            'vips': 'N/A',
            'moderators': 'N/A'
        },
        'discord': {
            'status': 'N/A'  # Wymagałoby integracji z Discord API
        },
        'database': db_stats
    })

@app.route('/web', defaults={'path': ''})
@app.route('/web/<path:path>')
def serve_web_panel(path):
    """Serwuje pliki web panelu"""
    if path == '':
        path = 'index.html'
    
    web_dir = os.path.join(os.getcwd(), 'web_panel')
    return send_from_directory(web_dir, path)

@app.route('/')
def index():
    """Przekierowanie na web panel"""
    return '''
    <html>
    <head>
        <title>KranikBot API Server</title>
        <style>
            body { font-family: Arial, sans-serif; background: #0f0f23; color: #e0e0ff; text-align: center; padding: 50px; }
            .container { max-width: 600px; margin: 0 auto; }
            .btn { background: #4fc3f7; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; display: inline-block; margin: 10px; }
            .btn:hover { background: #29b6f6; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 KranikBot API Server</h1>
            <p>Serwer API dla web-based panelu kontrolnego</p>
            <p>Status: <strong>Online</strong></p>
            <br>
            <a href="/web" class="btn">🌐 Otwórz Web Panel</a>
            <a href="/api/status" class="btn">📊 Status API</a>
        </div>
    </body>
    </html>
    '''

def main():
    """Główna funkcja"""
    safe_print("🌐 Uruchamianie KranikBot Web API Server...")
    
    # Sprawdź czy pliki botów istnieją
    if not os.path.exists(BOT_SCRIPT):
        safe_print(f"⚠️ Ostrzeżenie: Plik {BOT_SCRIPT} nie istnieje")
    
    if not os.path.exists(DISCORD_BOT_SCRIPT):
        safe_print(f"⚠️ Ostrzeżenie: Plik {DISCORD_BOT_SCRIPT} nie istnieje")
    
    # Wykryj istniejące boty
    for bot_type in ['twitch', 'discord']:
        script_name = BOT_SCRIPT if bot_type == 'twitch' else DISCORD_BOT_SCRIPT
        existing = detect_existing_bot(script_name)
        
        if existing:
            bot_processes[bot_type]['pid'] = existing['pid']
            bot_processes[bot_type]['start_time'] = existing['start_time']
            bot_processes[bot_type]['status'] = 'online'
            safe_print(f"✅ Wykryto działający {bot_type} bot (PID: {existing['pid']})")
    
    # Uruchom monitoring w tle
    monitor_thread = threading.Thread(target=monitor_bots, daemon=True)
    monitor_thread.start()
    
    safe_print("🚀 Serwer uruchomiony!")
    safe_print("🌐 Web Panel: http://localhost:5000/web")
    safe_print("📊 API Status: http://localhost:5000/api/status")
    safe_print(f"🔑 API Key: {API_KEY}")
    
    # Uruchom Flask (Railway używa zmiennej PORT)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    main()
