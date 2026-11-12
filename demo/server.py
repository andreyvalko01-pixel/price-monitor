"""Тестові "магазини" для локальної перевірки парсера без походів на реальні сайти.

    python demo/server.py            # ціни "сьогодні"
    python demo/server.py --day 2    # інший день — частина цін зміниться

Чотири магазини з різною розміткою, один (GadgetHub) малює каталог через JavaScript.
"""

import argparse
import json
import random
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# (назва в магазині, базова ціна) — у кожного магазину свої формулювання
CATALOG = {
    "technopark": [
        ("Смартфон Samsung Galaxy S24 8/128GB Onyx Black (SM-S921B)", 32999),
        ("Навушники Sony WH-1000XM5 Black", 13999),
        ("Apple AirPods Pro 2 USB-C", 9999),
        ("Смарт-годинник Apple Watch SE 40mm Midnight", 12599),
        ("Ноутбук Apple MacBook Air 13 M3 16/256GB", 49999),
        ("Портативна колонка JBL Flip 6 Black", 4999),
        ("Миша Logitech MX Master 3S Graphite", 4299),
    ],
    "elmart": [
        ("Samsung Galaxy S24 128 ГБ чорний", 33499),
        ("Sony WH-1000XM5 чорний", 13799),
        ("AirPods Pro 2 (USB-C)", 10199),
        ("Apple Watch SE 40 мм Midnight", 12399),
        ("JBL Flip 6 чорний", 4899),
        ("Google Pixel 8 128GB Obsidian", 27499),
    ],
    "gadgethub": [
        ("Galaxy S24 128GB Black Samsung", 32799),
        ("Sony WH-1000XM5", 14299),
        ("Apple AirPods Pro 2 USB-C", 9899),
        ("MacBook Air 13 M3 16GB 256GB", 48999),
        ("Logitech MX Master 3S", 4199),
        ("Google Pixel 8 128 GB", 26999),
    ],
    "smartik": [
        ("Samsung Galaxy S24 8/128Gb Black", 32899),
        ("Навушники бездротові Sony WH-1000XM5", 13999),
        ("Apple Watch SE 40mm", 12699),
        ("Apple MacBook Air 13 M3 16/256", 49499),
        ("JBL Flip 6", 5099),
        ("Logitech MX Master 3S графіт", 4399),
    ],
}


def prices_for_day(store: str, day: int):
    rnd = random.Random(f"{store}-{day}")
    result = []
    for title, base in CATALOG[store]:
        price = base
        if day > 0 and rnd.random() < 0.35:
            price = round(base * rnd.uniform(0.9, 1.08) / 10) * 10 - 1
        result.append((title, price))
    return result


def money(n):
    return f"{n:,}".replace(",", " ")


def page_technopark(items):
    cards = "".join(
        f'<div class="product"><a href="/p/{i}"><span class="product__name">{t}</span></a>'
        f'<span class="product__price">{money(p)} ₴</span></div>'
        for i, (t, p) in enumerate(items)
    )
    return f"<html><body><h1>TechnoPark</h1><div class='grid'>{cards}</div></body></html>"


def page_elmart(items):
    lis = "".join(
        f'<li class="item"><a href="/item?id={i}"><h3>{t}</h3></a><b data-price="{p}.00">{money(p)} грн</b></li>'
        for i, (t, p) in enumerate(items)
    )
    return f"<html><body><ul>{lis}</ul></body></html>"


def page_gadgethub(items):
    data = json.dumps([{"title": t, "price": p, "id": i} for i, (t, p) in enumerate(items)], ensure_ascii=False)
    # без JS сторінка порожня — звичайний HTTP-парсер нічого не знайде
    return f"""<html><body><div id="app">Завантаження…</div>
<script>
  const items = {data};
  setTimeout(() => {{
    document.getElementById('app').innerHTML = items.map(i =>
      `<div class="card"><a href="/g/${{i.id}}"><p class="card-title">${{i.title}}</p></a><p class="card-price">${{i.price.toLocaleString('uk-UA')}} UAH</p></div>`
    ).join('');
  }}, 300);
</script></body></html>"""


def page_smartik(items):
    rows = "".join(
        f'<tr class="row"><td class="name"><a href="/s/{i}">{t}</a></td><td class="cost">{p},00</td></tr>'
        for i, (t, p) in enumerate(items)
    )
    return f"<html><body><table>{rows}</table></body></html>"


PAGES = {
    "/technopark/catalog.html": ("technopark", page_technopark),
    "/elmart/list.html": ("elmart", page_elmart),
    "/gadgethub/index.html": ("gadgethub", page_gadgethub),
    "/smartik/products.html": ("smartik", page_smartik),
}


def make_handler(day):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in PAGES:
                self.send_error(404)
                return
            store, render = PAGES[self.path]
            body = render(prices_for_day(store, day)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    return Handler


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", type=int, default=0)
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    print(f"Демо-магазини на http://127.0.0.1:{args.port} (день {args.day})")
    ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(args.day)).serve_forever()
