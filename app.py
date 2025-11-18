#!/usr/bin/env python3
"""
Kiosk Image Display Server
A simple Flask server for managing and displaying images in kiosk mode.
"""

import os
import json
import time
import random
import requests
import hashlib
import uuid
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
from painting_searcher import PaintingSearcher

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = Path(__file__).parent / 'images'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
app.config['SLIDESHOW_INTERVAL'] = 600  # seconds (10 minutes)

# Create upload folder if it doesn't exist
app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)

# Create EXTRA_IMAGES folder for art search downloads
EXTRA_IMAGES_FOLDER = Path(__file__).parent / 'EXTRA_IMAGES'
EXTRA_IMAGES_FOLDER.mkdir(exist_ok=True)

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
            },
            'Extras': {
                'name': 'Extras',
                'created': time.time(),
                'interval': 3600  # 60 minutes
            }
        },  # Theme name -> theme info
        'image_themes': {},  # Image name -> list of theme names
        'active_theme': 'All Images',  # Default to All Images theme
        'atmospheres': {},  # Atmosphere name -> atmosphere info
        'atmosphere_themes': {},  # Atmosphere name -> list of theme names
        'active_atmosphere': None,  # No atmosphere active by default
        'day_scheduling_enabled': False,  # Enable/disable Day scheduling
        'day_times': {
            # 8 time periods of 3 hours each, starting at 5:00 AM
            # Times 5-8 mirror times 1-4 automatically
            '1': {'start_hour': 5, 'atmospheres': []},   # 5:00 AM - 8:00 AM
            '2': {'start_hour': 8, 'atmospheres': []},   # 8:00 AM - 11:00 AM
            '3': {'start_hour': 11, 'atmospheres': []},  # 11:00 AM - 2:00 PM
            '4': {'start_hour': 14, 'atmospheres': []},  # 2:00 PM - 5:00 PM
            '5': {'start_hour': 17, 'atmospheres': []},  # 5:00 PM - 8:00 PM (mirrors 1)
            '6': {'start_hour': 20, 'atmospheres': []},  # 8:00 PM - 11:00 PM (mirrors 2)
            '7': {'start_hour': 23, 'atmospheres': []},  # 11:00 PM - 2:00 AM (mirrors 3)
            '8': {'start_hour': 2, 'atmospheres': []}    # 2:00 AM - 5:00 AM (mirrors 4)
        },
        'shuffle_id': random.random(),  # Random ID for consistent shuffling
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
            # Ensure "Extras" theme always exists
            if 'Extras' not in settings['themes']:
                settings['themes']['Extras'] = {
                    'name': 'Extras',
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
            if 'shuffle_id' not in settings:
                settings['shuffle_id'] = random.random()
            if 'image_crops' not in settings:
                settings['image_crops'] = {}
            if 'day_scheduling_enabled' not in settings:
                settings['day_scheduling_enabled'] = False
            if 'day_times' not in settings:
                settings['day_times'] = {
                    '1': {'start_hour': 5, 'atmospheres': []},
                    '2': {'start_hour': 8, 'atmospheres': []},
                    '3': {'start_hour': 11, 'atmospheres': []},
                    '4': {'start_hour': 14, 'atmospheres': []},
                    '5': {'start_hour': 17, 'atmospheres': []},
                    '6': {'start_hour': 20, 'atmospheres': []},
                    '7': {'start_hour': 23, 'atmospheres': []},
                    '8': {'start_hour': 2, 'atmospheres': []}
                }
            return settings

    return defaults


def save_settings(settings):
    """Save settings to file and notify clients."""
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)
    # Emit settings update to all connected clients
    socketio.emit('settings_update', settings)


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


def get_current_time_period():
    """Get the current time period (1-8) based on current hour.
    Times 5-8 mirror times 1-4.
    """
    from datetime import datetime
    current_hour = datetime.now().hour

    # Map hours to time periods
    if 5 <= current_hour < 8:
        return '1'
    elif 8 <= current_hour < 11:
        return '2'
    elif 11 <= current_hour < 14:
        return '3'
    elif 14 <= current_hour < 17:
        return '4'
    elif 17 <= current_hour < 20:
        return '5'
    elif 20 <= current_hour < 23:
        return '6'
    elif 23 <= current_hour or current_hour < 2:
        return '7'
    else:  # 2 <= current_hour < 5
        return '8'


