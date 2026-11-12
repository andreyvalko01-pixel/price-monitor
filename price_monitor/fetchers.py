"""Завантаження сторінок: звичайний HTTP або браузер для сайтів на JavaScript."""

import itertools
import logging
import random
import time
from urllib.parse import urlparse

import httpx

log = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0",
]

RETRY_STATUSES = {429, 500, 502, 503, 504}


class FetchError(Exception):
    pass


class HttpFetcher:
    def __init__(self, timeout=20, retries=3, delay=1.5, proxies=None):
        self.timeout = timeout
        self.retries = retries
        self.delay = delay
        # проксі беремо по колу; None — без проксі
        self._proxies = itertools.cycle(proxies or [None])
        self._last_request: dict[str, float] = {}

    def _wait_for_domain(self, url: str):
        """Не частимо запитами в один домен — інакше швидко отримаємо бан."""
        domain = urlparse(url).netloc
        passed = time.monotonic() - self._last_request.get(domain, 0)
        if passed < self.delay:
            time.sleep(self.delay - passed + random.uniform(0, 0.5))
        self._last_request[domain] = time.monotonic()

    def get(self, url: str) -> str:
        last_error = None

        for attempt in range(1, self.retries + 1):
            proxy = next(self._proxies)
            self._wait_for_domain(url)
            headers = {"User-Agent": random.choice(USER_AGENTS), "Accept-Language": "uk-UA,uk;q=0.9"}

            try:
                with httpx.Client(proxy=proxy, timeout=self.timeout, follow_redirects=True) as client:
                    resp = client.get(url, headers=headers)

                if resp.status_code in RETRY_STATUSES:
                    raise FetchError(f"HTTP {resp.status_code}")
                resp.raise_for_status()
                return resp.text

            except (httpx.HTTPError, FetchError) as e:
                last_error = e
                pause = 2 ** attempt
                log.warning("%s: спроба %d/%d не вдалась (%s), чекаю %ds", url, attempt, self.retries, e, pause)
                time.sleep(pause)

        raise FetchError(f"Не вдалося завантажити {url}: {last_error}")


class BrowserFetcher:
    """Відкриває сторінку в headless Chromium через Playwright і віддає готовий HTML."""

    def __init__(self, timeout=30):
        self.timeout = timeout * 1000
        self._pw = None
        self._browser = None

    def __enter__(self):
        from playwright.sync_api import sync_playwright  # імпорт тут, щоб без браузера все інше працювало

        self._pw = sync_playwright().start()
        try:
            self._browser = self._pw.chromium.launch(headless=True)
        except Exception:
            # якщо браузери Playwright не встановлені — пробуємо системний Chrome
            self._browser = self._pw.chromium.launch(headless=True, channel="chrome")
        return self

    def __exit__(self, *exc):
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()

    def get(self, url: str, wait_for: str | None = None) -> str:
        page = self._browser.new_page(user_agent=random.choice(USER_AGENTS))
        try:
            page.goto(url, timeout=self.timeout, wait_until="domcontentloaded")
            if wait_for:
                page.wait_for_selector(wait_for, timeout=self.timeout)
            return page.content()
        finally:
            page.close()
