import os
import re
import sys
import requests
from io import BytesIO
from PIL import Image
import time

sys.path.append(os.path.join(os.path.dirname(__file__), 'Downloader'))
import plant_downloader

DATABASE_PATH = '../database.js'
ASSETS_DIR = '../assets'

def parse_database():
    plants = []
    with open(DATABASE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    match = re.search(r'const plantsData\s*=\s*\[(.*?)\];', content, re.DOTALL)
    if not match:
        print("Could not find plantsData")
        return plants

    data_str = match.group(1)
    parts = data_str.split('{ id:')
    for part in parts[1:]:
        id_match = re.search(r'^\s*([0-9a-zA-Z_]+)', part)
        if not id_match: continue
        pid = id_match.group(1)
        
        n_match = re.search(r"n:\s*'((?:[^'\\]|\\.)*)'", part)
        if not n_match:
            n_match = re.search(r'n:\s*"((?:[^"\\]|\\.)*)"', part)
            
        if n_match:
            name = n_match.group(1).replace("\\'", "'").replace('\\"', '"')
            plants.append({'id': pid, 'name': name})
            
    return plants

def download_and_process_image(url, output_path):
    try:
        headers = {
            'User-Agent': 'PlantCare Image Scraper (https://github.com/example/plantcare)'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        target_w, target_h = 800, 1000
        target_ratio = target_w / target_h
        img_ratio = img.width / img.height
        
        if img_ratio > target_ratio:
            new_h = int(img.width / target_ratio)
            padded = Image.new('RGB', (img.width, new_h), (255, 255, 255))
            padded.paste(img, (0, (new_h - img.height) // 2))
            img = padded
        elif img_ratio < target_ratio:
            new_w = int(img.height * target_ratio)
            padded = Image.new('RGB', (new_w, img.height), (255, 255, 255))
            padded.paste(img, ((new_w - img.width) // 2, 0))
            img = padded
            
        img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        img.save(output_path, 'JPEG', quality=85)
        return True
    except Exception as e:
        print(f"Error processing image from {url}: {e}")
        return False

def search_wikimedia(query):
    query = query.strip()
    headers = {
        'User-Agent': 'PlantCare Image Scraper (zrnnn@example.com)'
    }
    # Try searching Wikipedia first for the exact page
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "pageimages",
        "format": "json",
        "piprop": "original",
        "titles": query
    }
    try:
        res = requests.get(url, params=params, headers=headers, timeout=10).json()
        pages = res.get('query', {}).get('pages', {})
        for page_id, page_data in pages.items():
            if page_id != '-1' and 'original' in page_data:
                return page_data['original']['source']
    except Exception as e:
        print(f"  Error Wikipedia API: {e}")
        
    # Fallback to Wikimedia Commons search
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": f"{query} plant",
        "srnamespace": "6",
        "format": "json"
    }
    try:
        res = requests.get(url, params=params, headers=headers, timeout=10).json()
        search_results = res.get('query', {}).get('search', [])
        if search_results:
            title = search_results[0]['title']
            img_params = {
                "action": "query",
                "titles": title,
                "prop": "imageinfo",
                "iiprop": "url",
                "format": "json"
            }
            img_res = requests.get(url, params=img_params, headers=headers, timeout=10).json()
            pages = img_res.get('query', {}).get('pages', {})
            for page_id, page_data in pages.items():
                if 'imageinfo' in page_data:
                    return page_data['imageinfo'][0]['url']
    except Exception as e:
        print(f"  Error Commons API: {e}")
        
    return None

def main():
    if not os.path.exists(ASSETS_DIR):
        os.makedirs(ASSETS_DIR)
        
    plants = parse_database()
    print(f"Found {len(plants)} plants in database.")
    
    for plant in plants:
        # JS equivalent slug logic: p.n.replace(/\(Non-Aroid\)/g, '').replace(/[^a-zA-Z0-9]/g, '_').replace(/_+/g, '_').replace(/_$/, '');
        slug = re.sub(r'\(Non-Aroid\)', '', plant['name'])
        slug = re.sub(r'[^a-zA-Z0-9]', '_', slug)
        slug = re.sub(r'_+', '_', slug)
        slug = slug.rstrip('_').lower()
        
        output_path = os.path.join(ASSETS_DIR, f"plant_{slug}.jpg")
        if os.path.exists(output_path):
            print(f"[{plant['name']}] Image already exists. Skipping.")
            continue
            
        # Clean name for search
        search_name = plant['name'].replace('\\', '').replace('\'', '')
        
        print(f"[{plant['name']}] Searching Openverse, iNaturalist, Wikimedia...")
        
        candidate = plant_downloader.find_best_image(search_name, candidates=3, min_size=600, log=[])
        if not candidate:
            base_name = search_name.split(' ')[0] + ' ' + search_name.split(' ')[1] if len(search_name.split(' ')) > 1 else search_name
            if base_name != search_name:
                print(f"  Fallback searching for '{base_name}'...")
                candidate = plant_downloader.find_best_image(base_name, candidates=3, min_size=600, log=[])
            
        if candidate:
            img_url = candidate['url']
            print(f"  Downloading {img_url} from {candidate['source']}")
            if download_and_process_image(img_url, output_path):
                print(f"  Successfully saved to {output_path}")
            else:
                print(f"  Failed to process {img_url}")
        else:
            print(f"  Failed to find any image for {plant['name']}")
            
        time.sleep(1)

if __name__ == "__main__":
    main()
