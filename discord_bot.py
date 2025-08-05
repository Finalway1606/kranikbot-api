import os
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import threading
from datetime import datetime
import pytz
import sys

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

class DiscordBot:
    def __init__(self, user_database, discord_integration, shop=None):
        self.user_database = user_database
        self.discord_integration = discord_integration
        self.shop = shop
        self.bot_token = os.getenv('DISCORD_BOT_TOKEN')
        self.guild_id = os.getenv('DISCORD_GUILD_ID')
        self.bot = None
        self.guild = None
        
        # Strefa czasowa dla Polski
        self.poland_tz = pytz.timezone('Europe/Warsaw')
        
        if not self.bot_token or not self.guild_id:
            safe_print(f"⚠️ Discord bot token lub guild ID nie są skonfigurowane")
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
                
                embed.set_footer(text="KranikBot • Twitch Integration")
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
            except Exception as e:
                safe_print(f"❌ Błąd slash command leaderboard: {e}")
                await interaction.followup.send(
                    f"❌ Wystąpił błąd podczas pobierania rankingu: {e}", 
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
                
                # Import dla obsługi dat
                from datetime import timedelta
                import pytz
                
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
            name="update_shop",
            description="Wymusza aktualizację sklepu na Discord",
            guild=discord.Object(id=int(self.guild_id))
        )
        async def update_shop(interaction: discord.Interaction):
            """Slash command do wymuszenia aktualizacji sklepu"""
            
            # Sprawdź czy shop jest dostępny
            if not self.shop:
                await interaction.response.send_message(
                    "❌ Sklep nie jest dostępny!", 
                    ephemeral=True
                )
                return
            
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
                "🛒 Aktualizuję sklep na Discord...", 
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
    
    def start_bot(self):
        """Uruchamia Discord bot w osobnym wątku"""
        if not self.bot or not self.bot_token:
            safe_print(f"❌ Discord bot nie może zostać uruchomiony - brak konfiguracji")
            return False
        
        def run_bot():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.bot.start(self.bot_token))
            except Exception as e:
                safe_print(f"❌ Błąd uruchamiania Discord bot: {e}")
        
        thread = threading.Thread(target=run_bot)
        thread.daemon = True
        thread.start()
        
        safe_print(f"🚀 Discord bot uruchamiany w tle...")
        return True
    
    def stop_bot(self):
        """Zatrzymuje Discord bot"""
        if self.bot:
            try:
                asyncio.create_task(self.bot.close())
                safe_print(f"🛑 Discord bot zatrzymany")
            except Exception as e:
                safe_print(f"❌ Błąd zatrzymywania Discord bot: {e}")
