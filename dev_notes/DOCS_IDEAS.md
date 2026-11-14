# Ideas for the documentation

The user's ideas for the documentation, kept apart from the ideas for the program in
`dev_notes/IDEAS.md` (the user's rule), under the same rules: Claude keeps the file and may reword it,
an idea is removed as soon as it's done and trimmed as it's partly done, ideas are added only when the
user asks, and nothing here is started unprompted. "The documentation" is `README.md`, `GUIDE.md`,
`INSTALL.md` and the chapters in `docs/`, which are the user's own writing, the website built from them
(`internal_tools/build_docs.sh`, into `web_docs/`), and the videos on the user's YouTube channel
that the documents link.

## Demo videos, recorded by Claude in batches

The user's idea: Claude says which videos would help the documents, and better, asks the user and then
records them itself in a batch, for the user to upload to YouTube; then the user asks Claude to scan the
channel, and Claude asks where each video should go before linking it. The batch includes every demo
song recorded with a visualizer mode chosen at random, one video each.

What it would take:
- `internal_tools/record_demo.py` already records a set with `--visualizer` or `--clips`, through
  FluidSynth (`--fluidsynth`) or a DAW. A batch is a script that walks the examples, picks a mode at
  random for each (saying which, so a take can be repeated, and leaving out `cycle` unless asked), and
  records them one after another into `recordings/`, with a list of each file, its set and its mode.
- The recordings need the screen and the audio set up as `docs/RECORDING.md` says, so the batch
  stops at the first failure rather than recording silence, and asks before starting, since it takes
  each song's length in real time (about three minutes each, so over an hour for every demo).
- Questions to put to the user first: FluidSynth or a DAW for the sound; the clips, a visualizer or
  both for each song; which songs; the window size.
- Scanning the channel reads its public video list from YouTube, which no test or script does (tests
  never fetch anything); Claude reads it in the conversation, matches titles to sets, and proposes each
  link as new text for the user to confirm, by the rules for the user's documents.
- Other videos worth recording: each chapter's page being used (Patterns, the piano roll, Arrange
  playing live with edits heard), the MIDI import, an export opened in Live, and the video tutorial
  (`internal_tools/tutorial.sh`).

The videos already on the channel, and where they are linked:
- `https://www.youtube.com/watch?v=yt9NffJ1HF4`: the visualizers playing a song. `README.md` and
  `docs/VISUALIZERS.md`.
- `https://www.youtube.com/watch?v=JAswLZ8CGzk`: navigating around the tracker, an early build, so the
  program has changed since and will go on changing. `GUIDE.md`.
- `https://www.youtube.com/watch?v=zcIWxtHWwtQ`: The Entertainer played in real time, with no live
  editing and no cursor moving. `docs/DEMOS.md`.

The user will say when more demos are uploaded, and which demos they show.

## The website, what's left

The site builds from `GUIDE.md` and `docs/` with VitePress and is published from the committed
`web_docs/` by `internal_tools/publish_docs.sh`, as the `gh-pages` branch. Still to do:
- A landing page with a hero section and feature cards, in place of the guide's opening as the front
  page, which would need new text the user writes or confirms.
- "Edit this page on GitHub" links, VitePress's `editLink`, pointing at each Markdown source.
- A logo and a favicon.
- Nicer addresses: the pages are named by their files, like `/llamatron/PATTERNS`; lower case would
  need the staging to rename the pages and rewrite the links.
- Links from the documents to files in the repository, like `examples/by_genre/electronic/edm_density.yml`, are dead on
  the site and ignored (`ignoreDeadLinks`); the staging could point them at the files on GitHub.
- A check that `web_docs/` was rebuilt after a change to the documents: a test can't run VitePress, but
  the staging could write a hash of its sources into the site for a test to compare.
- The screenshots are light SVGs, which look harsh in the site's dark mode.
- `web_docs/` is about 6.4 MB of built files in git, since the user chose to commit the build rather
  than build it on GitHub; building in the workflow instead would drop them.
- Mermaid makes VitePress warn of a large bundle; loading it only on the pages with diagrams would help.
- A look through the site in a browser for anything that renders oddly.

## Guides on subjects that cross chapters

Chapters on chaos (registers, binding, conditions, probability, generators, Drift, saying chaos suits
tame songs too), on harmony (the Harmonizer, the Hocket, Grab, chords, progressions, voice leading) and
on density (Density, Swell and Articulate), each in `docs/` and in `GUIDE.md`'s table of guides, linking
the page chapters rather than repeating them, since each thing is described in one chapter only; and
a chapter on the render pipeline, linked from `docs/ARCHITECTURE.md`, with every stage and its order of
precedence. `docs/CONCEPTS.md` already covers part of the first three as recipes.

## Two tutorials from screenshots, for people starting from scratch

A very easy walk-through for someone who has never opened llamatron, built around screenshots of the
real tracker: starting a set, writing a simple song of a couple of patterns, arranging them in a scene
or two, saving, and exporting it as a Live set and as MIDI stems. Then a second, the advanced steps on
the same song: grooves, chains and generators, registers, grabs, morphs and the rest, one at a time.
Both are chapters in `docs/` linked from `GUIDE.md`, the user will edit them, and Claude takes the
first shot. `docs/CONCEPTS.md` is the order to use the pages in, without screenshots, and the
tutorials would link to it rather than repeat it.

How they're written: by what's selected and what's seen, never by counted presses. "Select Patterns
from the main menu and press Enter", "on the Song page, select Tempo and type 124", not "go down three
steps", because counts break the moment a row is added. Keystrokes are named where they help, in the
words the legend uses, and every one of them has to be kept true as keys change: a check like
`test/test_doc_paths.py`'s, reading the key names the tutorials quote against the pages' `keys()`, would
keep them honest, and `internal_tools/make_screenshots.py` already regenerates the screenshots from the
real tracker, so the tutorials' shots join its list and are retaken the same way. The song the
tutorials build should be a set in `examples/`, so that each step's screenshot comes from a real file
and the finished song can be loaded to compare.

## A tips and tricks document, and a FAQ

A tips and tricks document for ways of working that need no new feature, and a FAQ beside it. The
first tip to include is pattern categories by naming: a set shares its patterns between every song, so
the list grows, and naming patterns with a prefix like `leads foo` and `bass foo` groups them, since the
Patterns page sorts by name with `S` (Sort). The earlier idea of a `category` field with a completing
picker is folded into this; a filter on the Patterns page can come later if naming isn't enough.

## Sheet music for the examples, to be discussed

The user wants to talk about open-source tools that could make sheet music of the examples for the documentation website,
and wants it only if the result won't look terrible, since many examples have a lot of tracks. Nothing is to be built
before that talk. Points to bring to it:
- Candidate tools: LilyPond (engraving from its own text format, the best-looking output, and `examples/midi/` already
  keeps the Entertainer's LilyPond source), MuseScore's command line (MusicXML or MIDI in, PDF or SVG out), and
  Verovio (MusicXML or MEI in, SVG out, small enough to run in the build), with music21 or the MIDI export as the way in.
- Ways to keep a score readable: one or two chosen tracks only, such as the lead and the bass, named by each set; a
  lead sheet (the melody with chord symbols from the Progression chains) instead of every part; the first scene alone;
  drums left out or on one line.
- What the export gives: llamatron already writes MIDI per track (stems) and General MIDI, but notation needs more
  than MIDI holds, such as the key, beams and ties at bar lines, so a tool that quantizes and spells notes well matters.
- Where it would go: an image under each demo's summary on its genre page, made by the docs build, never by hand.

