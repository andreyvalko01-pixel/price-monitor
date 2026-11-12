import logging

import httpx

log = logging.getLogger(__name__)


def format_summary(df, changes, errors) -> str:
    lines = [f"📊 <b>Моніторинг цін</b>: {len(df)} товарів"]

    if changes:
        ups = sorted((c for c in changes if c["diff_pct"] > 0), key=lambda c: -c["diff_pct"])
        downs = sorted((c for c in changes if c["diff_pct"] < 0), key=lambda c: c["diff_pct"])
        lines.append(f"🔺 подорожчали: {len(ups)} · 🔻 подешевшали: {len(downs)}")
        lines.append("")
        # у повідомленні тільки топ змін, решта — у звіті
        for c in (downs[:5] + ups[:5]):
            arrow = "🔻" if c["diff_pct"] < 0 else "🔺"
            lines.append(f"{arrow} {c['product'][:40]} — {c['store']}: {c['old']:.0f} → {c['new']:.0f} ({c['diff_pct']:+.1f}%)")
    else:
        lines.append("Змін цін немає.")

    if errors:
        lines.append("")
        lines.append("⚠️ Не вдалося зібрати: " + ", ".join(errors))
    return "\n".join(lines)


def send_telegram(token: str, chat_id: str, text: str):
    resp = httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=15,
    )
    if resp.status_code != 200:
        log.error("Telegram відповів %s: %s", resp.status_code, resp.text)
