from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen.canvas import Canvas

from .config import REPORT_STORAGE_DIR
from .models import Account, Client, Liability, ReportRun, TrustAsset

PAGE_WIDTH, PAGE_HEIGHT = letter
BLUE = colors.HexColor("#005a97")
BLUE_DARK = colors.HexColor("#003f6f")
INK = colors.HexColor("#0f1f33")
MUTED = colors.HexColor("#53677f")
LINE = colors.HexColor("#d7e0ea")
SOFT_BLUE = colors.HexColor("#e8f2fb")
GREEN = colors.HexColor("#2f8a3c")
RED = colors.HexColor("#d94124")


def fmt_money(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.0f}"


def fmt_date(value: date | None) -> str:
    return value.strftime("%b %d, %Y") if value else "Not set"


def clean(text: str, max_len: int = 34) -> str:
    value = str(text or "")
    return value if len(value) <= max_len else f"{value[: max_len - 1]}..."


def set_font(canvas: Canvas, size: int = 10, bold: bool = False, color=INK) -> None:
    canvas.setFillColor(color)
    canvas.setFont("Helvetica-Bold" if bold else "Helvetica", size)


def draw_header(canvas: Canvas, client: Client, title: str, run: ReportRun, page_label: str) -> None:
    set_font(canvas, 20, True, BLUE)
    canvas.drawString(54, PAGE_HEIGHT - 60, "WealthPortal")
    set_font(canvas, 10, False, MUTED)
    canvas.drawRightString(PAGE_WIDTH - 54, PAGE_HEIGHT - 58, clean(client.household_name, 46))
    canvas.drawRightString(PAGE_WIDTH - 54, PAGE_HEIGHT - 73, f"{run.quarter} / {fmt_date(run.meeting_date)}")
    canvas.setStrokeColor(BLUE)
    canvas.setLineWidth(2.5)
    canvas.line(54, PAGE_HEIGHT - 88, PAGE_WIDTH - 54, PAGE_HEIGHT - 88)
    set_font(canvas, 24, True, BLUE)
    canvas.drawString(54, PAGE_HEIGHT - 128, title)
    set_font(canvas, 9, False, MUTED)
    canvas.drawRightString(PAGE_WIDTH - 54, PAGE_HEIGHT - 126, page_label)


def draw_metric(canvas: Canvas, x: float, y: float, width: float, label: str, value: str, color=INK) -> None:
    canvas.setStrokeColor(LINE)
    canvas.setFillColor(colors.white)
    canvas.rect(x, y, width, 72, stroke=True, fill=True)
    set_font(canvas, 8, True, MUTED)
    canvas.drawString(x + 12, y + 48, label.upper())
    set_font(canvas, 18, True, color)
    canvas.drawString(x + 12, y + 22, value)


def draw_section_title(canvas: Canvas, y: float, title: str) -> None:
    set_font(canvas, 12, True, BLUE_DARK)
    canvas.drawString(54, y, title.upper())
    canvas.setStrokeColor(LINE)
    canvas.line(54, y - 7, PAGE_WIDTH - 54, y - 7)


def draw_table(
    canvas: Canvas,
    x: float,
    y: float,
    headers: list[str],
    rows: list[list[str]],
    widths: list[float],
    row_height: int = 24,
) -> float:
    canvas.setFillColor(colors.HexColor("#eef2f6"))
    canvas.rect(x, y - row_height, sum(widths), row_height, stroke=False, fill=True)
    set_font(canvas, 8, True, INK)
    cursor_x = x
    for index, header in enumerate(headers):
        canvas.drawString(cursor_x + 6, y - 16, header)
        cursor_x += widths[index]

    y -= row_height
    set_font(canvas, 8, False, INK)
    for row_data in rows:
        canvas.setStrokeColor(LINE)
        canvas.line(x, y, x + sum(widths), y)
        cursor_x = x
        for index, value in enumerate(row_data):
            canvas.drawString(cursor_x + 6, y - 16, clean(value, 28))
            cursor_x += widths[index]
        y -= row_height
    canvas.setStrokeColor(LINE)
    canvas.rect(x, y, sum(widths), row_height * (len(rows) + 1), stroke=True, fill=False)
    return y - 10


