#!/usr/bin/env python3
"""
Capture screenshots of the Art Kiosk web interface for documentation.
"""

import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

# Configuration
BASE_URL = os.getenv("KIOSK_BASE_URL", "http://192.168.2.189")
OUTPUT_DIR = Path(__file__).parent / "doc_screenshots"


def capture_screenshots():
    """Capture all documentation screenshots."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # Management interface screenshots (desktop viewport)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        print("Capturing management interface...")

        # 1. Full management page
        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')
        time.sleep(1)
        page.screenshot(path=str(OUTPUT_DIR / "01_management_full.png"), full_page=True)
        print("  ✓ Full management page")

        # 2. Navigation bar area
        page.screenshot(path=str(OUTPUT_DIR / "02_navigation_bar.png"),
                       clip={"x": 0, "y": 0, "width": 1920, "height": 150})
        print("  ✓ Navigation bar")

        # 3. Day Scheduling section
        day_section = page.locator('text=Day Scheduling').first
        if day_section.count() > 0:
            day_section.scroll_into_view_if_needed()
            time.sleep(0.5)
            page.screenshot(path=str(OUTPUT_DIR / "03_day_scheduling.png"),
                           clip={"x": 0, "y": 100, "width": 1920, "height": 600})
            print("  ✓ Day Scheduling section")

        # 4. Scroll to atmospheres/themes section
        page.evaluate("window.scrollTo(0, 800)")
        time.sleep(0.5)
        page.screenshot(path=str(OUTPUT_DIR / "04_atmospheres_themes.png"))
        print("  ✓ Atmospheres/Themes section")

        # 5. Image grid section
        page.evaluate("window.scrollTo(0, 1500)")
        time.sleep(0.5)
        page.screenshot(path=str(OUTPUT_DIR / "05_image_grid.png"))
        print("  ✓ Image grid")

        # 6. Remote control section (scroll to find it)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(0.5)
        page.screenshot(path=str(OUTPUT_DIR / "06_remote_control.png"))
        print("  ✓ Remote control section")

        # 7. Debug page
        page.goto(f"{BASE_URL}/debug")
        page.wait_for_load_state('networkidle')
        time.sleep(1)
        page.screenshot(path=str(OUTPUT_DIR / "07_debug_page.png"))
        print("  ✓ Debug page")

        # 8. Backup page
        page.goto(f"{BASE_URL}/backup")
        page.wait_for_load_state('networkidle')
        time.sleep(1)
        page.screenshot(path=str(OUTPUT_DIR / "08_backup_page.png"))
        print("  ✓ Backup page")

        page.close()

        # Kiosk display screenshots (portrait viewport)
        print("\nCapturing kiosk display...")

        kiosk_page = browser.new_page(viewport={"width": 2560, "height": 2880})
        kiosk_page.goto(f"{BASE_URL}/view")
        kiosk_page.wait_for_selector('.slide.active', timeout=10000)
        time.sleep(2)

        # 9. Kiosk display (scaled down for documentation)
        kiosk_page.screenshot(path=str(OUTPUT_DIR / "09_kiosk_display.png"))
        print("  ✓ Kiosk display")

        # 10. Kiosk display fit mode
        kiosk_page.goto(f"{BASE_URL}/view?fit=true")
        kiosk_page.wait_for_selector('.slide.active', timeout=10000)
        time.sleep(2)
        kiosk_page.screenshot(path=str(OUTPUT_DIR / "10_kiosk_display_fit.png"))
        print("  ✓ Kiosk display (fit mode)")

        kiosk_page.close()
        browser.close()

    print(f"\n✓ All screenshots saved to: {OUTPUT_DIR}")
    return list(OUTPUT_DIR.glob("*.png"))


if __name__ == "__main__":
    screenshots = capture_screenshots()
    print(f"\nCaptured {len(screenshots)} screenshots:")
    for s in sorted(screenshots):
        print(f"  - {s.name}")
