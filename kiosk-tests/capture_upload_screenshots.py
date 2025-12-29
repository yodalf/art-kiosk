#!/usr/bin/env python3
"""
Capture screenshots focused on the upload and theme assignment workflow.
"""

import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = os.getenv("KIOSK_BASE_URL", "http://192.168.2.189")
OUTPUT_DIR = Path(__file__).parent / "doc_screenshots" / "upload"


def capture_upload_screenshots():
    """Capture screenshots for upload documentation."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        print("Capturing upload workflow screenshots...")

        # 1. Navigate to management page
        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')
        time.sleep(1)

        # 2. Scroll to upload area and capture
        page.evaluate("window.scrollTo(0, document.body.scrollHeight - 800)")
        time.sleep(0.5)

        # Find upload area
        upload_section = page.locator('text=Upload Images').first
        if upload_section.count() > 0:
            upload_section.scroll_into_view_if_needed()
            time.sleep(0.5)

        page.screenshot(path=str(OUTPUT_DIR / "01_upload_area.png"))
        print("  ✓ Upload area")

        # 3. Capture the image grid showing thumbnails
        page.evaluate("window.scrollTo(0, 1200)")
        time.sleep(0.5)
        page.screenshot(path=str(OUTPUT_DIR / "02_image_grid.png"))
        print("  ✓ Image grid with thumbnails")

        # 4. Try to capture an image card with theme selector
        # Click on an image to potentially show theme assignment UI
        image_card = page.locator('.image-card').first
        if image_card.count() > 0:
            # Hover to show controls
            image_card.hover()
            time.sleep(0.5)
            page.screenshot(path=str(OUTPUT_DIR / "03_image_card_hover.png"))
            print("  ✓ Image card with hover state")

            # Look for theme button/selector
            theme_btn = page.locator('.theme-btn, .themes-btn, [class*="theme"]').first
            if theme_btn.count() > 0:
                theme_btn.click()
                time.sleep(0.5)
                page.screenshot(path=str(OUTPUT_DIR / "04_theme_selector.png"))
                print("  ✓ Theme selector popup")

        # 5. Capture themes section
        page.evaluate("window.scrollTo(0, 600)")
        time.sleep(0.5)
        themes_section = page.locator('text=Themes').first
        if themes_section.count() > 0:
            themes_section.scroll_into_view_if_needed()
            time.sleep(0.5)
        page.screenshot(path=str(OUTPUT_DIR / "05_themes_section.png"))
        print("  ✓ Themes section")

        # 6. Full page for context
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(0.5)
        page.screenshot(path=str(OUTPUT_DIR / "06_full_page_top.png"))
        print("  ✓ Full page (top)")

        browser.close()

    print(f"\n✓ Screenshots saved to: {OUTPUT_DIR}")
    return list(OUTPUT_DIR.glob("*.png"))


if __name__ == "__main__":
    screenshots = capture_upload_screenshots()
    print(f"\nCaptured {len(screenshots)} screenshots")
