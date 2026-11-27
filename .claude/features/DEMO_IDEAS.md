# Demo Ideas

Wanted demos and examples: what each is, never its status or order (those are in `.claude/planning/QUEUE.md`). An idea
leaves this file once built. `.claude/format/EXAMPLES.md` says how examples are made; rewriting an existing example needs the
user's yes first.

## Synth Demos

Each made with its engine; no artist named in a title or name, a homage's inspiration kept in its notes.

- **Engines and effects under each synth demo**: on the synth demos' page, under each demo, a checkbox list of every
  engine the demo uses and, apart from it, of every effect it uses, if any; kept current as synth demos are added or
  changed.
- **log_garden.yml** on ComplexOsc, with the low-pass gates: audio-rate FM and the complex oscillator put through its paces,
  long tones (half notes and longer) in the intro, not only plucks; its oscillator mapped to several CCs that the demo tweaks.
- **switched_on_beep.yml** on Asheville: a Bach mashup in the style of the early synthesizer Bach albums, no drums
  (`MASHUPS.md` first).
- **llama_special.yml** on Monorail with Syrup pads: a hazy tune after 1980s public television documentaries, Oh8 drums.
- **403_forbidden.yml** on MozaicHypersaw: trance, a MozaicClassic arpeggio, Oh9 drums.
- **basement_combo.yml** on Classic Keys: an organ combo jazz jam, Tonewheel with the Rotary, Combo Organ, Piano, Stringy,
  SynTom and Struck.
- **packet_loss.yml** on Noise and Glitch: braindance, weird, abstract and mechanical, no lullaby; Glitch Drum and Chirpy.
- **blue_people.yml** on Pluck, Strings, Pipe and Struck: a percussive tube-and-pipe band piece in the Legend reverb.
- **glass_tide.yml** on Wavetable: digital ambient.
- **night_shift.yml** on FM with SynTom: a 1980s action-film synth score.
- The chip engines DustCart, BitArcade and Bytecrunch, and Pocket Drum, joining cartridge_quest and side_pocket.
- A demo for each new kind of modulator as it is built: LFO+ (a vibrato fading into held notes, a tremolo locked to
  the tempo through a ramp, a Smooth random drift), Snail, Chaos, Tide, Turing, Bounce and Swarm (SYNTH_IDEAS.md,
  "Demos of the new modulators").
- A set whose tracks play through FluidSynth and the built-in instruments together, its WAV export tested.
- **The electronic demos on the built-in synths**: once more synth and drum engines are built, edm_density.yml (Density)
  plays through the built-in synths and drum engines in place of its General MIDI sounds, its arrangement, patterns and
  clips kept and only its instruments changed; then the other electronic demos in `examples/by_genre/electronic/` are
  looked at again the same way, each change of a demo confirmed with the user first.

## Other Demos

- Learning examples of making a band with the Band Generators, numbered as the learning examples are, made by hand: a basic
  one, a power trio of guitar, bass and drums in a blues-rock style, and an advanced one with a larger band; no band named.
- A couple of demo songs whose making is explained in the documents, `no_stairway` one of them (`WIZARD_DESIGNS.md`).
- The concept examples reworked onto the built-in generators, every export byte for byte the same, with the same scenes, tracks
  and clips.
- The homages rewritten, all 49: true to the style of each work, its chords and its sections' order kept, no melody of it
  referenced; Phrasing on the leads; a lift in last choruses; the verse ceiling; Voice leading on keyboard and pad chords; new
  hooks where weak; a pilot first, Phrasing's mechanics settled first. With it, a discussion of whether the new phrasing and
  melody engines would make them better, whether they use the original songs' progressions correctly, and which are worth
  making again.
- New homages, then new mashups.

## More Demo Ideas

In the order of their priority, the highest first.

- **Demos by genre**: original music in each style asked, never a copy of a song, about three minutes unless noted:
  Electronic, filter_sweep, idm_chaos1 to idm_chaos3 and drift_berlin; Classical, drift_canon, drift_pastoral (a pastoral
  for strings, winds and horn in F major, Drift shaping dynamics and ornaments and borrowing Lydian), chamber_music,
  brass_doorknob, adagio (with Drift) and harmonizer; Children's, row_your_boat (Row, Row, Row Your Boat as a round, showing
  how a round is edited); New age, newish_age and gorge; Rock, van_llama and whipping_llama (Strum on their rhythm guitars);
  Musical theatre, retro_musical; Jazz, piano_trio (a medium swing, ii–V–I changes from Progression, a walking bass,
  brushes), bigband, llama_supreme and weather (ten minutes); Easy listening, the_mall; Metal, black_midi. Afterwards: look
  at a generative sequencer and a leading tracker online for ideas, and suggest clearer names for demos whose names do not
  say their style.
