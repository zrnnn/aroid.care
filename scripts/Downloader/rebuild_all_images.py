#!/usr/bin/env python3
"""
Project Aroid — Full Image Rebuild
====================================
1. Parses all plant names from database.js using the EXACT same slug
   formula the website uses:
   p.n.replace(/[^a-zA-Z0-9]/g,'_').replace(/_+/g,'_').replace(/_$/,'')
2. Clears every .jpg in the onlineimages/ folder
3. Downloads a fresh CC-licensed image for every plant
   (Openverse → iNaturalist → Wikimedia)
4. Resizes + center-crops to 1200x1500 px (4:5, matches website cards)
5. Saves as <slug>.jpg in onlineimages/
6. Writes _attribution_log.json with source / license info
"""

import json
import os
import re
import sys
import time
import io
from pathlib import Path

import requests
from PIL import Image
from tqdm import tqdm

# ─── Paths ────────────────────────────────────────────────────────────────────
# Script is at: PlantCare/assets/onlineimages/Downloader/rebuild_all_images.py
SCRIPT_DIR  = Path(__file__).resolve().parent
IMAGES_DIR  = SCRIPT_DIR.parent              # …/assets/onlineimages/
DB_PATH     = SCRIPT_DIR.parent.parent.parent / "database.js"  # …/PlantCare/database.js

TARGET_W, TARGET_H = 1200, 1500   # 4:5 portrait
MIN_SIZE           = 200           # px (shortest side minimum before download)
CANDIDATES         = 8             # how many candidates to evaluate per plant
REQUEST_DELAY      = 1.2           # seconds between API calls

HEADERS = {
    "User-Agent": "ProjectAroidImageRebuild/2.0 (botanical-archive; open-source)"
}

# ─── Slug Formula (mirrors JS exactly) ────────────────────────────────────────

def js_slug(plant_name: str) -> str:
    s = re.sub(r'[^a-zA-Z0-9]', '_', plant_name)
    s = re.sub(r'_+', '_', s)
    s = s.rstrip('_')
    return s

# ─── Extract plants from database.js ──────────────────────────────────────────

def extract_plants(db_path: Path) -> list[dict]:
    text = db_path.read_text(encoding='utf-8')
    found = []
    id_pattern = re.compile(r'\{\s*id\s*:\s*(\d+)')
    for id_match in id_pattern.finditer(text):
        pid = int(id_match.group(1))
        chunk = text[id_match.start(): id_match.start() + 2000]
        # Match n: 'value' where value may contain escaped \'
        n_match = re.search(r"n\s*:\s*'((?:[^'\\]|\\.)*?)'", chunk)
        if not n_match:
            continue
        raw  = n_match.group(1)
        name = raw.replace("\\'", "'")
        slug = js_slug(name)
        found.append({'id': pid, 'name': name, 'slug': slug})

    seen   = set()
    unique = []
    for p in found:
        if p['id'] not in seen:
            seen.add(p['id'])
            unique.append(p)
    return sorted(unique, key=lambda x: x['slug'])

# ─── Search Sources ────────────────────────────────────────────────────────────

def search_openverse(plant: str, candidates: int) -> list[dict]:
    params = {
        "q": plant.replace("'", ""),
        "category": "photograph",
        "page_size": candidates * 4,
    }
    url = "https://api.openverse.org/v1/images/?" + "&".join(f"{k}={v}" for k, v in params.items())
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"      Openverse error: {e}")
        return []
    results = []
    for item in data.get("results", []):
        img_url = item.get("url") or item.get("thumbnail")
        if not img_url:
            continue
        results.append({
            "url": img_url,
            "license": item.get("license", ""),
            "source": "openverse",
            "width": item.get("width", 0),
            "height": item.get("height", 0),
            "attribution": item.get("attribution", ""),
        })
    return results


def search_inaturalist(plant: str, candidates: int) -> list[dict]:
    try:
        r = requests.get("https://api.inaturalist.org/v1/taxa",
                         params={"q": plant.split()[0], "rank": "genus"}, timeout=15)
        r.raise_for_status()
        taxa = r.json().get("results", [])
    except Exception as e:
        print(f"      iNaturalist taxon error: {e}")
        return []
    if not taxa:
        return []
    taxon_id = taxa[0]["id"]
    try:
        r = requests.get("https://api.inaturalist.org/v1/observations",
                         params={"taxon_id": taxon_id, "photos": True,
                                 "per_page": candidates * 2, "order_by": "votes"},
                         headers=HEADERS, timeout=15)
        r.raise_for_status()
        observations = r.json().get("results", [])
    except Exception as e:
        print(f"      iNaturalist obs error: {e}")
        return []
    results = []
    for obs in observations:
        for photo in obs.get("photos", []):
            lc = photo.get("license_code", "unknown")
            url = photo.get("url", "").replace("square", "large")
            if not url:
                continue
            results.append({
                "url": url,
                "license": lc,
                "source": "inaturalist",
                "width": 0, "height": 0,
                "attribution": f"iNaturalist obs #{obs.get('id')} by {obs.get('user', {}).get('login', '?')}",
            })
    return results


