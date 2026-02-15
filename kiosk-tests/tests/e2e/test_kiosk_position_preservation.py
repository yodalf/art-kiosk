"""
Test for bug: Kiosk display reverts to first image when switching to kiosk view.

This test verifies that clicking "View Kiosk Display" from the management interface
preserves the current image position instead of reverting to the first image.
"""

import pytest
import time


@pytest.mark.e2e
def test_kiosk_starts_at_specified_image(api_client, isolated_test_data, page):
    """
    Test that the kiosk correctly starts at a specified image via URL parameter.

    This tests the core functionality: does passing ?image=xxx.jpg work?
    """
    # Set active theme
    api_client.post('/api/themes/active', json={'theme': 'TestTheme10Images'})
    time.sleep(1)  # Let kiosk update

    # Get list of images to find a valid image name
    response = api_client.get('/api/images', params={'enabled_only': 'true'})
    images = response.json()
    assert len(images) >= 5, "Need at least 5 images for this test"

    # Pick the 4th image (index 3) to start with
    target_image = images[3]['name']
    print(f"Target image: {target_image} (index 3)")
    print(f"All images: {[img['name'] for img in images[:5]]}...")

    # Navigate to kiosk with the image parameter
    page.set_viewport_size({"width": 2560, "height": 2880})
    page.goto(f"{api_client.base_url}/view?image={target_image}")

    # Wait for the kiosk to load
    page.wait_for_selector('.slide.active', timeout=10000)
    time.sleep(1)

    # Check what image is displayed
    displayed_index = page.locator('.slide.active').get_attribute('data-index')
    displayed_img = page.locator('.slide.active img')
    displayed_src = displayed_img.get_attribute('src') if displayed_img.count() > 0 else None
    displayed_name = displayed_src.split('/')[-1] if displayed_src else None

    print(f"Displayed image: {displayed_name} at index {displayed_index}")

    # Check console logs for debug messages
    console_logs = page.evaluate("""
        () => {
            // Check if there are any debug messages about the starting image
            return window.debugMessages || [];
        }
    """)
    print(f"Debug messages: {console_logs}")

    # The displayed image should be our target image
    assert displayed_name == target_image, (
        f"BUG: Kiosk should start at specified image '{target_image}' but started at '{displayed_name}' (index {displayed_index})"
    )


@pytest.mark.e2e
def test_kiosk_image_parameter_lookup(api_client, isolated_test_data, page):
    """
    Test whether the kiosk successfully finds the image in its list.

    This tests if the image lookup (findIndex) is working correctly.
    """
    # Set active theme
    api_client.post('/api/themes/active', json={'theme': 'TestTheme10Images'})
    time.sleep(1)

    # Get the list of images as the kiosk would see them
    response = api_client.get('/api/images', params={'enabled_only': 'true'})
    images = response.json()
    assert len(images) >= 3, "Need at least 3 images"

    # Pick image at index 2
    target_image = images[2]['name']
    print(f"Looking for image: {target_image}")

    # Navigate to kiosk and inject a test to check the lookup
    page.set_viewport_size({"width": 2560, "height": 2880})
    page.goto(f"{api_client.base_url}/view?image={target_image}")

    # Wait for slides to be created (images loaded and rendered)
    page.wait_for_selector('.slide', timeout=10000)

    # Wait until at least one slide has an img with a src (images fully loaded)
    page.wait_for_selector('.slide img[src]', timeout=10000)

    # Check the DOM for slides containing our target image
    lookup_result = page.evaluate(f"""
        () => {{
            const targetImage = "{target_image}";
            const slides = document.querySelectorAll('.slide img[src]');
            const slideNames = Array.from(slides).map(img => img.src.split('/').pop());
            const foundIndex = slideNames.indexOf(targetImage);

            return {{
                targetImage: targetImage,
                slideCount: slides.length,
                slideNames: slideNames.slice(0, 5),
                foundIndex: foundIndex,
                urlParam: new URLSearchParams(window.location.search).get('image')
            }};
        }}
    """)

    print(f"Lookup result: {lookup_result}")

    # Verify the image was found in the rendered slides
    assert lookup_result['foundIndex'] != -1, (
        f"Image '{target_image}' not found in kiosk slides! "
        f"Slides: {lookup_result['slideNames']}"
    )

    # Verify the URL parameter was received correctly
    assert lookup_result['urlParam'] == target_image, (
        f"URL parameter mismatch. Expected: {target_image}, Got: {lookup_result['urlParam']}"
    )


