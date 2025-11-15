#!/usr/bin/env python3
"""
Kiosk Image Display Server
A simple Flask server for managing and displaying images in kiosk mode.
"""

import os
import json
import time
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = Path(__file__).parent / 'images'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
app.config['SLIDESHOW_INTERVAL'] = 600  # seconds (10 minutes)

# Create upload folder if it doesn't exist
app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)

# Settings file
SETTINGS_FILE = Path(__file__).parent / 'settings.json'

# Remote control command queue
current_command = None
command_timestamp = 0

# Current image being displayed on kiosk
current_kiosk_image = None

# Debug message queue (stores last 100 messages)
from collections import deque
debug_messages = deque(maxlen=100)


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def get_settings():
    """Load settings from file."""
    defaults = {
        'interval': app.config['SLIDESHOW_INTERVAL'],
        'check_interval': 2,  # Check for changes every 2 seconds (C)
        'enabled_images': {},
        'dissolve_enabled': True,  # Dissolve transition enabled by default
        'themes': {
            'All Images': {
                'name': 'All Images',
                'created': time.time(),
                'interval': 3600  # 60 minutes
            }
        },  # Theme name -> theme info
        'image_themes': {},  # Image name -> list of theme names
        'active_theme': 'All Images',  # Default to All Images theme
        'atmospheres': {},  # Atmosphere name -> atmosphere info
        'atmosphere_themes': {},  # Atmosphere name -> list of theme names
        'active_atmosphere': None,  # No atmosphere active by default
        'image_crops': {}  # Image name -> crop data
    }

    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE, 'r') as f:
            settings = json.load(f)
            # Ensure check_interval is set to 2 if not present
            if 'check_interval' not in settings:
                settings['check_interval'] = 2
            # Ensure enabled_images exists
            if 'enabled_images' not in settings:
                settings['enabled_images'] = {}
            # Ensure dissolve_enabled exists
            if 'dissolve_enabled' not in settings:
                settings['dissolve_enabled'] = True
            # Ensure themes exist
            if 'themes' not in settings:
                settings['themes'] = {}
            # Ensure "All Images" theme always exists
            if 'All Images' not in settings['themes']:
                settings['themes']['All Images'] = {
                    'name': 'All Images',
                    'created': time.time(),
                    'interval': 3600
                }
            if 'image_themes' not in settings:
                settings['image_themes'] = {}
            if 'active_theme' not in settings:
                settings['active_theme'] = 'All Images'
            if 'atmospheres' not in settings:
                settings['atmospheres'] = {}
            if 'atmosphere_themes' not in settings:
                settings['atmosphere_themes'] = {}
            if 'active_atmosphere' not in settings:
                settings['active_atmosphere'] = None
            if 'image_crops' not in settings:
                settings['image_crops'] = {}
            return settings

    return defaults


def save_settings(settings):
    """Save settings to file."""
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)


def is_image_enabled(filename):
    """Check if an image is enabled (default: True)."""
    settings = get_settings()
    enabled_images = settings.get('enabled_images', {})
    return enabled_images.get(filename, True)  # Default to enabled


def set_image_enabled(filename, enabled):
    """Set whether an image is enabled."""
    settings = get_settings()
    if 'enabled_images' not in settings:
        settings['enabled_images'] = {}
    settings['enabled_images'][filename] = enabled
    save_settings(settings)


@app.route('/')
def manage():
    """Image management interface."""
    return render_template('manage.html')


@app.route('/view')
def kiosk():
    """Main kiosk display page."""
    settings = get_settings()
    return render_template('kiosk.html',
                         interval=settings.get('interval', 600),
                         check_interval=settings.get('check_interval', 2),
                         active_theme=settings.get('active_theme'))


@app.route('/upload')
def upload():
    """Image upload page."""
    return render_template('upload.html')