def search_wikimedia(plant: str, candidates: int) -> list[dict]:
    params = {
        "action": "query", "generator": "search",
        "gsrnamespace": 6, "gsrsearch": f"{plant} plant",
        "gsrlimit": candidates * 2, "prop": "imageinfo",
        "iiprop": "url|size|extmetadata", "iiurlwidth": 1200, "format": "json",
    }
    try:
        r = requests.get("https://commons.wikimedia.org/w/api.php",
                         params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"      Wikimedia error: {e}")
        return []
    results = []
    for page in data.get("query", {}).get("pages", {}).values():
        info_list = page.get("imageinfo", [])
        if not info_list:
            continue
        info = info_list[0]
        img_url = info.get("url", "")
        if not img_url:
            continue
        if not any(img_url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
            continue
        meta = info.get("extmetadata", {})
        license_name = meta.get("LicenseShortName", {}).get("value", "CC")
        artist = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "unknown"))
        results.append({
            "url": img_url,
            "license": license_name,
            "source": "wikimedia",
            "width": info.get("width", 0),
            "height": info.get("height", 0),
            "attribution": f"Wikimedia Commons, {artist}, {license_name}",
        })
    return results

# ─── Download + Validate + Resize ─────────────────────────────────────────────

def fetch_and_validate(url: str, min_size: int):
    try:
        r = requests.get(url, headers=HEADERS, timeout=25, stream=True)
        r.raise_for_status()
        data = b""
        for chunk in r.iter_content(chunk_size=16384):
            data += chunk
            if len(data) > 20 * 1024 * 1024:
                break
        r.close()
        img = Image.open(io.BytesIO(data)).convert("RGB")
        w, h = img.size
        if min(w, h) < min_size:
            return None, w, h
        return img, w, h
    except Exception as e:
        print(f"      fetch error: {e}")
        return None, 0, 0


def resize_and_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Cover resize then center crop."""
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w = round(src_w * scale)
    new_h = round(src_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top  = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))

# ─── Core: find + save one plant ──────────────────────────────────────────────

def find_and_save(plant_name: str, dest_path: Path, log: list) -> bool:
    all_candidates = []

    print(f"    -> Openverse ...")
    all_candidates.extend(search_openverse(plant_name, CANDIDATES))
    time.sleep(REQUEST_DELAY)

    if len(all_candidates) < CANDIDATES:
        print(f"    -> iNaturalist ...")
        all_candidates.extend(search_inaturalist(plant_name, CANDIDATES))
        time.sleep(REQUEST_DELAY)

    if len(all_candidates) < CANDIDATES:
        print(f"    -> Wikimedia ...")
        all_candidates.extend(search_wikimedia(plant_name, CANDIDATES))
        time.sleep(REQUEST_DELAY)

    # Sort by declared size
    all_candidates.sort(key=lambda c: min(c.get("width", 0), c.get("height", 0)), reverse=True)

    for candidate in all_candidates[:CANDIDATES * 2]:
        img, w, h = fetch_and_validate(candidate["url"], MIN_SIZE)
        if img is None:
            if w or h:
                print(f"      Too small ({w}x{h}), skipping ...")
            continue

        img = resize_and_crop(img, TARGET_W, TARGET_H)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(dest_path), "JPEG", quality=88, optimize=True)

        log.append({
            "plant":        plant_name,
            "slug":         dest_path.stem,
            "source":       candidate["source"],
            "url":          candidate["url"],
            "license":      candidate["license"],
            "original_size": f"{w}x{h}",
            "saved_size":   f"{TARGET_W}x{TARGET_H}",
            "attribution":  candidate["attribution"],
        })
        print(f"    Saved {TARGET_W}x{TARGET_H}  [{candidate['source']} / {candidate['license']}]")
        return True

    print(f"    No suitable image found.")
    return False

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("\nProject Aroid -- Full Image Rebuild")
    print(f"   Database:  {DB_PATH}")
    print(f"   Output:    {IMAGES_DIR}")
    print(f"   Target:    {TARGET_W}x{TARGET_H} px (JPEG)")

    if not DB_PATH.exists():
        print(f"ERROR: database.js not found at {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    plants = extract_plants(DB_PATH)
    print(f"\n   Found {len(plants)} plants in database.js\n")

    # Do not clear existing images to preserve the AI-generated ones.

    log     = []
    skipped = []

    for i, p in enumerate(tqdm(plants, desc="Downloading", unit="plant"), 1):
        name = p["name"]
        slug = p["slug"]
        dest = IMAGES_DIR / f"{slug}.jpg"

        print(f"\n[{i}/{len(plants)}] {name}")
        print(f"    slug -> {slug}.jpg")

        if dest.exists():
            print(f"    Already exists, skipping download.")
            continue

        ok = find_and_save(name, dest, log)
        if not ok:
            skipped.append(name)

        time.sleep(REQUEST_DELAY)

    print(f"\n{'─'*60}")
    print(f"Done! {len(log)} images downloaded and resized.")
    if skipped:
        print(f"Skipped ({len(skipped)}):")
        for s in skipped:
            print(f"  - {s}")

    log_path = IMAGES_DIR / "_attribution_log.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    print(f"Attribution log: {log_path}")

    # Update Inventory
    inv_path = IMAGES_DIR / "image_inventory.json"
    inventory = {}
    if inv_path.exists():
        inventory = json.loads(inv_path.read_text(encoding='utf-8'))
    
    for entry in log:
        slug = entry["slug"]
        inventory[slug] = "downloaded"
    
    with open(inv_path, "w", encoding="utf-8") as f:
        json.dump(inventory, f, indent=2, ensure_ascii=False)
    print(f"Inventory updated: {inv_path}")


if __name__ == "__main__":
    main()
