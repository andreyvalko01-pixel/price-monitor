import re
from dataclasses import dataclass
from urllib.parse import urljoin

from selectolax.lexbor import LexborHTMLParser as HTMLParser

from .config import StoreConfig


@dataclass
class Offer:
    store: str
    title: str
    price: float
    url: str


def parse_price(text: str) -> float | None:
    """'12 999 ₴', '12999.00 грн', '12,999' -> 12999.0"""
    if not text:
        return None
    cleaned = text.replace("\xa0", " ").replace(" ", " ")
    match = re.search(r"\d[\d\s.,]*", cleaned)
    if not match:
        return None

    number = re.sub(r"\s", "", match.group())
    # кома як десятковий роздільник: "1299,50"
    if re.search(r",\d{2}$", number):
        number = number.replace(".", "").replace(",", ".")
    else:
        number = number.replace(",", "")
    # "12999.00" — ок, але "12.999" (крапка як роздільник тисяч) — ні
    if re.search(r"\.\d{3}$", number):
        number = number.replace(".", "")

    try:
        return float(number)
    except ValueError:
        return None


def parse_offers(html: str, store: StoreConfig) -> list[Offer]:
    tree = HTMLParser(html)
    offers = []

    for node in tree.css(store.item):
        title_node = node.css_first(store.title)
        price_node = node.css_first(store.price)
        if not title_node or not price_node:
            continue

        raw_price = price_node.attributes.get(store.price_attr) if store.price_attr else price_node.text()
        price = parse_price(raw_price or "")
        if price is None:
            continue

        link = ""
        if store.link and (link_node := node.css_first(store.link)):
            link = urljoin(store.url, link_node.attributes.get("href") or "")

        offers.append(Offer(store=store.name, title=title_node.text(strip=True), price=price, url=link))

    return offers
