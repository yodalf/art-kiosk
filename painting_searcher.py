#!/usr/bin/env python3
"""
High-Resolution Portrait Painting Image Searcher
Searches multiple free sources for portrait paintings with resolution >= 1200x1400
"""

import requests
import json
import time
import os
import random
from typing import List, Dict, Tuple, Optional
from urllib.parse import quote
import re
from datetime import datetime
from pathlib import Path

class PaintingSearcher:
    def __init__(self, min_width: int = 1280, min_height: int = 1440, min_aspect_ratio_match: float = 85.0,
                 config_file: str = "sources_config.json", api_keys_file: str = "api_keys.json"):
        """
        Initialize the painting searcher with configurable parameters.

        Args:
            min_width: Minimum image width in pixels (default: 1280, half of 2560)
            min_height: Minimum image height in pixels (default: 1440, half of 2880)
            min_aspect_ratio_match: Minimum aspect ratio match percentage (default: 85.0)
            config_file: Path to sources configuration file
            api_keys_file: Path to API keys file
        """
        # Target display: 2560x2880 portrait mode
        self.min_width = min_width
        self.min_height = min_height
        self.min_aspect_ratio_match = min_aspect_ratio_match
        self.target_aspect_ratio = 2560 / 2880  # 0.889
        self.results = []

        # Load sources configuration
        self.sources_config = self._load_sources_config(config_file)
        self.api_keys = self._load_api_keys(api_keys_file)

    def _load_sources_config(self, config_file: str) -> Dict:
        """Load sources configuration from JSON file"""
        config_path = Path(config_file)
        if not config_path.exists():
            print(f"⚠️  Warning: {config_file} not found, using built-in sources only")
            return {"sources": {}, "default_settings": {}}

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                print(f"✅ Loaded sources configuration from {config_file}")

                # Show enabled sources
                enabled_sources = [name for name, source in config.get('sources', {}).items()
                                 if source.get('enabled', False)]
                if enabled_sources:
                    print(f"   Enabled sources: {', '.join(enabled_sources)}")

                return config
        except Exception as e:
            print(f"❌ Error loading {config_file}: {e}")
            return {"sources": {}, "default_settings": {}}

    def _load_api_keys(self, api_keys_file: str) -> Dict:
        """Load API keys from JSON file"""
        keys_path = Path(api_keys_file)
        if not keys_path.exists():
            print(f"ℹ️  {api_keys_file} not found - using template values only")
            print(f"   Copy {api_keys_file}.template to {api_keys_file} and add your API keys")
            return {}

        try:
            with open(keys_path, 'r') as f:
                keys = json.load(f)
                # Filter out comment fields
                api_keys = {k: v for k, v in keys.items() if not k.startswith('_')}
                print(f"✅ Loaded API keys from {api_keys_file}")
                return api_keys
        except Exception as e:
            print(f"❌ Error loading {api_keys_file}: {e}")
            return {}

    def get_api_key(self, key_name: str) -> Optional[str]:
        """Get an API key by name"""
        key = self.api_keys.get(key_name, '')
        if not key:
            print(f"⚠️  API key '{key_name}' not found or empty")
        return key if key else None
        
    def check_resolution(self, width: int, height: int) -> bool:
        """Check if image meets minimum resolution requirements"""
        return width >= self.min_width and height >= self.min_height
    
    def is_portrait_orientation(self, width: int, height: int) -> bool:
        """Check if image is in portrait orientation (height > width)"""
        return height > width

    def get_aspect_ratio_match(self, width: int, height: int) -> Tuple[float, float]:
        """
        Calculate how well the image aspect ratio matches the target display.
        Returns (aspect_ratio, match_score) where match_score is 0-100 (100 = perfect match)
        """
        if height == 0:
            return (0, 0)

        aspect_ratio = width / height

        # Calculate how close to target (0.889)
        difference = abs(aspect_ratio - self.target_aspect_ratio)
        # Convert to percentage match (allowing up to 20% difference)
        match_score = max(0, 100 - (difference / self.target_aspect_ratio * 100))

        return (aspect_ratio, match_score)

    def is_acceptable_aspect_ratio(self, width: int, height: int) -> bool:
        """
        Check if the aspect ratio is acceptable for the target display.
        Uses the configured min_aspect_ratio_match threshold
        Also strictly rejects landscape images (width > height)
        """
        if height == 0:
            return False

        # Strict landscape rejection
        if width >= height:
            return False

        _, match_score = self.get_aspect_ratio_match(width, height)
        return match_score >= self.min_aspect_ratio_match
    
    def search_met_museum(self, query: str = "portrait", limit: int = 20) -> List[Dict]:
        """
        Search Metropolitan Museum API for high-resolution paintings
        API: https://metmuseum.github.io/
        Note: Met Museum API doesn't provide dimensions, so aspect ratio cannot be pre-filtered
        """
        results = []
        print(f"\n🎨 Searching Metropolitan Museum Collection...")
        print(f"  ⚠️  Note: Met Museum results cannot be pre-filtered by aspect ratio")
        
        try:
            # Search for objects
            search_url = f"https://collectionapi.metmuseum.org/public/collection/v1/search"
            params = {
                'q': query,
                'hasImages': 'true',
                'medium': 'Paintings',
                'departmentId': '11|14|21'  # American, European, Modern Art
            }
            
            response = requests.get(search_url, params=params, timeout=10)
            if response.status_code != 200:
                print(f"  ❌ Failed to search Met Museum")
                return results
            
            data = response.json()
            all_object_ids = data.get('objectIDs', [])

            if not all_object_ids:
                print(f"  ⚠️  No results found")
                return results

            # Randomize for diversity
            random.shuffle(all_object_ids)
            object_ids = all_object_ids[:limit]

            print(f"  📊 Found {len(object_ids)} potential paintings")
            
            # Get details for each object
            for idx, obj_id in enumerate(object_ids, 1):
                print(f"  🔍 Checking painting {idx}/{len(object_ids)}...", end='\r')
                
                detail_url = f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{obj_id}"
                detail_response = requests.get(detail_url, timeout=10)
                
                if detail_response.status_code != 200:
                    continue
                
                obj_data = detail_response.json()
                
                # Check if it has a primary image
                if obj_data.get('primaryImage'):
                    title = obj_data.get('title', 'Untitled')
                    artist = obj_data.get('artistDisplayName', 'Unknown')
                    date = obj_data.get('objectDate', 'Unknown')
                    
                    # Met provides high-res images
                    image_url = obj_data['primaryImage']
                    
                    # Try to get additional images if available
                    additional_images = obj_data.get('additionalImages', [])
                    
                    result = {
                        'title': title,
                        'artist': artist,
                        'date': date,
                        'source': 'Metropolitan Museum',
                        'image_url': image_url,
                        'museum_url': f"https://www.metmuseum.org/art/collection/search/{obj_id}",
                        'resolution_note': 'High-resolution available (typically 3000+ px)',
                        'aspect_ratio_verified': False,  # Mark as unverified
                        'additional_images': additional_images[:2] if additional_images else []
                    }

                    results.append(result)
                
                time.sleep(0.2)  # Rate limiting
            
            print(f"\n  ✅ Found {len(results)} high-resolution paintings from Met Museum")
            
        except Exception as e:
            print(f"  ❌ Error searching Met Museum: {e}")
        
        return results
    
    def search_art_institute_chicago(self, query: str = "portrait", limit: int = 20) -> List[Dict]:
        """
        Search Art Institute of Chicago API
        API: https://api.artic.edu/docs/
        Note: Art Institute API doesn't provide dimensions, so aspect ratio cannot be pre-filtered
        """
        results = []
        print(f"\n🎨 Searching Art Institute of Chicago...")
        print(f"  ⚠️  Note: Art Institute results cannot be pre-filtered by aspect ratio")
        
        try:
            api_url = "https://api.artic.edu/api/v1/artworks/search"
            params = {
                'q': query,
                'query': {
                    'term': {
                        'classification_titles': 'painting'
                    }
                },
                'fields': 'id,title,artist_display,date_display,image_id,dimensions',
                'limit': limit
            }
            
            response = requests.get(api_url, params={'q': query, 'limit': limit, 
                                                    'fields': 'id,title,artist_display,date_display,image_id,dimensions'},
                                   timeout=10)
            
            if response.status_code != 200:
                print(f"  ❌ Failed to search Art Institute")
                return results
            
            data = response.json()
            artworks = data.get('data', [])

            if not artworks:
                print(f"  ⚠️  No results found")
                return results

            print(f"  📊 Found {len(artworks)} potential paintings")

            # Randomize for diversity
            random.shuffle(artworks)

            for artwork in artworks:
                if artwork.get('image_id'):
                    # IIIF image URL with size parameters
                    image_id = artwork['image_id']
                    # Request high resolution
                    image_url = f"https://www.artic.edu/iiif/2/{image_id}/full/1400,/0/default.jpg"
                    high_res_url = f"https://www.artic.edu/iiif/2/{image_id}/full/full/0/default.jpg"
                    
                    result = {
                        'title': artwork.get('title', 'Untitled'),
                        'artist': artwork.get('artist_display', 'Unknown'),
                        'date': artwork.get('date_display', 'Unknown'),
                        'source': 'Art Institute of Chicago',
                        'image_url': image_url,
                        'high_res_url': high_res_url,
                        'museum_url': f"https://www.artic.edu/artworks/{artwork['id']}",
                        'dimensions': artwork.get('dimensions', 'Unknown'),
                        'resolution_note': 'IIIF compliant - scalable to full resolution',
                        'aspect_ratio_verified': False  # Mark as unverified
                    }

                    results.append(result)
            
            print(f"  ✅ Found {len(results)} high-resolution paintings from Art Institute")
            
        except Exception as e:
            print(f"  ❌ Error searching Art Institute: {e}")
        
        return results
    
    def search_rijksmuseum(self, query: str = "portrait", limit: int = 20) -> List[Dict]:
        """
        Search Rijksmuseum API
        Note: Requires free API key from https://data.rijksmuseum.nl/object-metadata/api/
        """
        results = []
        print(f"\n🎨 Searching Rijksmuseum...")

        # Get API key from configuration
        API_KEY = self.get_api_key('rijksmuseum_key')
        if not API_KEY:
            print(f"  ⚠️  No Rijksmuseum API key found - skipping")
            print(f"  ℹ️  Get a free key at: https://data.rijksmuseum.nl/object-metadata/api/")
            return results
        
        try:
            api_url = "https://www.rijksmuseum.nl/api/en/collection"
            params = {
                'key': API_KEY,
                'q': query,
                'type': 'painting',
                'imgonly': 'true',
                'ps': limit,
                'p': 0
            }
            
            response = requests.get(api_url, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"  ❌ Failed to search Rijksmuseum (status: {response.status_code})")
                print(f"  ℹ️  Get your free API key at: https://data.rijksmuseum.nl/object-metadata/api/")
                return results
            
            data = response.json()
            artworks = data.get('artObjects', [])

            if not artworks:
                print(f"  ⚠️  No results found")
                return results

            print(f"  📊 Found {len(artworks)} paintings")

            # Randomize for diversity
            random.shuffle(artworks)

            for artwork in artworks:
                if artwork.get('webImage'):
                    web_image = artwork['webImage']
                    
                    # Check resolution
                    width = web_image.get('width', 0)
                    height = web_image.get('height', 0)

                    # Check both resolution and aspect ratio
                    if self.check_resolution(width, height) and self.is_acceptable_aspect_ratio(width, height):
                        aspect_ratio, match_score = self.get_aspect_ratio_match(width, height)

                        result = {
                            'title': artwork.get('title', 'Untitled'),
                            'artist': artwork.get('principalOrFirstMaker', 'Unknown'),
                            'date': artwork.get('longTitle', 'Unknown'),
                            'source': 'Rijksmuseum',
                            'image_url': web_image['url'],
                            'museum_url': artwork.get('links', {}).get('web', ''),
                            'resolution': f"{width}x{height}",
                            'is_portrait': self.is_portrait_orientation(width, height),
                            'aspect_ratio': round(aspect_ratio, 3),
                            'aspect_ratio_match': round(match_score, 1),
                            'aspect_ratio_verified': True  # Verified and filtered
                        }

                        results.append(result)
            
            print(f"  ✅ Found {len(results)} high-resolution paintings from Rijksmuseum")
            
        except Exception as e:
            print(f"  ❌ Error searching Rijksmuseum: {e}")
        
        return results
    
    def search_wikimedia_commons(self, query: str = "portrait painting", limit: int = 20) -> List[Dict]:
        """
        Search Wikimedia Commons for high-resolution paintings
        """
        results = []
        print(f"\n🎨 Searching Wikimedia Commons...")
        
        try:
            api_url = "https://commons.wikimedia.org/w/api.php"
            
            # Search for files
            search_params = {
                'action': 'query',
                'format': 'json',
                'list': 'search',
                'srsearch': f'{query} filetype:bitmap filemime:image/jpeg|image/png',
                'srnamespace': '6',  # File namespace
                'srlimit': limit * 2,  # Get more to filter
                'srprop': 'size|wordcount|timestamp|snippet'
            }
            
            response = requests.get(api_url, params=search_params, timeout=10)
            
            if response.status_code != 200:
                print(f"  ❌ Failed to search Wikimedia Commons")
                return results
            
            data = response.json()
            search_results = data.get('query', {}).get('search', [])

            if not search_results:
                print(f"  ⚠️  No results found")
                return results

            print(f"  📊 Found {len(search_results)} potential files")

            # Randomize for diversity
            random.shuffle(search_results)

            # Get image info for each result
            for item in search_results[:limit]:
                title = item['title']
                
                # Get file info
                info_params = {
                    'action': 'query',
                    'format': 'json',
                    'titles': title,
                    'prop': 'imageinfo',
                    'iiprop': 'url|size|mime|extmetadata',
                    'iiurlwidth': 1400  # Request thumbnail of specific width
                }
                
                info_response = requests.get(api_url, params=info_params, timeout=10)
                
                if info_response.status_code == 200:
                    info_data = info_response.json()
                    pages = info_data.get('query', {}).get('pages', {})
                    
                    for page_id, page_data in pages.items():
                        if 'imageinfo' in page_data:
                            image_info = page_data['imageinfo'][0]
                            width = image_info.get('width', 0)
                            height = image_info.get('height', 0)
                            
                            # Check both resolution and aspect ratio
                            if self.check_resolution(width, height) and self.is_acceptable_aspect_ratio(width, height):
                                metadata = image_info.get('extmetadata', {})
                                artist = metadata.get('Artist', {}).get('value', 'Unknown')
                                # Clean HTML from artist field
                                artist = re.sub('<[^<]+?>', '', artist)

                                aspect_ratio, match_score = self.get_aspect_ratio_match(width, height)

                                result = {
                                    'title': title.replace('File:', '').replace('.jpg', '').replace('.png', ''),
                                    'artist': artist[:100] if len(artist) > 100 else artist,
                                    'date': metadata.get('DateTimeOriginal', {}).get('value', 'Unknown'),
                                    'source': 'Wikimedia Commons',
                                    'image_url': image_info['url'],
                                    'thumbnail_url': image_info.get('thumburl', ''),
                                    'commons_url': f"https://commons.wikimedia.org/wiki/{title.replace(' ', '_')}",
                                    'resolution': f"{width}x{height}",
                                    'is_portrait': self.is_portrait_orientation(width, height),
                                    'aspect_ratio': round(aspect_ratio, 3),
                                    'aspect_ratio_match': round(match_score, 1),
                                    'aspect_ratio_verified': True,  # Verified and filtered
                                    'license': metadata.get('License', {}).get('value', 'See Commons page')
                                }

                                results.append(result)
                
                time.sleep(0.1)  # Rate limiting
            
            print(f"  ✅ Found {len(results)} high-resolution paintings from Wikimedia Commons")
            
        except Exception as e:
            print(f"  ❌ Error searching Wikimedia Commons: {e}")
        
        return results

    def search_cleveland_museum(self, query: str = "portrait", limit: int = 20) -> List[Dict]:
        """
        Search Cleveland Museum of Art Open Access API
        API: https://openaccess-api.clevelandart.org/
        """
        results = []
        print(f"\n🎨 Searching Cleveland Museum of Art...")

        try:
            # Cleveland API provides direct search with filters
            api_url = "https://openaccess-api.clevelandart.org/api/artworks/"
            params = {
                'q': query,
                'has_image': '1',
                'type': 'Painting',
                'limit': limit * 2,  # Get more to account for filtering
                'skip': 0
            }

            response = requests.get(api_url, params=params, timeout=10)

            if response.status_code != 200:
                print(f"  ❌ Failed to search Cleveland Museum (status: {response.status_code})")
                return results

            data = response.json()
            artworks = data.get('data', [])

            if not artworks:
                print(f"  ⚠️  No results found")
                return results

            print(f"  📊 Found {len(artworks)} potential paintings")

            # Randomize for diversity
            random.shuffle(artworks)

            for artwork in artworks:
                # Check if artwork has images
                images = artwork.get('images', {})
                if not images or not images.get('web'):
                    continue

                web_image = images['web']

                # Get dimensions from the web image
                width = web_image.get('width', 0)
                height = web_image.get('height', 0)

                # Convert to int if they're strings
                try:
                    width = int(width) if width else 0
                    height = int(height) if height else 0
                except (ValueError, TypeError):
                    continue

                # Check both resolution and aspect ratio
                if width and height and self.check_resolution(width, height) and self.is_acceptable_aspect_ratio(width, height):
                    aspect_ratio, match_score = self.get_aspect_ratio_match(width, height)

                    # Get print/full resolution URLs if available
                    print_url = images.get('print', {}).get('url', '')
                    full_url = images.get('full', {}).get('url', '')

                    result = {
                        'title': artwork.get('title', 'Untitled'),
                        'artist': artwork.get('creators', [{}])[0].get('description', 'Unknown') if artwork.get('creators') else 'Unknown',
                        'date': artwork.get('creation_date', 'Unknown'),
                        'source': 'Cleveland Museum of Art',
                        'image_url': web_image.get('url', ''),
                        'print_url': print_url,
                        'full_url': full_url,
                        'museum_url': artwork.get('url', ''),
                        'resolution': f"{width}x{height}",
                        'is_portrait': self.is_portrait_orientation(width, height),
                        'aspect_ratio': round(aspect_ratio, 3),
                        'aspect_ratio_match': round(match_score, 1),
                        'aspect_ratio_verified': True
                    }

                    results.append(result)

                    if len(results) >= limit:
                        break

            print(f"  ✅ Found {len(results)} high-resolution paintings from Cleveland Museum")

        except Exception as e:
            print(f"  ❌ Error searching Cleveland Museum: {e}")

        return results

    def search_europeana(self, query: str = "portrait", limit: int = 20) -> List[Dict]:
        """
        Search Europeana API
        API: https://api.europeana.eu/
        Note: Requires free API key from https://pro.europeana.eu/page/get-api
        """
        results = []
        print(f"\n🎨 Searching Europeana...")

        # Get API key from configuration
        API_KEY = self.get_api_key('europeana_key')
        if not API_KEY:
            print(f"  ⚠️  No Europeana API key found - skipping")
            print(f"  ℹ️  Get a free key at: https://pro.europeana.eu/page/get-api")
            return results

        try:
            # Search for paintings/portraits
            search_url = "https://api.europeana.eu/record/v2/search.json"
            params = {
                'wskey': API_KEY,
                'query': query,  # Removed restrictive 'what:painting' filter
                'media': 'true',
                'qf': 'TYPE:IMAGE',  # Only require it to be an image
                # Removed IMAGE_SIZE filters - we filter by actual dimensions anyway
                # Removed reusability filter - too restrictive
                'rows': limit * 10,  # Get many more since URLs are often broken
                'profile': 'rich'
            }

            response = requests.get(search_url, params=params, timeout=15)

            if response.status_code != 200:
                print(f"  ❌ Failed to search Europeana (status: {response.status_code})")
                return results

            data = response.json()
            items = data.get('items', [])

            if not items:
                print(f"  ⚠️  No results found")
                return results

            print(f"  📊 Found {len(items)} potential images, checking dimensions...")

            # Randomize for diversity
            random.shuffle(items)

            # For each item, we need to get detailed record to extract dimensions
            # Check ALL items to maximize valid results (many URLs will be broken)
            for item in items:
                try:
                    # Get the record ID
                    record_id = item.get('id')
                    if not record_id:
                        continue

                    # Fetch detailed record with technical metadata
                    record_url = f"https://api.europeana.eu/record/v2{record_id}.json"
                    record_params = {'wskey': API_KEY, 'profile': 'rich'}

                    record_response = requests.get(record_url, params=record_params, timeout=10)

                    if record_response.status_code != 200:
                        continue

                    record_data = record_response.json()
                    obj = record_data.get('object', {})

                    # Look for aggregations (contains both image URLs and webResources with dimensions)
                    aggregations = obj.get('aggregations', [])
                    if not aggregations:
                        continue

                    # Get the first aggregation (main resource)
                    main_agg = aggregations[0]

                    # Find the main image URL
                    edm_is_shown_by = main_agg.get('edmIsShownBy')

                    if not edm_is_shown_by:
                        continue

                    # Skip relative paths or invalid URLs
                    if not edm_is_shown_by.startswith(('http://', 'https://')):
                        continue

                    # Validate that the image URL is actually accessible
                    try:
                        url_check = requests.head(edm_is_shown_by, timeout=3, allow_redirects=True)
                        if url_check.status_code != 200:
                            # URL is broken, skip this item
                            continue
                    except Exception:
                        # URL is inaccessible, skip this item
                        continue

                    # Look for dimensions in webResources
                    width = None
                    height = None

                    for aggregation in aggregations:
                        web_resources = aggregation.get('webResources', [])
                        for resource in web_resources:
                            # First try to match the resource URL with edmIsShownBy
                            if resource.get('about') == edm_is_shown_by:
                                width = resource.get('ebucoreWidth')
                                height = resource.get('ebucoreHeight')
                                if width and height:
                                    break

                        # If exact match didn't work, try to find any resource with dimensions
                        if not (width and height):
                            for resource in web_resources:
                                w = resource.get('ebucoreWidth')
                                h = resource.get('ebucoreHeight')
                                if w and h:
                                    # Prefer larger dimensions
                                    try:
                                        if not width or (int(w) > int(width)):
                                            width = w
                                            height = h
                                    except (ValueError, TypeError):
                                        pass

                        if width and height:
                            break

                    # Check if we have valid dimensions
                    if not width or not height:
                        continue

                    # Convert to int if they're strings
                    try:
                        width = int(width)
                        height = int(height)
                    except (ValueError, TypeError):
                        continue

                    # Check both resolution and aspect ratio
                    if not self.check_resolution(width, height):
                        continue

                    if not self.is_acceptable_aspect_ratio(width, height):
                        continue

                    # Item passed all checks - extract and save
                    aspect_ratio, match_score = self.get_aspect_ratio_match(width, height)

                    # Extract metadata
                    title_list = obj.get('title', ['Untitled'])
                    title = title_list[0] if isinstance(title_list, list) else title_list

                    creator_list = obj.get('dcCreator', ['Unknown'])
                    creator = creator_list[0] if isinstance(creator_list, list) else creator_list

                    year_list = obj.get('year', ['Unknown'])
                    year = year_list[0] if isinstance(year_list, list) else year_list

                    result = {
                        'title': title[:100] if len(title) > 100 else title,
                        'artist': creator[:100] if len(creator) > 100 else creator,
                        'date': str(year),
                        'source': 'Europeana',
                        'image_url': edm_is_shown_by,
                        'museum_url': obj.get('guid', ''),
                        'resolution': f"{width}x{height}",
                        'is_portrait': self.is_portrait_orientation(width, height),
                        'aspect_ratio': round(aspect_ratio, 3),
                        'aspect_ratio_match': round(match_score, 1),
                        'aspect_ratio_verified': True
                    }

                    results.append(result)

                    if len(results) >= limit:
                        break

                    time.sleep(0.15)  # Rate limiting between record fetches

                except Exception as e:
                    # Skip individual items that fail
                    continue

            print(f"  ✅ Found {len(results)} high-resolution paintings from Europeana")

        except Exception as e:
            print(f"  ❌ Error searching Europeana: {e}")

        return results

    def search_harvard(self, query: str = "portrait", limit: int = 10) -> List[Dict]:
        """
        Search Harvard Art Museums API
        API: https://api.harvardartmuseums.org/
        """
        results = []
        print(f"\n🎨 Searching Harvard Art Museums...")

        # Get API key from configuration
        API_KEY = self.get_api_key('harvard_key')
        if not API_KEY:
            print(f"  ⚠️  No Harvard API key found - skipping")
            print(f"  ℹ️  Get a free key at: https://harvardartmuseums.org/collections/api")
            return results

        try:
            # Search for paintings with images
            search_url = "https://api.harvardartmuseums.org/object"
            params = {
                'apikey': API_KEY,
                'q': query,
                'classification': 'Paintings',
                'hasimage': 1,
                'size': limit * 3,  # Get more to filter
            }

            response = requests.get(search_url, params=params, timeout=15)

            if response.status_code != 200:
                print(f"  ❌ Failed to search Harvard (status: {response.status_code})")
                return results

            data = response.json()
            records = data.get('records', [])

            if not records:
                print(f"  ⚠️  No results found")
                return results

            print(f"  📊 Found {len(records)} potential paintings")

            # Randomize for diversity
            random.shuffle(records)

            for record in records:
                try:
                    # Get images array
                    images = record.get('images', [])
                    if not images:
                        continue

                    # Get dimensions from first image
                    img = images[0]
                    width = img.get('width')
                    height = img.get('height')

                    if not width or not height:
                        continue

                    # Convert to int
                    try:
                        width = int(width)
                        height = int(height)
                    except (ValueError, TypeError):
                        continue

                    # Check both resolution and aspect ratio
                    if not self.check_resolution(width, height):
                        continue

                    if not self.is_acceptable_aspect_ratio(width, height):
                        continue

                    # Item passed all checks - extract and save
                    aspect_ratio, match_score = self.get_aspect_ratio_match(width, height)

                    # Extract metadata
                    title = record.get('title', 'Untitled')

                    # Get artist from people array
                    artist = 'Unknown'
                    people = record.get('people', [])
                    if people and len(people) > 0:
                        artist = people[0].get('name', 'Unknown')

                    # Get date
                    date = record.get('dated', 'Unknown')

                    # Get image URL
                    image_url = record.get('primaryimageurl', '')

                    # Get museum URL
                    museum_url = record.get('url', '')

                    result = {
                        'title': title[:100] if len(title) > 100 else title,
                        'artist': artist[:100] if len(artist) > 100 else artist,
                        'date': str(date),
                        'source': 'Harvard Art Museums',
                        'image_url': image_url,
                        'museum_url': museum_url,
                        'resolution': f"{width}x{height}",
                        'is_portrait': self.is_portrait_orientation(width, height),
                        'aspect_ratio': round(aspect_ratio, 3),
                        'aspect_ratio_match': round(match_score, 1),
                        'aspect_ratio_verified': True
                    }

                    results.append(result)

                    if len(results) >= limit:
                        break

                except Exception as e:
                    # Skip individual items that fail
                    continue

            print(f"  ✅ Found {len(results)} high-resolution paintings from Harvard")

        except Exception as e:
            print(f"  ❌ Error searching Harvard: {e}")

        return results

    def search_google_images(self, query: str = "portrait painting", limit: int = 10) -> List[Dict]:
        """
        Search Google Images using Custom Search API
        API: https://developers.google.com/custom-search/v1/introduction
        Note: Free tier limited to 100 queries/day
        """
        results = []
        print(f"\n🎨 Searching Google Images...")

        # Get API credentials from configuration
        API_KEY = self.get_api_key('google_api_key')
        SEARCH_ENGINE_ID = self.get_api_key('google_search_engine_id')

        if not API_KEY or not SEARCH_ENGINE_ID:
            print(f"  ⚠️  No Google API credentials found - skipping")
            print(f"  ℹ️  Get API key at: https://console.cloud.google.com/apis/credentials")
            print(f"  ℹ️  Create search engine at: https://programmablesearchengine.google.com/")
            return results

        try:
            # Google Custom Search API only returns 10 results per query max
            # We'll need to make multiple requests with different start indices
            search_url = "https://www.googleapis.com/customsearch/v1"

            all_items = []

            # Make 20 queries (200 results) - this is Google's API hard limit
            # Google Custom Search API only allows start index up to 191 (last page starts at 191)
            # We filter by dimensions ourselves rather than using API filters
            for i in range(20):  # 20 queries = 200 results max (API limit)
                params = {
                    'key': API_KEY,
                    'cx': SEARCH_ENGINE_ID,
                    'q': query,
                    'searchType': 'image',
                    # No imgSize filter - we check dimensions ourselves
                    # No imgType filter - allow all types (photos, artwork, etc.)
                    'num': 10,              # Max per query
                    'start': i * 10 + 1,    # Start index (1-based)
                }

                response = requests.get(search_url, params=params, timeout=15)

                if response.status_code != 200:
                    print(f"  ❌ Failed to search Google Images (status: {response.status_code})")
                    if response.status_code == 429:
                        print(f"  ⚠️  API quota exceeded (100 queries/day limit)")
                    break

                data = response.json()
                items = data.get('items', [])

                if not items:
                    break

                all_items.extend(items)

                # Small delay between queries to avoid rate limiting
                if i < 19:  # Sleep between queries, but not after the last one
                    time.sleep(0.3)

            if not all_items:
                print(f"  ⚠️  No results found")
                return results

            print(f"  📊 Found {len(all_items)} potential images, filtering by dimensions...")

            # Randomly shuffle to get variety
            random.shuffle(all_items)

            for item in all_items:
                try:
                    # Get image metadata
                    image_meta = item.get('image', {})
                    width = image_meta.get('width')
                    height = image_meta.get('height')

                    if not width or not height:
                        continue

                    # Convert to int
                    try:
                        width = int(width)
                        height = int(height)
                    except (ValueError, TypeError):
                        continue

                    # Check both resolution and aspect ratio
                    if not self.check_resolution(width, height):
                        continue

                    if not self.is_acceptable_aspect_ratio(width, height):
                        continue

                    # Item passed all checks - extract and save
                    aspect_ratio, match_score = self.get_aspect_ratio_match(width, height)

                    # Extract metadata
                    title = item.get('title', 'Untitled')

                    # Get source page
                    page_url = item.get('image', {}).get('contextLink', '')

                    # Extract domain as "artist/source"
                    artist = 'Google Images'
                    if page_url:
                        from urllib.parse import urlparse
                        domain = urlparse(page_url).netloc
                        artist = domain.replace('www.', '')

                    # Get image URL
                    image_url = item.get('link', '')

                    result = {
                        'title': title[:100] if len(title) > 100 else title,
                        'artist': artist[:100] if len(artist) > 100 else artist,
                        'date': 'Unknown',
                        'source': 'Google Images',
                        'image_url': image_url,
                        'museum_url': page_url,
                        'resolution': f"{width}x{height}",
                        'is_portrait': self.is_portrait_orientation(width, height),
                        'aspect_ratio': round(aspect_ratio, 3),
                        'aspect_ratio_match': round(match_score, 1),
                        'aspect_ratio_verified': True
                    }

                    results.append(result)

                    if len(results) >= limit:
                        break

                except Exception as e:
                    # Skip individual items that fail
                    continue

            print(f"  ✅ Found {len(results)} high-resolution images from Google")

        except Exception as e:
            print(f"  ❌ Error searching Google Images: {e}")

        return results

    def save_results(self, results: List[Dict], filename: str = "painting_results.json"):
        """Save search results to JSON file"""
        output = {
            'search_date': datetime.now().isoformat(),
            'min_resolution': f"{self.min_width}x{self.min_height}",
            'total_results': len(results),
            'paintings': results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to {filename}")
    
    def generate_html_gallery(self, results: List[Dict], filename: str = "painting_gallery.html"):
        """Generate an HTML gallery of the found paintings"""
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>High-Resolution Portrait Paintings Gallery</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(to bottom, #f0f0f0, #e0e0e0);
            margin: 0;
            padding: 20px;
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 10px;
        }
        .stats {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
        }
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 30px;
            max-width: 1400px;
            margin: 0 auto;
        }
        .painting {
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow: hidden;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .painting:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 15px rgba(0,0,0,0.2);
        }
        .painting img {
            width: 100%;
            height: 400px;
            object-fit: cover;
            cursor: pointer;
        }
        .painting-info {
            padding: 15px;
        }
        .painting-title {
            font-weight: bold;
            color: #333;
            margin-bottom: 8px;
            font-size: 1.1em;
        }
        .painting-artist {
            color: #666;
            margin-bottom: 5px;
        }
        .painting-meta {
            font-size: 0.9em;
            color: #999;
            margin-bottom: 10px;
        }
        .painting-links {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .painting-links a {
            text-decoration: none;
            color: white;
            background: #4CAF50;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 0.9em;
            transition: background 0.3s;
        }
        .painting-links a:hover {
            background: #45a049;
        }
        .download-btn {
            color: white;
            background: #FF9800;
            border: none;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 0.9em;
            cursor: pointer;
            transition: background 0.3s;
        }
        .download-btn:hover {
            background: #F57C00;
        }
        .source-badge {
            display: inline-block;
            background: #2196F3;
            color: white;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 0.8em;
            margin-top: 5px;
        }
        .resolution-badge {
            display: inline-block;
            background: #9C27B0;
            color: white;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 0.8em;
            margin-left: 5px;
        }
        .aspect-ratio-badge {
            display: inline-block;
            color: white;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 0.8em;
            margin-left: 5px;
        }
        .aspect-ratio-excellent {
            background: #4CAF50;
        }
        .aspect-ratio-good {
            background: #FF9800;
        }
        .aspect-ratio-fair {
            background: #F44336;
        }
        .unverified-badge {
            display: inline-block;
            background: #FF9800;
            color: white;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 0.8em;
            margin-left: 5px;
        }
        .unverified-note {
            background: #fff3cd;
            border-left: 4px solid #ff9800;
            padding: 10px;
            margin-top: 10px;
            font-size: 0.85em;
            color: #856404;
        }
        .filter-container {
            text-align: center;
            margin-bottom: 20px;
        }
        .filter-button {
            background: #555;
            color: white;
            border: none;
            padding: 10px 20px;
            margin: 5px;
            border-radius: 5px;
            cursor: pointer;
            transition: background 0.3s;
        }
        .filter-button:hover {
            background: #333;
        }
        .filter-button.active {
            background: #4CAF50;
        }
    </style>
</head>
<body>
    <h1>🎨 High-Resolution Portrait Paintings Gallery</h1>
    <div class="stats">
        <p>Found """ + str(len(results)) + """ paintings for 2560x2880 display (minimum """ + str(self.min_width) + """x""" + str(self.min_height) + """ pixels)</p>
        <p>Search Date: """ + datetime.now().strftime("%Y-%m-%d %H:%M") + """</p>
    </div>
    
    <div class="filter-container">
        <button class="filter-button active" onclick="filterBySource('all')">All Sources</button>
        <button class="filter-button" onclick="filterBySource('Cleveland Museum of Art')">Cleveland</button>
        <button class="filter-button" onclick="filterBySource('Rijksmuseum')">Rijksmuseum</button>
        <button class="filter-button" onclick="filterBySource('Wikimedia Commons')">Wikimedia</button>
        <button class="filter-button" onclick="filterBySource('Europeana')">Europeana</button>
        <button class="filter-button" onclick="filterBySource('Harvard Art Museums')">Harvard</button>
        <button class="filter-button" onclick="filterBySource('Google Images')">Google</button>
    </div>
    
    <div class="gallery">
"""
        
        for painting in results:
            # Use thumbnail if available, otherwise use main image
            img_url = painting.get('thumbnail_url') or painting.get('image_url', '')
            
            html += f"""
        <div class="painting" data-source="{painting['source']}">
            <img src="{img_url}" alt="{painting['title']}" onclick="window.open('{painting.get('image_url', '')}', '_blank')">
            <div class="painting-info">
                <div class="painting-title">{painting['title'][:80]}...</div>
                <div class="painting-artist">by {painting['artist']}</div>
                <div class="painting-meta">{painting.get('date', 'Date unknown')}</div>
                <span class="source-badge">{painting['source']}</span>
"""
            
            if 'resolution' in painting:
                html += f"""                <span class="resolution-badge">{painting['resolution']}</span>
"""

            # All results are verified (only searching Rijksmuseum/Wikimedia)
            if 'aspect_ratio_match' in painting:
                match_score = painting.get('aspect_ratio_match', 0)
                if match_score >= 95:
                    badge_class = 'aspect-ratio-excellent'
                    label = f'✓ {match_score}% Perfect'
                elif match_score >= 90:
                    badge_class = 'aspect-ratio-excellent'
                    label = f'✓ {match_score}% Excellent'
                elif match_score >= 85:
                    badge_class = 'aspect-ratio-good'
                    label = f'✓ {match_score}% Good'
                else:
                    badge_class = 'aspect-ratio-fair'
                    label = f'✓ {match_score}% Match'

                html += f"""                <span class="aspect-ratio-badge {badge_class}">{label}</span>
"""
            
            html += """                <div class="painting-links" style="margin-top: 10px;">
"""

            if painting.get('image_url'):
                # Create a safe filename from title and artist
                safe_title = "".join(c for c in painting['title'][:50] if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_artist = "".join(c for c in painting['artist'][:30] if c.isalnum() or c in (' ', '-', '_')).strip()
                download_filename = f"IMAGES/{safe_artist} - {safe_title}.jpg"

                html += f"""                    <a href="{painting['image_url']}" target="_blank">Full Image</a>
                    <button class="download-btn" onclick="downloadImage('{painting['image_url']}', '{download_filename}')">Download</button>
"""

            if painting.get('high_res_url'):
                html += f"""                    <a href="{painting['high_res_url']}" target="_blank">Max Resolution</a>
"""

            if painting.get('museum_url'):
                html += f"""                    <a href="{painting['museum_url']}" target="_blank">Museum Page</a>
"""
            elif painting.get('commons_url'):
                html += f"""                    <a href="{painting['commons_url']}" target="_blank">Commons Page</a>
"""

            html += """                </div>
            </div>
        </div>
"""
        
        html += """
    </div>
    
    <script>
        function filterBySource(source) {
            const paintings = document.querySelectorAll('.painting');
            const buttons = document.querySelectorAll('.filter-button');

            // Update button states
            buttons.forEach(btn => {
                btn.classList.remove('active');
                if (btn.textContent.includes(source) || (source === 'all' && btn.textContent === 'All Sources')) {
                    btn.classList.add('active');
                }
            });

            // Filter paintings
            paintings.forEach(painting => {
                const paintingSource = painting.dataset.source;
                let matches = false;

                if (source === 'all') {
                    matches = true;
                } else {
                    matches = paintingSource === source;
                }

                painting.style.display = matches ? 'block' : 'none';
            });
        }

        async function downloadImage(imageUrl, filename) {
            try {
                // Fetch the image
                const response = await fetch(imageUrl, {
                    mode: 'cors',
                    credentials: 'omit'
                });

                if (!response.ok) {
                    throw new Error('Failed to fetch image');
                }

                // Get the blob
                const blob = await response.blob();

                // Create a download link
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = filename;

                // Trigger download
                document.body.appendChild(a);
                a.click();

                // Cleanup
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            } catch (error) {
                console.error('Download failed:', error);
                // Fallback: open in new tab if CORS fails
                window.open(imageUrl, '_blank');
                alert('Direct download blocked by CORS. Opening image in new tab - please right-click and save.');
            }
        }
    </script>
</body>
</html>
"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"🌐 HTML gallery saved to {filename}")
    
    def search_all(self, query: str = "portrait", limit_per_source: int = 10):
        """Search all available sources"""
        print(f"\n{'='*60}")
        print(f"🔍 SEARCHING FOR HIGH-RESOLUTION PORTRAIT PAINTINGS")
        print(f"{'='*60}")
        print(f"Query: '{query}'")
        print(f"Target Display: 2560x2880 pixels (portrait mode)")
        print(f"Minimum Resolution: {self.min_width}x{self.min_height} pixels")
        print(f"Aspect Ratio Filter: ≥{self.min_aspect_ratio_match}% match to 0.889 ratio (STRICT)")
        print(f"Orientation: Portrait ONLY (landscape rejected)")

        # Get sources from configuration
        sources = self.sources_config.get('sources', {})

        # List enabled sources
        enabled_sources = []
        for source_id, config in sources.items():
            if config.get('enabled', False):
                enabled_sources.append(config.get('name', source_id))

        sources_display = ', '.join(enabled_sources) if enabled_sources else 'None'
        print(f"Sources: VERIFIED ONLY ({sources_display})")
        print(f"{'='*60}")

        verified_results = []

        # Search built-in sources if enabled in config
        if sources.get('cleveland', {}).get('enabled', True):
            verified_results.extend(self.search_cleveland_museum(query, limit_per_source))

        if sources.get('rijksmuseum', {}).get('enabled', True):
            verified_results.extend(self.search_rijksmuseum(query, limit_per_source))

        if sources.get('wikimedia', {}).get('enabled', True):
            verified_results.extend(self.search_wikimedia_commons(query, limit_per_source))

        if sources.get('europeana', {}).get('enabled', True):
            verified_results.extend(self.search_europeana(query, limit_per_source))

        if sources.get('harvard', {}).get('enabled', False):
            verified_results.extend(self.search_harvard(query, limit_per_source))

        if sources.get('google_images', {}).get('enabled', False):
            verified_results.extend(self.search_google_images(query, limit_per_source))

        # Randomize results for diversity
        random.shuffle(verified_results)

        print(f"\n{'='*60}")
        print(f"📊 SEARCH COMPLETE")
        print(f"{'='*60}")
        print(f"✅ Verified paintings found: {len(verified_results)}")
        if verified_results:
            print(f"Best aspect ratio match: {verified_results[0].get('aspect_ratio_match', 0):.1f}%")
            print(f"Average aspect ratio match: {sum(r.get('aspect_ratio_match', 0) for r in verified_results) / len(verified_results):.1f}%")
        print(f"\n💡 All results are verified portrait mode with ≥85% aspect ratio match")

        return verified_results


def main():
    """Main function"""
    import argparse

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Search for high-resolution portrait paintings suitable for a 2560x2880 display'
    )
    parser.add_argument('--query', '-q', type=str, help='Search query (default: portrait)')
    parser.add_argument('--limit', '-l', type=int, help='Results per source (default: 10)')
    parser.add_argument('--min-width', type=int, help='Minimum image width in pixels (default: 1280)')
    parser.add_argument('--min-height', type=int, help='Minimum image height in pixels (default: 1440)')
    parser.add_argument('--min-aspect-match', type=float, help='Minimum aspect ratio match percentage (default: 85.0)')

    args = parser.parse_args()

    print("""
╔══════════════════════════════════════════════════════════════╗
║     High-Resolution Portrait Painting Image Searcher        ║
║                                                              ║
║  This tool searches multiple free museum APIs and archives  ║
║  for high-quality portrait paintings (≥1280x1440 pixels)    ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # Get search parameters from user or command line
    print("\n📝 SEARCH CONFIGURATION")
    print("-" * 30)

    # Query
    if args.query:
        query = args.query
        print(f"Search query: {query}")
    else:
        query = input("Enter search query (default: 'portrait'): ").strip()
        if not query:
            query = "portrait"

    # Results limit
    if args.limit:
        limit = args.limit
        print(f"Results per source: {limit}")
    else:
        try:
            limit = int(input("Results per source (default: 10): ").strip() or "10")
        except ValueError:
            limit = 10

    # Resolution settings
    if args.min_width:
        min_width = args.min_width
        print(f"Minimum width: {min_width}px")
    else:
        try:
            min_width_input = input("Minimum width in pixels (default: 1280): ").strip()
            min_width = int(min_width_input) if min_width_input else 1280
        except ValueError:
            min_width = 1280

    if args.min_height:
        min_height = args.min_height
        print(f"Minimum height: {min_height}px")
    else:
        try:
            min_height_input = input("Minimum height in pixels (default: 1440): ").strip()
            min_height = int(min_height_input) if min_height_input else 1440
        except ValueError:
            min_height = 1440

    # Aspect ratio match
    if args.min_aspect_match:
        min_aspect_match = args.min_aspect_match
        print(f"Minimum aspect ratio match: {min_aspect_match}%")
    else:
        try:
            aspect_input = input("Minimum aspect ratio match % (default: 85.0): ").strip()
            min_aspect_match = float(aspect_input) if aspect_input else 85.0
        except ValueError:
            min_aspect_match = 85.0

    # Create searcher instance with configured parameters
    searcher = PaintingSearcher(
        min_width=min_width,
        min_height=min_height,
        min_aspect_ratio_match=min_aspect_match
    )
    
    # Perform search
    results = searcher.search_all(query, limit)
    
    if results:
        # Save results
        print(f"\n💾 SAVING RESULTS")
        print("-" * 30)
        
        # JSON file
        json_file = f"paintings_{query.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        searcher.save_results(results, json_file)
        
        # HTML gallery
        html_file = f"gallery_{query.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        searcher.generate_html_gallery(results, html_file)
        
        print(f"\n✨ SUCCESS!")
        print(f"Found {len(results)} high-resolution portrait paintings")
        print(f"Results saved to:")
        print(f"  📄 {json_file}")
        print(f"  🌐 {html_file}")
        print(f"\nOpen the HTML file in your browser to view the gallery!")
    else:
        print("\n⚠️  No paintings found matching the criteria")
        print("Try different search terms or check your internet connection")


if __name__ == "__main__":
    main()
