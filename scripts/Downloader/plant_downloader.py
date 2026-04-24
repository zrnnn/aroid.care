#!/usr/bin/env python3
"""
Plant Image Downloader
======================
Searches for Creative Commons plant images via Openverse + iNaturalist,
validates them against style criteria, downloads and renames them.

Usage:
    python plant_downloader.py --list plants.txt --out ./plant_images
    python plant_downloader.py --list plants.txt --out ./plant_images --min-size 500 --max-per-plant 3
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

import requests
from PIL import Image
from tqdm import tqdm


# ─── Config Defaults ──────────────────────────────────────────────────────────

DEFAULT_MIN_SIZE    = 500       # px (shorter side)
DEFAULT_MAX_RESULTS = 1         # images per plant (set higher to pick best)
DEFAULT_CANDIDATES  = 5         # how many candidates to evaluate per plant
REQUEST_DELAY       = 1.0       # seconds between API calls (be polite)
DOWNLOAD_TIMEOUT    = 20        # seconds

HEADERS = {
    "User-Agent": "PlantImageDownloader/1.0 (botanical-collection; contact@example.com)"
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def slugify(name: str) -> str:
    """Turn 'Anthurium luxurians' → 'anthurium_luxurians'"""
    return re.sub(r"[^\w]+", "_", name.strip().lower()).strip("_")


def check_image_size(url: str, min_size: int) -> tuple[bool, int, int]:
    """
    Download image headers / small chunk to check dimensions.
    Returns (passes, width, height).
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=DOWNLOAD_TIMEOUT, stream=True)
        resp.raise_for_status()
        # Read only first 64 KB to let Pillow detect size
        chunk = b""
        for data in resp.iter_content(chunk_size=8192):
            chunk += data
            if len(chunk) >= 65536:
                break
        resp.close()

        import io
        img = Image.open(io.BytesIO(chunk))
        w, h = img.size
        return min(w, h) >= min_size, w, h
    except Exception:
        return False, 0, 0