@app.route('/api/images', methods=['GET'])
def list_images():
    """Get list of all images."""
    # Check if we should filter to only enabled images
    enabled_only = request.args.get('enabled_only', 'false').lower() == 'true'

    settings = get_settings()
    active_atmosphere = settings.get('active_atmosphere')
    active_theme = settings.get('active_theme')
    image_themes = settings.get('image_themes', {})
    atmosphere_themes = settings.get('atmosphere_themes', {})

    # Determine which themes to filter by
    allowed_themes = None
    if enabled_only:
        if active_atmosphere:
            # If atmosphere is active, get all themes in that atmosphere
            allowed_themes = set(atmosphere_themes.get(active_atmosphere, []))
        elif active_theme and active_theme != 'All Images':
            # If only a theme is active (no atmosphere), use that theme
            allowed_themes = {active_theme}

    images = []
    for file in sorted(app.config['UPLOAD_FOLDER'].iterdir()):
        if file.is_file() and allowed_file(file.name):
            enabled = is_image_enabled(file.name)

            # Skip disabled images if filtering
            if enabled_only and not enabled:
                continue

            # Apply theme/atmosphere filtering
            if allowed_themes is not None:
                image_theme_list = set(image_themes.get(file.name, []))
                # Image must belong to at least one of the allowed themes
                if not image_theme_list.intersection(allowed_themes):
                    continue

            # Get themes for this image
            themes = image_themes.get(file.name, [])

            images.append({
                'name': file.name,
                'url': f'/images/{file.name}',
                'size': file.stat().st_size,
                'enabled': enabled,
                'themes': themes
            })
    return jsonify(images)


@app.route('/api/images', methods=['POST'])
def upload_image():
    """Upload a new image."""
    global current_command, command_timestamp

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    filename = secure_filename(file.filename)
    filepath = app.config['UPLOAD_FOLDER'] / filename
    file.save(filepath)

    # Assign the new image to the active theme (if not "All Images")
    settings = get_settings()
    active_theme = settings.get('active_theme')
    if active_theme and active_theme != 'All Images':
        image_themes = settings.get('image_themes', {})
        image_themes[filename] = [active_theme]
        settings['image_themes'] = image_themes
        save_settings(settings)

    # Automatically jump to the newly uploaded image
    current_command = {'command': 'jump', 'image_name': filename}
    command_timestamp = time.time()

    return jsonify({
        'success': True,
        'filename': filename,
        'url': f'/images/{filename}'
    })


@app.route('/api/images/<filename>', methods=['DELETE'])
def delete_image(filename):
    """Delete an image."""
    filename = secure_filename(filename)
    filepath = app.config['UPLOAD_FOLDER'] / filename

    if not filepath.exists():
        return jsonify({'error': 'File not found'}), 404

    filepath.unlink()
    return jsonify({'success': True})


@app.route('/api/images/<filename>/toggle', methods=['POST'])
def toggle_image(filename):
    """Toggle enabled state of an image."""
    filename = secure_filename(filename)
    filepath = app.config['UPLOAD_FOLDER'] / filename

    if not filepath.exists():
        return jsonify({'error': 'File not found'}), 404

    data = request.json
    enabled = data.get('enabled', True)
    set_image_enabled(filename, enabled)

    return jsonify({'success': True, 'enabled': enabled})


@app.route('/api/settings', methods=['GET'])
def get_settings_api():
    """Get current settings."""
    return jsonify(get_settings())


