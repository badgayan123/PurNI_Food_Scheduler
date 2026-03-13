"""PurNi Menu."""
import io
from contextlib import asynccontextmanager
from datetime import datetime, date, timedelta
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from odf.opendocument import OpenDocumentSpreadsheet
from odf.table import Table, TableRow, TableCell
from odf.text import P
from backend.database import get_db, init_db
from backend.models import Week, MenuItem
from backend.nutrition import get_nutrition

# Week/day constants
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MEAL_SLOTS = ["breakfast", "lunch", "dinner", "snack"]


def get_week_info(d: date) -> tuple[int, int, date]:
    """Return (year, week_number, monday) for a date."""
    monday = d - timedelta(days=d.weekday())
    year = monday.year
    week_num = monday.isocalendar()[1]
    return year, week_num, monday


def monday_for_week(year: int, week_number: int) -> date:
    """Get Monday date for given ISO year and week number."""
    d = datetime.strptime(f"{year}-W{week_number:02d}-1", "%G-W%V-%u").date()
    return d


def format_week_date_range(monday: date) -> str:
    """Format as 'Mon 9 Mar - Sun 15 Mar 2026' for clear date display."""
    sunday = monday + timedelta(days=6)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    mon_str = f"Mon {monday.day} {months[monday.month - 1]}"
    sun_str = f"Sun {sunday.day} {months[sunday.month - 1]}"
    if monday.year == sunday.year:
        return f"{mon_str} - {sun_str} {monday.year}"
    return f"{mon_str} - {sun_str} {monday.year}/{sunday.year}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="PurNi Menu", version="1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    """Quick check that server is running."""
    return {"ok": True, "message": "PurNi Menu is running"}


# --- Pydantic schemas ---
class MenuItemCreate(BaseModel):
    day: int
    meal_slot: str
    food_name: str
    serving_size: str = "1 serving"
    calories: float = 0
    protein: float = 0
    added_by: str = ""


class MenuItemUpdate(BaseModel):
    food_name: str | None = None
    serving_size: str | None = None
    calories: float | None = None
    protein: float | None = None


class MenuItemResponse(BaseModel):
    id: int
    day: int
    meal_slot: str
    food_name: str
    serving_size: str
    calories: float
    protein: float
    added_by: str

    class Config:
        from_attributes = True


# --- API: Week ---
def _week_response(week: Week, monday: date, items_map: dict) -> dict:
    """Build full week response with date_range and items."""
    return {
        "id": week.id,
        "year": week.year,
        "week_number": week.week_number,
        "start_date": week.start_date.isoformat(),
        "date_range": format_week_date_range(monday),
        "items": items_map,
        "day_names": DAY_NAMES,
        "meal_slots": MEAL_SLOTS,
    }


@app.get("/api/weeks/current")
def get_current_week(db: Session = Depends(get_db)):
    """Get or create the current week - full response with items."""
    today = date.today()
    year, week_num, monday = get_week_info(today)
    week = db.query(Week).filter(Week.year == year, Week.week_number == week_num).first()
    if not week:
        week = Week(year=year, week_number=week_num, start_date=monday)
        db.add(week)
        db.commit()
        db.refresh(week)
    items = db.query(MenuItem).filter(MenuItem.week_id == week.id).order_by(MenuItem.id).all()
    by_slot = _group_items_by_slot(items)
    return _week_response(week, monday, by_slot)


def _group_items_by_slot(items: list) -> dict:
    """Group menu items by (day, slot) - each slot can have multiple items."""
    by_slot = {}
    for i in items:
        key = f"{i.day}_{i.meal_slot}"
        if key not in by_slot:
            by_slot[key] = []
        by_slot[key].append(MenuItemResponse.model_validate(i).model_dump())
    return by_slot


@app.get("/api/weeks/{year}/{week_number}")
def get_week_by_number(year: int, week_number: int, db: Session = Depends(get_db)):
    """Get a specific week by year and week number."""
    monday = monday_for_week(year, week_number)
    week = db.query(Week).filter(Week.year == year, Week.week_number == week_number).first()
    if not week:
        week = Week(year=year, week_number=week_number, start_date=monday)
        db.add(week)
        db.commit()
        db.refresh(week)
    items = db.query(MenuItem).filter(MenuItem.week_id == week.id).order_by(MenuItem.id).all()
    by_slot = _group_items_by_slot(items)
    return _week_response(week, monday, by_slot)


