#!/usr/bin/env python3
"""
Generate Art Kiosk Upload Guide PDF - French Version.
"""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage

SCREENSHOTS_DIR = Path(__file__).parent / "doc_screenshots" / "upload"
SCREENSHOTS_MAIN = Path(__file__).parent / "doc_screenshots"
OUTPUT_FILE = Path(__file__).parent.parent / "docs" / "Art_Kiosk_Guide_Telechargement_FR.pdf"


def get_image_size(img_path, max_width=6*inch, max_height=6*inch):
    """Calculate image size maintaining aspect ratio."""
    with PILImage.open(img_path) as img:
        w, h = img.size
    ratio = min(max_width / w, max_height / h)
    return w * ratio, h * ratio


def create_pdf():
    """Create the upload guide PDF in French."""
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
    story.append(Paragraph("Guide de téléchargement et d'attribution des thèmes", styles['Heading2']))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(
        "Ce guide explique comment télécharger des images vers Art Kiosk et les organiser en thèmes.",
        body_style
    ))
    story.append(Spacer(1, 0.3*inch))

    # Section 1: Accéder à l'interface de gestion
    story.append(Paragraph("1. Accéder à l'interface de gestion", heading1_style))
    story.append(Paragraph(
        "Ouvrez un navigateur web et accédez à l'adresse IP ou au nom d'hôte de votre kiosque. "
        "L'interface de gestion se chargera automatiquement.",
        body_style
    ))

    img_path = SCREENSHOTS_DIR / "06_full_page_top.png"
    if img_path.exists():
        w, h = get_image_size(img_path, max_width=6.5*inch, max_height=4*inch)
        story.append(Image(str(img_path), width=w, height=h))
        story.append(Paragraph("L'écran d'accueil de l'interface de gestion", caption_style))

    # Section 2: Télécharger des images
    story.append(Paragraph("2. Télécharger des images", heading1_style))
    story.append(Paragraph(
        "Les images peuvent être téléchargées par glisser-déposer ou via l'explorateur de fichiers.",
        body_style
    ))

    story.append(Paragraph("2.1 Utiliser le glisser-déposer", heading2_style))
    story.append(Paragraph("<b>Étape 1 :</b> Faites défiler jusqu'à la section galerie d'images.", step_style))
    story.append(Paragraph("<b>Étape 2 :</b> Faites glisser les fichiers image depuis votre ordinateur vers la zone de téléchargement ou directement sur la grille d'images.", step_style))
    story.append(Paragraph("<b>Étape 3 :</b> Attendez la fin du téléchargement. Un indicateur de progression affichera l'état du téléchargement.", step_style))

    story.append(Paragraph("2.2 Utiliser l'explorateur de fichiers", heading2_style))
    story.append(Paragraph("<b>Étape 1 :</b> Cliquez sur la zone de téléchargement ou sur le bouton « Choisir des fichiers ».", step_style))
    story.append(Paragraph("<b>Étape 2 :</b> Sélectionnez une ou plusieurs images depuis votre ordinateur.", step_style))
    story.append(Paragraph("<b>Étape 3 :</b> Cliquez sur « Ouvrir » pour lancer le téléchargement.", step_style))

    img_path = SCREENSHOTS_DIR / "01_upload_area.png"
    if img_path.exists():
        w, h = get_image_size(img_path, max_width=6.5*inch, max_height=4.5*inch)
        story.append(Spacer(1, 10))
        story.append(Image(str(img_path), width=w, height=h))
        story.append(Paragraph("La zone de téléchargement et la galerie d'images", caption_style))

    story.append(Paragraph(
        "<b>Formats supportés :</b> JPEG, PNG, GIF, WebP",
        body_style
    ))
    story.append(Paragraph(
        "<b>Taille maximale :</b> 50 Mo par image",
        body_style
    ))
    story.append(PageBreak())

    # Section 3: Gérer les images
    story.append(Paragraph("3. Gérer les images", heading1_style))
    story.append(Paragraph(
        "Après le téléchargement, les images apparaissent dans la galerie sous forme de vignettes. "
        "Chaque carte d'image propose des contrôles pour activer/désactiver et attribuer des thèmes.",
        body_style
    ))

    img_path = SCREENSHOTS_DIR / "02_image_grid.png"
    if img_path.exists():
        w, h = get_image_size(img_path, max_width=6.5*inch, max_height=4.5*inch)
        story.append(Image(str(img_path), width=w, height=h))
        story.append(Paragraph("Galerie d'images avec vignettes", caption_style))

    story.append(Paragraph("3.1 Activer/Désactiver des images", heading2_style))
    story.append(Paragraph(
        "Chaque image peut être activée ou désactivée. Seules les images activées apparaissent dans le diaporama.",
        body_style
    ))
    story.append(Paragraph("<b>Pour basculer :</b> Cliquez sur le bouton activer/désactiver sur la carte de l'image.", step_style))

    story.append(Paragraph("3.2 Accéder directement à une image", heading2_style))
    story.append(Paragraph(
        "Cliquez sur n'importe quelle vignette pour afficher immédiatement cette image sur le kiosque. "
        "Une bordure orange indique quelle image est actuellement affichée.",
        body_style
    ))

    img_path = SCREENSHOTS_DIR / "07_image_card_menu.png"
    if img_path.exists():
        w, h = get_image_size(img_path, max_width=6.5*inch, max_height=5*inch)
        story.append(Spacer(1, 10))
        story.append(Image(str(img_path), width=w, height=h))
        story.append(Paragraph("Interface de gestion avec le menu contextuel ouvert", caption_style))
    story.append(PageBreak())

    # Section 4: Attribuer des images aux thèmes
    story.append(Paragraph("4. Attribuer des images aux thèmes", heading1_style))
    story.append(Paragraph(
        "Les thèmes vous permettent d'organiser les images en collections. Chaque image peut appartenir à "
        "plusieurs thèmes, vous offrant une flexibilité dans l'organisation de votre contenu.",
        body_style
    ))

    story.append(Paragraph("4.1 Créer un thème", heading2_style))
    story.append(Paragraph("<b>Étape 1 :</b> Faites défiler jusqu'à la section « Thèmes » dans l'interface de gestion.", step_style))
    story.append(Paragraph("<b>Étape 2 :</b> Entrez un nom pour votre nouveau thème dans le champ de saisie.", step_style))
    story.append(Paragraph("<b>Étape 3 :</b> Cliquez sur « Créer » ou appuyez sur Entrée pour créer le thème.", step_style))

    img_path = SCREENSHOTS_DIR / "05_themes_section.png"
    if img_path.exists():
        w, h = get_image_size(img_path, max_width=6.5*inch, max_height=4.5*inch)
        story.append(Spacer(1, 10))
        story.append(Image(str(img_path), width=w, height=h))
        story.append(Paragraph("Section des thèmes affichant les thèmes disponibles", caption_style))

    story.append(Paragraph("4.2 Attribuer une image à des thèmes", heading2_style))
    story.append(Paragraph("<b>Étape 1 :</b> Trouvez l'image que vous souhaitez attribuer dans la galerie.", step_style))
    story.append(Paragraph("<b>Étape 2 :</b> Cliquez sur le bouton thème (icône d'étiquette) sur la carte de l'image.", step_style))
    story.append(Paragraph("<b>Étape 3 :</b> Une fenêtre contextuelle affichera tous les thèmes disponibles avec des cases à cocher.", step_style))
    story.append(Paragraph("<b>Étape 4 :</b> Cochez les thèmes auxquels vous souhaitez attribuer l'image.", step_style))
    story.append(Paragraph("<b>Étape 5 :</b> Cliquez en dehors de la fenêtre ou appuyez sur Échap pour la fermer.", step_style))

    img_path = SCREENSHOTS_DIR / "04_theme_selector.png"
    if img_path.exists():
        w, h = get_image_size(img_path, max_width=6.5*inch, max_height=4.5*inch)
        story.append(Spacer(1, 10))
        story.append(Image(str(img_path), width=w, height=h))
        story.append(Paragraph("Fenêtre de sélection des thèmes pour une image", caption_style))

    story.append(Paragraph("4.3 Activer un thème", heading2_style))
    story.append(Paragraph(
        "Pour afficher uniquement les images d'un thème spécifique :",
        body_style
    ))
    story.append(Paragraph("<b>Étape 1 :</b> Allez dans la section Thèmes.", step_style))
    story.append(Paragraph("<b>Étape 2 :</b> Cliquez sur le nom du thème pour l'activer.", step_style))
    story.append(Paragraph("<b>Étape 3 :</b> Le kiosque n'affichera désormais que les images attribuées à ce thème.", step_style))

    story.append(Spacer(1, 15))
    story.append(Paragraph(
        "<b>Remarque :</b> Le thème « All Images » (Toutes les images) est un thème permanent spécial qui "
        "affiche toujours toutes les images activées, indépendamment de leurs attributions de thèmes.",
        note_style
    ))
    story.append(PageBreak())

    # Section 5: Recadrer les images
    story.append(Paragraph("5. Recadrer les images", heading1_style))
    story.append(Paragraph(
        "La fonction de recadrage vous permet de sélectionner une région spécifique d'une image à afficher sur le kiosque. "
        "Cela est utile lorsque vous souhaitez vous concentrer sur une partie particulière d'une image ou ajuster son cadrage "
        "pour l'affichage portrait.",
        body_style
    ))

    story.append(Paragraph("5.1 Ouvrir l'outil de recadrage", heading2_style))
    story.append(Paragraph("<b>Étape 1 :</b> Trouvez l'image que vous souhaitez recadrer dans la galerie.", step_style))
    story.append(Paragraph("<b>Étape 2 :</b> Cliquez sur le bouton de menu (trois points) sur la carte de l'image.", step_style))
    story.append(Paragraph("<b>Étape 3 :</b> Sélectionnez « Crop » dans le menu contextuel.", step_style))

    story.append(Paragraph("5.2 Ajuster la zone de recadrage", heading2_style))
    story.append(Paragraph(
        "L'outil de recadrage s'ouvre avec une superposition de sélection sur votre image. La zone de recadrage "
        "est verrouillée au format d'affichage (portrait) par défaut.",
        body_style
    ))
    story.append(Paragraph("<b>Redimensionner :</b> Faites glisser les coins ou les bords de la zone de sélection pour redimensionner.", step_style))
    story.append(Paragraph("<b>Déplacer :</b> Cliquez et faites glisser à l'intérieur de la zone de sélection pour la repositionner.", step_style))
    story.append(Paragraph("<b>Déverrouiller le ratio :</b> Décochez « Lock aspect ratio » pour recadrer librement.", step_style))

    img_path = SCREENSHOTS_DIR / "08_crop_modal.png"
    if img_path.exists():
        w, h = get_image_size(img_path, max_width=6.5*inch, max_height=4.5*inch)
        story.append(Spacer(1, 10))
        story.append(Image(str(img_path), width=w, height=h))
        story.append(Paragraph("L'interface de l'outil de recadrage", caption_style))

    story.append(Paragraph("5.3 Enregistrer ou effacer un recadrage", heading2_style))
    story.append(Paragraph("<b>Enregistrer :</b> Cliquez sur « Save Crop » pour appliquer votre sélection de recadrage.", step_style))
    story.append(Paragraph("<b>Effacer :</b> Cliquez sur « Clear Crop » pour réinitialiser au recadrage par défaut.", step_style))
    story.append(Paragraph("<b>Annuler :</b> Cliquez sur « Cancel » pour fermer sans enregistrer les modifications.", step_style))

    story.append(Spacer(1, 15))
    story.append(Paragraph(
        "<b>Remarque :</b> Le recadrage ne modifie pas le fichier image original. Les paramètres de recadrage sont "
        "stockés séparément et appliqués lors de l'affichage de l'image sur le kiosque.",
        note_style
    ))
    story.append(PageBreak())

    # Section 6: Conseils et bonnes pratiques
    story.append(Paragraph("6. Conseils et bonnes pratiques", heading1_style))

    tips = [
        ("<b>Téléchargements groupés :</b>", "Sélectionnez plusieurs images à la fois pour accélérer le processus de téléchargement."),
        ("<b>Nommage des images :</b>", "Utilisez des noms de fichiers descriptifs - ils aident à identifier les images dans la galerie."),
        ("<b>Organisation des thèmes :</b>", "Créez des thèmes basés sur l'ambiance, le sujet ou le moment de la journée pour une planification facile."),
        ("<b>Tester avant de déployer :</b>", "Après le téléchargement, cliquez sur « View Kiosk Display » pour prévisualiser l'apparence des images."),
        ("<b>Sauvegardes régulières :</b>", "Utilisez la page Backup pour exporter vos paramètres et attributions de thèmes."),
    ]

    for title, description in tips:
        story.append(Paragraph(f"{title} {description}", body_style))

    story.append(Spacer(1, 20))
    story.append(Paragraph(
        "Pour plus d'informations, consultez le guide utilisateur complet d'Art Kiosk.",
        body_style
    ))

    # Build PDF
    doc.build(story)
    print(f"✓ PDF créé : {OUTPUT_FILE}")


if __name__ == "__main__":
    create_pdf()
