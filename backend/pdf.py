from datetime import date
from math import atan2, cos, sin
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

SACS_GREEN = colors.HexColor("#55b960")
SACS_GREEN_DARK = colors.HexColor("#22773a")
SACS_RED = colors.HexColor("#ef513c")
SACS_RED_DARK = colors.HexColor("#a62d1d")
SACS_BLUE = colors.HexColor("#4c8ed0")
SACS_NAVY = colors.HexColor("#173556")
SACS_LIGHT_BLUE = colors.HexColor("#b7d8ee")
SACS_ARROW_BLUE = colors.HexColor("#7e9ec0")
SACS_GOLD = colors.HexColor("#e5a82b")
SACS_PINK = colors.HexColor("#f3a6a9")


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
    canvas.drawString(54, PAGE_HEIGHT - 60, "Client Report Portal")
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


def draw_centered(canvas: Canvas, x: float, y: float, text: str, size: int = 10, bold: bool = False, color=INK) -> None:
    set_font(canvas, size, bold, color)
    canvas.drawCentredString(x, y, text)


def draw_sacs_header(canvas: Canvas, client: Client, run: ReportRun, show_client: bool = True) -> None:
    draw_centered(canvas, PAGE_WIDTH / 2, PAGE_HEIGHT - 42, "Simple Automated Cashflow System (SACS)", 17, True)
    if show_client:
        draw_centered(canvas, PAGE_WIDTH / 2, PAGE_HEIGHT - 76, clean(client.household_name, 48), 13, True)
    set_font(canvas, 8, False, MUTED)
    canvas.drawRightString(PAGE_WIDTH - 38, 28, f"{run.quarter} / {fmt_date(run.meeting_date)}")


def draw_arrow(
    canvas: Canvas,
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    color,
    width: float = 3,
    head_length: float = 14,
    head_width: float = 10,
    dashed: bool = False,
) -> None:
    angle = atan2(end_y - start_y, end_x - start_x)
    shaft_end_x = end_x - cos(angle) * head_length
    shaft_end_y = end_y - sin(angle) * head_length
    perp_x = -sin(angle) * head_width / 2
    perp_y = cos(angle) * head_width / 2

    canvas.saveState()
    canvas.setStrokeColor(color)
    canvas.setFillColor(color)
    canvas.setLineWidth(width)
    if dashed:
        canvas.setDash(4, 3)
    canvas.line(start_x, start_y, shaft_end_x, shaft_end_y)
    canvas.setDash()
    path = canvas.beginPath()
    path.moveTo(end_x, end_y)
    path.lineTo(shaft_end_x + perp_x, shaft_end_y + perp_y)
    path.lineTo(shaft_end_x - perp_x, shaft_end_y - perp_y)
    path.close()
    canvas.drawPath(path, stroke=1, fill=1)
    canvas.restoreState()


def draw_double_arrow(canvas: Canvas, start_x: float, start_y: float, end_x: float, end_y: float, color) -> None:
    draw_arrow(canvas, start_x, start_y, end_x, end_y, color, width=8, head_length=17, head_width=18)
    draw_arrow(canvas, end_x, end_y, start_x, start_y, color, width=8, head_length=17, head_width=18)


def draw_value_band(canvas: Canvas, center_x: float, center_y: float, width: float, height: float, value: str) -> None:
    canvas.setFillColor(colors.white)
    canvas.setStrokeColor(colors.HexColor("#d9e2eb"))
    canvas.roundRect(center_x - width / 2, center_y - height / 2, width, height, 1.5, stroke=True, fill=True)
    font_size = 13
    while canvas.stringWidth(value, "Helvetica", font_size) > width - 9 and font_size > 8:
        font_size -= 1
    draw_centered(canvas, center_x, center_y - 4, value, font_size, False, colors.HexColor("#9aa5ad"))


def draw_floor(canvas: Canvas, center_x: float, center_y: float, radius: float) -> None:
    y = center_y - radius + 26
    canvas.setStrokeColor(colors.HexColor("#202020"))
    canvas.setLineWidth(1.5)
    canvas.line(center_x - radius + 12, y + 8, center_x + radius - 12, y + 13)
    draw_centered(canvas, center_x, y - 4, "$1,000 Floor", 7, True, colors.HexColor("#1d1d1d"))


def draw_circle_node(canvas: Canvas, center_x: float, center_y: float, radius: float, fill_color, title: str, value: str) -> None:
    canvas.setFillColor(fill_color)
    canvas.setStrokeColor(colors.HexColor("#273647"))
    canvas.setLineWidth(2)
    canvas.circle(center_x, center_y, radius, stroke=True, fill=True)
    draw_centered(canvas, center_x, center_y + 36, title, 15, True, colors.white)
    draw_value_band(canvas, center_x, center_y - 2, radius * 1.18, 26, value)
    draw_floor(canvas, center_x, center_y, radius)


