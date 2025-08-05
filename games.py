import random
import time
from database import UserDatabase
from discord_integration import DiscordIntegration

class MiniGames:
    def __init__(self, db: UserDatabase, bot=None):
        self.db = db
        self.discord = DiscordIntegration()
        self.bot = bot
        self.active_polls = {}
        self.quiz_questions = [
            # Łatwe pytania (10 punktów)
            {"question": "Która planeta jest najbliżej Słońca?", "answer": "merkury", "points": 10},
            {"question": "Ile kontynentów jest na Ziemi?", "answer": "7", "points": 10},
            {"question": "Jaka jest stolica Polski?", "answer": "warszawa", "points": 10},
            {"question": "Ile nóg ma pająk?", "answer": "8", "points": 10},
            {"question": "Jaki kolor powstaje z mieszania czerwonego i niebieskiego?", "answer": "fioletowy", "points": 10},
            {"question": "Ile dni ma rok przestępny?", "answer": "366", "points": 10},
            {"question": "Jaka jest największa planeta w Układzie Słonecznym?", "answer": "jowisz", "points": 10},
            {"question": "Ile stron ma trójkąt?", "answer": "3", "points": 10},
            {"question": "Jaki gaz oddychamy?", "answer": "tlen", "points": 10},
            {"question": "Ile miesięcy ma rok?", "answer": "12", "points": 10},
            
            # Średnie pytania (15 punktów)
            {"question": "Która rzeka jest najdłuższa na świecie?", "answer": "nil", "points": 15},
            {"question": "W którym roku rozpoczęła się II wojna światowa?", "answer": "1939", "points": 15},
            {"question": "Jaka jest stolica Francji?", "answer": "paryż", "points": 15},
            {"question": "Ile wynosi pierwiastek z 64?", "answer": "8", "points": 15},
            {"question": "Kto napisał 'Pana Tadeusza'?", "answer": "mickiewicz", "points": 15},
            {"question": "Jaki ocean jest największy?", "answer": "spokojny", "points": 15},
            {"question": "Ile chromosomów ma człowiek?", "answer": "46", "points": 15},
            {"question": "W którym roku upadł Mur Berliński?", "answer": "1989", "points": 15},
            {"question": "Jaka jest waluta Japonii?", "answer": "jen", "points": 15},
            {"question": "Ile sekund ma minuta?", "answer": "60", "points": 15},
            {"question": "Kto wynalazł żarówkę?", "answer": "edison", "points": 15},
            {"question": "Jaka jest stolica Włoch?", "answer": "rzym", "points": 15},
            
            # Trudne pytania (20 punktów)
            {"question": "Jaka jest stolica Australii?", "answer": "canberra", "points": 20},
            {"question": "Ile kości ma dorosły człowiek?", "answer": "206", "points": 20},
            {"question": "Kto napisał 'Hamleta'?", "answer": "shakespeare", "points": 20},
            {"question": "Jaki pierwiastek ma symbol Au?", "answer": "złoto", "points": 20},
            {"question": "W którym roku Kolumb odkrył Amerykę?", "answer": "1492", "points": 20},
            {"question": "Ile wynosi liczba Pi (pierwsze 3 cyfry)?", "answer": "3.14", "points": 20},
            {"question": "Jaka jest najwyższa góra świata?", "answer": "everest", "points": 20},
            {"question": "Kto namalował 'Mona Lisę'?", "answer": "da vinci", "points": 20},
            {"question": "Jaka jest stolica Kanady?", "answer": "ottawa", "points": 20},
            {"question": "Ile planet jest w Układzie Słonecznym?", "answer": "8", "points": 20},
            
            # Bardzo trudne pytania (25 punktów)
            {"question": "Jaka jest stolica Kazachstanu?", "answer": "nur-sultan", "points": 25},
            {"question": "Kto skomponował 'Pory roku'?", "answer": "vivaldi", "points": 25},
            {"question": "Ile wynosi prędkość światła (w km/s)?", "answer": "300000", "points": 25},
            {"question": "W którym roku powstała Unia Europejska?", "answer": "1993", "points": 25},
            {"question": "Jaki pierwiastek ma symbol Hg?", "answer": "rtęć", "points": 25},
            {"question": "Kto napisał 'Wojnę i pokój'?", "answer": "tołstoj", "points": 25},
        ]
        self.current_quiz = None
        self.quiz_end_time = None
    
    def roll_dice(self, username):
        """Rzut kostką 1-100"""
        result = random.randint(1, 100)
        
        # Sprawdź czy użytkownik jest followerem
        is_follower = self.bot.is_follower(username) if self.bot else True
        
        # Nagrody za wysokie wyniki - tylko dla followerów
        if result >= 95:
            points = 50
            if is_follower:
                message = f"🎲 @{username} wyrzucił {result}! JACKPOT! +{points} punktów! 🎉"
                self.db.add_points(username, points, is_follower)
                # Powiadomienie Discord o dużej wygranej
                self.discord.notify_big_win(username, "dice", points)
            else:
                message = f"🎲 @{username} wyrzucił {result}! JACKPOT! Ale musisz być followerem aby otrzymać punkty! 🎉"
            self.db.update_game_stats(username, "dice", won=True)
        elif result >= 80:
            points = 20
            if is_follower:
                message = f"🎲 @{username} wyrzucił {result}! Świetny rzut! +{points} punktów! ✨"
                self.db.add_points(username, points, is_follower)
            else:
                message = f"🎲 @{username} wyrzucił {result}! Świetny rzut! Ale musisz być followerem aby otrzymać punkty! ✨"
            self.db.update_game_stats(username, "dice", won=True)
        elif result >= 50:
            points = 5
            if is_follower:
                message = f"🎲 @{username} wyrzucił {result}. Niezły rzut! +{points} punktów."
                self.db.add_points(username, points, is_follower)
            else:
                message = f"🎲 @{username} wyrzucił {result}. Niezły rzut! Ale musisz być followerem aby otrzymać punkty."
            self.db.update_game_stats(username, "dice", won=False)
        else:
            message = f"🎲 @{username} wyrzucił {result}. Spróbuj ponownie!"
            self.db.update_game_stats(username, "dice", won=False)
        
        return message
    
    def coin_flip(self, username, choice=None):
        """Rzut monetą"""
        result = random.choice(["orzeł", "reszka"])
        
        # Sprawdź czy użytkownik jest followerem
        is_follower = self.bot.is_follower(username) if self.bot else True
        
        if choice and choice.lower() in ["orzeł", "reszka", "orzel"]:
            user_choice = "orzeł" if choice.lower() in ["orzeł", "orzel"] else "reszka"
            
            if user_choice == result:
                points = 10
                if is_follower:
                    message = f"🪙 @{username} wybrał {user_choice} i wypadł {result}! Wygrana! +{points} punktów! 🎉"
                    self.db.add_points(username, points, is_follower)
                else:
                    message = f"🪙 @{username} wybrał {user_choice} i wypadł {result}! Wygrana! Ale musisz być followerem aby otrzymać punkty! 🎉"
                self.db.update_game_stats(username, "coinflip", won=True)
            else:
                message = f"🪙 @{username} wybrał {user_choice}, ale wypadł {result}. Przegrana! 😢"
                self.db.update_game_stats(username, "coinflip", won=False)
        else:
            message = f"🪙 @{username} rzucił monetą: {result}! (Użyj: !coinflip orzeł/reszka aby obstawiać)"
        
        return message
    
    def roulette(self, username, bet_input):
        """Ruletka z punktami - obsługuje liczby (0-36) i kolory (red/black)"""
        if not bet_input or bet_input.strip() == "":
            return f"❌ @{username}, podaj liczbę punktów lub kolor! Użyj: !roulette <punkty> lub !roulette red/black <punkty>"
        
        # Sprawdź czy użytkownik jest followerem
        is_follower = self.bot.is_follower(username) if self.bot else True
        if not is_follower:
            return f"❌ @{username}, musisz być followerem kanału aby grać w ruletę!"
        
        user = self.db.get_user(username)
        if not user:
            return f"❌ @{username}, wystąpił błąd z bazą danych!"
        
        current_points = user[1]  # points są na pozycji 1
        parts = bet_input.split()
        
        # Sprawdź czy to zakład na kolor
        if len(parts) == 2 and parts[0].lower() in ['red', 'black']:
            color_bet = parts[0].lower()
            try:
                bet_points = int(parts[1])
            except ValueError:
                return f"❌ @{username}, podaj prawidłową liczbę punktów po kolorze! Użyj: !roulette {color_bet} <punkty>"
            
            if bet_points <= 0:
                return f"❌ @{username}, musisz postawić przynajmniej 1 punkt!"
            
            if bet_points > current_points:
                return f"❌ @{username}, masz tylko {current_points} punktów!"
            
            # Losuj liczbę 0-36
            winning_number = random.randint(0, 36)
            
            # Określ kolor wygranej liczby (0 = zielony, 1-10,19-28 naprzemiennie, 11-18,29-36 naprzemiennie)
            if winning_number == 0:
                winning_color = "green"
                color_emoji = "🟢"
            elif winning_number in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]:
                winning_color = "red"
                color_emoji = "🔴"
            else:
                winning_color = "black"
                color_emoji = "⚫"
            
            if color_bet == winning_color:
                winnings = bet_points * 2
                self.db.add_points(username, winnings - bet_points, is_follower)
                message = f"🎰 @{username} wygrał zakład na {color_bet}! Wypadło {winning_number} {color_emoji}! Postawił {bet_points}, wygrał {winnings} punktów! 🎉"
                self.db.update_game_stats(username, "roulette", won=True)
                if winnings >= 50:
                    self.discord.notify_big_win(username, "roulette", winnings)
            else:
                self.db.remove_points(username, bet_points)
                message = f"🎰 @{username} przegrał zakład na {color_bet}. Wypadło {winning_number} {color_emoji}. Stracił {bet_points} punktów. 😢"
                self.db.update_game_stats(username, "roulette", won=False)
            
            return message
        
        # Sprawdź czy to zakład na konkretną liczbę (0-36)
        elif len(parts) == 2:
            try:
                number_bet = int(parts[0])
                bet_points = int(parts[1])
            except ValueError:
                return f"❌ @{username}, użyj: !roulette <liczba 0-36> <punkty> lub !roulette red/black <punkty>"
            
            if number_bet < 0 or number_bet > 36:
                return f"❌ @{username}, liczba musi być między 0 a 36!"
            
            if bet_points <= 0:
                return f"❌ @{username}, musisz postawić przynajmniej 1 punkt!"
            
            if bet_points > current_points:
                return f"❌ @{username}, masz tylko {current_points} punktów!"
            
            winning_number = random.randint(0, 36)
            
            if number_bet == winning_number:
                winnings = bet_points * 36  # Wypłata 36:1 za trafienie liczby
                self.db.add_points(username, winnings - bet_points, is_follower)
                message = f"🎰 @{username} TRAFIŁ LICZBĘ {winning_number}! JACKPOT! Postawił {bet_points}, wygrał {winnings} punktów! 🎉🎉🎉"
                self.db.update_game_stats(username, "roulette", won=True)
                self.discord.notify_big_win(username, "roulette", winnings)
            else:
                self.db.remove_points(username, bet_points)
                message = f"🎰 @{username} obstawił {number_bet}, ale wypadło {winning_number}. Stracił {bet_points} punktów. 😢"
                self.db.update_game_stats(username, "roulette", won=False)
            
            return message
        
        # Stary format - tylko punkty (zachowuję dla kompatybilności)
        else:
            try:
                bet_points = int(bet_input)
            except ValueError:
                return f"❌ @{username}, użyj: !roulette <punkty>, !roulette red/black <punkty> lub !roulette <liczba 0-36> <punkty>"
            
            if bet_points <= 0:
                return f"❌ @{username}, musisz postawić przynajmniej 1 punkt!"
            
            if bet_points > current_points:
                return f"❌ @{username}, masz tylko {current_points} punktów!"
            
            # Szanse: 40% wygrana (x2), 60% przegrana
            if random.randint(1, 100) <= 40:
                winnings = bet_points * 2
                self.db.add_points(username, winnings - bet_points, is_follower)
                message = f"🎰 @{username} wygrał w ruletce! Postawił {bet_points}, wygrał {winnings} punktów! 🎉"
                self.db.update_game_stats(username, "roulette", won=True)
                if winnings >= 50:
                    self.discord.notify_big_win(username, "roulette", winnings)
            else:
                self.db.remove_points(username, bet_points)
                message = f"🎰 @{username} przegrał w ruletce {bet_points} punktów. Spróbuj ponownie! 😢"
                self.db.update_game_stats(username, "roulette", won=False)
            
            return message
    
    def start_quiz(self):
        """Rozpoczyna quiz"""
        if self.current_quiz:
            return "❓ Quiz już trwa! Odpowiedz na aktualne pytanie."
        
        question_data = random.choice(self.quiz_questions)
        self.current_quiz = question_data
        self.quiz_end_time = time.time() + 30  # 30 sekund na odpowiedź
        
        return f"❓ QUIZ (30s): {question_data['question']} | Nagroda: {question_data['points']} punktów!"
    
    def answer_quiz(self, username, answer):
        """Sprawdza odpowiedź na quiz"""
        if not self.current_quiz:
            return f"❌ @{username}, nie ma aktywnego quizu! Użyj !quiz aby rozpocząć."
        
        if time.time() > self.quiz_end_time:
            correct_answer = self.current_quiz['answer']
            self.current_quiz = None
            return f"⏰ Czas minął! Prawidłowa odpowiedź to: {correct_answer}"
        
        # Sprawdź czy użytkownik jest followerem
        is_follower = self.bot.is_follower(username) if self.bot else True
        
        if answer.lower().strip() == self.current_quiz['answer'].lower():
            points = self.current_quiz['points']
            if is_follower:
                self.db.add_points(username, points, is_follower)
                self.db.update_game_stats(username, "quiz", won=True)
                self.current_quiz = None
                return f"🎉 @{username} odpowiedział prawidłowo! +{points} punktów!"
            else:
                self.db.update_game_stats(username, "quiz", won=True)
                self.current_quiz = None
                return f"🎉 @{username} odpowiedział prawidłowo! Ale musisz być followerem aby otrzymać punkty!"
        else:
            self.db.update_game_stats(username, "quiz", won=False)
            return f"❌ @{username}, nieprawidłowa odpowiedź! Spróbuj ponownie."
    
    def check_quiz_timeout(self):
        """Sprawdza czy quiz przekroczył limit czasu i automatycznie go kończy"""
        if self.current_quiz and time.time() > self.quiz_end_time:
            correct_answer = self.current_quiz['answer']
            self.current_quiz = None
            return f"⏰ Czas minął! Nikt nie odpowiedział. Prawidłowa odpowiedź to: {correct_answer}"
        return None
    
    def check_daily_bonus(self, username):
        """Sprawdza i przyznaje dzienny bonus"""
        # Sprawdź czy użytkownik jest followerem
        is_follower = self.bot.is_follower(username) if self.bot else True
        
        bonus = self.db.daily_bonus(username, is_follower)
        if bonus > 0:
            return f"🎁 @{username} otrzymał dzienny bonus: +{bonus} punktów!"
        return None
    
    def get_user_stats(self, username):
        """Pobiera statystyki użytkownika"""
        user = self.db.get_user(username)
        points = user[1]
        messages = user[2]
        
        # Sprawdź czy użytkownik jest followerem
        is_follower = self.bot.is_follower(username) if self.bot else True
        
        # Bonus dzienny - tylko dla followerów
        bonus_msg = ""
        if is_follower:
            daily_bonus = self.db.daily_bonus(username, is_follower)
            bonus_msg = f" | +{daily_bonus} dzienny bonus!" if daily_bonus > 0 else ""
        
        return f"📊 @{username}: {points} punktów | {messages} wiadomości{bonus_msg}"
    
    def get_leaderboard(self, limit=5):
        """Pobiera ranking"""
        top_users = self.db.get_top_users(limit)
        
        if not top_users:
            return "📊 Ranking jest pusty!"
        
        leaderboard = "🏆 TOP RANKING: "
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        
        for i, (username, points, messages) in enumerate(top_users):
            medal = medals[i] if i < len(medals) else f"{i+1}."
            leaderboard += f"{medal} {username}: {points} pkt | "
        
        return leaderboard.rstrip(" | ")
    
    def give_points(self, from_user, to_user, points, is_moderator=False):
        """Przekazuje punkty między użytkownikami"""
        # Sprawdź czy odbiorca jest followerem
        is_follower = self.bot.is_follower(to_user) if self.bot else True
        if not is_follower:
            return f"❌ @{from_user}, @{to_user} musi być followerem kanału aby otrzymać punkty!"
        
        if not is_moderator and from_user.lower() != "kranik1606":
            # Sprawdź czy ma wystarczająco punktów
            user = self.db.get_user(from_user)
            current_points = user[1]
            
            try:
                points = int(points)
            except ValueError:
                return f"❌ @{from_user}, podaj prawidłową liczbę punktów!"
            
            if points <= 0:
                return f"❌ @{from_user}, musisz przekazać przynajmniej 1 punkt!"
            
            if points > current_points:
                return f"❌ @{from_user}, masz tylko {current_points} punktów!"
            
            # Przekaż punkty
            self.db.remove_points(from_user, points)
            self.db.add_points(to_user, points, is_follower)
            return f"💝 @{from_user} przekazał {points} punktów dla @{to_user}!"
        else:
            # Moderator może dawać punkty za darmo
            try:
                points = int(points)
            except ValueError:
                return f"❌ Podaj prawidłową liczbę punktów!"
            
            self.db.add_points(to_user, points, is_follower)
            return f"🎁 @{to_user} otrzymał {points} punktów od moderatora!"
    
    def reset_all_points(self):
        """Resetuje punkty wszystkich użytkowników do 0 (tylko dla właściciela)"""
        affected_rows = self.db.reset_all_points()
        return affected_rows