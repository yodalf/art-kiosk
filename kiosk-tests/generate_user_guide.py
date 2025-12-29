#!/usr/bin/env python3
"""
Generate Art Kiosk User Guide PDF with screenshots.
"""

from pathlib import Path
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak,
    Table, TableStyle, KeepTogether
)
from reportlab.lib import colors
from PIL import Image as PILImage

SCREENSHOTS_DIR = Path(__file__).parent / "doc_screenshots"
OUTPUT_FILE = Path(__file__).parent.parent / "docs" / "Art_Kiosk_User_Guide.pdf"


def get_image_size(img_path, max_width=6*inch, max_height=7*inch):
    """Calculate image size maintaining aspect ratio."""
    with PILImage.open(img_path) as img:
        w, h = img.size

    # Scale to fit within max dimensions
    ratio = min(max_width / w, max_height / h)
    return w * ratio, h * ratio


def create_pdf():
    """Create the user guide PDF."""
    OUTPUT_FILE.parent.mkdir(exist_ok=True)

    doc = SimpleDocTemplate(
        str(OUTPUT_FILE),
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )

    # Styles
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=28,
        spaceAfter=30,
        textColor=HexColor('#2c3e50')
    )

    heading1_style = ParagraphStyle(
        'CustomHeading1',
        parent=styles['Heading1'],
        fontSize=18,
        spaceBefore=20,
        spaceAfter=12,
        textColor=HexColor('#34495e')
    )

    heading2_style = ParagraphStyle(
        'CustomHeading2',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=15,
        spaceAfter=8,
        textColor=HexColor('#34495e')
    )

    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=10,
        leading=14
    )

    caption_style = ParagraphStyle(
        'Caption',
        parent=styles['Italic'],
        fontSize=9,
        textColor=HexColor('#7f8c8d'),
        alignment=1,  # Center
        spaceBefore=5,
        spaceAfter=15
    )

    story = []

    # Title Page
    story.append(Spacer(1, 2*inch))
    story.append(Paragraph("Art Kiosk", title_style))
    story.append(Paragraph("User Guide", styles['Heading1']))
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph(
        "A comprehensive guide to the Art Kiosk web-based image display system",
        body_style
    ))
    story.append(Spacer(1, 2*inch))
    story.append(Paragraph("Version 1.0", body_style))
    story.append(PageBreak())

    # Table of Contents
    story.append(Paragraph("Table of Contents", heading1_style))
    toc_items = [
        "1. Overview",
        "2. Management Interface",
        "   2.1 Navigation",
        "   2.2 Day Scheduling",
        "   2.3 Atmospheres & Themes",
        "   2.4 Image Gallery",
        "   2.5 Remote Control",
        "   2.6 Cropping Images",
        "3. Kiosk Display",
        "4. Backup & Debug",
    ]
    for item in toc_items:
        story.append(Paragraph(item, body_style))
    story.append(PageBreak())

    # Section 1: Overview
    story.append(Paragraph("1. Overview", heading1_style))
    story.append(Paragraph(
        "Art Kiosk is a web-based image display system designed for Raspberry Pi "
        "with a 2560x2880 portrait monitor. It provides a slideshow display with "
        "remote management capabilities.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Key Features:</b>",
        body_style
    ))
    features = [
        "Web-based management interface accessible from any device",
        "Theme system for organizing images into collections",
        "Atmosphere system for grouping themes",
        "Day scheduling for automatic theme switching by time of day",
        "Remote control for navigation without physical access",
        "Video support with YouTube integration",
        "Backup and restore functionality",
    ]
    for feat in features:
        story.append(Paragraph(f"• {feat}", body_style))
    story.append(PageBreak())

    # Section 2: Management Interface
    story.append(Paragraph("2. Management Interface", heading1_style))
    story.append(Paragraph(
        "The management interface is accessible at the root URL (/) and provides "
        "complete control over the kiosk display.",
        body_style
    ))

    # Full management screenshot
    img_path = SCREENSHOTS_DIR / "01_management_full.png"
    if img_path.exists():
        w, h = get_image_size(img_path, max_width=6.5*inch, max_height=8*inch)
        story.append(Image(str(img_path), width=w, height=h))
        story.append(Paragraph("Figure 1: Full Management Interface", caption_style))
    story.append(PageBreak())

    # 2.1 Navigation
    story.append(Paragraph("2.1 Navigation", heading2_style))
    story.append(Paragraph(
        "The navigation bar at the top provides quick access to all sections:",
        body_style
    ))
    nav_items = [
        "<b>Backup</b> - Export and import settings",
        "<b>Debug</b> - View system logs and debug information",
        "<b>View Kiosk Display</b> - Open the slideshow view",
    ]
    for item in nav_items:
        story.append(Paragraph(f"• {item}", body_style))

    img_path = SCREENSHOTS_DIR / "02_navigation_bar.png"
    if img_path.exists():
        w, h = get_image_size(img_path, max_width=6.5*inch, max_height=1.5*inch)
        story.append(Spacer(1, 10))
        story.append(Image(str(img_path), width=w, height=h))
        story.append(Paragraph("Figure 2: Navigation Bar", caption_style))

    # 2.2 Day Scheduling
    story.append(Paragraph("2.2 Day Scheduling", heading2_style))
    story.append(Paragraph(
        "Day scheduling allows automatic switching of atmospheres based on time of day. "
        "When enabled, the kiosk will display different collections at different hours.",
        body_style
    ))
    story.append(Paragraph(
        "Configure time periods and assign atmospheres to each period. The system "
        "automatically transitions between periods at the specified times.",
        body_style
    ))

    img_path = SCREENSHOTS_DIR / "03_day_scheduling.png"
    if img_path.exists():
        w, h = get_image_size(img_path, max_width=6.5*inch, max_height=5*inch)
        story.append(Image(str(img_path), width=w, height=h))
        story.append(Paragraph("Figure 3: Day Scheduling Configuration", caption_style))
    story.append(PageBreak())

    # 2.3 Atmospheres & Themes
    story.append(Paragraph("2.3 Atmospheres & Themes", heading2_style))
    story.append(Paragraph(
        "<b>Themes</b> are collections of images. Each image can belong to multiple themes.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Atmospheres</b> are groups of themes. When an atmosphere is active, "
        "images from all themes in that atmosphere are displayed.",
        body_style
    ))
    story.append(Paragraph(
        "The 'All Images' theme is a special permanent theme that shows all enabled images.",
        body_style
    ))

    img_path = SCREENSHOTS_DIR / "04_atmospheres_themes.png"
    if img_path.exists():
        w, h = get_image_size(img_path, max_width=6.5*inch, max_height=6*inch)
        story.append(Image(str(img_path), width=w, height=h))
        story.append(Paragraph("Figure 4: Atmospheres and Themes", caption_style))
    story.append(PageBreak())

    # 2.4 Image Gallery
    story.append(Paragraph("2.4 Image Gallery", heading2_style))
    story.append(Paragraph(
        "The image gallery displays all uploaded images as thumbnails. Features include:",
        body_style
    ))
    gallery_features = [
        "Click thumbnail to jump kiosk to that image",
        "Enable/disable individual images",
        "Assign images to themes",
        "Crop images to focus on specific regions",
        "Upload new images via drag-and-drop",
        "Current image indicator (orange border)",
    ]
    for feat in gallery_features:
        story.append(Paragraph(f"• {feat}", body_style))

    img_path = SCREENSHOTS_DIR / "05_image_grid.png"
    if img_path.exists():
        w, h = get_image_size(img_path, max_width=6.5*inch, max_height=5.5*inch)
        story.append(Image(str(img_path), width=w, height=h))
        story.append(Paragraph("Figure 5: Image Gallery", caption_style))
    story.append(PageBreak())

    # 2.5 Remote Control
    story.append(Paragraph("2.5 Remote Control", heading2_style))
    story.append(Paragraph(
        "The remote control section allows you to control the kiosk display without "
        "physical access. Available commands:",
        body_style
    ))
    remote_commands = [
        "<b>Previous/Next</b> - Navigate between images",
        "<b>Play/Pause</b> - Control automatic slideshow advancement",
        "<b>Reload</b> - Refresh the kiosk display",
    ]
    for cmd in remote_commands:
        story.append(Paragraph(f"• {cmd}", body_style))

    img_path = SCREENSHOTS_DIR / "06_remote_control.png"
    if img_path.exists():
        w, h = get_image_size(img_path, max_width=6.5*inch, max_height=5.5*inch)
        story.append(Image(str(img_path), width=w, height=h))
        story.append(Paragraph("Figure 6: Remote Control & Image Gallery", caption_style))
    story.append(PageBreak())

    # 2.6 Cropping Images
    story.append(Paragraph("2.6 Cropping Images", heading2_style))
    story.append(Paragraph(
        "The crop function allows you to select a specific region of an image to display. "
        "Access it via the contextual menu (three dots) on any image card.",
        body_style
    ))
    crop_features = [
        "<b>Aspect ratio lock</b> - Keeps crop region matched to display proportions",
        "<b>Resize/Move</b> - Drag corners or edges to resize, drag inside to move",
        "<b>Save Crop</b> - Apply the crop selection",
        "<b>Clear Crop</b> - Reset to default crop",
    ]
    for feat in crop_features:
        story.append(Paragraph(f"• {feat}", body_style))

    img_path = SCREENSHOTS_DIR / "upload" / "08_crop_modal.png"
    if img_path.exists():
        w, h = get_image_size(img_path, max_width=6.5*inch, max_height=4.5*inch)
        story.append(Image(str(img_path), width=w, height=h))
        story.append(Paragraph("Figure 7: Crop Tool Interface", caption_style))
    story.append(PageBreak())

    # Section 3: Kiosk Display
    story.append(Paragraph("3. Kiosk Display", heading1_style))
    story.append(Paragraph(
        "The kiosk display (/view) shows images in fullscreen with smooth dissolve "
        "transitions. It's designed for a 2560x2880 portrait monitor.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Keyboard Controls:</b>",
        body_style
    ))
    keyboard_controls = [
        "Arrow Left/Right - Previous/Next image",
        "Space - Pause/Resume slideshow",
        "F - Toggle fill/fit mode",
        "R - Reload images",
    ]
    for ctrl in keyboard_controls:
        story.append(Paragraph(f"• {ctrl}", body_style))

    story.append(Paragraph(
        "<b>URL Parameters:</b>",
        body_style
    ))
    story.append(Paragraph(
        "• <b>?fit=true</b> - Start in fit mode (for external displays)",
        body_style
    ))
    story.append(Paragraph(
        "• <b>?image=filename.jpg</b> - Start at a specific image",
        body_style
    ))

    img_path = SCREENSHOTS_DIR / "09_kiosk_display.png"
    if img_path.exists():
        w, h = get_image_size(img_path, max_width=4*inch, max_height=5*inch)
        story.append(Spacer(1, 10))
        story.append(Image(str(img_path), width=w, height=h))
        story.append(Paragraph("Figure 8: Kiosk Display (Portrait Mode)", caption_style))
    story.append(PageBreak())

    # Section 4: Backup & Debug
    story.append(Paragraph("4. Backup & Debug", heading1_style))

    story.append(Paragraph("4.1 Backup", heading2_style))
    story.append(Paragraph(
        "The backup page allows you to export and import all settings, including "
        "themes, atmospheres, image assignments, and day scheduling configuration.",
        body_style
    ))

    img_path = SCREENSHOTS_DIR / "08_backup_page.png"
    if img_path.exists():
        w, h = get_image_size(img_path, max_width=6.5*inch, max_height=4*inch)
        story.append(Image(str(img_path), width=w, height=h))
        story.append(Paragraph("Figure 9: Backup Page", caption_style))

    story.append(Paragraph("4.2 Debug", heading2_style))
    story.append(Paragraph(
        "The debug page shows real-time logs from both the server and the kiosk display. "
        "Useful for troubleshooting issues.",
        body_style
    ))

    img_path = SCREENSHOTS_DIR / "07_debug_page.png"
    if img_path.exists():
        w, h = get_image_size(img_path, max_width=6.5*inch, max_height=4*inch)
        story.append(Image(str(img_path), width=w, height=h))
        story.append(Paragraph("Figure 10: Debug Page", caption_style))

    # Build PDF
    doc.build(story)
    print(f"✓ PDF created: {OUTPUT_FILE}")


if __name__ == "__main__":
    create_pdf()
