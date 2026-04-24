#!/usr/bin/env python3
import re
from pathlib import Path

# Downloader/ -> onlineimages/ -> assets/ -> PlantCare/database.js
DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / "database.js"

def js_slug(plant_name):
    s = re.sub(r'[^a-zA-Z0-9]', '_', plant_name)
    s = re.sub(r'_+', '_', s)
    s = s.rstrip('_')
    return s

def extract_plants(db_path):
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

    # Deduplicate by id
    seen = set()
    unique = []
    for p in found:
        if p['id'] not in seen:
            seen.add(p['id'])
            unique.append(p)
    return sorted(unique, key=lambda x: x['slug'])

plants = extract_plants(DB_PATH)
print(f'Total plants: {len(plants)}')
for p in plants:
    print(f'  [{p["id"]:3d}] {p["slug"]}.jpg  <-  {p["name"]}')
