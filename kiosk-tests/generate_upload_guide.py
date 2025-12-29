#!/usr/bin/env python3
"""
Generate Art Kiosk Upload Guide PDF.
"""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak,
    ListFlowable, ListItem
)
from PIL import Image as PILImage

SCREENSHOTS_DIR = Path(__file__).parent / "doc_screenshots" / "upload"
SCREENSHOTS_MAIN = Path(__file__).parent / "doc_screenshots"
OUTPUT_FILE = Path(__file__).parent.parent / "docs" / "Art_Kiosk_Upload_Guide.pdf"


def get_image_size(img_path, max_width=6*inch, max_height=6*inch):
    """Calculate image size maintaining aspect ratio."""
    with PILImage.open(img_path) as img:
        w, h = img.size
    ratio = min(max_width / w, max_height / h)
    return w * ratio, h * ratio


def create_pdf():
    """Create the upload guide PDF."""
    OUTPUT_FILE.parent.mkdir(exist_ok=True)

    doc = SimpleDocTemplate(
        str(OUTPUT_FILE),
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        spaceAfter=20,
        textColor=HexColor('#2c3e50')
    )

    heading1_style = ParagraphStyle(
        'CustomHeading1',
        parent=styles['Heading1'],
        fontSize=16,
        spaceBefore=20,
        spaceAfter=12,
        textColor=HexColor('#34495e')
    )

    heading2_style = ParagraphStyle(
        'CustomHeading2',
        parent=styles['Heading2'],
        fontSize=13,
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

    step_style = ParagraphStyle(
        'StepStyle',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=8,
        leading=14,
        leftIndent=20
    )

    caption_style = ParagraphStyle(
        'Caption',
        parent=styles['Italic'],
        fontSize=9,
        textColor=HexColor('#7f8c8d'),
        alignment=1,
        spaceBefore=5,
        spaceAfter=15
    )

    note_style = ParagraphStyle(
        'NoteStyle',
        parent=styles['Normal'],
        fontSize=10,
        leftIndent=20,
        rightIndent=20,
        spaceBefore=10,
        spaceAfter=10,
        backColor=HexColor('#f8f9fa'),
        borderPadding=10
    )

    story = []

    # Title
    story.append(Paragraph("Art Kiosk", title_style))
    story.append(Paragraph("Image Upload & Theme Assignment Guide", styles['Heading2']))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(
        "This guide explains how to upload images to the Art Kiosk and organize them into themes.",
        body_style
    ))
    story.append(Spacer(1, 0.3*inch))

    # Section 1: Accessing the Management Interface
    story.append(Paragraph("1. Accessing the Management Interface", heading1_style))
    story.append(Paragraph(
        "Open a web browser and navigate to your kiosk's IP address or hostname. "
        "The management interface will load automatically.",
        body_style
    ))

    img_path = SCREENSHOTS_DIR / "06_full_page_top.png"
    if img_path.exists():
        w, h = get_image_size(img_path, max_width=6.5*inch, max_height=4*inch)
        story.append(Image(str(img_path), width=w, height=h))
        story.append(Paragraph("The management interface home screen", caption_style))

    # Section 2: Uploading Images
    story.append(Paragraph("2. Uploading Images", heading1_style))
    story.append(Paragraph(
        "Images can be uploaded using drag-and-drop or the file browser.",
        body_style
    ))

    story.append(Paragraph("2.1 Using Drag and Drop", heading2_style))
    story.append(Paragraph("<b>Step 1:</b> Scroll down to the image gallery section.", step_style))
    story.append(Paragraph("<b>Step 2:</b> Drag image files from your computer onto the upload area or directly onto the image grid.", step_style))
    story.append(Paragraph("<b>Step 3:</b> Wait for the upload to complete. A progress indicator will show the upload status.", step_style))

    story.append(Paragraph("2.2 Using the File Browser", heading2_style))
    story.append(Paragraph("<b>Step 1:</b> Click the upload area or the 'Choose Files' button.", step_style))
    story.append(Paragraph("<b>Step 2:</b> Select one or more images from your computer.", step_style))
    story.append(Paragraph("<b>Step 3:</b> Click 'Open' to start the upload.", step_style))

    img_path = SCREENSHOTS_DIR / "01_upload_area.png"
    if img_path.exists():
        w, h = get_image_size(img_path, max_width=6.5*inch, max_height=4.5*inch)
        story.append(Spacer(1, 10))
        story.append(Image(str(img_path), width=w, height=h))
        story.append(Paragraph("The upload area and image gallery", caption_style))

    story.append(Paragraph(
        "<b>Supported formats:</b> JPEG, PNG, GIF, WebP",
        body_style
    ))
    story.append(Paragraph(
        "<b>Maximum file size:</b> 50 MB per image",
        body_style
    ))
    story.append(PageBreak())

    # Section 3: Managing Images
    story.append(Paragraph("3. Managing Images", heading1_style))
    story.append(Paragraph(
        "After uploading, images appear in the gallery as thumbnails. Each image card provides "
        "controls for enabling/disabling and theme assignment.",
        body_style
    ))

    img_path = SCREENSHOTS_DIR / "02_image_grid.png"
    if img_path.exists():
        w, h = get_image_size(img_path, max_width=6.5*inch, max_height=4.5*inch)
        story.append(Image(str(img_path), width=w, height=h))
        story.append(Paragraph("Image gallery with thumbnails", caption_style))

    story.append(Paragraph("3.1 Enabling/Disabling Images", heading2_style))
    story.append(Paragraph(
        "Each image can be enabled or disabled. Only enabled images appear in the slideshow.",
        body_style
    ))
    story.append(Paragraph("<b>To toggle:</b> Click the enable/disable button on the image card.", step_style))

    story.append(Paragraph("3.2 Jumping to an Image", heading2_style))
    story.append(Paragraph(
        "Click any thumbnail to immediately display that image on the kiosk. "
        "An orange border highlights which image is currently displayed.",
        body_style
    ))

    img_path = SCREENSHOTS_DIR / "07_image_card_menu.png"
    if img_path.exists():
        w, h = get_image_size(img_path, max_width=6.5*inch, max_height=5*inch)
        story.append(Spacer(1, 10))
        story.append(Image(str(img_path), width=w, height=h))
        story.append(Paragraph("Management interface with contextual menu open", caption_style))
    story.append(PageBreak())

    # Section 4: Assigning Images to Themes
    story.append(Paragraph("4. Assigning Images to Themes", heading1_style))
    story.append(Paragraph(
        "Themes allow you to organize images into collections. Each image can belong to "
        "multiple themes, giving you flexibility in how you group your content.",
        body_style
    ))

    story.append(Paragraph("4.1 Creating a Theme", heading2_style))
    story.append(Paragraph("<b>Step 1:</b> Scroll to the 'Themes' section in the management interface.", step_style))
    story.append(Paragraph("<b>Step 2:</b> Enter a name for your new theme in the input field.", step_style))
    story.append(Paragraph("<b>Step 3:</b> Click 'Create' or press Enter to create the theme.", step_style))

    img_path = SCREENSHOTS_DIR / "05_themes_section.png"
    if img_path.exists():
        w, h = get_image_size(img_path, max_width=6.5*inch, max_height=4.5*inch)
        story.append(Spacer(1, 10))
        story.append(Image(str(img_path), width=w, height=h))
        story.append(Paragraph("Themes section showing available themes", caption_style))

    story.append(Paragraph("4.2 Assigning an Image to Themes", heading2_style))
    story.append(Paragraph("<b>Step 1:</b> Find the image you want to assign in the gallery.", step_style))
    story.append(Paragraph("<b>Step 2:</b> Click the theme button (tag icon) on the image card.", step_style))
    story.append(Paragraph("<b>Step 3:</b> A popup will show all available themes with checkboxes.", step_style))
    story.append(Paragraph("<b>Step 4:</b> Check the themes you want to assign the image to.", step_style))
    story.append(Paragraph("<b>Step 5:</b> Click outside the popup or press Escape to close it.", step_style))

    img_path = SCREENSHOTS_DIR / "04_theme_selector.png"
    if img_path.exists():
        w, h = get_image_size(img_path, max_width=6.5*inch, max_height=4.5*inch)
        story.append(Spacer(1, 10))
        story.append(Image(str(img_path), width=w, height=h))
        story.append(Paragraph("Theme selection popup for an image", caption_style))

    story.append(Paragraph("4.3 Activating a Theme", heading2_style))
    story.append(Paragraph(
        "To display only images from a specific theme:",
        body_style
    ))
    story.append(Paragraph("<b>Step 1:</b> Go to the Themes section.", step_style))
    story.append(Paragraph("<b>Step 2:</b> Click on the theme name to activate it.", step_style))
    story.append(Paragraph("<b>Step 3:</b> The kiosk will now only show images assigned to that theme.", step_style))

    story.append(Spacer(1, 15))
    story.append(Paragraph(
        "<b>Note:</b> The 'All Images' theme is a special permanent theme that always shows "
        "all enabled images regardless of their theme assignments.",
        note_style
    ))
    story.append(PageBreak())

    # Section 5: Cropping Images
    story.append(Paragraph("5. Cropping Images", heading1_style))
    story.append(Paragraph(
        "The crop function allows you to select a specific region of an image to display on the kiosk. "
        "This is useful when you want to focus on a particular part of an image or adjust its framing "
        "for the portrait display.",
        body_style
    ))

    story.append(Paragraph("5.1 Opening the Crop Tool", heading2_style))
    story.append(Paragraph("<b>Step 1:</b> Find the image you want to crop in the gallery.", step_style))
    story.append(Paragraph("<b>Step 2:</b> Click the menu button (three dots) on the image card.", step_style))
    story.append(Paragraph("<b>Step 3:</b> Select 'Crop' from the contextual menu.", step_style))

    story.append(Paragraph("5.2 Adjusting the Crop Region", heading2_style))
    story.append(Paragraph(
        "The crop tool opens with a selection overlay on your image. The crop region is locked "
        "to the display's aspect ratio (portrait) by default.",
        body_style
    ))
    story.append(Paragraph("<b>Resize:</b> Drag the corners or edges of the selection box to resize.", step_style))
    story.append(Paragraph("<b>Move:</b> Click and drag inside the selection box to reposition it.", step_style))
    story.append(Paragraph("<b>Unlock aspect ratio:</b> Uncheck 'Lock aspect ratio' to crop freely.", step_style))

    img_path = SCREENSHOTS_DIR / "08_crop_modal.png"
    if img_path.exists():
        w, h = get_image_size(img_path, max_width=6.5*inch, max_height=4.5*inch)
        story.append(Spacer(1, 10))
        story.append(Image(str(img_path), width=w, height=h))
        story.append(Paragraph("The crop tool interface", caption_style))

    story.append(Paragraph("5.3 Saving or Clearing a Crop", heading2_style))
    story.append(Paragraph("<b>Save Crop:</b> Click the 'Save Crop' button to apply your crop selection.", step_style))
    story.append(Paragraph("<b>Clear Crop:</b> Click 'Clear Crop' to reset to the default crop for this image.", step_style))
    story.append(Paragraph("<b>Cancel:</b> Click 'Cancel' to close without saving changes.", step_style))

    story.append(Spacer(1, 15))
    story.append(Paragraph(
        "<b>Note:</b> Cropping does not modify the original image file. The crop settings are stored "
        "separately and applied when displaying the image on the kiosk.",
        note_style
    ))
    story.append(PageBreak())

    # Section 6: Tips and Best Practices
    story.append(Paragraph("6. Tips and Best Practices", heading1_style))

    tips = [
        ("<b>Batch uploads:</b>", "Select multiple images at once to speed up the upload process."),
        ("<b>Image naming:</b>", "Use descriptive filenames - they help identify images in the gallery."),
        ("<b>Theme organization:</b>", "Create themes based on mood, subject, or time of day for easy scheduling."),
        ("<b>Test before deploying:</b>", "After uploading, click 'View Kiosk Display' to preview how images look."),
        ("<b>Regular backups:</b>", "Use the Backup page to export your settings and theme assignments."),
    ]

    for title, description in tips:
        story.append(Paragraph(f"{title} {description}", body_style))

    story.append(Spacer(1, 20))
    story.append(Paragraph(
        "For more information, see the full Art Kiosk User Guide.",
        body_style
    ))

    # Build PDF
    doc.build(story)
    print(f"✓ PDF created: {OUTPUT_FILE}")


if __name__ == "__main__":
    create_pdf()
