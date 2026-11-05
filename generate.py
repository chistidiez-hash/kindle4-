"""Genera 3 pantallas (tiempo, calendario, noticias) para un Kindle 4 (600x800, grises)."""
import calendar
import json
import re
import sys
import textwrap
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from html import unescape
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

W, H = 600, 800
BASE = Path(__file__).parent
CFG = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
TZ = ZoneInfo(CFG["zona_horaria"])

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

FONT_DIRS = ["C:/Windows/Fonts", "/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/liberation"]


def font(size, bold=False):
    names = ["arialbd.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"] if bold else \
            ["arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"]
    for d in FONT_DIRS:
        for n in names:
            p = Path(d) / n
            if p.exists():
                return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "kindle-dashboard/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def lienzo(titulo):
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)
    ahora = datetime.now(TZ)
    d.rectangle([0, 0, W, 70], fill=0)
    d.text((20, 16), titulo, font=font(36, True), fill=255)
    hora = ahora.strftime("%H:%M")
    d.text((W - 20, 20), hora, font=font(30, True), fill=255, anchor="ra")
    d.line([0, H - 40, W, H - 40], fill=128, width=1)
    d.text((W // 2, H - 20), f"Actualizado {ahora:%d/%m/%Y %H:%M}", font=font(16), fill=90, anchor="mm")
    return img, d, ahora


# ---------- Tiempo ----------
WMO = {0: "Despejado", 1: "Casi despejado", 2: "Poco nuboso", 3: "Cubierto", 45: "Niebla", 48: "Niebla con escarcha",
       51: "Llovizna", 53: "Llovizna", 55: "Llovizna fuerte", 61: "Lluvia débil", 63: "Lluvia", 65: "Lluvia fuerte",
       66: "Lluvia helada", 67: "Lluvia helada", 71: "Nieve débil", 73: "Nieve", 75: "Nieve fuerte", 77: "Granizo fino",
       80: "Chubascos", 81: "Chubascos", 82: "Chubascos fuertes", 85: "Chubascos de nieve", 86: "Chubascos de nieve",
       95: "Tormenta", 96: "Tormenta con granizo", 99: "Tormenta con granizo"}


def pantalla_tiempo():
    q = urllib.parse.urlencode({
        "latitude": CFG["latitud"], "longitude": CFG["longitud"], "timezone": CFG["zona_horaria"],
        "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m,relative_humidity_2m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "forecast_days": 5,
    })
    j = json.loads(get("https://api.open-meteo.com/v1/forecast?" + q))
    img, d, ahora = lienzo(f"Tiempo · {CFG['ciudad']}")
    c = j["current"]
    d.text((W // 2, 150), f"{round(c['temperature_2m'])}°", font=font(150, True), fill=0, anchor="mm")
    d.text((W // 2, 245), WMO.get(c["weather_code"], "—"), font=font(34, True), fill=0, anchor="mm")
    d.text((W // 2, 290),
           f"Sensación {round(c['apparent_temperature'])}°  ·  Viento {round(c['wind_speed_10m'])} km/h  ·  Humedad {c['relative_humidity_2m']}%",
           font=font(19), fill=60, anchor="mm")
    d.line([30, 330, W - 30, 330], fill=0, width=2)
    dd = j["daily"]
    y = 338
    for i in range(5):
        f = datetime.fromisoformat(dd["time"][i])
        nombre = "Hoy" if i == 0 else DIAS[f.weekday()].capitalize()
        d.text((30, y + 8), nombre, font=font(28, True), fill=0)
        d.text((220, y + 12), WMO.get(dd["weather_code"][i], "—"), font=font(22), fill=40)
        d.text((W - 30, y + 8), f"{round(dd['temperature_2m_min'][i])}° / {round(dd['temperature_2m_max'][i])}°",
               font=font(28, True), fill=0, anchor="ra")
        p = dd["precipitation_probability_max"][i]
        d.text((W - 30, y + 44), f"lluvia {p}%", font=font(18), fill=90, anchor="ra")
        y += 82
        if i < 4:
            d.line([30, y - 6, W - 30, y - 6], fill=190, width=1)
    return img


# ---------- Calendario ----------
def pantalla_calendario():
    img, d, ahora = lienzo("Calendario")
    d.text((W // 2, 115), f"{MESES[ahora.month - 1].capitalize()} {ahora.year}", font=font(40, True), fill=0, anchor="mm")
    colw = (W - 40) // 7
    for i, n in enumerate(["L", "M", "X", "J", "V", "S", "D"]):
        d.text((20 + i * colw + colw // 2, 175), n, font=font(26, True), fill=0, anchor="mm")
    d.line([20, 195, W - 20, 195], fill=0, width=2)
    semanas = calendar.Calendar(0).monthdayscalendar(ahora.year, ahora.month)
    rowh = 62
    for r, sem in enumerate(semanas):
        for i, dia in enumerate(sem):
            if not dia:
                continue
            cx, cy = 20 + i * colw + colw // 2, 230 + r * rowh
            if dia == ahora.day:
                d.rounded_rectangle([cx - 28, cy - 24, cx + 28, cy + 24], 8, fill=0)
                d.text((cx, cy), str(dia), font=font(28, True), fill=255, anchor="mm")
            else:
                d.text((cx, cy), str(dia), font=font(28, i >= 5), fill=60 if i >= 5 else 0, anchor="mm")
    y = 230 + len(semanas) * rowh + 20
    d.line([20, y, W - 20, y], fill=128, width=1)
    d.text((20, y + 14), "Próximos eventos", font=font(26, True), fill=0)
    d.text((20, y + 56), "(calendario por configurar)", font=font(22), fill=110)
    return img


# ---------- Noticias ----------
def noticias():
    q = urllib.parse.urlencode({"q": CFG["noticias_consulta"], "hl": "es", "gl": "ES", "ceid": "ES:es"})
    root = ET.fromstring(get("https://news.google.com/rss/search?" + q))
    out = []
    for it in root.iter("item"):
        t = unescape(it.findtext("title", "")).strip()
        m = re.match(r"^(.*) - ([^-]+)$", t)
        titulo, fuente = (m.group(1), m.group(2)) if m else (t, "")
        out.append((titulo, fuente))
        if len(out) >= CFG["noticias_max"]:
            break
    return out


def pantalla_noticias():
    img, d, ahora = lienzo(f"Noticias · {CFG['ciudad']}")
    y = 90
    f_t, f_s = font(23, True), font(17)
    for titulo, fuente in noticias():
        lineas = textwrap.wrap(titulo, 44)
        if len(lineas) > 3:
            lineas = lineas[:3]
            lineas[-1] = lineas[-1].rstrip(" ,:;") + "…"
        alto = len(lineas) * 28 + 28
        if y + alto > H - 50:
            break
        for ln in lineas:
            d.text((25, y), ln, font=f_t, fill=0)
            y += 28
        d.text((25, y), fuente, font=f_s, fill=100)
        y += 38
        d.line([25, y - 8, W - 25, y - 8], fill=200, width=1)
    return img


def main():
    out = BASE / CFG["salida"]
    out.mkdir(exist_ok=True)
    for nombre, fn in [("1_tiempo", pantalla_tiempo), ("2_calendario", pantalla_calendario), ("3_noticias", pantalla_noticias)]:
        try:
            img = fn()
        except Exception as e:  # una fuente caída no debe tumbar las demás
            print(f"ERROR en {nombre}: {e}", file=sys.stderr)
            continue
        img.convert("L").save(out / f"{nombre}.png", optimize=True)
        print("ok", nombre)


if __name__ == "__main__":
    main()
