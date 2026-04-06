import os
import sys
import time
import random
import json
from datetime import datetime

# ──────────────────────────────────────────────
# WINDOWS SETUP
# ──────────────────────────────────────────────
if sys.platform == "win32":
    import msvcrt
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-10), 7)
else:
    import tty
    import termios

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
WIDTH       = 30
HEIGHT      = 20
SCORES_FILE = "snake_scores.json"

# ──────────────────────────────────────────────
# COLORS
# ──────────────────────────────────────────────
RESET   = "\033[0m"
GREEN   = "\033[92m"
RED     = "\033[91m"
YELLOW  = "\033[93m"
CYAN    = "\033[96m"
MAGENTA = "\033[95m"
WHITE   = "\033[97m"
BOLD    = "\033[1m"
BG_BLACK = "\033[40m"

def clear():
    os.system("cls" if sys.platform == "win32" else "clear")

def hide_cursor():
    print("\033[?25l", end="", flush=True)

def show_cursor():
    print("\033[?25h", end="", flush=True)

def move_cursor(x, y):
    print(f"\033[{y+1};{x+1}H", end="", flush=True)

# ──────────────────────────────────────────────
# INPUT
# ──────────────────────────────────────────────

def get_key_windows():
    if msvcrt.kbhit():
        key = msvcrt.getch()
        if key == b'\xe0':
            key = msvcrt.getch()
            return {b'H': 'UP', b'P': 'DOWN', b'K': 'LEFT', b'M': 'RIGHT'}.get(key)
        return {b'w': 'UP', b's': 'DOWN', b'a': 'LEFT', b'd': 'RIGHT',
                b'q': 'QUIT', b'p': 'PAUSE'}.get(key)
    return None

def get_key_unix():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        key = sys.stdin.read(1)
        if key == '\x1b':
            key += sys.stdin.read(2)
            return {'\x1b[A': 'UP', '\x1b[B': 'DOWN',
                    '\x1b[C': 'RIGHT', '\x1b[D': 'LEFT'}.get(key)
        return {'w': 'UP', 's': 'DOWN', 'a': 'LEFT', 'd': 'RIGHT',
                'q': 'QUIT', 'p': 'PAUSE'}.get(key)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

def get_key():
    if sys.platform == "win32":
        return get_key_windows()
    return get_key_unix()

# ──────────────────────────────────────────────
# SCORES
# ──────────────────────────────────────────────

def load_scores():
    if os.path.exists(SCORES_FILE):
        with open(SCORES_FILE) as f:
            return json.load(f)
    return []

