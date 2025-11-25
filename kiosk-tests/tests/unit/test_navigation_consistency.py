"""
Unit tests for navigation menu consistency across templates.

These tests verify that all templates have consistent navigation menus
without requiring the server to be running.
"""

import pytest
import re
from pathlib import Path


# Expected active navigation links (in order)
EXPECTED_NAV_LINKS = [
    '/remote',
    '/',
    '/upload',
    '/backup',
    '/debug',
]

# View kiosk link (appears at the end with special styling)
VIEW_KIOSK_LINK = '/view'

# Templates that have navigation menus
TEMPLATES_WITH_NAV = [
    'manage.html',
    'remote.html',
    'upload.html',
    'backup.html',
    'debug.html',
    'search.html',
    'extra-images.html',
]


def get_template_path():
    """Get the path to the templates directory."""
    # Navigate from kiosk-tests/tests/unit to templates/
    return Path(__file__).parent.parent.parent.parent / 'templates'


def extract_nav_links(html_content):
    """Extract active (non-commented) navigation links from HTML content."""
    # Remove HTML comments first
    html_without_comments = re.sub(r'<!--.*?-->', '', html_content, flags=re.DOTALL)

    # Find all nav-link href values
    nav_link_pattern = r'<a\s+href="([^"]+)"[^>]*class="[^"]*nav-link[^"]*"'
    matches = re.findall(nav_link_pattern, html_without_comments)

    return matches


def extract_nav_links_order(html_content):
    """Extract navigation links in order, excluding view-kiosk."""
    links = extract_nav_links(html_content)
    # Filter out view links (they have special positioning)
    return [link for link in links if not link.startswith('/view')]


@pytest.mark.unit
class TestNavigationConsistency:
    """Tests for navigation menu consistency across templates."""

    def test_all_templates_have_remote_link(self):
        """Test that all templates have the Remote link."""
        templates_path = get_template_path()

        for template_name in TEMPLATES_WITH_NAV:
            template_path = templates_path / template_name
            assert template_path.exists(), f"Template {template_name} not found"

            content = template_path.read_text()
            nav_links = extract_nav_links(content)

            assert '/remote' in nav_links, \
                f"Template {template_name} is missing /remote link"

    def test_all_templates_have_manage_link(self):
        """Test that all templates have the Manage link."""
        templates_path = get_template_path()

        for template_name in TEMPLATES_WITH_NAV:
            template_path = templates_path / template_name
            content = template_path.read_text()
            nav_links = extract_nav_links(content)

            assert '/' in nav_links, \
                f"Template {template_name} is missing / (Manage) link"

    def test_all_templates_have_upload_link(self):
        """Test that all templates have the Upload link."""
        templates_path = get_template_path()

        for template_name in TEMPLATES_WITH_NAV:
            template_path = templates_path / template_name
            content = template_path.read_text()
            nav_links = extract_nav_links(content)

            assert '/upload' in nav_links, \
                f"Template {template_name} is missing /upload link"

    def test_all_templates_have_backup_link(self):
        """Test that all templates have the Backup link."""
        templates_path = get_template_path()

        for template_name in TEMPLATES_WITH_NAV:
            template_path = templates_path / template_name
            content = template_path.read_text()
            nav_links = extract_nav_links(content)

            assert '/backup' in nav_links, \
                f"Template {template_name} is missing /backup link"

    def test_all_templates_have_debug_link(self):
        """Test that all templates have the Debug link."""
        templates_path = get_template_path()

        for template_name in TEMPLATES_WITH_NAV:
            template_path = templates_path / template_name
            content = template_path.read_text()
            nav_links = extract_nav_links(content)

            assert '/debug' in nav_links, \
                f"Template {template_name} is missing /debug link"

    def test_all_templates_have_view_kiosk_link(self):
        """Test that all templates have the View Kiosk link."""
        templates_path = get_template_path()

        for template_name in TEMPLATES_WITH_NAV:
            template_path = templates_path / template_name
            content = template_path.read_text()
            nav_links = extract_nav_links(content)

            view_links = [link for link in nav_links if link.startswith('/view')]
            assert len(view_links) > 0, \
                f"Template {template_name} is missing /view (View Kiosk) link"

    def test_navigation_link_order_consistency(self):
        """Test that all templates have navigation links in the same order."""
        templates_path = get_template_path()

        for template_name in TEMPLATES_WITH_NAV:
            template_path = templates_path / template_name
            content = template_path.read_text()
            nav_links = extract_nav_links_order(content)

            # Check the order matches expected (allowing for active page variations)
            assert nav_links == EXPECTED_NAV_LINKS, \
                f"Template {template_name} has incorrect navigation order.\n" \
                f"Expected: {EXPECTED_NAV_LINKS}\n" \
                f"Got: {nav_links}"

    def test_search_and_extra_images_are_disabled(self):
        """Test that Search Art and Extra Images links are commented out."""
        templates_path = get_template_path()

        for template_name in TEMPLATES_WITH_NAV:
            template_path = templates_path / template_name
            content = template_path.read_text()
            nav_links = extract_nav_links(content)

            # These should NOT appear in active links (they should be commented)
            assert '/search' not in nav_links, \
                f"Template {template_name} has /search link active (should be commented out)"
            assert '/extra-images' not in nav_links, \
                f"Template {template_name} has /extra-images link active (should be commented out)"

    def test_disabled_links_are_properly_commented(self):
        """Test that disabled links exist in HTML comments."""
        templates_path = get_template_path()

        for template_name in TEMPLATES_WITH_NAV:
            template_path = templates_path / template_name
            content = template_path.read_text()

            # Find HTML comments
            comments = re.findall(r'<!--.*?-->', content, flags=re.DOTALL)
            comments_text = ' '.join(comments)

            # The disabled links should be in comments
            assert '/search' in comments_text, \
                f"Template {template_name} should have /search in a comment"
            assert '/extra-images' in comments_text, \
                f"Template {template_name} should have /extra-images in a comment"