def draw_account_circle(
    canvas: Canvas,
    center_x: float,
    center_y: float,
    radius: float,
    fill_color,
    title_lines: list[str],
    value: str,
) -> None:
    canvas.setFillColor(fill_color)
    canvas.setStrokeColor(colors.HexColor("#273647"))
    canvas.setLineWidth(2)
    canvas.circle(center_x, center_y, radius, stroke=True, fill=True)
    title_y = center_y + 34
    for line in title_lines:
        draw_centered(canvas, center_x, title_y, line, 12, True, colors.white)
        title_y -= 26
    draw_value_band(canvas, center_x, center_y - 30, radius * 1.16, 24, value)


def draw_private_reserve_node(canvas: Canvas, center_x: float, center_y: float, radius: float, value: str) -> None:
    canvas.setFillColor(SACS_BLUE)
    canvas.setStrokeColor(colors.HexColor("#263b5f"))
    canvas.setLineWidth(2)
    canvas.circle(center_x, center_y, radius, stroke=True, fill=True)
    draw_centered(canvas, center_x, center_y + 48, "PRIVATE", 13, True, colors.white)
    draw_centered(canvas, center_x, center_y + 20, "RESERVE", 13, True, colors.white)
    draw_value_band(canvas, center_x, center_y - 8, radius * 1.1, 23, value)
    draw_piggy_bank(canvas, center_x, center_y - 44)


def draw_piggy_bank(canvas: Canvas, center_x: float, center_y: float) -> None:
    canvas.saveState()
    canvas.setFillColor(SACS_GOLD)
    canvas.setStrokeColor(SACS_GOLD)
    for offset_x, height in [(-35, 20), (-22, 30), (24, 32), (38, 20)]:
        canvas.roundRect(center_x + offset_x, center_y - 24, 10, height, 2, stroke=False, fill=True)
    for offset_x, offset_y, radius in [(-16, 23, 3), (-5, 32, 4), (8, 21, 3)]:
        canvas.circle(center_x + offset_x, center_y + offset_y, radius, stroke=False, fill=True)

    canvas.setFillColor(SACS_PINK)
    canvas.setStrokeColor(colors.HexColor("#cf6d73"))
    canvas.ellipse(center_x - 24, center_y - 14, center_x + 26, center_y + 18, stroke=True, fill=True)
    canvas.circle(center_x + 27, center_y + 5, 12, stroke=True, fill=True)
    canvas.setFillColor(colors.HexColor("#f7c4c5"))
    canvas.circle(center_x + 34, center_y + 4, 5, stroke=False, fill=True)
    canvas.setFillColor(colors.HexColor("#6e3d43"))
    canvas.circle(center_x + 24, center_y + 9, 1.4, stroke=False, fill=True)
    canvas.setStrokeColor(colors.HexColor("#cf6d73"))
    canvas.setLineWidth(2)
    canvas.line(center_x - 11, center_y - 14, center_x - 11, center_y - 22)
    canvas.line(center_x + 13, center_y - 14, center_x + 13, center_y - 22)
    canvas.line(center_x - 2, center_y + 18, center_x + 9, center_y + 25)
    canvas.restoreState()


def draw_papers_icon(canvas: Canvas, x: float, y: float) -> None:
    canvas.saveState()
    canvas.translate(x, y)
    canvas.rotate(-16)
    for offset in [0, 10, 20]:
        canvas.setFillColor(colors.HexColor("#f2f3f5"))
        canvas.setStrokeColor(colors.HexColor("#c7ccd2"))
        canvas.rect(offset, -offset / 2, 38, 54, stroke=True, fill=True)
        canvas.setStrokeColor(colors.HexColor("#9aa1aa"))
        canvas.line(offset + 8, 38 - offset / 2, offset + 30, 38 - offset / 2)
        canvas.line(offset + 8, 29 - offset / 2, offset + 30, 29 - offset / 2)
    canvas.restoreState()


def draw_income_arrow(canvas: Canvas) -> None:
    canvas.saveState()
    canvas.setFillColor(SACS_GREEN)
    canvas.setStrokeColor(colors.HexColor("#273647"))
    path = canvas.beginPath()
    path.moveTo(70, 655)
    path.lineTo(94, 634)
    path.lineTo(87, 628)
    path.lineTo(118, 607)
    path.lineTo(101, 644)
    path.lineTo(94, 638)
    path.lineTo(70, 659)
    path.close()
    canvas.drawPath(path, stroke=True, fill=True)
    canvas.restoreState()