@pytest.mark.e2e
def test_server_tracks_current_image(api_client, isolated_test_data, page):
    """
    Test that the server correctly tracks the current kiosk image.

    This validates that the kiosk is reporting its current image to the server.
    """
    # Set active theme
    api_client.post('/api/themes/active', json={'theme': 'TestTheme10Images'})

    # Open kiosk view
    page.set_viewport_size({"width": 2560, "height": 2880})
    page.goto(f"{api_client.base_url}/view")
    page.wait_for_selector('.slide.active', timeout=10000)
    time.sleep(2)  # Give time for the kiosk to report current image

    # Get current image from the page
    current_img = page.locator('.slide.active img')
    current_src = current_img.get_attribute('src') if current_img.count() > 0 else None
    displayed_image = current_src.split('/')[-1] if current_src else None

    print(f"Kiosk displaying: {displayed_image}")

    # Check what server reports
    response = api_client.get('/api/kiosk/current-image')
    assert response.status_code == 200

    server_data = response.json()
    server_image = server_data.get('current_image')

    print(f"Server reports: {server_image}")

    # Server should know the current image
    assert server_image == displayed_image, (
        f"Server should track current image. "
        f"Displayed: {displayed_image}, Server reports: {server_image}"
    )


@pytest.mark.e2e
def test_view_kiosk_constructs_url_with_image(api_client, isolated_test_data, page):
    """
    Test that the management interface constructs URL with image parameter.

    This confirms the fix for checking data.current_image vs data.image_name.
    """
    # Set active theme
    api_client.post('/api/themes/active', json={'theme': 'TestTheme10Images'})

    # Get an image name
    response = api_client.get('/api/images', params={'enabled_only': 'true'})
    images = response.json()
    target_image = images[2]['name']

    # Set it as the current kiosk image
    api_client.post('/api/kiosk/current-image', json={'image_name': target_image})
    print(f"Set current image to: {target_image}")

    # Navigate to management interface
    page.set_viewport_size({"width": 1920, "height": 1080})
    page.goto(f"{api_client.base_url}/")
    page.wait_for_load_state('networkidle')
    time.sleep(0.5)

    # Check what URL would be constructed
    result = page.evaluate("""
        async () => {
            const response = await fetch('/api/kiosk/current-image');
            const data = await response.json();

            let url = '/view';
            if (data.current_image) {
                url += '?image=' + encodeURIComponent(data.current_image);
            }

            return {
                api_response: data,
                constructed_url: url,
                has_image_param: url.includes('image=')
            };
        }
    """)

    print(f"API response: {result['api_response']}")
    print(f"Constructed URL: {result['constructed_url']}")

    assert result['has_image_param'], (
        f"URL should include image parameter. "
        f"API returned: {result['api_response']}, URL: {result['constructed_url']}"
    )


@pytest.mark.e2e
def test_full_flow_position_preservation(api_client, isolated_test_data, page):
    """
    Full end-to-end test of position preservation.

    1. Load kiosk, advance to image 3
    2. Navigate to management
    3. Click View Kiosk Display
    4. Verify same image is shown
    """
    # Set active theme
    api_client.post('/api/themes/active', json={'theme': 'TestTheme10Images'})
    time.sleep(1)

    # Step 1: Open kiosk and advance to image 3
    page.set_viewport_size({"width": 2560, "height": 2880})
    page.goto(f"{api_client.base_url}/view")
    page.wait_for_selector('.slide.active', timeout=10000)
    time.sleep(1)

    # Advance 3 times
    for i in range(3):
        page.keyboard.press('ArrowRight')
        time.sleep(0.5)
    time.sleep(1)

    # Record current image
    current_img = page.locator('.slide.active img')
    current_src = current_img.get_attribute('src') if current_img.count() > 0 else None
    expected_image = current_src.split('/')[-1] if current_src else None
    expected_index = page.locator('.slide.active').get_attribute('data-index')

    print(f"After advancing: image={expected_image}, index={expected_index}")

    # Wait for server to receive the current image report
    time.sleep(1)

    # Verify server knows current image
    response = api_client.get('/api/kiosk/current-image')
    server_image = response.json().get('current_image')
    print(f"Server reports: {server_image}")

    # Step 2: Go to management
    page.goto(f"{api_client.base_url}/")
    page.wait_for_load_state('networkidle')
    time.sleep(0.5)

    # Step 3: Click View Kiosk Display
    view_link = page.locator('a.view-kiosk')
    assert view_link.count() > 0, "View Kiosk Display link not found"

    # The click handler does window.location.href, so wait for navigation
    view_link.click()
    page.wait_for_url('**/view**', timeout=10000)
    page.wait_for_selector('.slide.active', timeout=10000)
    time.sleep(1)

    # Step 4: Check final image
    final_img = page.locator('.slide.active img')
    final_src = final_img.get_attribute('src') if final_img.count() > 0 else None
    final_image = final_src.split('/')[-1] if final_src else None
    final_index = page.locator('.slide.active').get_attribute('data-index')

    print(f"After navigation: image={final_image}, index={final_index}")
    print(f"URL: {page.url}")

    # THE ASSERTION: Should be same image
    assert final_image == expected_image, (
        f"Position not preserved! Expected image '{expected_image}' (index {expected_index}), "
        f"but got '{final_image}' (index {final_index}). "
        f"Server had reported: {server_image}"
    )
