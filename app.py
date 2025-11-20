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
from PIL import Image

app = Flask(__name__)


def is_thumbnail_mostly_black(image_path, threshold=30):
    """Check if an image is mostly black (average brightness below threshold).
    Returns True if the image is too dark, False otherwise.
    """
    try:
        img = Image.open(image_path).convert('L')  # Convert to grayscale
        pixels = list(img.getdata())
        avg_brightness = sum(pixels) / len(pixels)
        print(f"Thumbnail brightness: {avg_brightness:.1f} (threshold: {threshold})")
        return avg_brightness < threshold
    except Exception as e:
        print(f"Error checking thumbnail brightness: {e}")
        return False


socketio = SocketIO(app, cors_allowed_origins="*")
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = Path(__file__).parent / 'images'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
app.config['SLIDESHOW_INTERVAL'] = 600  # seconds (10 minutes)

# Create upload folder if it doesn't exist
app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)

# Create thumbnails folder for video previews
THUMBNAILS_FOLDER = Path(__file__).parent / 'thumbnails'
THUMBNAILS_FOLDER.mkdir(exist_ok=True)

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

# MPV IPC socket path
MPV_SOCKET = '/tmp/mpv-socket'
mpv_process = None
current_video_id = None  # Track which video is currently playing
video_transition_timer = None  # Timer for auto-transitioning after video interval
video_next_item = None  # Track the next item to show after video ends

# Debug message queue (stores last 500 messages)
from collections import deque
debug_messages = deque(maxlen=500)

