"""Зіставлення однакових товарів між магазинами.

Магазини пишуть назви по-різному:
    "Смартфон Samsung Galaxy S24 8/128GB Onyx Black (SM-S921B)"
    "Samsung Galaxy S24 128 ГБ чорний"
Тому спершу зводимо назву до набору значущих слів, а потім порівнюємо ці набори.
"""

import re

# слова, які не допомагають відрізнити один товар від іншого
STOP_WORDS = {
    "смартфон", "мобільний", "телефон", "навушники", "бездротові", "ноутбук", "планшет",
    "годинник", "смарт", "колонка", "портативна", "миша", "новий", "офіційний", "гарантія",
    "ua", "ucrf", "usb", "c",
}

# колір магазини вказують через раз, тому в ключ його не беремо
COLORS = {
    "чорний", "black", "onyx", "midnight", "obsidian", "графіт", "graphite",
    "білий", "white", "silver", "сріблястий", "синій", "blue", "зелений", "green",
}

# окремо вказана оперативка ("16GB 256GB") — лишаємо тільки накопичувач
RAM_SIZES = {"4gb", "6gb", "8gb", "12gb", "16gb", "18gb", "24gb", "32gb"}


def normalize(title: str) -> str:
    text = title.lower()
    text = re.sub(r"\(.*?\)", " ", text)                          # артикули в дужках
    text = re.sub(r"(\d+)\s*(?:gb|гб)\b", r"\1gb", text)
    text = re.sub(r"(\d+)\s*(?:tb|тб)\b", r"\1tb", text)
    text = re.sub(r"(\d+)\s*(?:mm|мм)\b", r"\1mm", text)
    text = re.sub(r"\b\d+(?:gb)?/(\d+)(?:gb)?\b", r"\1gb", text)  # "8/128gb", "16/256" -> "128gb"
    text = re.sub(r"[^\w\s]", " ", text)

    words = {
        w for w in text.split()
        if w not in STOP_WORDS and w not in COLORS and w not in RAM_SIZES
    }
    return " ".join(sorted(words))


def similarity(a: str, b: str) -> float:
    """Частка спільних слів відносно коротшої назви. Числа (модель, пам'ять) мають збігатися."""
    wa, wb = set(a.split()), set(b.split())
    if not wa or not wb:
        return 0.0

    nums_a = {w for w in wa if any(ch.isdigit() for ch in w)}
    nums_b = {w for w in wb if any(ch.isdigit() for ch in w)}
    if nums_a and nums_b and not (nums_a <= nums_b or nums_b <= nums_a):
        return 0.0

    return len(wa & wb) / min(len(wa), len(wb))


def group_offers(offers, threshold: float = 0.8):
    """Групує пропозиції з різних магазинів у товари. Повертає список груп."""
    groups: list[dict] = []

    for offer in sorted(offers, key=lambda o: len(o.title)):
        key = normalize(offer.title)
        best, best_score = None, 0.0

        for group in groups:
            # в одній групі не може бути двох пропозицій від одного магазину
            if offer.store in group["stores"]:
                continue
            score = similarity(key, group["key"])
            if score > best_score:
                best, best_score = group, score

        if best and best_score >= threshold:
            best["offers"].append(offer)
            best["stores"].add(offer.store)
        else:
            groups.append({"key": key, "title": offer.title, "offers": [offer], "stores": {offer.store}})

    return groups
