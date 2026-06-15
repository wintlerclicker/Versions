#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_exe.py — собрать Dark of Hemi v2.0 в один исполняемый файл.

Использует PyInstaller. Работает на Windows (.exe), Linux (ELF) и macOS (Mach-O):
PyInstaller собирает под ТУ ОС, на которой запущен (кросс-компиляции нет —
для Windows .exe запускайте этот скрипт на Windows).

Особенность проекта: игра v1.1.0 лежит в файле "привет.txt" (не .py), поэтому
его нужно положить рядом с бинарником как data-файл (--add-data). Скрипт делает
это автоматически.

Запуск:
    python3 build_exe.py            # собрать onefile-бинарник
    python3 build_exe.py --clean    # пересобрать с нуля
    python3 build_exe.py --name MyGame
"""

import os
import sys
import shutil
import subprocess
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
ENTRY = os.path.join(HERE, "dark_of_hemi_v2.0.py")
V1 = os.path.join(HERE, "привет.txt")
CRYPTO = os.path.join(HERE, "crypto80.py")


def ensure_pyinstaller():
    try:
        import PyInstaller  # noqa: F401
        return True
    except ImportError:
        print("[build] PyInstaller не найден — устанавливаю...")
        rc = subprocess.call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        if rc != 0:
            print("[build][ОШИБКА] Не удалось установить PyInstaller.")
            print("                 Установите вручную: pip install pyinstaller")
            return False
        return True


def build(name, clean):
    if not os.path.exists(ENTRY):
        sys.exit(f"[build][ОШИБКА] нет {ENTRY}")
    if not os.path.exists(V1):
        sys.exit(f"[build][ОШИБКА] нет {V1} (игра v1.1.0)")

    # --add-data использует ';' на Windows и ':' на остальных ОС
    sep = ";" if os.name == "nt" else ":"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", name,
        "--console",
        # положить привет.txt и crypto80.py рядом внутрь бинарника
        "--add-data", f"{V1}{sep}.",
    ]
    if os.path.exists(CRYPTO):
        cmd += ["--add-data", f"{CRYPTO}{sep}."]
    if clean:
        cmd.append("--clean")
    cmd.append(ENTRY)

    print("[build] Команда:", " ".join(cmd))
    rc = subprocess.call(cmd, cwd=HERE)
    if rc != 0:
        sys.exit(f"[build][ОШИБКА] PyInstaller вернул код {rc}")

    out_dir = os.path.join(HERE, "dist")
    ext = ".exe" if os.name == "nt" else ""
    binary = os.path.join(out_dir, name + ext)
    print()
    print("=" * 50)
    if os.path.exists(binary):
        size = os.path.getsize(binary) / (1024 * 1024)
        print(f"[build] ГОТОВО: {binary} ({size:.1f} MB)")
    else:
        print(f"[build] Бинарник ожидается в {out_dir}/{name}{ext}")
    print("=" * 50)
    print("ВАЖНО: при запуске бинарник распакует привет.txt во временную папку")
    print("и загрузит её через importlib (см. _resolve_v1_path в коде).")


def main():
    p = argparse.ArgumentParser(description="Сборка Dark of Hemi v2.0 в исполняемый файл.")
    p.add_argument("--name", default="DarkOfHemi", help="Имя бинарника")
    p.add_argument("--clean", action="store_true", help="Пересобрать с нуля")
    args = p.parse_args()

    if not ensure_pyinstaller():
        sys.exit(1)
    build(args.name, args.clean)


if __name__ == "__main__":
    main()