def draw_note(canvas: Canvas, x: float, y: float, text: str) -> None:
    set_font(canvas, 9, False, MUTED)
    words = text.split()
    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if canvas.stringWidth(candidate, "Helvetica", 9) > PAGE_WIDTH - 108:
            canvas.drawString(x, y, line)
            y -= 13
            line = word
        else:
            line = candidate
    if line:
        canvas.drawString(x, y, line)


def generate_sacs_pdf(client: Client, run: ReportRun, snapshot: dict, output_path: Path) -> None:
    sacs = snapshot["sacs"]
    canvas = Canvas(str(output_path), pagesize=letter)
    draw_header(canvas, client, "SACS Cash Flow Summary", run, "Page 1 of 2")

    box_width = (PAGE_WIDTH - 132) / 3
    draw_metric(canvas, 54, PAGE_HEIGHT - 230, box_width, "Monthly Inflow", fmt_money(sacs["monthly_inflow"]), BLUE_DARK)
    draw_metric(canvas, 66 + box_width, PAGE_HEIGHT - 230, box_width, "Monthly Outflow", fmt_money(sacs["monthly_outflow"]), RED)
    draw_metric(canvas, 78 + box_width * 2, PAGE_HEIGHT - 230, box_width, "Excess Transfer", fmt_money(sacs["excess_transfer"]), GREEN)

    y = PAGE_HEIGHT - 285
    draw_section_title(canvas, y, "Private Reserve")
    y -= 44
    target = max(float(sacs["private_reserve_target"]), 1)
    fill = max(0, min(1, float(sacs["private_reserve_balance"]) / target))
    canvas.setFillColor(SOFT_BLUE)
    canvas.rect(54, y, PAGE_WIDTH - 108, 18, stroke=False, fill=True)
    canvas.setFillColor(GREEN)
    canvas.rect(54, y, (PAGE_WIDTH - 108) * fill, 18, stroke=False, fill=True)
    set_font(canvas, 10, True, INK)
    canvas.drawString(54, y - 20, f"{fmt_money(sacs['private_reserve_balance'])} of {fmt_money(sacs['private_reserve_target'])}")

    y -= 62
    rows = [
        ["Six months expenses", fmt_money(sacs["monthly_outflow"] * 6)],
        ["Deductibles", fmt_money(sacs["deductibles"])],
        ["Reserve target", fmt_money(sacs["private_reserve_target"])],
        ["Reserve gap", fmt_money(sacs["private_reserve_gap"])],
    ]
    draw_table(canvas, 54, y, ["Rule", "Value"], rows, [250, 170])
    draw_note(
        canvas,
        54,
        108,
        "SACS values are generated from report run inputs. Excess equals inflow minus outflow. "
        "Private reserve target equals six months of expenses plus deductibles.",
    )
    canvas.showPage()

    draw_header(canvas, client, "Reserve and Investment Context", run, "Page 2 of 2")
    draw_metric(canvas, 54, PAGE_HEIGHT - 230, box_width, "Private Reserve", fmt_money(run.private_reserve_balance), BLUE_DARK)
    draw_metric(canvas, 66 + box_width, PAGE_HEIGHT - 230, box_width, "Investment Balance", fmt_money(run.investment_account_balance), BLUE_DARK)
    draw_metric(canvas, 78 + box_width * 2, PAGE_HEIGHT - 230, box_width, "Reserve Target", fmt_money(sacs["private_reserve_target"]), GREEN)
    draw_section_title(canvas, PAGE_HEIGHT - 285, "Planning Notes")
    draw_note(canvas, 54, PAGE_HEIGHT - 326, run.notes or "No notes entered.")
    canvas.save()


