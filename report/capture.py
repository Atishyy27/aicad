"""Screenshot the live app by driving it the way a person would.

Set AICAD_BROWSER to a Chrome or Brave binary. Shots land in report/shots/ under the names the
report generator expects. Software WebGL is forced so the 3D view renders headless.
"""
import os, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "https://aicad-vercel.vercel.app"
REQUEST = sys.argv[2] if len(sys.argv) > 2 else "knuckle joint for 50 kN"
BRAVE = os.environ.get("AICAD_BROWSER", "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser")
OUT = Path(__file__).parent / "shots"
OUT.mkdir(exist_ok=True)


def shot(target, name, full=False):
    p = OUT / f"{name}.png"
    target.screenshot(path=str(p), **({"full_page": True} if full else {}))
    print(f"  {name:22s} {p.stat().st_size//1024:5d} KB")


def tab(page, pane):
    page.click(f'.tab[data-p="{pane}"]')
    time.sleep(0.6)


with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=BRAVE, headless=True,
                           args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    page = b.new_page(viewport={"width": 1600, "height": 950}, device_scale_factor=2)
    # light theme for print: a dark page prints badly and wastes toner
    page.add_init_script("try{localStorage.setItem('aicad-theme','light')}catch(e){}")
    page.goto(URL, wait_until="networkidle", timeout=90_000)
    shot(page, "01-landing")

    page.fill("#text", REQUEST)
    page.click("#go")
    page.wait_for_selector("#matRows tr[data-i]", timeout=120_000)
    page.wait_for_function("document.getElementById('busy').classList.contains('hidden') && "
                           "document.getElementById('vTime').textContent.length > 0", timeout=200_000)
    time.sleep(4)
    shot(page, "02-understood")
    shot(page.locator("#matBlk"), "10-materials")
    shot(page.locator(".center"), "04-model")
    shot(page.locator("section.right"), "07-checks")
    tab(page, "pDims"); shot(page.locator("section.right"), "06-dimensions")
    tab(page, "pLog"); shot(page.locator("section.right"), "03-working-log")

    # the weak-spot colouring lives inside the viewer frame
    frame = page.frame_locator("#viewer")
    try:
        frame.get_by_text("Weak spots").click(timeout=10_000)
        time.sleep(3)
        shot(page.locator(".center"), "08-weak-spots")
    except Exception as exc:
        print("  weak spots view not captured:", exc)

    tab(page, "pSheet")
    page.wait_for_selector("#pSheet .sheet svg", timeout=280_000)
    time.sleep(1)
    tab(page, "pFiles"); shot(page.locator("section.right"), "09-files")
    # the sheet pane is narrow; render the same SVG on its own at A3 proportions for the report
    svg = page.inner_html("#pSheet .sheet")
    sheet = b.new_page(viewport={"width": 1680, "height": 1188}, device_scale_factor=2)
    full = svg.replace("<svg ", '<svg style="width:100%;height:auto" ', 1)
    sheet.set_content("<html><body style='margin:0;background:#fff'>" + full + "</body></html>")
    time.sleep(1)
    shot(sheet, "05-drawing")
    b.close()
print("done")
