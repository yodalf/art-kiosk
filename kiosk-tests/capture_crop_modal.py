#!/usr/bin/env python3
"""
Capture screenshot of the crop modal dialog.
"""

import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = os.getenv("KIOSK_BASE_URL", "http://192.168.2.189")
OUTPUT_DIR = Path(__file__).parent / "doc_screenshots" / "upload"


def capture_crop_modal():
    """Capture screenshot with crop modal open."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1200, "height": 900})

        print("Capturing crop modal...")

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')
        time.sleep(1)

        # Find the first image card's menu button
        menu_buttons = page.locator('.action-menu-button')
        count = menu_buttons.count()
        print(f"  Found {count} menu buttons")

        if count == 0:
            print("  No menu buttons found!")
            browser.close()
            return

        # Click the first menu button to open contextual menu
        menu_button = menu_buttons.nth(0)
        menu_button.scroll_into_view_if_needed()
        time.sleep(0.3)
        menu_button.click()
        time.sleep(0.5)

        # Find and click "Crop" in the menu
        crop_item = page.locator('.menu-item:has-text("Crop")').first
        if crop_item.count() > 0:
            crop_item.click()
            time.sleep(1)  # Wait for crop modal to open and image to load
            print("  ✓ Clicked 'Crop' menu item")

            # Verify crop modal is open
            crop_modal = page.locator('#crop-modal.active, .crop-modal.active')
            if crop_modal.count() > 0:
                print("  ✓ Crop modal opened")

                # Wait for cropper to initialize
                time.sleep(1)

                # Take screenshot
                page.screenshot(path=str(OUTPUT_DIR / "08_crop_modal.png"))
                print("  ✓ Screenshot saved")
            else:
                print("  ✗ Crop modal did not open")
        else:
            print("  ✗ 'Crop' menu item not found")

        browser.close()

    print(f"\n✓ Screenshot saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    capture_crop_modal()