@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Update settings."""
    settings = request.json
    save_settings(settings)
    return jsonify({'success': True})


@app.route('/api/control/send', methods=['POST'])
def send_command():
    """Send a command to the kiosk display."""
    global current_command, command_timestamp

    data = request.json
    command = data.get('command')

    # Handle jump command with image name parameter
    if command == 'jump':
        image_name = data.get('image_name')
        if not image_name:
            return jsonify({'error': 'Missing image_name parameter'}), 400
        current_command = {'command': 'jump', 'image_name': image_name}
        command_timestamp = time.time()
        return jsonify({'success': True, 'command': command, 'image_name': image_name})
    elif command in ['next', 'prev', 'pause', 'play', 'reload']:
        current_command = command
        command_timestamp = time.time()
        return jsonify({'success': True, 'command': command})
    else:
        return jsonify({'error': 'Invalid command'}), 400


@app.route('/api/control/poll', methods=['GET'])
def poll_command():
    """Poll for new commands (called by kiosk display)."""
    global current_command, command_timestamp

    # Return command if it exists and is less than 5 seconds old
    if current_command and (time.time() - command_timestamp < 5):
        cmd = current_command
        current_command = None  # Clear after sending
        return jsonify({'command': cmd})
    else:
        return jsonify({'command': None})


@app.route('/api/debug/log', methods=['POST'])
def log_debug():
    """Receive debug message from kiosk."""
    global debug_messages

    data = request.json
    message = data.get('message', '')
    level = data.get('level', 'info')
    timestamp = time.time()

    debug_messages.append({
        'timestamp': timestamp,
        'level': level,
        'message': message
    })

    return jsonify({'success': True})


@app.route('/api/debug/messages', methods=['GET'])
def get_debug_messages():
    """Get recent debug messages."""
    global debug_messages
    return jsonify(list(debug_messages))


@app.route('/api/debug/clear', methods=['POST'])
def clear_debug_messages():
    """Clear debug messages."""
    global debug_messages
    debug_messages.clear()
    return jsonify({'success': True})


@app.route('/api/kiosk/current-image', methods=['POST'])
def set_current_image():
    """Set the current image being displayed on kiosk."""
    global current_kiosk_image

    data = request.json
    image_name = data.get('image_name')

    if image_name:
        current_kiosk_image = image_name

    return jsonify({'success': True})


@app.route('/api/kiosk/current-image', methods=['GET'])
def get_current_image():
    """Get the current image being displayed on kiosk."""
    global current_kiosk_image
    return jsonify({'image_name': current_kiosk_image})


@app.route('/api/themes', methods=['GET'])
def list_themes():
    """Get list of all themes."""
    settings = get_settings()
    themes = settings.get('themes', {})
    active_theme = settings.get('active_theme')
    return jsonify({'themes': themes, 'active_theme': active_theme})


@app.route('/api/themes', methods=['POST'])
def create_theme():
    """Create a new theme."""
    data = request.json
    theme_name = data.get('name')

    if not theme_name:
        return jsonify({'error': 'Theme name is required'}), 400

    settings = get_settings()
    themes = settings.get('themes', {})

    if theme_name in themes:
        return jsonify({'error': 'Theme already exists'}), 400

    themes[theme_name] = {
        'name': theme_name,
        'created': time.time(),
        'interval': 3600  # Default: 60 minutes in seconds
    }
    settings['themes'] = themes
    save_settings(settings)

    return jsonify({'success': True, 'theme': themes[theme_name]})


@app.route('/api/themes/<theme_name>', methods=['DELETE'])
def delete_theme(theme_name):
    """Delete a theme."""
    # Prevent deletion of "All Images" theme
    if theme_name == 'All Images':
        return jsonify({'error': 'Cannot delete the "All Images" theme'}), 400

    settings = get_settings()
    themes = settings.get('themes', {})

    if theme_name not in themes:
        return jsonify({'error': 'Theme not found'}), 404

    # Remove theme
    del themes[theme_name]
    settings['themes'] = themes

    # Remove theme from all images
    image_themes = settings.get('image_themes', {})
    for img_name in image_themes:
        if theme_name in image_themes[img_name]:
            image_themes[img_name].remove(theme_name)
    settings['image_themes'] = image_themes

    # Clear active theme if it was the deleted one
    if settings.get('active_theme') == theme_name:
        settings['active_theme'] = None

    save_settings(settings)
    return jsonify({'success': True})


@app.route('/api/themes/<theme_name>/interval', methods=['POST'])
def update_theme_interval(theme_name):
    """Update a theme's interval."""
    data = request.json
    interval = data.get('interval')

    if interval is None:
        return jsonify({'error': 'Interval is required'}), 400

    try:
        interval = int(interval)
        if interval < 1:
            return jsonify({'error': 'Interval must be positive'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid interval value'}), 400

    settings = get_settings()
    themes = settings.get('themes', {})

    if theme_name not in themes:
        return jsonify({'error': 'Theme not found'}), 404

    # Update theme interval
    themes[theme_name]['interval'] = interval
    settings['themes'] = themes

    # If this is the active theme, also update the global interval
    if settings.get('active_theme') == theme_name:
        settings['interval'] = interval

    save_settings(settings)
    return jsonify({'success': True, 'theme': themes[theme_name]})


@app.route('/api/themes/active', methods=['POST'])
def set_active_theme():
    """Set the active theme."""
    data = request.json
    theme_name = data.get('theme_name')

    if not theme_name:
        return jsonify({'error': 'Theme name is required'}), 400

    settings = get_settings()
    themes = settings.get('themes', {})

    # Validate theme exists
    if theme_name not in themes:
        return jsonify({'error': 'Theme not found'}), 404

    # Update interval to theme's interval
    theme_interval = themes[theme_name].get('interval', 3600)
    settings['interval'] = theme_interval

    settings['active_theme'] = theme_name
    save_settings(settings)

    return jsonify({'success': True, 'active_theme': theme_name, 'interval': settings['interval']})


@app.route('/api/images/<filename>/themes', methods=['POST'])
def update_image_themes(filename):
    """Update themes for an image."""
    filename = secure_filename(filename)
    filepath = app.config['UPLOAD_FOLDER'] / filename

    if not filepath.exists():
        return jsonify({'error': 'File not found'}), 404

    data = request.json
    themes = data.get('themes', [])

    settings = get_settings()
    image_themes = settings.get('image_themes', {})
    image_themes[filename] = themes
    settings['image_themes'] = image_themes
    save_settings(settings)

    return jsonify({'success': True, 'themes': themes})


@app.route('/api/atmospheres', methods=['GET'])
def list_atmospheres():
    """Get list of all atmospheres."""
    settings = get_settings()
    atmospheres = settings.get('atmospheres', {})
    active_atmosphere = settings.get('active_atmosphere')
    atmosphere_themes = settings.get('atmosphere_themes', {})
    return jsonify({
        'atmospheres': atmospheres,
        'active_atmosphere': active_atmosphere,
        'atmosphere_themes': atmosphere_themes
    })


@app.route('/api/atmospheres', methods=['POST'])
def create_atmosphere():
    """Create a new atmosphere."""
    data = request.json
    atmosphere_name = data.get('name')

    if not atmosphere_name:
        return jsonify({'error': 'Atmosphere name is required'}), 400

    settings = get_settings()
    atmospheres = settings.get('atmospheres', {})

    if atmosphere_name in atmospheres:
        return jsonify({'error': 'Atmosphere already exists'}), 400

    atmospheres[atmosphere_name] = {
        'name': atmosphere_name,
        'created': time.time(),
        'interval': 3600  # Default: 60 minutes in seconds
    }
    settings['atmospheres'] = atmospheres
    save_settings(settings)

    return jsonify({'success': True, 'atmosphere': atmospheres[atmosphere_name]})


@app.route('/api/atmospheres/<atmosphere_name>', methods=['DELETE'])
def delete_atmosphere(atmosphere_name):
    """Delete an atmosphere."""
    settings = get_settings()
    atmospheres = settings.get('atmospheres', {})

    if atmosphere_name not in atmospheres:
        return jsonify({'error': 'Atmosphere not found'}), 404

    # Remove atmosphere
    del atmospheres[atmosphere_name]
    settings['atmospheres'] = atmospheres

    # Remove atmosphere from atmosphere_themes mapping
    atmosphere_themes = settings.get('atmosphere_themes', {})
    if atmosphere_name in atmosphere_themes:
        del atmosphere_themes[atmosphere_name]
    settings['atmosphere_themes'] = atmosphere_themes

    # Clear active atmosphere if it was the deleted one
    if settings.get('active_atmosphere') == atmosphere_name:
        settings['active_atmosphere'] = None

    save_settings(settings)
    return jsonify({'success': True})


@app.route('/api/atmospheres/<atmosphere_name>/interval', methods=['POST'])
def update_atmosphere_interval(atmosphere_name):
    """Update an atmosphere's interval."""
    data = request.json
    interval = data.get('interval')

    if interval is None:
        return jsonify({'error': 'Interval is required'}), 400

    try:
        interval = int(interval)
        if interval < 1:
            return jsonify({'error': 'Interval must be positive'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid interval value'}), 400

    settings = get_settings()
    atmospheres = settings.get('atmospheres', {})

    if atmosphere_name not in atmospheres:
        return jsonify({'error': 'Atmosphere not found'}), 404

    # Update atmosphere interval
    atmospheres[atmosphere_name]['interval'] = interval
    settings['atmospheres'] = atmospheres

    # If this is the active atmosphere, also update the global interval
    if settings.get('active_atmosphere') == atmosphere_name:
        settings['interval'] = interval

    save_settings(settings)
    return jsonify({'success': True, 'atmosphere': atmospheres[atmosphere_name]})


@app.route('/api/atmospheres/active', methods=['POST'])
def set_active_atmosphere():
    """Set the active atmosphere."""
    data = request.json
    atmosphere_name = data.get('atmosphere_name')

    settings = get_settings()
    atmospheres = settings.get('atmospheres', {})

    # Allow setting to None to clear active atmosphere
    if atmosphere_name is None:
        settings['active_atmosphere'] = None
        # Restore active theme's interval
        active_theme = settings.get('active_theme')
        if active_theme:
            themes = settings.get('themes', {})
            if active_theme in themes:
                settings['interval'] = themes[active_theme].get('interval', 3600)
        save_settings(settings)
        return jsonify({'success': True, 'active_atmosphere': None})

    if not atmosphere_name:
        return jsonify({'error': 'Atmosphere name is required'}), 400

    # Validate atmosphere exists
    if atmosphere_name not in atmospheres:
        return jsonify({'error': 'Atmosphere not found'}), 404

    # Update interval to atmosphere's interval
    atmosphere_interval = atmospheres[atmosphere_name].get('interval', 3600)
    settings['interval'] = atmosphere_interval

    settings['active_atmosphere'] = atmosphere_name
    save_settings(settings)

    return jsonify({'success': True, 'active_atmosphere': atmosphere_name, 'interval': settings['interval']})


@app.route('/api/atmospheres/<atmosphere_name>/themes', methods=['POST'])
def update_atmosphere_themes(atmosphere_name):
    """Update themes for an atmosphere."""
    settings = get_settings()
    atmospheres = settings.get('atmospheres', {})

    if atmosphere_name not in atmospheres:
        return jsonify({'error': 'Atmosphere not found'}), 404

    data = request.json
    themes = data.get('themes', [])

    atmosphere_themes = settings.get('atmosphere_themes', {})
    atmosphere_themes[atmosphere_name] = themes
    settings['atmosphere_themes'] = atmosphere_themes
    save_settings(settings)

    return jsonify({'success': True, 'themes': themes})


@app.route('/images/<filename>')
def serve_image(filename):
    """Serve uploaded images."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    # Load and log settings on startup
    settings = get_settings()
    print(f"Starting kiosk server...")
    print(f"Settings file: {SETTINGS_FILE}")
    print(f"Settings loaded: interval={settings.get('interval')}s, check_interval={settings.get('check_interval')}s")
    print(f"Enabled images: {len(settings.get('enabled_images', {}))} entries")
    if settings.get('enabled_images'):
        for img, enabled in settings['enabled_images'].items():
            print(f"  - {img}: {'enabled' if enabled else 'disabled'}")

    # Run on all interfaces, port 80
    app.run(host='0.0.0.0', port=80, debug=False)
