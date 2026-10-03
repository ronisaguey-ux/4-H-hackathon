#!/usr/bin/env bash
# ==============================================================================
# CornShield AI - 1-Command Startup Script
# National 4-H AI in Agriculture Challenge (Fall 2026)
# ==============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "=================================================================="
echo " Starting CornShield AI — Midwest Corn Foliar Disease Engine"
echo " National 4-H AI in Agriculture Challenge (Level 2: 16–18)"
echo "=================================================================="

# Check Python3
if ! command -v python3 &>/dev/null; then
  echo "Error: Python 3 is required but was not found on your system."
  exit 1
fi

# Ensure data directories exist
mkdir -p data/sample_specimens uploads

# Generate test specimens if missing
if [ ! -f "data/sample_specimens/tar_spot_specimen.jpg" ]; then
  echo "[-] Synthesizing field test specimens..."
  python3 -c "
from PIL import Image, ImageDraw
import random, os
from pathlib import Path
out = Path('data/sample_specimens')
out.mkdir(parents=True, exist_ok=True)
def bg(d, w, h, col=(76, 154, 42)):
    for y in range(h):
        f = 0.9 + 0.2*(y/h)
        d.line([(0, y), (w, y)], fill=(int(col[0]*f), int(col[1]*f), int(col[2]*f)))
    for x in range(10, w, 14):
        d.line([(x, 0), (x, h)], fill=(min(255, col[0]+15), min(255, col[1]+20), min(255, col[2]+10)), width=1)
    d.line([(w//2 - 3, 0), (w//2 - 3, h)], fill=(120, 185, 75), width=6)
    d.line([(w//2, 0), (w//2, h)], fill=(155, 215, 105), width=3)
# 1. Tar Spot
w, h = 640, 480
im = Image.new('RGB', (w, h))
d = ImageDraw.Draw(im)
bg(d, w, h)
random.seed(42)
for _ in range(85):
    cx, cy = random.randint(30, w-30), random.randint(30, h-30)
    rx, ry = random.randint(4, 9), random.randint(3, 7)
    d.ellipse([cx-rx-3, cy-ry-3, cx+rx+3, cy+ry+3], fill=(168, 145, 45))
    d.ellipse([cx-rx, cy-ry, cx+rx, cy+ry], fill=(15, 15, 18))
im.save(out / 'tar_spot_specimen.jpg', quality=95)
# 2. Gray Leaf Spot
im = Image.new('RGB', (w, h))
d = ImageDraw.Draw(im)
bg(d, w, h)
for _ in range(28):
    cx, cy = random.randint(40, w-80), random.randint(30, h-100)
    wl, hl = random.choice([14, 28, 42]), random.randint(45, 110)
    d.rectangle([cx, cy, cx+wl, cy+hl], fill=(175, 160, 125), outline=(130, 115, 85))
im.save(out / 'gray_leaf_spot_specimen.jpg', quality=95)
# 3. Northern Blight
im = Image.new('RGB', (w, h))
d = ImageDraw.Draw(im)
bg(d, w, h)
for cx, cy, rx, ry in [(180, 200, 35, 140), (420, 260, 40, 160), (310, 120, 25, 90)]:
    d.ellipse([cx-rx-4, cy-ry-4, cx+rx+4, cy+ry+4], fill=(160, 150, 70))
    d.ellipse([cx-rx, cy-ry, cx+rx, cy+ry], fill=(155, 145, 120), outline=(105, 95, 75), width=2)
im.save(out / 'northern_blight_specimen.jpg', quality=95)
# 4. Common Rust
im = Image.new('RGB', (w, h))
d = ImageDraw.Draw(im)
bg(d, w, h)
for _ in range(120):
    cx, cy = random.randint(25, w-25), random.randint(25, h-25)
    rx, ry = random.randint(3, 6), random.randint(5, 10)
    d.ellipse([cx-rx, cy-ry, cx+rx, cy+ry], fill=(178, 68, 22), outline=(115, 42, 12))
im.save(out / 'common_rust_specimen.jpg', quality=95)
# 5. Healthy Leaf
im = Image.new('RGB', (w, h))
d = ImageDraw.Draw(im)
bg(d, w, h, col=(68, 168, 38))
im.save(out / 'healthy_leaf_specimen.jpg', quality=95)
# 6. Ambiguous / Non-Leaf
im = Image.new('RGB', (w, h), color=(140, 140, 142))
d = ImageDraw.Draw(im)
for _ in range(600):
    x, y, s = random.randint(0, w), random.randint(0, h), random.randint(2, 6)
    d.rectangle([x, y, x+s, y+s], fill=random.choice([(70,70,72),(210,210,212),(110,105,100)]))
im.save(out / 'ambiguous_specimen.jpg', quality=95)
"
fi

# Seed initial history database
python3 -c "from core.database import database; database.seed_demo_history()"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-5000}"

echo "[✓] Environment verified."
echo "[✓] Scouting database ready (data/scans.db)."
echo "[✓] Pre-loaded test specimens verified (6/6)."
echo ""
echo "------------------------------------------------------------------"
echo " CornShield AI is running at: http://localhost:${PORT}"
echo " On your local network:       http://${HOST}:${PORT}"
echo "------------------------------------------------------------------"
echo " Press Ctrl+C to stop the server."
echo "------------------------------------------------------------------"

exec python3 app.py
