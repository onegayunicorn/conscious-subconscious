# Channels

Where this audience actually lives, what to post, and how to sound. Ordered by expected
value, not by reach. Tone rules are as important as the venue list — this project dies the
moment it sounds like a wellness pitch.

**Boundary:** every post carries the short disclaimer from `messaging.md` §7. If a channel's
culture cannot tolerate a disclaimer, the channel is wrong for this project, regardless of
its size.

## Tone guidance (applies to all channels)

- **State the assumption in the first two sentences.** It is the most interesting thing about
  the project and it pre-empts the pseudoscience accusation.
- **Be boring about the biology.** Technical, dry, precise. Enthusiasm belongs to the
  engineering and the pedagogy, not to the tissue.
- **Link the grading table before the diagram.** Lead sceptics to the rubric; lead builders to
  the protocol envelope.
- **Never use the words "heal", "healing" or "heals" as a verb about a person.** Refer to "a
  modelled tissue variable" or "`damage_level`".
- **Answer hostility with the grade table, not with adjectives.** "Here is the grade for that
  claim, and here is why it is D" ends arguments that marketing cannot.
- **No engagement bait, no threads-as-marketing, no emoji, no exclamation marks.**
- **Disclose the AI-generated provenance early.** It is a limitation, and disclosing it is
  better than being caught not disclosing it.

## Channels

### 1. GitHub (primary)

- **Where:** `onegayunicorn/conscious-subconscious` — README, topics, releases, Discussions
  (if enabled).
- **What:** the canonical artefact. README carries the one-liner, one diagram, the
  boundary block, the grade table summary, and a copy-paste reproducible run. Topics:
  `simulation`, `reproducible-research`, `cognitive-science`, `biofeedback`,
  `open-source`, `python`, `fastapi`, `typescript`.
- **Tone:** documentation. Plain, complete, no personality beyond clarity.
- **Signal to watch:** issues and forks from accounts with real histories; "how do I change
  X" questions are the best signal there is.

### 2. Hacker News

- **Where:** `Show HN`, once. No repeat submissions.
- **What:** the engineering framing — "a reproducible simulation sandbox with a Python core,
  FastAPI service, JSON-Schema envelope and React console, where the domain premise is an
  assumption the repo grades as unsupported". Link the repository, not a blog post.
- **Tone:** technical, self-critical, no adjectives. HN rewards people who pre-empt their own
  weak points; the grade table is the strongest HN asset the project has.
- **Expected reaction:** the top comment will either be "the numbers are made up" (which the
  repo already says) or "why does this need a Kubernetes manifest" (a fair question — answer
  it factually). Prepare both answers in advance.
- **Do not:** argue about medicine in the thread. Point to `research/experimental-design.md`
  and stop.

### 3. Reddit

- **r/simulation, r/agentbasedmodeling, r/cellular_automata (read rules first):** post the
  *model* angle — two coupled control loops, a mediator field, seeded reproducibility.
  Ask for modelling criticism. Do not post the biology framing here; it is off-topic and will
  read as spam.
- **r/cognitivescience:** post the attention/expectancy framing and ask for literature the
  project may have missed. This is the audience most likely to correct the review.
- **r/ExperiencedDevs / r/Python / r/typescript:** post the architecture, only if there is a
  genuine engineering lesson to share (the protocol envelope is the candidate).
- **Not r/woundcare, r/nursing, r/medicine or any clinical subreddit.** The project has
  nothing to offer them and posting there would be irresponsible.
- **Tone:** participation-first. Comment usefully in the subreddit for a while before
  linking anything. Self-promotion rules are enforced unevenly; assume they are strict.

### 4. Mastodon / Bluesky

- **Where:** the scientific-computing and open-science parts of the fediverse; the
  simulation and HCI clusters on Bluesky.
- **What:** short posts about a single idea — one post on the rubric, one on why the boost
  distribution is not a model of attention, one on the protocol envelope. One idea per post.
- **Tone:** conversational, technical, caveat included in the post body rather than a reply.
- **Why it matters:** these are the same people as the stage-1 soft-launch list. This is where
  the first ten critical readers are found.

### 5. University course lists and teaching channels

- **Where:** computational-cognition and HCI course reading lists, methods modules on
  simulation, science-communication modules, open educational resource collections.
- **What:** offer the project as a *teaching case* on assumption-labelling: it is small, it is
  runnable, and it contains a graded example of a bad claim. Write to the module convenor
  directly with a two-paragraph email; do not spam departments.
- **Tone:** collegial and specific — name the module outcome it supports.
- **Signal:** a course page linking the repo. This is one of the few genuinely durable
  outcomes available to a project like this.

### 6. Biofeedback / open-hardware communities

- **Where:** open-source HRV and biofeedback forums, LSL (Lab Streaming Layer) community
  channels, open-hardware mailing lists.
- **What:** the adapter boundary — how a heart-rate stream becomes a sandbox input, and why
  the project refuses to treat that input as evidence.
- **Tone:** engineering. These communities already dislike hype; the refusal to overclaim is
  the reason they will care.
- **Do not:** post in consumer wellness forums. There is no version of that post that does not
  read as a health claim.

### 7. Not channels (deliberate exclusions)

| Channel | Why excluded |
| --- | --- |
| Paid search/social ads | No budget, and the message needs a sceptical reader, not an impression. |
| Wellness influencers | Requires the health claim the project forbids. |
| Clinical or patient communities | Not a medical device; nothing here is for patients. |
| Product Hunt and app-store-style listings | Frames the project as a consumer product with a benefit, which it is neither. |
| Repost-only aggregators | Context-stripping risk; the social card carries the disclaimer precisely for this reason. |

## Content-to-channel map

| Asset | Primary channel |
| --- | --- |
| `media/mind-tissue-diagram.svg` | GitHub README, architecture docs, HN comment |
| `media/key-visual.svg` | Repository header, long-form posts |
| `media/social-card.svg` | Link previews everywhere |
| `media/logo.svg` | Repository, docs, favicon derivation |
| `research/evidence-grading.md` | Reddit, HN, educator outreach |
| `research/experimental-design.md` | Researchers, journalists asking "what would it take?" |
| `media/brand.md` | Forks, installations, anyone re-presenting the project |
