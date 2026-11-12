import pytest

from price_monitor.config import StoreConfig
from price_monitor.matching import group_offers, normalize
from price_monitor.parser import Offer, parse_offers, parse_price


@pytest.mark.parametrize("raw, expected", [
    ("12 999 ₴", 12999),
    ("12\xa0999 грн", 12999),
    ("12999.00", 12999),
    ("1299,50", 1299.5),
    ("12,999", 12999),
    ("12.999 UAH", 12999),
    ("ціна за запитом", None),
])
def test_parse_price(raw, expected):
    assert parse_price(raw) == expected


def test_normalize_ignores_noise():
    a = normalize("Смартфон Samsung Galaxy S24 8/128GB Onyx Black (SM-S921B)")
    b = normalize("Samsung Galaxy S24 128 ГБ чорний")
    assert a == b


def test_group_offers_matches_same_product():
    offers = [
        Offer("A", "Навушники Sony WH-1000XM5 Black", 13999, ""),
        Offer("B", "Sony WH-1000XM5 чорний", 13799, ""),
        Offer("C", "Apple AirPods Pro 2 USB-C", 9899, ""),
    ]
    groups = group_offers(offers)
    assert len(groups) == 2
    sony = next(g for g in groups if "sony" in g["key"])
    assert sony["stores"] == {"A", "B"}


def test_same_store_never_grouped_twice():
    offers = [
        Offer("A", "Apple Watch SE 40mm", 12599, ""),
        Offer("A", "Apple Watch SE 40mm Midnight", 12599, ""),
    ]
    assert len(group_offers(offers)) == 2


def test_parse_offers_with_attribute_price():
    html = '<ul><li class="item"><a href="/x"><h3>JBL Flip 6</h3></a><b data-price="4899.00">4 899</b></li></ul>'
    store = StoreConfig(name="Elmart", url="https://shop.ua/list", item="li.item", title="h3",
                        price="[data-price]", price_attr="data-price", link="a")
    [offer] = parse_offers(html, store)
    assert offer.price == 4899
    assert offer.url == "https://shop.ua/x"
