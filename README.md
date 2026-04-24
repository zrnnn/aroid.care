# Project.Aroid - The Botanical Archive

## Overview
**Project.Aroid** is a modern, high-end, interactive Single-Page Application (SPA) designed as a digital encyclopedia and scientific diagnostic center for rare tropical aroids and exotic houseplants. 

The application utilizes a stunning "Editorial Nature" dark theme, relying on heavy glassmorphism, fluid micro-animations, and a highly responsive single-file architecture (`index.html`). It is designed to emulate the premium feel of a luxury editorial magazine while delivering deeply scientific horticultural data.

## Architecture & Technology Stack
- **Structure:** Single-File Architecture (HTML, CSS, and JavaScript encapsulated in a single file) for maximum portability and instant load times.
- **Styling:** [Tailwind CSS](https://tailwindcss.com/) (via CDN).
  - **Aesthetics:** Deep "moody" dark mode with a blurred, fading background image, subtle CSS noise overlay, and heavy use of frosted glass (`backdrop-filter`).
  - **Color Palette:** Curated `forest` and `sage` tokens to maintain a natural, cohesive, and premium aesthetic.
  - **Typography:** *Inter* (Sans-Serif) heavily utilizing negative tracking and massive font weights (`font-black`) for striking, editorial headlines.
- **Logic:** Vanilla ES6 JavaScript (DOM Manipulation & Routing).
- **Routing:** Custom `history.pushState` implementation for smooth, URL-based navigation without page reloads, fully supporting browser back/forward buttons.

## Features & Functionalities

### 1. The Botanical Archive (Catalog)
- **Extensive Database:** Contains **68** meticulously researched plant species across 13 genera (Monstera, Philodendron, Anthurium, Alocasia, Syngonium, Hoya, Ficus, etc.).
- **Smart Search & Filtering:** 
  - Real-time search by name, genus, or botanical traits.
  - Quick-filter tags for genera and variegation.
  - Dedicated mobile-friendly search bar.
- **Advanced Sorting:** Dropdown UI to sort the catalog by **Name (A-Z)**, **Difficulty Level**, and **Light Requirements**.

### 2. Immersive Detail Pages
Clicking a plant card opens a full-screen, deeply immersive detail view featuring:
- **Scientific Lore:** Extended paragraphs detailing the plant's evolutionary background, natural habitat, and botanical anomalies (e.g., nyctinasty, meristematic tissue instability).
- **Care Parameters:** Sleek glass tiles displaying exact requirements for Light, Water, Humidity, Toxicity, Difficulty, and Fertilizer.
- **Animated Substrate Visualizers:** Horizontal CSS-animated percentage bars that visually break down the perfect Organic and Mineral soil mixtures.
- **Cross-Linked Pest Warnings:** "Common Pests" are listed as interactive tags that route directly to the Diagnostics Center.

### 3. Diagnostics Center (First Aid)
A comprehensive, visual deep-dive into plant health, featuring dedicated pages for every issue:
- **10 Nutrient Deficiencies:** (e.g., Nitrogen, Calcium, Iron, Manganese).
- **6 Critical Pests:** (Spider Mites, Thrips, Mealybugs, Scale, Fungus Gnats, Aphids).
- **Scientific Deep Dives:** Every diagnostic page explains the cellular biological mechanism of the issue, how to spot it, look-alikes, exact eradication steps, and the pest's lifecycle.

### 4. Propagation Guide
A sleek, dual-column layout detailing professional propagation techniques:
- **Node Cuttings:** For climbing hemiepiphytes.
- **Rhizome Division:** For terrestrial and clumping species.

## Data Model & Logic
The application employs an efficient, object-oriented data architecture to minimize redundancy (DRY):
1. **`genusDefaults`:** Baseline care parameters, common pests, and substrate recipes for overarching genera (e.g., all Anthuriums share baseline humidity needs).
2. **`plantsData`:** An array of 68 specific objects containing the unique ID, genus (`g`), name (`n`), scientific lore (`feat`), and difficulty level (`lvl`).
3. **`override` System:** Specific plants can override `genusDefaults`. For example, *Monstera obliqua 'Peru'* overrides the standard Monstera humidity requirement to be much higher.
4. **`diagnosticsData` & `pestData`:** Massive arrays containing the deep scientific copy for the Diagnostics Center.

## Installation & Execution
Because this is a pure client-side application (no backend or build step required):
1. Save `index.html`, `database.js`, and the `./assets/` folder locally.
2. Open `index.html` in any modern web browser.
3. *Note on Routing:* If running directly via the `file://` protocol, `history.pushState` will be safely caught in a `try/catch` block to prevent CORS errors. For full URL updating functionality, run a simple local server (e.g., `python3 -m http.server`).


## GitHub Pages Deployment
This repository is configured for automated GitHub Pages deployment via GitHub Actions (`.github/workflows/deploy-pages.yml`).

- **Suggested site URL:** `https://<your-github-username>.github.io/aroid.care/`
- In GitHub repo settings, set **Pages → Build and deployment → Source = GitHub Actions**.
- Push to `main` to publish updates automatically.

## Extensibility (For Developers)
- **Adding Plants:** Add a new object to the `plantsData` array in `database.js`. Download an image, name it matching the plant's slug (e.g., `monstera_deliciosa.jpg`), and place it in `./assets/onlineimages/`.
- **Generating Unified Images:** Check the `image_generation_prompt.md` file for the exact LLM prompt formula used to generate the high-end, 1:1 macro photography assets.