def save_score(score, level):
    scores = load_scores()
    scores.append({
        "score": score,
        "level": level,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    scores.sort(key=lambda x: x["score"], reverse=True)
    scores = scores[:10]  # keep top 10
    with open(SCORES_FILE, "w") as f:
        json.dump(scores, f, indent=2)

def show_leaderboard():
    scores = load_scores()
    clear()
    print(f"\n{BOLD}{YELLOW}  🏆 TOP 10 LEADERBOARD{RESET}\n")
    print(f"  {'#':<4} {'Score':<8} {'Level':<8} {'Date'}")
    print("  " + "─" * 40)
    if not scores:
        print(f"  {CYAN}No scores yet. Play a game!{RESET}")
    for i, s in enumerate(scores):
        medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"  {i+1}."
        print(f"  {medal}  {s['score']:<8} {s['level']:<8} {s['date']}")
    print()
    input("  Press Enter to go back...")

# ──────────────────────────────────────────────
# GAME
# ──────────────────────────────────────────────

class SnakeGame:
    def __init__(self, level=1):
        self.level    = level
        self.speed    = max(0.05, 0.2 - (level - 1) * 0.03)
        self.score    = 0
        self.paused   = False
        self.game_over = False

        # snake starts in middle
        cx = WIDTH // 2
        cy = HEIGHT // 2
        self.snake = [(cx, cy), (cx-1, cy), (cx-2, cy)]
        self.direction = 'RIGHT'
        self.next_dir  = 'RIGHT'

        self.food     = self._place_food()
        self.bonus    = None
        self.bonus_timer = 0

    def _place_food(self):
        while True:
            pos = (random.randint(1, WIDTH-2), random.randint(1, HEIGHT-2))
            if pos not in self.snake:
                return pos

    def _place_bonus(self):
        while True:
            pos = (random.randint(1, WIDTH-2), random.randint(1, HEIGHT-2))
            if pos not in self.snake and pos != self.food:
                return pos

    def update(self, key):
        if key == 'QUIT':
            self.game_over = True
            return
        if key == 'PAUSE':
            self.paused = not self.paused
            return

        # direction
        opposites = {'UP': 'DOWN', 'DOWN': 'UP', 'LEFT': 'RIGHT', 'RIGHT': 'LEFT'}
        if key in ('UP', 'DOWN', 'LEFT', 'RIGHT'):
            if key != opposites.get(self.direction):
                self.next_dir = key

        if self.paused:
            return

        self.direction = self.next_dir

        # move head
        hx, hy = self.snake[0]
        if   self.direction == 'UP':    hy -= 1
        elif self.direction == 'DOWN':  hy += 1
        elif self.direction == 'LEFT':  hx -= 1
        elif self.direction == 'RIGHT': hx += 1

        new_head = (hx, hy)

        # wall collision
        if hx <= 0 or hx >= WIDTH-1 or hy <= 0 or hy >= HEIGHT-1:
            self.game_over = True
            return

        # self collision
        if new_head in self.snake:
            self.game_over = True
            return

        self.snake.insert(0, new_head)

        # eat food
        if new_head == self.food:
            self.score += 10 * self.level
            self.food = self._place_food()
            # spawn bonus every 5 foods
            if self.score % (50 * self.level) == 0:
                self.bonus = self._place_bonus()
                self.bonus_timer = 50
        elif new_head == self.bonus:
            self.score += 50 * self.level
            self.bonus = None
            self.bonus_timer = 0
            self.snake.pop()  # don't grow on bonus
        else:
            self.snake.pop()

        # bonus timer
        if self.bonus:
            self.bonus_timer -= 1
            if self.bonus_timer <= 0:
                self.bonus = None

    def draw(self):
        # build grid
        grid = [[' ' for _ in range(WIDTH)] for _ in range(HEIGHT)]

        # walls
        for x in range(WIDTH):
            grid[0][x] = '─'
            grid[HEIGHT-1][x] = '─'
        for y in range(HEIGHT):
            grid[y][0] = '│'
            grid[y][WIDTH-1] = '│'
        grid[0][0] = '╔'
        grid[0][WIDTH-1] = '╗'
        grid[HEIGHT-1][0] = '╚'
        grid[HEIGHT-1][WIDTH-1] = '╝'

        # food
        fx, fy = self.food
        grid[fy][fx] = '●'

        # bonus
        if self.bonus:
            bx, by = self.bonus
            grid[by][bx] = '★'

        # snake body
        for i, (sx, sy) in enumerate(self.snake):
            grid[sy][sx] = '█' if i == 0 else '▪'

        # render
        move_cursor(0, 0)
        lines = []
        for y, row in enumerate(grid):
            line = ""
            for x, cell in enumerate(row):
                if cell in ('╔','╗','╚','╝','─','│'):
                    line += f"{CYAN}{cell}{RESET}"
                elif cell == '█':  # head
                    line += f"{GREEN}{BOLD}{cell}{RESET}"
                elif cell == '▪':  # body
                    line += f"{GREEN}{cell}{RESET}"
                elif cell == '●':  # food
                    line += f"{RED}{cell}{RESET}"
                elif cell == '★':  # bonus
                    line += f"{YELLOW}{cell}{RESET}"
                else:
                    line += cell
            lines.append(line)

        print('\n'.join(lines))

        # HUD
        status = f"{YELLOW}⏸ PAUSED{RESET}" if self.paused else f"{GREEN}▶ PLAYING{RESET}"
        bonus_info = f"  {YELLOW}★ BONUS!{RESET}" if self.bonus else ""
        print(f"\n  {WHITE}Score: {BOLD}{YELLOW}{self.score}{RESET}  "
              f"{WHITE}Level: {BOLD}{CYAN}{self.level}{RESET}  "
              f"{WHITE}Length: {BOLD}{MAGENTA}{len(self.snake)}{RESET}  "
              f"{status}{bonus_info}")
        print(f"  {WHITE}W/A/S/D or ↑←↓→ to move  |  P = pause  |  Q = quit{RESET}")


def play(level=1):
    clear()
    hide_cursor()
    game = SnakeGame(level)

    last_update = time.time()

    try:
        while not game.game_over:
            key = get_key()
            now = time.time()

            if now - last_update >= game.speed:
                game.update(key)
                game.draw()
                last_update = now
            elif key:
                game.update(key)
                game.draw()

        # game over screen
        move_cursor(0, HEIGHT + 4)
        print(f"\n  {RED}{BOLD}💀 GAME OVER!{RESET}")
        print(f"  Final Score : {YELLOW}{BOLD}{game.score}{RESET}")
        print(f"  Snake Length: {MAGENTA}{len(game.snake)}{RESET}")
        save_score(game.score, level)
        print(f"  {GREEN}Score saved!{RESET}\n")

    finally:
        show_cursor()

    input("  Press Enter to continue...")

# ──────────────────────────────────────────────
# MAIN MENU
# ──────────────────────────────────────────────

def main():
    while True:
        clear()
        print(f"""
{GREEN}{BOLD}
  ███████╗███╗   ██╗ █████╗ ██╗  ██╗███████╗
  ██╔════╝████╗  ██║██╔══██╗██║ ██╔╝██╔════╝
  ███████╗██╔██╗ ██║███████║█████╔╝ █████╗
  ╚════██║██║╚██╗██║██╔══██║██╔═██╗ ██╔══╝
  ███████║██║ ╚████║██║  ██║██║  ██╗███████╗
  ╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝
{RESET}""")

        print(f"  {WHITE}1. 🎮 Play (Easy){RESET}")
        print(f"  {WHITE}2. ⚡ Play (Medium){RESET}")
        print(f"  {WHITE}3. 🔥 Play (Hard){RESET}")
        print(f"  {WHITE}4. 🏆 Leaderboard{RESET}")
        print(f"  {WHITE}0. 👋 Exit{RESET}\n")

        choice = input("  Choose: ").strip()

        if   choice == "1": play(level=1)
        elif choice == "2": play(level=3)
        elif choice == "3": play(level=6)
        elif choice == "4": show_leaderboard()
        elif choice == "0":
            clear()
            print(f"\n  {GREEN}👋 Thanks for playing!{RESET}\n")
            break
        else:
            print(f"  {RED}Invalid choice.{RESET}")
            time.sleep(0.5)

if __name__ == "__main__":
    main()
