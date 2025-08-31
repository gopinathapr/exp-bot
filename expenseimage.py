import time

from PIL import Image, ImageDraw, ImageFont

dataMock = [
    ["Lunch with team", 50, "Food", "Lunch"],
    ["Office supplies", 30, "Stationery", "Pens"],
    ["Taxi fare", 20, "Transport", "Taxi"],
]
headers = ["Description", "Amount", "Main Type", "Sub Type"]

FONT_PATH = "/Courier.ttc"
FONT_SIZE = 18
font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

row_height = 40
col_widths = [250, 100, 140, 300]
padding = 20

width = sum(col_widths) + 2 * padding


def create_image(today_expenses: list = None):
    if not today_expenses:
        print("No data provided to create image.")
        return None
    data = []
    for exp in today_expenses:
        if exp.main_type is None:
            exp.main_type = ""
        if exp.sub_type is None:
            exp.sub_type = ""
        data.append([exp.desc, exp.amount, exp.main_type, exp.sub_type])

    height = (len(data) + 2) * row_height + 2 * padding
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)
    x = padding
    y = padding

    for i, header in enumerate(headers):
        draw.text((x, y), header, font=font, fill="black", align="center", stroke_width=1, stroke_fill="blue")
        x += col_widths[i]

    y += row_height
    for row in data:
        x = padding
        for i, cell in enumerate(row):
            draw.text((x, y), str(cell), font=font, fill="black")
            x += col_widths[i]
        y += row_height

    # Save image
    name = f"expense_summary{time.time()}.png"
    img.save(name)
    print("Image saved as :", name)
    return name