def draw_sacs_page_one(canvas: Canvas, client: Client, run: ReportRun, sacs: dict) -> None:
    draw_sacs_header(canvas, client, run)
    inflow_x, flow_y, radius = 160, 568, 76
    outflow_x = 452
    reserve_x, reserve_y, reserve_radius = PAGE_WIDTH / 2, 330, 74
    excess = float(sacs["excess_transfer"])
    transfer_color = SACS_GREEN_DARK if excess >= 0 else SACS_RED_DARK

    set_font(canvas, 36, True, SACS_GREEN_DARK)
    canvas.drawString(34, PAGE_HEIGHT - 77, "$")
    set_font(canvas, 8, True, SACS_GREEN)
    canvas.drawString(26, PAGE_HEIGHT - 101, "Monthly inflow")
    canvas.drawString(26, PAGE_HEIGHT - 116, "Household sources")
    draw_income_arrow(canvas)

    draw_circle_node(canvas, inflow_x, flow_y, radius, SACS_GREEN, "INFLOW", fmt_money(sacs["monthly_inflow"]))
    draw_circle_node(canvas, outflow_x, flow_y, radius, SACS_RED, "OUTFLOW", fmt_money(sacs["monthly_outflow"]))

    draw_arrow(canvas, inflow_x + radius + 8, flow_y + 13, outflow_x - radius - 8, flow_y + 13, SACS_RED, 2.1, 15, 11)
    draw_centered(canvas, PAGE_WIDTH / 2, flow_y + 34, f"X = {fmt_money(sacs['monthly_outflow'])}/month", 8, True, SACS_RED_DARK)
    draw_centered(canvas, PAGE_WIDTH / 2, flow_y - 16, "Automated transfer on the 28th", 5, False, colors.HexColor("#303a44"))

    draw_papers_icon(canvas, PAGE_WIDTH - 126, PAGE_HEIGHT - 86)
    set_font(canvas, 7, True, colors.HexColor("#303a44"))
    canvas.drawString(PAGE_WIDTH - 105, PAGE_HEIGHT - 139, "X = Monthly")
    canvas.drawString(PAGE_WIDTH - 95, PAGE_HEIGHT - 150, "Expenses")
    canvas.setStrokeColor(colors.HexColor("#303a44"))
    canvas.setLineWidth(1.8)
    canvas.line(PAGE_WIDTH - 88, PAGE_HEIGHT - 153, PAGE_WIDTH - 88, flow_y)
    draw_arrow(canvas, PAGE_WIDTH - 88, flow_y, outflow_x + radius - 16, flow_y, colors.HexColor("#303a44"), 1.8, 10, 8)

    draw_arrow(canvas, inflow_x, flow_y - radius - 3, reserve_x - reserve_radius + 20, reserve_y + 28, SACS_ARROW_BLUE, 2.2, 17, 13)
    draw_centered(canvas, 214, 417, f"{fmt_money(excess)}/mo", 8, True, transfer_color)

    draw_private_reserve_node(canvas, reserve_x, reserve_y, reserve_radius, fmt_money(sacs["private_reserve_balance"]))
    draw_centered(canvas, PAGE_WIDTH / 2, reserve_y - reserve_radius - 34, "MONTHLY CASHFLOW", 10, True)


def draw_sacs_page_two(canvas: Canvas, client: Client, run: ReportRun, sacs: dict) -> None:
    draw_sacs_header(canvas, client, run, show_client=False)
    canvas.setStrokeColor(colors.HexColor("#a8b8ce"))
    canvas.setLineWidth(1.4)
    canvas.setDash(5, 5)
    canvas.line(PAGE_WIDTH / 2, PAGE_HEIGHT - 94, PAGE_WIDTH / 2, 435)
    canvas.setDash()

    left_x, right_x, center_y, radius = 205, 410, 564, 76
    draw_account_circle(canvas, left_x, center_y, radius, SACS_LIGHT_BLUE, ["FICA", "ACCOUNT"], fmt_money(sacs["private_reserve_target"]))
    draw_account_circle(canvas, right_x, center_y, radius, SACS_NAVY, ["INVESTMENT", "ACCOUNT"], f"{fmt_money(run.investment_account_balance)}+")
    draw_double_arrow(canvas, left_x + radius - 5, center_y, right_x - radius + 5, center_y, SACS_ARROW_BLUE)
    draw_centered(canvas, left_x, center_y - radius - 25, "6X Monthly Expenses + Deductibles", 7, False)
    draw_centered(canvas, right_x, center_y - radius - 25, "Remainder", 7, False)
    draw_centered(canvas, PAGE_WIDTH / 2, 112, "LONG TERM CASHFLOW", 10, True)
    draw_centered(canvas, PAGE_WIDTH / 2, 82, "(Magnified Private Reserve Cashflow)", 10, True, SACS_BLUE)


def generate_sacs_pdf(client: Client, run: ReportRun, snapshot: dict, output_path: Path) -> None:
    sacs = snapshot["sacs"]
    canvas = Canvas(str(output_path), pagesize=letter)
    draw_sacs_page_one(canvas, client, run, sacs)
    canvas.showPage()
    draw_sacs_page_two(canvas, client, run, sacs)
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