# Test mode controls (for automated testing)
test_mode = {
    'enabled': False,
    'mock_time': None,  # Unix timestamp to use instead of real time
    'force_interval': None,  # Override slideshow interval (milliseconds)
    'force_check_interval': None,  # Override smart reload check interval (milliseconds)
}


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
        'atmospheres': {
            'All Images': {
                'name': 'All Images',
                'created': time.time(),
                'interval': 3600  # 60 minutes
            }
        },  # Atmosphere name -> atmosphere info
        'atmosphere_themes': {
            'All Images': []  # All Images atmosphere shows all themes
        },  # Atmosphere name -> list of theme names
        'active_atmosphere': None,  # No atmosphere active by default
        'day_scheduling_enabled': False,  # Enable/disable Day scheduling
        'day_times': {
            # 6 time periods of 2 hours each, repeating every 12 hours
            # Times 4-6 mirror times 1-3 automatically
            '1': {'start_hour': 6, 'atmospheres': []},   # 6:00 AM - 8:00 AM
            '2': {'start_hour': 8, 'atmospheres': []},   # 8:00 AM - 10:00 AM
            '3': {'start_hour': 10, 'atmospheres': []},  # 10:00 AM - 12:00 PM
            '4': {'start_hour': 12, 'atmospheres': []},  # 12:00 PM - 2:00 PM (mirrors 1)
            '5': {'start_hour': 14, 'atmospheres': []},  # 2:00 PM - 4:00 PM (mirrors 2)
            '6': {'start_hour': 16, 'atmospheres': []},  # 4:00 PM - 6:00 PM (mirrors 3)
            '7': {'start_hour': 18, 'atmospheres': []},  # 6:00 PM - 8:00 PM (mirrors 1)
            '8': {'start_hour': 20, 'atmospheres': []},  # 8:00 PM - 10:00 PM (mirrors 2)
            '9': {'start_hour': 22, 'atmospheres': []},  # 10:00 PM - 12:00 AM (mirrors 3)
            '10': {'start_hour': 0, 'atmospheres': []},  # 12:00 AM - 2:00 AM (mirrors 1)
            '11': {'start_hour': 2, 'atmospheres': []},  # 2:00 AM - 4:00 AM (mirrors 2)
            '12': {'start_hour': 4, 'atmospheres': []}   # 4:00 AM - 6:00 AM (mirrors 3)
        },
        'shuffle_id': random.random(),  # Random ID for consistent shuffling
        'image_crops': {},  # Image name -> crop data
        'video_urls': [],  # List of video URLs {url: str, id: str}
        'video_themes': {},  # Video ID -> list of themes (like image_themes)
        'enabled_videos': {}  # Video ID -> enabled state (like enabled_images)
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
            # Ensure "All Images" atmosphere always exists
            if 'All Images' not in settings['atmospheres']:
                settings['atmospheres']['All Images'] = {
                    'name': 'All Images',
                    'created': time.time(),
                    'interval': 3600
                }
            if 'atmosphere_themes' not in settings:
                settings['atmosphere_themes'] = {}
            # Ensure "All Images" atmosphere has empty themes list (shows all)
            if 'All Images' not in settings['atmosphere_themes']:
                settings['atmosphere_themes']['All Images'] = []
            if 'active_atmosphere' not in settings:
                settings['active_atmosphere'] = None
            if 'shuffle_id' not in settings:
                settings['shuffle_id'] = random.random()
            if 'image_crops' not in settings:
                settings['image_crops'] = {}
            if 'video_themes' not in settings:
                settings['video_themes'] = {}
            if 'enabled_videos' not in settings:
                settings['enabled_videos'] = {}
            if 'day_scheduling_enabled' not in settings:
                settings['day_scheduling_enabled'] = False
            if 'day_times' not in settings:
                settings['day_times'] = {
                    '1': {'start_hour': 6, 'atmospheres': []},
                    '2': {'start_hour': 8, 'atmospheres': []},
                    '3': {'start_hour': 10, 'atmospheres': []},
                    '4': {'start_hour': 12, 'atmospheres': []},
                    '5': {'start_hour': 14, 'atmospheres': []},
                    '6': {'start_hour': 16, 'atmospheres': []},
                    '7': {'start_hour': 18, 'atmospheres': []},
                    '8': {'start_hour': 20, 'atmospheres': []},
                    '9': {'start_hour': 22, 'atmospheres': []},
                    '10': {'start_hour': 0, 'atmospheres': []},
                    '11': {'start_hour': 2, 'atmospheres': []},
                    '12': {'start_hour': 4, 'atmospheres': []}
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
    """Get the current time period (1-12) based on current hour.
    6 periods of 2 hours each, repeating every 12 hours.
    Times 4-6 mirror 1-3, times 7-9 mirror 1-3, times 10-12 mirror 1-3.
    """
    from datetime import datetime

    # Use mock time if in test mode
    if test_mode['enabled'] and test_mode['mock_time'] is not None:
        current_hour = datetime.fromtimestamp(test_mode['mock_time']).hour
    else:
        current_hour = datetime.now().hour

    # Map hours to time periods (2-hour blocks)
    if 6 <= current_hour < 8:
        return '1'
    elif 8 <= current_hour < 10:
        return '2'
    elif 10 <= current_hour < 12:
        return '3'
    elif 12 <= current_hour < 14:
        return '4'
    elif 14 <= current_hour < 16:
        return '5'
    elif 16 <= current_hour < 18:
        return '6'
    elif 18 <= current_hour < 20:
        return '7'
    elif 20 <= current_hour < 22:
        return '8'
    elif 22 <= current_hour < 24:
        return '9'
    elif 0 <= current_hour < 2:
        return '10'
    elif 2 <= current_hour < 4:
        return '11'
    else:  # 4 <= current_hour < 6
        return '12'


def get_active_atmospheres_for_time(time_period, settings):
    """Get atmospheres for a time period, handling mirroring.
    Times 7-12 mirror times 1-6 (12-hour repeat pattern).
    If no atmospheres are assigned, returns ['All Images'].
    """
    day_times = settings.get('day_times', {})

    # Handle mirroring - times 7-12 mirror times 1-6
    mirror_map = {
        '7': '1',   # 6 PM mirrors 6 AM
        '8': '2',   # 8 PM mirrors 8 AM
        '9': '3',   # 10 PM mirrors 10 AM
        '10': '4',  # 12 AM mirrors 12 PM
        '11': '5',  # 2 AM mirrors 2 PM
        '12': '6'   # 4 AM mirrors 4 PM
    }

    source_time = mirror_map.get(time_period, time_period)
    atmospheres = day_times.get(source_time, {}).get('atmospheres', [])

    # If no atmospheres assigned, default to "All Images"
    if not atmospheres:
        return ['All Images']

    return atmospheres


@app.route('/remote')
def remote():
    """Remote control interface."""
    return render_template('remote.html')


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


@app.route('/loading')
def loading():
    """Loading page displayed while video is starting."""
    return render_template('loading.html')


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

            # If no atmospheres assigned to this time, show all images (don't filter)
            if not allowed_themes:
                allowed_themes = None  # None means show all images (like "All Images" theme)
        elif active_atmosphere:
            # If atmosphere is active (no day scheduling), get all themes in that atmosphere
            atm_themes = atmosphere_themes.get(active_atmosphere, [])
            # Special case: "All Images" atmosphere or empty themes list means show all images
            if active_atmosphere == 'All Images' or not atm_themes:
                allowed_themes = None
            else:
                allowed_themes = set(atm_themes)
        elif active_theme and active_theme != 'All Images':
            # If only a theme is active (no atmosphere), use that theme
            allowed_themes = {active_theme}

    video_themes = settings.get('video_themes', {})
    enabled_videos = settings.get('enabled_videos', {})
    video_urls = settings.get('video_urls', [])

    items = []

    # Add images
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

            items.append({
                'name': file.name,
                'url': f'/images/{file.name}',
                'size': file.stat().st_size,
                'enabled': enabled,
                'themes': themes,
                'type': 'image'
            })

    # Add videos
    for video in video_urls:
        video_id = video.get('id')
        enabled = enabled_videos.get(video_id, True)  # Default to enabled

        # Skip disabled videos if filtering
        if enabled_only and not enabled:
            continue

        # Apply theme/atmosphere filtering
        if allowed_themes is not None:
            video_theme_list = set(video_themes.get(video_id, []))
            # Video must belong to at least one of the allowed themes
            if not video_theme_list.intersection(allowed_themes):
                continue

        # Get themes for this video
        themes = video_themes.get(video_id, [])

        items.append({
            'name': video_id,
            'url': video.get('url'),
            'size': None,
            'enabled': enabled,
            'themes': themes,
            'type': 'video',
            'video_id': video_id
        })

    # Randomize the order of items with a consistent seed
    # Use shuffle_id so both management and kiosk see the same order
    # shuffle_id is regenerated when atmosphere/theme changes
    shuffle_id = settings.get('shuffle_id', 0)
    random.seed(shuffle_id)
    random.shuffle(items)
    random.seed()  # Reset to random seed for other operations

    return jsonify(items)


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

    # Get current state and toggle it
    current_state = is_image_enabled(filename)
    new_state = not current_state
    set_image_enabled(filename, new_state)

    # Notify clients that image list changed
    notify_image_list_change()

    return jsonify({'success': True, 'enabled': new_state})


def get_current_interval(settings):
    """
    Determine the current interval (cadence) based on priority:
    1. Day scheduling enabled → use first atmosphere's interval from current time period
    2. Active atmosphere set → use atmosphere's interval
    3. Active theme set → use theme's interval
    4. Default → use settings['interval']

    Atmosphere cadence always takes precedence over theme cadence.
    """
    day_scheduling_enabled = settings.get('day_scheduling_enabled', False)

    if day_scheduling_enabled:
        # Day scheduling is active - use current time period's first atmosphere interval
        current_time = get_current_time_period()
        time_atmospheres = get_active_atmospheres_for_time(current_time, settings)

        if time_atmospheres:
            # Use the first atmosphere's interval
            atmospheres = settings.get('atmospheres', {})
            first_atm = time_atmospheres[0]
            if first_atm in atmospheres:
                return atmospheres[first_atm].get('interval', 3600)

    # If no day scheduling or no atmospheres in time period, check active atmosphere
    active_atmosphere = settings.get('active_atmosphere')
    if active_atmosphere:
        atmospheres = settings.get('atmospheres', {})
        if active_atmosphere in atmospheres:
            return atmospheres[active_atmosphere].get('interval', 3600)

    # Fall back to active theme interval
    active_theme = settings.get('active_theme')
    if active_theme:
        themes = settings.get('themes', {})
        if active_theme in themes:
            return themes[active_theme].get('interval', 3600)

    # Final fallback to settings interval
    return settings.get('interval', 3600)


@app.route('/api/settings', methods=['GET'])
def get_settings_api():
    """Get current settings with dynamically calculated interval."""
    settings = get_settings()

    # Override interval with the correct current interval based on atmosphere/theme precedence
    settings['interval'] = get_current_interval(settings)

    return jsonify(settings)


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
        # Also emit via WebSocket for clients that don't poll
        socketio.emit('remote_command', {'command': 'jump', 'image_name': image_name})
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
    global current_kiosk_image, current_video_id

    if request.method == 'POST':
        data = request.json
        image_name = data.get('image_name')
        current_kiosk_image = image_name
        # Clear video ID when showing an image (unless it's a video name)
        if image_name and not image_name.startswith('video:'):
            current_video_id = None
        return jsonify({'success': True})
    else:  # GET
        return jsonify({
            'current_image': current_kiosk_image,
            'current_video_id': current_video_id
        })


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
    interval = data.get('interval', 3600)  # Default: 60 minutes in seconds

    if not theme_name:
        return jsonify({'error': 'Theme name is required'}), 400

    settings = get_settings()
    themes = settings.get('themes', {})

    if theme_name in themes:
        return jsonify({'error': 'Theme already exists'}), 400

    themes[theme_name] = {
        'name': theme_name,
        'created': time.time(),
        'interval': interval
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

    # Switch to 'All Images' if deleting the active theme
    if settings.get('active_theme') == theme_name:
        settings['active_theme'] = 'All Images'
        # Update interval to All Images' interval
        if 'All Images' in themes:
            settings['interval'] = themes['All Images'].get('interval', 3600)

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
    theme_name = data.get('theme') or data.get('theme_name')

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
    interval = data.get('interval', 3600)  # Default: 60 minutes in seconds

    if not atmosphere_name:
        return jsonify({'error': 'Atmosphere name is required'}), 400

    settings = get_settings()
    atmospheres = settings.get('atmospheres', {})

    if atmosphere_name in atmospheres:
        return jsonify({'error': 'Atmosphere already exists'}), 400

    atmospheres[atmosphere_name] = {
        'name': atmosphere_name,
        'created': time.time(),
        'interval': interval
    }
    settings['atmospheres'] = atmospheres
    save_settings(settings)

    return jsonify({'success': True, 'atmosphere': atmospheres[atmosphere_name]})


@app.route('/api/atmospheres/<atmosphere_name>', methods=['DELETE'])
def delete_atmosphere(atmosphere_name):
    """Delete an atmosphere."""
    # Prevent deletion of "All Images" atmosphere
    if atmosphere_name == 'All Images':
        return jsonify({'error': 'Cannot delete "All Images" atmosphere'}), 400

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
    atmosphere_name = data.get('atmosphere') or data.get('atmosphere_name')

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
    day_times_data = settings.get('day_times', {})

    return jsonify({
        'enabled': settings.get('day_scheduling_enabled', False),
        'current_time_period': current_time,
        'day_times': day_times_data,
        'time_periods': day_times_data  # Alias for backward compatibility
    })


@app.route('/api/day/toggle', methods=['POST'])
def toggle_day_scheduling():
    """Toggle Day scheduling on/off."""
    data = request.json
    enabled = data.get('enabled', False)

    settings = get_settings()
    settings['day_scheduling_enabled'] = enabled

    # If disabling, revert to "All Images" atmosphere
    if not enabled:
        settings['active_atmosphere'] = 'All Images'

    # Regenerate shuffle_id when toggling
    settings['shuffle_id'] = random.random()

    save_settings(settings)

    return jsonify({
        'success': True,
        'enabled': enabled,
        'current_time_period': get_current_time_period()
    })


@app.route('/api/day/enable', methods=['POST'])
def enable_day_scheduling():
    """Enable Day scheduling."""
    settings = get_settings()
    settings['day_scheduling_enabled'] = True
    settings['shuffle_id'] = random.random()
    save_settings(settings)
    return jsonify({
        'success': True,
        'enabled': True,
        'current_time_period': get_current_time_period()
    })


@app.route('/api/day/disable', methods=['POST'])
def disable_day_scheduling():
    """Disable Day scheduling."""
    settings = get_settings()
    settings['day_scheduling_enabled'] = False
    settings['active_atmosphere'] = None  # Clear atmosphere when disabling
    settings['shuffle_id'] = random.random()
    save_settings(settings)
    return jsonify({
        'success': True,
        'enabled': False
    })


@app.route('/api/day/times/<time_id>/atmospheres', methods=['POST'])
@app.route('/api/day/time-periods/<time_id>', methods=['POST'])
def update_time_atmospheres(time_id):
    """Update atmospheres for a specific time period."""
    try:
        if time_id not in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']:
            return jsonify({'error': 'Invalid time ID'}), 400

        data = request.json
        if data is None:
            return jsonify({'error': 'No JSON data provided'}), 400

        atmospheres = data.get('atmospheres', [])

        settings = get_settings()
        day_times = settings.get('day_times', {})

        if time_id not in day_times:
            return jsonify({'error': 'Time period not found'}), 404

        # Update atmospheres for this time
        day_times[time_id]['atmospheres'] = atmospheres

        # Handle mirroring: update all mirrored times
        # Times 1-6 are the source, times 7-12 mirror them
        mirror_groups = {
            '1': ['7'],   # 6 AM mirrors at 6 PM
            '2': ['8'],   # 8 AM mirrors at 8 PM
            '3': ['9'],   # 10 AM mirrors at 10 PM
            '4': ['10'],  # 12 PM mirrors at 12 AM
            '5': ['11'],  # 2 PM mirrors at 2 AM
            '6': ['12']   # 4 PM mirrors at 4 AM
        }

        mirrored_ids = []

        # If updating a source time (1-6), update its mirror
        if time_id in mirror_groups:
            for mirror_id in mirror_groups[time_id]:
                if mirror_id in day_times:  # Only update if mirror exists
                    day_times[mirror_id]['atmospheres'] = atmospheres
                    mirrored_ids.append(mirror_id)
        # If updating a mirror time (7-12), update the source
        else:
            # Find which source this mirrors
            source_map = {
                '7': '1', '8': '2', '9': '3',
                '10': '4', '11': '5', '12': '6'
            }
            source_id = source_map.get(time_id)
            if source_id:
                # Update source
                if source_id in day_times:  # Only update if source exists
                    day_times[source_id]['atmospheres'] = atmospheres
                    mirrored_ids.append(source_id)
                # Update the mirror (if not self)
                for mirror_id in mirror_groups[source_id]:
                    if mirror_id != time_id and mirror_id in day_times:  # Only update if mirror exists
                        day_times[mirror_id]['atmospheres'] = atmospheres
                        mirrored_ids.append(mirror_id)

        settings['day_times'] = day_times

        # Regenerate shuffle_id when changing time atmospheres
        settings['shuffle_id'] = random.random()

        save_settings(settings)

        return jsonify({
            'success': True,
            'time_id': time_id,
            'atmospheres': atmospheres,
            'mirrored_ids': mirrored_ids
        })
    except Exception as e:
        import traceback
        print(f"Error in update_time_atmospheres: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500


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


# ============================================================================
# VIDEO URL MANAGEMENT (Experimental)
# ============================================================================

@app.route('/api/videos', methods=['GET'])
def list_videos():
    """Get list of all video URLs."""
    settings = get_settings()
    videos = settings.get('video_urls', [])
    return jsonify(videos)


@app.route('/api/videos', methods=['POST'])
def add_video():
    """Add a video URL.
    Request: {"url": "https://..."}
    """
    data = request.get_json()
    url = data.get('url', '').strip()

    if not url:
        return jsonify({'error': 'URL is required'}), 400

    settings = get_settings()
    videos = settings.get('video_urls', [])

    # Generate unique ID
    video_id = str(uuid.uuid4())

    # Add video
    video = {
        'id': video_id,
        'url': url,
        'created': time.time()
    }
    videos.append(video)
    settings['video_urls'] = videos

    # Enable the video by default
    enabled_videos = settings.get('enabled_videos', {})
    enabled_videos[video_id] = True
    settings['enabled_videos'] = enabled_videos

    # Assign the new video to the active theme (if not "All Images")
    active_theme = settings.get('active_theme')
    if active_theme and active_theme != 'All Images':
        video_themes = settings.get('video_themes', {})
        video_themes[video_id] = [active_theme]
        settings['video_themes'] = video_themes

    save_settings(settings)
    socketio.emit('settings_update', settings)

    return jsonify(video)


@app.route('/api/videos/<video_id>', methods=['DELETE'])
def delete_video(video_id):
    """Delete a video URL and its thumbnail."""
    settings = get_settings()
    videos = settings.get('video_urls', [])

    # Find and remove video
    videos = [v for v in videos if v.get('id') != video_id]
    settings['video_urls'] = videos

    # Clean up enabled_videos
    enabled_videos = settings.get('enabled_videos', {})
    if video_id in enabled_videos:
        del enabled_videos[video_id]
        settings['enabled_videos'] = enabled_videos

    # Clean up video_themes
    video_themes = settings.get('video_themes', {})
    if video_id in video_themes:
        del video_themes[video_id]
        settings['video_themes'] = video_themes

    # Delete the thumbnail if it exists
    thumbnail_path = THUMBNAILS_FOLDER / f"{video_id}.png"
    if thumbnail_path.exists():
        thumbnail_path.unlink()
        print(f"Deleted thumbnail: {thumbnail_path}")

    save_settings(settings)
    socketio.emit('settings_update', settings)

    return jsonify({'success': True})


@app.route('/api/videos/<video_id>/themes', methods=['POST'])
def update_video_themes(video_id):
    """Update themes for a video (like images).
    Request: {"themes": ["Theme1", "Theme2"]}
    """
    data = request.get_json()
    themes = data.get('themes', [])

    settings = get_settings()
    video_themes = settings.get('video_themes', {})
    video_themes[video_id] = themes
    settings['video_themes'] = video_themes

    save_settings(settings)
    socketio.emit('settings_update', settings)

    return jsonify({'success': True, 'themes': themes})


@app.route('/api/videos/<video_id>/toggle', methods=['POST'])
def toggle_video(video_id):
    """Toggle enabled state for a video."""
    settings = get_settings()
    enabled_videos = settings.get('enabled_videos', {})

    # Toggle the state (default to True if not set)
    current_state = enabled_videos.get(video_id, True)
    enabled_videos[video_id] = not current_state
    settings['enabled_videos'] = enabled_videos

    save_settings(settings)
    socketio.emit('settings_update', settings)

    return jsonify({'success': True, 'enabled': enabled_videos[video_id]})


@app.route('/api/videos/<video_id>/generate-thumbnail', methods=['POST'])
def generate_thumbnail(video_id):
    """Generate a thumbnail for a video by playing it and taking a screenshot.
    This will start the video, wait 20 seconds for it to load, take a screenshot,
    and leave the video playing.
    """
    import subprocess
    import threading

    settings = get_settings()
    videos = settings.get('video_urls', [])
    video = next((v for v in videos if v.get('id') == video_id), None)

    if not video:
        return jsonify({'error': 'Video not found'}), 404

    def generate_thumbnail_async():
        try:
            import time

            print(f"Generating thumbnail for video: {video['url']}")

            # STEP 1: Start playing the video using execute-mpv endpoint
            # This will handle showing the loading screen and starting mpv
            url = video['url']

            # Navigate to loading page
            with app.app_context():
                socketio.emit('show_loading')
            time.sleep(0.5)

            # Kill any existing mpv
            subprocess.run(['pkill', '-9', 'mpv'], check=False)
            time.sleep(0.3)

            # Start mpv
            print(f"Starting mpv for thumbnail generation...")
            mpv_env = os.environ.copy()
            mpv_env['DISPLAY'] = ':0'
            mpv_proc = subprocess.Popen([
                'mpv',
                '--vo=x11',
                '--fullscreen',
                '--loop-file=inf',
                '--no-audio',
                '--ytdl-format=bestvideo[height<=720]+bestaudio/best',
                '--hwdec=auto',
                '--cache=auto',
                '--panscan=1.0',
                url
            ], env=mpv_env)

            print(f"MPV started with PID: {mpv_proc.pid}")

            # Update current video ID and notify UI that video is playing
            global current_video_id
            current_video_id = video_id
            settings = get_settings()
            settings['current_video_id'] = video_id
            save_settings(settings)

            with app.app_context():
                socketio.emit('video_started', {'video_id': video_id})

            # STEP 2: Take screenshot with retry if mostly black
            thumbnail_path = THUMBNAILS_FOLDER / f"{video_id}.png"
            max_retries = 2

            for attempt in range(max_retries + 1):
                # Wait for video to load
                wait_time = 10 if attempt == 0 else 5
                print(f"Waiting {wait_time} seconds for video to load (attempt {attempt + 1}/{max_retries + 1})...")
                time.sleep(wait_time)

                # Take screenshot
                print(f"Taking screenshot to: {thumbnail_path}")
                result = subprocess.run([
                    'scrot',
                    str(thumbnail_path)
                ], env={'DISPLAY': ':0'}, capture_output=True)

                if result.returncode == 0:
                    # Check if thumbnail is mostly black
                    if is_thumbnail_mostly_black(thumbnail_path):
                        if attempt < max_retries:
                            print(f"Thumbnail is mostly black, retrying...")
                            # Delete the black thumbnail before retrying
                            if thumbnail_path.exists():
                                thumbnail_path.unlink()
                            continue
                        else:
                            print(f"Thumbnail still mostly black after {max_retries + 1} attempts, keeping it anyway")

                    print(f"Thumbnail saved successfully: {thumbnail_path}")
                    # Emit event to notify frontend that thumbnail is ready
                    with app.app_context():
                        socketio.emit('thumbnail_generated', {'video_id': video_id})
                    break
                else:
                    print(f"Failed to generate thumbnail: {result.stderr}")
                    break

            # STEP 3: Video is left playing for preview
            print("Video left playing for preview")

        except Exception as e:
            print(f"Error generating thumbnail: {e}")
            import traceback
            traceback.print_exc()

    # Start thumbnail generation in background thread
    thread = threading.Thread(target=generate_thumbnail_async, daemon=True)
    thread.start()

    return jsonify({'success': True, 'message': 'Thumbnail generation started...'})


@app.route('/thumbnails/<filename>')
def serve_thumbnail(filename):
    """Serve video thumbnails."""
    return send_from_directory(THUMBNAILS_FOLDER, filename)


@app.route('/api/videos/<video_id>/play', methods=['POST'])
def play_video(video_id):
    """Play a video using mpv (legacy endpoint - redirects to execute-mpv).
    """
    import threading

    settings = get_settings()
    videos = settings.get('video_urls', [])

    # Find video
    video = next((v for v in videos if v.get('id') == video_id), None)
    if not video:
        return jsonify({'error': 'Video not found'}), 404

    def launch_mpv_async():
        """Launch mpv in background thread to avoid blocking the response."""
        try:
            import time
            # STEP 1: Navigate Firefox to loading page via WebSocket
            print("Showing loading page...")
            with app.app_context():
                socketio.emit('show_loading')
            time.sleep(0.5)

            # STEP 2: Kill existing mpv
            print("Killing any existing mpv...")
            subprocess.run(['pkill', '-9', 'mpv'], check=False)
            time.sleep(0.3)

            # STEP 3: Launch mpv with exact same settings as working kiosk
            print(f"Launching mpv with video: {video['url']}")
            mpv_env = os.environ.copy()
            mpv_env['DISPLAY'] = ':0'
            mpv_proc = subprocess.Popen([
                'mpv',
                '--fullscreen',
                '--no-osd-bar',
                '--osd-level=0',
                '--no-border',
                '--loop-file=inf',
                '--ytdl-format=best',
                '--hwdec=auto',
                '--no-keepaspect',
                '--video-unscaled=no',
                '--no-audio',
                '--mute=yes',
                video['url']
            ], env=mpv_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"MPV process started with PID: {mpv_proc.pid}")

            print("MPV launch command sent")

            # STEP 4: Wait a moment for mpv to start, then navigate Firefox back to kiosk view in background
            time.sleep(2)
            print("Navigating Firefox back to kiosk view in background...")
            with app.app_context():
                socketio.emit('show_kiosk')

        except Exception as e:
            print(f"Error executing mpv: {e}")
            import traceback
            traceback.print_exc()

    # Start mpv in background thread
    thread = threading.Thread(target=launch_mpv_async, daemon=True)
    thread.start()

    # Return immediately
    return jsonify({'success': True, 'message': 'Video playback starting...'})


def cancel_video_transition_timer():
    """Cancel any pending video auto-transition timer."""
    global video_transition_timer
    if video_transition_timer:
        video_transition_timer.cancel()
        video_transition_timer = None


def start_video_transition_timer():
    """Start a timer to auto-transition after the video interval expires."""
    import threading
    import subprocess

    global video_transition_timer

    # Cancel any existing timer
    cancel_video_transition_timer()

    # Get the current interval from settings
    settings = get_settings()
    interval_seconds = settings.get('interval', 3600)

    print(f"Starting video auto-transition timer for {interval_seconds} seconds", flush=True)

    def auto_transition():
        """Called when video interval expires - transition to next item."""
        global video_transition_timer, current_video_id, video_next_item
        video_transition_timer = None

        print(f"Video auto-transition timer fired after {interval_seconds} seconds", flush=True)

        # Stop mpv
        subprocess.run(['pkill', '-9', 'mpv'], check=False)
        current_video_id = None

        # Update settings to clear current video
        settings = get_settings()
        settings['current_video_id'] = None
        save_settings(settings)

        # Navigate Firefox back to kiosk view with the next item
        # Pass the next item name so kiosk continues from where it left off
        next_item = video_next_item
        video_next_item = None

        with app.app_context():
            if next_item:
                print(f"Navigating to next item: {next_item}", flush=True)
                socketio.emit('show_kiosk', {'start_image': next_item})
            else:
                socketio.emit('show_kiosk', {})

        print("Video auto-transition complete", flush=True)

    video_transition_timer = threading.Timer(interval_seconds, auto_transition)
    video_transition_timer.daemon = True
    video_transition_timer.start()


@app.route('/api/videos/execute-mpv', methods=['POST'])
def execute_mpv():
    """Execute mpv to play a video using IPC mode for better control.
    This will stop Firefox (kiosk display) and start mpv.
    """
    import subprocess
    import os
    import threading
    import sys

    print("========== execute_mpv() CALLED ==========", flush=True)

    global mpv_process, current_video_id, video_next_item

    data = request.get_json()
    url = data.get('url')
    video_id = data.get('video_id') or data.get('title')  # Get video ID from request (kiosk sends 'title')
    print(f"URL: {url}, Video ID: {video_id}", flush=True)

    # Store the current video ID in memory and persist to settings
    current_video_id = video_id
    settings = get_settings()
    settings['current_video_id'] = video_id
    save_settings(settings)

    # Calculate the next item in the list for auto-transition
    if video_id:
        try:
            # Get enabled images list (same as what kiosk sees)
            # We need to make a request to our own endpoint to get the properly filtered list
            import requests as req
            images_resp = req.get('http://localhost/api/images?enabled_only=true', timeout=5)
            images = images_resp.json()

            # Find video index and calculate next item
            video_index = None
            for i, item in enumerate(images):
                if item.get('name') == video_id:
                    video_index = i
                    break

            if video_index is not None and len(images) > 1:
                next_index = (video_index + 1) % len(images)
                video_next_item = images[next_index].get('name')
                print(f"Next item after video: {video_next_item} (index {next_index})", flush=True)
            else:
                video_next_item = None
                print(f"Could not find video in list or list too short", flush=True)
        except Exception as e:
            print(f"Error calculating next item: {e}", flush=True)
            video_next_item = None
    else:
        video_next_item = None

    if not url:
        return jsonify({'error': 'URL is required'}), 400

    print("About to create thread for launch_mpv_async...", flush=True)

    def launch_mpv_async():
        """Launch mpv in background thread to avoid blocking the response."""
        try:
            import time
            import sys

            # STEP 1: Navigate Firefox to loading page via WebSocket
            print("Showing loading page...", flush=True)
            with app.app_context():
                socketio.emit('show_loading')
            time.sleep(0.5)

            # STEP 2: Kill existing mpv
            print("Killing any existing mpv...", flush=True)
            subprocess.run(['pkill', '-9', 'mpv'], check=False)
            time.sleep(0.3)

            # STEP 3: Launch mpv with working configuration for Raspberry Pi 5
            # Uses x11 video output for compatibility, limits format to reduce CPU load
            # Disables audio to reduce CPU usage further
            print(f"Launching mpv with video: {url}", flush=True)
            mpv_env = os.environ.copy()
            mpv_env['DISPLAY'] = ':0'
            mpv_proc = subprocess.Popen([
                'mpv',
                '--vo=x11',
                '--fullscreen',
                '--loop-file=inf',
                '--no-audio',
                '--ytdl-format=bestvideo[height<=720]+bestaudio/best',
                '--hwdec=auto',
                '--cache=auto',
                '--panscan=1.0',  # Crop video to fill screen (portrait mode)
                url
            ], env=mpv_env)

            print(f"MPV STARTED WITH PID: {mpv_proc.pid}", flush=True)
            print(f"Started mpv with video: {url}", flush=True)

            # Check if mpv is still running after a brief moment
            time.sleep(0.5)
            poll_result = mpv_proc.poll()
            if poll_result is not None:
                print(f"WARNING: MPV exited immediately with code: {poll_result}", flush=True)
            else:
                print(f"MPV process still running (PID: {mpv_proc.pid})", flush=True)

            # STEP 4: Wait for mpv window to appear and bring it to front using xdotool
            print("Waiting for mpv window to appear...", flush=True)
            time.sleep(2)

            # Use xdotool to find and focus the mpv window
            print("Bringing mpv window to front with xdotool...", flush=True)
            subprocess.run(['xdotool', 'search', '--class', 'mpv', 'windowactivate'], check=False)
            time.sleep(0.5)
            print("MPV window should now be in front", flush=True)

            # Emit event to notify UI that video is playing
            with app.app_context():
                socketio.emit('video_playing', {'status': 'playing'})

            # Start the auto-transition timer
            start_video_transition_timer()

            # Generate thumbnail if it doesn't exist
            if video_id:
                thumbnail_path = THUMBNAILS_FOLDER / f"{video_id}.png"
                if not thumbnail_path.exists():
                    print(f"No thumbnail for video {video_id}, generating one...")
                    max_retries = 2

                    for attempt in range(max_retries + 1):
                        # Wait for video to load
                        wait_time = 10 if attempt == 0 else 5
                        print(f"Waiting {wait_time}s for thumbnail (attempt {attempt + 1}/{max_retries + 1})...")
                        time.sleep(wait_time)

                        # Take screenshot
                        result = subprocess.run([
                            'scrot',
                            str(thumbnail_path)
                        ], env={'DISPLAY': ':0'}, capture_output=True)

                        if result.returncode == 0:
                            # Check if thumbnail is mostly black
                            if is_thumbnail_mostly_black(thumbnail_path):
                                if attempt < max_retries:
                                    print(f"Thumbnail is mostly black, retrying...")
                                    # Delete the black thumbnail before retrying
                                    if thumbnail_path.exists():
                                        thumbnail_path.unlink()
                                    continue
                                else:
                                    print(f"Thumbnail still mostly black, keeping it anyway")

                            print(f"Thumbnail saved: {thumbnail_path}")
                            with app.app_context():
                                socketio.emit('thumbnail_generated', {'video_id': video_id})
                            break
                        else:
                            print(f"Failed to generate thumbnail: {result.stderr}")
                            break

        except Exception as e:
            print(f"Error launching mpv: {e}", flush=True)
            import traceback
            traceback.print_exc()

    # Start mpv in background thread
    print("Creating thread...", flush=True)
    thread = threading.Thread(target=launch_mpv_async, daemon=True)
    print(f"Thread created: {thread}", flush=True)
    print("Starting thread...", flush=True)
    thread.start()
    print("Thread started!", flush=True)

    # Return immediately
    return jsonify({'success': True, 'message': 'Video playback starting...'})


@app.route('/api/videos/stop-mpv', methods=['POST'])
def stop_mpv():
    """Stop mpv video playback and restore Firefox kiosk display."""
    import subprocess
    import threading

    global mpv_process, current_video_id

    # Cancel any pending auto-transition timer
    cancel_video_transition_timer()

    # Get optional jump_to parameter
    data = request.get_json(silent=True) or {}
    jump_to_image = data.get('jump_to')

    def stop_mpv_async(target_image):
        """Stop mpv and restore Firefox in background thread."""
        try:
            import time

            # STEP 1: Kill mpv process
            print("Killing mpv...")
            global mpv_process, current_video_id
            if mpv_process is not None:
                try:
                    mpv_process.terminate()
                    mpv_process.wait(timeout=2)
                except:
                    mpv_process.kill()
                mpv_process = None
                print("Terminated mpv process")

            # Clear the current video ID from memory and settings
            current_video_id = None
            settings = get_settings()
            settings['current_video_id'] = None
            save_settings(settings)

            # Also kill any lingering mpv processes
            subprocess.run(['pkill', '-9', 'mpv'], check=False)
            time.sleep(0.3)

            # STEP 2: Navigate Firefox to kiosk view with target image
            if target_image:
                print(f"Showing kiosk view with target: {target_image}")
                socketio.emit('show_kiosk', {'start_image': target_image})
                time.sleep(1.5)  # Wait for kiosk.html to load with target image
            else:
                print("Showing kiosk view...")
                socketio.emit('show_kiosk')

            # STEP 4: Bring Firefox window to foreground (after new image is ready)
            print("Bringing Firefox to foreground...")
            subprocess.run([
                'bash', '-c',
                'DISPLAY=:0 xdotool search --name Firefox windowactivate'
            ], check=False)

            # Emit event to notify UI that video stopped
            socketio.emit('video_stopped', {'status': 'stopped'})

            print("Kiosk view restored")
        except Exception as e:
            print(f"Error stopping mpv: {e}")
            import traceback
            traceback.print_exc()

    # Start stop process in background thread
    thread = threading.Thread(target=stop_mpv_async, args=(jump_to_image,), daemon=True)
    thread.start()

    # Return immediately
    return jsonify({'success': True, 'message': 'Stopping video...'})


### Test Mode API Endpoints (for automated testing)

@app.route('/api/test/enable', methods=['POST'])
def enable_test_mode():
    """Enable test mode for automated testing."""
    test_mode['enabled'] = True
    socketio.emit('test_mode_enabled', test_mode)
    return jsonify({
        'success': True,
        'test_mode': test_mode
    })


@app.route('/api/test/disable', methods=['POST'])
def disable_test_mode():
    """Disable test mode and reset all overrides."""
    test_mode['enabled'] = False
    test_mode['mock_time'] = None
    test_mode['force_interval'] = None
    test_mode['force_check_interval'] = None
    socketio.emit('test_mode_disabled')
    return jsonify({
        'success': True,
        'test_mode': test_mode
    })


@app.route('/api/test/time', methods=['POST'])
def set_mock_time():
    """Set mock time for testing time-dependent features.
    Request: {"timestamp": 1234567890} (Unix timestamp)
    """
    data = request.get_json()
    test_mode['mock_time'] = data.get('timestamp')

    # Broadcast time change to trigger kiosk updates
    socketio.emit('test_time_changed', {
        'timestamp': test_mode['mock_time']
    })

    return jsonify({
        'success': True,
        'mock_time': test_mode['mock_time'],
        'current_time_period': get_current_time_period()
    })


@app.route('/api/test/intervals', methods=['POST'])
def set_test_intervals():
    """Override slideshow and check intervals for faster testing.
    Request: {
        "slideshow_interval": 1000,  // milliseconds
        "check_interval": 500         // milliseconds
    }
    """
    data = request.get_json()
    test_mode['force_interval'] = data.get('slideshow_interval')
    test_mode['force_check_interval'] = data.get('check_interval')

    # Broadcast interval change to kiosk
    socketio.emit('test_intervals_changed', {
        'slideshow_interval': test_mode['force_interval'],
        'check_interval': test_mode['force_check_interval']
    })

    return jsonify({
        'success': True,
        'force_interval': test_mode['force_interval'],
        'force_check_interval': test_mode['force_check_interval']
    })


@app.route('/api/test/status', methods=['GET'])
def get_test_status():
    """Get current test mode status."""
    return jsonify({
        'test_mode': test_mode,
        'current_time_period': get_current_time_period() if test_mode['enabled'] else None
    })


@app.route('/api/test/trigger-hour-boundary', methods=['POST'])
def trigger_hour_boundary():
    """Manually trigger hour boundary check (for testing).
    Broadcasts event to kiosk to check hour boundary immediately.
    """
    socketio.emit('test_trigger_hour_check')
    return jsonify({'success': True})


@app.route('/api/test/trigger-slideshow-advance', methods=['POST'])
def trigger_slideshow_advance():
    """Manually advance slideshow to next image (for testing)."""
    socketio.emit('remote_command', {'command': 'next'})
    return jsonify({'success': True})


def monitor_hour_changes():
    """Background thread to monitor hour changes and emit WebSocket events."""
    import threading

    last_time_period = None

    while True:
        try:
            settings = get_settings()
            if settings.get('day_scheduling_enabled'):
                current_period = get_current_time_period()

                if last_time_period is not None and last_time_period != current_period:
                    # Hour boundary crossed - emit event
                    socketio.emit('hour_boundary_changed', {
                        'previous_period': last_time_period,
                        'current_period': current_period
                    })

                last_time_period = current_period
        except Exception as e:
            print(f"Error in hour monitor: {e}")

        # Check every 30 seconds
        time.sleep(30)

@app.route('/api/videos/playback-status', methods=['GET'])
def get_playback_status():
    """Get current video playback status."""
    import subprocess
    global mpv_process, current_video_id

    # Check if mpv is actually running (handles server restarts)
    try:
        result = subprocess.run(['pgrep', '-x', 'mpv'], capture_output=True, text=True)
        is_playing = result.returncode == 0  # pgrep returns 0 if process found
    except:
        is_playing = False

    # Get video_id from settings if not in memory (handles server restarts)
    if current_video_id is None:
        settings = get_settings()
        current_video_id = settings.get('current_video_id')

    return jsonify({
        'playing': is_playing,
        'video_id': current_video_id if is_playing else None
    })


# ====================================================================
# BACKUP AND RESTORE
# ====================================================================

BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
MAX_BACKUPS = 3  # Regular backups
MAX_TESTING_BACKUPS = 2  # Testing backups (separate from regular)
TESTING_BACKUP_PREFIX = 'kiosk_testing_backup_'
REGULAR_BACKUP_PREFIX = 'kiosk_backup_'

@app.route('/backup')
def backup_page():
    """Serve the backup management page."""
    return render_template('backup.html')


@app.route('/api/backups', methods=['GET'])
def list_backups():
    """List all available backups."""
    if not os.path.exists(BACKUP_DIR):
        return jsonify({'backups': []})

    backups = []
    for filename in os.listdir(BACKUP_DIR):
        if filename.endswith('.tgz'):
            filepath = os.path.join(BACKUP_DIR, filename)
            stat = os.stat(filepath)
            backups.append({
                'name': filename,
                'size': stat.st_size,
                'created': stat.st_mtime,
                'created_formatted': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))
            })

    # Sort by creation time, newest first
    backups.sort(key=lambda x: x['created'], reverse=True)
    return jsonify({'backups': backups})


@app.route('/api/backup', methods=['POST'])
def create_backup():
    """Create a new backup of settings, images, and extra-images."""
    import tarfile
    import tempfile

    # Check if this is a testing backup
    data = request.get_json(silent=True) or {}
    is_testing = data.get('testing', False)

    # Ensure backup directory exists
    os.makedirs(BACKUP_DIR, exist_ok=True)

    # Generate backup filename with timestamp
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    if is_testing:
        backup_name = f'{TESTING_BACKUP_PREFIX}{timestamp}.tgz'
    else:
        backup_name = f'{REGULAR_BACKUP_PREFIX}{timestamp}.tgz'
    backup_path = os.path.join(BACKUP_DIR, backup_name)

    try:
        with tarfile.open(backup_path, 'w:gz') as tar:
            # Add settings.json
            if os.path.exists(SETTINGS_FILE):
                tar.add(SETTINGS_FILE, arcname='settings.json')

            # Add images directory
            upload_folder = str(app.config['UPLOAD_FOLDER'])
            if os.path.exists(upload_folder):
                for filename in os.listdir(upload_folder):
                    filepath = os.path.join(upload_folder, filename)
                    if os.path.isfile(filepath):
                        tar.add(filepath, arcname=f'images/{filename}')

            # Add extra-images directory
            extra_images_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'EXTRA_IMAGES')
            if os.path.exists(extra_images_dir):
                for filename in os.listdir(extra_images_dir):
                    filepath = os.path.join(extra_images_dir, filename)
                    if os.path.isfile(filepath):
                        tar.add(filepath, arcname=f'EXTRA_IMAGES/{filename}')

            # Add thumbnails directory (video thumbnails)
            if THUMBNAILS_FOLDER.exists():
                for filename in os.listdir(THUMBNAILS_FOLDER):
                    filepath = THUMBNAILS_FOLDER / filename
                    if filepath.is_file():
                        tar.add(str(filepath), arcname=f'thumbnails/{filename}')

        # Get backup size
        backup_size = os.path.getsize(backup_path)

        # Clean up old backups (keep only MAX_BACKUPS for regular, MAX_TESTING_BACKUPS for testing)
        cleanup_old_backups(is_testing)

        return jsonify({
            'success': True,
            'backup': {
                'name': backup_name,
                'size': backup_size,
                'created': os.path.getmtime(backup_path),
                'created_formatted': time.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def cleanup_old_backups(is_testing=False):
    """Remove old backups, keeping only the newest MAX_BACKUPS (regular) or MAX_TESTING_BACKUPS (testing)."""
    if not os.path.exists(BACKUP_DIR):
        return

    # Separate regular and testing backups
    regular_backups = []
    testing_backups = []

    for filename in os.listdir(BACKUP_DIR):
        if filename.endswith('.tgz'):
            filepath = os.path.join(BACKUP_DIR, filename)
            mtime = os.path.getmtime(filepath)
            if filename.startswith(TESTING_BACKUP_PREFIX):
                testing_backups.append((filepath, mtime))
            elif filename.startswith(REGULAR_BACKUP_PREFIX):
                regular_backups.append((filepath, mtime))

    # Sort by modification time, oldest first
    regular_backups.sort(key=lambda x: x[1])
    testing_backups.sort(key=lambda x: x[1])

    # Remove oldest regular backups if we have more than MAX_BACKUPS
    while len(regular_backups) > MAX_BACKUPS:
        oldest = regular_backups.pop(0)
        try:
            os.remove(oldest[0])
            print(f"Removed old regular backup: {oldest[0]}")
        except Exception as e:
            print(f"Error removing old backup {oldest[0]}: {e}")

    # Remove oldest testing backups if we have more than MAX_TESTING_BACKUPS
    while len(testing_backups) > MAX_TESTING_BACKUPS:
        oldest = testing_backups.pop(0)
        try:
            os.remove(oldest[0])
            print(f"Removed old testing backup: {oldest[0]}")
        except Exception as e:
            print(f"Error removing old backup {oldest[0]}: {e}")


@app.route('/api/backup/restore/<backup_name>', methods=['POST'])
def restore_backup(backup_name):
    """Restore from a backup file."""
    import tarfile
    import shutil

    backup_path = os.path.join(BACKUP_DIR, backup_name)

    if not os.path.exists(backup_path):
        return jsonify({'success': False, 'error': 'Backup not found'}), 404

    try:
        with tarfile.open(backup_path, 'r:gz') as tar:
            # Extract to a temporary directory first
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                tar.extractall(tmpdir)

                # Restore settings.json
                settings_src = os.path.join(tmpdir, 'settings.json')
                if os.path.exists(settings_src):
                    shutil.copy2(settings_src, SETTINGS_FILE)

                # Restore images
                images_src = os.path.join(tmpdir, 'images')
                upload_folder = str(app.config['UPLOAD_FOLDER'])
                if os.path.exists(images_src):
                    # Clear existing images
                    if os.path.exists(upload_folder):
                        for f in os.listdir(upload_folder):
                            os.remove(os.path.join(upload_folder, f))
                    else:
                        os.makedirs(upload_folder, exist_ok=True)

                    # Copy restored images
                    for filename in os.listdir(images_src):
                        src = os.path.join(images_src, filename)
                        dst = os.path.join(upload_folder, filename)
                        shutil.copy2(src, dst)

                # Restore extra-images
                extra_src = os.path.join(tmpdir, 'EXTRA_IMAGES')
                extra_dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'EXTRA_IMAGES')
                if os.path.exists(extra_src):
                    # Clear existing extra images
                    if os.path.exists(extra_dst):
                        for f in os.listdir(extra_dst):
                            os.remove(os.path.join(extra_dst, f))
                    else:
                        os.makedirs(extra_dst, exist_ok=True)

                    # Copy restored extra images
                    for filename in os.listdir(extra_src):
                        src = os.path.join(extra_src, filename)
                        dst = os.path.join(extra_dst, filename)
                        shutil.copy2(src, dst)

                # Restore thumbnails (video thumbnails)
                thumbnails_src = os.path.join(tmpdir, 'thumbnails')
                if os.path.exists(thumbnails_src):
                    # Clear existing thumbnails
                    if THUMBNAILS_FOLDER.exists():
                        for f in os.listdir(THUMBNAILS_FOLDER):
                            os.remove(THUMBNAILS_FOLDER / f)
                    else:
                        THUMBNAILS_FOLDER.mkdir(exist_ok=True)

                    # Copy restored thumbnails
                    for filename in os.listdir(thumbnails_src):
                        src = os.path.join(thumbnails_src, filename)
                        dst = THUMBNAILS_FOLDER / filename
                        shutil.copy2(src, dst)

        # Emit multiple events to ensure kiosk picks up the restored settings/images
        socketio.emit('remote_command', {'command': 'reload'})
        socketio.emit('image_list_changed')
        socketio.emit('settings_update', {})

        return jsonify({
            'success': True,
            'message': f'Restored from {backup_name}'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/backup/<backup_name>', methods=['DELETE'])
def delete_backup(backup_name):
    """Delete a specific backup."""
    backup_path = os.path.join(BACKUP_DIR, backup_name)

    if not os.path.exists(backup_path):
        return jsonify({'success': False, 'error': 'Backup not found'}), 404

    try:
        os.remove(backup_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


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

    # Start background thread to monitor hour changes
    import threading
    hour_monitor_thread = threading.Thread(target=monitor_hour_changes, daemon=True)
    hour_monitor_thread.start()
    print("Started hour boundary monitor thread")

    # Run on all interfaces, port 80
    socketio.run(app, host='0.0.0.0', port=80, debug=False, allow_unsafe_werkzeug=True)
