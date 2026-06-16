#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой монитор потенциального крипто-арбитража.

Что делает:
  * запрашивает публичные bid/ask цены у нескольких бирж;
  * ищет, где дешевле купить и где дороже продать;
  * считает грубый спред до комиссий и после учёта комиссии.

Что НЕ делает:
  * не торгует автоматически;
  * не хранит API-ключи;
  * не переводит деньги между биржами;
  * не гарантирует прибыль.

Примеры:
    python3 arbitrage_monitor.py
    python3 arbitrage_monitor.py --symbols BTCUSDT ETHUSDT
    python3 arbitrage_monitor.py --watch --interval 15 --min-net 0.5
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional


USER_AGENT = "arbitrage-monitor/1.0"
DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
DEFAULT_EXCHANGES = ["okx", "kucoin", "gateio", "mexc"]


@dataclass
class Quote:
    exchange: str
    symbol: str
    bid: float
    ask: float


@dataclass
class Opportunity:
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    gross_percent: float
    net_percent: float


@dataclass
class TradeEstimate:
    capital_rub: float
    usd_rub_rate: float
    start_usdt: float
    coin_amount: float
    end_usdt: float
    end_rub: float
    profit_rub: float
    total_cost_percent: float


def fetch_json(url: str, timeout: float = 10.0) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_usd_rub_rate() -> float:
    payload = fetch_json("https://www.cbr-xml-daily.ru/daily_json.js")
    usd = payload["Valute"]["USD"]["Value"]
    if usd <= 0:
        raise ValueError("ЦБ РФ вернул некорректный курс USD/RUB")
    return float(usd)


def fetch_binance(symbol: str) -> Quote:
    payload = fetch_json(
        f"https://api.binance.com/api/v3/ticker/bookTicker?symbol={urllib.parse.quote(symbol)}"
    )
    return Quote(
        exchange="Binance",
        symbol=symbol,
        bid=float(payload["bidPrice"]),
        ask=float(payload["askPrice"]),
    )


def fetch_bybit(symbol: str) -> Quote:
    payload = fetch_json(
        "https://api.bybit.com/v5/market/tickers"
        f"?category=spot&symbol={urllib.parse.quote(symbol)}"
    )
    row = payload["result"]["list"][0]
    return Quote(
        exchange="Bybit",
        symbol=symbol,
        bid=float(row["bid1Price"]),
        ask=float(row["ask1Price"]),
    )


def fetch_okx(symbol: str) -> Quote:
    inst_id = symbol.replace("USDT", "-USDT")
    payload = fetch_json(
        f"https://www.okx.com/api/v5/market/ticker?instId={urllib.parse.quote(inst_id)}"
    )
    row = payload["data"][0]
    return Quote(
        exchange="OKX",
        symbol=symbol,
        bid=float(row["bidPx"]),
        ask=float(row["askPx"]),
    )


def fetch_kucoin(symbol: str) -> Quote:
    pair = symbol.replace("USDT", "-USDT")
    payload = fetch_json(
        "https://api.kucoin.com/api/v1/market/orderbook/level1"
        f"?symbol={urllib.parse.quote(pair)}"
    )
    row = payload["data"]
    return Quote(
        exchange="KuCoin",
        symbol=symbol,
        bid=float(row["bestBid"]),
        ask=float(row["bestAsk"]),
    )


def fetch_gateio(symbol: str) -> Quote:
    pair = symbol.replace("USDT", "_USDT")
    payload = fetch_json(
        "https://api.gateio.ws/api/v4/spot/tickers"
        f"?currency_pair={urllib.parse.quote(pair)}"
    )
    row = payload[0]
    return Quote(
        exchange="Gate.io",
        symbol=symbol,
        bid=float(row["highest_bid"]),
        ask=float(row["lowest_ask"]),
    )


def fetch_mexc(symbol: str) -> Quote:
    payload = fetch_json(
        f"https://api.mexc.com/api/v3/ticker/bookTicker?symbol={urllib.parse.quote(symbol)}"
    )
    return Quote(
        exchange="MEXC",
        symbol=symbol,
        bid=float(payload["bidPrice"]),
        ask=float(payload["askPrice"]),
    )


EXCHANGES: Dict[str, Callable[[str], Quote]] = {
    "bybit": fetch_bybit,
    "binance": fetch_binance,
    "gateio": fetch_gateio,
    "kucoin": fetch_kucoin,
    "mexc": fetch_mexc,
    "okx": fetch_okx,
}


def fetch_quotes(symbol: str, exchanges: Iterable[str]) -> List[Quote]:
    quotes: List[Quote] = []
    for exchange_name in exchanges:
        fetcher = EXCHANGES[exchange_name]
        try:
            quote = fetcher(symbol)
        except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError) as exc:
            print(
                f"[WARN] {symbol}: не удалось получить котировку с {exchange_name}: {exc}",
                file=sys.stderr,
            )
            continue
        if quote.bid <= 0 or quote.ask <= 0:
            print(
                f"[WARN] {symbol}: {exchange_name} вернул некорректную цену bid/ask",
                file=sys.stderr,
            )
            continue
        quotes.append(quote)
    return quotes


