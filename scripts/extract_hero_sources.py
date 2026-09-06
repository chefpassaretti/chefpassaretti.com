"""
Find each recipe's likely thumbnail source still, resize to web hero, write to
images/recipes/temp for review.

VID*.png thumbnails are Canva exports and are NOT used as heroes.
Their XMP usually lacks a file path, so we:
1. Prefer DaVinci Still*.png exports (and other non-VID photos) in the same folder
2. Prefer candidates whose date aligns with the Canva Created date when present
3. Pick the best visual match with OpenCV template matching
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MEDIA_ROOT = Path(r"C:\Users\mep07\chefpassaretti")
MD_DIR = MEDIA_ROOT / "Web Recipe Pages"
SITE_ROOT = MEDIA_ROOT / "chefpassaretti.com"
OUT_DIR = SITE_ROOT / "images" / "recipes" / "temp"
REPORT = SITE_ROOT / "scripts" / "_hero_source_report.txt"

YT_ID_RE = re.compile(r"youtube\.com/watch\?v=([A-Za-z0-9_-]{6,})")
HERO_MAX = 1600
JPEG_QUALITY = 82

# Manual overrides when folder naming is ambiguous
FOLDER_OVERRIDES = {
    "15-minute-fresh-tomato-pasta": "007 Pomodorini",
    "making-cacio-e-pepe": "001 Cacio e pepe",
    "making-homemade-pizza": "000 Pizza",
    "rigatoni-no-vodka": "002 Rigatoni No Vodka",
    "homemade-guacamole": "003 Guacamole",
    "blended-zucchini-spaghetti": "004 Spaghetti Zucchini",
    "caramelized-zucchini-spaghetti": "031 Fried Zucchini and Spaghetti",
    "one-bowl-chocolate-chip-cookies": "005 Chocolate Chip Cookies",
    "baked-chicken-parmesan": "006 Chicken Parm",
    "tavern-style-thin-crust-pizza": "008 Thin Crust Pizza",
    "homemade-crepes": "009 Crepes",
    "focaccia-barese": "010 Foccacia Barese",
    "lemon-butter-sage-pasta": "011 Lemon Butter Sage Pasta",
    "chicken-marsala": "012 Chicken Marsala",
    "epi-de-ble": "013 Epi de ble",
    "spaghetti-alla-nerano": "014 Spaghetti alla Nerrano",
    "homemade-mushroom-ravioli": "015 Mushroom Ravioli",
    "spaghetti-aglio-e-olio": "016 Spaghetti aglio e olio",
    "marsala-mushroom-risotto": "017 Marsala Risotto",
    "pasta-al-limone": "018 Pasta al limone",
    "grandma-pizza": "019 Grandma Pizza",
    "homemade-tiramisu": "020 Tiramisu",
    "sausage-baby-broccoli-pasta": "021 Sausage and Baby Broccoli Pasta",
    "pasta-pomodoro": "022 Pasta Pomodoro",
    "long-hot-pepper-anchovy-pasta": "023 Pasta with Long Hot Peppers and Anchovies",
    "pistachio-pesto-pasta": "024 Pistachio Pesto Pasta",
    "pappardelle-with-mushrooms": "025 Pappardelle and Mushroom Pasta",
    "eggplant-parmesan": "026 Eggplant Parmesean",
    "sausage-and-peppers": "027 Sausage and Peppers",
    "roasted-red-pepper-pasta": "028 Pepper and Tomato Pasta",
    "sage-brown-butter-gnocchi": "030 Sage and Brown Butter Gnocchi",
    "eggplant-rollatini": "032 Eggplant Rollatini",
    "fresh-tomato-zucchini-pasta": "033 Tomato and Zucchini Pasta",
    "white-wine-lemon-scallop-spaghetti": "034 Spaghetti with Scallops",
    "sausage-and-basil-pasta": "035 Sausage and Basil Pasta",
    "pepperoni-vodka-pasta": "036 Pepperoni Vodka Sauce",
    "mushroom-anchovy-pasta": "039 Spaghetti Mushrooms Anchovies",
}


@dataclass
class Recipe:
    slug: str
    title: str
    hero: str
    youtube_id: str


def normalize_md(text: str) -> str:
    text = text.replace("\\*", "*").replace("\\#", "#").replace("\\-", "-")
    text = text.replace("\\.", ".")
    return re.sub(r"\n{3,}", "\n\n", text)


def field(text: str, name: str) -> str:
    m = re.search(rf"\*\*{re.escape(name)}:\*\*\s*(.+)", text)
    return m.group(1).strip() if m else ""


def load_published_recipes() -> list[Recipe]:
    recipes = []
    for path in sorted(MD_DIR.glob("*.md")):
        raw = normalize_md(path.read_text(encoding="utf-8"))
        youtube = field(raw, "YouTube URL")
        yt = YT_ID_RE.search(youtube or "")
        if not yt:
            continue
        title_m = re.match(r"^#\s+(.+)$", raw, re.MULTILINE)
        slug = field(raw, "Slug") or path.stem
        hero = field(raw, "Hero image") or f"{slug}.jpg"
        recipes.append(
            Recipe(
                slug=slug,
                title=title_m.group(1).strip() if title_m else slug,
                hero=hero,
                youtube_id=yt.group(1),
            )
        )
    return recipes


def numbered_folders() -> dict[str, Path]:
    out = {}
    for d in MEDIA_ROOT.iterdir():
        if not d.is_dir():
            continue
        m = re.match(r"^(\d{3})\s+", d.name)
        if m:
            out[m.group(1)] = d
    return out


def find_folder(recipe: Recipe, folders: dict[str, Path]) -> Path | None:
    if recipe.slug in FOLDER_OVERRIDES:
        p = MEDIA_ROOT / FOLDER_OVERRIDES[recipe.slug]
        if p.is_dir():
            return p
    # Fuzzy: folder name contains distinctive words from title
    title = recipe.title.lower()
    best = None
    best_score = 0
    for folder in folders.values():
        name = re.sub(r"^\d{3}\s+", "", folder.name).lower()
        score = 0
        for token in re.findall(r"[a-z0-9]+", name):
            if len(token) >= 4 and token in title:
                score += len(token)
        if score > best_score:
            best_score = score
            best = folder
    return best if best_score >= 6 else None


def find_thumbnails(folder: Path) -> list[Path]:
    thumbs = []
    for p in folder.iterdir():
        if not p.is_file():
            continue
        name = p.name
        upper = name.upper()
        if not name.lower().endswith((".png", ".jpg", ".jpeg")):
            continue
        if upper.startswith("VID") and "PACKAGING" not in upper:
            thumbs.append(p)
    # Prefer canonical VID### Name.png without -1/-2/_1/_2 suffixes
    def rank(p: Path) -> tuple:
        stem = p.stem
        suffix_penalty = 1 if re.search(r"[-_](\d+)$", stem) else 0
        # Prefer .png Canva exports
        png_bonus = 0 if p.suffix.lower() == ".png" else 1
        return (suffix_penalty, png_bonus, -p.stat().st_mtime, p.name.lower())

    return sorted(thumbs, key=rank)


def canva_created_date(thumb: Path) -> str | None:
    try:
        im = Image.open(thumb)
        xmp = im.info.get("xmp") or im.info.get("XML:com.adobe.xmp") or b""
        if isinstance(xmp, str):
            xmp = xmp.encode("utf-8", errors="replace")
        text = xmp.decode("utf-8", errors="replace")
        m = re.search(r"<Attrib:Created>(\d{4}-\d{2}-\d{2})</Attrib:Created>", text)
        if m:
            return m.group(1)
    except Exception:
        return None
    return None


def candidate_images(folder: Path) -> list[Path]:
    cands = []
    for p in folder.iterdir():
        if not p.is_file():
            continue
        low = p.name.lower()
        if not low.endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp")):
            continue
        if p.name.upper().startswith("VID"):
            continue
        if "chatgpt" in low or "thumbnail" in low:
            continue
        if low.endswith(".drx"):
            continue
        # Skip other Canva exports / finished thumbs (keep DaVinci Still*.png + camera JPGs)
        if low.endswith(".png") and not low.startswith("still"):
            try:
                im = Image.open(p)
                xmp = im.info.get("xmp") or im.info.get("XML:com.adobe.xmp") or b""
                if isinstance(xmp, str):
                    xmp = xmp.encode("utf-8", errors="replace")
                text = xmp.decode("utf-8", errors="replace") if xmp else ""
                if "Canva" in text or im.size == (1280, 720):
                    continue
            except Exception:
                pass
        cands.append(p)
    return cands


def date_bonus(path: Path, created: str | None) -> float:
    if not created:
        return 0.0
    # Still 2026-07-09 ... or 20260707_...
    name = path.name
    m = re.search(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})", name)
    if not m:
        return 0.0
    file_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    if file_date == created:
        return 0.15
    # within 2 days
    try:
        d1 = datetime.strptime(created, "%Y-%m-%d")
        d2 = datetime.strptime(file_date, "%Y-%m-%d")
        delta = abs((d1 - d2).days)
        if delta <= 2:
            return 0.08
    except ValueError:
        pass
    return 0.0


def still_bonus(path: Path) -> float:
    return 0.05 if path.name.lower().startswith("still") else 0.0


def load_bgr(path: Path, max_side: int = 1600) -> np.ndarray | None:
    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        return None
    h, w = img.shape[:2]
    scale = max_side / max(h, w)
    if scale < 1:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return img


def match_score(thumb_bgr: np.ndarray, cand_bgr: np.ndarray) -> float:
    """Return best normalized correlation of candidate patches against thumbnail."""
    th = thumb_bgr.copy()
    # Ignore top/bottom text bands commonly used in Canva thumbnails
    h, w = th.shape[:2]
    y0, y1 = int(h * 0.12), int(h * 0.88)
    th = th[y0:y1, :]
    th_gray = cv2.cvtColor(th, cv2.COLOR_BGR2GRAY)
    cand_gray = cv2.cvtColor(cand_bgr, cv2.COLOR_BGR2GRAY)

    best = -1.0
    th_h, th_w = th_gray.shape[:2]

    # Try several relative scales: source food often fills most of the thumb
    for scale in (0.95, 0.85, 0.75, 0.65, 0.55, 0.45, 0.35):
        cw = max(32, int(th_w * scale))
        ch = max(32, int(th_h * scale))
        # Keep candidate aspect ratio
        c_h, c_w = cand_gray.shape[:2]
        aspect = c_w / c_h
        if cw / ch > aspect:
            cw = max(32, int(ch * aspect))
        else:
            ch = max(32, int(cw / aspect))
        if ch >= th_h or cw >= th_w:
            continue
        resized = cv2.resize(cand_gray, (cw, ch), interpolation=cv2.INTER_AREA)
        res = cv2.matchTemplate(th_gray, resized, cv2.TM_CCOEFF_NORMED)
        score = float(res.max())
        if score > best:
            best = score

    # Also try matching a center crop of the candidate into the thumb
    c_h, c_w = cand_gray.shape[:2]
    for frac in (0.9, 0.7, 0.5):
        cw, ch = int(c_w * frac), int(c_h * frac)
        left, top = (c_w - cw) // 2, (c_h - ch) // 2
        crop = cand_gray[top : top + ch, left : left + cw]
        for target_w in (int(th_w * 0.85), int(th_w * 0.7), int(th_w * 0.55)):
            target_h = max(32, int(target_w * ch / cw))
            if target_h >= th_h or target_w >= th_w:
                continue
            resized = cv2.resize(crop, (target_w, target_h), interpolation=cv2.INTER_AREA)
            res = cv2.matchTemplate(th_gray, resized, cv2.TM_CCOEFF_NORMED)
            score = float(res.max())
            if score > best:
                best = score

    return best


def choose_source(folder: Path, thumb: Path) -> tuple[Path | None, float, str]:
    created = canva_created_date(thumb)
    cands = candidate_images(folder)
    if not cands:
        return None, -1.0, "no candidates"

    thumb_bgr = load_bgr(thumb, max_side=1280)
    if thumb_bgr is None:
        return None, -1.0, "could not read thumbnail"

    scored = []
    for cand in cands:
        img = load_bgr(cand, max_side=1600)
        if img is None:
            continue
        base = match_score(thumb_bgr, img)
        total = base + date_bonus(cand, created) + still_bonus(cand)
        scored.append((total, base, cand))

    if not scored:
        return None, -1.0, "no readable candidates"

    scored.sort(key=lambda x: x[0], reverse=True)
    best_total, best_base, best_path = scored[0]
    detail = (
        f"created={created or 'n/a'}; "
        f"top={best_path.name} score={best_total:.3f} (match={best_base:.3f}); "
        f"runners="
        + ", ".join(f"{p.name}:{t:.3f}" for t, b, p in scored[1:4])
    )
    return best_path, best_total, detail


def resize_hero(src: Path, dest: Path) -> None:
    im = Image.open(src).convert("RGB")
    im.thumbnail((HERO_MAX, HERO_MAX), Image.Resampling.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "JPEG", quality=JPEG_QUALITY, optimize=True)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    recipes = load_published_recipes()
    folders = numbered_folders()
    lines = []
    ok = 0
    fail = 0

    print(f"Recipes with YouTube: {len(recipes)}")
    print(f"Output: {OUT_DIR}")

    for recipe in recipes:
        folder = find_folder(recipe, folders)
        if folder is None:
            msg = f"FAIL {recipe.hero}: no folder match for {recipe.slug} ({recipe.title})"
            print(msg)
            lines.append(msg)
            fail += 1
            continue

        thumbs = find_thumbnails(folder)
        if not thumbs:
            # Fallback naming like "15 minutes.png"
            alts = [
                p
                for p in folder.glob("*.png")
                if not p.name.lower().startswith("still")
                and "chatgpt" not in p.name.lower()
                and p.stat().st_size > 200_000
            ]
            thumbs = sorted(alts, key=lambda p: -p.stat().st_mtime)

        if not thumbs:
            msg = f"FAIL {recipe.hero}: no VID thumbnail in {folder.name}"
            print(msg)
            lines.append(msg)
            fail += 1
            continue

        thumb = thumbs[0]
        source, score, detail = choose_source(folder, thumb)
        if source is None or score < 0.25:
            msg = (
                f"FAIL {recipe.hero}: weak/no match in {folder.name} "
                f"thumb={thumb.name} {detail}"
            )
            print(msg)
            lines.append(msg)
            fail += 1
            continue

        dest = OUT_DIR / recipe.hero
        resize_hero(source, dest)
        size_kb = dest.stat().st_size // 1024
        msg = (
            f"OK   {recipe.hero}: {folder.name} | thumb={thumb.name} | "
            f"source={source.name} | {size_kb}KB | {detail}"
        )
        print(msg)
        lines.append(msg)
        ok += 1

    summary = f"\nDone. OK={ok} FAIL={fail} -> {OUT_DIR}"
    print(summary)
    lines.append(summary)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report: {REPORT}")


if __name__ == "__main__":
    main()
