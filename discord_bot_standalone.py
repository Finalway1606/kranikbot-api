#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Discord Bot Standalone - Niezależny Discord Bot
Może działać bez Twitch bota, używa tej samej bazy danych.
"""

import os
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import threading
from datetime import datetime, timedelta
import pytz
import sys
import signal
from dotenv import load_dotenv

# Ładowanie zmiennych środowiskowych
load_dotenv()

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
        print(text, flush=True)
    except UnicodeEncodeError:
        # Zamień emoji na tekst ASCII
        safe_text = text.encode('ascii', 'replace').decode('ascii')
        print(safe_text, flush=True)
    except Exception as e:
        try:
            clean_text = ''.join(char for char in text if ord(char) < 128)
            print(f"[LOG] {clean_text}", flush=True)
        except:
            print(f"[LOG] Message encoding error", flush=True)

class StandaloneDiscordBot:
    def __init__(self):
        # Import lokalny aby uniknąć problemów z zależnościami
        from database import UserDatabase
        from discord_integration import DiscordIntegration
        from shop import Shop
        
        self.user_database = UserDatabase()
        self.discord_integration = DiscordIntegration()
        self.shop = Shop(self.user_database)
        self.bot_token = os.getenv('DISCORD_BOT_TOKEN')
        self.guild_id = os.getenv('DISCORD_GUILD_ID')
        self.bot = None
        self.guild = None
        self.running = False
        
        # Strefa czasowa dla Polski
        self.poland_tz = pytz.timezone('Europe/Warsaw')
        
        if not self.bot_token or not self.guild_id:
            safe_print(f"❌ Discord bot token lub guild ID nie są skonfigurowane")
            safe_print(f"📖 Sprawdź plik .env i DISCORD_INTEGRATION_SETUP.md")
            return
        
        # Konfiguracja intents
        intents = discord.Intents.default()
        intents.guilds = True
        intents.message_content = True
        
        # Tworzenie bota
        self.bot = commands.Bot(command_prefix='!', intents=intents)
        
        # Dodanie event handlers
        self.setup_events()
        self.setup_commands()
        
        safe_print(f"🤖 Standalone Discord Bot zainicjalizowany")
    
    def start_shop_monitor(self):
        """Uruchamia monitorowanie zmian w sklepie i automatyczne aktualizacje Discord"""
        def shop_monitor_loop():
            # Pierwsze uruchomienie po 30 sekundach
            import time
            time.sleep(30)
            
            while True:
                try:
                    safe_print(f"🛒 Sprawdzam zmiany w sklepie...")
                    self.shop.update_shop_post_if_changed()
                    
                    # Sprawdzaj co 5 minut
                    time.sleep(300)
                    
                except Exception as e:
                    safe_print(f"❌ Błąd monitorowania sklepu: {e}")
                    time.sleep(300)  # Spróbuj ponownie za 5 minut
        
        shop_thread = threading.Thread(target=shop_monitor_loop, daemon=True)
        shop_thread.start()
        safe_print(f"🛒 Monitor zmian w sklepie uruchomiony")
    
    def setup_events(self):
        """Konfiguruje event handlers"""
        @self.bot.event
        async def on_ready():
            safe_print(f'🤖 Discord bot zalogowany jako {self.bot.user}')
            
            # Pobierz guild
            self.guild = self.bot.get_guild(int(self.guild_id))
            if self.guild:
                safe_print(f'🏠 Połączono z serwerem: {self.guild.name}')
                
                # Synchronizuj slash commands
                try:
                    synced = await self.bot.tree.sync(guild=self.guild)
                    safe_print(f'✅ Zsynchronizowano {len(synced)} slash commands')
                except Exception as e:
                    safe_print(f'❌ Błąd synchronizacji slash commands: {e}')
            else:
                safe_print(f'❌ Nie znaleziono serwera o ID: {self.guild_id}')
            
            self.running = True
            
            # Uruchom monitor sklepu
            self.start_shop_monitor()
            
            safe_print(f"🚀 Standalone Discord Bot gotowy do pracy!")
    
    def setup_commands(self):
        """Konfiguruje slash commands"""
        
        @self.bot.tree.command(
            name="update_leaderboard",
            description="Aktualizuje ranking punktów na kanale Discord",
            guild=discord.Object(id=int(self.guild_id))
        )
        async def update_leaderboard(interaction: discord.Interaction):
            """Slash command do aktualizacji rankingu"""
            
            # Sprawdź uprawnienia (administrator lub określona rola)
            if not (interaction.user.guild_permissions.administrator or 
                   any(role.name.lower() in ['moderator', 'mod', 'admin'] for role in interaction.user.roles)):
                await interaction.response.send_message(
                    "❌ Nie masz uprawnień do używania tej komendy!", 
                    ephemeral=True
                )
                return
            
            # Odpowiedz natychmiast
            await interaction.response.send_message(
                "🏆 Aktualizuję ranking Discord...", 
                ephemeral=True
            )
            
            try:
                # Wymusz aktualizację rankingu
                self.discord_integration.force_update_leaderboard(self.user_database)
                safe_print(f"✅ Ranking Discord wymuszony przez slash command przez {interaction.user}")
                
                # Wyślij potwierdzenie
                await interaction.followup.send(
                    "✅ Ranking został zaktualizowany!", 
                    ephemeral=True
                )
                
            except Exception as e:
                safe_print(f"❌ Błąd slash command update_leaderboard: {e}")
                await interaction.followup.send(
                    f"❌ Wystąpił błąd podczas aktualizacji rankingu: {e}", 
                    ephemeral=True
                )
        
        @self.bot.tree.command(
            name="leaderboard",
            description="Pokazuje aktualny ranking punktów",
            guild=discord.Object(id=int(self.guild_id))
        )
        async def show_leaderboard(interaction: discord.Interaction):
            """Slash command do pokazania rankingu"""
            
            await interaction.response.defer(ephemeral=True)
            
            try:
                # Pobierz top użytkowników
                top_users = self.user_database.get_top_users(10)
                
                if not top_users:
                    await interaction.followup.send(
                        "📊 Brak danych w rankingu!", 
                        ephemeral=True
                    )
                    return
                
                # Stwórz embed z rankingiem
                embed = discord.Embed(
                    title="🏆 RANKING PUNKTÓW",
                    description="Top 10 graczy ze streama",
                    color=0xFFD700,  # Złoty
                    timestamp=datetime.now(self.poland_tz)
                )
                
                # Emoji dla pozycji
                position_emojis = {
                    1: "🥇", 2: "🥈", 3: "🥉",
                    4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"
                }
                
                leaderboard_text = ""
                for i, (username, points) in enumerate(top_users, 1):
                    emoji = position_emojis.get(i, f"{i}.")
                    leaderboard_text += f"{emoji} **{username}** - {points:,} pkt\n"
                
                embed.add_field(
                    name="🏆 TOP 10",
                    value=leaderboard_text,
                    inline=False
                )
                
                embed.set_footer(text="KranikBot • Standalone Discord Bot")
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
            except Exception as e:
                safe_print(f"❌ Błąd slash command leaderboard: {e}")
                await interaction.followup.send(
                    f"❌ Wystąpił błąd podczas pobierania rankingu: {e}", 
                    ephemeral=True
                )
        
        @self.bot.tree.command(
            name="update_shop",
            description="Wymusza aktualizację sklepu na Discord",
            guild=discord.Object(id=int(self.guild_id))
        )
        async def update_shop(interaction: discord.Interaction):
            """Slash command do aktualizacji sklepu"""
            
            # Sprawdź uprawnienia (administrator, moderator lub kranik1606)
            is_admin = interaction.user.guild_permissions.administrator
            is_mod = any(role.name.lower() in ['moderator', 'mod', 'admin'] for role in interaction.user.roles)
            is_kranik = interaction.user.name.lower() == "kranik1606"
            
            if not (is_admin or is_mod or is_kranik):
                await interaction.response.send_message(
                    "❌ Nie masz uprawnień do używania tej komendy!", 
                    ephemeral=True
                )
                return
            
            # Sprawdź czy shop jest dostępny
            if not self.shop:
                await interaction.response.send_message(
                    "❌ Sklep nie jest dostępny!", 
                    ephemeral=True
                )
                return
            
            # Odpowiedz natychmiast
            await interaction.response.send_message(
                "🛒 Aktualizuję sklep Discord...", 
                ephemeral=True
            )
            
            try:
                # Uruchom aktualizację sklepu w osobnym wątku
                def update_shop_thread():
                    try:
                        self.shop.force_update_shop_post()
                        safe_print(f"✅ Sklep Discord zaktualizowany przez slash command przez {interaction.user}")
                    except Exception as e:
                        safe_print(f"❌ Błąd w wątku aktualizacji sklepu: {e}")
                
                # Uruchom w osobnym wątku
                thread = threading.Thread(target=update_shop_thread)
                thread.daemon = True
                thread.start()
                
                # Wyślij potwierdzenie
                await interaction.followup.send(
                    "✅ Sklep został zaktualizowany!", 
                    ephemeral=True
                )
                
            except Exception as e:
                safe_print(f"❌ Błąd slash command update_shop: {e}")
                await interaction.followup.send(
                    f"❌ Wystąpił błąd podczas aktualizacji sklepu: {e}", 
                    ephemeral=True
                )

        @self.bot.tree.command(
            name="clear_channel",
            description="Usuwa wszystkie wiadomości z tego kanału",
            guild=discord.Object(id=int(self.guild_id))
        )
        async def clear_channel(interaction: discord.Interaction):
            """Slash command do usuwania wszystkich wiadomości z kanału"""
            
            # Lista dozwolonych kanałów
            allowed_channels = [
                1343251287122120714,  # Pierwszy dozwolony kanał
                1367042368355831818,  # Drugi dozwolony kanał
                1401702526503358464   # Trzeci dozwolony kanał
            ]
            
            # Sprawdź czy kanał jest na liście dozwolonych
            if interaction.channel.id not in allowed_channels:
                await interaction.response.send_message(
                    "❌ Ta komenda może być używana tylko w określonych kanałach!", 
                    ephemeral=True
                )
                return
            
            # Sprawdź uprawnienia (administrator lub określona rola)
            if not (interaction.user.guild_permissions.administrator or 
                   any(role.name.lower() in ['moderator', 'mod', 'admin'] for role in interaction.user.roles)):
                await interaction.response.send_message(
                    "❌ Nie masz uprawnień do używania tej komendy!", 
                    ephemeral=True
                )
                return
            
            # Odpowiedz natychmiast
            await interaction.response.send_message(
                "🗑️ Usuwam wszystkie wiadomości z tego kanału...", 
                ephemeral=True
            )
            
            try:
                channel = interaction.channel
                deleted_count = 0
                
                # Usuń wiadomości w partiach (Discord ma limit 100 wiadomości na raz)
                while True:
                    # Pobierz wiadomości (maksymalnie 100)
                    messages = []
                    async for message in channel.history(limit=100):
                        messages.append(message)
                    
                    if not messages:
                        break
                    
                    # Podziel wiadomości na nowe (< 14 dni) i stare (>= 14 dni)
                    # Discord bulk delete działa tylko dla wiadomości młodszych niż 14 dni
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
                    
                    # Bulk delete dla nowych wiadomości
                    if new_messages:
                        if len(new_messages) == 1:
                            await new_messages[0].delete()
                            deleted_count += 1
                        else:
                            try:
                                await channel.delete_messages(new_messages)
                                deleted_count += len(new_messages)
                            except discord.HTTPException:
                                # Jeśli bulk delete nie działa, usuń pojedynczo
                                for message in new_messages:
                                    try:
                                        await message.delete()
                                        deleted_count += 1
                                    except discord.NotFound:
                                        pass
                                    except discord.Forbidden:
                                        pass
                    
                    # Usuń stare wiadomości pojedynczo
                    for message in old_messages:
                        try:
                            await message.delete()
                            deleted_count += 1
                        except discord.NotFound:
                            pass
                        except discord.Forbidden:
                            pass
                        except discord.HTTPException:
                            # Wiadomość może być za stara lub chroniona
                            pass
                
                # Wyślij potwierdzenie
                await interaction.followup.send(
                    f"✅ Usunięto {deleted_count} wiadomości z kanału {channel.mention}!", 
                    ephemeral=True
                )
                
                safe_print(f"🗑️ Usunięto {deleted_count} wiadomości z kanału {channel.name} przez {interaction.user}")
                
            except discord.Forbidden:
                await interaction.followup.send(
                    "❌ Bot nie ma uprawnień do usuwania wiadomości w tym kanale!", 
                    ephemeral=True
                )
            except Exception as e:
                safe_print(f"❌ Błąd slash command clear_channel: {e}")
                await interaction.followup.send(
                    f"❌ Wystąpił błąd podczas usuwania wiadomości: {e}", 
                    ephemeral=True
                )
        
        @self.bot.tree.command(
            name="status",
            description="Pokazuje status standalone Discord bota",
            guild=discord.Object(id=int(self.guild_id))
        )
        async def bot_status(interaction: discord.Interaction):
            """Slash command do sprawdzenia statusu bota"""
            
            embed = discord.Embed(
                title="🤖 Status Discord Bota",
                description="Informacje o standalone Discord bocie",
                color=0x00FF00,  # Zielony
                timestamp=datetime.now(self.poland_tz)
            )
            
            embed.add_field(
                name="🟢 Status",
                value="Online (Standalone)",
                inline=True
            )
            
            embed.add_field(
                name="🏠 Serwer",
                value=f"{self.guild.name}" if self.guild else "Nieznany",
                inline=True
            )
            
            embed.add_field(
                name="👥 Użytkownicy w bazie",
                value=f"{len(self.user_database.get_all_users())}",
                inline=True
            )
            
            embed.set_footer(text="KranikBot • Standalone Discord Bot")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        @self.bot.tree.command(
            name="stats",
            description="Wyświetla statystyki bota na kanale statystyk",
            guild=discord.Object(id=int(self.guild_id))
        )
        async def show_stats(interaction: discord.Interaction):
            """Slash command do wyświetlania statystyk na określonym kanale"""
            
            # Sprawdź uprawnienia (administrator, moderator lub kranik1606)
            is_admin = interaction.user.guild_permissions.administrator
            is_mod = any(role.name.lower() in ['moderator', 'mod', 'admin'] for role in interaction.user.roles)
            is_owner = interaction.user.name.lower() == "kranik1606"
            
            if not (is_admin or is_mod or is_owner):
                await interaction.response.send_message(
                    "❌ Nie masz uprawnień do używania tej komendy!", 
                    ephemeral=True
                )
                return
            
            # Odpowiedz natychmiast
            await interaction.response.send_message(
                "📊 Wysyłam statystyki na kanał...", 
                ephemeral=True
            )
            
            try:
                # Pobierz statystyki z bazy danych
                stats = self.user_database.get_daily_stats()
                
                # ID kanału do wysłania statystyk
                stats_channel_id = 1402757620837781658
                
                # Pobierz kanał
                channel = self.bot.get_channel(stats_channel_id)
                if not channel:
                    await interaction.followup.send(
                        f"❌ Nie mogę znaleźć kanału o ID {stats_channel_id}!", 
                        ephemeral=True
                    )
                    return
                
                # Stwórz embed ze statystykami
                embed = discord.Embed(
                    title="📊 Statystyki bota",
                    description="Aktualne statystyki KranikBot",
                    color=0x00FF00,  # Zielony
                    timestamp=datetime.now(self.poland_tz)
                )
                
                embed.add_field(
                    name="👥 Nowi użytkownicy (dzisiaj)",
                    value=f"{stats.get('new_users', 0)}",
                    inline=True
                )
                
                embed.add_field(
                    name="🎮 Gry rozegrane (łącznie)",
                    value=f"{stats.get('games_played', 0)}",
                    inline=True
                )
                
                embed.add_field(
                    name="💰 Punkty rozdane (łącznie)",
                    value=f"{stats.get('points_given', 0):,}",
                    inline=True
                )
                
                embed.add_field(
                    name="🎁 Nagrody kupione",
                    value=f"{stats.get('rewards_bought', 0)}",
                    inline=True
                )
                
                embed.add_field(
                    name="❤️ Nowi followerzy",
                    value=f"{stats.get('new_followers', 0)}",
                    inline=True
                )
                
                embed.add_field(
                    name="⭐ Nowi subskrybenci",
                    value=f"{stats.get('new_subs', 0)}",
                    inline=True
                )
                
                embed.set_footer(text="KranikBot • Statystyki")
                
                # Wyślij embed na kanał statystyk
                await channel.send(embed=embed)
                
                # Potwierdź wysłanie
                await interaction.followup.send(
                    f"✅ Statystyki zostały wysłane na kanał {channel.mention}!", 
                    ephemeral=True
                )
                
                safe_print(f"📊 Statystyki wysłane na kanał przez {interaction.user}")
                
            except Exception as e:
                safe_print(f"❌ Błąd slash command stats: {e}")
                await interaction.followup.send(
                    f"❌ Wystąpił błąd podczas wysyłania statystyk: {e}", 
                    ephemeral=True
                )
        
        @self.bot.tree.command(
            name="send_bot_info",
            description="Wysyła grafikę z funkcjonalnościami bota na kanał",
            guild=discord.Object(id=int(self.guild_id))
        )
        async def send_bot_info(interaction: discord.Interaction, channel_id: str = None):
            """Slash command do wysyłania grafiki z funkcjonalnościami bota"""
            
            # Sprawdź uprawnienia
            if not (interaction.user.guild_permissions.administrator or 
                   any(role.name.lower() in ['moderator', 'mod'] for role in interaction.user.roles) or
                   interaction.user.name.lower() == 'kranik1606'):
                await interaction.response.send_message(
                    "❌ Nie masz uprawnień do użycia tej komendy!", 
                    ephemeral=True
                )
                return
            
            # Odpowiedz natychmiast
            await interaction.response.send_message(
                "📤 Wysyłam grafikę z funkcjonalnościami bota...", 
                ephemeral=True
            )
            
            try:
                # Określ kanał docelowy
                if channel_id:
                    try:
                        target_channel = self.bot.get_channel(int(channel_id))
                        if not target_channel:
                            await interaction.followup.send(
                                f"❌ Nie znaleziono kanału o ID: {channel_id}", 
                                ephemeral=True
                            )
                            return
                    except ValueError:
                        await interaction.followup.send(
                            "❌ Nieprawidłowe ID kanału!", 
                            ephemeral=True
                        )
                        return
                else:
                    target_channel = interaction.channel
                
                # Ścieżka do pliku grafiki
                import os
                svg_path = os.path.join(os.path.dirname(__file__), "twitch_bot_funkcjonalnosci_onepager.svg")
                
                if not os.path.exists(svg_path):
                    await interaction.followup.send(
                        "❌ Nie znaleziono pliku grafiki!", 
                        ephemeral=True
                    )
                    return
                
                # Wyślij plik
                with open(svg_path, 'rb') as f:
                    file = discord.File(f, filename="kranik_bot_funkcjonalnosci.svg")
                    
                    embed = discord.Embed(
                        title="🤖 KRANIK BOT - Funkcjonalności",
                        description="Kompletny przegląd wszystkich komend i uprawnień Twitch bota",
                        color=0x9146FF,
                        timestamp=datetime.now(self.poland_tz)
                    )
                    
                    embed.add_field(
                        name="👑 Właściciel",
                        value="Pełny dostęp do wszystkich funkcji",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="🛡️ Moderatorzy",
                        value="Uprawnienia moderacyjne",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="⭐ VIP/Subskrybenci",
                        value="Dodatkowe przywileje",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="🎵 Spotify",
                        value="Żądania piosenek, kontrola odtwarzania",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="🎮 Gry",
                        value="Roll, coinflip, roulette, quiz",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="🛒 Sklep",
                        value="System nagród za punkty",
                        inline=True
                    )
                    
                    embed.set_footer(text="KranikBot • Automatyczne funkcje i integracja Discord")
                    
                    await target_channel.send(embed=embed, file=file)
                
                await interaction.followup.send(
                    f"✅ Grafika została wysłana na kanał {target_channel.mention}!", 
                    ephemeral=True
                )
                
                safe_print(f"📤 Wysłano grafikę funkcjonalności na kanał {target_channel.name} przez {interaction.user}")
                
            except discord.Forbidden:
                await interaction.followup.send(
                    "❌ Bot nie ma uprawnień do wysyłania wiadomości na tym kanale!", 
                    ephemeral=True
                )
            except Exception as e:
                safe_print(f"❌ Błąd slash command send_bot_info: {e}")
                await interaction.followup.send(
                    f"❌ Wystąpił błąd podczas wysyłania grafiki: {e}", 
                    ephemeral=True
                )
    
    async def run_async(self):
        """Uruchamia bota asynchronicznie"""
        if not self.bot or not self.bot_token:
            safe_print(f"❌ Discord bot nie może zostać uruchomiony - brak konfiguracji")
            return False
        
        try:
            await self.bot.start(self.bot_token)
        except Exception as e:
            safe_print(f"❌ Błąd uruchamiania Discord bot: {e}")
            return False
    
    def run(self):
        """Uruchamia bota w głównej pętli"""
        if not self.bot or not self.bot_token:
            safe_print(f"❌ Discord bot nie może zostać uruchomiony - brak konfiguracji")
            return False
        
        try:
            safe_print(f"🚀 Uruchamiam Standalone Discord Bot...")
            asyncio.run(self.run_async())
        except KeyboardInterrupt:
            safe_print(f"🛑 Discord bot zatrzymany przez użytkownika")
        except Exception as e:
            safe_print(f"❌ Błąd uruchamiania Discord bot: {e}")
            return False
        
        return True
    
    def stop(self):
        """Zatrzymuje bota"""
        if self.bot and self.running:
            try:
                asyncio.create_task(self.bot.close())
                self.running = False
                safe_print(f"🛑 Standalone Discord bot zatrzymany")
            except Exception as e:
                safe_print(f"❌ Błąd zatrzymywania Discord bot: {e}")

def signal_handler(signum, frame):
    """Obsługa sygnału zatrzymania"""
    safe_print(f"\n🛑 Otrzymano sygnał zatrzymania...")
    sys.exit(0)

def main():
    """Główna funkcja uruchamiająca standalone Discord bot"""
    safe_print(f"🤖 === STANDALONE DISCORD BOT ===")
    safe_print(f"🔧 Inicjalizacja...")
    
    # Obsługa sygnałów
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Stwórz i uruchom bota
    bot = StandaloneDiscordBot()
    
    if bot.bot and bot.bot_token:
        safe_print(f"✅ Bot skonfigurowany poprawnie")
        bot.run()
    else:
        safe_print(f"❌ Błąd konfiguracji bota")
        safe_print(f"📖 Sprawdź plik .env i DISCORD_INTEGRATION_SETUP.md")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)