# --- API: Menu items ---
@app.post("/api/weeks/{week_id}/items")
async def add_menu_item(week_id: int, item: MenuItemCreate, db: Session = Depends(get_db)):
    week = db.query(Week).filter(Week.id == week_id).first()
    if not week:
        raise HTTPException(404, "Week not found")
    if item.day < 0 or item.day > 6:
        raise HTTPException(400, "day must be 0-6")
    if item.meal_slot not in MEAL_SLOTS:
        raise HTTPException(400, f"meal_slot must be one of {MEAL_SLOTS}")
    # Auto-fill nutrition if not provided
    calories, protein = item.calories, item.protein
    if (item.calories == 0 and item.protein == 0) and item.food_name:
        calories, protein = await get_nutrition(item.food_name)
    db_item = MenuItem(
        week_id=week_id,
        day=item.day,
        meal_slot=item.meal_slot,
        food_name=item.food_name,
        serving_size=item.serving_size,
        calories=calories,
        protein=protein,
        added_by=item.added_by or "Nitesh",
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return MenuItemResponse.model_validate(db_item)


@app.patch("/api/items/{item_id}")
def update_menu_item(item_id: int, update: MenuItemUpdate, db: Session = Depends(get_db)):
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    if update.food_name is not None:
        item.food_name = update.food_name
    if update.serving_size is not None:
        item.serving_size = update.serving_size
    if update.calories is not None:
        item.calories = update.calories
    if update.protein is not None:
        item.protein = update.protein
    db.commit()
    db.refresh(item)
    return MenuItemResponse.model_validate(item)


@app.delete("/api/items/{item_id}")
def delete_menu_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    db.delete(item)
    db.commit()
    return {"ok": True}


# --- API: Nutrition lookup ---
@app.get("/api/nutrition/lookup")
async def lookup_nutrition(q: str = Query(..., min_length=1)):
    """Look up calories and protein for a food name."""
    calories, protein = await get_nutrition(q)
    return {"calories": calories, "protein": protein}


# --- API: PDF download ---
@app.get("/api/menu-pdf/{year}/{week_number}")
def download_menu_pdf(year: int, week_number: int, db: Session = Depends(get_db)):
    """Download the week's menu as a beautiful PDF."""
    try:
        d = datetime.strptime(f"{year}-W{week_number:02d}-1", "%G-W%V-%u").date()
    except ValueError:
        raise HTTPException(400, "Invalid year or week number")
    _, _, monday = get_week_info(d)
    week = db.query(Week).filter(Week.year == year, Week.week_number == week_number).first()
    if not week:
        week = Week(year=year, week_number=week_number, start_date=monday)
        db.add(week)
        db.commit()
        db.refresh(week)
    items = db.query(MenuItem).filter(MenuItem.week_id == week.id).order_by(MenuItem.id).all()
    by_slot = {}
    for item in items:
        key = f"{item.day}_{item.meal_slot}"
        if key not in by_slot:
            by_slot[key] = []
        by_slot[key].append(item)

    try:
        buf = _build_menu_pdf(week, monday, by_slot)
        pdf_bytes = buf.getvalue()
    except ImportError as e:
        raise HTTPException(500, f"PDF generation requires reportlab. Run: pip install reportlab. {e}")
    except Exception as e:
        raise HTTPException(500, f"PDF generation failed: {str(e)}")

    filename = f"PurNi_Menu_{year}_W{week_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# --- PDF builder ---
def _build_menu_pdf(week: Week, monday: date, by_slot: dict) -> io.BytesIO:
    """Build PDF: title + date range + food names only (no subtitle, serving, cal/protein)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    elements = []
    styles = getSampleStyleSheet()

    # Title only - NO subtitle
    title_style = ParagraphStyle(
        name="CustomTitle", parent=styles["Heading1"],
        fontSize=28, textColor=colors.HexColor("#c99a4a"),
        spaceAfter=6, alignment=1)
    elements.append(Paragraph("PurNi Menu", title_style))
    elements.append(Spacer(1, 0.3*cm))

    # Date range
    date_range = format_week_date_range(monday)
    date_style = ParagraphStyle(
        name="DateRange", parent=styles["Normal"],
        fontSize=14, textColor=colors.HexColor("#333333"),
        alignment=1, spaceAfter=12)
    elements.append(Paragraph(date_range, date_style))
    elements.append(Spacer(1, 0.4*cm))

    # Table: food names only (no serving_size, no cal/protein, no totals row)
    day_dates = [(monday + timedelta(days=i)).strftime("%d %b") for i in range(7)]
    header_row = ["Meal"] + [f"{DAY_NAMES[i]}\n{day_dates[i]}" for i in range(7)]
    data = [header_row]

    for slot in MEAL_SLOTS:
        row = [slot.capitalize()]
        for day in range(7):
            key = f"{day}_{slot}"
            slot_items = by_slot.get(key, [])
            if slot_items:
                row.append("\n".join(x.food_name for x in slot_items))
            else:
                row.append("-")
        data.append(row)

    t = Table(data, colWidths=[2.2*cm] + [3.2*cm]*7, rowHeights=[0.9*cm] + [2.2*cm]*4)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2d3748")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("BACKGROUND", (0,1), (0,-1), colors.HexColor("#4a5568")),
        ("TEXTCOLOR", (0,1), (0,-1), colors.white),
        ("FONTNAME", (0,1), (0,-1), "Helvetica-Bold"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ("ROWBACKGROUNDS", (1,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    elements.append(t)

    doc.build(elements)
    buf.seek(0)
    return buf


# --- API: ODS download ---
def _cell(text: str):
    tc = TableCell(valuetype="string")
    tc.addElement(P(text=str(text)))
    return tc


@app.get("/api/weeks/{year}/{week_number}/download/ods")
def download_menu_ods(year: int, week_number: int, db: Session = Depends(get_db)):
    """Download the week's menu as an ODF spreadsheet (.ods)."""
    d = datetime.strptime(f"{year}-W{week_number:02d}-1", "%G-W%V-%u").date()
    _, _, monday = get_week_info(d)
    week = db.query(Week).filter(Week.year == year, Week.week_number == week_number).first()
    if not week:
        week = Week(year=year, week_number=week_number, start_date=monday)
        db.add(week)
        db.commit()
        db.refresh(week)
    items = db.query(MenuItem).filter(MenuItem.week_id == week.id).all()
    by_slot = {}
    for item in items:
        key = f"{item.day}_{item.meal_slot}"
        if key not in by_slot:
            by_slot[key] = []
        by_slot[key].append(item)

    doc = OpenDocumentSpreadsheet()
    table = Table(name="PurNi Menu")
    date_range = format_week_date_range(week.start_date)

    # Header row: Meal / Mon date / Tue / ... / Sun
    day_dates = [(monday + timedelta(days=i)).strftime("%d %b") for i in range(7)]
    header = TableRow()
    header.addElement(_cell("Meal"))
    for dname, ddate in zip(DAY_NAMES, day_dates):
        header.addElement(_cell(f"{dname}\n{ddate}"))
    table.addElement(header)

    for slot in MEAL_SLOTS:
        row = TableRow()
        row.addElement(_cell(slot.capitalize()))
        for day in range(7):
            key = f"{day}_{slot}"
            slot_items = by_slot.get(key, [])
            if slot_items:
                lines = [x.food_name for x in slot_items]
                cell_text = "\n".join(lines)
                row.addElement(_cell(cell_text))
            else:
                row.addElement(_cell("-"))
        table.addElement(row)

    doc.spreadsheet.addElement(table)
    buf = io.BytesIO()
    doc.save(buf)
    ods_bytes = buf.getvalue()
    filename = f"PurNi_Menu_{year}_W{week_number}.ods"
    return Response(
        content=ods_bytes,
        media_type="application/vnd.oasis.opendocument.spreadsheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# --- Serve frontend ---
def _get_static_dir() -> Path:
    """Find frontend dir: works for local, Render, Azure."""
    base = Path(__file__).resolve().parent.parent
    front = base / "frontend"
    if (front / "index.html").exists():
        return front
    # Fallback: cwd (Render/Azure often set this to project root)
    cwd_front = Path.cwd() / "frontend"
    if (cwd_front / "index.html").exists():
        return cwd_front
    return front  # Return anyway so mount doesn't fail


STATIC_DIR = _get_static_dir()


@app.get("/")
def index():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    # Fallback if frontend not found
    return HTMLResponse("""
    <!DOCTYPE html><html><head><meta charset="utf-8"><title>PurNi Menu</title></head>
    <body><h1>PurNi Menu</h1><p>Frontend files not found. <a href="/api/health">API status</a></p></body>
    </html>
    """)


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