def get_active_atmospheres_for_time(time_period, settings):
    """Get atmospheres for a time period, handling mirroring.
    Times 5-8 mirror times 1-4 respectively.
    """
    day_times = settings.get('day_times', {})

    # Handle mirroring
    mirror_map = {
        '5': '1',
        '6': '2',
        '7': '3',
        '8': '4'
    }

    source_time = mirror_map.get(time_period, time_period)
    return day_times.get(source_time, {}).get('atmospheres', [])


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


@app.route('/search')
def search_art():
    """Art search page."""
    return render_template('search.html')


@app.route('/extra-images')
def extra_images_page():
    """Extra images management page."""
    return render_template('extra-images.html')


@app.route('/debug')
def debug_page():
    """Debug console page."""
    return render_template('debug.html')


@app.route('/api/images', methods=['GET'])
def list_images():
    """Get list of all images."""
    # Check if we should filter to only enabled images
    enabled_only = request.args.get('enabled_only', 'false').lower() == 'true'

    settings = get_settings()
    day_scheduling_enabled = settings.get('day_scheduling_enabled', False)
    active_atmosphere = settings.get('active_atmosphere')
    active_theme = settings.get('active_theme')
    image_themes = settings.get('image_themes', {})
    atmosphere_themes = settings.get('atmosphere_themes', {})

    # Determine which themes to filter by
    allowed_themes = None
    if enabled_only:
        if day_scheduling_enabled:
            # Day scheduling is active - use current time period's atmospheres
            current_time = get_current_time_period()
            time_atmospheres = get_active_atmospheres_for_time(current_time, settings)

            # Collect all themes from all atmospheres in current time period
            allowed_themes = set()
            for atm_name in time_atmospheres:
                atm_themes = atmosphere_themes.get(atm_name, [])
                allowed_themes.update(atm_themes)

            # If no atmospheres assigned to this time, no images shown
            if not allowed_themes:
                allowed_themes = set()  # Empty set means no images match
        elif active_atmosphere:
            # If atmosphere is active (no day scheduling), get all themes in that atmosphere
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

    # Randomize the order of images with a consistent seed
    # Use shuffle_id so both management and kiosk see the same order
    # shuffle_id is regenerated when atmosphere/theme changes
    shuffle_id = settings.get('shuffle_id', 0)
    random.seed(shuffle_id)
    random.shuffle(images)
    random.seed()  # Reset to random seed for other operations

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

    # Generate UUID-based filename
    original_filename = file.filename
    extension = Path(original_filename).suffix
    filename = f"{uuid.uuid4()}{extension}"
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

    # Automatically jump to the newly uploaded image via WebSocket
    socketio.emit('remote_command', {'command': 'jump', 'image_name': filename})

    # Notify clients that image list changed
    notify_image_list_change()

    return jsonify({
        'success': True,
        'filename': filename,
        'url': f'/images/{filename}'
    })


@app.route('/api/images/<path:filename>', methods=['DELETE'])
def delete_image(filename):
    """Delete an image."""
    try:
        print(f"Delete request received for: {filename}")
        # Don't use secure_filename here as it modifies the filename
        # Just ensure it doesn't have path traversal
        if '..' in filename or filename.startswith('/'):
            print(f"Delete failed: Invalid filename (path traversal attempt): {filename}")
            return jsonify({'error': 'Invalid filename'}), 400

        filepath = app.config['UPLOAD_FOLDER'] / filename

        if not filepath.exists():
            print(f"Delete failed: File not found: {filepath}")
            # List files in directory for debugging
            print(f"Files in upload folder: {list(app.config['UPLOAD_FOLDER'].iterdir())}")
            return jsonify({'error': 'File not found'}), 404

        print(f"Deleting image: {filepath}")
        filepath.unlink()

        # Clean up settings for this image
        settings = get_settings()
        if 'enabled_images' in settings and filename in settings['enabled_images']:
            del settings['enabled_images'][filename]
        if 'image_themes' in settings and filename in settings['image_themes']:
            del settings['image_themes'][filename]
        if 'image_crops' in settings and filename in settings['image_crops']:
            del settings['image_crops'][filename]
        save_settings(settings)

        # Notify clients that image list changed
        notify_image_list_change()

        print(f"Successfully deleted image: {filename}")
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error deleting image {filename}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/images/<path:filename>/toggle', methods=['POST'])
def toggle_image(filename):
    """Toggle enabled state of an image."""
    # Don't use secure_filename here as it modifies the filename
    # Just ensure it doesn't have path traversal
    if '..' in filename or filename.startswith('/'):
        return jsonify({'error': 'Invalid filename'}), 400

    filepath = app.config['UPLOAD_FOLDER'] / filename

    if not filepath.exists():
        return jsonify({'error': 'File not found'}), 404

    data = request.json
    enabled = data.get('enabled', True)
    set_image_enabled(filename, enabled)

    # Notify clients that image list changed
    notify_image_list_change()

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