def download_image(url: str, dest_path: Path) -> bool:
    """Download full image to dest_path. Returns True on success."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=DOWNLOAD_TIMEOUT, stream=True)
        resp.raise_for_status()
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=16384):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"      ✗ Download failed: {e}")
        return False


# ─── Source 1: Openverse (Creative Commons) ───────────────────────────────────

def search_openverse(plant: str, candidates: int, min_size: int) -> list[dict]:
    """
    Search Openverse for CC-licensed plant images.
    Returns list of candidate dicts with keys: url, title, license, source, width, height.
    """
    params = {
        "q": f"{plant} plant closeup",
        "license_type": "commercial,modification",   # CC licenses that allow reuse
        "category": "photograph",
        "page_size": candidates * 2,                 # fetch extra; some will fail size check
        "unstable__include_sensitive_results": False,
    }
    # Prefer larger images
    url = f"https://api.openverse.org/v1/images/?{urlencode(params)}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"      Openverse API error: {e}")
        return []

    results = []
    for item in data.get("results", []):
        img_url = item.get("url") or item.get("thumbnail")
        if not img_url:
            continue
        results.append({
            "url":     img_url,
            "title":   item.get("title", ""),
            "license": item.get("license", ""),
            "source":  "openverse",
            "width":   item.get("width", 0),
            "height":  item.get("height", 0),
            "attribution": item.get("attribution", ""),
        })
    return results


# ─── Source 2: iNaturalist ────────────────────────────────────────────────────

def search_inaturalist(plant: str, candidates: int) -> list[dict]:
    """
    Search iNaturalist for plant observations with CC-licensed photos.
    """
    # Step 1: resolve taxon ID
    taxon_url = "https://api.inaturalist.org/v1/taxa"
    try:
        resp = requests.get(taxon_url, params={"q": plant, "rank": "species,genus"}, timeout=15)
        resp.raise_for_status()
        taxa = resp.json().get("results", [])
    except Exception as e:
        print(f"      iNaturalist taxon error: {e}")
        return []

    if not taxa:
        return []

    taxon_id = taxa[0]["id"]

    # Step 2: find observations with CC photos
    obs_url = "https://api.inaturalist.org/v1/observations"
    params = {
        "taxon_id": taxon_id,
        "photos": True,
        "photo_licensed": True,
        "quality_grade": "research",
        "per_page": candidates * 2,
        "order_by": "votes",
    }
    try:
        resp = requests.get(obs_url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        observations = resp.json().get("results", [])
    except Exception as e:
        print(f"      iNaturalist obs error: {e}")
        return []

    results = []
    for obs in observations:
        for photo in obs.get("photos", []):
            license_code = photo.get("license_code", "")
            if not license_code:
                continue  # skip all-rights-reserved
            # Get large size
            url = photo.get("url", "").replace("square", "large")
            if not url:
                continue
            results.append({
                "url":     url,
                "title":   obs.get("species_guess", plant),
                "license": license_code,
                "source":  "inaturalist",
                "width":   0,   # unknown until download
                "height":  0,
                "attribution": f"iNaturalist obs #{obs.get('id')} by {obs.get('user', {}).get('login', '?')}",
            })
    return results


# ─── Source 3: Wikimedia Commons ─────────────────────────────────────────────

def search_wikimedia(plant: str, candidates: int) -> list[dict]:
    """
    Search Wikimedia Commons for plant images (all CC-licensed or public domain).
    """
    params = {
        "action":      "query",
        "generator":   "search",
        "gsrnamespace": 6,             # File: namespace
        "gsrsearch":   f"{plant} plant",
        "gsrlimit":    candidates * 2,
        "prop":        "imageinfo",
        "iiprop":      "url|size|extmetadata",
        "iiurlwidth":  1200,
        "format":      "json",
    }
    url = "https://commons.wikimedia.org/w/api.php"
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"      Wikimedia API error: {e}")
        return []

    results = []
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        info_list = page.get("imageinfo", [])
        if not info_list:
            continue
        info = info_list[0]
        img_url = info.get("url", "")
        if not img_url:
            continue

        # Only photos (skip SVG, OGG, etc.)
        if not any(img_url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
            continue

        meta   = info.get("extmetadata", {})
        license_name = meta.get("LicenseShortName", {}).get("value", "CC")
        artist = meta.get("Artist", {}).get("value", "unknown")
        # Strip HTML tags from artist
        artist = re.sub(r"<[^>]+>", "", artist)

        results.append({
            "url":     img_url,
            "title":   page.get("title", plant),
            "license": license_name,
            "source":  "wikimedia",
            "width":   info.get("width", 0),
            "height":  info.get("height", 0),
            "attribution": f"Wikimedia Commons, {artist}, {license_name}",
        })
    return results


# ─── Core Logic ───────────────────────────────────────────────────────────────

def find_best_image(plant: str, candidates: int, min_size: int, log: list) -> dict | None:
    """
    Try Openverse first, then iNaturalist. 
    Returns first candidate that passes the size check, or None.
    """
    all_candidates = []

    # Gather candidates from both sources
    print(f"    → Openverse …")
    ov = search_openverse(plant, candidates, min_size)
    all_candidates.extend(ov)
    time.sleep(REQUEST_DELAY)

    if len(all_candidates) < candidates:
        print(f"    → iNaturalist …")
        inat = search_inaturalist(plant, candidates)
        all_candidates.extend(inat)
        time.sleep(REQUEST_DELAY)

    if len(all_candidates) < candidates:
        print(f"    → Wikimedia Commons …")
        wm = search_wikimedia(plant, candidates)
        all_candidates.extend(wm)
        time.sleep(REQUEST_DELAY)

    # Sort by declared size (prefer larger)
    all_candidates.sort(
        key=lambda c: min(c.get("width", 0), c.get("height", 0)),
        reverse=True
    )

    for candidate in all_candidates[:candidates * 2]:
        passes, w, h = check_image_size(candidate["url"], min_size)
        if passes:
            candidate["width"]  = w
            candidate["height"] = h
            log.append({
                "plant":   plant,
                "source":  candidate["source"],
                "url":     candidate["url"],
                "license": candidate["license"],
                "size":    f"{w}×{h}",
                "attribution": candidate["attribution"],
            })
            return candidate
        else:
            print(f"      ↷ Too small ({w}×{h}), skipping …")

    return None


def ext_from_url(url: str) -> str:
    path = url.split("?")[0]
    suffix = Path(path).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"} else ".jpg"


def run(plant_list: list[str], out_dir: Path, min_size: int, max_per_plant: int, candidates: int):
    out_dir.mkdir(parents=True, exist_ok=True)
    log = []
    skipped = []

    print(f"\n🌿 Plant Image Downloader")
    print(f"   Plants:      {len(plant_list)}")
    print(f"   Output:      {out_dir.resolve()}")
    print(f"   Min size:    {min_size} px")
    print(f"   Max/plant:   {max_per_plant}")
    print(f"   Candidates:  {candidates}\n")

    for i, plant in enumerate(tqdm(plant_list, desc="Plants", unit="plant"), 1):
        plant = plant.strip()
        if not plant or plant.startswith("#"):
            continue

        print(f"\n[{i}/{len(plant_list)}] {plant}")
        slug = slugify(plant)

        # Check if already downloaded
        existing = list(out_dir.glob(f"{slug}*"))
        if existing:
            print(f"    ✓ Already exists: {existing[0].name}")
            continue

        candidate = find_best_image(plant, candidates, min_size, log)

        if candidate is None:
            print(f"    ✗ No suitable image found for '{plant}'")
            skipped.append(plant)
            continue

        ext      = ext_from_url(candidate["url"])
        filename = f"{slug}{ext}"
        dest     = out_dir / filename

        print(f"    ↓ Downloading {candidate['width']}×{candidate['height']} from {candidate['source']} …")
        if download_image(candidate["url"], dest):
            print(f"    ✓ Saved: {filename}  [{candidate['license']}]")
        else:
            skipped.append(plant)

        time.sleep(REQUEST_DELAY)

    # ── Summary ──────────────────────────────────────────────────────────────

    print(f"\n{'─'*60}")
    print(f"✅  Done! {len(log)} images downloaded.")
    if skipped:
        print(f"⚠️   Skipped ({len(skipped)}): {', '.join(skipped)}")

    # Save attribution log
    log_path = out_dir / "_attribution_log.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    print(f"📋  Attribution log: {log_path}")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Download CC-licensed plant images with consistent style.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python plant_downloader.py --list plants.txt --out ./images
  python plant_downloader.py --list plants.txt --out ./images --min-size 800 --candidates 8
  python plant_downloader.py --plant "Monstera deliciosa" --out ./images
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list",  metavar="FILE",  help="Text file with one plant name per line")
    group.add_argument("--plant", metavar="NAME",  help="Single plant name (for testing)")

    parser.add_argument("--out",         default="./plant_images", metavar="DIR",
                        help="Output folder (default: ./plant_images)")
    parser.add_argument("--min-size",    type=int, default=DEFAULT_MIN_SIZE, metavar="PX",
                        help=f"Minimum image dimension in px (default: {DEFAULT_MIN_SIZE})")
    parser.add_argument("--max-per-plant", type=int, default=DEFAULT_MAX_RESULTS, metavar="N",
                        help=f"Max images per plant (default: {DEFAULT_MAX_RESULTS})")
    parser.add_argument("--candidates",  type=int, default=DEFAULT_CANDIDATES, metavar="N",
                        help=f"Candidates to evaluate per plant (default: {DEFAULT_CANDIDATES})")

    args = parser.parse_args()

    if args.list:
        list_path = Path(args.list)
        if not list_path.exists():
            print(f"Error: Plant list '{args.list}' not found.", file=sys.stderr)
            sys.exit(1)
        plants = list_path.read_text(encoding="utf-8").splitlines()
    else:
        plants = [args.plant]

    plants = [p.strip() for p in plants if p.strip() and not p.startswith("#")]

    run(
        plant_list    = plants,
        out_dir       = Path(args.out),
        min_size      = args.min_size,
        max_per_plant = args.max_per_plant,
        candidates    = args.candidates,
    )


if __name__ == "__main__":
    main()
