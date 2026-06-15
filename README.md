#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import sqlite3
import random
import time
import hashlib
import base64
import secrets
import string
import zlib
import threading
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

# ==================== КОНСТАНТЫ ====================
VERSION = "1.1.0"
GAME_NAME = "Dark of Hemi"
ATTACK_TIME_LIMIT = 15.0
ADMIN_PASSWORD = "fallenv4392!AdminSecure2024"
BASE_SAVE_SLOTS = 5
EXTRA_SLOT_COST = 500
MAX_TOTAL_SLOTS = 20
SHOP_REFRESH_TIME = 300
AUTO_SAVE_INTERVAL = 60

# GitHub URL для новостей
NEWS_URL = "https://raw.githubusercontent.com/wintlerclicker/DarkOfHemi/main/news"

# Контакты поддержки
SUPPORT_TG = "@ManagerFallen"
SUPPORT_DS = "error_top99lol._98265"
SUPPORT_EMAIL = "errortoplol36@gmail.com"
DEVELOPER_NAME = "The Fallen Angel"

# Цены на X++ предметы
XPP_SCYTHE_PRICE = 500000
XPP_ARMOR_PRICE = 300000

SCYTHE_ID = None
XPP_ARMOR_IDS = []

# ==================== ЦВЕТА ====================
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GOLD = '\033[93m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    BLINK = '\033[5m'
    RESET = '\033[0m'
    
    RARITY = {
        "U": WHITE, "F": WHITE, "D": BLUE, "C": BLUE,
        "B": GREEN, "B+": GREEN, "B++": GREEN, "A": YELLOW,
        "A+": YELLOW, "A++": YELLOW, "S": MAGENTA, "S+": MAGENTA,
        "S++": MAGENTA, "H": CYAN, "H+": CYAN, "H++": CYAN,
        "X": RED + BOLD, "X+": RED + BOLD, "X++": GOLD + BOLD + BLINK
    }

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_border(text: str, color: str = Colors.CYAN, width: int = 70):
    print(f"{color}{'═' * width}{Colors.RESET}")
    print(f"{color}║{text.center(width - 2)}║{Colors.RESET}")
    print(f"{color}{'═' * width}{Colors.RESET}")

def show_health_bar(current: int, maximum: int, width: int = 30) -> str:
    if maximum <= 0:
        maximum = 1
    current = min(current, maximum)
    percent = current / maximum
    filled = int(width * percent)
    empty = width - filled
    bar = "█" * filled + "░" * empty
    if percent > 0.6:
        color = Colors.GREEN
    elif percent > 0.3:
        color = Colors.YELLOW
    else:
        color = Colors.RED
    return f"{color}{bar}{Colors.RESET} [{current}/{maximum}]"

def pause(lang):
    input(f"\n{Colors.CYAN}{lang.get('press_enter')}{Colors.RESET}")

def loading_animation(text: str):
    print(f"{Colors.CYAN}{text}{Colors.RESET}", end="", flush=True)
    for _ in range(3):
        time.sleep(0.2)
        print(".", end="", flush=True)
    print(f"{Colors.GREEN} OK{Colors.RESET}")

# ==================== МЕНЮ СО СТРЕЛКАМИ ====================
def arrow_menu(options: List[str], title: str = "", lang=None) -> int:
    import msvcrt
    current = 0
    
    while True:
        clear()
        if title:
            show_border(title, Colors.CYAN, 70)
        
        print()
        for i, option in enumerate(options):
            if i == current:
                print(f"{Colors.GREEN}▶ {option}{Colors.RESET}")
            else:
                print(f"  {option}")
        
        if lang:
            print(f"\n{Colors.DIM}↑↓ - move, SPACE - select{Colors.RESET}")
        
        key = msvcrt.getch()
        
        if key == b'\xe0':
            key = msvcrt.getch()
            if key == b'H':
                current = (current - 1) % len(options)
            elif key == b'P':
                current = (current + 1) % len(options)
        elif key == b' ':
            return current
        elif key == b'\r':
            return current

# ==================== JSON ЯЗЫКИ ====================
class LanguageManager:
    def __init__(self):
        self.lang_dir = Path("lang")
        self.lang_dir.mkdir(parents=True, exist_ok=True)
        self.current_lang = "ru"
        self.strings = {}
        self.create_default_lang_files()
        self.load_language("ru")
    
    def create_default_lang_files(self):
        ru_file = self.lang_dir / "ru.json"
        en_file = self.lang_dir / "en.json"
        
        if not ru_file.exists():
            ru_data = {
                "welcome": "ДОБРО ПОЖАЛОВАТЬ", "new_game": "НОВАЯ ИГРА",
                "load_game": "ЗАГРУЗИТЬ ИГРУ", "settings": "НАСТРОЙКИ",
                "exit": "ВЫХОД", "news": "НОВОСТИ", "about": "О РАЗРАБОТЧИКЕ",
                "attack": "АТАКА", "potion_hp": "ЗЕЛЬЕ HP", "potion_mp": "ЗЕЛЬЕ MP",
                "defense": "ЗАЩИТА", "flee": "ПОБЕГ", "victory": "ПОБЕДА!",
                "defeat": "ПОРАЖЕНИЕ!", "critical": "КРИТИЧЕСКИЙ УДАР!",
                "level_up": "УРОВЕНЬ ПОВЫШЕН!", "shop": "МАГАЗИН",
                "inventory": "ИНВЕНТАРЬ", "save": "СОХРАНИТЬ", "rest": "ОТДОХНУТЬ",
                "boss": "БОСС", "gold": "золота", "diamonds": "алмазов",
                "level": "Уровень", "hp": "Здоровье", "mp": "Мана", "exp": "Опыт",
                "attack_stat": "Атака", "defense_stat": "Защита", "magic_stat": "Магия",
                "crit_stat": "Крит", "agility_stat": "Ловкость", "kills": "Убийств",
                "boss_kills": "Боссов", "language": "Язык", "back": "НАЗАД",
                "sell": "ПРОДАТЬ", "donate": "ДОНАТ", "daily": "ЕЖЕДНЕВНАЯ НАГРАДА",
                "quests": "КВЕСТЫ", "achievements": "ДОСТИЖЕНИЯ", "prestige": "ПРЕСТИЖ",
                "map": "КАРТА", "travel": "ПУТЕШЕСТВИЕ", "press_enter": "Нажмите Enter..."
            }
            with open(ru_file, "w", encoding="utf-8") as f:
                json.dump(ru_data, f, ensure_ascii=False, indent=2)
        
        if not en_file.exists():
            en_data = {
                "welcome": "WELCOME", "new_game": "NEW GAME", "load_game": "LOAD GAME",
                "settings": "SETTINGS", "exit": "EXIT", "news": "NEWS", "about": "ABOUT DEVELOPER",
                "attack": "ATTACK", "potion_hp": "HP POTION", "potion_mp": "MP POTION",
                "defense": "DEFENSE", "flee": "FLEE", "victory": "VICTORY!",
                "defeat": "DEFEAT!", "critical": "CRITICAL HIT!", "level_up": "LEVEL UP!",
                "shop": "SHOP", "inventory": "INVENTORY", "save": "SAVE", "rest": "REST",
                "boss": "BOSS", "gold": "gold", "diamonds": "diamonds", "level": "Level",
                "hp": "HP", "mp": "MP", "exp": "EXP", "attack_stat": "Attack",
                "defense_stat": "Defense", "magic_stat": "Magic", "crit_stat": "Crit",
                "agility_stat": "Agility", "kills": "Kills", "boss_kills": "Bosses",
                "language": "Language", "back": "BACK", "sell": "SELL", "donate": "DONATE",
                "daily": "DAILY REWARD", "quests": "QUESTS", "achievements": "ACHIEVEMENTS",
                "prestige": "PRESTIGE", "map": "MAP", "travel": "TRAVEL",
                "press_enter": "Press Enter..."
            }
            with open(en_file, "w", encoding="utf-8") as f:
                json.dump(en_data, f, ensure_ascii=False, indent=2)
    
    def load_language(self, lang: str):
        lang_file = self.lang_dir / f"{lang}.json"
        if lang_file.exists():
            with open(lang_file, "r", encoding="utf-8") as f:
                self.strings = json.load(f)
            self.current_lang = lang
        else:
            self.create_default_lang_files()
            self.load_language(lang)
    
    def get(self, key: str) -> str:
        return self.strings.get(key, key)
    
    def set_language(self, lang: str):
        self.load_language(lang)

# ==================== 3 МИРА ====================
WORLDS = [
    {"id": 1, "name_ru": "Средиземье", "name_en": "Middle Earth", "icon": "🌍", "min_level": 0, "max_level": 999},
    {"id": 2, "name_ru": "Запределье", "name_en": "Beyond", "icon": "🌌", "min_level": 1000, "max_level": 1999},
    {"id": 3, "name_ru": "Бесконечность", "name_en": "Infinity", "icon": "♾️", "min_level": 2000, "max_level": 3600},
]

# ==================== ЛОКАЦИИ (60 штук) ====================
LOCATION_NAMES_RU = [
    "Стартовая деревня", "Теневой лес", "Горы великанов", "Пустыня смерти", "Драконья пещера",
    "Болото проклятых", "Замок тьмы", "Храм древних", "Вулкан гнева", "Небесный город",
    "Ледяные пики", "Подземелье", "Долина ветров", "Кристальные пещеры", "Чертоги богов",
    "Грибной лес", "Заброшенные руины", "Мистическое озеро", "Пещера времени", "Финальный чертог",
    "Лес теней", "Пещеры страха", "Плато драконов", "Морская бездна", "Город мёртвых",
    "Храм луны", "Кузница духов", "Библиотека знаний", "Сад душ", "Арена чемпионов"
]

LOCATION_NAMES_EN = [
    "Starting Village", "Shadow Forest", "Giant Mountains", "Desert of Death", "Dragon Cave",
    "Swamp of Cursed", "Castle of Darkness", "Temple of Ancients", "Volcano of Wrath", "Heavenly City",
    "Ice Peaks", "Dungeon", "Valley of Winds", "Crystal Caves", "Halls of Gods",
    "Mushroom Forest", "Abandoned Ruins", "Mystic Lake", "Cave of Time", "Final Hall",
    "Shadow Woods", "Caverns of Fear", "Dragon Plateau", "Sea Abyss", "City of Dead",
    "Moon Temple", "Spirit Forge", "Library of Knowledge", "Garden of Souls", "Champion Arena"
]

LOCATION_ICONS = ["🏠", "🌲", "⛰️", "🏜️", "🐉", "🪦", "🏰", "🏛️", "🌋", "✨", "❄️", "🕳️", "🌬️", "💎", "👑", "🍄", "🏚️", "🌊", "⏰", "⭐", "🌳", "🕯️", "🦅", "🌊", "💀", "🌙", "⚒️", "📚", "🌸", "⚔️"]

class Location:
    def __init__(self, id: int, name_ru: str, name_en: str, icon: str, level_req: int, 
                 world_id: int, x: int, y: int, connected_to: List[int]):
        self.id = id
        self.name_ru = name_ru
        self.name_en = name_en
        self.icon = icon
        self.level_req = level_req
        self.world_id = world_id
        self.x = x
        self.y = y
        self.connected_to = connected_to

def generate_locations() -> List[Location]:
    locations = []
    loc_id = 1
    
    for world in WORLDS:
        base_level = world["min_level"]
        for i in range(20):  # 20 локаций на мир = 60 всего
            level_req = base_level + (i * 50) if base_level > 0 else i * 5 + 1
            
            name_ru = LOCATION_NAMES_RU[i % len(LOCATION_NAMES_RU)] + f" {i+1}" if i >= 20 else LOCATION_NAMES_RU[i]
            name_en = LOCATION_NAMES_EN[i % len(LOCATION_NAMES_EN)] + f" {i+1}" if i >= 20 else LOCATION_NAMES_EN[i]
            icon = LOCATION_ICONS[i % len(LOCATION_ICONS)]
            
            # Создаём связи (соседние локации в сетке)
            x = i % 5
            y = (i // 5) % 4
            connected = []
            if x > 0:
                connected.append(loc_id - 1)
            if x < 4:
                connected.append(loc_id + 1)
            if y > 0:
                connected.append(loc_id - 5)
            if y < 3:
                connected.append(loc_id + 5)
            
            locations.append(Location(loc_id, name_ru, name_en, icon, level_req, world["id"], x, y, connected))
            loc_id += 1
    
    return locations

LOCATIONS = generate_locations()

# ==================== КАРТА МИРА ====================
class WorldMap:
    def __init__(self, lang: LanguageManager):
        self.locations = LOCATIONS
        self.current_location_id = 1
        self.lang_manager = lang
    
    def get_text(self, key: str) -> str:
        return self.lang_manager.get(key)
    
    def get_location_name(self, loc: Location) -> str:
        return loc.name_ru if self.lang_manager.current_lang == "ru" else loc.name_en
    
    def get_world_name(self, world_id: int) -> str:
        for w in WORLDS:
            if w["id"] == world_id:
                return w["name_ru"] if self.lang_manager.current_lang == "ru" else w["name_en"]
        return "Unknown"
    
    def get_current_location(self) -> Optional[Location]:
        for loc in self.locations:
            if loc.id == self.current_location_id:
                return loc
        return None
    
    def get_location_by_id(self, loc_id: int) -> Optional[Location]:
        for loc in self.locations:
            if loc.id == loc_id:
                return loc
        return None
    
    def can_travel_to(self, location: Location, player_level: int) -> bool:
        return player_level >= location.level_req
    
    def show_map(self):
        clear()
        show_border(self.get_text("map"), Colors.GREEN, 80)
        
        # Группируем локации по мирам
        for world in WORLDS:
            world_locs = [loc for loc in self.locations if loc.world_id == world["id"]]
            if not world_locs:
                continue
            
            print(f"\n{Colors.GOLD}═══ {world['icon']} {self.get_world_name(world['id'])} ═══{Colors.RESET}")
            print(f"{Colors.DIM}Уровни: {world['min_level']}-{world['max_level']}{Colors.RESET}")
            
            # Создаём сетку 5x4 для каждого мира
            grid = [[" " * 12 for _ in range(5)] for _ in range(4)]
            
            for loc in world_locs:
                if 0 <= loc.x < 5 and 0 <= loc.y < 4:
                    if loc.id == self.current_location_id:
                        icon = f"{Colors.GOLD}📍{loc.icon}{Colors.RESET}"
                    else:
                        icon = loc.icon
                    name = self.get_location_name(loc)[:8]
                    grid[loc.y][loc.x] = f"{icon} {name}"
            
            print(f"{Colors.CYAN}   +{'-' * 65}+{Colors.RESET}")
            for y in range(4):
                line = f"{Colors.CYAN}{y}  |{Colors.RESET}"
                for x in range(5):
                    cell = grid[y][x]
                    line += f" {cell:<11} {Colors.CYAN}|{Colors.RESET}"
                print(line)
                print(f"{Colors.CYAN}   +{'-' * 65}+{Colors.RESET}")
        
        print(f"\n{Colors.YELLOW}📍 - {self.get_text('your_position')}{Colors.RESET}")
        print(f"{Colors.DIM}🔒 - {self.get_text('locked')}{Colors.RESET}")
    
    def show_current_location_info(self):
        current = self.get_current_location()
        if not current:
            return
        
        clear()
        world_name = self.get_world_name(current.world_id)
        show_border(f"{current.icon} {self.get_location_name(current)} [{world_name}]", Colors.MAGENTA, 70)
        
        desc_ru = f"Локация в мире {world_name}" if self.lang_manager.current_lang == "ru" else f"Location in {world_name}"
        print(f"\n{Colors.CYAN}{desc_ru}{Colors.RESET}")
        print(f"{Colors.YELLOW}{self.get_text('level_required')}: {current.level_req}{Colors.RESET}")
        
        connections = []
        for loc_id in current.connected_to:
            loc = self.get_location_by_id(loc_id)
            if loc:
                if self.can_travel_to(loc, 0):
                    connections.append(f"{Colors.GREEN}{self.get_location_name(loc)}{Colors.RESET}")
                else:
                    connections.append(f"{Colors.RED}{self.get_location_name(loc)} ({self.get_text('need_level')} {loc.level_req}){Colors.RESET}")
        
        if connections:
            print(f"\n{Colors.CYAN}🚪 {self.get_text('travel')}:{Colors.RESET}")
            for conn in connections:
                print(f"  • {conn}")
    
    def travel_to(self, loc_id: int, player_level: int) -> bool:
        target = self.get_location_by_id(loc_id)
        if not target:
            return False
        
        if not self.can_travel_to(target, player_level):
            print(f"{Colors.RED}❌ {self.get_text('level_required')} {target.level_req}!{Colors.RESET}")
            return False
        
        current = self.get_current_location()
        if current and loc_id not in current.connected_to:
            print(f"{Colors.RED}❌ {self.get_text('not_connected')}!{Colors.RESET}")
            return False
        
        self.current_location_id = loc_id
        print(f"{Colors.GREEN}✅ {self.get_text('travel_success')} {self.get_location_name(target)}!{Colors.RESET}")
        return True
    
    def travel_menu(self, player_level: int):
        current = self.get_current_location()
        if not current:
            return
        
        while True:
            self.show_current_location_info()
            
            options = []
            loc_ids = []
            
            for loc_id in current.connected_to:
                loc = self.get_location_by_id(loc_id)
                if loc:
                    name = self.get_location_name(loc)
                    if self.can_travel_to(loc, player_level):
                        options.append(f"🚪 {name}")
                    else:
                        options.append(f"🔒 {name} ({self.get_text('need_level')} {loc.level_req})")
                    loc_ids.append(loc_id)
            
            options.append(f"🗺️ {self.get_text('show_map')}")
            options.append(f"◀️ {self.get_text('back')}")
            
            print(f"\n{Colors.CYAN}──────────────────────────────────────────────────{Colors.RESET}")
            
            choice = arrow_menu(options, self.get_text("choose_direction"), self.lang_manager)
            
            if choice < len(loc_ids):
                target_id = loc_ids[choice]
                if self.travel_to(target_id, player_level):
                    return
                pause(self.lang_manager)
            elif choice == len(loc_ids):
                self.show_map()
                pause(self.lang_manager)
            else:
                break

# ==================== 35 КЛАССОВ ====================
CLASSES = [
    {"id": 1, "icon": "⚔️", "name_ru": "Воин", "name_en": "Warrior", "hp": 850, "mp": 200, "attack": 95, "defense": 80, "magic": 10, "crit": 10, "agility": 15},
    {"id": 2, "icon": "🔮", "name_ru": "Маг", "name_en": "Mage", "hp": 520, "mp": 350, "attack": 20, "defense": 30, "magic": 95, "crit": 8, "agility": 12},
    {"id": 3, "icon": "🗡️", "name_ru": "Разбойник", "name_en": "Rogue", "hp": 620, "mp": 180, "attack": 88, "defense": 45, "magic": 15, "crit": 25, "agility": 35},
    {"id": 4, "icon": "🛡️", "name_ru": "Паладин", "name_en": "Paladin", "hp": 780, "mp": 220, "attack": 75, "defense": 85, "magic": 40, "crit": 8, "agility": 12},
    {"id": 5, "icon": "🌿", "name_ru": "Друид", "name_en": "Druid", "hp": 680, "mp": 240, "attack": 55, "defense": 60, "magic": 75, "crit": 10, "agility": 20},
    {"id": 6, "icon": "💀", "name_ru": "Некромант", "name_en": "Necromancer", "hp": 580, "mp": 300, "attack": 30, "defense": 40, "magic": 88, "crit": 8, "agility": 10},
    {"id": 7, "icon": "😈", "name_ru": "Демон", "name_en": "Demon", "hp": 720, "mp": 190, "attack": 85, "defense": 55, "magic": 50, "crit": 15, "agility": 25},
    {"id": 8, "icon": "🏹", "name_ru": "Лучник", "name_en": "Archer", "hp": 590, "mp": 170, "attack": 85, "defense": 40, "magic": 10, "crit": 22, "agility": 30},
    {"id": 9, "icon": "⛏️", "name_ru": "Шаман", "name_en": "Shaman", "hp": 640, "mp": 260, "attack": 45, "defense": 55, "magic": 80, "crit": 8, "agility": 18},
    {"id": 10, "icon": "🧙", "name_ru": "Монах", "name_en": "Monk", "hp": 700, "mp": 150, "attack": 78, "defense": 50, "magic": 20, "crit": 18, "agility": 28},
    {"id": 11, "icon": "👑", "name_ru": "Рыцарь", "name_en": "Knight", "hp": 950, "mp": 160, "attack": 70, "defense": 95, "magic": 10, "crit": 8, "agility": 10},
    {"id": 12, "icon": "🔥", "name_ru": "Берсерк", "name_en": "Berserker", "hp": 800, "mp": 100, "attack": 105, "defense": 35, "magic": 5, "crit": 20, "agility": 22},
    {"id": 13, "icon": "❄️", "name_ru": "Криомант", "name_en": "Cryomancer", "hp": 550, "mp": 320, "attack": 25, "defense": 45, "magic": 90, "crit": 8, "agility": 14},
    {"id": 14, "icon": "⚡", "name_ru": "Элементаль", "name_en": "Elemental", "hp": 580, "mp": 340, "attack": 30, "defense": 40, "magic": 92, "crit": 10, "agility": 16},
    {"id": 15, "icon": "🕊️", "name_ru": "Жрец", "name_en": "Priest", "hp": 560, "mp": 360, "attack": 25, "defense": 35, "magic": 85, "crit": 5, "agility": 12},
    {"id": 16, "icon": "🦇", "name_ru": "Вампир", "name_en": "Vampire", "hp": 650, "mp": 160, "attack": 82, "defense": 50, "magic": 30, "crit": 20, "agility": 32},
    {"id": 17, "icon": "🧟", "name_ru": "Некротик", "name_en": "Necrotic", "hp": 750, "mp": 140, "attack": 65, "defense": 70, "magic": 25, "crit": 5, "agility": 8},
    {"id": 18, "icon": "🔱", "name_ru": "Танцор клинков", "name_en": "Blade Dancer", "hp": 600, "mp": 170, "attack": 80, "defense": 45, "magic": 10, "crit": 28, "agility": 40},
    {"id": 19, "icon": "🌙", "name_ru": "Лунный жрец", "name_en": "Moon Priest", "hp": 580, "mp": 280, "attack": 35, "defense": 45, "magic": 78, "crit": 12, "agility": 18},
    {"id": 20, "icon": "☀️", "name_ru": "Солнечный рыцарь", "name_en": "Sun Knight", "hp": 720, "mp": 200, "attack": 80, "defense": 70, "magic": 45, "crit": 12, "agility": 15},
    {"id": 21, "icon": "🔪", "name_ru": "Ассасин", "name_en": "Assassin", "hp": 500, "mp": 150, "attack": 95, "defense": 35, "magic": 5, "crit": 35, "agility": 45},
    {"id": 22, "icon": "✨", "name_ru": "Чародей", "name_en": "Sorcerer", "hp": 480, "mp": 400, "attack": 15, "defense": 25, "magic": 100, "crit": 10, "agility": 10},
    {"id": 23, "icon": "🗿", "name_ru": "Варвар", "name_en": "Barbarian", "hp": 900, "mp": 80, "attack": 100, "defense": 40, "magic": 0, "crit": 15, "agility": 18},
    {"id": 24, "icon": "⛪", "name_ru": "Инквизитор", "name_en": "Inquisitor", "hp": 650, "mp": 200, "attack": 70, "defense": 60, "magic": 55, "crit": 10, "agility": 14},
    {"id": 25, "icon": "📜", "name_ru": "Рунный маг", "name_en": "Rune Mage", "hp": 530, "mp": 330, "attack": 25, "defense": 35, "magic": 93, "crit": 8, "agility": 12},
    {"id": 26, "icon": "🐉", "name_ru": "Драконий рыцарь", "name_en": "Dragon Knight", "hp": 850, "mp": 220, "attack": 90, "defense": 75, "magic": 35, "crit": 12, "agility": 20},
    {"id": 27, "icon": "🌀", "name_ru": "Призыватель", "name_en": "Summoner", "hp": 550, "mp": 350, "attack": 20, "defense": 30, "magic": 85, "crit": 5, "agility": 10},
    {"id": 28, "icon": "🌑", "name_ru": "Темный рыцарь", "name_en": "Dark Knight", "hp": 700, "mp": 210, "attack": 85, "defense": 65, "magic": 40, "crit": 15, "agility": 18},
    {"id": 29, "icon": "⭐", "name_ru": "Звёздный чародей", "name_en": "Star Sorcerer", "hp": 510, "mp": 380, "attack": 20, "defense": 30, "magic": 98, "crit": 12, "agility": 14},
    {"id": 30, "icon": "💎", "name_ru": "Кристальный рыцарь", "name_en": "Crystal Knight", "hp": 800, "mp": 180, "attack": 75, "defense": 90, "magic": 25, "crit": 10, "agility": 12},
    {"id": 31, "icon": "⚙️", "name_ru": "Инженер", "name_en": "Engineer", "hp": 600, "mp": 250, "attack": 65, "defense": 55, "magic": 30, "crit": 15, "agility": 20},
    {"id": 32, "icon": "👻", "name_ru": "Жнец душ", "name_en": "Soul Reaper", "hp": 580, "mp": 200, "attack": 90, "defense": 40, "magic": 35, "crit": 25, "agility": 30},
    {"id": 33, "icon": "🎭", "name_ru": "Бард", "name_en": "Bard", "hp": 550, "mp": 280, "attack": 45, "defense": 40, "magic": 60, "crit": 15, "agility": 25},
    {"id": 34, "icon": "🔮", "name_ru": "Провидец", "name_en": "Seer", "hp": 490, "mp": 390, "attack": 15, "defense": 25, "magic": 95, "crit": 15, "agility": 15},
    {"id": 35, "icon": "💀", "name_ru": "Лич", "name_en": "Lich", "hp": 600, "mp": 350, "attack": 35, "defense": 45, "magic": 90, "crit": 10, "agility": 12}
]

# ==================== МЕГА-МОНСТРЫ ====================
MONSTER_TIERS = [
    {"tier": "Обычный", "tier_en": "Normal", "mult_hp": 1.0, "mult_attack": 1.0, "mult_defense": 1.0, "exp_mult": 1.0, "color": Colors.WHITE},
    {"tier": "Сильный", "tier_en": "Strong", "mult_hp": 2.0, "mult_attack": 1.8, "mult_defense": 1.5, "exp_mult": 2.0, "color": Colors.GREEN},
    {"tier": "Элитный", "tier_en": "Elite", "mult_hp": 5.0, "mult_attack": 3.0, "mult_defense": 2.5, "exp_mult": 5.0, "color": Colors.BLUE},
    {"tier": "Легендарный", "tier_en": "Legendary", "mult_hp": 10.0, "mult_attack": 5.0, "mult_defense": 4.0, "exp_mult": 10.0, "color": Colors.MAGENTA},
    {"tier": "Мифический", "tier_en": "Mythic", "mult_hp": 20.0, "mult_attack": 8.0, "mult_defense": 6.0, "exp_mult": 20.0, "color": Colors.RED},
    {"tier": "Божественный", "tier_en": "Divine", "mult_hp": 50.0, "mult_attack": 15.0, "mult_defense": 10.0, "exp_mult": 50.0, "color": Colors.YELLOW},
    {"tier": "Космический", "tier_en": "Cosmic", "mult_hp": 100.0, "mult_attack": 25.0, "mult_defense": 15.0, "exp_mult": 100.0, "color": Colors.CYAN},
    {"tier": "Хаоса", "tier_en": "Chaos", "mult_hp": 200.0, "mult_attack": 40.0, "mult_defense": 25.0, "exp_mult": 200.0, "color": Colors.RED + Colors.BOLD},
]

MONSTER_NAMES_RU = ["Гоблин-разрушитель", "Орк-генерал", "Тролль-берсерк", "Волк-альфа", "Медведь-шатун", "Паук-людоед", "Скелет-рыцарь", "Зомби-мутант", "Призрак-ужас", "Вампир-лорд", "Демон-князь", "Имп-убийца", "Голем-титан", "Элементаль-хаоса", "Гарпия-королева", "Сирена-смерть", "Минотавр-убийца", "Циклоп-гигант", "Грифон-небесный", "Химера-ужас"]
MONSTER_NAMES_EN = ["Goblin-Destroyer", "Orc-General", "Troll-Berserker", "Alpha-Wolf", "Raging-Bear", "Man-Eater-Spider", "Skeleton-Knight", "Mutant-Zombie", "Terror-Ghost", "Vampire-Lord", "Demon-Prince", "Assassin-Imp", "Titan-Golem", "Chaos-Elemental", "Queen-Harpy", "Death-Siren", "Minotaur-Slayer", "Giant-Cyclops", "Sky-Griffin", "Horror-Chimera"]

def generate_mega_monster(player_level: int, lang: str) -> Dict:
    tier = random.choices(MONSTER_TIERS, weights=[0.35, 0.25, 0.15, 0.10, 0.06, 0.04, 0.03, 0.02])[0]
    level = max(1, player_level + random.randint(-2, 5))
    
    name = random.choice(MONSTER_NAMES_RU if lang == "ru" else MONSTER_NAMES_EN)
    tier_name = tier["tier"] if lang == "ru" else tier["tier_en"]
    
    base_hp = 80 + level * 12
    base_attack = 15 + level * 3
    base_defense = 8 + level * 2
    base_exp = 80 + level * 20
    base_gold = 40 + level * 12
    
    return {
        "name": name, "tier": tier_name, "tier_color": tier["color"],
        "level": level, "hp": int(base_hp * tier["mult_hp"]),
        "max_hp": int(base_hp * tier["mult_hp"]), "attack": int(base_attack * tier["mult_attack"]),
        "defense": int(base_defense * tier["mult_defense"]), "exp_reward": int(base_exp * tier["exp_mult"]),
        "gold_reward": int(base_gold * tier["exp_mult"]), "icon": random.choice(["👾", "👹", "🧟", "🧛", "🐉"])
    }

# ==================== ПИТОМЦЫ ====================
PETS = [
    {"id": 1, "icon": "🔥", "name_ru": "Феникс", "name_en": "Phoenix", "attack": 50, "defense": 30, "hp": 200, "crit": 10, "agility": 15, "price_diamonds": 100},
    {"id": 2, "icon": "🐉", "name_ru": "Дракон", "name_en": "Dragon", "attack": 80, "defense": 40, "hp": 300, "crit": 15, "agility": 20, "price_diamonds": 250},
    {"id": 3, "icon": "🐕", "name_ru": "Цербер", "name_en": "Cerberus", "attack": 120, "defense": 60, "hp": 500, "crit": 20, "agility": 25, "price_diamonds": 500},
    {"id": 4, "icon": "🗿", "name_ru": "Титан", "name_en": "Titan", "attack": 200, "defense": 100, "hp": 1000, "crit": 25, "agility": 30, "price_diamonds": 1000},
]

# ==================== РЕДКОСТИ ====================
RARITIES = [
    {"name": "U", "name_en": "U", "mult": 0.5, "level": 1, "chance": 0.20, "color": Colors.WHITE},
    {"name": "F", "name_en": "F", "mult": 0.7, "level": 5, "chance": 0.18, "color": Colors.WHITE},
    {"name": "D", "name_en": "D", "mult": 0.9, "level": 10, "chance": 0.15, "color": Colors.BLUE},
    {"name": "C", "name_en": "C", "mult": 1.1, "level": 20, "chance": 0.12, "color": Colors.BLUE},
    {"name": "B", "name_en": "B", "mult": 1.3, "level": 35, "chance": 0.10, "color": Colors.GREEN},
    {"name": "B+", "name_en": "B+", "mult": 1.5, "level": 50, "chance": 0.08, "color": Colors.GREEN},
    {"name": "A", "name_en": "A", "mult": 1.8, "level": 70, "chance": 0.06, "color": Colors.YELLOW},
    {"name": "A+", "name_en": "A+", "mult": 2.1, "level": 90, "chance": 0.05, "color": Colors.YELLOW},
    {"name": "S", "name_en": "S", "mult": 2.5, "level": 120, "chance": 0.04, "color": Colors.MAGENTA},
    {"name": "S+", "name_en": "S+", "mult": 3.0, "level": 160, "chance": 0.03, "color": Colors.MAGENTA},
    {"name": "SS", "name_en": "SS", "mult": 3.5, "level": 200, "chance": 0.02, "color": Colors.RED},
    {"name": "X", "name_en": "X", "mult": 5.0, "level": 300, "chance": 0.01, "color": Colors.CYAN},
    {"name": "X+", "name_en": "X+", "mult": 6.0, "level": 400, "chance": 0.008, "color": Colors.CYAN + Colors.BOLD},
    {"name": "X++", "name_en": "X++", "mult": 7.5, "level": 500, "chance": 0.005, "color": Colors.GOLD + Colors.BOLD + Colors.BLINK},
]

ITEM_SLOTS = ["weapon", "armor", "helmet", "boots", "gloves", "ring", "necklace", "belt", "cloak", "scythe"]

# ==================== ГЕНЕРАЦИЯ ПРЕДМЕТОВ ====================
ITEMS = []
item_id = 1

for rarity in RARITIES:
    for slot in ITEM_SLOTS:
        mult = rarity["mult"]
        
        if slot == "scythe":
            scythe_mult = mult * 2.5
            item = {
                "id": item_id, "name_ru": f"{rarity['name']} Коса Смерти", "name_en": f"{rarity['name_en']} Scythe of Death",
                "rank": rarity["name"], "slot": "scythe", "attack": int(45 * scythe_mult),
                "defense": int(15 * scythe_mult), "hp": int(200 * scythe_mult), "mp": int(100 * scythe_mult),
                "crit": int(25 * scythe_mult), "agility": int(20 * scythe_mult), "magic": int(30 * scythe_mult),
                "price": int(500 * scythe_mult), "price_diamonds": int(50 * scythe_mult),
                "level_req": rarity["level"], "sell_price": int(250 * scythe_mult), "is_scythe": True
            }
            if rarity["name"] == "X++":
                SCYTHE_ID = item_id
                item["price"] = XPP_SCYTHE_PRICE
        else:
            item = {
                "id": item_id, "name_ru": f"{rarity['name']} {slot}", "name_en": f"{rarity['name_en']} {slot}",
                "rank": rarity["name"], "slot": slot, "attack": int(12 * mult), "defense": int(10 * mult),
                "hp": int(60 * mult), "mp": int(40 * mult), "crit": int(3 * mult),
                "agility": int(4 * mult), "magic": int(8 * mult), "price": int(120 * mult),
                "price_diamonds": int(12 * mult), "level_req": rarity["level"], "sell_price": int(60 * mult)
            }
        
        if slot == "armor" and rarity["name"] == "X++":
            XPP_ARMOR_IDS.append(item_id)
            item["price"] = XPP_ARMOR_PRICE
        
        ITEMS.append(item)
        item_id += 1

# ==================== КВЕСТЫ ====================
QUESTS = [
    {"id": 1, "icon": "⚔️", "name_ru": "Начинающий воин", "name_en": "Novice Warrior", "desc_ru": "Убейте 10 монстров", "desc_en": "Kill 10 monsters", "type": "kill", "target": 10, "reward_exp": 500, "reward_gold": 200, "reward_diamonds": 0},
    {"id": 2, "icon": "👑", "name_ru": "Охотник на боссов", "name_en": "Boss Hunter", "desc_ru": "Убейте 3 босса", "desc_en": "Kill 3 bosses", "type": "boss_kill", "target": 3, "reward_exp": 2000, "reward_gold": 1000, "reward_diamonds": 0},
    {"id": 3, "icon": "💰", "name_ru": "Богатство", "name_en": "Wealth", "desc_ru": "Соберите 10000 золота", "desc_en": "Collect 10000 gold", "type": "gold", "target": 10000, "reward_exp": 1000, "reward_gold": 500, "reward_diamonds": 0},
    {"id": 4, "icon": "⭐", "name_ru": "Мастер уровня", "name_en": "Level Master", "desc_ru": "Достигните 50 уровня", "desc_en": "Reach level 50", "type": "level", "target": 50, "reward_exp": 5000, "reward_gold": 5000, "reward_diamonds": 0},
]

# ==================== ДОСТИЖЕНИЯ ====================
ACHIEVEMENTS = [
    {"id": 1, "icon": "🎯", "name_ru": "Первая кровь", "name_en": "First Blood", "desc_ru": "Убейте первого монстра", "desc_en": "Kill your first monster", "type": "kills", "target": 1, "reward_gold": 100, "reward_diamonds": 0},
    {"id": 2, "icon": "🏆", "name_ru": "Охотник", "name_en": "Hunter", "desc_ru": "Убейте 100 монстров", "desc_en": "Kill 100 monsters", "type": "kills", "target": 100, "reward_gold": 1000, "reward_diamonds": 0},
    {"id": 3, "icon": "👑", "name_ru": "Убийца боссов", "name_en": "Boss Slayer", "desc_ru": "Убейте первого босса", "desc_en": "Kill your first boss", "type": "boss_kills", "target": 1, "reward_gold": 500, "reward_diamonds": 0},
    {"id": 4, "icon": "💰", "name_ru": "Богач", "name_en": "Rich", "desc_ru": "Соберите 100000 золота", "desc_en": "Collect 100000 gold", "type": "gold", "target": 100000, "reward_gold": 5000, "reward_diamonds": 0},
    {"id": 5, "icon": "⭐", "name_ru": "Мастер уровня", "name_en": "Level Master", "desc_ru": "Достигните 100 уровня", "desc_en": "Reach level 100", "type": "level", "target": 100, "reward_gold": 10000, "reward_diamonds": 0},
]

# ==================== 30-СЛОЙНОЕ ШИФРОВАНИЕ ====================
class UltraSecureCrypto:
    MASTER_KEYS = [f"DarkOfHemi_V1.1_Key_{i:03d}_Secure" for i in range(30)]
    
    @staticmethod
    def _xor_transform(data: bytes, key_idx: int) -> bytes:
        key = UltraSecureCrypto.MASTER_KEYS[key_idx % len(UltraSecureCrypto.MASTER_KEYS)].encode()
        return bytes([data[i] ^ key[i % len(key)] for i in range(len(data))])
    
    @staticmethod
    def encrypt(data: str) -> str:
        try:
            result = data.encode()
            for i in range(30):
                result = UltraSecureCrypto._xor_transform(result, i)
                result = zlib.compress(result, level=9)
                result = base64.b85encode(result)
            return result.decode()
        except:
            return ""
    
    @staticmethod
    def decrypt(data: str) -> str:
        try:
            result = data.encode()
            for i in range(29, -1, -1):
                result = base64.b85decode(result)
                result = zlib.decompress(result)
                result = UltraSecureCrypto._xor_transform(result, i)
            return result.decode()
        except:
            return ""

# ==================== НОВОСТИ ====================
class NewsManager:
    @staticmethod
    def get_news(lang: LanguageManager) -> str:
        try:
            req = urllib.request.Request(NEWS_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.read().decode('utf-8')
        except:
            return lang.get("error") + ": " + lang.get("no_internet")
    
    @staticmethod
    def show_news(lang: LanguageManager):
        clear()
        show_border(lang.get("news"), Colors.CYAN, 70)
        print(f"\n{Colors.YELLOW}📡 {lang.get('loading')}...{Colors.RESET}\n")
        news_text = NewsManager.get_news(lang)
        print(f"{Colors.CYAN}{'─' * 68}{Colors.RESET}")
        for line in news_text.split('\n'):
            if len(line) > 65:
                for i in range(0, len(line), 65):
                    print(f"{Colors.WHITE}{line[i:i+65]}{Colors.RESET}")
            else:
                print(f"{Colors.WHITE}{line}{Colors.RESET}")
        print(f"{Colors.CYAN}{'─' * 68}{Colors.RESET}")
        pause(lang)

# ==================== БАЗА ДАННЫХ ====================
class Database:
    def get_pet_name(self, pet_id):
        """Возвращает имя питомца"""
        names = {1: "Волк", 2: "Медведь", 3: "Феникс", 4: "Дракон", 5: "Единорог"}
        return names.get(pet_id, "Питомец")

    def __init__(self, lang: LanguageManager):
        self.db_path = Path("data/game.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.lang_manager = lang
        self.max_slots = BASE_SAVE_SLOTS
        self.init_db()
        self.load_settings()
    
    def get_text(self, key: str) -> str:
        return self.lang_manager.get(key)
    
    def load_settings(self):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key = 'max_slots'")
        row = c.fetchone()
        if row:
            self.max_slots = int(row[0])
        conn.close()
    
    def set_max_slots(self, slots: int):
        self.max_slots = min(slots, MAX_TOTAL_SLOTS)
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('max_slots', ?)", (str(self.max_slots),))
        conn.commit()
        conn.close()
    
    def init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS heroes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, class_id INTEGER, level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0, gold INTEGER DEFAULT 5000, diamonds INTEGER DEFAULT 0,
            kills INTEGER DEFAULT 0, boss_kills INTEGER DEFAULT 0, hp INTEGER, mp INTEGER,
            max_hp INTEGER, max_mp INTEGER, attack INTEGER, defense INTEGER, magic INTEGER,
            crit INTEGER, agility INTEGER, potions_hp INTEGER DEFAULT 10, potions_mp INTEGER DEFAULT 5,
            pet_id INTEGER DEFAULT 0, inventory TEXT DEFAULT '[]', equipped TEXT DEFAULT '{}',
            quests_progress TEXT DEFAULT '{}', achievements_unlocked TEXT DEFAULT '[]',
            total_gold_earned INTEGER DEFAULT 0, last_daily TIMESTAMP, current_location INTEGER DEFAULT 1,
            save_slot INTEGER DEFAULT 1, save_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY, reward_diamonds INTEGER, reward_gold INTEGER,
            reward_item_id INTEGER DEFAULT 0, used INTEGER DEFAULT 0,
            created_by TEXT, created TIMESTAMP, expires TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, value TEXT
        )''')
        
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('max_slots', ?)", (str(BASE_SAVE_SLOTS),))
        conn.commit()
        conn.close()
    
    def get_all_saves(self) -> List[Dict]:
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("SELECT save_slot, name, level, save_time FROM heroes ORDER BY save_slot")
        rows = c.fetchall()
        conn.close()
        return [{"slot": r[0], "name": r[1], "level": r[2], "time": r[3]} for r in rows]
    
    def save_hero(self, hero, save_slot: int = 1):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO heroes 
            (id, name, class_id, level, exp, gold, diamonds, kills, boss_kills,
             hp, mp, max_hp, max_mp, attack, defense, magic, crit, agility,
             potions_hp, potions_mp, pet_id, inventory, equipped, quests_progress,
             achievements_unlocked, total_gold_earned, last_daily, current_location, save_slot, save_time)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)''',
            (hero.name, hero.class_id, hero.level, hero.exp, hero.gold, hero.diamonds,
             hero.kills, hero.boss_kills, hero.hp, hero.mp, hero.max_hp, hero.max_mp,
             hero.attack, hero.defense, hero.magic, hero.crit, hero.agility,
             hero.potions_hp, hero.potions_mp, hero.pet_id,
             json.dumps(hero.inventory), json.dumps(hero.equipped),
             json.dumps(hero.quests_progress), json.dumps(hero.achievements_unlocked),
             hero.total_gold_earned, hero.last_daily, hero.current_location, save_slot))
        conn.commit()
        conn.close()
    
    def load_hero(self, save_slot: int = 1):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("SELECT * FROM heroes WHERE save_slot = ?", (save_slot,))
        row = c.fetchone()
        conn.close()
        return row
    
    def delete_hero(self, save_slot: int = 1):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("DELETE FROM heroes WHERE save_slot = ?", (save_slot,))
        conn.commit()
        conn.close()
    
    def export_hero(self, save_slot: int = 1, filename: str = None) -> str:
        data = self.load_hero(save_slot)
        if not data:
            return None
        
        if not filename:
            filename = f"hero_export_{data[1]}_{save_slot}_{int(time.time())}.db"
        
        export_path = Path("exports") / filename
        export_path.parent.mkdir(parents=True, exist_ok=True)
        
        export_data = {
            "name": data[1], "class_id": data[2], "level": data[3], "exp": data[4],
            "gold": data[5], "diamonds": data[6], "kills": data[7], "boss_kills": data[8],
            "hp": data[9], "mp": data[10], "max_hp": data[11], "max_mp": data[12],
            "attack": data[13], "defense": data[14], "magic": data[15], "crit": data[16],
            "agility": data[17], "potions_hp": data[18], "potions_mp": data[19], "pet_id": data[20],
            "inventory": json.loads(data[21]), "equipped": json.loads(data[22]),
            "quests_progress": json.loads(data[23]), "achievements_unlocked": json.loads(data[24]),
            "total_gold_earned": data[25], "last_daily": data[26], "current_location": data[27] if len(data) > 27 else 1
        }
        
        encrypted = UltraSecureCrypto.encrypt(json.dumps(export_data))
        with open(export_path, 'w', encoding='utf-8') as f:
            f.write(encrypted)
        return str(export_path)
    
    def import_hero(self, filepath: str) -> bool:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                encrypted = f.read()
            data = json.loads(UltraSecureCrypto.decrypt(encrypted))
            
            existing_slots = [s["slot"] for s in self.get_all_saves()]
            for slot in range(1, self.max_slots + 1):
                if slot not in existing_slots:
                    conn = sqlite3.connect(str(self.db_path))
                    c = conn.cursor()
                    c.execute('''INSERT INTO heroes 
                        (name, class_id, level, exp, gold, diamonds, kills, boss_kills,
                         hp, mp, max_hp, max_mp, attack, defense, magic, crit, agility,
                         potions_hp, potions_mp, pet_id, inventory, equipped, quests_progress,
                         achievements_unlocked, total_gold_earned, last_daily, current_location, save_slot, save_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)''',
                        (data["name"], data["class_id"], data["level"], data["exp"],
                         data["gold"], data["diamonds"], data["kills"], data["boss_kills"],
                         data["hp"], data["mp"], data["max_hp"], data["max_mp"],
                         data["attack"], data["defense"], data["magic"], data["crit"], data["agility"],
                         data["potions_hp"], data["potions_mp"], data["pet_id"],
                         json.dumps(data["inventory"]), json.dumps(data["equipped"]),
                         json.dumps(data["quests_progress"]), json.dumps(data["achievements_unlocked"]),
                         data["total_gold_earned"], data["last_daily"], data.get("current_location", 1), slot))
                    conn.commit()
                    conn.close()
                    return True
            return False
        except:
            return False

# ==================== ПРОМОКОДЫ ====================
class PromoCodeManager:
    def __init__(self, db: Database):
        self.db = db
    
    def generate_promo(self, diamonds: int, gold: int, item_id: int = 0) -> str:
        code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(45))
        expires = (datetime.now() + timedelta(days=30)).isoformat()
        conn = sqlite3.connect(str(Path("data/game.db")))
        c = conn.cursor()
        c.execute("INSERT INTO promocodes (code, reward_diamonds, reward_gold, reward_item_id, created_by, created, expires) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (code, diamonds, gold, item_id, "admin", datetime.now().isoformat(), expires))
        conn.commit()
        conn.close()
        return code
    
    def use_promo(self, code: str, hero=None) -> Optional[Dict]:
        conn = sqlite3.connect(str(Path("data/game.db")))
        c = conn.cursor()
        c.execute("SELECT reward_diamonds, reward_gold, reward_item_id, used, expires FROM promocodes WHERE code = ?", (code,))
        row = c.fetchone()
        if row and not row[3]:
            expires = datetime.fromisoformat(row[4])
            if expires < datetime.now():
                conn.close()
                return None
            c.execute("UPDATE promocodes SET used = 1 WHERE code = ?", (code,))
            conn.commit()
            conn.close()
            if hero:
                hero.diamonds += row[0]
                hero.gold += row[1]
                if row[2] > 0:
                    hero.add_item(row[2])
            return {"diamonds": row[0], "gold": row[1], "item_id": row[2]}
        conn.close()
        return None

# ==================== ГЕРОЙ ====================
class Hero:
    def __init__(self, name: str, class_id: int, db: Database):
        self.db = db
        self.name = name
        self.class_id = class_id
        self.level = 1
        self.exp = 0
        self.exp_needed = 100
        self.gold = 5000
        self.diamonds = 0
        self.kills = 0
        self.boss_kills = 0
        self.potions_hp = 10
        self.potions_mp = 5
        self.pet_id = 0
        self.inventory = []
        self.equipped = {}
        self.quests_progress = {}
        self.achievements_unlocked = []
        self.total_gold_earned = 0
        self.last_daily = None
        self.current_location = 1
        self.secret_set_active = False
        self._secret_message_shown = False
        
        class_data = CLASSES[class_id - 1]
        self.class_icon = class_data["icon"]
        self.class_name_ru = class_data["name_ru"]
        self.class_name_en = class_data["name_en"]
        
        self.base_hp = class_data["hp"]
        self.base_mp = class_data["mp"]
        self.base_attack = class_data["attack"]
        self.base_defense = class_data["defense"]
        self.base_magic = class_data["magic"]
        self.base_crit = class_data["crit"]
        self.base_agility = class_data["agility"]
        
        self.init_quests()
        self.update_stats()
    
    def get_text(self, key: str) -> str:
        return self.db.get_text(key)
    
    def get_class_name(self) -> str:
        return self.class_name_ru if self.db.lang_manager.current_lang == "ru" else self.class_name_en
    
    def init_quests(self):
        for quest in QUESTS:
            if str(quest["id"]) not in self.quests_progress:
                self.quests_progress[str(quest["id"])] = 0
    
    def check_secret_set(self):
        is_soul_reaper = (self.class_id == 32)
        has_scythe = False
        has_xpp_armor = False
        
        for slot, item_id in self.equipped.items():
            for item in ITEMS:
                if item["id"] == item_id:
                    if item.get("is_scythe"):
                        has_scythe = True
                    if slot == "armor" and item["rank"] == "X++":
                        has_xpp_armor = True
                    break
        
        self.secret_set_active = is_soul_reaper and has_scythe and has_xpp_armor
        
        if self.secret_set_active and not self._secret_message_shown:
            print(f"\n{Colors.GOLD}{'═' * 70}{Colors.RESET}")
            print(f"{Colors.GOLD}{self.get_text('secret_set_warning')}{Colors.RESET}")
            print(f"{Colors.GOLD}{self.get_text('secret_set_desc')}{Colors.RESET}")
            print(f"{Colors.GOLD}{'═' * 70}{Colors.RESET}")
            self._secret_message_shown = True
    
    def update_stats(self):
        self.max_hp = self.base_hp + (self.level - 1) * 25
        self.max_mp = self.base_mp + (self.level - 1) * 12
        self.attack = self.base_attack + (self.level - 1) * 6
        self.defense = self.base_defense + (self.level - 1) * 4
        self.magic = self.base_magic + (self.level - 1) * 5
        self.crit = self.base_crit + (self.level - 1) // 5
        self.agility = self.base_agility + (self.level - 1) * 2
        
        for pet in PETS:
            if pet["id"] == self.pet_id:
                self.attack += pet["attack"]
                self.defense += pet["defense"]
                self.max_hp += pet["hp"]
                self.crit += pet["crit"]
                self.agility += pet.get("agility", 0)
                break
        
        for slot, item_id in self.equipped.items():
            for item in ITEMS:
                if item["id"] == item_id:
                    self.attack += item.get("attack", 0)
                    self.defense += item.get("defense", 0)
                    self.max_hp += item.get("hp", 0)
                    self.max_mp += item.get("mp", 0)
                    self.crit += item.get("crit", 0)
                    self.agility += item.get("agility", 0)
                    self.magic += item.get("magic", 0)
                    break
        
        self.check_secret_set()
        
        if not hasattr(self, 'hp'):
            self.hp = self.max_hp
            self.mp = self.max_mp
        self.hp = min(self.hp, self.max_hp)
        self.mp = min(self.mp, self.max_mp)
    
    def take_damage(self, damage: int) -> int:
        if self.secret_set_active:
            damage = int(damage * 0.05)
            if damage < 1:
                damage = 1
            print(f"{Colors.GOLD}{self.get_text('secret_set_damage_reduce')}{Colors.RESET}")
        return damage
    
    def add_exp(self, amount: int):
        self.exp += amount
        leveled = False
        levels_gained = 0
        while self.exp >= self.exp_needed and levels_gained < 100:
            self.level += 1
            levels_gained += 1
            self.exp -= self.exp_needed
            self.exp_needed = int(self.exp_needed * 1.2)
            leveled = True
        
        if leveled:
            self.update_stats()
            self.hp = self.max_hp
            self.mp = self.max_mp
            if levels_gained == 1:
                print(f"\n{Colors.YELLOW}{'=' * 50}{Colors.RESET}")
                print(f"{Colors.YELLOW}{self.get_text('level_up')} {self.level}!{Colors.RESET}")
                print(f"{Colors.GREEN}+25 HP, +12 MP, +6 ATK, +4 DEF, +5 MAG{Colors.RESET}")
                print(f"{Colors.YELLOW}{'=' * 50}{Colors.RESET}")
            else:
                print(f"\n{Colors.YELLOW}{'=' * 50}{Colors.RESET}")
                print(f"{Colors.YELLOW}{self.get_text('level_up')} +{levels_gained} (NOW {self.level})!{Colors.RESET}")
                print(f"{Colors.GREEN}+{levels_gained * 25} HP, +{levels_gained * 12} MP, +{levels_gained * 6} ATK, +{levels_gained * 4} DEF, +{levels_gained * 5} MAG{Colors.RESET}")
                print(f"{Colors.YELLOW}{'=' * 50}{Colors.RESET}")
            self.check_achievements()
        self.check_quests("exp", amount)
        return leveled
    
    def add_gold(self, amount: int):
        self.gold += amount
        self.total_gold_earned += amount
        self.check_quests("gold", amount)
    
    def add_kill(self, is_boss: bool = False):
        self.kills += 1
        if is_boss:
            self.boss_kills += 1
            self.check_quests("boss_kill", 1)
        self.check_quests("kill", 1)
        self.check_achievements()
    
    def check_quests(self, quest_type: str, amount: int):
        for quest in QUESTS:
            if quest["type"] == quest_type:
                qid = str(quest["id"])
                if qid in self.quests_progress and self.quests_progress[qid] >= 0:
                    self.quests_progress[qid] += amount
                    if self.quests_progress[qid] >= quest["target"]:
                        self.add_exp(quest["reward_exp"])
                        self.add_gold(quest["reward_gold"])
                        self.diamonds += quest["reward_diamonds"]
                        name = quest["name_" + self.db.lang_manager.current_lang]
                        print(f"\n{Colors.GREEN}✨ {self.get_text('quest_complete')} {name}! ✨{Colors.RESET}")
                        self.quests_progress[qid] = -1
    
    def check_achievements(self):
        for ach in ACHIEVEMENTS:
            if ach["id"] in self.achievements_unlocked:
                continue
            achieved = False
            if ach["type"] == "kills" and self.kills >= ach["target"]:
                achieved = True
            elif ach["type"] == "boss_kills" and self.boss_kills >= ach["target"]:
                achieved = True
            elif ach["type"] == "gold" and self.total_gold_earned >= ach["target"]:
                achieved = True
            elif ach["type"] == "level" and self.level >= ach["target"]:
                achieved = True
            
            if achieved:
                self.achievements_unlocked.append(ach["id"])
                self.add_gold(ach["reward_gold"])
                self.diamonds += ach["reward_diamonds"]
                name = ach["name_" + self.db.lang_manager.current_lang]
                print(f"\n{Colors.YELLOW}🏆 {self.get_text('achievement_unlocked')} {name}! 🏆{Colors.RESET}")
    
    def daily_reward(self) -> Dict:
        today = datetime.now().date()
        if self.last_daily:
            last = datetime.fromisoformat(self.last_daily).date()
            if last == today:
                return {"claimed": False, "message": self.get_text("daily_already")}
        
        reward_gold = 1000 + self.level * 100
        self.add_gold(reward_gold)
        self.last_daily = datetime.now().isoformat()
        return {"claimed": True, "gold": reward_gold, "diamonds": 0}
    
    def show_stats(self):
        hp_bar = show_health_bar(self.hp, self.max_hp, 35)
        mp_bar = show_health_bar(self.mp, self.max_mp, 35)
        exp_bar = show_health_bar(self.exp, self.exp_needed, 35)
        class_name = self.get_class_name()
        pet_name = self.db.get_pet_name(self.pet_id)
        
        print(f"\n{Colors.CYAN}{'─' * 65}{Colors.RESET}")
        print(f"{Colors.YELLOW}{self.class_icon} {class_name} {self.name} | {self.get_text('level')} {self.level}{Colors.RESET}")
        if self.secret_set_active:
            print(f"{Colors.GOLD}🔥 {self.get_text('secret_set_warning')} 🔥{Colors.RESET}")
        print(f"{Colors.RED}{self.get_text('hp')}: {hp_bar}{Colors.RESET}")
        print(f"{Colors.BLUE}{self.get_text('mp')}: {mp_bar}{Colors.RESET}")
        print(f"{Colors.GREEN}{self.get_text('exp')}: {exp_bar}{Colors.RESET}")
        print(f"{Colors.CYAN}{'─' * 65}{Colors.RESET}")
        print(f"{Colors.YELLOW}⚔️{self.attack}  {Colors.CYAN}🛡️{self.defense}  {Colors.MAGENTA}🔮{self.magic}  {Colors.RED}💥{self.crit}%  {Colors.GREEN}🏃{self.agility}{Colors.RESET}")
        print(f"{Colors.GREEN}💰 {self.gold} | 💎 {self.diamonds} | 🏆 {self.kills} {self.get_text('kills')} | 👑 {self.boss_kills} {self.get_text('boss_kills')}{Colors.RESET}")
        print(f"{Colors.MAGENTA}💊 HP: {self.potions_hp} | 🧪 MP: {self.potions_mp} | 🐾 {pet_name}{Colors.RESET}")
        print(f"{Colors.CYAN}{'─' * 65}{Colors.RESET}")
    
    def use_hp_potion(self) -> bool:
        if self.potions_hp > 0 and self.hp < self.max_hp:
            heal = min(250, self.max_hp - self.hp)
            self.hp += heal
            self.potions_hp -= 1
            print(f"{Colors.GREEN}💚 +{heal} {self.get_text('hp_restore')}! {self.get_text('potion_hp')}: {self.potions_hp}{Colors.RESET}")
            return True
        print(f"{Colors.RED}❌ {self.get_text('no_hp_potions')}{Colors.RESET}")
        return False
    
    def use_mp_potion(self) -> bool:
        if self.potions_mp > 0 and self.mp < self.max_mp:
            restore = min(150, self.max_mp - self.mp)
            self.mp += restore
            self.potions_mp -= 1
            print(f"{Colors.BLUE}💙 +{restore} {self.get_text('mp_restore')}! {self.get_text('potion_mp')}: {self.potions_mp}{Colors.RESET}")
            return True
        print(f"{Colors.RED}❌ {self.get_text('no_mp_potions')}{Colors.RESET}")
        return False
    
    def rest(self):
        self.hp = min(self.max_hp, self.hp + int(self.max_hp * 0.5))
        self.mp = min(self.max_mp, self.mp + int(self.max_mp * 0.5))
        print(f"{Colors.GREEN}💤 {self.get_text('rest')}! +50% HP/MP{Colors.RESET}")
    
    def is_alive(self) -> bool:
        return self.hp > 0
    
    def add_item(self, item_id: int):
        if len(self.inventory) < 100:
            self.inventory.append(item_id)
            self.check_quests("items", 1)
            print(f"{Colors.GREEN}🎁 {self.get_text('item_received')} {self.get_item_name(item_id)}{Colors.RESET}")
        else:
            print(f"{Colors.RED}❌ {self.get_text('inventory_full')}{Colors.RESET}")
    
    def get_item_name(self, item_id: int) -> str:
        for item in ITEMS:
            if item["id"] == item_id:
                return item["name_" + self.db.lang_manager.current_lang]
        return "Unknown"
    
    def get_item_data(self, item_id: int) -> Optional[Dict]:
        for item in ITEMS:
            if item["id"] == item_id:
                return item
        return None
    
    def equip_item(self, item_id: int) -> bool:
        item = self.get_item_data(item_id)
        if item and item_id in self.inventory:
            slot = item["slot"]
            if slot in self.equipped:
                self.inventory.append(self.equipped[slot])
            self.equipped[slot] = item_id
            self.inventory.remove(item_id)
            self.update_stats()
            print(f"{Colors.GREEN}✅ {self.get_text('equipped')} {self.get_item_name(item_id)}{Colors.RESET}")
            return True
        return False
    
    def sell_item(self, item_id: int) -> bool:
        item = self.get_item_data(item_id)
        if item and item_id in self.inventory:
            self.inventory.remove(item_id)
            self.add_gold(item["sell_price"])
            print(f"{Colors.GREEN}💰 {self.get_text('sold')} {item['sell_price']} {self.get_text('gold')}!{Colors.RESET}")
            return True
        return False

# ==================== СИСТЕМА АТАКИ ====================
class AttackSystem:
    @staticmethod
    def generate_code() -> str:
        return ''.join(str(random.randint(0, 9)) for _ in range(6))
    
    @staticmethod
    def execute(hero: Hero, base_damage: int) -> int:
        code = AttackSystem.generate_code()
        
        print(f"\n{Colors.YELLOW}{'═' * 50}{Colors.RESET}")
        print(f"{Colors.YELLOW}⚡ {hero.get_text('code_prompt')} ⚡{Colors.RESET}")
        print(f"{Colors.CYAN}{hero.get_text('code_label')}: {Colors.GREEN}{code}{Colors.RESET}")
        print(f"{Colors.CYAN}{hero.get_text('time_label')}: {ATTACK_TIME_LIMIT} {hero.get_text('seconds')}{Colors.RESET}")
        print(f"{Colors.YELLOW}{'═' * 50}{Colors.RESET}")
        
        start = time.time()
        user_input = input(f"{Colors.CYAN}> {Colors.RESET}").strip()
        elapsed = time.time() - start
        
        if user_input != code or elapsed > ATTACK_TIME_LIMIT:
            print(f"{Colors.RED}❌ {hero.get_text('wrong_code')}{Colors.RESET}")
            return 0
        
        multiplier = max(0.2, (ATTACK_TIME_LIMIT - elapsed) / ATTACK_TIME_LIMIT)
        damage = int(base_damage * (1.2 + multiplier * 1.3)) + hero.agility // 3
        
        if hero.secret_set_active:
            damage = int(damage * 5)
            print(f"{Colors.GOLD}{hero.get_text('secret_set_damage_boost')}{Colors.RESET}")
        
        if random.random() < hero.crit / 100:
            damage = int(damage * 1.8)
            print(f"{Colors.MAGENTA}💥 {hero.get_text('critical')} 💥{Colors.RESET}")
        
        if elapsed < 2:
            print(f"{Colors.GREEN}{hero.get_text('perfect')} ", end="")
        elif elapsed < 4:
            print(f"{Colors.GREEN}{hero.get_text('excellent')} ", end="")
        elif elapsed < 7:
            print(f"{Colors.GREEN}{hero.get_text('good')} ", end="")
        elif elapsed < 10:
            print(f"{Colors.YELLOW}{hero.get_text('normal')} ", end="")
        else:
            print(f"{Colors.RED}{hero.get_text('slow')} ", end="")
        
        print(f"{damage} {hero.get_text('damage')} ({elapsed:.1f} {hero.get_text('seconds')}){Colors.RESET}")
        return damage

# ==================== БОЕВАЯ СИСТЕМА ====================
class BattleSystem:
    @staticmethod
    def fight(hero: Hero, monster: Dict, is_boss: bool = False):
        clear()
        monster_hp = monster["hp"]
        monster_max_hp = monster["max_hp"]
        monster_name = monster["name"]
        monster_tier = monster["tier"]
        
        title = f"⚔️ {hero.get_text('battle')}: {monster_name} ⚔️"
        if is_boss:
            title = f"👑 {hero.get_text('boss')}: {monster_name} 👑"
        show_border(title, Colors.RED if is_boss else Colors.MAGENTA, 70)
        print(f"{monster['tier_color']}{hero.get_text('level')}: {monster['level']} | {hero.get_text('info')}: {monster_tier}{Colors.RESET}")
        
        while hero.is_alive() and monster_hp > 0:
            clear()
            hero.show_stats()
            
            monster_bar = show_health_bar(monster_hp, monster_max_hp, 35)
            print(f"\n{monster['icon']} {monster['tier_color']}{monster_name}{Colors.RESET}")
            print(f"{Colors.RED}{monster_bar}{Colors.RESET}")
            
            print(f"\n{Colors.CYAN}{'─' * 50}{Colors.RESET}")
            print(f"{Colors.GREEN}[1] ⚔️ {hero.get_text('attack')}{Colors.RESET}")
            print(f"[2] 💊 {hero.get_text('potion_hp')} ({hero.potions_hp})")
            print(f"[3] 💙 {hero.get_text('potion_mp')} ({hero.potions_mp})")
            print(f"[4] 🛡️ {hero.get_text('defense')}")
            print(f"[5] 🏃 {hero.get_text('flee')}")
            print(f"{Colors.CYAN}{'─' * 50}{Colors.RESET}")
            
            choice = input(f"\n{Colors.YELLOW}> {Colors.RESET}")
            defense_bonus = False
            
            if choice == "1":
                base_damage = hero.attack + random.randint(-15, 25) - monster["defense"] // 3
                base_damage = max(10, base_damage)
                damage = AttackSystem.execute(hero, base_damage)
                if damage > 0:
                    monster_hp -= damage
                    print(f"{Colors.GREEN}⚔️ {hero.get_text('damage')}: {damage}{Colors.RESET}")
            elif choice == "2":
                hero.use_hp_potion()
                pause(hero.db.lang_manager)
                continue
            elif choice == "3":
                hero.use_mp_potion()
                pause(hero.db.lang_manager)
                continue
            elif choice == "4":
                print(f"{Colors.BLUE}🛡️ {hero.get_text('defense_activated')}{Colors.RESET}")
                defense_bonus = True
            elif choice == "5":
                if random.random() < 0.4:
                    print(f"{Colors.GREEN}🏃 {hero.get_text('flee_success')}{Colors.RESET}")
                    pause(hero.db.lang_manager)
                    return False
                else:
                    print(f"{Colors.RED}❌ {hero.get_text('flee_failed')}{Colors.RESET}")
            
            if monster_hp <= 0:
                break
            
            print(f"\n{Colors.RED}💀 {hero.get_text('enemy_turn')} 💀{Colors.RESET}")
            monster_damage = monster["attack"] + random.randint(-15, 35) - hero.defense // 3
            monster_damage = max(1, monster_damage)
            
            tier_mult = 1.0
            if "Элитный" in monster["tier"] or "Elite" in monster["tier"]:
                tier_mult = 1.3
            elif "Легендарный" in monster["tier"] or "Legendary" in monster["tier"]:
                tier_mult = 1.8
            elif "Мифический" in monster["tier"] or "Mythic" in monster["tier"]:
                tier_mult = 2.5
            elif "Божественный" in monster["tier"] or "Divine" in monster["tier"]:
                tier_mult = 4.0
            elif "Космический" in monster["tier"] or "Cosmic" in monster["tier"]:
                tier_mult = 6.0
            elif "Хаоса" in monster["tier"] or "Chaos" in monster["tier"]:
                tier_mult = 10.0
            
            monster_damage = int(monster_damage * tier_mult)
            
            if defense_bonus:
                monster_damage = monster_damage // 2
            
            monster_damage = hero.take_damage(monster_damage)
            
            if random.random() < 0.15:
                monster_damage = int(monster_damage * 1.5)
                print(f"{Colors.RED}💥 {hero.get_text('enemy_critical')} 💥{Colors.RESET}")
            
            hero.hp -= monster_damage
            print(f"{Colors.RED}💀 {monster_name} {hero.get_text('enemy_attacks')} -{monster_damage} HP!{Colors.RESET}")
            time.sleep(0.8)
        
        if hero.is_alive():
            hero.add_gold(monster["gold_reward"])
            hero.add_exp(monster["exp_reward"])
            hero.add_kill(is_boss)
            
            print(f"\n{Colors.GREEN}{'🎉' * 35}{Colors.RESET}")
            print(f"{Colors.GREEN}{hero.get_text('victory'):^70}{Colors.RESET}")
            print(f"{Colors.GREEN}+{monster['exp_reward']} EXP, +{monster['gold_reward']} {hero.get_text('gold')}{Colors.RESET}")
            
            if random.random() < 0.3:
                rarity = random.choices(RARITIES, weights=[r["chance"] for r in RARITIES])[0]
                possible_items = [item for item in ITEMS if item["level_req"] <= hero.level and item["rank"] == rarity["name"]]
                if possible_items:
                    item = random.choice(possible_items)
                    hero.add_item(item["id"])
                    print(f"{Colors.MAGENTA}🎁 {hero.get_text('item_dropped')} {rarity['name']} {item['slot']}!{Colors.RESET}")
            
            print(f"{Colors.GREEN}{'🎉' * 35}{Colors.RESET}")
            pause(hero.db.lang_manager)
            return True
        else:
            print(f"\n{Colors.RED}{'💀' * 35}{Colors.RESET}")
            print(f"{Colors.RED}{hero.get_text('defeat'):^70}{Colors.RESET}")
            print(f"{Colors.RED}{'-30% ' + hero.get_text('gold'):^70}{Colors.RESET}")
            hero.gold = int(hero.gold * 0.7)
            hero.hp = hero.max_hp // 2
            hero.mp = hero.max_mp // 2
            print(f"{Colors.RED}{'💀' * 35}{Colors.RESET}")
            pause(hero.db.lang_manager)
            return False

# ==================== МАГАЗИН ====================
class ShopManager:
    def __init__(self):
        self.current_items = []
        self.last_refresh = time.time()
        self.refresh_shop()
    
    def refresh_shop(self):
        self.current_items = random.sample(ITEMS, min(10, len(ITEMS)))
        self.last_refresh = time.time()
    
    def show_shop(self, hero: Hero, db: Database):
        lang = db.lang_manager
        if time.time() - self.last_refresh > SHOP_REFRESH_TIME:
            self.refresh_shop()
            print(f"{Colors.GREEN}🔄 {lang.get('shop_refreshed')}{Colors.RESET}")
            time.sleep(1)
        
        while True:
            clear()
            show_border(lang.get("shop"), Colors.YELLOW, 70)
            print(f"{Colors.CYAN}💰 {hero.gold} {lang.get('gold')} | 💎 {hero.diamonds} {lang.get('diamonds')}{Colors.RESET}\n")
            
            print(f"{Colors.GREEN}[1] 💊 {lang.get('potion_hp')} (50💰) - 250 HP{Colors.RESET}")
            print(f"[2] 💙 {lang.get('potion_mp')} (40💰) - 150 MP")
            print(f"[3] 📦 {lang.get('set_purchased')} (400💰) - 5 HP + 5 MP")
            print(f"\n{Colors.MAGENTA}--- {lang.get('shop')} ---{Colors.RESET}")
            
            for i, item in enumerate(self.current_items[:10], 4):
                item_name = hero.get_item_name(item["id"])
                color = Colors.RARITY.get(item["rank"], Colors.WHITE)
                print(f"[{i}] {color}{item_name}{Colors.RESET} - {item['price']}💰")
            
            print(f"\n{Colors.CYAN}[S] {lang.get('sell')}{Colors.RESET}")
            print(f"[B] 💎 {lang.get('buy_slot')} ({EXTRA_SLOT_COST}💎)")
            print(f"{Colors.RED}[0] {lang.get('back')}{Colors.RESET}")
            
            choice = input(f"\n{Colors.YELLOW}> {Colors.RESET}").strip().upper()
            
            if choice == "1" and hero.gold >= 50:
                hero.gold -= 50
                hero.potions_hp += 1
                print(f"{Colors.GREEN}✅ {lang.get('purchased')}{Colors.RESET}")
            elif choice == "2" and hero.gold >= 40:
                hero.gold -= 40
                hero.potions_mp += 1
                print(f"{Colors.GREEN}✅ {lang.get('purchased')}{Colors.RESET}")
            elif choice == "3" and hero.gold >= 400:
                hero.gold -= 400
                hero.potions_hp += 5
                hero.potions_mp += 5
                print(f"{Colors.GREEN}✅ {lang.get('set_purchased')}{Colors.RESET}")
            elif choice.isdigit() and 4 <= int(choice) < 4 + len(self.current_items):
                idx = int(choice) - 4
                if idx < len(self.current_items):
                    item = self.current_items[idx]
                    if hero.gold >= item["price"]:
                        hero.gold -= item["price"]
                        hero.add_item(item["id"])
                        print(f"{Colors.GREEN}✅ {lang.get('purchased')}{Colors.RESET}")
                    else:
                        print(f"{Colors.RED}❌ {lang.get('not_enough_gold')}{Colors.RESET}")
            elif choice == "S":
                ShopManager.sell_items(hero, db)
            elif choice == "B":
                if hero.diamonds >= EXTRA_SLOT_COST and db.max_slots < MAX_TOTAL_SLOTS:
                    hero.diamonds -= EXTRA_SLOT_COST
                    db.set_max_slots(db.max_slots + 1)
                    print(f"{Colors.GREEN}✅ {lang.get('slot_bought')} {db.max_slots}{Colors.RESET}")
                else:
                    print(f"{Colors.RED}❌ {lang.get('no_diamonds')} {lang.get('max_slots')}!{Colors.RESET}")
            elif choice == "0":
                break
            else:
                print(f"{Colors.RED}❌ {lang.get('invalid_choice')}{Colors.RESET}")
            
            hero.db.save_hero(hero)
            pause(lang)
    
    @staticmethod
    def sell_items(hero: Hero, db: Database):
        lang = db.lang_manager
        while True:
            clear()
            show_border(lang.get("sell"), Colors.CYAN, 70)
            print(f"{Colors.CYAN}💰 {hero.gold} {lang.get('gold')}{Colors.RESET}\n")
            
            if not hero.inventory:
                print(f"{Colors.YELLOW}{lang.get('no_items')}{Colors.RESET}")
                pause(lang)
                return
            
            print(f"{Colors.MAGENTA}{'─' * 50}{Colors.RESET}")
            items_list = []
            for i, item_id in enumerate(hero.inventory, 1):
                item = hero.get_item_data(item_id)
                if item:
                    item_name = hero.get_item_name(item_id)
                    color = Colors.RARITY.get(item["rank"], Colors.WHITE)
                    items_list.append((i, item_id, item_name, item["sell_price"], color))
                    print(f"[{i}] {color}{item_name}{Colors.RESET} - {item['sell_price']}💰")
            print(f"{Colors.MAGENTA}{'─' * 50}{Colors.RESET}")
            print(f"[0] {lang.get('back')}")
            
            choice = input(f"\n{Colors.YELLOW}> {Colors.RESET}")
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(items_list):
                    hero.sell_item(items_list[idx][1])
                elif choice == "0":
                    break
            pause(lang)

# ==================== ДОНАТ ====================
class DonateManager:
    @staticmethod
    def show_donate(hero: Hero, db: Database, promo_manager):
        lang = db.lang_manager
        while True:
            clear()
            show_border(lang.get("donate"), Colors.CYAN, 70)
            print(f"{Colors.CYAN}💎 {hero.diamonds} {lang.get('diamonds')} | 💰 {hero.gold} {lang.get('gold')}{Colors.RESET}\n")
            
            print(f"{Colors.GOLD}══════════════════════════════════════════════════{Colors.RESET}")
            print(f"{Colors.GOLD}{lang.get('price_list').upper()}{Colors.RESET}")
            print(f"{Colors.GOLD}══════════════════════════════════════════════════{Colors.RESET}")
            
            price_list = [{"diamonds": 100, "price_usd": 0.99}, {"diamonds": 500, "price_usd": 3.99},
                         {"diamonds": 1000, "price_usd": 6.99}, {"diamonds": 5000, "price_usd": 29.99},
                         {"diamonds": 10000, "price_usd": 49.99}]
            
            for i, price in enumerate(price_list, 1):
                print(f"{Colors.CYAN}[{i}] {price['diamonds']}💎 = ${price['price_usd']}{Colors.RESET}")
            
            print(f"\n{Colors.MAGENTA}--- {lang.get('pets')} ---{Colors.RESET}")
            for i, pet in enumerate(PETS, len(price_list) + 1):
                pet_name = db.get_pet_name(pet["id"])
                status = "✅" if hero.pet_id == pet["id"] else "  "
                print(f"[{i}] {status} {pet['icon']} {pet_name} - {pet['price_diamonds']}💎")
                print(f"    +{pet['attack']} ATK, +{pet['defense']} DEF, +{pet['hp']} HP, +{pet['crit']}% CRIT")
            
            print(f"\n{Colors.YELLOW}[P] {lang.get('donate')} ({lang.get('promo')}){Colors.RESET}")
            print(f"{Colors.RED}[0] {lang.get('back')}{Colors.RESET}")
            
            choice = input(f"\n{Colors.YELLOW}> {Colors.RESET}").strip().upper()
            
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(price_list):
                    price_info = price_list[idx]
                    print(f"\n{Colors.CYAN}{lang.get('buy_diamonds')}:{Colors.RESET}")
                    print(f"{Colors.YELLOW}  Telegram: {SUPPORT_TG}{Colors.RESET}")
                    print(f"{Colors.YELLOW}  Discord: {SUPPORT_DS}{Colors.RESET}")
                    print(f"{Colors.YELLOW}  Email: {SUPPORT_EMAIL}{Colors.RESET}")
                    pause(lang)
                elif len(price_list) <= idx < len(price_list) + len(PETS):
                    pet_idx = idx - len(price_list)
                    if 0 <= pet_idx < len(PETS):
                        pet = PETS[pet_idx]
                        if hero.diamonds >= pet["price_diamonds"]:
                            hero.diamonds -= pet["price_diamonds"]
                            hero.pet_id = pet["id"]
                            hero.update_stats()
                            print(f"{Colors.GREEN}✅ {lang.get('purchased')} {db.get_pet_name(pet['id'])}!{Colors.RESET}")
                        else:
                            print(f"{Colors.RED}❌ {lang.get('no_diamonds')}!{Colors.RESET}")
            elif choice == "P":
                code = input(f"{Colors.CYAN}{lang.get('enter_promo')}: {Colors.RESET}").strip()
                reward = promo_manager.use_promo(code, hero)
                if reward:
                    print(f"{Colors.GREEN}✅ {lang.get('promo_activated')} +{reward['diamonds']}💎 +{reward['gold']}💰{Colors.RESET}")
                else:
                    print(f"{Colors.RED}❌ {lang.get('promo_invalid')}{Colors.RESET}")
                hero.db.save_hero(hero)
                time.sleep(2)
            elif choice == "0":
                break
            else:
                print(f"{Colors.RED}❌ {lang.get('invalid_choice')}{Colors.RESET}")
            
            hero.db.save_hero(hero)
            pause(lang)

# ==================== ОСНОВНАЯ ИГРА ====================
class DarkOfHemi:
    def __init__(self):
        self.lang_manager = LanguageManager()
        self.select_language()
        self.db = Database(self.lang_manager)
        self.promo_manager = PromoCodeManager(self.db)
        self.shop_manager = ShopManager()
        self.world_map = WorldMap(self.lang_manager)
        self.hero = None
        self.running = True
    
    def select_language(self):
        clear()
        print(f"{Colors.GOLD}{'═' * 50}{Colors.RESET}")
        print(f"{Colors.GOLD}{self.lang_manager.get('select_language').center(50)}{Colors.RESET}")
        print(f"{Colors.GOLD}{'═' * 50}{Colors.RESET}")
        print(f"\n{Colors.CYAN}[1] {self.lang_manager.get('russian')}{Colors.RESET}")
        print(f"[2] {self.lang_manager.get('english')}")
        print(f"{Colors.GOLD}{'═' * 50}{Colors.RESET}")
        
        while True:
            choice = input(f"\n{Colors.YELLOW}> {Colors.RESET}")
            if choice == "1":
                self.lang_manager.set_language("ru")
                break
            elif choice == "2":
                self.lang_manager.set_language("en")
                break
            else:
                print(f"{Colors.RED}❌ {self.lang_manager.get('invalid_language')}{Colors.RESET}")
    
    def loading_screen(self):
        clear()
        print(f"{Colors.RED}{'═' * 80}{Colors.RESET}")
        print(f"{Colors.GOLD}{'DARK OF HEMI v' + VERSION + ' - ' + self.lang_manager.get('loading').center(80)}{Colors.RESET}")
        print(f"{Colors.RED}{'═' * 80}{Colors.RESET}\n")
        
        steps = [
            self.lang_manager.get("loading_encryption"), self.lang_manager.get("loading_db"),
            self.lang_manager.get("loading_classes"), self.lang_manager.get("loading_monsters"),
            self.lang_manager.get("loading_bosses"), self.lang_manager.get("loading_items"),
            self.lang_manager.get("loading_pets"), self.lang_manager.get("loading_promos"),
            self.lang_manager.get("loading_quests"), self.lang_manager.get("loading_achievements"),
            self.lang_manager.get("loading_world"), self.lang_manager.get("loading_data"),
            self.lang_manager.get("loading_saves")
        ]
        
        for step in steps:
            loading_animation(step)
        
        print(f"\n{Colors.GREEN}{'═' * 80}{Colors.RESET}")
        print(f"{Colors.GREEN}{self.lang_manager.get('loading_complete').center(80)}{Colors.RESET}")
        print(f"{Colors.GREEN}{'═' * 80}{Colors.RESET}")
        time.sleep(1.5)
    
    def show_title(self):
        clear()
        print(f"{Colors.RED}{'═' * 80}{Colors.RESET}")
        print(f"{Colors.GOLD}{f'DARK OF HEMI v{VERSION}'.center(80)}{Colors.RESET}")
        print(f"{Colors.CYAN}{'35 CLASSES | MEGA MONSTERS | 30-LAYER ENCRYPTION'.center(80)}{Colors.RESET}")
        print(f"{Colors.MAGENTA}{f'DEVELOPER: {DEVELOPER_NAME}'.center(80)}{Colors.RESET}")
        print(f"{Colors.CYAN}{f'SUPPORT: {SUPPORT_TG} | {SUPPORT_DS}'.center(80)}{Colors.RESET}")
        print(f"{Colors.RED}{'═' * 80}{Colors.RESET}")
        print()
    
    def show_save_slots_menu(self):
        while True:
            clear()
            show_border(self.lang_manager.get("select_slot"), Colors.CYAN, 70)
            
            saves = self.db.get_all_saves()
            available_slots = set(range(1, self.db.max_slots + 1))
            used_slots = {s["slot"] for s in saves}
            free_slots = available_slots - used_slots
            
            print(f"\n{Colors.GREEN}{self.lang_manager.get('available_slots')}: {len(free_slots)}/{self.db.max_slots}{Colors.RESET}")
            print(f"{Colors.DIM}{self.lang_manager.get('buy_slot')}: {EXTRA_SLOT_COST}💎{Colors.RESET}\n")
            
            print(f"{Colors.YELLOW}--- {self.lang_manager.get('saves')} ---{Colors.RESET}")
            for save in saves:
                print(f"{Colors.CYAN}[{save['slot']}] {save['name']} | {self.lang_manager.get('level')} {save['level']} | {save['time'][:16]}{Colors.RESET}")
            
            if free_slots:
                print(f"\n{Colors.GREEN}--- {self.lang_manager.get('empty_slots')} ---{Colors.RESET}")
                for slot in sorted(free_slots):
                    print(f"{Colors.GREEN}[{slot}] {self.lang_manager.get('empty')}{Colors.RESET}")
            
            print(f"\n{Colors.CYAN}[E] {self.lang_manager.get('export')}{Colors.RESET}")
            print(f"[I] {self.lang_manager.get('import')}{Colors.RESET}")
            print(f"[D] {self.lang_manager.get('delete')}{Colors.RESET}")
            print(f"{Colors.RED}[0] {self.lang_manager.get('back')}{Colors.RESET}")
            
            choice = input(f"\n{Colors.YELLOW}> {Colors.RESET}").strip().upper()
            
            if choice == "0":
                return None
            elif choice == "E":
                self.export_character()
            elif choice == "I":
                self.import_character()
            elif choice == "D":
                self.delete_save()
            elif choice.isdigit():
                slot = int(choice)
                if 1 <= slot <= self.db.max_slots:
                    return slot
                else:
                    print(f"{Colors.RED}❌ {self.lang_manager.get('invalid_slot')}{Colors.RESET}")
                    pause(self.lang_manager)
            else:
                print(f"{Colors.RED}❌ {self.lang_manager.get('invalid_choice')}{Colors.RESET}")
                pause(self.lang_manager)
    
    def export_character(self):
        saves = self.db.get_all_saves()
        if not saves:
            print(f"{Colors.RED}❌ {self.lang_manager.get('no_saves')}!{Colors.RESET}")
            pause(self.lang_manager)
            return
        
        print(f"\n{Colors.CYAN}{self.lang_manager.get('select_export_slot')}{Colors.RESET}")
        for save in saves:
            print(f"[{save['slot']}] {save['name']} | {self.lang_manager.get('level')} {save['level']}")
        
        slot = input(f"\n{Colors.YELLOW}> {Colors.RESET}")
        if slot.isdigit():
            slot = int(slot)
            filename = self.db.export_hero(slot)
            if filename:
                print(f"{Colors.GREEN}✅ {self.lang_manager.get('export_success')} {filename}{Colors.RESET}")
            else:
                print(f"{Colors.RED}❌ {self.lang_manager.get('error')}!{Colors.RESET}")
        pause(self.lang_manager)
    
    def import_character(self):
        print(f"{Colors.CYAN}{self.lang_manager.get('import')}:{Colors.RESET}")
        filepath = input(f"{Colors.YELLOW}> {Colors.RESET}").strip()
        if self.db.import_hero(filepath):
            print(f"{Colors.GREEN}✅ {self.lang_manager.get('import_success')}!{Colors.RESET}")
        else:
            print(f"{Colors.RED}❌ {self.lang_manager.get('error')}!{Colors.RESET}")
        pause(self.lang_manager)
    
    def delete_save(self):
        saves = self.db.get_all_saves()
        if not saves:
            print(f"{Colors.RED}❌ {self.lang_manager.get('no_saves')}!{Colors.RESET}")
            pause(self.lang_manager)
            return
        
        print(f"\n{Colors.CYAN}{self.lang_manager.get('select_delete_slot')}{Colors.RESET}")
        for save in saves:
            print(f"[{save['slot']}] {save['name']} | {self.lang_manager.get('level')} {save['level']}")
        
        slot = input(f"\n{Colors.YELLOW}> {Colors.RESET}")
        if slot.isdigit():
            slot = int(slot)
            confirm = input(f"{Colors.RED}{self.lang_manager.get('delete_confirm')} (y/n): {Colors.RESET}")
            if confirm.lower() == 'y':
                self.db.delete_hero(slot)
                print(f"{Colors.GREEN}✅ {self.lang_manager.get('delete_success')}!{Colors.RESET}")
        pause(self.lang_manager)
    
    def main_menu(self):
        while True:
            self.show_title()
            print(f"{Colors.GREEN}[1] {self.lang_manager.get('new_game')}{Colors.RESET}")
            print(f"[2] {self.lang_manager.get('load_game')}")
            print(f"[3] {self.lang_manager.get('settings')}")
            print(f"[4] {self.lang_manager.get('news')}")
            print(f"[5] {self.lang_manager.get('about')}")
            print(f"[M] 🗺️ {self.lang_manager.get('map')}")
            print(f"{Colors.RED}[0] {self.lang_manager.get('exit')}{Colors.RESET}")
            
            choice = input(f"\n{Colors.YELLOW}> {Colors.RESET}").strip().upper()
            
            if choice == "1":
                slot = self.show_save_slots_menu()
                if slot:
                    self.new_game(slot)
                    break
            elif choice == "2":
                slot = self.show_save_slots_menu()
                if slot:
                    if self.load_game(slot):
                        self.game_loop()
                        break
            elif choice == "3":
                self.settings_menu()
            elif choice == "4":
                NewsManager.show_news(self.lang_manager)
            elif choice == "5":
                self.show_about()
            elif choice == "M":
                self.world_map.show_map()
                pause(self.lang_manager)
            elif choice == "0":
                print(f"{Colors.GREEN}Thanks for playing! The Fallen Angel awaits you again!{Colors.RESET}")
                sys.exit(0)
    
    def settings_menu(self):
        while True:
            clear()
            show_border(self.lang_manager.get("settings"), Colors.YELLOW, 70)
            current_lang = "Русский" if self.lang_manager.current_lang == "ru" else "English"
            print(f"\n{Colors.CYAN}[1] {self.lang_manager.get('language')}: {Colors.GREEN}{current_lang}{Colors.RESET}")
            print(f"[2] {self.lang_manager.get('donate')} ({self.lang_manager.get('promo')})")
            print(f"[3] 🔧 {self.lang_manager.get('admin_panel')}")
            print(f"{Colors.RED}[0] {self.lang_manager.get('back')}{Colors.RESET}")
            
            choice = input(f"\n{Colors.YELLOW}> {Colors.RESET}")
            
            if choice == "1":
                new_lang = "en" if self.lang_manager.current_lang == "ru" else "ru"
                self.lang_manager.set_language(new_lang)
                self.world_map.lang_manager = self.lang_manager
                print(f"{Colors.GREEN}✅ {self.lang_manager.get('language_changed')}{Colors.RESET}")
                time.sleep(1)
            elif choice == "2":
                if self.hero:
                    code = input(f"{Colors.CYAN}{self.lang_manager.get('enter_promo')}: {Colors.RESET}").strip()
                    reward = self.promo_manager.use_promo(code, self.hero)
                    if reward:
                        print(f"{Colors.GREEN}✅ {self.lang_manager.get('promo_activated')} +{reward['diamonds']}💎 +{reward['gold']}💰{Colors.RESET}")
                    else:
                        print(f"{Colors.RED}❌ {self.lang_manager.get('promo_invalid')}{Colors.RESET}")
                else:
                    print(f"{Colors.YELLOW}{self.lang_manager.get('load_first')}{Colors.RESET}")
                time.sleep(2)
            elif choice == "3":
                self.admin_panel()
            elif choice == "0":
                break
    
    def admin_panel(self):
        pwd = input(f"{Colors.RED}{self.lang_manager.get('admin_password')}: {Colors.RESET}")
        if pwd != ADMIN_PASSWORD:
            print(f"{Colors.RED}❌ {self.lang_manager.get('admin_invalid')}{Colors.RESET}")
            time.sleep(1.5)
            return
        
        while True:
            clear()
            show_border(self.lang_manager.get("admin_panel"), Colors.RED, 70)
            print(f"{Colors.CYAN}[1] {self.lang_manager.get('create_promo')}{Colors.RESET}")
            print(f"[2] {self.lang_manager.get('give_resources')}")
            print(f"[3] {self.lang_manager.get('give_scythe')}")
            print(f"[4] {self.lang_manager.get('give_armor')}")
            print(f"{Colors.RED}[0] {self.lang_manager.get('exit_admin')}{Colors.RESET}")
            
            choice = input(f"\n{Colors.YELLOW}> {Colors.RESET}")
            
            if choice == "1":
                diamonds = int(input(f"{self.lang_manager.get('diamonds')}: ") or 0)
                gold = int(input(f"{self.lang_manager.get('gold')}: ") or 0)
                code = self.promo_manager.generate_promo(diamonds, gold)
                print(f"{Colors.GREEN}✅ {self.lang_manager.get('promo_created')}{Colors.RESET}")
                print(f"{Colors.CYAN}{self.lang_manager.get('code')}: {Colors.YELLOW}{code}{Colors.RESET}")
                pause(self.lang_manager)
            elif choice == "2":
                if self.hero:
                    diamonds = int(input(f"{self.lang_manager.get('diamonds')}: ") or 0)
                    gold = int(input(f"{self.lang_manager.get('gold')}: ") or 0)
                    self.hero.diamonds += diamonds
                    self.hero.gold += gold
                    print(f"{Colors.GREEN}✅ +{diamonds}💎 +{gold}💰{Colors.RESET}")
                else:
                    print(f"{Colors.RED}❌ {self.lang_manager.get('no_hero')}{Colors.RESET}")
                pause(self.lang_manager)
            elif choice == "3":
                if self.hero and SCYTHE_ID:
                    self.hero.add_item(SCYTHE_ID)
                    print(f"{Colors.GREEN}✅ {self.lang_manager.get('give_scythe')}!{Colors.RESET}")
                else:
                    print(f"{Colors.RED}❌ {self.lang_manager.get('error')}!{Colors.RESET}")
                pause(self.lang_manager)
            elif choice == "4":
                if self.hero and XPP_ARMOR_IDS:
                    self.hero.add_item(XPP_ARMOR_IDS[0])
                    print(f"{Colors.GREEN}✅ {self.lang_manager.get('give_armor')}!{Colors.RESET}")
                else:
                    print(f"{Colors.RED}❌ {self.lang_manager.get('error')}!{Colors.RESET}")
                pause(self.lang_manager)
            elif choice == "0":
                break
    
    def show_about(self):
        clear()
        show_border(self.lang_manager.get("about"), Colors.MAGENTA, 70)
        print(f"\n{Colors.YELLOW}Dark of Hemi v{VERSION}{Colors.RESET}")
        print(f"{Colors.CYAN}Developer: {Colors.GOLD}{DEVELOPER_NAME}{Colors.RESET}")
        print(f"\n{Colors.GREEN}Features:{Colors.RESET}")
        print(f"  • 35 unique classes")
        print(f"  • 60 locations in 3 worlds")
        print(f"  • Mega monsters (8 tiers)")
        print(f"  • 30-layer encryption")
        print(f"  • Promo code system")
        print(f"  • Pets and donate shop")
        print(f"  • Secret set: Soul Reaper + Scythe + X++ Armor")
        print(f"\n{Colors.CYAN}Support:{Colors.RESET}")
        print(f"  Telegram: {SUPPORT_TG}")
        print(f"  Discord: {SUPPORT_DS}")
        print(f"  Email: {SUPPORT_EMAIL}")
        pause(self.lang_manager)
    
    def new_game(self, save_slot: int):
        clear()
        show_border(self.lang_manager.get("new_game"), Colors.GREEN, 70)
        
        name = input(f"{Colors.CYAN}{self.lang_manager.get('enter_name')}: {Colors.RESET}").strip()
        if not name:
            name = "Hero"
        
        print(f"\n{Colors.YELLOW}{self.lang_manager.get('select_class')}:{Colors.RESET}")
        for i, cls in enumerate(CLASSES, 1):
            class_name = cls["name_" + self.lang_manager.current_lang]
            print(f"\n{Colors.CYAN}[{i}] {cls['icon']} {class_name}{Colors.RESET}")
            print(f"    ❤️{cls['hp']} HP  ⚔️{cls['attack']} ATK  🛡️{cls['defense']} DEF  🔮{cls['magic']} MAG  🎯{cls['crit']}% CRIT")
        
        while True:
            try:
                choice = int(input(f"\n{Colors.YELLOW}> {Colors.RESET}"))
                if 1 <= choice <= len(CLASSES):
                    break
                print(f"{Colors.RED}❌ {self.lang_manager.get('invalid_choice')}{Colors.RESET}")
            except ValueError:
                print(f"{Colors.RED}❌ {self.lang_manager.get('enter_number')}{Colors.RESET}")
        
        self.hero = Hero(name, choice, self.db)
        self.hero.current_location = 1
        self.db.save_hero(self.hero, save_slot)
        self.world_map.current_location_id = 1
        
        class_name = self.hero.get_class_name()
        print(f"\n{Colors.GREEN}{'=' * 50}{Colors.RESET}")
        print(f"{Colors.GREEN}✨ Welcome, {name} - {class_name}! ✨{Colors.RESET}")
        print(f"{Colors.GREEN}{'=' * 50}{Colors.RESET}")
        print(f"\n{Colors.CYAN}💡 TIP: Enter the code that appears on screen during battle!{Colors.RESET}")
        print(f"{Colors.CYAN}🗺️ Press T to travel between locations!{Colors.RESET}")
        pause(self.lang_manager)
        self.game_loop()
    
    def load_game(self, save_slot: int) -> bool:
        data = self.db.load_hero(save_slot)
        if not data:
            print(f"\n{Colors.RED}❌ {self.lang_manager.get('no_saves')}!{Colors.RESET}")
            pause(self.lang_manager)
            return False
        
        self.hero = Hero(data[1], data[2], self.db)
        self.hero.name = data[1]
        self.hero.level = data[3]
        self.hero.exp = data[4]
        self.hero.gold = data[5]
        self.hero.diamonds = data[6]
        self.hero.kills = data[7]
        self.hero.boss_kills = data[8]
        self.hero.hp = data[9]
        self.hero.mp = data[10]
        self.hero.max_hp = data[11]
        self.hero.max_mp = data[12]
        self.hero.attack = data[13]
        self.hero.defense = data[14]
        self.hero.magic = data[15]
        self.hero.crit = data[16]
        self.hero.agility = data[17]
        self.hero.potions_hp = data[18] if data[18] else 10
        self.hero.potions_mp = data[19] if data[19] else 5
        self.hero.pet_id = data[20] if data[20] else 0
        self.hero.inventory = json.loads(data[21]) if data[21] else []
        self.hero.equipped = json.loads(data[22]) if data[22] else {}
        self.hero.quests_progress = json.loads(data[23]) if len(data) > 23 and data[23] else {}
        self.hero.achievements_unlocked = json.loads(data[24]) if len(data) > 24 and data[24] else []
        self.hero.total_gold_earned = data[25] if len(data) > 25 else 0
        self.hero.last_daily = data[26] if len(data) > 26 else None
        self.hero.current_location = data[27] if len(data) > 27 else 1
        
        self.hero.update_stats()
        self.hero.init_quests()
        self.world_map.current_location_id = self.hero.current_location
        
        print(f"\n{Colors.GREEN}✅ {self.lang_manager.get('game_loaded')}{Colors.RESET}")
        pause(self.lang_manager)
        return True
    
    def game_loop(self):
        def auto_save():
            while self.running and self.hero and self.hero.is_alive():
                time.sleep(AUTO_SAVE_INTERVAL)
                if self.hero:
                    self.db.save_hero(self.hero)
        
        auto_save_thread = threading.Thread(target=auto_save, daemon=True)
        auto_save_thread.start()
        
        while self.running and self.hero.is_alive():
            clear()
            show_border(self.lang_manager.get("main_menu"), Colors.MAGENTA, 70)
            self.hero.show_stats()
            
            print(f"\n{Colors.CYAN}{'─' * 50}{Colors.RESET}")
            print(f"{Colors.GREEN}[1] ⚔️ {self.lang_manager.get('battle')} ({self.lang_manager.get('monster')}){Colors.RESET}")
            print(f"[2] 👑 {self.lang_manager.get('battle')} ({self.lang_manager.get('boss')})")
            print(f"[3] 🏪 {self.lang_manager.get('shop')}")
            print(f"[4] 💊 {self.lang_manager.get('potion_hp')} ({self.hero.potions_hp})")
            print(f"[5] 💙 {self.lang_manager.get('potion_mp')} ({self.hero.potions_mp})")
            print(f"[6] 💤 {self.lang_manager.get('rest')}")
            print(f"[7] 📦 {self.lang_manager.get('inventory')}")
            print(f"[8] 🎁 {self.lang_manager.get('daily')}")
            print(f"[9] 💎 {self.lang_manager.get('donate')}")
            print(f"[A] 🏆 {self.lang_manager.get('achievements')}")
            print(f"[Q] 📜 {self.lang_manager.get('quests')}")
            print(f"[T] 🗺️ {self.lang_manager.get('travel')}")
            print(f"[S] 💾 {self.lang_manager.get('save')}")
            print(f"{Colors.RED}[0] {self.lang_manager.get('exit')}{Colors.RESET}")
            
            choice = input(f"\n{Colors.YELLOW}> {Colors.RESET}").strip().upper()
            
            if choice == "1":
                monster = generate_mega_monster(self.hero.level, self.lang_manager.current_lang)
                BattleSystem.fight(self.hero, monster)
                self.hero.current_location = self.world_map.current_location_id
                self.db.save_hero(self.hero)
            elif choice == "2":
                if self.hero.level >= 5:
                    monster = generate_mega_monster(self.hero.level + 3, self.lang_manager.current_lang)
                    monster["tier"] = "BOSS"
                    monster["tier_color"] = Colors.RED + Colors.BOLD
                    monster["name"] = f"👑 {monster['name']} 👑"
                    monster["hp"] = int(monster["hp"] * 3)
                    monster["max_hp"] = monster["hp"]
                    monster["attack"] = int(monster["attack"] * 2)
                    monster["exp_reward"] = int(monster["exp_reward"] * 2)
                    monster["gold_reward"] = int(monster["gold_reward"] * 2)
                    BattleSystem.fight(self.hero, monster, is_boss=True)
                    self.hero.current_location = self.world_map.current_location_id
                    self.db.save_hero(self.hero)
                else:
                    print(f"{Colors.RED}❌ {self.lang_manager.get('need_level_5')}{Colors.RESET}")
                    pause(self.lang_manager)
            elif choice == "3":
                self.shop_manager.show_shop(self.hero, self.db)
                self.hero.current_location = self.world_map.current_location_id
                self.db.save_hero(self.hero)
            elif choice == "4":
                self.hero.use_hp_potion()
                self.db.save_hero(self.hero)
                pause(self.lang_manager)
            elif choice == "5":
                self.hero.use_mp_potion()
                self.db.save_hero(self.hero)
                pause(self.lang_manager)
            elif choice == "6":
                self.hero.rest()
                self.db.save_hero(self.hero)
                pause(self.lang_manager)
            elif choice == "7":
                self.show_inventory()
                self.hero.current_location = self.world_map.current_location_id
            elif choice == "8":
                reward = self.hero.daily_reward()
                if reward["claimed"]:
                    print(f"{Colors.GREEN}✅ {self.lang_manager.get('daily_received')}{Colors.RESET}")
                    print(f"{Colors.GREEN}+{reward['gold']}💰{Colors.RESET}")
                else:
                    print(f"{Colors.YELLOW}{reward['message']}{Colors.RESET}")
                self.db.save_hero(self.hero)
                pause(self.lang_manager)
            elif choice == "9":
                DonateManager.show_donate(self.hero, self.db, self.promo_manager)
                self.hero.current_location = self.world_map.current_location_id
            elif choice == "A":
                self.show_achievements()
            elif choice == "Q":
                self.show_quests()
            elif choice == "T":
                self.world_map.travel_menu(self.hero.level)
                self.hero.current_location = self.world_map.current_location_id
                self.db.save_hero(self.hero)
            elif choice == "S":
                self.db.save_hero(self.hero)
                print(f"{Colors.GREEN}✅ {self.lang_manager.get('game_saved')}{Colors.RESET}")
                pause(self.lang_manager)
            elif choice == "0":
                self.db.save_hero(self.hero)
                self.main_menu()
                return
    
    def show_inventory(self):
        while True:
            clear()
            show_border(self.lang_manager.get("inventory"), Colors.CYAN, 70)
            print(f"{Colors.CYAN}💰 {self.hero.gold} {self.lang_manager.get('gold')}{Colors.RESET}\n")
            
            print(f"{Colors.YELLOW}--- {self.lang_manager.get('equipment')} ---{Colors.RESET}")
            for slot, item_id in self.hero.equipped.items():
                print(f"  {slot}: {self.hero.get_item_name(item_id)}")
            
            print(f"\n{Colors.YELLOW}--- {self.lang_manager.get('inventory_title')} ---{Colors.RESET}")
            if not self.hero.inventory:
                print(f"  {Colors.DIM}{self.lang_manager.get('empty_inventory')}{Colors.RESET}")
            else:
                for i, item_id in enumerate(self.hero.inventory, 1):
                    item = self.hero.get_item_data(item_id)
                    if item:
                        color = Colors.RARITY.get(item["rank"], Colors.WHITE)
                        print(f"  [{i}] {color}{self.hero.get_item_name(item_id)}{Colors.RESET} (ATK: +{item['attack']}, DEF: +{item['defense']})")
            
            print(f"\n{Colors.CYAN}[E] {self.lang_manager.get('equip_item')}{Colors.RESET}")
            print(f"[S] {self.lang_manager.get('sell')}")
            print(f"{Colors.RED}[0] {self.lang_manager.get('back')}{Colors.RESET}")
            
            choice = input(f"\n{Colors.YELLOW}> {Colors.RESET}").strip().upper()
            
            if choice == "E":
                if self.hero.inventory:
                    try:
                        idx = int(input(f"{Colors.CYAN}{self.lang_manager.get('enter_item_number')}: {Colors.RESET}")) - 1
                        if 0 <= idx < len(self.hero.inventory):
                            self.hero.equip_item(self.hero.inventory[idx])
                            self.db.save_hero(self.hero)
                        else:
                            print(f"{Colors.RED}❌ {self.lang_manager.get('invalid_choice')}{Colors.RESET}")
                    except ValueError:
                        print(f"{Colors.RED}❌ {self.lang_manager.get('enter_number')}{Colors.RESET}")
                else:
                    print(f"{Colors.RED}❌ {self.lang_manager.get('empty_inventory')}{Colors.RESET}")
                pause(self.lang_manager)
            elif choice == "S":
                ShopManager.sell_items(self.hero, self.db)
            elif choice == "0":
                break
    
    def show_achievements(self):
        while True:
            clear()
            show_border(self.lang_manager.get("achievements"), Colors.YELLOW, 70)
            for ach in ACHIEVEMENTS:
                unlocked = ach["id"] in self.hero.achievements_unlocked
                status = "✅" if unlocked else "🔒"
                color = Colors.GREEN if unlocked else Colors.DIM
                name = ach["name_" + self.lang_manager.current_lang]
                desc = ach["desc_" + self.lang_manager.current_lang]
                print(f"\n{color}{status} {ach['icon']} {name}{Colors.RESET}")
                print(f"  {desc}")
                if not unlocked:
                    print(f"  {Colors.DIM}Reward: {ach['reward_gold']}💰{Colors.RESET}")
            print(f"\n{Colors.RED}[0] {self.lang_manager.get('back')}{Colors.RESET}")
            if input(f"\n{Colors.YELLOW}> {Colors.RESET}") == "0":
                break
    
    def show_quests(self):
        while True:
            clear()
            show_border(self.lang_manager.get("quests"), Colors.GREEN, 70)
            for quest in QUESTS:
                qid = str(quest["id"])
                progress = self.hero.quests_progress.get(qid, 0)
                completed = progress >= quest["target"] or progress == -1
                status = "✅" if completed else "📌"
                color = Colors.GREEN if completed else Colors.CYAN
                name = quest["name_" + self.lang_manager.current_lang]
                desc = quest["desc_" + self.lang_manager.current_lang]
                print(f"\n{color}{status} {quest['icon']} {name}{Colors.RESET}")
                print(f"  {desc}")
                if not completed and progress >= 0:
                    current = min(progress, quest["target"])
                    bar = show_health_bar(current, quest["target"], 20)
                    print(f"  Progress: {bar}")
                    print(f"  {Colors.DIM}Reward: {quest['reward_exp']} EXP + {quest['reward_gold']}💰{Colors.RESET}")
                elif completed:
                    print(f"  {Colors.GREEN}COMPLETED!{Colors.RESET}")
            print(f"\n{Colors.RED}[0] {self.lang_manager.get('back')}{Colors.RESET}")
            if input(f"\n{Colors.YELLOW}> {Colors.RESET}") == "0":
                break

# ==================== ЗАПУСК ====================
if __name__ == "__main__":
    try:
        game = DarkOfHemi()
        game.loading_screen()
        game.main_menu()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Game interrupted. The Fallen Angel awaits you again!{Colors.RESET}")
    except Exception as e:
        print(f"\n{Colors.RED}Critical error: {e}{Colors.RESET}")
        print(f"{Colors.CYAN}For support:{Colors.RESET}")
        print(f"  Telegram: {SUPPORT_TG}")
        print(f"  Discord: {SUPPORT_DS}")
        print(f"  Email: {SUPPORT_EMAIL}")
        input("\nPress Enter to exit...")
