# Farm Tower Defense 🌾

A turn-based farming combat game with a **Python CLI** and a **Flask web demo(Not yet)**.

## Features

### Core Gameplay
- **Turn-based combat** with Attack, Heal, and Skills
- **6 skills** with cooldowns and unique effects
- **Boss waves every 5 rounds** with names and ASCII intros
- **Story arcs** at milestone waves, then **Endless Mode** after the finale
- **Area transitions** with flavorful descriptions

### Events & Progression
- **Random events every 3 waves**, plus **wave‑range events**
- **Chance for a second random event** with special messaging
- **Event cycling** so events rotate before repeating

### Shop & Konami
- **Shop items** (tonics, gold, seeds) with **end‑game replacements** in Endless Mode
- **Konami fragments** drop from bosses, **corrode after 5 rounds**, and can be activated
- **Unlimited activations** with **dynamic Konami pricing** that increases every 3 successes

## Versions

### Python CLI
- Modular classes with type hints and test-friendly IO
- Comprehensive unit tests

### Web Demo (Flask)
- Minimal UI for browser play
- Mirrors CLI mechanics (endless mode, events, shop)

## Requirements

- **Python**: 3.10+ (stdlib only for CLI)
- **Web**: Flask (`web_app/requirements.txt`)

## How to Play

### Python (CLI)
```bash
python farm_tower_defense.py
```

### Web (Flask)
```bash
cd web_app
python app.py
```
Then open `http://127.0.0.1:5000`.

## Running Tests

```bash
python -m unittest test_farm_tower_defense.py
```

## Project Structure

- `farm_tower_defense.py` – Python implementation
- `web_app/` – Flask web demo
- `test_farm_tower_defense.py` – Unit tests
- `README.md` – This file
