#!/usr/bin/env python3
"""
Capture screenshot of management interface with contextual menu opened.
"""

import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = os.getenv("KIOSK_BASE_URL", "http://192.168.2.189")
OUTPUT_DIR = Path(__file__).parent / "doc_screenshots" / "upload"


def capture_image_card_menu():
    """Capture full page screenshot with menu open."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Use narrower, taller viewport
        page = browser.new_page(viewport={"width": 1200, "height": 1400})

        print("Capturing management interface with contextual menu...")

        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state('networkidle')
        time.sleep(1)

        # Use the 1st image card's menu button (index 0)
        menu_buttons = page.locator('.action-menu-button')
        count = menu_buttons.count()
        print(f"  Found {count} menu buttons")

        # Get the 1st button
        button_index = 0
        menu_button = menu_buttons.nth(button_index)

        # Scroll to make the button visible in a good position
        menu_button.scroll_into_view_if_needed()
        time.sleep(0.3)

        # Get button position
        box = menu_button.bounding_box()
        print(f"  Button {button_index} at y={box['y']:.0f}")

        # Scroll so the button is in the middle-lower area (giving room for menu above)
        if box["y"] < 600:
            scroll_up = 600 - box["y"]
            page.evaluate(f"window.scrollBy(0, -{scroll_up})")
            time.sleep(0.3)
            box = menu_button.bounding_box()
            print(f"  After scroll adjustment, button at y={box['y']:.0f}")

        # Click to open the menu
        menu_button.click()
        time.sleep(0.5)

        # Verify dropdown is open
        dropdown = page.locator('.action-menu-dropdown.show')
        if dropdown.count() > 0:
            dropdown_box = dropdown.bounding_box()
            print(f"  ✓ Menu dropdown opened at y={dropdown_box['y']:.0f}")

            # Now click on "Add to theme" to open the submenu
            add_to_theme = page.locator('text=Add to theme').first
            if add_to_theme.count() > 0:
                add_to_theme.hover()
                time.sleep(0.3)
                add_to_theme.click()
                time.sleep(0.5)
                print("  ✓ Clicked 'Add to theme'")

                # Check if submenu opened
                submenu = page.locator('.theme-submenu, [class*="submenu"]')
                if submenu.count() > 0:
                    print("  ✓ Submenu opened")
            else:
                print("  ✗ 'Add to theme' not found")

            # Make sure everything is visible
            dropdown_box = dropdown.bounding_box()
            if dropdown_box and dropdown_box["y"] < 20:
                scroll_adjust = 20 - dropdown_box["y"]
                page.evaluate(f"window.scrollBy(0, -{scroll_adjust})")
                time.sleep(0.3)
        else:
            print("  ✗ Menu did not open!")

        # Take full page screenshot
        page.screenshot(path=str(OUTPUT_DIR / "07_image_card_menu.png"))
        print("  ✓ Full page screenshot saved (1200x1400)")

        browser.close()

    print(f"\n✓ Screenshot saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    capture_image_card_menu()
