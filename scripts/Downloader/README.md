# 🌿 Plant Image Downloader

Automatisch CC-lizenzierte Pflanzenbilder suchen, prüfen, herunterladen und umbenennen.

## Quellen

| Quelle | Lizenz | Besonderheit |
|--------|--------|-------------|
| **Openverse** (WordPress/CC) | CC BY, CC BY-SA, CC0 u.a. | Größte CC-Bilddatenbank |
| **iNaturalist** | CC BY, CC BY-NC u.a. | Spezialisiert auf Naturfotos, sehr hohe Qualität |

---

## Setup

```bash
# Python 3.10+ benötigt
pip install requests Pillow tqdm
```

---

## Nutzung

### Einfachste Variante – Liste aus Datei:
```bash
python plant_downloader.py --list plants.txt --out ./meine_bilder
```

### Einzelne Pflanze testen:
```bash
python plant_downloader.py --plant "Anthurium luxurians" --out ./test
```

### Mit allen Optionen:
```bash
python plant_downloader.py \
  --list plants.txt \
  --out ./plant_images \
  --min-size 800 \
  --candidates 10
```

---

## Parameter

| Parameter | Standard | Beschreibung |
|-----------|----------|-------------|
| `--list FILE` | – | Textdatei mit Pflanzennamen (eine pro Zeile) |
| `--plant NAME` | – | Einzelner Pflanzenname (zum Testen) |
| `--out DIR` | `./plant_images` | Ausgabeordner |
| `--min-size PX` | `500` | Mindestgröße in Pixel (kürzeste Seite) |
| `--candidates N` | `5` | Wie viele Kandidaten pro Pflanze geprüft werden |

---

## Pflanzenliste (plants.txt)

```
# Kommentare mit # ignoriert
Anthurium luxurians
Monstera deliciosa
Philodendron gloriosum
# Begonia pavonina   ← auskommentiert, wird übersprungen
Hoya kerrii
```

---

## Ausgabe

```
plant_images/
├── anthurium_luxurians.jpg
├── monstera_deliciosa.jpg
├── philodendron_gloriosum.jpg
└── _attribution_log.json      ← Lizenz & Quellen aller Bilder
```

### Attribution Log (`_attribution_log.json`)
```json
[
  {
    "plant": "Anthurium luxurians",
    "source": "inaturalist",
    "url": "https://...",
    "license": "cc-by-nc",
    "size": "1024×768",
    "attribution": "iNaturalist obs #12345678 by username"
  }
]
```

---

## Tipps für beste Ergebnisse

- **Wissenschaftliche Namen** verwenden (z.B. `Monstera deliciosa` statt `Monstera`)
- `--candidates 8` oder höher setzen, wenn Bilder oft zu klein sind
- `--min-size 800` für höhere Qualität
- Bereits heruntergeladene Pflanzen werden **übersprungen** – du kannst jederzeit weitermachen
- Das Skript legt eine Pause zwischen Anfragen ein (API-freundlich)

---

## Häufige Probleme

| Problem | Lösung |
|---------|--------|
| Pflanze nicht gefunden | Prüfe den wissenschaftlichen Namen; iNaturalist kennt fast alle Arten |
| Alle Bilder zu klein | `--candidates 10` und `--min-size 500` |
| Langsam | Normal – API-Pausen sind Absicht, um nicht geblockt zu werden |
