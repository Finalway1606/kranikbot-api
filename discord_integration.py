import os
import requests
import json
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Optional
import discord
import pytz
import sys
import hashlib

# Konfiguracja UTF-8 dla Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

def safe_print(text):
    """Bezpieczne wyświetlanie tekstu z emoji na Windows"""
    try:
        print(text)
    except UnicodeEncodeError:
        # Zamień emoji na tekst ASCII
        safe_text = text.encode('ascii', 'replace').decode('ascii')
        print(safe_text)

class DiscordIntegration:
    def __init__(self):
        # Strefa czasowa dla Polski
        self.poland_tz = pytz.timezone('Europe/Warsaw')
        self.webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        self.bot_token = os.getenv('DISCORD_BOT_TOKEN')
        self.guild_id = os.getenv('DISCORD_GUILD_ID')
        self.special_role_id = os.getenv('DISCORD_SPECIAL_ROLE_ID')
        self.leaderboard_channel_id = os.getenv('DISCORD_LEADERBOARD_CHANNEL_ID')
        self.stream_channel_id = os.getenv('DISCORD_STREAM_CHANNEL_ID')
        
        # Hash do sprawdzania zmian w rankingu
        self.last_leaderboard_hash = None
        
        # Sprawdź czy Discord jest skonfigurowany
        self.enabled = bool(self.webhook_url)
        self.bot_enabled = bool(self.bot_token and self.guild_id)
        
        if not self.enabled:
            safe_print(f"⚠️ Discord webhook nie jest skonfigurowany - funkcje Discord wyłączone")
        else:
            safe_print(f"✅ Discord integration włączona!")
            
        if self.bot_enabled:
            safe_print(f"🤖 Discord bot gotowy do nadawania ról!")
        elif self.enabled:
            safe_print(f"⚠️ Discord bot nie skonfigurowany - automatyczne role wyłączone")
    
    def get_poland_time(self):
        """Zwraca aktualny czas w Polsce"""
        return datetime.now(self.poland_tz)
    
    def send_webhook_message(self, content: str, embeds: list = None, username: str = "KranikBot"):
        """Wysyła wiadomość przez webhook Discord"""
        if not self.enabled:
            return False
        
        try:
            data = {
                "content": content,
                "username": username,
                "avatar_url": "https://cdn.discordapp.com/attachments/your_avatar_url_here"
            }
            
            if embeds:
                data["embeds"] = embeds
            
            response = requests.post(self.webhook_url, json=data)
            return response.status_code == 204
            
        except Exception as e:
            safe_print(f"❌ Błąd wysyłania webhook Discord: {e}")
            return False
    
    def notify_reward_purchase(self, twitch_username: str, reward_name: str, price: int, duration_hours: int):
        """Powiadamia Discord o zakupie nagrody"""
        if not self.enabled:
            return
        
        # Różne kolory dla różnych typów nagród
        color_map = {
            "vip": 0xFFD700,      # Złoty
            "discord": 0x7289DA,   # Discord blue
            "stream": 0x9146FF,    # Twitch purple
            "game": 0x00FF00       # Zielony
        }
        
        # Określ kolor na podstawie nazwy nagrody
        color = 0x9146FF  # Domyślny Twitch purple
        for key, value in color_map.items():
            if key in reward_name.lower():
                color = value
                break
        
        # Format czasu
        if duration_hours >= 24:
            duration_text = f"{duration_hours // 24} dni"
        elif duration_hours >= 1:
            duration_text = f"{duration_hours} godzin"
        else:
            duration_text = "jednorazowo"
        
        embed = {
            "title": "🎁 Nowa nagroda kupiona!",
            "description": f"**{twitch_username}** kupił nagrodę za **{price} punktów**",
            "color": color,
            "fields": [
                {
                    "name": "🏆 Nagroda",
                    "value": reward_name,
                    "inline": True
                },
                {
                    "name": "⏰ Czas trwania", 
                    "value": duration_text,
                    "inline": True
                },
                {
                    "name": "💰 Koszt",
                    "value": f"{price} punktów",
                    "inline": True
                }
            ],
            "timestamp": self.get_poland_time().isoformat(),
            "footer": {
                "text": "KranikBot • Twitch Integration"
            }
        }
        
        self.send_webhook_message("", embeds=[embed])

    async def update_shop_post(self, channel_id: int, embed_data: dict, message_id: int = None):
        """Aktualizuje lub wysyła nowy post ze sklepem na Discord"""
        if not self.bot_enabled:
            safe_print(f"❌ Discord bot nie jest skonfigurowany do aktualizacji sklepu")
            return None
        
        try:
            intents = discord.Intents.default()
            intents.guilds = True
            intents.message_content = True
            
            client = discord.Client(intents=intents)
            result_message_id = None
            
            @client.event
            async def on_ready():
                nonlocal result_message_id
                try:
                    guild = client.get_guild(int(self.guild_id))
                    if not guild:
                        safe_print(f"❌ Nie znaleziono serwera Discord o ID: {self.guild_id}")
                        await client.close()
                        return
                    
                    channel = guild.get_channel(int(channel_id))
                    if not channel:
                        safe_print(f"❌ Nie znaleziono kanału o ID: {channel_id}")
                        await client.close()
                        return
                    
                    # Stwórz embed Discord
                    embed = discord.Embed(
                        title=embed_data["title"],
                        description=embed_data["description"],
                        color=embed_data["color"]
                    )
                    
                    # Dodaj pola
                    for field in embed_data["fields"]:
                        embed.add_field(
                            name=field["name"],
                            value=field["value"],
                            inline=field.get("inline", True)
                        )
                    
                    # Dodaj footer
                    if "footer" in embed_data:
                        embed.set_footer(text=embed_data["footer"]["text"])
                    
                    # Usuń poprzednie wiadomości bota ze sklepem (podobnie jak w kanale statystyk)
                    deleted_count = 0
                    async for message in channel.history(limit=20):
                        if message.author == client.user:
                            try:
                                await message.delete()
                                deleted_count += 1
                                await asyncio.sleep(0.5)  # Rate limit
                            except discord.NotFound:
                                pass  # Wiadomość już usunięta
                            except Exception as e:
                                safe_print(f"⚠️ Nie można usunąć wiadomości: {e}")
                    
                    if deleted_count > 0:
                        safe_print(f"🗑️ Usunięto {deleted_count} poprzednich wiadomości ze sklepem")
                    
                    # Wyślij nową wiadomość ze sklepem
                    message = await channel.send(embed=embed)
                    result_message_id = message.id
                    safe_print(f"✅ Wysłano nowy post ze sklepem w kanale #{channel.name}")
                    
                except Exception as e:
                    safe_print(f"❌ Błąd aktualizacji postu ze sklepem: {e}")
                finally:
                    await client.close()
            
            await client.start(self.bot_token)
            return result_message_id
            
        except Exception as e:
            safe_print(f"❌ Błąd połączenia z Discord (sklep): {e}")
            return None

    def update_shop_post_async(self, channel_id: int, embed_data: dict, message_id: int = None):
        """Wrapper do uruchamiania aktualizacji sklepu w osobnym wątku"""
        def run_async():
            try:
                result = asyncio.run(self.update_shop_post(channel_id, embed_data, message_id))
                return result
            except Exception as e:
                safe_print(f"❌ Błąd async aktualizacji sklepu: {e}")
                return None
        
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
        return thread
    
    def get_leaderboard_hash(self, user_database):
        """Generuje hash aktualnego stanu rankingu"""
        try:
            # Pobierz top 20 użytkowników
            top_users = user_database.get_top_users(20)
            
            # Pobierz statystyki ogólne
            total_users = user_database.get_total_users_count()
            total_points = user_database.get_total_points_distributed()
            
            # Stwórz dane do hash (bez timestamp)
            leaderboard_data = {
                "top_users": top_users,
                "total_users": total_users,
                "total_points": total_points
            }
            
            # Generuj hash
            data_string = json.dumps(leaderboard_data, sort_keys=True)
            return hashlib.md5(data_string.encode()).hexdigest()
            
        except Exception as e:
            safe_print(f"❌ Błąd generowania hash rankingu: {e}")
            return None
    
    def check_leaderboard_changes(self, user_database):
        """Sprawdza czy ranking się zmienił od ostatniego sprawdzenia"""
        current_hash = self.get_leaderboard_hash(user_database)
        
        if current_hash is None:
            return False  # Błąd - nie aktualizuj
        
        if self.last_leaderboard_hash is None:
            self.last_leaderboard_hash = current_hash
            return False  # Pierwsza inicjalizacja - nie wysyłaj wiadomości
        
        if current_hash != self.last_leaderboard_hash:
            self.last_leaderboard_hash = current_hash
            return True  # Ranking się zmienił
        
        return False  # Brak zmian
    
    def initialize_leaderboard_hash(self, user_database):
        """Inicjalizuje hash rankingu bez wysyłania wiadomości na Discord"""
        current_hash = self.get_leaderboard_hash(user_database)
        if current_hash is not None:
            self.last_leaderboard_hash = current_hash
            safe_print("ℹ️ Zainicjalizowano hash rankingu bez wysyłania wiadomości")

    
    async def update_leaderboard_channel(self, user_database):
        """Automatycznie aktualizuje kanał z rankingiem punktów"""
        if not self.bot_enabled or not self.leaderboard_channel_id:
            return False
        
        try:
            intents = discord.Intents.default()
            intents.guilds = True
            intents.message_content = True
            
            client = discord.Client(intents=intents)
            
            @client.event
            async def on_ready():
                try:
                    guild = client.get_guild(int(self.guild_id))
                    if not guild:
                        safe_print(f"❌ Nie znaleziono serwera Discord o ID: {self.guild_id}")
                        await client.close()
                        return
                    
                    channel = guild.get_channel(int(self.leaderboard_channel_id))
                    if not channel:
                        safe_print(f"❌ Nie znaleziono kanału rankingu o ID: {self.leaderboard_channel_id}")
                        await client.close()
                        return
                    
                    # Wyczyść kanał
                    async for message in channel.history(limit=100):
                        await message.delete()
                        await asyncio.sleep(0.5)  # Rate limit
                    
                    # Pobierz top użytkowników
                    top_users = user_database.get_top_users(20)  # Top 20
                    
                    # Stwórz embed z rankingiem
                    embed = discord.Embed(
                        title="🏆 RANKING PUNKTÓW",
                        description="Najlepsi gracze ze streama",
                        color=0xFFD700,  # Złoty
                        timestamp=self.get_poland_time()
                    )
                    embed.set_footer(text="KranikBot • Aktualizowane co 30 minut")
                    
                    # Emoji dla pozycji
                    position_emojis = {
                        1: "🥇", 2: "🥈", 3: "🥉",
                        4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"
                    }
                    
                    # Podziel na grupy po 10
                    top_10 = top_users[:10]
                    next_10 = top_users[10:20]
                    
                    # Top 10
                    if top_10:
                        top_10_text = ""
                        for i, (username, points, messages) in enumerate(top_10, 1):
                            emoji = position_emojis.get(i, f"{i}.")
                            top_10_text += f"{emoji} **{username}** - {points:,} pkt\n"
                        
                        embed.add_field(
                            name="🏆 TOP 10",
                            value=top_10_text,
                            inline=False
                        )
                    
                    # Pozycje 11-20
                    if next_10:
                        next_10_text = ""
                        for i, (username, points, messages) in enumerate(next_10, 11):
                            next_10_text += f"{i}. **{username}** - {points:,} pkt\n"
                        
                        embed.add_field(
                            name="📊 Pozycje 11-20",
                            value=next_10_text,
                            inline=False
                        )
                    
                    # Statystyki ogólne
                    total_users = user_database.get_total_users_count()
                    total_points = user_database.get_total_points_distributed()
                    
                    embed.add_field(
                        name="📈 Statystyki ogólne",
                        value=f"👥 Łącznie użytkowników: **{total_users}**\n💰 Rozdanych punktów: **{total_points:,}**",
                        inline=False
                    )
                    
                    # Wyślij embed
                    await channel.send(embed=embed)
                    safe_print(f"✅ Zaktualizowano ranking punktów w kanale #{channel.name}")
                    
                except Exception as e:
                    safe_print(f"❌ Błąd aktualizacji rankingu: {e}")
                finally:
                    await client.close()
            
            await client.start(self.bot_token)
            return True
            
        except Exception as e:
            safe_print(f"❌ Błąd połączenia z Discord (ranking): {e}")
            return False
    

    

    
    def update_leaderboard_async(self, user_database, update_hash_after=True):
        """Wrapper do uruchamiania aktualizacji rankingu w osobnym wątku"""
        def run_async():
            try:
                result = asyncio.run(self.update_leaderboard_channel(user_database))
                # Aktualizuj hash po udanej aktualizacji Discord
                if result and update_hash_after:
                    self.last_leaderboard_hash = self.get_leaderboard_hash(user_database)
                    safe_print("🔄 Hash rankingu zaktualizowany po udanej aktualizacji Discord")
            except Exception as e:
                safe_print(f"❌ Błąd async aktualizacji rankingu: {e}")
        
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
    
    def update_leaderboard_if_changed(self, user_database):
        """Aktualizuje ranking na Discord tylko jeśli coś się zmieniło"""
        if self.check_leaderboard_changes(user_database):
            safe_print("🔄 Wykryto zmiany w rankingu - aktualizuję Discord...")
            # Hash już zaktualizowany w check_leaderboard_changes, nie aktualizuj ponownie
            self.update_leaderboard_async(user_database, update_hash_after=False)
        else:
            safe_print("ℹ️ Brak zmian w rankingu - nie aktualizuję Discord")
    
    def force_update_leaderboard(self, user_database):
        """Wymusza aktualizację rankingu na Discord"""
        safe_print("🔄 Wymuszam aktualizację rankingu na Discord...")
        # NIE aktualizuj hash przed wymuszeniem - pozwól automatycznemu systemowi wykryć zmiany
        self.update_leaderboard_async(user_database)
    
    async def clear_discord_channel(self, channel_id: str, requester_username: str = "Admin"):
        """Czyści wszystkie wiadomości z kanału Discord"""
        if not self.bot_enabled:
            safe_print(f"❌ Discord bot nie jest skonfigurowany do czyszczenia kanałów")
            return False
        
        try:
            # Konfiguracja intents
            intents = discord.Intents.default()
            intents.guilds = True
            intents.message_content = True
            
            client = discord.Client(intents=intents)
            
            @client.event
            async def on_ready():
                try:
                    guild = client.get_guild(int(self.guild_id))
                    if not guild:
                        safe_print(f"❌ Nie znaleziono serwera Discord o ID: {self.guild_id}")
                        await client.close()
                        return
                    
                    channel = guild.get_channel(int(channel_id))
                    if not channel:
                        safe_print(f"❌ Nie znaleziono kanału o ID: {channel_id}")
                        await client.close()
                        return
                    
                    safe_print(f"🧹 Rozpoczynam czyszczenie kanału #{channel.name}...")
                    
                    # Wyślij powiadomienie o rozpoczęciu czyszczenia
                    embed = {
                        "title": "🧹 Rozpoczęto czyszczenie kanału",
                        "description": f"Kanał **#{channel.name}** jest czyszczony przez **{requester_username}**",
                        "color": 0xFFA500,  # Pomarańczowy
                        "timestamp": self.get_poland_time().isoformat(),
                        "footer": {
                            "text": "KranikBot • Channel Cleanup"
                        }
                    }
                    
                    self.send_webhook_message("", embeds=[embed])
                    
                    # Pobierz wszystkie wiadomości
                    messages = []
                    async for message in channel.history(limit=None):
                        messages.append(message)
                    
                    total_messages = len(messages)
                    safe_print(f"📊 Znaleziono {total_messages} wiadomości do usunięcia")
                    
                    if total_messages == 0:
                        safe_print(f"✅ Kanał jest już pusty")
                        await client.close()
                        return
                    
                    deleted_count = 0
                    
                    # Podziel wiadomości na nowe (bulk delete) i stare (pojedyncze)
                    # Użyj UTC z timezone aware datetime
                    import pytz
                    now = datetime.now(pytz.UTC)
                    two_weeks_ago = now - timedelta(days=14)
                    
                    new_messages = []
                    old_messages = []
                    
                    for message in messages:
                        # Upewnij się, że message.created_at ma timezone info
                        message_time = message.created_at
                        if message_time.tzinfo is None:
                            # Jeśli message nie ma timezone, dodaj UTC
                            message_time = message_time.replace(tzinfo=pytz.UTC)
                        
                        if message_time > two_weeks_ago:
                            new_messages.append(message)
                        else:
                            old_messages.append(message)
                    
                    # Bulk delete dla nowych wiadomości (do 100 na raz)
                    if new_messages:
                        safe_print(f"🚀 Usuwam {len(new_messages)} nowych wiadomości (bulk delete)...")
                        
                        # Podziel na grupy po 100
                        for i in range(0, len(new_messages), 100):
                            batch = new_messages[i:i+100]
                            await channel.delete_messages(batch)
                            deleted_count += len(batch)
                            safe_print(f"✅ Usunięto {deleted_count}/{total_messages} wiadomości")
                            
                            # Krótka pauza między batch'ami
                            await asyncio.sleep(1)
                    
                    # Pojedyncze usuwanie dla starych wiadomości
                    if old_messages:
                        safe_print(f"⏳ Usuwam {len(old_messages)} starych wiadomości (pojedynczo)...")
                        
                        for i, message in enumerate(old_messages):
                            try:
                                await message.delete()
                                deleted_count += 1
                                
                                # Progress co 10 wiadomości
                                if (i + 1) % 10 == 0:
                                    safe_print(f"✅ Usunięto {deleted_count}/{total_messages} wiadomości")
                                
                                # Rate limit - 1 wiadomość na sekundę dla starych
                                await asyncio.sleep(1.1)
                                
                            except discord.errors.NotFound:
                                # Wiadomość już usunięta
                                deleted_count += 1
                                continue
                            except Exception as e:
                                safe_print(f"⚠️ Błąd usuwania wiadomości: {e}")
                                continue
                    
                    safe_print(f"✅ Czyszczenie zakończone! Usunięto {deleted_count}/{total_messages} wiadomości")
                    
                    # Wyślij powiadomienie o zakończeniu
                    embed = {
                        "title": "✅ Czyszczenie kanału zakończone",
                        "description": f"Kanał **#{channel.name}** został wyczyszczony",
                        "color": 0x00FF00,  # Zielony
                        "fields": [
                            {
                                "name": "🧹 Usunięto wiadomości",
                                "value": f"{deleted_count}/{total_messages}",
                                "inline": True
                            },
                            {
                                "name": "👤 Zlecił",
                                "value": requester_username,
                                "inline": True
                            }
                        ],
                        "timestamp": self.get_poland_time().isoformat(),
                        "footer": {
                            "text": "KranikBot • Channel Cleanup Complete"
                        }
                    }
                    
                    self.send_webhook_message("", embeds=[embed])
                    
                except Exception as e:
                    safe_print(f"❌ Błąd podczas czyszczenia kanału: {e}")
                    
                    # Wyślij powiadomienie o błędzie
                    embed = {
                        "title": "❌ Błąd czyszczenia kanału",
                        "description": f"Wystąpił błąd podczas czyszczenia kanału",
                        "color": 0xFF0000,  # Czerwony
                        "fields": [
                            {
                                "name": "🐛 Błąd",
                                "value": str(e)[:1000],  # Ogranicz długość
                                "inline": False
                            }
                        ],
                        "timestamp": self.get_poland_time().isoformat(),
                        "footer": {
                            "text": "KranikBot • Error"
                        }
                    }
                    
                    self.send_webhook_message("", embeds=[embed])
                
                finally:
                    await client.close()
            
            # Uruchom bota Discord
            await client.start(self.bot_token)
            return True
            
        except Exception as e:
            safe_print(f"❌ Błąd inicjalizacji Discord bota: {e}")
            return False
    
    async def assign_discord_role(self, twitch_username: str, duration_hours: int = 168):
        """Automatycznie nadaje rolę Discord użytkownikowi"""
        if not self.bot_enabled or not self.special_role_id:
            safe_print(f"❌ Discord bot nie jest skonfigurowany do nadawania ról")
            return False
        
        try:
            # Konfiguracja intents - z privileged intents
            intents = discord.Intents.default()
            intents.guilds = True
            intents.members = True  # Potrzebne do wyszukiwania użytkowników
            
            client = discord.Client(intents=intents)
            
            @client.event
            async def on_ready():
                try:
                    guild = client.get_guild(int(self.guild_id))
                    if not guild:
                        safe_print(f"❌ Nie znaleziono serwera Discord o ID: {self.guild_id}")
                        await client.close()
                        return
                    
                    role = guild.get_role(int(self.special_role_id))
                    if not role:
                        safe_print(f"❌ Nie znaleziono roli o ID: {self.special_role_id}")
                        await client.close()
                        return
                    
                    # Znajdź użytkownika po nazwie Twitch (może być w nicku lub display name)
                    target_member = None
                    for member in guild.members:
                        # Sprawdź nick, display name i username
                        if (member.display_name.lower() == twitch_username.lower() or
                            member.name.lower() == twitch_username.lower() or
                            (member.nick and member.nick.lower() == twitch_username.lower())):
                            target_member = member
                            break
                    
                    if not target_member:
                        safe_print(f"❌ Nie znaleziono użytkownika Discord dla Twitch: {twitch_username}")
                        # Wyślij powiadomienie o potrzebie ręcznego nadania roli
                        self.request_manual_action(
                            "discord_role",
                            twitch_username,
                            f"Nie znaleziono użytkownika Discord. Nadaj rolę '{role.name}' ręcznie na {duration_hours} godzin."
                        )
                        await client.close()
                        return
                    
                    # Nadaj rolę
                    await target_member.add_roles(role, reason=f"Automatyczne nadanie roli za zakup w sklepie Twitch (na {duration_hours}h)")
                    
                    safe_print(f"✅ Nadano rolę '{role.name}' użytkownikowi {target_member.display_name} ({twitch_username})")
                    
                    # Wyślij powiadomienie o sukcesie
                    embed = {
                        "title": "👑 Rola VIP nadana automatycznie!",
                        "description": f"Użytkownik **{target_member.display_name}** otrzymał rolę VIP **{role.name}**",
                        "color": 0xFFD700,  # Złoty dla VIP
                        "fields": [
                            {
                                "name": "👤 Twitch",
                                "value": twitch_username,
                                "inline": True
                            },
                            {
                                "name": "👑 Rola VIP",
                                "value": role.name,
                                "inline": True
                            },
                            {
                                "name": "⏰ Czas trwania",
                                "value": f"{duration_hours} godzin (7 dni)",
                                "inline": True
                            }
                        ],
                        "timestamp": self.get_poland_time().isoformat(),
                        "footer": {
                            "text": "KranikBot • VIP Role Assignment"
                        }
                    }
                    
                    self.send_webhook_message("", embeds=[embed])
                    
                    # Zaplanuj usunięcie roli w osobnym zadaniu
                    if duration_hours > 0:
                        asyncio.create_task(self._schedule_role_removal(target_member, role, duration_hours))
                    
                except Exception as e:
                    safe_print(f"❌ Błąd nadawania roli Discord: {e}")
                finally:
                    await client.close()
            
            # Uruchom bota
            await client.start(self.bot_token)
            return True
            
        except Exception as e:
            safe_print(f"❌ Błąd połączenia z Discord: {e}")
            return False
    
    async def _schedule_role_removal(self, member, role, duration_hours):
        """Planuje usunięcie roli po określonym czasie"""
        try:
            await asyncio.sleep(duration_hours * 3600)  # Konwersja na sekundy
            await member.remove_roles(role, reason=f"Automatyczne usunięcie roli po {duration_hours}h")
            safe_print(f"✅ Usunięto rolę '{role.name}' od użytkownika {member.display_name}")
            
            # Powiadomienie o usunięciu roli
            embed_remove = {
                "title": "👑 Rola VIP wygasła",
                "description": f"Rola VIP **{role.name}** została automatycznie usunięta od **{member.display_name}**",
                "color": 0xFFA500,  # Pomarańczowy
                "timestamp": datetime.now().isoformat(),
                "footer": {
                    "text": "KranikBot • VIP Role Expiration"
                }
            }
            
            self.send_webhook_message("", embeds=[embed_remove])
        except Exception as e:
            safe_print(f"❌ Błąd usuwania roli: {e}")

    def assign_role_async(self, twitch_username: str, duration_hours: int = 168):
        """Wrapper do uruchamiania nadawania ról w osobnym wątku"""
        def run_async():
            try:
                asyncio.run(self.assign_discord_role(twitch_username, duration_hours))
            except Exception as e:
                safe_print(f"❌ Błąd async nadawania roli: {e}")
        
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
    
    def notify_big_win(self, username: str, game: str, points: int):
        """Powiadamia o dużej wygranej w grze"""
        if not self.enabled or points < 50:  # Tylko duże wygrane
            return
        
        # Emoji dla różnych gier
        game_emojis = {
            "dice": "🎲",
            "coinflip": "🪙", 
            "roulette": "🎰",
            "quiz": "❓"
        }
        
        emoji = game_emojis.get(game, "🎮")
        
        embed = {
            "title": f"{emoji} WIELKA WYGRANA!",
            "description": f"**{username}** wygrał **{points} punktów** w grze **{game}**!",
            "color": 0x00FF00,  # Zielony
            "timestamp": self.get_poland_time().isoformat(),
            "footer": {
                "text": "KranikBot • Game Notification"
            }
        }
        
        self.send_webhook_message("🎉 Ktoś ma szczęście!", embeds=[embed])
    
    def notify_new_follower(self, username: str):
        """Powiadamia o nowym followerze"""
        if not self.enabled:
            return
        
        embed = {
            "title": "💜 Nowy follower!",
            "description": f"**{username}** zaczął obserwować kanał!",
            "color": 0x9146FF,  # Twitch purple
            "timestamp": self.get_poland_time().isoformat(),
            "footer": {
                "text": "KranikBot • Follow Notification"
            }
        }
        
        self.send_webhook_message("", embeds=[embed])
    
    def notify_new_subscriber(self, username: str, tier: str = "1"):
        """Powiadamia o nowym subskrybencie"""
        if not self.enabled:
            return
        
        tier_colors = {
            "1": 0x9146FF,    # Twitch purple
            "2": 0xFFD700,    # Złoty
            "3": 0xFF69B4     # Różowy
        }
        
        embed = {
            "title": "🌟 Nowy subskrybent!",
            "description": f"**{username}** zasubskrybował kanał (Tier {tier})!",
            "color": tier_colors.get(tier, 0x9146FF),
            "timestamp": self.get_poland_time().isoformat(),
            "footer": {
                "text": "KranikBot • Subscription Notification"
            }
        }
        
        self.send_webhook_message("", embeds=[embed])
    
    def notify_stream_status(self, is_live: bool, title: str = "", game: str = ""):
        """Powiadamia o statusie streama na dedykowanym kanale Discord"""
        if not self.bot_enabled or not self.stream_channel_id:
            # Fallback do webhook jeśli kanał nie jest skonfigurowany
            if self.enabled:
                if is_live:
                    embed = {
                        "title": "🔴 Stream LIVE!",
                        "description": f"Stream właśnie się rozpoczął!\n\n🎮 **[Oglądaj na Twitch](https://twitch.tv/kranik1606)**",
                        "color": 0xFF0000,
                        "fields": [],
                        "timestamp": self.get_poland_time().isoformat(),
                        "footer": {"text": "KranikBot • Stream Notification"}
                    }
                    if title:
                        embed["fields"].append({"name": "📺 Tytuł", "value": title, "inline": False})
                    if game:
                        embed["fields"].append({"name": "🎮 Gra", "value": game, "inline": False})
                    self.send_webhook_message("@everyone Stream się rozpoczął! 🎉", embeds=[embed])
                else:
                    embed = {
                        "title": "⚫ Stream zakończony",
                        "description": "Stream właśnie się zakończył. Dzięki za oglądanie!",
                        "color": 0x808080,
                        "timestamp": self.get_poland_time().isoformat(),
                        "footer": {"text": "KranikBot • Stream Notification"}
                    }
                    self.send_webhook_message("", embeds=[embed])
            return
        
        # Wyślij na dedykowany kanał Discord
        self.send_stream_notification_async(is_live, title, game)
    
    def send_stream_notification_async(self, is_live: bool, title: str = "", game: str = ""):
        """Wysyła powiadomienie o streamie na dedykowany kanał Discord"""
        def run_async():
            try:
                asyncio.run(self.send_stream_notification(is_live, title, game))
            except Exception as e:
                safe_print(f"❌ Błąd wysyłania powiadomienia o streamie: {e}")
        
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
    
    async def send_stream_notification(self, is_live: bool, title: str = "", game: str = ""):
        """Wysyła powiadomienie o streamie na Discord"""
        try:
            intents = discord.Intents.default()
            intents.guilds = True
            intents.message_content = True
            
            client = discord.Client(intents=intents)
            
            @client.event
            async def on_ready():
                try:
                    guild = client.get_guild(int(self.guild_id))
                    if not guild:
                        safe_print(f"❌ Nie znaleziono serwera Discord o ID: {self.guild_id}")
                        await client.close()
                        return
                    
                    channel = guild.get_channel(int(self.stream_channel_id))
                    if not channel:
                        safe_print(f"❌ Nie znaleziono kanału stream o ID: {self.stream_channel_id}")
                        await client.close()
                        return
                    
                    if is_live:
                        # Stream LIVE
                        embed = discord.Embed(
                            title="🔴 Stream LIVE!",
                            description="Stream właśnie się rozpoczął!",
                            color=0xFF0000,
                            timestamp=self.get_poland_time()
                        )
                        
                        if title:
                            embed.add_field(name="📺 Tytuł", value=title, inline=False)
                        if game:
                            embed.add_field(name="🎮 Gra", value=game, inline=False)
                        
                        embed.add_field(name="🎮 Link", value="**[Oglądaj na Twitch](https://twitch.tv/kranik1606)**", inline=False)
                        embed.set_footer(text="KranikBot • Stream Notification")
                        
                        await channel.send("@everyone Stream się rozpoczął! 🎉", embed=embed)
                        safe_print(f"✅ Wysłano powiadomienie LIVE na kanał #{channel.name}")
                    else:
                        # Stream OFF
                        embed = discord.Embed(
                            title="⚫ Stream zakończony",
                            description="Stream właśnie się zakończył. Dzięki za oglądanie!",
                            color=0x808080,
                            timestamp=self.get_poland_time()
                        )
                        embed.set_footer(text="KranikBot • Stream Notification")
                        
                        await channel.send(embed=embed)
                        safe_print(f"✅ Wysłano powiadomienie OFF na kanał #{channel.name}")
                    
                except Exception as e:
                    safe_print(f"❌ Błąd wysyłania powiadomienia o streamie: {e}")
                finally:
                    await client.close()
            
            await client.start(self.bot_token)
            
        except Exception as e:
            safe_print(f"❌ Błąd połączenia z Discord (stream notification): {e}")
    
    def request_manual_action(self, action_type: str, username: str, details: str):
        """Prosi moderatorów o ręczną akcję"""
        if not self.enabled:
            return
        
        action_emojis = {
            "vip": "👑",
            "role": "🎭", 
            "title": "📺",
            "game": "🎮"
        }
        
        emoji = action_emojis.get(action_type, "⚠️")
        
        embed = {
            "title": f"{emoji} Wymagana akcja moderatora",
            "description": f"Użytkownik **{username}** potrzebuje ręcznej realizacji nagrody",
            "color": 0xFFA500,  # Pomarańczowy
            "fields": [
                {
                    "name": "👤 Użytkownik",
                    "value": username,
                    "inline": True
                },
                {
                    "name": "🔧 Akcja",
                    "value": action_type,
                    "inline": True
                },
                {
                    "name": "📝 Szczegóły",
                    "value": details,
                    "inline": False
                }
            ],
            "timestamp": self.get_poland_time().isoformat(),
            "footer": {
                "text": "KranikBot • Manual Action Required"
            }
        }
        
        self.send_webhook_message("🔔 Moderatorzy, potrzebna wasza pomoc!", embeds=[embed])
    
    def send_daily_stats(self, stats: dict):
        """Wysyła dzienne statystyki"""
        if not self.enabled:
            return
        
        embed = {
            "title": "📊 Dzienne statystyki bota",
            "color": 0x00BFFF,  # Niebieski
            "fields": [
                {
                    "name": "👥 Nowi użytkownicy",
                    "value": str(stats.get('new_users', 0)),
                    "inline": True
                },
                {
                    "name": "🎮 Gry rozegrane",
                    "value": str(stats.get('games_played', 0)),
                    "inline": True
                },
                {
                    "name": "🛒 Nagrody kupione",
                    "value": str(stats.get('rewards_bought', 0)),
                    "inline": True
                },
                {
                    "name": "💰 Punkty rozdane",
                    "value": str(stats.get('points_given', 0)),
                    "inline": True
                },
                {
                    "name": "💜 Nowi followerzy",
                    "value": str(stats.get('new_followers', 0)),
                    "inline": True
                },
                {
                    "name": "🌟 Nowi subskrybenci",
                    "value": str(stats.get('new_subs', 0)),
                    "inline": True
                }
            ],
            "timestamp": self.get_poland_time().isoformat(),
            "footer": {
                "text": "KranikBot • Daily Statistics"
            }
        }
        
        self.send_webhook_message("", embeds=[embed])