- **The demos as a course**: the featured songs first
  (edm_density, minimal_techno, mainstreet_hoedown and new ones), then a learning path from hello_world and the Entertainer,
  which uses no features, through each feature simplest first, the order kept in one data file that docs/DEMOS.md's tables
  and the descriptions come from; each demo's entry in docs/DEMOS.md and its set's Notes get generated "Read about it" links
  to the chapter and heading of every feature it uses (from py_legacy/internal_tools/demo_features.py and a map of features to
  chapters), a test failing when a link is missing or points nowhere. The examples are in examples/learning, examples/other
  and examples/by_genre, where the new demos go by purpose.
- **Features the demos underuse**: `py_legacy/internal_tools/demo_features.py` (`py_legacy/internal_tools/demo_features.sh`) prints which
  features each set in `examples/` uses, and which none or only one does, so a feature without a demo is a candidate for a
  new demo or for a scene in an existing one. Run once, no set used: conditions, a pattern's own time signature, a
  scene's chains, a track's chains, clip names, a clip's scale, a song seed, or several songs. One set alone used each of:
  slides, register sets, register binding, a pattern's direction, a clip's shapes, register resets, a scene's groove, muted
  tracks, a track's groove, drifts, inversions and glides, with a few more the tool lists. The existing demos stay as they
  are; the gaps are for the new demo below. ### A demo of several songs in one set A new demo set that covers what no other
  demo does: it holds several songs, uses clip names, gives a song a seed, plays in time signatures other than 4/4, and
  gives at least one pattern a time signature of its own. Its purpose is mostly coverage, but it has to be musically
  interesting rather than chaff: the songs are in one genre, still to choose, and the point of putting them in one set is
  that they share patterns intelligently, the way a set of songs for one concert would, with a pattern playing in more than
  one song, perhaps at another tempo, scale or time signature, and with each song adding patterns of its own. It should use
  plenty of the other features too, chosen because the music wants them, like the other demos do. Nothing in `examples/`
  plays in 3/4 or 6/8 yet, so at least one song should. It gets an entry in `docs/DEMOS.md`, a description that says what to
  keep when changing it, and a place in `HAND_WRITTEN` in `tests/app/test_demos.py` unless it's written through
  `tests/data/demo_sources/make_demos.py`. The genre and the tunes are to be decided with the user first.
- **Code Examples**: The user's idea, to be discussed once the genre work has rested for a while. A top-level folder,
  `code_examples/`, of scripts the user calls "code example" tasks, which Claude may generate when asked. Together they show
  the "API" for llamatron, marked unstable, since the classes underneath are internal and change freely. Every code example
  builds its set from llamatron's own objects, never from YAML, unless the user says otherwise for one. The first three: - a
  script that imports a MIDI file named on its command line and saves it as a YAML set; - a basic song exactly like the
  hello world demo; - a more complex song with several clips, generators and chains and a few other settings changed,
  sounding more or less like one of the demos. It means: a folder and a README saying the API is unstable; tests that run
  each example and hold the second to the hello world demo's music; the GPL header and the code rules on each script; a
  decision on whether the website gets a page for them.
- **Demo videos, recorded by Claude in batches**: The user's idea: Claude says which videos would help the documents, and
  better, asks the user and then records them itself in a batch, for the user to upload to YouTube; then the user asks
  Claude to scan the channel, and Claude asks where each video should go before linking it. The batch includes every demo
  song recorded with a visualizer mode chosen at random, one video each. What it would take: -
  `py_legacy/internal_tools/record_demo.py` already records a set with `--visualizer` or `--clips`, through FluidSynth
  (`--fluidsynth`) or a DAW. A batch is a script that walks the examples, picks a mode at random for each (saying which, so
  a take can be repeated, and leaving out `cycle` unless asked), and records them one after another into
  `output/recordings/`, with a list of each file, its set and its mode. - The recordings need the screen and the audio set
  up as `docs/RECORDING.md` says, so the batch stops at the first failure rather than recording silence, and asks before
  starting, since it takes each song's length in real time (about three minutes each, so over an hour for every demo). -
  Questions to put to the user first: FluidSynth or a DAW for the sound; the clips, a visualizer or both for each song;
  which songs; the window size. - Scanning the channel reads its public video list from YouTube, which no test or script
  does (tests never fetch anything); Claude reads it in the conversation, matches titles to sets, and proposes each link as
  new text for the user to confirm, by the rules for the user's documents. - Other videos worth recording: each chapter's
  page being used (Patterns, the piano roll, Arrange playing live with edits heard), the MIDI import, and an export opened
  in Live. The videos already on the channel, and where they are linked: - `https://www.youtube.com/watch?v=yt9NffJ1HF4`:
  the visualizers playing a song. `README.md` and `docs/VISUALIZERS.md`. - `https://www.youtube.com/watch?v=JAswLZ8CGzk`:
  navigating around the tracker, an early build, so the program has changed since and will go on changing. `docs/GUIDE.md`.
  - `https://www.youtube.com/watch?v=zcIWxtHWwtQ`: The Entertainer played in real time, with no live editing and no cursor
  moving. `docs/DEMOS.md`. The user will say when more demos are uploaded, and which demos they show.