@app.route('/api/kiosk/current-image', methods=['GET', 'POST'])
def current_image():
    """Get or update the current image being displayed on kiosk."""
    global current_kiosk_image

    if request.method == 'POST':
        data = request.json
        image_name = data.get('image_name')
        current_kiosk_image = image_name
        return jsonify({'success': True})
    else:  # GET
        return jsonify({'current_image': current_kiosk_image})


@app.route('/api/kiosk/reshuffle', methods=['POST'])
def reshuffle_images():
    """Reshuffle images with a new random order, optionally avoiding a specific image as first."""
    try:
        settings = get_settings()
        data = request.json or {}
        avoid_first = data.get('avoid_first')  # Image name to avoid as first image

        print(f"[RESHUFFLE] Request received. avoid_first={avoid_first}")

        # Get the current image list (same logic as list_images endpoint)
        enabled_only = True
        active_atmosphere = settings.get('active_atmosphere')
        active_theme = settings.get('active_theme')
        image_themes = settings.get('image_themes', {})
        atmosphere_themes = settings.get('atmosphere_themes', {})

        # Determine which themes to filter by
        allowed_themes = None
        if enabled_only:
            if active_atmosphere:
                allowed_themes = set(atmosphere_themes.get(active_atmosphere, []))
            elif active_theme and active_theme != 'All Images':
                allowed_themes = {active_theme}

        # Get images
        images = []
        upload_folder = app.config['UPLOAD_FOLDER']
        if upload_folder.exists():
            for file in upload_folder.iterdir():
                if file.is_file() and allowed_file(file.name):
                    filename = file.name
                    # Check if image is enabled
                    is_enabled = settings.get('enabled_images', {}).get(filename, True)
                    if enabled_only and not is_enabled:
                        continue

                    # Check theme filtering
                    if allowed_themes is not None:
                        img_themes = set(image_themes.get(filename, []))
                        if not img_themes.intersection(allowed_themes):
                            continue

                    images.append({'name': filename})

        print(f"[RESHUFFLE] Found {len(images)} images to shuffle")

        # If no avoid_first constraint, just generate a new shuffle
        if not avoid_first or len(images) <= 1:
            new_shuffle_id = random.random()
            settings['shuffle_id'] = new_shuffle_id
            save_settings(settings)
            print(f"[RESHUFFLE] No constraint, using shuffle_id={new_shuffle_id}")
            return jsonify({'success': True, 'shuffle_id': new_shuffle_id})

        # Keep trying new shuffles until we find one where first image != avoid_first
        # With N images avoiding 1, probability of success is (N-1)/N per attempt
        # For 3 images: 66% per attempt, 99.9% within 20 attempts
        max_attempts = 100
        for attempt in range(max_attempts):
            new_shuffle_id = random.random()

            # Test this shuffle
            random.seed(new_shuffle_id)
            test_images = images.copy()
            random.shuffle(test_images)
            random.seed()

            first_image = test_images[0]['name'] if test_images else None

            if first_image != avoid_first:
                # Success! This shuffle has a different first image
                settings['shuffle_id'] = new_shuffle_id
                save_settings(settings)
                print(f"[RESHUFFLE] Success on attempt {attempt+1}: first={first_image}, shuffle_id={new_shuffle_id}")
                return jsonify({'success': True, 'shuffle_id': new_shuffle_id})
            else:
                print(f"[RESHUFFLE] Attempt {attempt+1}: first={first_image} matches avoid={avoid_first}, retrying")

        # If we somehow fail after 100 attempts, just use the last one
        settings['shuffle_id'] = new_shuffle_id
        save_settings(settings)
        print(f"[RESHUFFLE] Max attempts reached, using shuffle_id={new_shuffle_id}")
        return jsonify({'success': True, 'shuffle_id': new_shuffle_id, 'warning': 'Could not avoid specified image'})

    except Exception as e:
        print(f"[RESHUFFLE] ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


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
    # Prevent deletion of "All Images" and "Extras" themes
    if theme_name in ['All Images', 'Extras']:
        return jsonify({'error': f'Cannot delete the "{theme_name}" theme'}), 400

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

    # Clear active atmosphere when setting a theme
    settings['active_atmosphere'] = None

    # Regenerate shuffle_id for new random order (only once!)
    settings['shuffle_id'] = random.random()

    save_settings(settings)

    return jsonify({'success': True, 'active_theme': theme_name, 'interval': settings['interval']})


@app.route('/api/images/<path:filename>/themes', methods=['POST'])
def update_image_themes(filename):
    """Update themes for an image."""
    # Don't use secure_filename here as it modifies the filename
    # Just ensure it doesn't have path traversal
    if '..' in filename or filename.startswith('/'):
        return jsonify({'error': 'Invalid filename'}), 400

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

    # Notify clients that image list changed (themes changed)
    notify_image_list_change()

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
        # Regenerate shuffle_id for new random order
        settings['shuffle_id'] = random.random()
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

    # Regenerate shuffle_id for new random order
    settings['shuffle_id'] = random.random()

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


@app.route('/api/day/status', methods=['GET'])
def get_day_status():
    """Get Day scheduling status and current time period."""
    settings = get_settings()
    current_time = get_current_time_period()

    return jsonify({
        'enabled': settings.get('day_scheduling_enabled', False),
        'current_time_period': current_time,
        'day_times': settings.get('day_times', {})
    })


@app.route('/api/day/toggle', methods=['POST'])
def toggle_day_scheduling():
    """Toggle Day scheduling on/off."""
    data = request.json
    enabled = data.get('enabled', False)

    settings = get_settings()
    settings['day_scheduling_enabled'] = enabled

    # If disabling, clear active atmosphere
    if not enabled:
        settings['active_atmosphere'] = None

    # Regenerate shuffle_id when toggling
    settings['shuffle_id'] = random.random()

    save_settings(settings)

    return jsonify({
        'success': True,
        'enabled': enabled,
        'current_time_period': get_current_time_period()
    })


@app.route('/api/day/times/<time_id>/atmospheres', methods=['POST'])
def update_time_atmospheres(time_id):
    """Update atmospheres for a specific time period."""
    if time_id not in ['1', '2', '3', '4', '5', '6', '7', '8']:
        return jsonify({'error': 'Invalid time ID'}), 400

    data = request.json
    atmospheres = data.get('atmospheres', [])

    settings = get_settings()
    day_times = settings.get('day_times', {})

    if time_id not in day_times:
        return jsonify({'error': 'Time period not found'}), 404

    # Update atmospheres for this time
    day_times[time_id]['atmospheres'] = atmospheres

    # Handle mirroring: update mirrored time as well
    mirror_map = {
        '1': '5',
        '2': '6',
        '3': '7',
        '4': '8',
        '5': '1',
        '6': '2',
        '7': '3',
        '8': '4'
    }

    mirrored_id = mirror_map.get(time_id)
    if mirrored_id:
        day_times[mirrored_id]['atmospheres'] = atmospheres

    settings['day_times'] = day_times

    # Regenerate shuffle_id when changing time atmospheres
    settings['shuffle_id'] = random.random()

    save_settings(settings)

    return jsonify({
        'success': True,
        'time_id': time_id,
        'atmospheres': atmospheres,
        'mirrored_id': mirrored_id
    })


@app.route('/images/<filename>')
def serve_image(filename):
    """Serve uploaded images."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/extra-images/<filename>')
def serve_extra_image(filename):
    """Serve extra images."""
    return send_from_directory(EXTRA_IMAGES_FOLDER, filename)


@app.route('/api/extra-images', methods=['GET'])
def list_extra_images():
    """List all extra images."""
    try:
        images = []
        settings = get_settings()

        for file in EXTRA_IMAGES_FOLDER.iterdir():
            if file.is_file() and file.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']:
                images.append({
                    'name': file.name,
                    'url': f'/extra-images/{file.name}',
                    'size': file.stat().st_size,
                    'themes': settings.get('image_themes', {}).get(file.name, [])
                })

        # Sort by name
        images.sort(key=lambda x: x['name'])

        return jsonify(images)
    except Exception as e:
        print(f"Error listing extra images: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/extra-images/<filename>', methods=['DELETE'])
def delete_extra_image(filename):
    """Delete an extra image."""
    try:
        filepath = EXTRA_IMAGES_FOLDER / filename
        if filepath.exists():
            filepath.unlink()

            # Remove from settings
            settings = get_settings()
            if 'image_themes' in settings and filename in settings['image_themes']:
                del settings['image_themes'][filename]
                save_settings(settings)

            socketio.emit('image_list_changed')
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        print(f"Error deleting extra image: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/extra-images/<filename>/themes', methods=['POST'])
def update_extra_image_themes(filename):
    """Update theme assignments for an extra image."""
    try:
        data = request.json
        themes = data.get('themes', [])

        settings = get_settings()
        if 'image_themes' not in settings:
            settings['image_themes'] = {}

        settings['image_themes'][filename] = themes
        save_settings(settings)

        socketio.emit('settings_update', settings)
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error updating themes: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/extra-images/<filename>/import', methods=['POST'])
def import_single_extra_image(filename):
    """Import a single extra image to main images folder."""
    try:
        import shutil

        source = EXTRA_IMAGES_FOLDER / filename
        if not source.exists():
            return jsonify({'error': 'Image not found'}), 404

        # Generate UUID-based filename
        extension = source.suffix
        new_filename = f"{uuid.uuid4()}{extension}"
        dest = app.config['UPLOAD_FOLDER'] / new_filename

        shutil.move(str(source), str(dest))

        # Enable the imported image by default and assign to Extras theme
        settings = get_settings()
        if 'enabled_images' not in settings:
            settings['enabled_images'] = {}
        settings['enabled_images'][dest.name] = True

        # Assign to Extras theme
        if 'image_themes' not in settings:
            settings['image_themes'] = {}
        settings['image_themes'][dest.name] = ['Extras']

        save_settings(settings)

        socketio.emit('image_list_changed')
        return jsonify({'success': True, 'imported_filename': dest.name})
    except Exception as e:
        print(f"Error importing image: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/extra-images/import-all', methods=['POST'])
def import_all_extra_images():
    """Import all extra images to main images folder."""
    try:
        import shutil

        settings = get_settings()
        if 'enabled_images' not in settings:
            settings['enabled_images'] = {}
        if 'image_themes' not in settings:
            settings['image_themes'] = {}

        imported = 0
        for file in EXTRA_IMAGES_FOLDER.iterdir():
            if file.is_file() and file.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']:
                # Generate UUID-based filename
                extension = file.suffix
                new_filename = f"{uuid.uuid4()}{extension}"
                dest = app.config['UPLOAD_FOLDER'] / new_filename

                shutil.move(str(file), str(dest))

                # Enable the imported image by default and assign to Extras theme
                settings['enabled_images'][dest.name] = True
                settings['image_themes'][dest.name] = ['Extras']

                imported += 1

        save_settings(settings)
        socketio.emit('image_list_changed')
        return jsonify({'success': True, 'imported_count': imported})
    except Exception as e:
        print(f"Error importing images: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/extra-images/delete-all', methods=['POST'])
def delete_all_extra_images():
    """Delete all extra images."""
    try:
        deleted = 0
        for file in EXTRA_IMAGES_FOLDER.iterdir():
            if file.is_file() and file.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']:
                file.unlink()
                deleted += 1

        # Clear theme assignments
        settings = get_settings()
        if 'image_themes' in settings:
            # Remove only extra images from themes
            for filename in list(settings['image_themes'].keys()):
                if not (app.config['UPLOAD_FOLDER'] / filename).exists():
                    del settings['image_themes'][filename]
            save_settings(settings)

        socketio.emit('image_list_changed')
        return jsonify({'success': True, 'deleted': deleted})
    except Exception as e:
        print(f"Error deleting all images: {e}")
        return jsonify({'error': str(e)}), 500


@socketio.on('start_art_search')
def handle_art_search(data):
    """Handle art search via WebSocket with progress updates."""
    try:
        query = data.get('query', 'portrait')
        min_aspect_ratio_match = data.get('min_aspect_ratio_match', 85.0)
        google_only = data.get('google_only', False)

        def progress_callback(message):
            """Emit progress messages to client."""
            socketio.emit('search_progress', {'message': message}, room=request.sid)

        progress_callback(f"Starting search for '{query}'...")
        progress_callback(f"Aspect ratio threshold: {min_aspect_ratio_match}%")
        if google_only:
            progress_callback("Mode: Google Images only")

        # Create searcher with custom aspect ratio match threshold
        searcher = PaintingSearcher(
            min_aspect_ratio_match=min_aspect_ratio_match,
            api_keys_file='api_keys.json'
        )

        # Search each source individually with progress updates
        all_results = []
        sources_config = searcher.sources_config.get('sources', {})

        if google_only:
            # Only search Google Images
            if sources_config.get('google_images', {}).get('enabled', False):
                progress_callback("🎨 Searching Google Images...")
                results = searcher.search_google_images(query, 10)
                all_results.extend(results)
                progress_callback(f"✓ Google: Found {len(results)} artworks")
        else:
            # Search all museums
            if sources_config.get('cleveland', {}).get('enabled', True):
                progress_callback("🎨 Searching Cleveland Museum of Art...")
                results = searcher.search_cleveland_museum(query, 10)
                all_results.extend(results)
                progress_callback(f"✓ Cleveland: Found {len(results)} artworks")

            if sources_config.get('rijksmuseum', {}).get('enabled', True):
                progress_callback("🎨 Searching Rijksmuseum...")
                results = searcher.search_rijksmuseum(query, 10)
                all_results.extend(results)
                progress_callback(f"✓ Rijksmuseum: Found {len(results)} artworks")

            if sources_config.get('wikimedia', {}).get('enabled', True):
                progress_callback("🎨 Searching Wikimedia Commons...")
                results = searcher.search_wikimedia_commons(query, 10)
                all_results.extend(results)
                progress_callback(f"✓ Wikimedia: Found {len(results)} artworks")

            if sources_config.get('europeana', {}).get('enabled', True):
                progress_callback("🎨 Searching Europeana...")
                results = searcher.search_europeana(query, 10)
                all_results.extend(results)
                progress_callback(f"✓ Europeana: Found {len(results)} artworks")

            if sources_config.get('harvard', {}).get('enabled', False):
                progress_callback("🎨 Searching Harvard Art Museums...")
                results = searcher.search_harvard(query, 10)
                all_results.extend(results)
                progress_callback(f"✓ Harvard: Found {len(results)} artworks")

            if sources_config.get('google_images', {}).get('enabled', False):
                progress_callback("🎨 Searching Google Images...")
                results = searcher.search_google_images(query, 10)
                all_results.extend(results)
                progress_callback(f"✓ Google: Found {len(results)} artworks")

        # Randomize results
        random.shuffle(all_results)

        progress_callback(f"✅ Search complete! Total: {len(all_results)} artworks")

        emit('search_complete', {
            'success': True,
            'results': all_results,
            'query': query,
            'total': len(all_results)
        })

    except Exception as e:
        print(f"Art search error: {e}")
        import traceback
        traceback.print_exc()
        emit('search_error', {
            'success': False,
            'error': str(e)
        })


@app.route('/api/download-art', methods=['POST'])
def api_download_art():
    """Download an artwork to EXTRA_IMAGES folder."""
    try:
        data = request.json
        image_url = data.get('image_url')
        title = data.get('title', 'Untitled')
        artist = data.get('artist', 'Unknown')
        source = data.get('source', 'Unknown')

        if not image_url:
            return jsonify({'error': 'Missing image_url'}), 400

        # Try to determine extension from URL
        extension = '.jpg'
        if image_url.lower().endswith('.png'):
            extension = '.png'
        elif image_url.lower().endswith('.jpeg'):
            extension = '.jpeg'

        # Generate UUID-based filename
        filename = f"{uuid.uuid4()}{extension}"
        filepath = EXTRA_IMAGES_FOLDER / filename

        # Download the image
        response = requests.get(image_url, timeout=30, stream=True)
        response.raise_for_status()

        # Save to EXTRA_IMAGES folder
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return jsonify({
            'success': True,
            'filename': filename,
            'filepath': str(filepath),
            'size': filepath.stat().st_size
        })

    except Exception as e:
        print(f"Download error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    print(f"Client connected: {request.sid}")
    # Send current settings to newly connected client
    settings = get_settings()
    emit('settings_update', settings)


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    print(f"Client disconnected: {request.sid}")


@socketio.on('send_command')
def handle_send_command(data):
    """Handle remote command via WebSocket."""
    command = data.get('command')

    # Handle jump command with image name parameter
    if command == 'jump':
        image_name = data.get('image_name')
        if not image_name:
            emit('command_error', {'error': 'Missing image_name parameter'})
            return
        # Broadcast to kiosk display
        socketio.emit('remote_command', {'command': 'jump', 'image_name': image_name})
        emit('command_sent', {'success': True, 'command': command, 'image_name': image_name})
    # Handle jump_extra command for displaying extra images
    elif command == 'jump_extra':
        image_name = data.get('image_name')
        if not image_name:
            emit('command_error', {'error': 'Missing image_name parameter'})
            return
        # Broadcast to kiosk display
        socketio.emit('remote_command', {'command': 'jump_extra', 'image_name': image_name})
        emit('command_sent', {'success': True, 'command': command, 'image_name': image_name})
    # Handle refresh_extra_crop command for refreshing extra image with updated crop
    elif command == 'refresh_extra_crop':
        image_name = data.get('image_name')
        if not image_name:
            emit('command_error', {'error': 'Missing image_name parameter'})
            return
        # Broadcast to kiosk display
        socketio.emit('remote_command', {'command': 'refresh_extra_crop', 'image_name': image_name})
        emit('command_sent', {'success': True, 'command': command, 'image_name': image_name})
    elif command in ['next', 'prev', 'pause', 'play', 'reload', 'resume_from_extra']:
        # Broadcast to kiosk display
        socketio.emit('remote_command', command)
        emit('command_sent', {'success': True, 'command': command})
    else:
        emit('command_error', {'error': 'Invalid command'})


@socketio.on('log_debug')
def handle_log_debug(data):
    """Handle debug log message via WebSocket."""
    global debug_messages

    message = data.get('message', '')
    level = data.get('level', 'info')
    timestamp = time.time()

    log_entry = {
        'timestamp': timestamp,
        'level': level,
        'message': message
    }

    debug_messages.append(log_entry)

    # Broadcast to all clients (especially management UI)
    socketio.emit('debug_message', log_entry)


def notify_image_list_change():
    """Notify all clients that the image list has changed."""
    socketio.emit('image_list_changed', {})


def rename_all_images_to_uuid():
    """Rename all images to UUID-based names and update settings."""
    settings = get_settings()
    rename_map = {}  # old_name -> new_name

    # Rename all main images
    for file in app.config['UPLOAD_FOLDER'].iterdir():
        if file.is_file() and allowed_file(file.name):
            old_name = file.name
            extension = file.suffix
            new_name = f"{uuid.uuid4()}{extension}"
            new_path = app.config['UPLOAD_FOLDER'] / new_name

            # Rename the file
            file.rename(new_path)
            rename_map[old_name] = new_name
            print(f"Renamed: {old_name} -> {new_name}")

    # Rename all extra images
    for file in EXTRA_IMAGES_FOLDER.iterdir():
        if file.is_file() and file.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']:
            old_name = file.name
            extension = file.suffix
            new_name = f"{uuid.uuid4()}{extension}"
            new_path = EXTRA_IMAGES_FOLDER / new_name

            # Rename the file
            file.rename(new_path)
            rename_map[old_name] = new_name
            print(f"Renamed (extra): {old_name} -> {new_name}")

    # Update settings to reflect new names
    if 'enabled_images' in settings:
        new_enabled = {}
        for old_name, enabled in settings['enabled_images'].items():
            new_name = rename_map.get(old_name, old_name)
            new_enabled[new_name] = enabled
        settings['enabled_images'] = new_enabled

    if 'image_themes' in settings:
        new_themes = {}
        for old_name, themes in settings['image_themes'].items():
            new_name = rename_map.get(old_name, old_name)
            new_themes[new_name] = themes
        settings['image_themes'] = new_themes

    if 'image_crops' in settings:
        new_crops = {}
        for old_name, crop_data in settings['image_crops'].items():
            new_name = rename_map.get(old_name, old_name)
            new_crops[new_name] = crop_data
        settings['image_crops'] = new_crops

    save_settings(settings)
    return rename_map


@app.route('/api/images/rename-all-to-uuid', methods=['POST'])
def rename_all_to_uuid():
    """Rename all images to UUID-based names."""
    try:
        rename_map = rename_all_images_to_uuid()
        notify_image_list_change()
        return jsonify({
            'success': True,
            'renamed_count': len(rename_map),
            'rename_map': rename_map
        })
    except Exception as e:
        print(f"Error renaming images: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


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
    socketio.run(app, host='0.0.0.0', port=80, debug=False, allow_unsafe_werkzeug=True)
