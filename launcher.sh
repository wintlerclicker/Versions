#!/usr/bin/env bash
# =============================================================
# Dark of Hemi v2.0 — Лаунчер для Linux и macOS
# =============================================================
# Находит Python 3, проверяет наличие игровых файлов и запускает
# игру в выбранном режиме. Поддерживает шифратор/дешифратор.
#
#   ./launcher.sh                 # меню
#   ./launcher.sh single          # одиночная игра
#   ./launcher.sh mobile          # мобильный режим
#   ./launcher.sh server          # LAN-сервер
#   ./launcher.sh client <IP>     # LAN-клиент
#   ./launcher.sh encrypt <file>  # зашифровать файл
#   ./launcher.sh decrypt <file>  # расшифровать файл
# =============================================================

set -euo pipefail

# Каталог скрипта (работает и при запуске по симлинку)
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
HERE="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"

GAME="$HERE/dark_of_hemi_v2.0.py"
CRYPTO="$HERE/crypto80.py"

# ---------- определить ОС ----------
OS="$(uname -s)"
case "$OS" in
  Linux*)  PLATFORM="Linux" ;;
  Darwin*) PLATFORM="macOS" ;;
  *)       PLATFORM="$OS" ;;
esac

# ---------- найти Python 3 ----------
find_python() {
  for py in python3 python; do
    if command -v "$py" >/dev/null 2>&1; then
      if "$py" -c 'import sys; sys.exit(0 if sys.version_info[0]==3 else 1)' 2>/dev/null; then
        echo "$py"; return 0
      fi
    fi
  done
  return 1
}

PYTHON="$(find_python || true)"
if [ -z "$PYTHON" ]; then
  echo "[ОШИБКА] Python 3 не найден. Установите его:" >&2
  echo "  Linux:  sudo apt install python3   (или dnf/pacman)" >&2
  echo "  macOS:  brew install python3       (или с python.org)" >&2
  exit 1
fi

if [ ! -f "$GAME" ]; then
  echo "[ОШИБКА] Не найден $GAME" >&2
  exit 1
fi

banner() {
  echo "============================================="
  echo " DARK OF HEMI v2.0 — Лаунчер ($PLATFORM)"
  echo " Python: $($PYTHON --version 2>&1)"
  echo "============================================="
}

run_game() { exec "$PYTHON" "$GAME" "$@"; }

run_crypto() {
  if [ ! -f "$CRYPTO" ]; then echo "[ОШИБКА] нет $CRYPTO" >&2; exit 1; fi
  exec "$PYTHON" "$CRYPTO" "$@"
}

# ---------- режим из аргумента ----------
MODE="${1:-menu}"
case "$MODE" in
  single)  run_game --single ;;
  mobile)  run_game --mobile ;;
  server)  shift; run_game --server "$@" ;;
  client)
    shift
    IP="${1:-127.0.0.1}"
    shift || true
    run_game --client "$IP" "$@"
    ;;
  encrypt)
    shift
    F="${1:?Укажите файл: ./launcher.sh encrypt <file>}"
    read -r -s -p "Пароль: " PW; echo
    run_crypto encrypt -i "$F" -o "$F.enc" --password "$PW"
    ;;
  decrypt)
    shift
    F="${1:?Укажите файл: ./launcher.sh decrypt <file>}"
    read -r -s -p "Пароль: " PW; echo
    OUT="${F%.enc}.dec"
    run_crypto decrypt -i "$F" -o "$OUT" --password "$PW"
    ;;
  menu)
    banner
    echo "Выберите режим:"
    echo "  1) Одиночная игра"
    echo "  2) Мобильный режим"
    echo "  3) LAN-сервер"
    echo "  4) LAN-клиент"
    echo "  5) Зашифровать файл"
    echo "  6) Расшифровать файл"
    echo "  0) Выход"
    printf "> "
    read -r choice
    case "$choice" in
      1) run_game --single ;;
      2) run_game --mobile ;;
      3) run_game --server ;;
      4) printf "IP сервера [127.0.0.1]: "; read -r ip; run_game --client "${ip:-127.0.0.1}" ;;
      5) printf "Файл: "; read -r f; read -r -s -p "Пароль: " PW; echo; run_crypto encrypt -i "$f" -o "$f.enc" --password "$PW" ;;
      6) printf "Файл: "; read -r f; read -r -s -p "Пароль: " PW; echo; run_crypto decrypt -i "$f" -o "${f%.enc}.dec" --password "$PW" ;;
      0) exit 0 ;;
      *) echo "Неверный выбор"; exit 1 ;;
    esac
    ;;
  -h|--help|help)
    banner
    grep -E '^#( |=)' "$0" | sed 's/^# \{0,1\}//'
    ;;
  *)
    echo "[ОШИБКА] Неизвестный режим: $MODE (см. ./launcher.sh --help)" >&2
    exit 1
    ;;
esac
