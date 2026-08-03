# Chef Passaretti — Start Here

Project handoff for continuing work on chefpassaretti.com.

---

## Read First

Authoritative project documents (read before making changes):

- `docs/WEBSITE-SPEC.md`
- `docs/DESIGN-SYSTEM.md`
- `docs/CONTENT-MODEL.md`
- `docs/DEVELOPMENT-WORKFLOW.md`
- `.cursor/rules/website.mdc`

The design system currently has the most complete guidance. `WEBSITE-SPEC.md`, `CONTENT-MODEL.md`, and `DEVELOPMENT-WORKFLOW.md` are still scaffolds and should be followed as they are filled in.

---

## Current Status

- The repository is connected to GitHub Pages.
- The homepage redesign is complete and live.
- The homepage is now the visual baseline for future pages.
- The project remains a static HTML/CSS website.

Current site pages:

- `index.html` — redesigned food-first homepage
- `recipes.html` — recipe index
- `kitchen.html` — kitchen / equipment page
- `recipes/fresh-tomato-pasta.html` — first individual recipe page (needs template refactor)
- `styles.css` — shared stylesheet (homepage design language established)

Navigation: Home · Recipes · Kitchen

---

## Current Priority

Design and build the reusable individual recipe page template.

The homepage is done. Do not redesign it. Align future recipe pages with the homepage’s typography, spacing, photography emphasis, and calm editorial tone.

---

## Next Implementation Target

Refactor `recipes/fresh-tomato-pasta.html` into the first instance of the standard recipe page template.

Use this page to establish structure, styles, and patterns that every future recipe page will reuse. Preserve existing verified content; do not invent missing measurements, servings, equipment, or notes.

---

## Required Recipe Page Structure

Every individual recipe page should follow this order:

1. Recipe title
2. Hero image
3. Short introduction
4. Recipe summary
5. Embedded YouTube video
6. Ingredients
7. Instructions
8. Chef’s notes
9. Equipment used
10. Related recipes

---

## Constraints

- Preserve the existing static HTML/CSS architecture.
- Do not introduce React, Next.js, Tailwind, a CMS, or a build system.
- Reuse the homepage design language.
- Use semantic HTML and maintainable CSS.
- Do not redesign the homepage.
- Do not invent recipe facts, measurements, products, affiliate links, or personal details.

---

## Working Method

1. Read the project documents before making changes.
2. Analyze the current implementation.
3. Present a concise implementation plan before editing files.
4. Wait for approval.
5. Make one logical change at a time.
6. Keep commits focused.

---

## Resume Prompt

Read `.cursor/START-HERE.md` and continue with the current priority.
