from pathlib import Path

root = Path(__file__).resolve().parents[1] / "recipes"
updated = 0

for path in sorted(root.glob("*.html")):
    text = path.read_text(encoding="utf-8")
    orig = text

    if "youtube.com/embed" not in text:
        continue

    if 'referrerpolicy=' not in text:
        text = text.replace(
            "allowfullscreen>",
            'referrerpolicy="strict-origin-when-cross-origin"\n                allowfullscreen>',
        )

    if 'name="referrer"' not in text:
        text = text.replace(
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            '    <meta name="referrer" content="strict-origin-when-cross-origin">',
        )

    if text != orig:
        path.write_text(text, encoding="utf-8")
        updated += 1
        print("updated", path.name)

print("total", updated)