def find_opportunity(symbol: str, quotes: List[Quote], fee_percent: float) -> Optional[Opportunity]:
    if len(quotes) < 2:
        return None

    cheapest = min(quotes, key=lambda item: item.ask)
    richest = max(quotes, key=lambda item: item.bid)

    if cheapest.exchange == richest.exchange:
        return None

    gross_percent = ((richest.bid - cheapest.ask) / cheapest.ask) * 100
    net_percent = gross_percent - (fee_percent * 2)

    return Opportunity(
        symbol=symbol,
        buy_exchange=cheapest.exchange,
        sell_exchange=richest.exchange,
        buy_price=cheapest.ask,
        sell_price=richest.bid,
        gross_percent=gross_percent,
        net_percent=net_percent,
    )


def print_quotes(symbol: str, quotes: List[Quote]) -> None:
    print(f"\n[{symbol}] Котировки")
    for quote in sorted(quotes, key=lambda item: item.ask):
        print(
            f"  {quote.exchange:<7} buy ask={quote.ask:>12.6f} | sell bid={quote.bid:>12.6f}"
        )


def estimate_trade(
    opportunity: Opportunity,
    capital_rub: float,
    usd_rub_rate: float,
    fee_percent: float,
    slippage_percent: float,
    transfer_fee_usdt: float,
) -> TradeEstimate:
    start_usdt = capital_rub / usd_rub_rate
    total_cost_percent = (fee_percent * 2) + slippage_percent
    tradable_usdt = max(start_usdt - transfer_fee_usdt, 0.0)
    coin_amount = tradable_usdt / opportunity.buy_price if opportunity.buy_price > 0 else 0.0
    end_usdt_before_sell_fee = coin_amount * opportunity.sell_price
    end_usdt = end_usdt_before_sell_fee * (1 - total_cost_percent / 100)
    end_rub = end_usdt * usd_rub_rate
    profit_rub = end_rub - capital_rub
    return TradeEstimate(
        capital_rub=capital_rub,
        usd_rub_rate=usd_rub_rate,
        start_usdt=start_usdt,
        coin_amount=coin_amount,
        end_usdt=end_usdt,
        end_rub=end_rub,
        profit_rub=profit_rub,
        total_cost_percent=total_cost_percent,
    )


def print_opportunity(
    opportunity: Opportunity,
    min_net: float,
    estimate: Optional[TradeEstimate] = None,
) -> None:
    marker = "SIGNAL" if opportunity.net_percent >= min_net else "INFO"
    print(
        f"[{marker}] {opportunity.symbol}: купить на {opportunity.buy_exchange} "
        f"по {opportunity.buy_price:.6f}, продать на {opportunity.sell_exchange} "
        f"по {opportunity.sell_price:.6f} | gross={opportunity.gross_percent:.3f}% "
        f"| net≈{opportunity.net_percent:.3f}%"
    )
    if estimate is not None:
        print(
            f"        старт={estimate.capital_rub:.2f} RUB (~{estimate.start_usdt:.2f} USDT) "
            f"| объём={estimate.coin_amount:.8f} | итог≈{estimate.end_rub:.2f} RUB "
            f"| прибыль≈{estimate.profit_rub:.2f} RUB"
        )


def print_manual_steps(opportunity: Opportunity, estimate: Optional[TradeEstimate]) -> None:
    print("        шаги:")
    print(f"        1. Пополнить {opportunity.buy_exchange} и купить {opportunity.symbol}.")
    print(f"        2. Перевести {opportunity.symbol} или эквивалент на {opportunity.sell_exchange}.")
    print(f"        3. Продать на {opportunity.sell_exchange} по рынку или лимитно.")
    print("        4. Проверить фактические комиссии, сеть вывода и ликвидность стакана.")
    if estimate is not None:
        print(
            f"        5. При текущей оценке ожидаемый результат: "
            f"{estimate.end_rub:.2f} RUB, profit≈{estimate.profit_rub:.2f} RUB."
        )


