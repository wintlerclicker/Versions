#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
protection.py — дополнительные уровни защиты Dark of Hemi v2.0.

Поверх 80-слойного crypto80 и игрового античита добавляет:

  1. IntegrityGuard   — SHA-256 контроль целостности файлов игры (детект модов).
  2. AntiDebug        — детект отладчика/трассировки (sys.gettrace, audit hooks).
  3. EnvGuard         — детект подозрительного окружения (PYTHONINSPECT, frozen).
  4. SaveVault        — двойная защита сейвов: crypto80 + HMAC + привязка к "железу".
  5. RuntimeWatchdog  — периодическая проверка статов в фоне (детект инъекций памяти).
  6. LicenseToken     — оффлайн-токен запуска (опционально).

Это НЕ криптостойкая DRM (Python декомпилируется), а многослойный барьер,
поднимающий цену взлома. Все слои логируют срабатывания в cheaters.log.
"""

import os
import sys
import time
import hmac
import hashlib
import threading

# переиспользуем логгер читеров из основного модуля, если он загружен
try:
    from importlib import import_module
    _v2 = None
    for _name, _mod in list(sys.modules.items()):
        if getattr(_mod, "__file__", "") and _name not in ("protection",):
            if hasattr(_mod, "log_cheat") and hasattr(_mod, "CHEATERS_LOG"):
                _v2 = _mod
                break
except Exception:  # noqa: BLE001
    _v2 = None


def _log(who, reason):
    if _v2 is not None:
        _v2.log_cheat(who, reason)
    else:
        sys.stderr.write(f"[protection] {who} | {reason}\n")


_SECRET = b"DarkOfHemi-v2.0-Protection-Layer-Secret"


# ==================== 1. ЦЕЛОСТНОСТЬ ФАЙЛОВ ====================
class IntegrityGuard:
    """Проверка SHA-256 ключевых файлов против эталонного манифеста."""

    @staticmethod
    def file_hash(path):
        h = hashlib.sha256()
        try:
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
        except OSError:
            return None
        return h.hexdigest()

    @classmethod
    def build_manifest(cls, files, base_dir):
        """Сгенерировать манифест {относительный путь: sha256}."""
        manifest = {}
        for f in files:
            full = os.path.join(base_dir, f)
            digest = cls.file_hash(full)
            if digest:
                manifest[f] = digest
        return manifest

    @classmethod
    def verify(cls, manifest, base_dir, who="player"):
        """Вернуть список изменённых/отсутствующих файлов (пусто = OK)."""
        bad = []
        for f, expected in manifest.items():
            actual = cls.file_hash(os.path.join(base_dir, f))
            if actual != expected:
                bad.append(f)
        if bad:
            _log(who, f"integrity violation: {','.join(bad)}")
        return bad


# ==================== 2. АНТИ-ОТЛАДКА ====================
class AntiDebug:
    @staticmethod
    def is_traced():
        """True, если активен трассировщик/отладчик (pdb, профайлер и т.п.)."""
        if sys.gettrace() is not None:
            return True
        # известные модули отладчиков в памяти
        for mod in ("pdb", "pydevd", "bdb", "_pydevd_bundle"):
            if mod in sys.modules:
                return True
        return False

    @classmethod
    def check(cls, who="player"):
        if cls.is_traced():
            _log(who, "debugger/tracer detected")
            return False
        return True


# ==================== 3. ОКРУЖЕНИЕ ====================
class EnvGuard:
    SUSPICIOUS_ENV = ("PYTHONINSPECT", "PYTHONBREAKPOINT", "PYTHONTRACEMALLOC")

    @classmethod
    def check(cls, who="player"):
        flags = [e for e in cls.SUSPICIOUS_ENV if os.environ.get(e)]
        if os.environ.get("PYTHONBREAKPOINT") not in (None, "0", ""):
            pass
        if flags:
            _log(who, f"suspicious env: {','.join(flags)}")
            return False
        return True

    @staticmethod
    def is_frozen():
        return getattr(sys, "frozen", False)


# ==================== 4. ХРАНИЛИЩЕ СЕЙВОВ ====================
class SaveVault:
    """Сейвы: crypto80(80 слоёв) + HMAC + опциональная привязка к машине."""

    @staticmethod
    def _machine_id():
        """Грубый отпечаток машины (не PII): hostname + platform."""
        import platform
        raw = (platform.node() + "|" + platform.platform()).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]

    @classmethod
    def seal(cls, data_str, password="", bind_machine=False):
        """Зашифровать строку сейва. Возвращает токен."""
        from crypto80 import Crypto80
        pw = password
        if bind_machine:
            pw = password + "|" + cls._machine_id()
        token = Crypto80.encrypt(data_str, password=pw)
        # внешняя HMAC-печать поверх токена
        tag = hmac.new(_SECRET, token.encode("ascii"), hashlib.sha256).hexdigest()[:32]
        return f"{tag}:{token}"

    @classmethod
    def unseal(cls, sealed, password="", bind_machine=False, who="player"):
        """Расшифровать. Бросает ValueError при подмене."""
        from crypto80 import Crypto80
        if ":" not in sealed:
            _log(who, "save vault: malformed token")
            raise ValueError("Повреждённый сейв.")
        tag, token = sealed.split(":", 1)
        expected = hmac.new(_SECRET, token.encode("ascii"), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(tag, expected):
            _log(who, "save vault: outer HMAC mismatch")
            raise ValueError("Сейв изменён (внешняя печать).")
        pw = password
        if bind_machine:
            pw = password + "|" + cls._machine_id()
        return Crypto80.decrypt(token, password=pw)


# ==================== 5. ФОНОВЫЙ СТОРОЖ ====================
class RuntimeWatchdog:
    """Периодически проверяет статы героя на превышение потолков (детект cheat-engine)."""

    def __init__(self, hero, max_stats, who="player", interval=5.0):
        self.hero = hero
        self.max_stats = max_stats
        self.who = who
        self.interval = interval
        self._stop = threading.Event()
        self._thread = None

    def _loop(self):
        while not self._stop.wait(self.interval):
            for stat, cap in self.max_stats.items():
                val = getattr(self.hero, stat, None)
                if val is not None and val > cap:
                    _log(self.who, f"watchdog: {stat}={val} > {cap} (memory injection?)")
                    setattr(self.hero, stat, cap)

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self._stop.set()


# ==================== 6. ЛИЦЕНЗИОННЫЙ ТОКЕН ====================
class LicenseToken:
    """Оффлайн-токен запуска: подписанный срок действия (не сетевая DRM)."""

    @staticmethod
    def issue(user, valid_until_epoch):
        payload = f"{user}|{int(valid_until_epoch)}"
        sig = hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()[:32]
        return f"{payload}|{sig}"

    @staticmethod
    def verify(token, now_epoch, who="player"):
        try:
            user, until, sig = token.split("|")
        except ValueError:
            _log(who, "license: malformed token")
            return False
        payload = f"{user}|{until}"
        expected = hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(sig, expected):
            _log(who, "license: bad signature")
            return False
        if now_epoch > int(until):
            _log(who, "license: expired")
            return False
        return True


# ==================== АГРЕГАТОР ====================
class ProtectionSuite:
    """Запустить все статические проверки разом. Возвращает отчёт."""

    @staticmethod
    def run_all(base_dir=None, manifest=None, who="player"):
        base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        report = {
            "anti_debug": AntiDebug.check(who),
            "env": EnvGuard.check(who),
            "frozen": EnvGuard.is_frozen(),
            "integrity": True,
        }
        if manifest:
            bad = IntegrityGuard.verify(manifest, base_dir, who)
            report["integrity"] = not bad
            report["integrity_bad"] = bad
        report["ok"] = report["anti_debug"] and report["env"] and report["integrity"]
        return report


if __name__ == "__main__":
    # самопроверка
    here = os.path.dirname(os.path.abspath(__file__))
    files = ["dark_of_hemi_v2.0.py", "crypto80.py", "protection.py", "привет.txt"]
    files = [f for f in files if os.path.exists(os.path.join(here, f))]
    man = IntegrityGuard.build_manifest(files, here)
    print(f"[protection] Манифест целостности ({len(man)} файлов):")
    for f, h in man.items():
        print(f"  {h[:16]}…  {f}")
    rep = ProtectionSuite.run_all(here, man, who="self-test")
    print("[protection] Отчёт:", rep)
