# Brand and visual identity

Boundary: the brand must never make a health claim. The visual identity exists to make the
project look like infrastructure — clinical, calm, engineered — so that the honest framing
reads as competence rather than apology.

## Name usage

- **Written name:** `conscious-subconscious` — lowercase, hyphenated, one token.
- **In prose, first mention:** *conscious-subconscious* (italic) or "the conscious-subconscious
  sandbox".
- **In code:** `conscious_subconscious` (Python package), `conscious-subconscious` (repo,
  Docker image, npm-style identifiers).
- **Never:** "Conscious Subconscious", "CS", "the CS project", "MindHeal", or any stylised
  capitalisation. Never pair the name with a tagline that implies treatment.
- **Never** add a registered/trademark symbol. This is an MIT-licensed open-source project,
  not a brand to be protected.

## Tone of voice

| Principle | In practice |
| --- | --- |
| Explicit over impressive | The first sentence names the assumption and its status. |
| Clinical calm | Short declaratives. No urgency, no superlatives, no exclamation marks. |
| Self-critical before others are | State the grade of your own claim before someone asks. |
| Precise nouns | "`damage_level`", "attention budget", "mediator field" — not "energy", "vibes", "flow". |
| No wellness vocabulary | No "journey", "align", "unlock", "natural healing", "wellness". |
| Honest about mechanism status | "This models an unvalidated assumption" is a feature of the voice, not a disclaimer bolted on. |

Voice samples:

- Good: *"The model assumes attention multiplies a repair rate. That assumption is graded D.
  Here is what the model does with it anyway."*
- Bad: *"Discover how your mind can support the body's natural healing."*

## Palette

Six colours. Deliberately a calm, clinical, deep base with exactly one warm accent, so that
the single warm hue always means "the conscious process / the focused signal" and never
becomes decorative.

| Role | Name | Hex | Rationale |
| --- | --- | --- | --- |
| Base / background | Deep Tissue Navy | `#0B1C2C` | Near-black blue; reads as instrument panel rather than app. High contrast for light text; neutral enough to sit beside academic white pages. |
| Structure | Mediator Blue | `#123A5A` | Panels, cards, diagram containers. Clearly related to the base but separable, so diagrams can be layered without borders everywhere. |
| Process (subconscious) | Perfusion Teal | `#2E7D9A` | Mid-tone for flows and fields. Reads as fluid and physiological without being red or pink, i.e. without suggesting blood or injury. |
| Signal (subconscious) | Homeostatic Mint | `#7FD1C1` | The homeostatic curve. Light, calm, non-alarming; the "steady, automatic, unremarkable" half of the model. |
| Accent (conscious) | Attentional Amber | `#F2A65A` | The single warm accent. Used *only* for the conscious pulse, the attention budget, and the expectancy module. Warm without being alarming (deliberately not red), and semantically distinct from the rest of the palette. |
| Surface / text | Clinical Paper | `#E9EEF2` | Text on dark surfaces, and light backgrounds where a light surface is required. Slightly cool, so it does not fight the navy. |

Usage split: roughly **80% deep base and structure, 15% teal and mint, 5% amber**. If amber
covers more than about a tenth of a composition, the visual language has broken.
Amber must never be the largest area in a layout; it is the interrupt, not the surface.

Contrast notes: `#E9EEF2` on `#0B1C2C` is high contrast and safe for body text.
`#F2A65A` on `#0B1C2C` is high contrast and safe for labels. Do not place mint or amber on
Clinical Paper for text — use Deep Tissue Navy or Mediator Blue for text on light surfaces.

## Type pairing

Two widely available open-source families (both SIL Open Font License):

| Role | Family | Use |
| --- | --- | --- |
| Display and body | **Inter** | Titles, headings, body text, UI labels. Wide language coverage, designed for screens, neutral. |
| Data and code | **IBM Plex Mono** | Variable names (`damage_level`), parameter values, code, protocol fields, axis labels. |

Rules:

- Body text: Inter, regular/medium. Headings: Inter semibold. Do not use Inter Black; the voice
  is calm.
- Any identifier that appears in the code must be set in IBM Plex Mono, in every medium — this
  is a deliberate visual cue that the text is talking about a *model* rather than a patient.
- No third family. No script faces, no novelty faces, no all-caps display type.
- Letter-spacing: default. Do not tight-track headings to make them look "designed".

## Usage rules

1. **The disclaimer travels with the mark.** Any composition using the logo, key visual or
   social card must retain the short disclaimer line: *Educational and artistic simulation
   only. Not a medical device, not clinical evidence, not medical advice. No claim that
   attention heals tissue.*
2. **Do not recolor the mark** beyond the palette. Inverted (light-on-dark) and monochrome
   (single-colour `#0B1C2C` or `#E9EEF2`) versions are acceptable; rainbow or gradient
   recolouring is not.
3. **Clear space.** Minimum clear space around the logo equals the height of the logo's centre
   node (about 6% of the mark's width). Do not crop the rounded background away.
4. **Minimum size.** Logo: 24 px on screen / 8 mm in print. Social card: do not scale below
   600 px wide.
5. **No imagery of people, wounds, skin, bodies, hands, or medical settings** in any asset.
   The only subjects are abstract geometry and text.
6. **No before/after framing, no progress bars that imply recovery, no red or pink anywhere.**
7. **No effects.** No drop shadows, no glows, no bevels, no 3D. The SVGs use flat fills and
   strokes only.
8. **No embedded images, external fonts, or scripts in the SVGs.** The marks must render
   standalone, offline, in any viewer.
9. **Attribution.** When reused, credit "conscious-subconscious (MIT), github.com/onegayunicorn/conscious-subconscious".

## Asset summary

| Asset | Size | Purpose |
| --- | --- | --- |
| `logo.svg` | 512×512 | Mark: smooth homeostatic curve crossed by a focused signal pulse |
| `mind-tissue-diagram.svg` | 1200×700 | Architecture: tissue, two loops, mediator field, hardware/protocol boundary |
| `key-visual.svg` | 1600×900 | Hero graphic for the repository or site |
| `social-card.svg` | 1200×630 | Link preview with name, positioning line and disclaimer |
