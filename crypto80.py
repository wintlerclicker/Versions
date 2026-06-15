#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
crypto80 — 80-слойный шифратор/дешифратор для Dark of Hemi.

Развитие v1 UltraSecureCrypto (30 слоёв) до 80 слоёв с:
  * пер-слойным ключом (HKDF-подобный вывод через HMAC-SHA256),
  * чередованием обратимых преобразований (XOR / rotate / reverse / swap),
  * сжатием zlib и кодированием base85,
  * солью (16 байт) на каждое сообщение,
  * HMAC-SHA256 печатью целостности (детект подмены).

Использование как библиотеки:
    from crypto80 import Crypto80
    token = Crypto80.encrypt("секрет", password="pw")
    text  = Crypto80.decrypt(token, password="pw")

Как CLI:
    python3 crypto80.py encrypt -i save.json -o save.enc --password pw
    python3 crypto80.py decrypt -i save.enc  -o save.json --password pw
    echo "привет" | python3 crypto80.py encrypt --password pw
"""

import os
import sys
import zlib
import hmac
import json
import base64
import hashlib
import argparse

LAYERS = 80
_MAGIC = b"DOH80\x00"          # маркер формата
_BASE_SECRET = b"DarkOfHemi-v2.0-Crypto80-Master-Secret"


class Crypto80:
    # ---------- вывод ключей ----------
    @staticmethod
    def _derive_keys(password, salt, n=LAYERS):
        """Детерминированно вывести n пер-слойных ключей из пароля+соли.

        Используем PBKDF2 как корень + HMAC-цепочку для расширения — это
        повторяемо при дешифровке и зависит и от пароля, и от соли.
        """
        pw = (password or "").encode("utf-8")
        root = hashlib.pbkdf2_hmac("sha256", pw + _BASE_SECRET, salt, 100_000, dklen=32)
        keys = []
        prev = root
        for i in range(n):
            prev = hmac.new(root, prev + i.to_bytes(4, "big"), hashlib.sha256).digest()
            keys.append(prev)
        return keys, root

    # ---------- обратимые примитивы ----------
    @staticmethod
    def _xor(data, key):
        klen = len(key)
        return bytes(b ^ key[i % klen] for i, b in enumerate(data))

    @staticmethod
    def _rotl(data, n):
        if not data:
            return data
        n %= len(data)
        return data[n:] + data[:n]

    @staticmethod
    def _rotr(data, n):
        if not data:
            return data
        n %= len(data)
        return data[-n:] + data[:-n] if n else data

    @staticmethod
    def _swap_nibbles(data):
        return bytes(((b << 4) & 0xF0) | (b >> 4) for b in data)

    # ---------- один слой вперёд/назад (на сырых байтах, без расширения) ----------
    @classmethod
    def _forward_layer(cls, data, key, idx):
        """Один обратимый раунд перемешивания. Размер НЕ меняется (нет base85
        внутри цикла — иначе 1.25^80 → экспоненциальный взрыв и OOM)."""
        # 1) XOR пер-слойным ключом
        data = cls._xor(data, key)
        # 2) чередуем побайтовое преобразование по индексу слоя
        mode = idx % 4
        if mode == 0:
            data = cls._rotl(data, (key[0] % 7) + 1)
        elif mode == 1:
            data = cls._swap_nibbles(data)
        elif mode == 2:
            data = data[::-1]
        else:
            data = cls._rotr(data, (key[1] % 5) + 1)
        return data

    @classmethod
    def _backward_layer(cls, data, key, idx):
        mode = idx % 4
        if mode == 0:
            data = cls._rotr(data, (key[0] % 7) + 1)
        elif mode == 1:
            data = cls._swap_nibbles(data)   # инволюция
        elif mode == 2:
            data = data[::-1]
        else:
            data = cls._rotl(data, (key[1] % 5) + 1)
        data = cls._xor(data, key)
        return data

    # ---------- публичный API ----------
    @classmethod
    def encrypt(cls, text, password=""):
        """Зашифровать строку. Возвращает ASCII-токен (base85).

        Порядок: zlib(1 раз) → 80 раундов перемешивания → HMAC → base85(1 раз).
        Сжатие и кодирование выполняются однократно, поэтому размер линейный.
        """
        salt = os.urandom(16)
        keys, root = cls._derive_keys(password, salt)
        data = zlib.compress(text.encode("utf-8"), level=9)   # сжатие один раз
        for i in range(LAYERS):
            data = cls._forward_layer(data, keys[i], i)
        # печать целостности по зашифрованному телу
        tag = hmac.new(root, salt + data, hashlib.sha256).digest()
        envelope = _MAGIC + salt + tag + data
        return base64.b85encode(envelope).decode("ascii")    # кодирование один раз

    @classmethod
    def decrypt(cls, token, password=""):
        """Расшифровать токен. Бросает ValueError при подмене/неверном пароле."""
        try:
            envelope = base64.b85decode(token.encode("ascii"))
        except Exception as e:  # noqa: BLE001
            raise ValueError("Некорректный токен (не base85).") from e
        if not envelope.startswith(_MAGIC):
            raise ValueError("Неверный формат (нет маркера DOH80).")
        off = len(_MAGIC)
        salt = envelope[off:off + 16]
        tag = envelope[off + 16:off + 48]
        body = envelope[off + 48:]
        keys, root = cls._derive_keys(password, salt)
        expected = hmac.new(root, salt + body, hashlib.sha256).digest()
        if not hmac.compare_digest(tag, expected):
            raise ValueError("Целостность нарушена: неверный пароль или подмена данных.")
        data = body
        for i in range(LAYERS - 1, -1, -1):
            data = cls._backward_layer(data, keys[i], i)
        return zlib.decompress(data).decode("utf-8")          # распаковка один раз


# ==================== CLI ====================
def _read_input(args):
    if args.input:
        with open(args.input, "rb") as f:
            return f.read().decode("utf-8")
    return sys.stdin.read()


def _write_output(args, text):
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"[crypto80] Записано в {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="crypto80.py",
        description="80-слойный шифратор/дешифратор Dark of Hemi.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("encrypt", "decrypt"):
        sp = sub.add_parser(name, help=f"{name} данные")
        sp.add_argument("-i", "--input", help="Входной файл (иначе stdin)")
        sp.add_argument("-o", "--output", help="Выходной файл (иначе stdout)")
        sp.add_argument("-p", "--password", default="", help="Пароль (опционально)")

    args = p.parse_args(argv)
    try:
        data = _read_input(args)
        if args.cmd == "encrypt":
            _write_output(args, Crypto80.encrypt(data.rstrip("\n"), args.password))
        else:
            _write_output(args, Crypto80.decrypt(data.strip(), args.password))
    except ValueError as e:
        print(f"[crypto80][ОШИБКА] {e}", file=sys.stderr)
        return 2
    except OSError as e:
        print(f"[crypto80][ОШИБКА ФАЙЛА] {e}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
