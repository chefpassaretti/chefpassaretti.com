"""
One-off / repeatable generator: Web Recipe Pages Markdown -> static HTML.
Does not run automatically; invoke manually when recipes are ready.
"""

from __future__ import annotations

import re
import urllib.request
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD_DIR = Path(r"C:\Users\mep07\chefpassaretti\Web Recipe Pages")
RECIPES_DIR = ROOT / "recipes"
IMAGES_DIR = ROOT / "images" / "recipes"
YT_ID_RE = re.compile(r"youtube\.com/watch\?v=([A-Za-z0-9_-]{6,})")


def normalize_md(text: str) -> str:
    # Some files escaped markdown with backslashes
    text = text.replace("\\*", "*").replace("\\#", "#").replace("\\-", "-")
    text = text.replace("\\.", ".")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def field(text: str, name: str) -> str:
    m = re.search(rf"\*\*{re.escape(name)}:\*\*\s*(.+)", text)
    return m.group(1).strip() if m else ""


def section(text: str, heading: str) -> str:
    m = re.search(
        rf"## {re.escape(heading)}\s*\n(.*?)(?=\n## |\Z)",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    return m.group(1).strip() if m else ""


def bullets(block: str) -> list[str]:
    items = []
    for line in block.splitlines():
        line = line.strip()
        if line.startswith("- "):
            items.append(line[2:].strip())
    return items


def numbered(block: str) -> list[str]:
    items = []
    for line in block.splitlines():
        line = line.strip()
        m = re.match(r"^\d+\.\s+(.*)$", line)
        if m:
            items.append(m.group(1).strip())
    return items


def summary_map(block: str) -> dict[str, str]:
    out = {}
    for item in bullets(block):
        if ":" in item:
            k, v = item.split(":", 1)
            out[k.strip().lower()] = v.strip()
    return out


def parse_recipe(path: Path) -> dict | None:
    raw = normalize_md(path.read_text(encoding="utf-8"))
    title_m = re.match(r"^#\s+(.+)$", raw, re.MULTILINE)
    if not title_m:
        return None
    youtube = field(raw, "YouTube URL")
    yt = YT_ID_RE.search(youtube or "")
    if not yt:
        return None

    slug = field(raw, "Slug") or path.stem
    hero = field(raw, "Hero image") or f"{slug}.jpg"
    meta = field(raw, "Meta description")
    intro = section(raw, "Short introduction")
    summary = summary_map(section(raw, "Recipe summary"))
    ingredients = bullets(section(raw, "Ingredients"))
    instructions = numbered(section(raw, "Instructions"))
    notes = section(raw, "Chef's notes")
    equipment = bullets(section(raw, "Equipment used"))
    related = [
        r
        for r in bullets(section(raw, "Related recipes"))
        if r and r.lower() not in {"none yet", "none", "n/a"}
    ]
    blurb = section(raw, "Index blurb") or intro.split(".")[0] + "."

    return {
        "title": title_m.group(1).strip(),
        "slug": slug,
        "youtube_id": yt.group(1),
        "hero": hero,
        "meta": meta or blurb,
        "intro": intro,
        "summary": summary,
        "ingredients": ingredients,
        "instructions": instructions,
        "notes": notes,
        "equipment": equipment,
        "related": related,
        "blurb": blurb.strip(),
    }


def download_hero(youtube_id: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1000:
        return True
    for name in ("maxresdefault.jpg", "sddefault.jpg", "hqdefault.jpg"):
        url = f"https://img.youtube.com/vi/{youtube_id}/{name}"
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                data = resp.read()
            # YouTube returns a tiny placeholder gif/jpeg for missing maxres
            if len(data) < 5000 and name == "maxresdefault.jpg":
                continue
            dest.write_bytes(data)
            return True
        except Exception:
            continue
    return False


def li_list(items: list[str], ordered: bool = False) -> str:
    tag = "ol" if ordered else "ul"
    body = "\n".join(f"                <li>{escape(i)}</li>" for i in items)
    return f"            <{tag}>\n{body}\n            </{tag}>"


def related_html(slugs: list[str], catalog: dict[str, dict]) -> str:
    links = []
    for slug in slugs:
        if slug in catalog:
            links.append(
                f'                <li><a href="{escape(slug)}.html">{escape(catalog[slug]["title"])}</a></li>'
            )
    if not links:
        return "            <p>More recipes coming soon.</p>"
    return "            <ul class=\"recipe-related\">\n" + "\n".join(links) + "\n            </ul>"


def summary_html(summary: dict[str, str]) -> str:
    order = [
        ("prep time", "Prep Time"),
        ("cook time", "Cook Time"),
        ("total time", "Total Time"),
        ("servings", "Servings"),
    ]
    parts = []
    for key, label in order:
        if key in summary and summary[key]:
            parts.append(
                f"""            <div class="recipe-summary__item">
                <strong>{label}</strong>
                {escape(summary[key])}
            </div>"""
            )
    if not parts:
        return ""
    return '        <div class="recipe-summary">\n' + "\n".join(parts) + "\n        </div>"


def recipe_html(r: dict, catalog: dict[str, dict]) -> str:
    notes = escape(r["notes"]).replace("\n\n", "</p>\n            <p>").replace("\n", " ")
    equipment = (
        li_list(r["equipment"])
        if r["equipment"]
        else "            <p>Equipment notes coming soon.</p>"
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="referrer" content="strict-origin-when-cross-origin">
    <meta name="description" content="{escape(r['meta'])}">
    <title>{escape(r['title'])} | Chef Passaretti</title>
    <link rel="stylesheet" href="../styles.css">
</head>
<body>

<header class="site-header">
    <nav>
        <a class="site-logo" href="../index.html">Chef Passaretti</a>
        <a href="../index.html">Home</a>
        <a href="../recipes.html" aria-current="page">Recipes</a>
        <a href="../kitchen.html">Kitchen</a>
    </nav>
</header>

<article class="recipe-page">
    <a class="recipe-page__back" href="../recipes.html">← All Recipes</a>

    <h1>{escape(r['title'])}</h1>

    <div class="recipe-page__hero">
        <img
            src="../images/recipes/{escape(r['hero'])}"
            alt="{escape(r['title'])}"
            width="1280"
            height="720"
        >
    </div>

    <p class="recipe-page__intro">
        {escape(r['intro'])}
    </p>

{summary_html(r['summary'])}

    <section class="recipe-block" aria-labelledby="video-heading">
        <h2 id="video-heading">Watch the Video</h2>
        <div class="video-container">
            <iframe
                src="https://www.youtube.com/embed/{escape(r['youtube_id'])}"
                title="{escape(r['title'])}"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                referrerpolicy="strict-origin-when-cross-origin"
                allowfullscreen>
            </iframe>
        </div>
    </section>

    <section class="recipe-block" aria-labelledby="ingredients-heading">
        <h2 id="ingredients-heading">Ingredients</h2>
{li_list(r['ingredients'])}
    </section>

    <section class="recipe-block" aria-labelledby="instructions-heading">
        <h2 id="instructions-heading">Instructions</h2>
{li_list(r['instructions'], ordered=True)}
    </section>

    <section class="recipe-block" aria-labelledby="notes-heading">
        <h2 id="notes-heading">Chef’s Notes</h2>
            <p>{notes}</p>
    </section>

    <section class="recipe-block" aria-labelledby="equipment-heading">
        <h2 id="equipment-heading">Equipment Used</h2>
{equipment}
    </section>

    <section class="recipe-block" aria-labelledby="related-heading">
        <h2 id="related-heading">Related Recipes</h2>
{related_html(r['related'], catalog)}
    </section>
</article>

<footer class="site-footer">
    <div class="site-footer-inner">
        <nav class="site-footer-nav" aria-label="Footer">
            <a href="../index.html">Home</a>
            <a href="../recipes.html">Recipes</a>
            <a href="../kitchen.html">Kitchen</a>
        </nav>
        <p>© 2026 Chef Passaretti</p>
    </div>
</footer>

</body>
</html>
"""


def recipes_index_html(recipes: list[dict]) -> str:
    cards = []
    for r in recipes:
        cards.append(
            f"""        <a class="recipe-index-card" href="recipes/{escape(r['slug'])}.html">
            <div class="recipe-index-card__image">
                <img
                    src="images/recipes/{escape(r['hero'])}"
                    alt="{escape(r['title'])}"
                    width="800"
                    height="600"
                >
            </div>
            <h2>{escape(r['title'])}</h2>
            <p>{escape(r['blurb'])}</p>
        </a>"""
        )
    grid = "\n\n".join(cards)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta
        name="description"
        content="Browse recipes featured on the Chef Passaretti YouTube channel."
    >
    <title>Recipes | Chef Passaretti</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>

<header class="site-header">
    <nav>
        <a class="site-logo" href="index.html">Chef Passaretti</a>
        <a href="index.html">Home</a>
        <a href="recipes.html" aria-current="page">Recipes</a>
        <a href="kitchen.html">Kitchen</a>
    </nav>
</header>

<main class="section page-shell">
    <div class="section-inner">
        <p class="section-kicker">Recipe Library</p>
        <h1>Recipes</h1>
        <p class="section-intro">
            Written recipes from the Chef Passaretti YouTube channel—each with
            cooking notes, ingredients, and the full video.
        </p>

        <div class="recipe-index-grid">
{grid}
        </div>
    </div>
</main>

<footer class="site-footer">
    <div class="site-footer-inner">
        <nav class="site-footer-nav" aria-label="Footer">
            <a href="index.html">Home</a>
            <a href="recipes.html">Recipes</a>
            <a href="kitchen.html">Kitchen</a>
        </nav>
        <p>© 2026 Chef Passaretti</p>
    </div>
</footer>

</body>
</html>
"""


def main() -> None:
    RECIPES_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    recipes: list[dict] = []
    skipped: list[str] = []

    for path in sorted(MD_DIR.glob("*.md")):
        parsed = parse_recipe(path)
        if not parsed:
            skipped.append(path.name)
            continue
        recipes.append(parsed)

    catalog = {r["slug"]: r for r in recipes}
    # Also allow filename-stem lookups for related links
    for r in recipes:
        catalog.setdefault(r["slug"], r)

    print(f"Publishing {len(recipes)} recipes; skipping {len(skipped)}: {skipped}")

    for r in recipes:
        hero_path = IMAGES_DIR / r["hero"]
        ok = download_hero(r["youtube_id"], hero_path)
        print(f"  [{'ok' if ok else 'NO IMAGE'}] {r['slug']}")
        (RECIPES_DIR / f"{r['slug']}.html").write_text(
            recipe_html(r, catalog), encoding="utf-8"
        )

    recipes_sorted = sorted(recipes, key=lambda r: r["title"].lower())
    (ROOT / "recipes.html").write_text(
        recipes_index_html(recipes_sorted), encoding="utf-8"
    )

    print(f"Wrote recipes.html and {len(recipes)} recipe pages.")


if __name__ == "__main__":
    main()
