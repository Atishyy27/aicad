"""Screenshot the live app by driving it the way a person would.

Uses the Brave already on this Mac, so nothing is downloaded and nothing leaves the machine
except the page requests themselves. Shots land in report/shots/.
"""
import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "https://aicad-vercel.vercel.app"
REQUEST = sys.argv[2] if len(sys.argv) > 2 else "knuckle joint for 50 kN"
BRAVE = __import__("os").environ.get("AICAD_BROWSER", "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser")
OUT = Path(__file__).parent / "shots"
OUT.mkdir(exist_ok=True)

def shot(page, name, full=False):
    p = OUT / f"{name}.png"
    page.screenshot(path=str(p), full_page=full)
    print(f"  {name:22s} {p.stat().st_size//1024:5d} KB")

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=BRAVE, headless=True,
                           args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    page = b.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=2)
    page.goto(URL, wait_until="networkidle", timeout=90_000)
    shot(page, "01-landing")

    page.fill("#text", REQUEST)
    page.click("#go")
    page.wait_for_selector("#specCard:not(.hidden)", timeout=90_000)
    shot(page, "02-understood")

    page.click("#build")
    page.wait_for_selector("#result:not(.hidden)", timeout=280_000)
    time.sleep(3)
    shot(page, "03-working-log", full=True)

    # Click the tab button itself. A plain text match hits the first node containing the word,
    # which on the first run matched something else entirely and every tab shot came out the same.
    tabs = [("v3d", "04-model"), ("vsheet", "05-drawing"), ("vdims", "06-dimensions"),
            ("vchecks", "07-checks"), ("vweak", "08-weak-spots"), ("vfiles", "09-files")]
    for i, (key, name) in enumerate(tabs):
        try:
            page.click(f'button.tab[data-tab="{key}"]')
            page.wait_for_selector(f"#{key}:not(.hidden)", timeout=20_000)
            time.sleep(3 if key in ("v3d", "vsheet") else 1.2)
            el = page.query_selector(f"#{key}")
            if el and key in ("v3d", "vsheet"):
                el.screenshot(path=str(OUT / f"{name}.png"))
                print(f"  {name:22s} {(OUT / f'{name}.png').stat().st_size//1024:5d} KB (panel)")
            else:
                shot(page, name, full=True)
        except Exception as exc:
            print(f"  {name}: could not capture ({exc.__class__.__name__}: {exc})"[:150])
    b.close()
print("done")
