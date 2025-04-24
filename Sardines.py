#!/usr/bin/env python3
import pygame, sys, math, random, json, os
import pygame.gfxdraw
from pygame.math import Vector2

# -------------------------------
# Constants and Global Variables
# -------------------------------
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
HIGH_SCORE_FILE = "high_scores.json"

# Define game states
GAME_STATES = {
    "MENU": "menu",
    "PLAYING": "playing",
    "GAMEOVER": "gameover",
    "NAME_INPUT": "name_input"
}

# Color definitions (using nicer shades)
COLORS = {
    "BLUE": (10, 10, 50),
    "LIGHT_BLUE": (30, 144, 255),
    "WHITE": (255, 255, 255),
    "RED": (220, 20, 60),
    "GREEN": (60, 179, 113),
    "YELLOW": (255, 215, 0),
    "BLACK": (0, 0, 0),
    "ORANGE": (255, 140, 0),
    "PURPLE": (138, 43, 226)
}

# -------------------------------
# Helper Drawing Functions
# -------------------------------
def draw_antialiased_ellipse(surface, rect, color):
    # Draw an anti-aliased ellipse outline using gfxdraw
    x, y, w, h = rect
    for i in range(2):  # thickness of outline
        pygame.gfxdraw.ellipse(surface, x + w//2, y + h//2, (w//2)-i, (h//2)-i, color)

def fill_antialiased_ellipse(surface, rect, color):
    # Draw a filled anti-aliased ellipse
    pygame.gfxdraw.filled_ellipse(surface, rect[0] + rect[2]//2, rect[1] + rect[3]//2, rect[2]//2, rect[3]//2, color)

# -------------------------------
# Base Game Object Class
# -------------------------------
class GameObject:
    def __init__(self, x, y, width, height):
        self.position = Vector2(x, y)
        self.size = Vector2(width, height)
    def get_rect(self, shrink=0):
        # Optionally shrink the rect for less sensitive collision
        return pygame.Rect(int(self.position.x + shrink), int(self.position.y + shrink), int(self.size.x - 2*shrink), int(self.size.y - 2*shrink))
    def collides_with(self, other):
        # Use a buffer/shrink for both objects
        buffer = 18  # pixels to shrink collision box on all sides
        return self.get_rect(buffer).colliderect(other.get_rect(buffer))

# -------------------------------
# Player (Fish) Class with Improved Visuals
# -------------------------------
class Fish(GameObject):
    def __init__(self, x, y):
        super().__init__(x, y, 100, 70)
        self.speed = 345  # pixels per second
        self.invincible = False
        self.invincible_timer = 0
        self.direction = 1  # 1 = right, -1 = left
        self.velocity = Vector2(0, 0)
    def update(self, dt, keys):
        self.velocity = Vector2(0, 0)
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.velocity.x = -1
            self.direction = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.velocity.x = 1
            self.direction = 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.velocity.y = -1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.velocity.y = 1
        if self.velocity.length() > 0:
            self.velocity.normalize_ip()
        self.position += self.velocity * self.speed * dt
        self.position.x = max(0, min(SCREEN_WIDTH - self.size.x, self.position.x))
        self.position.y = max(0, min(SCREEN_HEIGHT - self.size.y, self.position.y))
        if self.invincible:
            self.invincible_timer -= dt
            if self.invincible_timer <= 0:
                self.invincible = False
    def draw(self, surface):
        rect = self.get_rect()
        center = rect.center
        font = pygame.font.SysFont("Segoe UI Emoji", 60)
        emoji = "🐟" if not self.invincible else "🦄"
        emoji_surf = font.render(emoji, True, (255,255,255))
        emoji_rect = emoji_surf.get_rect(center=center)
        surface.blit(emoji_surf, emoji_rect)

# -------------------------------
# Shark (Enemy) Class with Improved Visuals and Behavior
# -------------------------------
class Shark(GameObject):
    def __init__(self, x, y, speed):
        super().__init__(x, y, 140, 90)
        self.speed = speed
    def update(self, dt, target_position):
        # Use predictive chase with a random offset for unpredictable movement
        direction = target_position - self.position
        if direction.length() > 0:
            direction.normalize_ip()
            random_offset = Vector2(random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3))
            direction += random_offset
            if direction.length() > 0:
                direction.normalize_ip()
            self.position += direction * self.speed * dt
    def draw(self, surface):
        rect = self.get_rect()
        center = rect.center
        font = pygame.font.SysFont("Segoe UI Emoji", 70)
        emoji = "🦈"
        emoji_surf = font.render(emoji, True, (255,255,255))
        emoji_rect = emoji_surf.get_rect(center=center)
        surface.blit(emoji_surf, emoji_rect)

# -------------------------------
# Powerup Class
# -------------------------------
class Powerup(GameObject):
    def __init__(self, x, y, type):
        super().__init__(x, y, 30, 30)
        self.type = type
        self.active = True
    def draw(self, surface):
        rect = self.get_rect()
        center = rect.center
        font = pygame.font.SysFont("Segoe UI Emoji", 32)
        if self.type == "invincible":
            emoji = "⭐"
        elif self.type == "slow":
            emoji = "🐢"
        elif self.type == "score":
            emoji = "💎"
        elif self.type == "mystery":
            emoji = "🎲"
        else:
            emoji = "🍀"
        emoji_surf = font.render(emoji, True, (255,255,255))
        emoji_rect = emoji_surf.get_rect(center=center)
        surface.blit(emoji_surf, emoji_rect)

# -------------------------------
# Button Class (for Menus)
# -------------------------------
class Button:
    def __init__(self, x, y, width, height, text, color, hover_color, action):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.action = action  # Callback
        self.is_hovered = False

    def draw(self, surface, font):
        draw_color = self.hover_color if self.is_hovered else self.color
        # Draw rounded rectangle for button background
        pygame.draw.rect(surface, draw_color, self.rect, border_radius=10)
        # Draw white outline
        pygame.draw.rect(surface, COLORS["WHITE"], self.rect, 2, border_radius=10)
        text_surf = font.render(self.text, True, COLORS["WHITE"])
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def contains(self, point):
        return self.rect.collidepoint(point)

# -------------------------------
# Background Bubble (for visual ambience)
# -------------------------------
class Bubble:
    def __init__(self):
        self.radius = random.randint(2, 6)
        self.x = random.uniform(0, SCREEN_WIDTH)
        self.y = SCREEN_HEIGHT + self.radius
        self.speed = random.uniform(30, 80)
    def update(self, dt):
        self.y -= self.speed * dt
        if self.y + self.radius < 0:
            self.y = SCREEN_HEIGHT + self.radius
            self.x = random.uniform(0, SCREEN_WIDTH)
    def draw(self, surface):
        pygame.gfxdraw.aacircle(surface, int(self.x), int(self.y), self.radius, COLORS["WHITE"])

# -------------------------------
# Main Game Class
# -------------------------------
class SharkChaseGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Improved Shark Chase Game")
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.SysFont("Arial", 40)
        self.font_medium = pygame.font.SysFont("Arial", 30)
        self.font_small = pygame.font.SysFont("Arial", 20)
        self.state = GAME_STATES["MENU"]
        self.username = "Player"
        self.username_input = ""
        self.difficulty = 1
        self.spawn_rate = 2000  # milliseconds between spawns
        self.last_spawn_time = pygame.time.get_ticks()
        self.game_time = 0
        self.score = 0
        self.powerup_spawn_rate = 10000 # Spawn powerup every 10 seconds
        self.last_powerup_spawn_time = pygame.time.get_ticks()
        self.player = Fish(SCREEN_WIDTH/2, SCREEN_HEIGHT/2)
        self.sharks = []
        self.powerups = []
        self.bubbles = [Bubble() for _ in range(30)]
        self.high_scores = self.load_high_scores()
        self.buttons = [
            Button(300, 150, 200, 50, "Easy", COLORS["GREEN"], (0,255,0), lambda: self.set_difficulty(1)),
            Button(300, 220, 200, 50, "Medium", COLORS["YELLOW"], (255,255,0), lambda: self.set_difficulty(2)),
            Button(300, 290, 200, 50, "Hard", COLORS["RED"], (255,0,0), lambda: self.set_difficulty(3)),
            Button(300, 360, 200, 50, "Set Name", COLORS["PURPLE"], (138,43,226), self.enter_name_mode),
            Button(300, 430, 200, 50, "Start", COLORS["LIGHT_BLUE"], (30,144,255), self.start_game)
        ]
    def load_high_scores(self):
        if os.path.exists(HIGH_SCORE_FILE):
            with open(HIGH_SCORE_FILE, "r") as f:
                return json.load(f)
        return []
    def save_high_scores(self):
        with open(HIGH_SCORE_FILE, "w") as f:
            json.dump(self.high_scores, f)
    def update_high_scores(self):
        new_score = {"name": self.username, "score": int(self.score)}
        self.high_scores.append(new_score)
        self.high_scores.sort(key=lambda s: s["score"], reverse=True)
        self.high_scores = self.high_scores[:5]
        self.save_high_scores()
    def set_difficulty(self, level):
        self.difficulty = level
    def enter_name_mode(self):
        self.username_input = ""
        self.state = GAME_STATES["NAME_INPUT"]
    def start_game(self):
        self.state = GAME_STATES["PLAYING"]
        self.score = 0
        self.game_time = 0
        self.player.position = Vector2(SCREEN_WIDTH/2, SCREEN_HEIGHT/2)
        self.sharks.clear()
        self.powerups.clear()
        self.last_spawn_time = pygame.time.get_ticks()
        self.last_powerup_spawn_time = pygame.time.get_ticks() # Reset powerup timer
    def restart_game(self):
        self.start_game()
    def spawn_shark(self):
        side = random.randint(0, 3)
        if side == 0:
            x = -100
            y = random.uniform(0, SCREEN_HEIGHT)
        elif side == 1:
            x = SCREEN_WIDTH + 100
            y = random.uniform(0, SCREEN_HEIGHT)
        elif side == 2:
            x = random.uniform(0, SCREEN_WIDTH)
            y = -100
        else:
            x = random.uniform(0, SCREEN_WIDTH)
            y = SCREEN_HEIGHT + 100
        speed = 150 + self.difficulty * 40
        shark = Shark(x, y, speed)
        self.sharks.append(shark)

    def spawn_powerup(self):
        x = random.uniform(50, SCREEN_WIDTH - 50)
        y = random.uniform(50, SCREEN_HEIGHT - 50)
        types = ["invincible", "slow", "score", "mystery"]
        powerup_type = random.choice(types)
        powerup = Powerup(x, y, powerup_type)
        self.powerups.append(powerup)

    def update(self, dt):
        if self.state == GAME_STATES["PLAYING"]:
            self.game_time += dt
            self.score += dt * 20
            keys = pygame.key.get_pressed()
            self.player.update(dt, keys)
            player_center = self.player.get_rect().center
            for shark in self.sharks:
                shark.update(dt, Vector2(player_center))
                if shark.collides_with(self.player) and not self.player.invincible:
                    self.update_high_scores()
                    self.state = GAME_STATES["GAMEOVER"]
            for powerup in self.powerups:
                if powerup.collides_with(self.player):
                    if powerup.type == "invincible":
                        self.player.invincible = True
                        self.player.invincible_timer = 3
                    elif powerup.type == "slow":
                        for shark in self.sharks:
                            shark.speed *= 0.5
                    elif powerup.type == "score":
                        self.score += 200
                    elif powerup.type == "mystery":
                        effect = random.choice(["invincible", "slow", "score"])
                        if effect == "invincible":
                            self.player.invincible = True
                            self.player.invincible_timer = 3
                        elif effect == "slow":
                            for shark in self.sharks:
                                shark.speed *= 0.5
                        elif effect == "score":
                            self.score += 200
                    powerup.active = False
            self.powerups = [p for p in self.powerups if p.active]
            if pygame.time.get_ticks() - self.last_spawn_time > self.spawn_rate:
                self.spawn_shark()
                self.last_spawn_time = pygame.time.get_ticks()
            if pygame.time.get_ticks() - self.last_powerup_spawn_time > self.powerup_spawn_rate:
                self.spawn_powerup()
                self.last_powerup_spawn_time = pygame.time.get_ticks()
            for bubble in self.bubbles:
                bubble.update(dt)
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if self.state == GAME_STATES["GAMEOVER"]:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.restart_game()
                    if event.key == pygame.K_m:
                        self.state = GAME_STATES["MENU"]
            if self.state == GAME_STATES["MENU"]:
                if event.type == pygame.MOUSEMOTION:
                    pos = event.pos
                    for button in self.buttons:
                        button.is_hovered = button.contains(pos)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    pos = event.pos
                    for button in self.buttons:
                        if button.contains(pos):
                            button.action()
            if self.state == GAME_STATES["NAME_INPUT"]:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        self.username = self.username_input.strip() if self.username_input.strip() else "Player"
                        self.state = GAME_STATES["MENU"]
                    elif event.key == pygame.K_BACKSPACE:
                        self.username_input = self.username_input[:-1]
                    else:
                        if event.unicode.isprintable():
                            self.username_input += event.unicode
    def draw(self):
        self.screen.fill(COLORS["BLUE"])
        for bubble in self.bubbles:
            bubble.draw(self.screen)
        if self.state == GAME_STATES["MENU"]:
            self.draw_menu()
        elif self.state in (GAME_STATES["PLAYING"], GAME_STATES["GAMEOVER"]):
            self.player.draw(self.screen)
            for shark in self.sharks:
                shark.draw(self.screen)
            for powerup in self.powerups:
                powerup.draw(self.screen)
            score_text = self.font_small.render(f"Score: {int(self.score)}", True, COLORS["YELLOW"])
            time_text = self.font_small.render(f"Time: {int(self.game_time)}", True, COLORS["YELLOW"])
            self.screen.blit(score_text, (10, 10))
            self.screen.blit(time_text, (10, 40))
            if self.state == GAME_STATES["GAMEOVER"]:
                self.draw_game_over()
        if self.state == GAME_STATES["NAME_INPUT"]:
            self.draw_name_input()
        pygame.display.flip()
    def draw_menu(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        # Smaller, centered ASCII Art Title for 'SARDINES'
        ascii_title = [
            "   _____                ___                ",
            "  / ___/____ __________/ (_)___  ___  _____",
            "  \\__ \\/ __ `/ ___/ __  / / __ \\/ _ \\/ ___/",
            " ___/ / /_/ / /  / /_/ / / / / /  __(__  ) ",
            "/____/\\__,_/_/   \\__,_/_/_/ /_/\\___/____/  "
        ]
        ascii_font = pygame.font.SysFont("Courier New", 20, bold=True) # Reverted font size
        title_start_y = 35 # Target center Y for the title block (Adjusted slightly higher)
        line_height = ascii_font.get_linesize() # Get actual line height from font
        num_lines = len(ascii_title)
        total_height = num_lines * line_height
        block_top_y = title_start_y - total_height // 2 # Calculate top Y for the entire block

        for i, line in enumerate(ascii_title):
            color = COLORS["LIGHT_BLUE"]
            text = ascii_font.render(line, True, color)
            # Center horizontally, position vertically line by line from block_top_y
            rect = text.get_rect(centerx=SCREEN_WIDTH/2, top=block_top_y + i * line_height)
            self.screen.blit(text, rect)

        # Difficulty selector label and buttons moved above menu buttons
        diff_label_font = pygame.font.SysFont("Arial", 24, bold=True)
        diff_label = diff_label_font.render("Select Difficulty:", True, COLORS["WHITE"])
        diff_label_rect = diff_label.get_rect(center=(SCREEN_WIDTH/2, 180)) # Moved up
        self.screen.blit(diff_label, diff_label_rect)

        difficulty_names = {1: "Easy", 2: "Medium", 3: "Hard"}
        diff_colors = {1: COLORS["GREEN"], 2: COLORS["YELLOW"], 3: COLORS["RED"]}
        diff_box_y = 210 # Moved up
        for i, level in enumerate([1,2,3]):
            color = diff_colors[level] if self.difficulty == level else COLORS["BLACK"]
            border_color = diff_colors[level]
            diff_box = pygame.Rect(260 + i*100, diff_box_y, 80, 40)
            pygame.draw.rect(self.screen, color, diff_box, border_radius=8)
            pygame.draw.rect(self.screen, border_color, diff_box, 3, border_radius=8)
            diff_text = diff_label_font.render(difficulty_names[level], True, COLORS["WHITE"] if self.difficulty == level else border_color)
            diff_text_rect = diff_text.get_rect(center=diff_box.center)
            self.screen.blit(diff_text, diff_text_rect)

        # Draw menu buttons (Adjust Y positions)
        button_start_y = 280 # Moved down to make space for difficulty selector
        button_spacing = 70
        font_ascii = pygame.font.SysFont("Courier New", 18, bold=True)
        for i, button in enumerate(self.buttons):
            # Update button rect position dynamically based on index
            button.rect.y = button_start_y + i * button_spacing
            button.draw(self.screen, font_ascii)

        # Username in bottom left corner
        username_text = font_ascii.render(f"Username: {self.username}", True, COLORS["WHITE"])
        self.screen.blit(username_text, (10, SCREEN_HEIGHT - 30))

        # Creator credit in ASCII at bottom left (LVXCAS - Corrected)
        ascii_lvxcas = [
            "    __ _    ___  ___________   _____",
            "   / /| |  / / |/ / ____/   | / ___/",
            "  / / | | / /|   / /   / /| | \\__ \\ ",
            " / /__| |/ //   / /___/ ___ |___/ / ",
            "/_____/___//_/|_\\____/_/  |_/____/  "
        ]
        lvxcas_font = pygame.font.SysFont("Courier New", 14, bold=True)
        credit_start_y = SCREEN_HEIGHT - 100 # Adjusted Y position
        for i, line in enumerate(ascii_lvxcas):
            text = lvxcas_font.render(line, True, COLORS["LIGHT_BLUE"])
            self.screen.blit(text, (10, credit_start_y + i*14))

    def draw_game_over(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        game_over_text = pygame.font.SysFont("Courier New", 40, bold=True).render("GAME OVER", True, COLORS["RED"])
        score_text = pygame.font.SysFont("Courier New", 30, bold=True).render(f"Score: {int(self.score)}", True, COLORS["WHITE"])
        restart_text = pygame.font.SysFont("Courier New", 20).render("Press R to restart", True, COLORS["WHITE"])
        menu_text = pygame.font.SysFont("Courier New", 20).render("Press M for menu", True, COLORS["WHITE"])

        self.screen.blit(game_over_text, game_over_text.get_rect(center=(SCREEN_WIDTH/2, 150)))
        self.screen.blit(score_text, score_text.get_rect(center=(SCREEN_WIDTH/2, 220)))

        # Display High Scores
        high_score_title = pygame.font.SysFont("Courier New", 30, bold=True).render("High Scores:", True, COLORS["YELLOW"])
        self.screen.blit(high_score_title, high_score_title.get_rect(center=(SCREEN_WIDTH/2, 280)))
        y_offset = 320
        for i, score_entry in enumerate(self.high_scores):
            entry_text = pygame.font.SysFont("Courier New", 20).render(f"{i+1}. {score_entry['name']} - {score_entry['score']}", True, COLORS["WHITE"])
            self.screen.blit(entry_text, entry_text.get_rect(center=(SCREEN_WIDTH/2, y_offset)))
            y_offset += 30

        self.screen.blit(restart_text, restart_text.get_rect(center=(SCREEN_WIDTH/2, y_offset + 20)))
        self.screen.blit(menu_text, menu_text.get_rect(center=(SCREEN_WIDTH/2, y_offset + 50)))

    def draw_name_input(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        prompt_text = pygame.font.SysFont("Courier New", 30, bold=True).render("Enter username:", True, COLORS["WHITE"])
        input_text = pygame.font.SysFont("Courier New", 30, bold=True).render(self.username_input, True, COLORS["YELLOW"])
        prompt_rect = prompt_text.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 - 30))
        input_rect = input_text.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 + 10))
        self.screen.blit(prompt_text, prompt_rect)
        self.screen.blit(input_text, input_rect)
    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()

if __name__ == "__main__":
    game = SharkChaseGame()
    game.run()
