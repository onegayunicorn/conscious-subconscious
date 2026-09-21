# media/ — brand and visual assets

Index of the assets in this folder, and what each is for.

**Boundary:** every asset here is part of an educational and artistic modelling project. This
is not a medical device, not clinical evidence and not medical advice, and no asset may be
used to suggest that attention, focus or visualisation heals tissue. Any reuse must keep the
disclaimer line; the social card and key visual carry it by design so that partial reuse
still carries the caveat.

All SVG files are hand-authored XML: no `<image>`, no external fonts, no scripts, no embedded
raster. They render standalone and offline.

## Contents

| File | Size (viewBox) | What it is | Where to use it |
| --- | --- | --- | --- |
| `brand.md` | — | Name usage, tone of voice, the six-colour palette with rationale, the Inter + IBM Plex Mono pairing, and usage rules | Read before producing any new asset or fork of this project |
| `logo.svg` | 512×512 | The mark: a smooth homeostatic curve (mint) crossed by a focused signal pulse (amber) with a node at the crossing | Repository, docs headers, favicon derivation, presentations |
| `mind-tissue-diagram.svg` | 1200×700 | Reference architecture: tissue at centre, subconscious loop left, conscious loop right, mediator field beneath, hardware/protocol boundary at the bottom | README architecture section, talks, technical posts |
| `key-visual.svg` | 1600×900 | Hero graphic in the logo's visual language, with name, description, version line and disclaimer | Repository header, project page, long-form posts |
| `social-card.svg` | 1200×630 | Social preview card: project name, one-line positioning, and the disclaimer in small type | Link previews (GitHub social preview, Mastodon/Bluesky cards, blog embeds) |

## Usage notes

- **Palette:** `#0B1C2C` base, `#123A5A` structure, `#2E7D9A` process, `#7FD1C1` subconscious
  signal, `#F2A65A` conscious accent, `#E9EEF2` surface/text. See `brand.md` for the rationale
  and the ~5% cap on the amber accent.
- **Type:** Inter for display and body, IBM Plex Mono for anything that names a variable or a
  protocol field. Both are SIL Open Font License. The SVGs reference these families by name
  with generic fallbacks; no font files are bundled and no font is fetched.
- **Amber means the conscious process.** If the accent appears somewhere other than the signal
  pulse, the attention budget or the expectancy module, the visual language has drifted.
- **Colour-swapping:** only monochrome or inverted variants are acceptable. Do not gradient,
  recolour or add effects.
- **Attribution:** "conscious-subconscious (MIT), github.com/onegayunicorn/conscious-subconscious".

## Not in this folder, deliberately

- No photography, illustration or iconography of people, bodies, skin, wounds, hands,
  clinicians or clinical settings.
- No before/after imagery, no progress bars implying recovery, no reds or pinks.
- No store badges, pricing graphics, tier tables or "buy" affordances: payments are not
  implemented in this project.
- No generated raster variants. If a PNG export is needed, render these SVGs; do not create a
  parallel source of truth.
