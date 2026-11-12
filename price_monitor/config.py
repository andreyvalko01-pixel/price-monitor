import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class StoreConfig:
    name: str
    url: str
    item: str
    title: str
    price: str
    render: str = "http"
    link: str | None = None
    price_attr: str | None = None
    wait_for: str | None = None


@dataclass
class Config:
    database: Path
    report_dir: Path
    change_threshold: float
    http: dict
    telegram: dict
    google_sheets: dict
    stores: list[StoreConfig] = field(default_factory=list)


def load_config(path: str | Path) -> Config:
    with open(path, "rb") as f:
        raw = tomllib.load(f)

    general = raw.get("general", {})
    return Config(
        database=Path(general.get("database", "data/prices.sqlite")),
        report_dir=Path(general.get("report_dir", "reports")),
        change_threshold=float(general.get("change_threshold", 1.0)),
        http=raw.get("http", {}),
        telegram=raw.get("telegram", {}),
        google_sheets=raw.get("google_sheets", {}),
        stores=[StoreConfig(**s) for s in raw.get("stores", [])],
    )
