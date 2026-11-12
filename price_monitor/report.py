"""Зведена таблиця цін і вивантаження: Excel, HTML, Google Sheets."""

import html
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

log = logging.getLogger(__name__)

RED = "FFE3E3"     # ціна виросла
GREEN = "E2F6E5"   # ціна впала
BEST = "FFF4CC"    # найдешевша пропозиція


def build_table(groups, storage, run_at, stores, threshold):
    """Рядок = товар, колонки = магазини. Додатково рахуємо зміни відносно минулого запуску."""
    rows, changes = [], []

    for g in groups:
        row = {"Товар": g["title"]}
        for offer in g["offers"]:
            row[offer.store] = offer.price
            prev = storage.previous_price(g["key"], offer.store, run_at)
            if prev and abs(offer.price - prev) / prev * 100 >= threshold:
                changes.append({
                    "product": g["title"],
                    "store": offer.store,
                    "old": prev,
                    "new": offer.price,
                    "diff_pct": round((offer.price - prev) / prev * 100, 1),
                })
        rows.append(row)

    df = pd.DataFrame(rows).reindex(columns=["Товар", *stores])
    df["Мін. ціна"] = df[stores].min(axis=1)
    df["Де дешевше"] = df[stores].idxmin(axis=1)
    df["Магазинів"] = df[stores].notna().sum(axis=1)
    df = df.sort_values(["Магазинів", "Товар"], ascending=[False, True]).reset_index(drop=True)
    return df, changes


def _change_map(changes):
    return {(c["product"], c["store"]): c for c in changes}


def save_excel(df, changes, stores, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    change_map = _change_map(changes)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Ціни", index=False)
        pd.DataFrame(changes or [], columns=["product", "store", "old", "new", "diff_pct"]).rename(columns={
            "product": "Товар", "store": "Магазин", "old": "Було", "new": "Стало", "diff_pct": "Зміна, %",
        }).to_excel(writer, sheet_name="Зміни", index=False)

        ws = writer.sheets["Ціни"]
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center")

        for r, record in enumerate(df.itertuples(index=False), start=2):
            product = record[0]
            for c, store in enumerate(stores, start=2):
                cell = ws.cell(row=r, column=c)
                cell.number_format = "# ##0"
                change = change_map.get((product, store))
                if change:
                    cell.fill = PatternFill("solid", fgColor=RED if change["diff_pct"] > 0 else GREEN)
                elif cell.value is not None and cell.value == record[len(stores) + 1]:
                    cell.fill = PatternFill("solid", fgColor=BEST)

        ws.column_dimensions["A"].width = 46
        for col in range(2, ws.max_column + 1):
            ws.column_dimensions[get_column_letter(col)].width = 14
        ws.freeze_panes = "B2"

    log.info("Excel: %s", path)


def save_html(df, changes, stores, path: Path):
    """Простий HTML-звіт, який зручно відкрити з телефона або скинути клієнту."""
    change_map = _change_map(changes)

    def cell(product, store, value, best):
        if pd.isna(value):
            return '<td class="empty">—</td>'
        css, note = "", ""
        if (ch := change_map.get((product, store))):
            css = "up" if ch["diff_pct"] > 0 else "down"
            note = f'<small>{ch["diff_pct"]:+.1f}%</small>'
        elif value == best:
            css = "best"
        return f'<td class="{css}">{value:,.0f}{note}</td>'.replace(",", " ")

    body = []
    for rec in df.to_dict("records"):
        product = rec["Товар"]
        tds = "".join(cell(product, s, rec[s], rec["Мін. ціна"]) for s in stores)
        body.append(f"<tr><th>{html.escape(product)}</th>{tds}<td>{html.escape(str(rec['Де дешевше']))}</td></tr>")

    ups = sum(1 for c in changes if c["diff_pct"] > 0)
    downs = len(changes) - ups
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    page = f"""<!doctype html>
<html lang="uk"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Моніторинг цін — {now}</title>
<style>
  body {{ font: 14px/1.4 system-ui, sans-serif; margin: 24px; color: #1f2937; background: #f8fafc; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  .meta {{ color: #64748b; margin-bottom: 18px; }}
  .stats {{ display: flex; gap: 12px; margin-bottom: 18px; }}
  .stat {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 10px 16px; }}
  .stat b {{ display: block; font-size: 22px; }}
  table {{ border-collapse: collapse; background: #fff; width: 100%; border: 1px solid #e2e8f0; }}
  th, td {{ padding: 8px 12px; border-bottom: 1px solid #eef2f7; text-align: right; white-space: nowrap; }}
  thead th {{ background: #1e293b; color: #fff; position: sticky; top: 0; }}
  thead th:first-child {{ text-align: left; }}
  tbody th {{ text-align: left; font-weight: 500; white-space: normal; }}
  td small {{ display: block; font-size: 11px; }}
  .up {{ background: #ffe3e3; color: #b91c1c; }}
  .down {{ background: #e2f6e5; color: #15803d; }}
  .best {{ background: #fff4cc; font-weight: 600; }}
  .empty {{ color: #cbd5e1; text-align: center; }}
</style></head><body>
<h1>Моніторинг цін конкурентів</h1>
<div class="meta">Оновлено {now} · магазинів: {len(stores)}</div>
<div class="stats">
  <div class="stat"><b>{len(df)}</b>товарів</div>
  <div class="stat"><b style="color:#b91c1c">{ups}</b>подорожчали</div>
  <div class="stat"><b style="color:#15803d">{downs}</b>подешевшали</div>
</div>
<table><thead><tr><th>Товар</th>{"".join(f"<th>{html.escape(s)}</th>" for s in stores)}<th>Де дешевше</th></tr></thead>
<tbody>{"".join(body)}</tbody></table>
</body></html>"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8")
    log.info("HTML: %s", path)


def upload_to_sheets(df, changes, settings):
    """Перезаписує аркуш "Ціни" у Google-таблиці і підсвічує змінені клітинки."""
    import gspread

    gc = gspread.service_account(filename=settings["credentials"])
    sh = gc.open(settings["spreadsheet"])
    try:
        ws = sh.worksheet("Ціни")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet("Ціни", rows=500, cols=20)

    data = df.fillna("").astype(object).values.tolist()
    ws.clear()
    ws.update([df.columns.tolist(), *data])
    ws.format("1:1", {"textFormat": {"bold": True}})

    columns = df.columns.tolist()
    products = df["Товар"].tolist()
    for ch in changes:
        row = products.index(ch["product"]) + 2
        col = columns.index(ch["store"]) + 1
        color = {"red": 1, "green": 0.89, "blue": 0.89} if ch["diff_pct"] > 0 else {"red": 0.89, "green": 0.96, "blue": 0.9}
        ws.format(gspread.utils.rowcol_to_a1(row, col), {"backgroundColor": color})

    log.info("Google Sheets оновлено: %s", settings["spreadsheet"])
