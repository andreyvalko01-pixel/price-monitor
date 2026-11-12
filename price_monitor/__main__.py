"""Запуск: python -m price_monitor --config config.toml"""

import argparse
import logging
import sys
from datetime import datetime

from .config import load_config
from .fetchers import BrowserFetcher, FetchError, HttpFetcher
from .matching import group_offers
from .notify import format_summary, send_telegram
from .parser import parse_offers
from .report import build_table, save_excel, save_html, upload_to_sheets
from .storage import PriceStorage

log = logging.getLogger("price_monitor")


def collect(config):
    http = HttpFetcher(
        timeout=config.http.get("timeout", 20),
        retries=config.http.get("retries", 3),
        delay=config.http.get("delay", 1.5),
        proxies=config.http.get("proxies"),
    )

    offers, errors = [], []
    browser_stores = [s for s in config.stores if s.render == "browser"]
    http_stores = [s for s in config.stores if s.render != "browser"]

    for store in http_stores:
        try:
            found = parse_offers(http.get(store.url), store)
            log.info("%s: %d товарів", store.name, len(found))
            offers += found
        except FetchError as e:
            log.error(e)
            errors.append(store.name)

    # браузер запускаємо один раз на всі JS-магазини — це найповільніша частина
    if browser_stores:
        with BrowserFetcher(timeout=config.http.get("timeout", 30)) as browser:
            for store in browser_stores:
                try:
                    found = parse_offers(browser.get(store.url, wait_for=store.wait_for), store)
                    log.info("%s (browser): %d товарів", store.name, len(found))
                    offers += found
                except Exception as e:
                    log.error("%s: %s", store.name, e)
                    errors.append(store.name)

    return offers, errors


def main():
    parser = argparse.ArgumentParser(description="Моніторинг цін конкурентів")
    parser.add_argument("--config", default="config.toml")
    parser.add_argument("--no-notify", action="store_true", help="не надсилати повідомлення в Telegram")
    args = parser.parse_args()

    # у консолі Windows за замовчуванням cp1251, а в зведенні є емодзі
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    config = load_config(args.config)
    store_names = [s.name for s in config.stores]

    offers, errors = collect(config)
    if not offers:
        log.error("Нічого не зібрано, звіт не формую")
        return 1

    groups = group_offers(offers)
    storage = PriceStorage(config.database)
    run_at = storage.save_run(groups)
    df, changes = build_table(groups, storage, run_at, store_names, config.change_threshold)
    storage.close()

    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    save_excel(df, changes, store_names, config.report_dir / f"prices_{stamp}.xlsx")
    save_html(df, changes, store_names, config.report_dir / "latest.html")

    if config.google_sheets.get("enabled"):
        try:
            upload_to_sheets(df, changes, config.google_sheets)
        except Exception as e:
            log.error("Google Sheets: %s", e)

    summary = format_summary(df, changes, errors)
    print("\n" + summary.replace("<b>", "").replace("</b>", ""))

    if config.telegram.get("enabled") and not args.no_notify:
        send_telegram(config.telegram["token"], config.telegram["chat_id"], summary)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
