"""Captura de pantallas de VocabApp para el portafolio (README).

Ejecutar con el servidor levantado en http://127.0.0.1:5000
Uso: python3 scripts/take_screenshots.py
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"
OUT = Path(__file__).resolve().parent.parent / "screenshots"
OUT.mkdir(exist_ok=True)

PAGES = [
    ("dashboard", "/", "01-dashboard"),
    ("quiz", "/study/quiz", "02-quiz"),
    ("estadisticas", "/study/stats", "03-estadisticas"),
    ("informe", "/report", "04-informe"),
    ("vocabulario", "/vocabulary/", "05-vocabulario"),
]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        for name, path, prefix in PAGES:
            page.goto(BASE + path, wait_until="networkidle")
            page.wait_for_timeout(1500)
            file = OUT / f"{prefix}.png"
            page.screenshot(path=str(file), full_page=True)
            print(f"[OK] {name}: {file.name}")
        browser.close()


if __name__ == "__main__":
    main()