def append_report_row(
    report_file: str,
    opportunity: Opportunity,
    estimate: Optional[TradeEstimate],
) -> None:
    header = [
        "timestamp_utc",
        "symbol",
        "buy_exchange",
        "sell_exchange",
        "buy_price",
        "sell_price",
        "gross_percent",
        "net_percent",
        "capital_rub",
        "end_rub",
        "profit_rub",
    ]
    row = [
        time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        opportunity.symbol,
        opportunity.buy_exchange,
        opportunity.sell_exchange,
        f"{opportunity.buy_price:.8f}",
        f"{opportunity.sell_price:.8f}",
        f"{opportunity.gross_percent:.6f}",
        f"{opportunity.net_percent:.6f}",
        f"{estimate.capital_rub:.2f}" if estimate else "",
        f"{estimate.end_rub:.2f}" if estimate else "",
        f"{estimate.profit_rub:.2f}" if estimate else "",
    ]
    write_header = False
    try:
        with open(report_file, "r", encoding="utf-8", newline=""):
            pass
    except FileNotFoundError:
        write_header = True

    with open(report_file, "a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        if write_header:
            writer.writerow(header)
        writer.writerow(row)


def run_once(
    symbols: List[str],
    exchanges: List[str],
    fee_percent: float,
    min_net: float,
    capital_rub: Optional[float],
    usd_rub_rate: Optional[float],
    slippage_percent: float,
    transfer_fee_usdt: float,
    report_file: Optional[str],
) -> None:
    for symbol in symbols:
        quotes = fetch_quotes(symbol, exchanges)
        if not quotes:
            print(f"\n[{symbol}] Нет доступных котировок.")
            continue

        print_quotes(symbol, quotes)
        opportunity = find_opportunity(symbol, quotes, fee_percent)
        if opportunity is None:
            print(f"[INFO] {symbol}: данных для сравнения недостаточно.")
            continue

        estimate = None
        if capital_rub is not None and usd_rub_rate is not None:
            estimate = estimate_trade(
                opportunity,
                capital_rub=capital_rub,
                usd_rub_rate=usd_rub_rate,
                fee_percent=fee_percent,
                slippage_percent=slippage_percent,
                transfer_fee_usdt=transfer_fee_usdt,
            )

        print_opportunity(opportunity, min_net, estimate)
        print_manual_steps(opportunity, estimate)
        if report_file is not None:
            append_report_row(report_file, opportunity, estimate)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Монитор потенциального арбитражного спреда между биржами."
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=DEFAULT_SYMBOLS,
        help="Список тикеров, например: BTCUSDT ETHUSDT SOLUSDT",
    )
    parser.add_argument(
        "--exchanges",
        nargs="+",
        choices=sorted(EXCHANGES),
        default=DEFAULT_EXCHANGES,
        help="Биржи для сравнения.",
    )
    parser.add_argument(
        "--fee-percent",
        type=float,
        default=0.1,
        help="Комиссия одной стороны сделки в процентах. По умолчанию 0.1",
    )
    parser.add_argument(
        "--min-net",
        type=float,
        default=0.3,
        help="Минимальный net-spread в процентах для пометки SIGNAL.",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Повторять проверку по кругу.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=20,
        help="Пауза между циклами в режиме --watch, секунд.",
    )
    parser.add_argument(
        "--capital-rub",
        type=float,
        help="Стартовая сумма в рублях для оценки результата, например 1000.",
    )
    parser.add_argument(
        "--usd-rub-rate",
        type=float,
        help="Курс USD/RUB вручную. Если не указан, будет запрос к API ЦБ РФ.",
    )
    parser.add_argument(
        "--slippage-percent",
        type=float,
        default=0.15,
        help="Дополнительный запас на проскальзывание и скрытые издержки, в процентах.",
    )
    parser.add_argument(
        "--transfer-fee-usdt",
        type=float,
        default=1.0,
        help="Оценка стоимости перевода между биржами в USDT.",
    )
    parser.add_argument(
        "--report-file",
        help="CSV-файл для сохранения найденных сигналов.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    symbols = [symbol.upper() for symbol in args.symbols]
    usd_rub_rate = args.usd_rub_rate

    print("Монитор арбитража запущен.")
    print("Это рабочий полуавтомат: поиск связок, расчёт и инструкция для ручного исполнения.")

    if args.capital_rub is not None and usd_rub_rate is None:
        try:
            usd_rub_rate = fetch_usd_rub_rate()
        except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as exc:
            print(f"[WARN] Не удалось получить USD/RUB: {exc}", file=sys.stderr)
            print("[WARN] Укажите курс вручную через --usd-rub-rate", file=sys.stderr)
            usd_rub_rate = None

    if usd_rub_rate is not None:
        print(f"Курс USD/RUB для расчёта: {usd_rub_rate:.4f}")

    try:
        while True:
            print(f"\n=== Проверка {time.strftime('%Y-%m-%d %H:%M:%S')} UTC ===")
            run_once(
                symbols=symbols,
                exchanges=args.exchanges,
                fee_percent=args.fee_percent,
                min_net=args.min_net,
                capital_rub=args.capital_rub,
                usd_rub_rate=usd_rub_rate,
                slippage_percent=args.slippage_percent,
                transfer_fee_usdt=args.transfer_fee_usdt,
                report_file=args.report_file,
            )
            if not args.watch:
                break
            time.sleep(max(args.interval, 1))
    except KeyboardInterrupt:
        print("\nОстановлено пользователем.")
        return 130

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
