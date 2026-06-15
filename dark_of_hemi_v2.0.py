#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dark of Hemi v2.0
=================
Расширение Dark of Hemi v1.1.0:
  * Кроссплатформенность и мобильный режим (Android/iOS/desktop)
  * 3-уровневый античит (клиент + сервер + подписанные сохранения)
  * Новые оффлайн-системы (крафт, престиж, профессии, улучшения и т.д.)
  * LAN-мультиплеер (PvP, рейды, чат, торговля, гильдии) — только stdlib

v1.1.0 (файл "привет.txt") НЕ модифицируется — он загружается через importlib
и переиспользуется. Запуск:

    python3 dark_of_hemi_v2.0.py --single            # одиночная игра
    python3 dark_of_hemi_v2.0.py --mobile            # мобильный режим
    python3 dark_of_hemi_v2.0.py --server            # LAN-сервер
    python3 dark_of_hemi_v2.0.py --client 127.0.0.1  # LAN-клиент
"""

import os
import sys
import argparse
import importlib.util
from importlib.machinery import SourceFileLoader
import platform
import json
import time
import gc
import hmac
import hashlib
import logging
import socket
import threading
import queue
from collections import deque, defaultdict

# ==================== КОНСТАНТЫ v2 ====================
V2_VERSION = "2.0.0"
DEFAULT_PORT = 50007
HERE = os.path.dirname(os.path.abspath(__file__))
V1_FILENAME = "привет.txt"

# Античит-пороги
MIN_ACTION_INTERVAL = 0.1      # сек между одинаковыми действиями
MAX_EXP_GAIN = 10000           # максимум опыта за раз (сервер)
MAX_GOLD_GAIN = 5000           # максимум золота за раз (сервер)
MAX_ACTIONS_PER_5S = 10        # лимит действий за 5 секунд
AUTO_SAVE_MOBILE = 30          # автосейв на телефоне, сек

# Жёсткие потолки характеристик
MAX_STATS = {
    "level": 1000,
    "attack": 99999,
    "defense": 99999,
    "magic": 99999,
    "gold": 999999999,
    "diamonds": 99999,
}

# Файлы
CHEATERS_LOG = os.path.join(HERE, "cheaters.log")
DATA_DIR = os.path.join(HERE, "data")


# ==================== ЗАГРУЗКА v1 ====================
_V1_CACHE = None


def load_v1():
    """Загрузить v1.1.0 (привет.txt) как модуль через importlib.

    Импорт безопасен: весь файловый ввод-вывод v1 спрятан внутри __init__/функций,
    а DarkOfHemi запускается только под `if __name__ == "__main__"`.
    """
    global _V1_CACHE
    if _V1_CACHE is not None:
        return _V1_CACHE

    v1_path = os.path.join(HERE, V1_FILENAME)
    if not os.path.exists(v1_path):
        raise FileNotFoundError(
            f"Не найден файл v1.1.0: {v1_path}. "
            f"Положите '{V1_FILENAME}' рядом с dark_of_hemi_v2.0.py"
        )

    # .txt не распознаётся importlib как Python-исходник, поэтому передаём
    # SourceFileLoader явно (иначе spec_from_file_location вернёт None).
    loader = SourceFileLoader("dark_v1", v1_path)
    spec = importlib.util.spec_from_file_location("dark_v1", v1_path, loader=loader)
    module = importlib.util.module_from_spec(spec)
    # Чтобы dataclass/typing внутри работал, регистрируем модуль до exec
    sys.modules["dark_v1"] = module
    try:
        spec.loader.exec_module(module)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"Не удалось загрузить v1.1.0: {e}") from e

    _patch_v1(module)
    _V1_CACHE = module
    return module


def _patch_v1(v1):
    """Заменить Windows-only arrow_menu(msvcrt) на кроссплатформенный numeric-вариант."""
    def cross_platform_arrow_menu(options, title="", lang=None):
        Colors = v1.Colors
        if title:
            print(f"\n{Colors.CYAN}{title}{Colors.RESET}")
        for i, opt in enumerate(options):
            print(f"  {Colors.YELLOW}{i + 1}{Colors.RESET}. {opt}")
        idx = safe_menu(len(options), prompt="> ", allow_zero=True)
        # safe_menu вернёт 0 для «назад» — мапим на последний пункт, иначе индекс-1
        if idx == 0:
            return len(options) - 1
        return idx - 1

    v1.arrow_menu = cross_platform_arrow_menu


# ==================== ПЛАТФОРМА ====================
def detect_platform():
    """Грубое определение платформы. iOS/Android детект ненадёжен — см. is_mobile()."""
    plat = platform.platform().lower()
    sys_plat = sys.platform

    if "ANDROID_ROOT" in os.environ or "ANDROID_DATA" in os.environ or "android" in plat:
        return "android"
    if sys_plat == "ios" or "iphone" in plat or "ipad" in plat:
        return "ios"
    if sys_plat.startswith("win"):
        return "windows"
    if sys_plat.startswith("linux"):
        return "linux"
    if sys_plat.startswith("darwin"):
        return "mac"
    return "unknown"


def is_mobile(force_mobile=False):
    """Мобильный режим. Авто-детект ненадёжен на iOS — всегда уважаем флаг --mobile."""
    if force_mobile:
        return True
    return detect_platform() in ("android", "ios")


# ==================== БЕЗОПАСНЫЙ ВВОД МЕНЮ ====================
def safe_menu(num_options, prompt="> ", allow_zero=True):
    """Кроссплатформенный numeric-ввод (без msvcrt).

    Возвращает int в диапазоне [1..num_options], либо 0 если allow_zero и ввод '0'.
    Повторяет запрос при некорректном вводе. EOF/Ctrl-D -> 0.
    """
    while True:
        try:
            raw = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            return 0
        if raw == "" :
            continue
        if not raw.lstrip("-").isdigit():
            print("  Введите число.")
            continue
        val = int(raw)
        if allow_zero and val == 0:
            return 0
        if 1 <= val <= num_options:
            return val
        print(f"  Введите число от {'0' if allow_zero else '1'} до {num_options}.")


# ==================== ЛОГГЕР ЧИТЕРОВ ====================
def _build_cheater_logger():
    logger = logging.getLogger("dark_of_hemi.cheaters")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        try:
            handler = logging.FileHandler(CHEATERS_LOG, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
            logger.addHandler(handler)
        except OSError:
            # если файл недоступен (только чтение на телефоне) — пишем в stderr
            logger.addHandler(logging.StreamHandler(sys.stderr))
    return logger


CHEAT_LOG = _build_cheater_logger()


def log_cheat(who, reason):
    """Записать подозрительное действие в cheaters.log."""
    CHEAT_LOG.info("%s | %s", who, reason)


# ==================== ПОДПИСАННЫЕ СОХРАНЕНИЯ ====================
class SecureSave:
    """HMAC-SHA256 подпись JSON-сохранений + детект подмены.

    Ключ выводится из машинно-независимого секрета; для LAN/single этого
    достаточно, чтобы поймать ручную правку файла сохранения.
    """

    # Секрет «зашит» — это не криптозащита от реверса, а барьер от naive-читов.
    _SECRET = b"DarkOfHemi-v2.0-save-integrity-key-2024"

    @classmethod
    def _sign(cls, payload_str):
        return hmac.new(cls._SECRET, payload_str.encode("utf-8"), hashlib.sha256).hexdigest()

    @classmethod
    def save(cls, data, filename):
        """Сохранить dict с подписью. Возвращает путь."""
        payload_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        sig = cls._sign(payload_str)
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump({"data": data, "sig": sig}, f, ensure_ascii=False)
        return filename

    @classmethod
    def load(cls, filename, who="unknown"):
        """Загрузить и проверить подпись. Бросает ValueError при подмене."""
        with open(filename, "r", encoding="utf-8") as f:
            wrapped = json.load(f)
        if "data" not in wrapped or "sig" not in wrapped:
            log_cheat(who, f"malformed save file {os.path.basename(filename)}")
            raise ValueError("Повреждённое сохранение (нет подписи).")
        payload_str = json.dumps(wrapped["data"], sort_keys=True, ensure_ascii=False)
        if not hmac.compare_digest(cls._sign(payload_str), wrapped["sig"]):
            log_cheat(who, f"tampered save file {os.path.basename(filename)}")
            raise ValueError("Сохранение изменено вручную! (неверная подпись)")
        return wrapped["data"]


# ==================== КЛИЕНТСКИЙ АНТИЧИТ ====================
class ClientAntiCheat:
    """Уровень 1: локальные проверки скорости/урона/характеристик."""

    def __init__(self, who="player"):
        self.who = who
        self.last_action_time = {}
        self.suspicious = []

    def check_timing(self, action):
        """False, если действие повторяется слишком быстро (< MIN_ACTION_INTERVAL)."""
        now = time.time()
        last = self.last_action_time.get(action, 0.0)
        self.last_action_time[action] = now
        if now - last < MIN_ACTION_INTERVAL:
            self.suspicious.append((action, now))
            log_cheat(self.who, f"timing cheat: {action} dt={now - last:.4f}s")
            return False
        return True

    def check_damage(self, damage, attack):
        """Урон не должен превышать attack*3 (потолок клиента)."""
        cap = max(1, attack) * 3
        if damage > cap:
            log_cheat(self.who, f"damage cheat: {damage} > cap {cap}")
            return False
        return True

    def clamp_stats(self, hero):
        """Привести характеристики к MAX_STATS. Возвращает список нарушений."""
        violations = []
        for stat, max_val in MAX_STATS.items():
            cur = getattr(hero, stat, None)
            if cur is not None and cur > max_val:
                setattr(hero, stat, max_val)
                violations.append(stat)
        # внутренняя согласованность
        if getattr(hero, "hp", 0) > getattr(hero, "max_hp", 0):
            hero.hp = hero.max_hp
            violations.append("hp>max_hp")
        if violations:
            log_cheat(self.who, f"stat clamp: {','.join(violations)}")
        return violations


# ==================== МОНИТОР ПОВЕДЕНИЯ ====================
class BehaviorMonitor:
    """Скользящее окно действий + детект нечеловеческих паттернов."""

    def __init__(self, who="player"):
        self.who = who
        self.actions = deque(maxlen=200)

    def add_action(self, action):
        now = time.time()
        self.actions.append((now, action))
        return not self.is_suspicious()

    def is_suspicious(self):
        now = time.time()
        # > MAX_ACTIONS_PER_5S * 2 любых действий за 5с
        recent = [a for t, a in self.actions if now - t < 5]
        if len(recent) > MAX_ACTIONS_PER_5S * 2:
            log_cheat(self.who, f"action flood: {len(recent)} actions / 5s")
            return True
        # > 30 атак за 10с (3 атаки/сек)
        recent_attacks = [a for t, a in self.actions if a == "attack" and now - t < 10]
        if len(recent_attacks) > 30:
            log_cheat(self.who, f"attack flood: {len(recent_attacks)} attacks / 10s")
            return True
        return False


# ==================== МОБИЛЬНЫЙ UI ====================
class MobileUI:
    """Упрощённый интерфейс для телефона: цифры 1-8, 0 = назад, экономия ресурсов."""

    def __init__(self, enabled=False):
        self.enabled = enabled

    def cleanup(self):
        """Сброс мусора для экономии памяти (телефон вылетает при нехватке)."""
        if self.enabled:
            gc.collect()

    def banner(self, platform_name):
        if not self.enabled:
            return
        print("=" * 40)
        print(f" DARK OF HEMI v{V2_VERSION}  [MOBILE]")
        print(f" platform: {platform_name}")
        print(" Управление: 1-8 действия, 0 назад")
        print(f" Автосейв каждые {AUTO_SAVE_MOBILE} сек")
        print("=" * 40)

    def menu(self, options, title=""):
        """Нарисовать компактное меню и вернуть выбор (0..len)."""
        if title:
            print(f"\n[{title}]")
        for i, opt in enumerate(options):
            print(f" {i + 1}. {opt}")
        print(" 0. Назад")
        return safe_menu(len(options), prompt="> ", allow_zero=True)


# ==================== СОСТОЯНИЕ v2 (sidecar) ====================
class HeroV2State:
    """Контейнер v2-полей, которых нет в фиксированной схеме v1 (30 колонок).

    Сохраняется отдельным подписанным файлом data/hero_v2_<slot>.json.
    """

    DEFAULTS = {
        "prestige": 0,                 # 0..10
        "prestige_mult": 1.0,          # множитель от престижа
        "professions": {},             # {"smith": lvl, "alchemist": lvl, "fisher": lvl}
        "materials": {},               # {"iron": 5, "herb": 3, ...}
        "upgrades": {},                # {item_id: +N}
        "sockets": {},                 # {item_id: [gem,...]}
        "transmog": {},                # {slot: item_id-скин}
        "home_level": 0,               # 0..5
        "potions": {},                 # {potion_key: count}
        "daily_streak": 0,             # дней подряд
        "last_daily_day": None,        # epoch-day последнего захода
        "achievements_v2": [],         # id разблокированных v2-достижений
        "endless_best": 0,             # лучший рекорд бесконечного режима
        "bank_gold": 0,                # золото в банке
        "world_seed": 0,               # сид процедурного мира
    }

    def __init__(self, data=None):
        self.data = dict(self.DEFAULTS)
        if data:
            self.data.update(data)
            # вложенные словари — копируем, чтобы не делить ссылку с DEFAULTS
            for k in ("professions", "materials", "upgrades", "sockets", "transmog", "potions"):
                self.data[k] = dict(self.data.get(k) or {})

    def __getitem__(self, k):
        return self.data[k]

    def __setitem__(self, k, v):
        self.data[k] = v

    def get(self, k, default=None):
        return self.data.get(k, default)

    @staticmethod
    def _path(slot):
        return os.path.join(DATA_DIR, f"hero_v2_{slot}.json")

    @classmethod
    def load(cls, slot=1, who="player"):
        path = cls._path(slot)
        if not os.path.exists(path):
            return cls()
        try:
            return cls(SecureSave.load(path, who=who))
        except ValueError:
            # подмена обнаружена — стартуем с дефолтов (факт записан в cheaters.log)
            return cls()

    def save(self, slot=1):
        return SecureSave.save(self.data, self._path(slot))


# ==================== ПРЕСТИЖ ====================
class PrestigeSystem:
    MAX_PRESTIGE = 10
    REQUIRED_LEVEL = 100  # минимальный уровень для престижа

    @staticmethod
    def can_prestige(hero, state):
        return (getattr(hero, "level", 1) >= PrestigeSystem.REQUIRED_LEVEL
                and state["prestige"] < PrestigeSystem.MAX_PRESTIGE)

    @staticmethod
    def do_prestige(hero, state):
        """Сброс уровня в обмен на постоянный множитель. Возвращает (ok, msg)."""
        if not PrestigeSystem.can_prestige(hero, state):
            return False, f"Нужен уровень {PrestigeSystem.REQUIRED_LEVEL} и престиж < {PrestigeSystem.MAX_PRESTIGE}."
        state["prestige"] += 1
        # +10% к базовым статам за каждый уровень престижа
        state["prestige_mult"] = round(1.0 + 0.10 * state["prestige"], 2)
        hero.level = 1
        hero.exp = 0
        return True, f"Престиж {state['prestige']}/10! Множитель x{state['prestige_mult']}"


# ==================== ПРОЦЕДУРНЫЙ МИР (сид) ====================
class ProceduralWorld:
    """Детерминированная генерация по сиду. ВАЖНО: и сервер, и клиенты должны
    использовать одинаковый порядок вызовов random.Random(seed)."""

    BIOMES = ["Лес", "Пустыня", "Тундра", "Вулкан", "Болото", "Пещеры", "Руины", "Океан"]
    MODIFIERS = ["проклятый", "благословенный", "туманный", "кристальный", "выжженный", "древний"]

    def __init__(self, seed):
        import random as _r
        self.seed = seed
        self.rng = _r.Random(seed)

    def generate_region(self, index):
        biome = self.rng.choice(self.BIOMES)
        modifier = self.rng.choice(self.MODIFIERS)
        danger = self.rng.randint(1, 100)
        loot_bonus = round(self.rng.uniform(1.0, 3.0), 2)
        return {
            "index": index,
            "name": f"{modifier.capitalize()} {biome}",
            "danger": danger,
            "loot_bonus": loot_bonus,
        }

    def generate_world(self, n_regions=10):
        return [self.generate_region(i) for i in range(n_regions)]


# ==================== КРАФТ (20 рецептов) ====================
class CraftingSystem:
    # рецепт: id -> {name, materials:{mat:count}, result_stat, result_value}
    RECIPES = {}

    @classmethod
    def _build_recipes(cls):
        if cls.RECIPES:
            return
        mats = ["iron", "herb", "wood", "crystal", "leather", "bone", "essence", "gold_ore"]
        stats = [("attack", 5), ("defense", 5), ("hp", 20), ("magic", 4), ("crit", 2)]
        import itertools
        rid = 1
        for i in range(20):
            m1 = mats[i % len(mats)]
            m2 = mats[(i + 3) % len(mats)]
            stat, base = stats[i % len(stats)]
            cls.RECIPES[rid] = {
                "name": f"Рецепт #{rid} ({stat}+{base + i})",
                "materials": {m1: 2 + (i % 3), m2: 1 + (i % 2)},
                "result_stat": stat,
                "result_value": base + i,
            }
            rid += 1

    @classmethod
    def can_craft(cls, state, recipe_id):
        cls._build_recipes()
        r = cls.RECIPES.get(recipe_id)
        if not r:
            return False
        have = state["materials"]
        return all(have.get(m, 0) >= cnt for m, cnt in r["materials"].items())

    @classmethod
    def craft(cls, hero, state, recipe_id):
        cls._build_recipes()
        if not cls.can_craft(state, recipe_id):
            return False, "Недостаточно материалов."
        r = cls.RECIPES[recipe_id]
        for m, cnt in r["materials"].items():
            state["materials"][m] -= cnt
        stat = r["result_stat"]
        cur = getattr(hero, stat, 0)
        setattr(hero, stat, cur + r["result_value"])
        return True, f"Создано: {r['name']} (+{r['result_value']} {stat})"


# ==================== ПРОФЕССИИ ====================
class ProfessionSystem:
    PROFESSIONS = {
        "smith": "Кузнец",
        "alchemist": "Алхимик",
        "fisher": "Рыбак",
    }
    MAX_LEVEL = 50
    # что добывает каждая профессия
    GATHER = {
        "smith": ["iron", "gold_ore", "crystal"],
        "alchemist": ["herb", "essence", "bone"],
        "fisher": ["wood", "leather", "essence"],
    }

    @classmethod
    def train(cls, state, prof):
        if prof not in cls.PROFESSIONS:
            return False, "Нет такой профессии."
        profs = state["professions"]
        lvl = profs.get(prof, 0)
        if lvl >= cls.MAX_LEVEL:
            return False, f"{cls.PROFESSIONS[prof]} уже максимального уровня."
        profs[prof] = lvl + 1
        return True, f"{cls.PROFESSIONS[prof]}: уровень {lvl + 1}"

    @classmethod
    def gather(cls, state, prof, rng):
        """Добыть материалы (зависит от уровня). rng — random.Random для детерминизма."""
        if prof not in cls.PROFESSIONS:
            return False, "Нет такой профессии."
        lvl = state["professions"].get(prof, 0)
        if lvl < 1:
            return False, "Сначала изучите профессию."
        mat = rng.choice(cls.GATHER[prof])
        amount = 1 + rng.randint(0, max(1, lvl // 10))
        state["materials"][mat] = state["materials"].get(mat, 0) + amount
        return True, f"Добыто: {mat} x{amount}"


# ==================== УЛУЧШЕНИЕ ПРЕДМЕТОВ (+1..+5) ====================
class ItemUpgrade:
    MAX_PLUS = 5
    # шанс успеха по текущему уровню
    SUCCESS_CHANCE = {0: 0.95, 1: 0.80, 2: 0.65, 3: 0.50, 4: 0.35}

    @classmethod
    def upgrade(cls, state, item_id, rng):
        cur = state["upgrades"].get(str(item_id), 0)
        if cur >= cls.MAX_PLUS:
            return False, f"Предмет уже +{cls.MAX_PLUS} (максимум)."
        chance = cls.SUCCESS_CHANCE.get(cur, 0.2)
        if rng.random() < chance:
            state["upgrades"][str(item_id)] = cur + 1
            return True, f"Успех! Предмет улучшен до +{cur + 1}"
        return False, f"Неудача. Предмет остался +{cur}"


# ==================== КАМНИ УСИЛЕНИЯ (сокеты) ====================
class GemSocketSystem:
    GEMS = {
        "ruby": ("attack", 10),
        "sapphire": ("magic", 8),
        "emerald": ("defense", 10),
        "diamond": ("hp", 50),
        "topaz": ("crit", 5),
    }
    MAX_SOCKETS = 3

    @classmethod
    def insert(cls, hero, state, item_id, gem):
        if gem not in cls.GEMS:
            return False, "Нет такого камня."
        slots = state["sockets"].setdefault(str(item_id), [])
        if len(slots) >= cls.MAX_SOCKETS:
            return False, f"Все {cls.MAX_SOCKETS} слота заняты."
        slots.append(gem)
        stat, val = cls.GEMS[gem]
        setattr(hero, stat, getattr(hero, stat, 0) + val)
        return True, f"Камень {gem} вставлен (+{val} {stat})"


# ==================== ТРАНСМОГРИФИКАЦИЯ ====================
class TransmogSystem:
    @staticmethod
    def apply(state, slot, skin_item_id):
        state["transmog"][slot] = skin_item_id
        return True, f"Внешний вид слота '{slot}' изменён."

    @staticmethod
    def clear(state, slot):
        state["transmog"].pop(slot, None)
        return True, f"Внешний вид слота '{slot}' сброшен."


# ==================== ДОМ ====================
class HomeSystem:
    MAX_LEVEL = 5
    UPGRADE_COST = {1: 1000, 2: 5000, 3: 20000, 4: 50000, 5: 100000}
    # бонусы за уровень дома (пассивные)
    BONUS = {0: 0, 1: 5, 2: 15, 3: 30, 4: 50, 5: 100}

    @classmethod
    def upgrade(cls, hero, state):
        lvl = state["home_level"]
        if lvl >= cls.MAX_LEVEL:
            return False, "Дом максимального уровня."
        cost = cls.UPGRADE_COST[lvl + 1]
        if getattr(hero, "gold", 0) < cost:
            return False, f"Нужно {cost} золота."
        hero.gold -= cost
        state["home_level"] = lvl + 1
        return True, f"Дом улучшен до уровня {lvl + 1} (бонус +{cls.BONUS[lvl + 1]})"

    @classmethod
    def rest_bonus(cls, state):
        return cls.BONUS[state["home_level"]]


# ==================== ЗЕЛЬЯ (5 видов) ====================
class PotionSystem:
    POTIONS = {
        "heal": ("Лечение", "hp", 200),
        "mana": ("Мана", "mp", 100),
        "strength": ("Сила", "attack", 15),
        "iron": ("Железная кожа", "defense", 15),
        "luck": ("Удача", "crit", 10),
    }

    @classmethod
    def use(cls, hero, state, key):
        if key not in cls.POTIONS:
            return False, "Нет такого зелья."
        have = state["potions"].get(key, 0)
        if have < 1:
            return False, "Зелье закончилось."
        state["potions"][key] = have - 1
        name, stat, val = cls.POTIONS[key]
        if stat == "hp":
            hero.hp = min(getattr(hero, "max_hp", val), getattr(hero, "hp", 0) + val)
        elif stat == "mp":
            hero.mp = min(getattr(hero, "max_mp", val), getattr(hero, "mp", 0) + val)
        else:
            setattr(hero, stat, getattr(hero, stat, 0) + val)
        return True, f"Использовано: {name}"


# ==================== ПОГОДА / ВРЕМЯ СУТОК ====================
class WeatherSystem:
    WEATHER = ["☀️ Ясно", "🌧️ Дождь", "⛈️ Гроза", "🌫️ Туман", "❄️ Снег", "🌪️ Буря"]

    def __init__(self, rng):
        self.rng = rng
        self.current = self.rng.choice(self.WEATHER)

    def tick(self):
        if self.rng.random() < 0.3:
            self.current = self.rng.choice(self.WEATHER)
        return self.current


class DayNightCycle:
    """Время суток влияет на мобов: ночью сильнее."""
    PHASES = ["🌅 Утро", "☀️ День", "🌇 Вечер", "🌙 Ночь"]

    def __init__(self, start=0):
        self.index = start % 4

    def advance(self):
        self.index = (self.index + 1) % 4
        return self.PHASES[self.index]

    @property
    def phase(self):
        return self.PHASES[self.index]

    def monster_multiplier(self):
        # ночью мобы на 50% сильнее, вечером на 20%
        return {0: 1.0, 1: 1.0, 2: 1.2, 3: 1.5}[self.index]


# ==================== СЛУЧАЙНЫЕ СОБЫТИЯ (5 типов) ====================
class EventSystem:
    EVENTS = ["treasure", "ambush", "merchant", "blessing", "curse"]

    @classmethod
    def trigger(cls, hero, state, rng):
        ev = rng.choice(cls.EVENTS)
        if ev == "treasure":
            g = rng.randint(100, 1000)
            hero.gold = getattr(hero, "gold", 0) + g
            return ev, f"💰 Сокровище! +{g} золота"
        if ev == "ambush":
            dmg = rng.randint(10, 50)
            hero.hp = max(1, getattr(hero, "hp", 1) - dmg)
            return ev, f"⚔️ Засада! -{dmg} HP"
        if ev == "merchant":
            return ev, "🧙 Странствующий торговец предлагает товары"
        if ev == "blessing":
            hero.attack = getattr(hero, "attack", 0) + 5
            return ev, "✨ Благословение! +5 к атаке"
        if ev == "curse":
            hero.defense = max(0, getattr(hero, "defense", 0) - 3)
            return ev, "💀 Проклятие! -3 к защите"
        return ev, "Ничего не произошло"


# ==================== СЕЗОННЫЕ СОБЫТИЯ ====================
class SeasonalEvents:
    # выбираем сезон по дню месяца, чтобы не зависеть от Date.now в коде
    SEASONS = {
        "winter": "❄️ Зимний фестиваль (x2 опыт)",
        "spring": "🌸 Весеннее цветение (x2 материалы)",
        "summer": "☀️ Летний турнир (PvP бонусы)",
        "autumn": "🍂 Осенний урожай (x2 золото)",
    }

    @staticmethod
    def current(month):
        if month in (12, 1, 2):
            return "winter"
        if month in (3, 4, 5):
            return "spring"
        if month in (6, 7, 8):
            return "summer"
        return "autumn"


# ==================== ЕЖЕДНЕВНЫЙ КАЛЕНДАРЬ ====================
class DailyCalendar:
    # награды по дням стрика (циклично по 7)
    REWARDS = {
        1: ("gold", 500), 2: ("gold", 1000), 3: ("diamonds", 10),
        4: ("gold", 2000), 5: ("diamonds", 20), 6: ("gold", 5000),
        7: ("diamonds", 50),
    }

    @classmethod
    def claim(cls, hero, state, today_epoch_day):
        last = state["last_daily_day"]
        if last == today_epoch_day:
            return False, "Награда уже получена сегодня."
        if last is not None and today_epoch_day - last == 1:
            state["daily_streak"] += 1
        else:
            state["daily_streak"] = 1
        state["last_daily_day"] = today_epoch_day
        day = ((state["daily_streak"] - 1) % 7) + 1
        kind, amount = cls.REWARDS[day]
        setattr(hero, kind, getattr(hero, kind, 0) + amount)
        return True, f"День {day}: +{amount} {kind} (стрик {state['daily_streak']})"


# ==================== БЕСКОНЕЧНЫЙ РЕЖИМ ====================
class EndlessMode:
    """Бесконечные волны мобов. Возвращает достигнутую волну."""

    @staticmethod
    def wave_monster(v1, wave, player_level, lang="ru"):
        """Сгенерировать моба для волны через v1.generate_mega_monster, усилив по волне."""
        mon = v1.generate_mega_monster(max(player_level, wave), lang)
        scale = 1.0 + wave * 0.1
        mon["hp"] = int(mon["hp"] * scale)
        mon["attack"] = int(mon["attack"] * scale)
        return mon

    @staticmethod
    def record(state, wave):
        if wave > state["endless_best"]:
            state["endless_best"] = wave
            return True
        return False


# ==================== БАНК (часть экономики) ====================
class BankSystem:
    @staticmethod
    def deposit(hero, state, amount):
        if amount <= 0 or getattr(hero, "gold", 0) < amount:
            return False, "Недостаточно золота."
        hero.gold -= amount
        state["bank_gold"] += amount
        return True, f"Внесено {amount}. В банке: {state['bank_gold']}"

    @staticmethod
    def withdraw(hero, state, amount):
        if amount <= 0 or state["bank_gold"] < amount:
            return False, "Недостаточно средств в банке."
        state["bank_gold"] -= amount
        hero.gold = getattr(hero, "gold", 0) + amount
        return True, f"Снято {amount}. В банке: {state['bank_gold']}"


# ==================== V2 ДОСТИЖЕНИЯ (+30) ====================
def build_v2_achievements():
    """30 новых достижений. Возвращает dict id->{name, check(hero,state)}."""
    ach = {}
    # пороги по разным метрикам
    specs = [
        ("prestige", lambda h, s, n: s["prestige"] >= n, [1, 3, 5, 10], "Престиж"),
        ("home", lambda h, s, n: s["home_level"] >= n, [1, 3, 5], "Дом ур."),
        ("endless", lambda h, s, n: s["endless_best"] >= n, [10, 50, 100], "Волна"),
        ("bank", lambda h, s, n: s["bank_gold"] >= n, [10000, 100000, 1000000], "Банк"),
        ("daily", lambda h, s, n: s["daily_streak"] >= n, [7, 30, 100], "Стрик"),
        ("level", lambda h, s, n: getattr(h, "level", 1) >= n, [50, 100, 500], "Уровень"),
        ("gold", lambda h, s, n: getattr(h, "gold", 0) >= n, [100000, 1000000, 100000000], "Золото"),
        ("attack", lambda h, s, n: getattr(h, "attack", 0) >= n, [1000, 10000, 50000], "Атака"),
        ("materials", lambda h, s, n: sum(s["materials"].values()) >= n, [50, 500, 5000], "Материалы"),
        ("professions", lambda h, s, n: any(v >= n for v in s["professions"].values() or [0]), [10, 50], "Профессия"),
    ]
    aid = 1
    for key, fn, thresholds, label in specs:
        for n in thresholds:
            ach[aid] = {
                "name": f"{label} {n}",
                "check": (lambda h, s, fn=fn, n=n: fn(h, s, n)),
            }
            aid += 1
    return ach


V2_ACHIEVEMENTS = build_v2_achievements()


def check_v2_achievements(hero, state):
    """Вернуть список новоразблокированных id."""
    unlocked = set(state["achievements_v2"])
    newly = []
    for aid, a in V2_ACHIEVEMENTS.items():
        if aid not in unlocked:
            try:
                if a["check"](hero, state):
                    unlocked.add(aid)
                    newly.append(aid)
            except Exception:  # noqa: BLE001
                pass
    state["achievements_v2"] = sorted(unlocked)
    return newly


# ==================== ПРОТОКОЛ ====================
class NetProtocol:
    """Newline-delimited JSON. Без I/O — чисто кодирование (юнит-тестируемо).

    ВАЖНО: никогда не использовать indent= в json.dumps, иначе перевод строки
    внутри payload сломает кадрирование.
    """

    @staticmethod
    def make(msg_type, seq=0, pid=None, **fields):
        msg = {"type": msg_type, "seq": seq, "pid": pid, "ts": 0.0}
        msg.update(fields)
        return msg

    @staticmethod
    def encode(msg):
        line = json.dumps(msg, ensure_ascii=False, separators=(",", ":"))
        assert "\n" not in line, "payload содержит перевод строки — кадрирование сломано"
        return (line + "\n").encode("utf-8")

    @staticmethod
    def decode_stream(buffer):
        """Принять str-буфер, вернуть (список сообщений, остаток-буфер)."""
        messages = []
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()
            if not line:
                continue
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                # битый кадр — пропускаем
                continue
        return messages, buffer


# ==================== СЕРВЕРНЫЙ АНТИЧИТ ====================
class ServerAntiCheat:
    """Уровень 2: авторитетная валидация всех действий на сервере."""

    def __init__(self):
        self.history = defaultdict(lambda: deque(maxlen=100))  # pid -> deque[(t, action)]

    def validate(self, pid, action_type, value, attacker_attack=0):
        """Вернуть (ok, reason). reason пустой если ok."""
        now = time.time()

        if action_type == "exp_gain" and value > MAX_EXP_GAIN:
            return False, f"exp_gain {value} > {MAX_EXP_GAIN}"
        if action_type == "gold_gain" and value > MAX_GOLD_GAIN:
            return False, f"gold_gain {value} > {MAX_GOLD_GAIN}"
        if action_type == "damage":
            max_damage = attacker_attack * 2 + 50
            if value > max_damage:
                return False, f"damage {value} > {max_damage}"

        # частота действий
        hist = self.history[pid]
        hist.append((now, action_type))
        recent = [t for t, a in hist if now - t < 5]
        if len(recent) > MAX_ACTIONS_PER_5S:
            return False, f"action rate {len(recent)}/5s > {MAX_ACTIONS_PER_5S}"

        return True, ""


# ==================== СЕРВЕРНЫЙ МИР ====================
class ServerWorld:
    """Авторитетное состояние: дуэли, рейды, торговля, гильдии, аукцион, мир-боссы."""

    def __init__(self, seed=0):
        self.seed = seed
        self.lock = threading.Lock()
        self.duels = {}          # duel_id -> {a, b, hp:{pid:hp}}
        self.raids = {}          # raid_id -> {boss_hp, max_hp, lock, participants:set}
        self.trades = {}         # trade_id -> {...}
        self.guilds = {}         # guild_name -> {leader, members:set}
        self.auctions = {}       # auction_id -> {seller, item_id, price}
        self.chat_log = deque(maxlen=200)
        self._counter = 0

    def _next_id(self, prefix):
        with self.lock:
            self._counter += 1
            return f"{prefix}{self._counter}"

    # --- рейды (с per-instance lock против гонок) ---
    def start_raid(self, boss_hp):
        rid = self._next_id("raid")
        self.raids[rid] = {
            "boss_hp": boss_hp, "max_hp": boss_hp,
            "lock": threading.Lock(), "participants": set(), "damage_by": defaultdict(int),
        }
        return rid

    def raid_hit(self, rid, pid, damage):
        """Применить урон по боссу под per-instance lock (FIFO). Возвращает (boss_hp, dead)."""
        raid = self.raids.get(rid)
        if raid is None:
            return None, False
        with raid["lock"]:
            raid["participants"].add(pid)
            raid["damage_by"][pid] += damage
            raid["boss_hp"] = max(0, raid["boss_hp"] - damage)
            dead = raid["boss_hp"] == 0
            return raid["boss_hp"], dead

    # --- гильдии ---
    def guild_create(self, name, leader_pid):
        if name in self.guilds:
            return False, "Гильдия уже существует."
        self.guilds[name] = {"leader": leader_pid, "members": {leader_pid}}
        return True, f"Гильдия '{name}' создана."

    def guild_join(self, name, pid):
        g = self.guilds.get(name)
        if not g:
            return False, "Нет такой гильдии."
        if len(g["members"]) >= 10:
            return False, "Гильдия заполнена (10/10)."
        g["members"].add(pid)
        return True, f"Вы вступили в '{name}'."

    # --- торговля (сервер как эскроу) ---
    def open_trade(self, from_pid, to_pid, give_items, want_gold):
        tid = self._next_id("trade")
        self.trades[tid] = {
            "from": from_pid, "to": to_pid,
            "give": list(give_items), "want_gold": want_gold,
            "accepted": False,
        }
        return tid

    # --- аукцион ---
    def auction_list(self, seller_pid, item_id, price):
        aid = self._next_id("auc")
        self.auctions[aid] = {"seller": seller_pid, "item_id": item_id, "price": price}
        return aid


# ==================== СОЕДИНЕНИЕ КЛИЕНТА (на сервере) ====================
class ClientConn:
    def __init__(self, sock, addr, pid):
        self.sock = sock
        self.addr = addr
        self.pid = pid
        self.name = f"player{pid}"
        self.class_id = 0
        self.level = 1
        self.attack = 10
        self.send_lock = threading.Lock()
        self.buffer = ""
        self.alive = True

    def send(self, msg):
        try:
            with self.send_lock:
                self.sock.sendall(NetProtocol.encode(msg))
        except OSError:
            self.alive = False

    def close(self):
        self.alive = False
        try:
            self.sock.close()
        except OSError:
            pass


# ==================== СЕРВЕР ====================
class GameServer:
    def __init__(self, host="0.0.0.0", port=DEFAULT_PORT, seed=0):
        self.host = host
        self.port = port
        self.clients = {}          # pid -> ClientConn
        self.clients_lock = threading.Lock()
        self.anticheat = ServerAntiCheat()
        self.world = ServerWorld(seed=seed)
        self.seed = seed
        self._pid_counter = 0
        self._server_sock = None
        self.running = False

    def _next_pid(self):
        self._pid_counter += 1
        return self._pid_counter

    def broadcast(self, msg, exclude=None):
        with self.clients_lock:
            conns = list(self.clients.values())
        for c in conns:
            if c.pid != exclude:
                c.send(msg)

    def start(self):
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self.host, self.port))
        self._server_sock.listen(8)
        self.running = True
        print(f"[server] Слушаю {self.host}:{self.port} (seed={self.seed}). Ctrl-C для выхода.")
        try:
            while self.running:
                try:
                    sock, addr = self._server_sock.accept()
                except OSError:
                    break
                pid = self._next_pid()
                conn = ClientConn(sock, addr, pid)
                with self.clients_lock:
                    self.clients[pid] = conn
                threading.Thread(target=self._client_loop, args=(conn,), daemon=True).start()
        finally:
            self.shutdown()

    def shutdown(self):
        self.running = False
        with self.clients_lock:
            for c in self.clients.values():
                c.close()
            self.clients.clear()
        if self._server_sock:
            try:
                self._server_sock.close()
            except OSError:
                pass

    def _client_loop(self, conn):
        while conn.alive and self.running:
            try:
                chunk = conn.sock.recv(4096)
            except OSError:
                break
            if not chunk:
                break
            conn.buffer += chunk.decode("utf-8", errors="replace")
            messages, conn.buffer = NetProtocol.decode_stream(conn.buffer)
            for msg in messages:
                self._handle(conn, msg)
        self._disconnect(conn)

    def _disconnect(self, conn):
        with self.clients_lock:
            self.clients.pop(conn.pid, None)
        conn.close()
        self.broadcast(NetProtocol.make("leave", pid=conn.pid, name=conn.name))

    def _kick(self, conn, reason):
        log_cheat(conn.name, f"server kick: {reason}")
        conn.send(NetProtocol.make("kick", pid=conn.pid, reason=reason))
        conn.close()

    def _handle(self, conn, msg):
        mtype = msg.get("type")

        if mtype == "hello":
            conn.name = msg.get("name", conn.name)
            conn.class_id = msg.get("class_id", 0)
            conn.level = msg.get("level", 1)
            conn.attack = msg.get("attack", 10)
            with self.clients_lock:
                roster = [{"pid": c.pid, "name": c.name, "level": c.level}
                          for c in self.clients.values()]
            conn.send(NetProtocol.make("welcome", pid=conn.pid,
                                       players=roster, world_seed=self.seed))
            self.broadcast(NetProtocol.make("join", pid=conn.pid, name=conn.name),
                           exclude=conn.pid)

        elif mtype == "chat":
            text = str(msg.get("text", ""))[:200]
            ok, reason = self.anticheat.validate(conn.pid, "chat", 0)
            if not ok:
                self._kick(conn, reason)
                return
            self.world.chat_log.append((conn.name, text))
            self.broadcast(NetProtocol.make("chat", pid=conn.pid, name=conn.name, text=text))

        elif mtype == "pvp_action":
            damage = int(msg.get("damage", 0))
            ok, reason = self.anticheat.validate(conn.pid, "damage", damage, conn.attack)
            if not ok:
                self._kick(conn, reason)
                return
            duel_id = msg.get("duel_id")
            self.broadcast(NetProtocol.make("pvp_result", pid=conn.pid,
                                            duel_id=duel_id, attacker=conn.pid, damage=damage))

        elif mtype == "raid_start":
            boss_hp = int(msg.get("boss_hp", 10000))
            rid = self.world.start_raid(boss_hp)
            self.broadcast(NetProtocol.make("raid_update", raid_id=rid,
                                            boss_hp=boss_hp, last_hitter=None, damage=0))
            conn.send(NetProtocol.make("raid_started", raid_id=rid, boss_hp=boss_hp))

        elif mtype == "raid_action":
            damage = int(msg.get("damage", 0))
            ok, reason = self.anticheat.validate(conn.pid, "damage", damage, conn.attack)
            if not ok:
                self._kick(conn, reason)
                return
            rid = msg.get("raid_id")
            boss_hp, dead = self.world.raid_hit(rid, conn.pid, damage)
            if boss_hp is None:
                conn.send(NetProtocol.make("error", code="no_raid", msg="Рейд не найден"))
                return
            self.broadcast(NetProtocol.make("raid_update", raid_id=rid,
                                            boss_hp=boss_hp, last_hitter=conn.pid, damage=damage))
            if dead:
                self.broadcast(NetProtocol.make("raid_complete", raid_id=rid))

        elif mtype == "guild_create":
            ok, m = self.world.guild_create(msg.get("name", ""), conn.pid)
            conn.send(NetProtocol.make("guild_result", ok=ok, msg=m))

        elif mtype == "guild_join":
            ok, m = self.world.guild_join(msg.get("name", ""), conn.pid)
            conn.send(NetProtocol.make("guild_result", ok=ok, msg=m))

        elif mtype == "trade_offer":
            tid = self.world.open_trade(conn.pid, msg.get("target_pid"),
                                        msg.get("give", []), msg.get("want_gold", 0))
            with self.clients_lock:
                target = self.clients.get(msg.get("target_pid"))
            if target:
                target.send(NetProtocol.make("trade_offer", pid=conn.pid, trade_id=tid,
                                             give=msg.get("give", []), want_gold=msg.get("want_gold", 0)))
            conn.send(NetProtocol.make("trade_opened", trade_id=tid))

        elif mtype == "ping":
            conn.send(NetProtocol.make("pong", pid=conn.pid))

        elif mtype == "state_sync":
            # сервер ограничивает присланные статы потолками
            hero = msg.get("hero", {})
            corrections = {}
            for stat, max_val in MAX_STATS.items():
                if stat in hero and hero[stat] > max_val:
                    corrections[stat] = max_val
            if corrections:
                log_cheat(conn.name, f"state_sync clamp: {list(corrections)}")
                conn.send(NetProtocol.make("state_correction", fields=corrections))

        else:
            conn.send(NetProtocol.make("error", code="unknown_type", msg=str(mtype)))


# ==================== КЛИЕНТ ====================
class GameClient:
    def __init__(self, host, port=DEFAULT_PORT, name="player"):
        self.host = host
        self.port = port
        self.name = name
        self.sock = None
        self.pid = None
        self.seed = 0
        self.inbox = queue.Queue()
        self.buffer = ""
        self.alive = False
        self._seq = 0

    def connect(self, hero=None):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.alive = True
        threading.Thread(target=self._recv_loop, daemon=True).start()
        hello = NetProtocol.make(
            "hello", name=self.name,
            class_id=getattr(hero, "class_id", 0),
            level=getattr(hero, "level", 1),
            attack=getattr(hero, "attack", 10),
        )
        self.send(hello)

    def _recv_loop(self):
        while self.alive:
            try:
                chunk = self.sock.recv(4096)
            except OSError:
                break
            if not chunk:
                break
            self.buffer += chunk.decode("utf-8", errors="replace")
            messages, self.buffer = NetProtocol.decode_stream(self.buffer)
            for msg in messages:
                if msg.get("type") == "welcome":
                    self.pid = msg.get("pid")
                    self.seed = msg.get("world_seed", 0)
                self.inbox.put(msg)
        self.alive = False

    def send(self, msg):
        self._seq += 1
        msg["seq"] = self._seq
        if self.pid is not None:
            msg["pid"] = self.pid
        try:
            self.sock.sendall(NetProtocol.encode(msg))
        except OSError:
            self.alive = False

    def poll(self):
        """Неблокирующе забрать входящие сообщения (для UI-потока)."""
        out = []
        while True:
            try:
                out.append(self.inbox.get_nowait())
            except queue.Empty:
                break
        return out

    def close(self):
        self.alive = False
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass


# ==================== ЗАГЛУШЁННЫЙ HERO ДЛЯ СЕРВЕРА ====================
def make_net_hero(v1):
    """Подкласс v1.Hero, который буферизует события вместо print(),
    чтобы вывод одного игрока не печатался в терминале другого."""

    class NetHero(v1.Hero):
        def __init__(self, *a, **kw):
            self.events = []
            super().__init__(*a, **kw)

        def _emit(self, text):
            self.events.append(text)

        def drain_events(self):
            ev, self.events = self.events, []
            return ev

    return NetHero


# ==================== ОРКЕСТРАТОР ====================
class DarkOfHemiV2:
    def __init__(self, args):
        self.args = args
        self.platform = detect_platform()
        self.mobile = is_mobile(args.mobile)
        self.ui = MobileUI(enabled=self.mobile)

    # --- режимы запуска ---
    def run_single(self):
        v1 = load_v1()
        if self.mobile:
            self.ui.banner(self.platform)
        else:
            print(f"[v2.0] Платформа: {self.platform} | Мобильный режим: {self.mobile}")
        self.ui.cleanup()
        game = v1.DarkOfHemi()
        game.loading_screen()
        game.main_menu()

    def run_server(self):
        load_v1()  # убедимся, что v1 доступен (общие данные мира)
        seed = self.args.seed if self.args.seed is not None else 12345
        server = GameServer(port=self.args.port, seed=seed)
        try:
            server.start()
        except KeyboardInterrupt:
            print("\n[server] Остановка...")
        finally:
            server.shutdown()

    def run_client(self):
        v1 = load_v1()
        name = self.args.name or f"Игрок-{self.platform}"
        client = GameClient(self.args.client, port=self.args.port, name=name)
        print(f"[client] Подключение к {self.args.client}:{self.args.port} как '{name}'...")
        try:
            client.connect()
        except OSError as e:
            print(f"[client] Не удалось подключиться: {e}")
            return
        # ждём welcome
        deadline = 0
        while client.pid is None and deadline < 50 and client.alive:
            for msg in client.poll():
                if msg.get("type") == "welcome":
                    print(f"[client] Подключено! pid={msg['pid']}, "
                          f"игроков онлайн: {len(msg.get('players', []))}, "
                          f"сид мира: {msg.get('world_seed')}")
            time.sleep(0.1)
            deadline += 1
        if client.pid is None:
            print("[client] Сервер не ответил.")
            client.close()
            return
        # простой интерактивный чат-цикл (демо мультиплеера)
        print("[client] Введите сообщение для чата, '/quit' для выхода.")
        self._client_chat_loop(client)
        client.close()

    def _client_chat_loop(self, client):
        import threading as _t

        def reader():
            while client.alive:
                for msg in client.poll():
                    t = msg.get("type")
                    if t == "chat":
                        print(f"  💬 {msg.get('name')}: {msg.get('text')}")
                    elif t == "join":
                        print(f"  ➕ {msg.get('name')} присоединился")
                    elif t == "leave":
                        print(f"  ➖ игрок {msg.get('pid')} вышел")
                    elif t == "kick":
                        print(f"  ⛔ Вы отключены: {msg.get('reason')}")
                        client.alive = False
                time.sleep(0.2)

        _t.Thread(target=reader, daemon=True).start()
        while client.alive:
            try:
                line = input()
            except (EOFError, KeyboardInterrupt):
                break
            if line.strip() == "/quit":
                break
            if line.strip():
                client.send(NetProtocol.make("chat", text=line.strip()))

    def dispatch(self):
        if self.args.server:
            return self.run_server()
        if self.args.client:
            return self.run_client()
        # по умолчанию — одиночная игра
        return self.run_single()


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="dark_of_hemi_v2.0.py",
        description="Dark of Hemi v2.0 — RPG с мобильным режимом, античитом и LAN-мультиплеером.",
    )
    p.add_argument("--single", action="store_true", help="Одиночная игра (по умолчанию)")
    p.add_argument("--mobile", action="store_true", help="Мобильный режим (упрощённый UI)")
    p.add_argument("--server", action="store_true", help="Запуск как LAN-сервер")
    p.add_argument("--client", metavar="IP", help="Подключиться к LAN-серверу по IP")
    p.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Порт (по умолчанию {DEFAULT_PORT})")
    p.add_argument("--name", default=None, help="Имя игрока (для мультиплеера)")
    p.add_argument("--seed", type=int, default=None, help="Сид процедурного мира (сервер)")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        DarkOfHemiV2(args).dispatch()
    except KeyboardInterrupt:
        print("\nВыход.")
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"\n[ОШИБКА] {e}")
        import traceback
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