def generate_tcc_pdf(
    client: Client,
    run: ReportRun,
    snapshot: dict,
    accounts: list[Account],
    liabilities: list[Liability],
    trust_assets: list[TrustAsset],
    output_path: Path,
) -> None:
    summary = snapshot["household"]
    retirement = [account for account in accounts if account.category == "retirement"][:12]
    non_retirement = [account for account in accounts if account.category != "retirement"][:6]
    canvas = Canvas(str(output_path), pagesize=letter)
    draw_header(canvas, client, "Total Client Capital", run, "TCC")

    box_width = (PAGE_WIDTH - 132) / 3
    draw_metric(canvas, 54, PAGE_HEIGHT - 230, box_width, "Retirement", fmt_money(summary["retirement_total"]), BLUE_DARK)
    draw_metric(canvas, 66 + box_width, PAGE_HEIGHT - 230, box_width, "Non-Retirement", fmt_money(summary["non_retirement_total"]), BLUE_DARK)
    draw_metric(canvas, 78 + box_width * 2, PAGE_HEIGHT - 230, box_width, "Trust Value", fmt_money(summary["trust_total"]), GREEN)

    y = PAGE_HEIGHT - 278
    draw_section_title(canvas, y, "Retirement Accounts")
    y = draw_table(
        canvas,
        54,
        y - 18,
        ["Owner", "Account", "Institution", "Balance"],
        [[item.owner, item.name, item.institution, fmt_money(item.balance)] for item in retirement] or [["", "No retirement accounts entered", "", ""]],
        [82, 168, 150, 88],
        21,
    )
    draw_section_title(canvas, y, "Non-Retirement Accounts")
    y = draw_table(
        canvas,
        54,
        y - 18,
        ["Owner", "Account", "Institution", "Balance"],
        [[item.owner, item.name, item.institution, fmt_money(item.balance)] for item in non_retirement] or [["", "No non-retirement accounts entered", "", ""]],
        [82, 168, 150, 88],
        21,
    )
    draw_section_title(canvas, y, "Trust Assets and Liabilities")
    trust_text = ", ".join(f"{item.name}: {fmt_money(item.value)}" for item in trust_assets) or "No trust assets entered"
    liability_text = ", ".join(f"{item.name}: {fmt_money(item.balance)}" for item in liabilities[:3]) or "No liabilities entered"
    y = draw_table(
        canvas,
        54,
        y - 18,
        ["Type", "Details"],
        [["Trust", trust_text], ["Liabilities", liability_text]],
        [92, 396],
        24,
    )
    draw_section_title(canvas, y, "Summary Totals")
    draw_table(
        canvas,
        54,
        y - 18,
        ["Total", "Value"],
        [
            ["Grand total before liabilities", fmt_money(summary["grand_total"])],
            ["Liabilities displayed separately", fmt_money(summary["liabilities_total"])],
            ["Net worth after liabilities", fmt_money(summary["net_worth_after_liabilities"])],
        ],
        [296, 192],
        24,
    )
    draw_note(
        canvas,
        54,
        52,
        "TCC grand total includes retirement, non-retirement, and trust values. "
        "Liabilities are displayed separately and are not subtracted from the TCC grand total.",
    )
    canvas.save()


def report_paths(client: Client, run: ReportRun) -> tuple[Path, Path]:
    safe_name = "".join(ch if ch.isalnum() else "_" for ch in client.household_name).strip("_")
    run_dir = REPORT_STORAGE_DIR / client.id / run.quarter.replace(" ", "_")
    run_dir.mkdir(parents=True, exist_ok=True)
    return (
        run_dir / f"{safe_name}_{run.quarter.replace(' ', '_')}_SACS.pdf",
        run_dir / f"{safe_name}_{run.quarter.replace(' ', '_')}_TCC.pdf",
    )


def file_size(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0
