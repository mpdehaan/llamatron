# Ideas

The user's ideas for later, recorded by Claude, with what each one would mean for the code. It's
also where the user asks what they want to do and what would need to change as a result, so each
idea notes its implications: what it touches, what it depends on, and what's still undecided.
Nothing here is finished: Claude removes an idea as soon as it's built, without being asked, and
trims the finished parts out of an idea that's partly built, keeping only what's still to do.
Ideas are added when the user asks.

An idea's heading starts with its priority where the user has given one, `(High priority)`,
`(Medium priority)` or `(Low priority)`, and everything else is unranked, so that the file can be
sorted by priority when the user asks; there is no separate list of what comes first. Anything
marked **In progress**, started but not finished, counts as a priority without being marked one:
when the user asks what to do next, name the unfinished work first, before any idea that hasn't
been started. Keys are described by what they do, not by their letters, since the letters change.

## In progress: the designs agreed with the user on 2026-11-11, to build in this order

Everything below was settled question by question with the user; it is recorded here so that it
survives, and each part is trimmed out as it is built. Register binding, the = rows, the
conditions, At limit, Reset each scene, Allowed inc max, the clip's Scale and the arpeggiator's
register adds, with its editor's fields and Step's "(pattern)", Drift, chains on clips, scenes and tracks, the settings pages' sections, and Density, Swell and Articulate are already built, the one list of time settings below, which Step, Every and Over choose from, Progression with its demos, the Inversion row and Voice leading with theirs, Strum with `13_classic_strum.yml`, the Euclidean mask with `euclidean.yml`, Restart on every generator, Glide, Shorten, Rush and Drag with `14_acid_glide.yml` and `llama_boom.yml`, the Hocket with `19_hocket_shanty.yml`, and Genre on every song (examples still to come take the genres the user approved: Electronic for filter_sweep, idm_chaos1 to 3 and drift_berlin; Classical for drift_canon, drift_pastoral, chamber_music, brass_doorknob, adagio and harmonizer; Children's for row_your_boat; New age for newish_age and gorge; Rock for van_llama and whipping_llama; Musical theatre for retro_musical; Jazz for piano_trio, bigband, llama_supreme and weather; Easy listening for the_mall; Metal for black_midi).

**Time settings, everywhere.** Every time setting is one of: Step (how long one step of a
generator's own row is, default "(pattern)", the step size of the pattern the clip plays), Every
(how often it moves to its next thing, default "1 bar"), Over (how long one ramp lasts, default
"(whole)"), or the Harmonizer's Delay (default "(none)"). All choose from one list: "(pattern)"
or "(whole)" where it applies, 1/64 to 1/2 with dotted and triplet values, then 1 to 16 bars.

11. **The Harmonizer**. Each harmonizer is one voice: in the scale, exact half steps, voice-led,
    or later chord tones; Delay makes a canon or a round; "Follow the melody's rhythm" (default)
    or "Keep this track's rhythm". The design had a Lead track field on the Scene page, overridable
    on the clip page; the Hocket, built since, names its source track on the generator instead, at
    the user's choice, so the Harmonizer might well do the same, to be asked when it's built.
12. **General MIDI previews in git**: the user's goal is to check `sh user_scripts/demos_to_midi.sh`'s files, with
    `previews/DEMOS.md` describing every demo, into git, so that people without a synth can hear the
    demos (not yet).
**Demos, each about three minutes unless noted**: filter_sweep, idm_chaos1 to idm_chaos3,
drift_canon, drift_pastoral (classical: a pastoral for strings, winds and horn in F major, after
Beethoven, Vaughan Williams and Grieg, Drift shaping dynamics and ornaments and borrowing Lydian),
drift_berlin, chord_progression_generator, blues_chords,
voice_leading, row_your_boat, edm_density, bolero_swell, acid_articulate, acid_glide, strum,
euclidean, harmonizer; the pieces van_llama, whipping_llama (with Strum on its rhythm guitar, as van_llama), retro_musical, piano_trio (a jazz
piano trio at a medium swing: ii–V–I changes from Progression, a walking bass, brushes), bigband, chamber_music, gorge,
the_mall, newish_age, brass_doorknob, llama_supreme, black_midi and adagio (with Drift), and
weather (ten minutes). Each is original music in the style asked, never a copy of a song.

**After all this**: look at Numerology and Renoise online for ideas; suggest clearer names for the
demos whose names don't say their style.

## In progress: the batch videos, new visualizers and new demos agreed with the user

Built in this order, each trimmed out as it lands:
1. The Julia mode (neon contour lines, its number travelling round the Mandelbrot set's edge a step a bar) and the
   Newton mode (its roots the held notes, placed by pitch class, the regions in the tracks' colours).
2. The demos as a course (the user's choice): the featured songs first (edm_density, minimal_techno,
   mainstreet_hoedown and new ones), then a learning path from hello_world and the Entertainer, which uses no
   features, through each feature simplest first, the order kept in one data file that docs/DEMOS.md's tables and the
   descriptions come from; each demo's entry in docs/DEMOS.md and its set's Notes get generated "Read about it" links to
   the chapter and heading of every feature it uses (from internal_tools/demo_features.py and a map of features to
   chapters), a test failing when a link is missing or points nowhere. The examples are in examples/learning, examples/other and
   examples/by_genre (the user's choice), where the new demos go by purpose.

## (High priority) The batch recorder reading each song's visualizer

A song now names the visualizer mode Arrange shows first (`SongSetting.VISUALIZER`), and the set one too, the song's over the
set's (`Setlist.visualizer_for`). What's left of the user's ask: each example's pairing in `internal_tools/visualizer_pairings.yml`
becomes its song's `visualizer`, the batch recorder (`internal_tools/record_batch.py`) reads the mode from the set, and the separate
file goes, so that the set itself says which mode suits it and a new demo carries its own.

## Details shown on one track, scene or clip of Arrange

Rather than the details view opening every cell at once (`R`), a key would open the details of what the cursor is on alone,
and the same key again close them: on a track's name, the whole column; on a scene's name, the whole row; on a clip, that
clip only, though its scene's row and its track's column grow to fit it, since a row is as tall and a column as wide as
its largest cell. For the code: `ArrangeDrawing.track_width` and `scene_lines` would ask which columns, rows and cells are
open, a set kept on the page or the app for the session, rather than the one switch `shows_arrange_details`, and
`draw_details` and the Tab picking would act only on open cells; `details_layout` already works the widths and heights out
per column and per row. Whether the blue dividers show while only some cells are open, and how this sits beside `R`, are
to be discussed.

## Uniquify, a wizard after importing a MIDI file, to be discussed

After a MIDI file is imported (the main screen's Import, `ImportDialog`, `finish_import`), a next step, a wizard of
dialogs called Uniquify, would offer to make the imported song the user's own: it looks over the song and keeps its
major details and its scales (the scale objects the import made), and, each as an option, changes up the chords and
changes up the melodies while keeping the overall feel. It might also put generators to work on the result, which is
to be discussed with the user, perhaps as an option of its own. For the code: it would run on the song the import
added, as one change that one undo takes back, like the import itself (`Document.import_song`), reading the patterns
as the import wrote them (degrees in the found key, chords, grids from `importers/steps.py`); changing chords could
reuse what Progression and `composition/progressions.py` know about a scale's chords, and changing melodies would
need rules of its own, such as keeping rhythm and contour while moving degrees within the chord. What "the overall
feel" keeps, how much changes, and which generators, are the questions to settle first.

## A composing tool, to be discussed

The user calls it critical that llamatron learns to compose well in a style: the homage review in `dev_notes/QUEUE.md`
writes its method down as "demo generation intelligence", which this tool and the wizards that generate songs should build on.
Its core is a codified library of genre and subgenre, each a genome of traits after the idea of the Music Genome Project, and
the rules of expectation in David Huron's "Sweet Anticipation" as they vary by genre (see the review in the queue).

**What exists.** Claude wrote the 32 demos of 2026-11-12 (the homages, `strange_woodworking.yml` and
`incoming_message.yml`, and a black MIDI demo since deleted) with a small composing tool, kept as it was in `dev_notes/composing_tool/`: a sketch, not part of the
program, following none of the code's rules yet. The user wants it to become part of llamatron some day, and this is the
starting point for that talk.

**How it works.**
- A song is a short Python specification: tempo, key, genre, instruments and tracks, the patterns, the progressions and the
  scenes, each scene a name, a length in bars, which pattern each track plays (with its chains) and a sentence about it.
- Melodies are written as one token a step: `5` a degree, `b3` and `#4` with an accidental, `5'` and `5,` an octave up or
  down, `1:3` with a chord symbol, `5!90` with a velocity, `.` a rest and `-` a tie. Drums are a line of characters a voice,
  `x` loud, `o` soft and `.` silent, with a table of named beats (rock, disco, punk, shuffle, trance and so on) to start from.
- Harmony is written once: the bass, the chords and any riff are one bar over chord I, and a Progression chain in each scene
  moves them through the chords, as `07_blues_chords.yml` does. Only the melody is written out against the chords.
- The tool works out each scene's length: the clip with the longest pattern repeats to fill the scene and every other clip
  loops, so that every clip lasts as long as its scene, as the examples require. It also writes the notes' scene list and
  "When changing this demo" from the specification, reads the set back through `Setlist.read_file` and saves it in the
  program's own layout, and reports each song's length in seconds, its count of notes, and any note off the piano's keys.

**What it could become in llamatron.** Some directions to talk over, none decided:
- A text notation for a pattern, typed into the pattern editor or pasted into it, the way the tokens above write a melody.
- A "new song from a form" page: pick a beat, a key, progressions for the verse and chorus and a form, and get the tracks,
  patterns and scenes laid out, the melody left to write.
- Beats and bass figures as a library of starting patterns, offered when a pattern is added.
- The scene-length rule (one clip repeats, the rest loop) as what a new scene does by default.

## (High priority) Mono instruments, to be discussed

From the user on 2026-11-11, while designing the Hocket, as a high priority discussion: a Mono
toggle on the instrument editor, for an instrument that plays one note at a time, as a monosynth or
a modular patch does. A Hocket hands notes to tracks that may also play notes of their own, and
several tracks may share one instrument, so notes can overlap on an instrument that can't sound
them together. What it needs, to discuss: whether Mono changes what is exported and played in real
time, or only warns; which note wins when two overlap (the newest, cutting the one before, as most
monosynths do, or the oldest, or the highest or lowest); what a chord does on a mono instrument
(its root, its top note, or refused); whether an overlap cut short becomes a legato slide, as the
Glide row's overlap is; whether it is judged per track or across every track sharing the
instrument; and whether the analyzer idea below would report overlaps on a mono instrument.

## (High priority) Music videos from a Live set's audio, a helper script apart from the tracker

From the user on 2026-11-11: a spin-off mode of the project, a helper script that works
differently from the tracker and turns a finished song into a music video for YouTube, a `.mov`
of a visualizer playing to the song's own audio. It takes two things: the audio that Ableton Live
renders from the song's Live set, probably AIFF, where the set may have been given any synths and
effects in Live, and the song's MIDI files, which the script reads so that the visualizer follows
the real notes and everything lines up with the audio. The Live set has to keep the song's
playing time, so that the audio and the MIDI last the same.

- **What the video shows.** The visualizer alone, full screen, with no scene bar, no clips and no
  tracker around it. It doesn't open with the splash's sine-wave letters; instead something like a
  "produced by llamatron" that flies in from the left and then fades away, its look to be designed.
- **Where it lives.** Not in the GUI: a script run from the command line, given the audio file and
  the MIDI files.
- **What it would mean for the code.** The visualizer modes (`visualizers/`) already draw from
  what they hear (`visualizers/heard.py`), which the script would feed from the MIDI files by
  time rather than from real-time playback; each frame drawn at a fixed rate, rendered to images
  rather than to a terminal, and joined with the audio into a `.mov` (`ffmpeg`, if installed, or
  AVFoundation on a Mac). How the visualizer's characters and big pixels become video frames, at
  what resolution, is the main thing to design.
- **Undecided.** The audio formats taken; how the MIDI files are given (the MIDI (Stems) export,
  the single file, or the set itself); which visualizer mode, or Cycle; the intro's look and
  length; the video's size and frame rate; and what is done when the audio and the MIDI disagree
  in length.

## Generators for composing in sections, approved by the user, each with a demo

From the user on 2026-11-11: chain generators that work at the level of phrases and sections
rather than single notes, each to be discussed in detail before it's built, and each shown in a
demo of its own. Several work best keeping state across repeats and scenes, as Drift will, and
would be built on its song-wide machinery.

- **Progression**, to build first, with `06_chord_progression_generator.yml`: a one-bar figure played
  through a chord progression, moved along the scale bar by bar, so that "1 6 4 5" plays it on
  I, vi, IV and V and a riff becomes a section.
- **Voice leading**, after a discussion of chord inversions, which come first: each chord takes
  the inversion nearest the chord before it, within a range, so chords move smoothly. It covers
  "Inversions" under Chords below.
- **Canon**, with `row_your_boat.yml`, Row, Row, Row Your Boat as a round: the clip repeated a
  number of steps later, moved along the scale and quieter, so one line becomes a round or a
  canon. The demo is to show how a round is edited in the tracker.
- **Density**, with `edm_density.yml`, an EDM piece to show it off: thins a clip by the strength
  of each note's place in the bar, downbeats kept longest, from 0% to 100% of the notes, for
  builds, breakdowns and drops from one full pattern, driven by a scene, Drift or a register.
- **Swell**, with `swell.yml`, its genre to choose: velocity shaped across a phrase or across
  repeats, crescendo, decrescendo or accents on strong beats.
- **Strum**, with `13_classic_strum.yml`, a simple acoustic guitar piece: a chord's notes spread in time,
  down or up like a guitar, or rolled like a harp.
- **Euclidean mask**, with `euclidean.yml`: plays only the notes that land on a Euclidean rhythm
  of so many hits in so many steps, with a length of its own, for West African, Latin and IDM
  rhythms and polyrhythm from one pattern.

Set aside for now, by the user: Develop (motif transformations across repeats), Ornament (trills,
mordents, turns and grace notes as one setting) and Register fold (notes kept inside an octave
range).

Declined, by the user: generators that change a bass line (walking bass, approach notes, pedal
point, anticipation, ghost notes, octaves, root-fifth, boom-chuck, acid). Bass lines and other
parts may instead come later from templates or styles that create patterns and scenes, as the
wizards and pattern generators below describe, but not now.

## Chordify

From the user on 2026-11-11, while settling how generators keep their state: a generator, or a
setting of the arpeggiator, that turns single notes into chords on chosen steps of the bar, the
opposite of what the arpeggiator does. Painted on a whole scene, every track's copy works on the
same steps, so that tracks whose patterns are the same length line up. Undecided: whether it is a
kind of its own or part of the arpeggiator, how the steps and the chord are chosen (a chord
symbol, as the Chord row's, or the scale's triad), and whether a note already a chord is left
alone.

## (High priority) A humanize generator

From the user on 2026-11-11, at the top priority. A generator, beside the arpeggiators,
AutoRatchets and the coming Drift, that makes a part sound played by a person rather than a
machine: small random changes to each note's velocity, its timing a little early or late, and
perhaps its gate a little longer or shorter, each within a range the composer sets, with a seed
like an arp's so that a take can be repeated. Drift's Vel+= with a small range does the velocity
part slowly, trigger by trigger; humanize works note by note, which is what a player's hands do.
What it needs: a settings class and an editor like the others, and a place in the render.
Velocity can change on a finished clip's sounds in a chain, as generators work today, but timing
can't: the groove moves notes in `exporters/timing.py` after the render, so humanized timing
would either be applied there, as a per-note random groove, or the chain would need to move a
note's start, which no generator does yet. Undecided: the ranges and their defaults, whether
timing is in ticks, milliseconds or a share of a step, whether it stays inside a groove's cell so
that notes keep their order, and whether a drum track wants different defaults from a melody.
`mainstreet_hoedown.yml` is the first song it would suit.

## (High priority) ChordRoller, a generator for rolled chords

A generator that plays a chord rolled, as a pianist or a harpist spreads one: the chord's lowest note sounds where the chord
is written, each other note starts a little later than the one below, and the notes end at different times too, so that the
chord opens and closes like a fan and never as a block. It is close to nudging each note by hand, but worked out for the whole
chord from a few settings.

How it sits beside what exists: Strum already starts a chord's notes one after another, by a spread in milliseconds, in either
direction, with a fade and loose timing, and every note of a strummed chord still ends where the chord ends. ChordRoller
differs in two ways: the lowest note always comes first, on the beat, and the ends are staggered as well as the starts. So the
question to settle with the user before building is whether it is a generator of its own, as asked, or a setting of Strum that
staggers the ends, which would give one place for everything about a chord's spread; a generator of its own is the plainer
thing to find by name. What it needs: a settings class and an editor like the other generators, an example set that uses it,
a page in `docs/generators/`, and a place in the render beside Strum's, since Strum moves starts after the render as a groove
does. Undecided: whether the spread is in milliseconds, as Strum's is, or a share of the note's length; how the ends are
staggered (the same order as the starts, the reverse, or a random order from the seed); whether a note may end after the next
chord starts; and what a single note does, which is presumably nothing.

## (High priority) BlackHole Record: the song as a WAV from Live, with no export

From the user on 2026-11-10. An export kind under the Ableton Live set in the Ctrl+X dialog,
called BlackHole Record, that records the sound of the song as Live plays it, through the
recorder's machinery (`internal_tools/record_demo.py`, `docs/RECORDING.md`): the tracker plays the song
in real time into Live over the IAC driver, with Live's MIDI inputs enabled, and the sound comes
back through BlackHole, the loopback device the recorder uses,
into an audio file beside the set, `<set>_<song>.wav`, or AIFF, whichever is the smarter choice
for audio, with no export from Live and no bouncing by hand. The recording is the highest quality
the machine can make, since the goal is a file to upload to SoundCloud: lossless, at the device's
full sample rate and bit depth (SoundCloud takes WAV, AIFF and FLAC up to 4 GB, and plays them
back transcoded, so the upload should be the lossless master, never an MP3). The whole thing is in the GUI: the
dialog asks whatever it reasonably needs, the MIDI port, the audio device, the file's kind, and
confirms before writing over a file, as the Live set export does. While it records, the tracker
hops to a copy of the Arrange page so that the song is seen playing, with the top left corner
reading `EXPORTING` in place of the crumbs, and goes back to the main screen when the take is
done, saying where the file went on the status line.

- **What it would mean for the code.** An `Exporter` subclass in `exporters/` that renders
  nothing itself but drives the transport (`tui/transport.py`) and an audio capture: the
  recorder's `screencapture` records a window with sound, where this wants sound alone, so the
  capture is a small program reading the loopback device, `sox` or `ffmpeg` if present, or a
  Swift script like the recorder's device listing, writing WAV or AIFF; the take's length is the
  song's seconds from `Lengths.song_seconds()` plus a lead-out, as `take_seconds` works it out;
  the tracks need instruments on the driver, made in memory as the recorder's `assign_tracks`
  makes them, so the set isn't changed. The Arrange page gets an exporting mode, `crumb_trail`
  reading `MSG_EXPORTING_CRUMB`, with Space and the edits off. The export list in
  `exporters/exports.py` grows a kind, and the command line's `--to` could take it too.
- **The guide.** With this the user wants `GUIDE.md` to become the top-level guide, broken into
  reasonable subsections, with an Export section that holds the Live set, the MIDI kinds and
  BlackHole Record together. Claude proposes the subsections when this is started, and the
  user and Claude settle them before anything moves.
- **Undecided.** The questions of the dialog, what happens when Live isn't running or its MIDI
  inputs aren't enabled (a message saying what to turn on, since the tracker can't tell what
  Live heard), and whether the recording tool and this share one capture program.

## (High priority) Showing where playback is, inside the patterns, and lighting the roll

From the user on 2026-11-10, after hearing real-time playback for the first time, and the first
of the high priorities.

- **Progress through a scene shown inside the scene's patterns.** Arrange's scene bar and each
  playing clip's bar fill as read heads today; the user thinks the step that is playing can be
  shown in the patterns of the playing scene too, so that the pattern editor open on a playing pattern marks the step
  that sounds now. What it needs: the transport knows each scene's elapsed seconds
  (`scene_elapsed`), and a clip's step at a moment is the elapsed time at the scene's tempo in
  the pattern's step size, modulo the pattern's length, with the direction's order for a
  pattern that doesn't play forward; the pattern editor would ask the transport on the playback
  timer's tick, as Arrange does, and draw the step's edge or step number differently.
- **Listen in a dialog that shows where it is in the pattern.** `L` (Listen) on the clip page
  and in the pattern editor says `listening` on the status line today. The user would consider
  a dialog, like the one above, that stays up while listening and shows the step that sounds
  now, with the same key stopping it.
- **The piano roll lighting up, in colour.** The roll could light the note that sounds now, in
  colour, as the lights on Arrange are the one place colour is allowed today (`.claude/UX.md`,
  "Drawing"). The user wants to explore the questions about a colour mode as this is built,
  rather than settle them first: which things light, whether a colour mode is a setting, and
  what shows without colour.
- **A key that plays and stops says what it will do.** Where a legend or the F1 dialog lists
  `L` twice, as play and as stop, the user wants the word to change with the state, so that the
  key says what pressing it does now, and `Play/Stop` as one entry only where the state can't be
  known. The legends already switch (`ClipPage` and `PatternEditor` bind `LISTEN` or
  `STOP_LISTENING` by state), so the doubled `L` is the F1 dialog, which lists every binding of
  the class, `LISTEN` and `STOP_LISTENING` both; the same goes for Arrange's `PLAY_SCENE` and
  `STOP_PLAYING`, `PLAY_CLIP` and `STOP_CLIP`. The F1 dialog would list the one that applies
  now, or one line with both words.

## (High priority) The visualizer: a lava lamp of rippling colour over the clip area

**In progress.** Stages 1 to 5 are built (`.claude/TRACKER.md`, "The visualizer"): `Z` on
Arrange with Real Time on, `--visualizer`, the recorder's question, `internal_tools/preview_visualizer.sh`, the
notes heard from the transport, and the lava lamp's water, colour and rotozoom on shared pieces,
held under a limiter so that it never flashes; `internal_tools/time_visualizer.sh` times it at about 1 to 3%
of a frame's budget on an 80 by 24 console with 8 to 64 tracks. What is left is stage 6, tuning it
with the user. The spectrum analyser, MilkDrop, the llamas, the hypercube, fireworks, WarpZone, pipes, plasma,
the maze, Mystify, Laser Llama, Mandelbrot and Life are built too,
with Cycle, which shows each in turn every 15 seconds, and each mode's name shown for eight seconds
when it changes. What the user said on 2026-11-10 comes first, and the earlier notes fill
in where they don't conflict. The plan is kept here so that it survives a closed session.

**What it is.** On Arrange, while the set's Real Time switch is on, a key steps the clip area
through the visualizer's modes and, after the last, back to the clips. The clip area is
everything inside the scene names on the left and the track names along the top, down to just
above the footer, which the visualizer never covers, so the scene names, the track names, the
legend and the status line stay. With Real Time off there is no visualizer, since nothing
plays; an export has no use for one. Arrange never opens on a visualizer, except when the demo
recorder is asked to record one (below). One mode to begin with, the lava lamp, but the modes
are a list, so more can follow, sharing pieces or not. From the earlier notes: a mode's name
shows large in the middle for a moment as the key switches to it, as a television shows its
channel, and Esc brings the clips back too.

**The recorder.** `sh user_scripts/record.sh` (`internal_tools/record_demo.py`, not the tutorial) gets a way to record a
visualizer mode instead of the clips: it asks, after the set, whether to record the clips or a
visualizer and which mode, and a flag says the same so a script needn't answer
(`--visualizer <name>`); the launch (`tui/launch.py`) carries the choice, so the tracker shows the
splash as ever and then opens Arrange with that mode showing before the song plays.
`docs/RECORDING.md` documents it, the one guide for recording, kept apart from `GUIDE.md`, which
links to it.

**The first mode, the lava lamp, in the user's words.** The clip area is a grid of big blocky
pixels, low resolution, like a rotozoomer drawn small, blown back up and lightly anti-aliased,
the pixels still very large. Mostly primary-coloured blobs drift around, one for each track,
each a source that sends ripples out as its track's notes fire: thicker ripples for longer
notes, the colour shifting with the pitch. The view rotozooms gently, turning and zooming with
the beat it can hear, and where waves from different sources meet they splash and bounce off
each other like ripples in water. Vaguely a lava lamp, in the spirit of the early WinAmp
visualizers, never muddy, never overwhelming the music. It suits the song by how it is coded,
not by analysing it, and it stays honest: it knows only notes that have started, never what is
coming. The user will speak of it in poetic terms and change it as it is tuned, so its
parameters are named constants in its module, grouped by what they shape, and parts may change
or go. A song can have as many as 64 tracks, so performance matters a great deal.

**Claude's proposal for how it works**, to discuss:

- **Two resolutions.** The visible grid is big pixels, each two terminal columns by one row, so
  that it is square, sized to the clip area and worked out again when the terminal is resized.
  Behind it is a simulation at twice that in each direction, and each big pixel is the average
  of its four simulation cells, which is the derez and the light anti-aliasing. On an 80 by 24
  console that is about 30 by 15 big pixels over a 60 by 30 simulation; a large terminal is a
  few thousand big pixels. Everything is worked out for that region alone.
- **Water.** One height field of whole numbers, the classic demo-scene ripple: each cell becomes
  the sum of its four neighbours halved, less its value the frame before, then damped by a
  shift. Waves spread, interfere and bounce off the edges with no physics beyond that, which is
  the splashing the user describes.
- **Sources.** A track is a blob that drifts on a slow Lissajous path of its own, drawn as a soft
  disc of its colour. A note starting pushes a ring into the water at the blob, as strong as its
  velocity, and a note that is still held keeps pushing a little every frame, so a long note makes
  a thicker, longer train of waves without the visualizer knowing its length in advance. A drum
  track's hits are short sharp rings of white rather than colour.
- **Colour.** Each track takes a base hue from a fixed cycle of primaries (or the instrument's
  Colour setting, from the earlier notes, once there is one), the note's pitch moves the hue a
  little within that colour and its octave the brightness. A colour field of three channels is
  painted where each source's waves are strong and blends with its neighbours every frame, so
  colours meet and mix at the wave fronts. The background stays dark, and an overall limiter
  keeps the brightness down as more tracks play, so 64 tracks never wash out to white.
- **Rotozoom.** The big pixels sample the simulation through a slight rotation and zoom: a slow
  spin, and a zoom that pulses on the song's beats at its tempo (the tempo is the song's own
  setting, so knowing it isn't seeing the future) and swells with how many notes just started.
- **The beat and the theme, by how it's coded.** Faster tempos move everything faster, busy
  passages make more waves, low notes darker and high notes brighter, drums flash and melodies
  colour, so minimal techno and The Entertainer look different without any analysis.
- **Drawing.** Each terminal cell is a full block in one colour, or a shade block mixing two,
  which gives the anti-aliasing many more tones; runs of the same style are drawn as one piece of
  text. Colour is the second place it's allowed, after the playback lights (`.claude/UX.md`,
  "Drawing"), and how many colours a terminal shows is to be decided.
- **Performance.** The MIDI goes out from the Realtime Sender Process, so drawing can never delay a
  note; what drawing costs is the tracker's own time, and the screen answering keys. The
  simulation is whole-number arithmetic on arrays, with no image library: a frame's budget is a
  few milliseconds on an 80 by 24 console, measured with a song of 64 tracks, and a frame that runs
  late is skipped rather than queued. It runs on its own timer only while it shows, and costs
  nothing when the clips are shown. The notes come from the transport, which already knows what
  sounds on each track (`Score.is_sounding`, `sounding_across`), giving each note's number and
  velocity as it starts and while it is held, so no MIDI is read back.

**Stages**, each tested and shown to the user before the next:

6. Tuning with the user on `minimal_techno.yml` and `entertainer.yml`, and a timing tool
   that draws frames of a 64-track song and reports the cost of a frame.

**Decided with the user on 2026-11-10.** numpy holds the arrays. The colours are full colour where
the terminal shows it, falling back to 256 and then 16, chosen for clean transitions and smooth
gradients with big derezzed pixels. A process of its own for the visualizer, with what it draws
sent back, is fine if measuring says it's needed, since the Mac has cores to spare. `make
preview-visualizer` plays a set with the visualizer and no video, so each stage can be seen and
commented on as it's built; the recorder asks clips or visualizer.

**Undecided.** Everything about the look, which is tuned by eye, and the name flashing large as
the key changes mode, which waits for a second mode.

## (High priority) Info about a set on the Open page, before opening it

From the user on 2026-11-10. On the Open page, a key on a set's row, `I` (Info) say, opens a
dialog that says what the file holds before you decide to open it: the set's title, its
description (the one line saying what it plays), its author, and for each song its name, its
tempo and its length when played. Enter in the dialog opens the set and Esc cancels, back to the
list, so that a look costs one key and opening after the look costs one more.

- **What it would mean for the code.** The dialog reads the file the way the Open page already
  reads nothing: `Setlist.read_file` gives the title, description, author and each song's
  tempo, and the length comes from the same estimate Arrange uses (`tui/lengths.py`,
  `measured(song)`), which needs a `Document` of the set, so the dialog builds one in memory
  and throws it away unless Enter keeps it, in which case opening is already done. A file that
  can't be read says so in the dialog instead, with the file's error, and a file that needs
  corrections says that it would open with corrections and how many. The dialog is a
  `MessageDialog` with two answers rather than one, Enter open and Esc cancel, which is a
  `ConfirmDialog` whose buttons read Open and Cancel. The key goes in `keybindings.OpenPage`
  with a legend entry, and the Open page's help names it.
- **Undecided.** Whether Enter on a row should show the info first and Enter again open, which
  would cost everyone a key on every open, or stay as it is with the info on its own key,
  which Claude would choose. Whether a set of several songs lists them all, or the first few
  with a count, since the dialog has to fit an 80 by 24 console.

## (High priority) Arrange scrolls with what plays, when launched for recording

From the user on 2026-11-10, for the demo recorder (docs/RECORDING.md, being built). A long song
has more scenes than fit on an 80 by 24 console, and a video of the Arrange page that stays on the
first scenes shows nothing of the rest. The user suggests that Arrange scrolls down to keep the
playing scene in view, and only when the tracker is launched with a flag, say
`--launch-for-recording`, which may set other properties for a take too, rather than always, since
in ordinary use the cursor decides what Arrange shows and the page shouldn't move under it. What it
needs: Arrange's `top`, the first scene shown, is set by `visible_scenes` to keep the cursor's row
on screen; launched for recording, the playback timer's redraw would move `top` so that the lowest
playing scene (`Transport.playing_scenes`) is shown, and leave the cursor where it is. What else the
flag sets is open: the user mentioned other properties without naming them. The recorder's own
flags, `--autoplay` and `--autoplay-quit-when-finished`, are separate, so a take can be played
without the page scrolling.

## The video tutorial, a long one with chapters (unfinished, set aside by the user)

Agreed with the user, then set aside until they come back to it. What's built: the captions are a strip at the foot of the
screen (`tui/caption_strip.py`), bold black on white over a white line, the page moved up two lines, a long sentence shown a
part at a time for as long as it takes to read, and the recorder writes them as a SubRip file beside the video for YouTube,
which can't turn captions on for everyone (`tutorial/subtitles.py`); the narrator box is gone. What was agreed and not built:

- One long video with YouTube chapters, its first chapter the short easy one: a melody on the piano roll, a drum pattern, two
  tracks, two scenes, playing and exporting.
- The script is data in the repository, written once by Claude and replayed by the runner without Claude: chapters of
  high-level steps (open a demo, go to a page, put the cursor on a named cell, press a binding by name, show the details view
  and lock into a cell, open Scene View, play a scene and wait, build a target song with today's plan), each with its
  caption, the captions businesslike and explaining the purpose of each feature and the musical reason for each edit, never
  selling or saying what llamatron is. Before anything is coded or recorded, Claude writes the whole script to a file for the
  user to read.
- About 85% of the features covered: three demos opened, explained and played, `edm_density.yml`,
  `17_complex_gifts_chain.yml` (cut to a plain workout of chains for this) and `22_registers.yml` as it is, with the details
  view and Scene View shown on them, then a song of the tutorial's own built live, then exported.
- Developed fast: no pacing, silent music, one chapter at a time, no video; the user records the long video only when they
  choose, and a short recording first for them to judge before going far.
- Open: the short recording to judge the caption strip, and the script itself.

## The video tutorial may record the terminal after the tracker quits

From the user on 2026-11-11. The demo recorder had a bug where the last moments of a video showed
the terminal's own text after the tracker quit; `internal_tools/record_demo.py` now holds the tracker on
screen for `HOLD_SECONDS` after the lead-out and trims `TRIMMED_SECONDS` off the end with
`avconvert`. `internal_tools/make_video_tutorial.py` stops its recording another way, by typing into
`screencapture`'s pseudo-terminal when the tracker quits, and may still show a last moment of the
terminal; if it does, the same hold and trim would fix it.

## (High priority) The file picker, shared and better

From the user on 2026-11-10. Every file picker is one: the Open page
(`screens/open_page.py`, which starts in `examples/`), the MIDI import's, and any later one, the
same page given what files it shows and where it starts. The files people want may be far
outside the tracker's directory, so it needs to get there quickly: a full path typed in, with
`~` for the home directory, and perhaps recent directories and recent files. The MIDI import
starts in the home directory until this is designed. Undecided: which of those, and how a typed
path is reached on a page whose `/` already searches, for which Claude offered a row at the top
of the list, "type a path", that Enter opens a prompt on (a directory goes there, a file opens,
a path that doesn't exist says so on the status line), a letter key, `G` (Go to path), opening
the same prompt, or both, recommending the row, since nobody has to know a key to get around.

## (High priority) Accents on beats: velocity in grooves

We should use the time signature information of the arrangement demo to add velocity on beats.
We should research whether we can automatically use, in a per track setting, some knowledge
of time signature to maybe auto fill in the velocity numbers, but this can be explored seperately.

Claude's note from 2026-11-07: this and "velocity shaping in grooves" are the same feature seen
from two sides. A groove already repeats a row of cells from the start of the scene, so a second
row on a groove, a velocity amount per cell, gives accents on the beats per track with no new
concept, chosen the way grooves are now. Swing on the MPC, the Linn drums, Elektron's boxes and
the Cirklon is timing only, and a velocity-only pattern is an accent row rather than a groove,
which is why timing came first.

## (High priority) Marking the chords that fit the scale in the chord picker

From the user on 2026-11-08: when the pattern editor knows the one scale a pattern plays under
(the gauge's scale, `Document.pattern_scale`, known when the pattern's uses agree on one or when
nothing uses it and the current song has one), the chord picker on the Chord row (`Enter`, the
`GridChoiceDialog` laid out by `CHORD_GROUPS`) puts a check mark beside each fixed chord whose
notes all lie in that scale from the step's note, like `✓ M` on a major chord from the root of a
major scale. The scale chords (`5`, `3`, `7` and so on) are built from the scale, so they always
fit and need no mark; the mark is for the named ones, `M`, `m`, `dom7` and the rest. Since a new
song starts with `C Major` as its scale, the scale is known most of the time, and only a pattern
played under several scales goes without the marks. What it would mean for the code: a `Chord` or
`Scale` method that says whether a chord's notes are all in a scale, `GridChoiceDialog` taking a
mark per option, and the Chord row working out the marks from the step's degree, accidental and
octave. The user wants to talk this over before it's started.

## (High priority) New patterns from the clip page

From the user on 2026-11-08. `P` (Pattern) already opens a clip's pattern in the editor, from
Arrange and from the clip page. The clip page could gain two `Button`s under its settings: one
that adds a new pattern, assigns it to the clip and opens it, so a clip can be filled in without
a trip to the Patterns page; and one that adds a new pattern as a copy of another, asking which
pattern to copy in a picker and then assigning and opening it the same way. Because a pattern
made this way is used by this clip alone, the editor knows its scale at once, from the clip's
scene or the song. What it would mean for the code: the clip page building its buttons with
`FieldPage.button`, `Document.add_pattern` and `copy_named` (the Patterns page's `C`) followed by
`set_clip_slot_setting`, then opening the editor as `P` does. The user wants to talk this over
before it's started.

## (High priority) More ways to munge a pattern

The user has tried the pattern editor's munge dialog (`M`: reverse after the cursor, reverse before
it, reverse all, pivot around it, randomize) by hand, so the next step is to think about which
other munges earn a place in it. Each is a `Pattern` method that rearranges or rewrites the steps
in place, like the five there now, and the cursor stays on its step. Candidates to weigh, not
decisions: rotate the steps left or right by one (the Cirklon's and Elektron's nudge), invert the
degrees around the step under the cursor or around the scale's root, transpose every degree by a
number of scale steps, double the pattern by repeating it at twice the steps or halve it, thin it
by dropping every other note or by a probability, swap two halves, and copy one row's values from
another pattern. Which of them belong in the munge dialog, which are really pattern generators
(see "Pattern generators on the Patterns page", which already has notes for pattern builders, and
the Metrics Wizard's "Transforms") and which want a key of their own is the thing to decide.

## Refactoring

### The goal

The long-term goal is very readable, object-oriented code: classes in files of their own,
designed with care, each doing one clear job, and never cryptic or obfuscated. Someone reading
it without AI help should be able to see what each class is for and how the pieces fit. The
earlier readability ideas belong here: moving classes into individual files, sharing behavior
through base classes where several classes repeat the same shape, more small helper methods
with names that say what they do, and code and comments that explain the why, in the order a
reader needs it.

### Rules for every class

- **No class reads or changes another class's data members directly.** Everything goes
  through methods on the class that owns the data.
- **Nobody uses the classes as an API.** llamatron is used through the text UI, so the classes
  are internal and their methods can be renamed or reshaped freely to suit the design.
- **Plain accessor methods, not Python's accessor magic.** Another class changes a member only
  through a method like `set_name(name)`, and reads it only through one like `get_name()`,
  rather than through properties or descriptors, so that what happens is visible where it
  happens, and every setter can validate what it's given. Setters can take sensible defaults,
  like `set_name(name=None)`.
- **Only the accessors that are used.** Getters and setters aren't added for every member
  automatically. A class has only the ones other classes actually call, so its accessors show
  what's part of its contract with the rest of the program.

These rules are in CLAUDE.md and the whole codebase follows them since the accessor audit below.
Every change to the song goes through `Document` and the objects' setters, which is what made
undo and redo easy and will make wizards easy.

### The accessor audit

**Done on 2026-11-07.** Every class keeps its data private behind `get_` and `set_` methods, only
where other classes use them; the `_Validated` descriptor and every property are gone; `Note`,
`Chord`, `Scale`, `Rest`, `Degree`, `Held` and `Control` are plain immutable classes with getters;
the grid lives in `src/llamatron/grid/` and the tracker in `tui/screens/` and `tui/dialogs/`, one
class per file. Decided with the user along the way: references between objects stay names looked
up at render, which keeps binding late, and every step was checked with `internal_tools/compare_exports.py`
and the full suite. What's still worth doing under the same heading is moving more behaviour onto
the objects that own the data wherever a reader would look for it there first.

Open question from 2026-11-08: probability rolls and random directions are seeded from the
song's seed, the scene and the **track's name** (`ClipSlotPlayer`), so renaming a track changes
what a song with probability plays, though nothing breaks. Renames are meant to change nothing.
Seeding from the track's place instead would make renames safe but reordering tracks unsafe,
and either change alters existing renders once. `test/test_renames.py` keeps track names in the
examples until this is decided.

### Other design decisions to revisit

- **Chain generators work on rendered notes, not steps.** That keeps binding late, so a chain
  follows scale changes, but a chain's result can never be seen or edited in the tracker, and a
  generator can't think in steps. Worth keeping in mind when designing the pattern generators
  above, which would write steps instead.

## Time signatures, what's left

Time signatures were built on 2026-11-07: on the song and optionally on a pattern, purely
graphical in llamatron (bold step numbers on beats, the signature in the editor's header) and
metadata in the exports (a meta event in every MIDI file, the Live set's control and each Live
clip's own signature). Still to think through:

- **Scenes.** A meter change mid-song would be an optional `time_signature` on a scene, meaning
  the song's when left out, written as a second meta event where the scene starts and into Live's
  scene settings. It's rare in this music, and it needs no migration, so it waits for a song that
  needs it.
- **Bar lines and bar counts, low priority.** Beats have bold numbers and a bold double line
  down their left edge since 2026-11-07. The first step of each bar could get one more mark, a
  heavier line or a bar count in the header, which would help most in long patterns, where a
  block of steps may start in the middle of a bar.
- **Patterns that don't fill a bar.** A pattern shorter or longer than a bar, or one with a
  pickup, starts its count somewhere, which links to the pickups idea.

## A scene_length setting on scenes

Noted 2026-11-07, not wanted yet. Today a scene has no length of its own: it lasts as long as its
longest clip that doesn't loop, with repeats. That keeps a scene's length from being a second
thing to keep in step with its clips, and it's how Session View works, but there's no way to say
"this scene is eight bars" independent of what's in it. A scene of short clips that should last
longer needs a repeat or a loop, and silence at the end of a scene needs a clip to carry it.

An optional `scene_length` on a scene, in bars or whole notes, would pad a shorter scene with
silence and cut a longer one, with `None` keeping today's behaviour so that older files still
load. The Cirklon, or one of the user's earlier projects, had a fixed scene length of this kind.
It would also be a natural home for a scene's time signature (see above), since a length in bars
needs one. docs/WHY_LLAMATRON.md's point about scenes without a length is held back until this is decided.

## Chords

### Grabbing whole chords

Today a grab step takes a single note, the chord's root, even when the track it grabs from plays a
chord. A chord grab feature could let a step take the whole chord. If it comes, it should
probably be a choice rather than a change, because single-note grabs are what basslines and
hocketing need.

### Custom chord types and scale types

Let a song define its own chord types and scale types, each a new kind of named object kept
in the song, like scales and arps already are, and then usable anywhere the built-in ones are.

A custom chord wouldn't need to be musically "right". It's just a shape of notes built from the
step's note, such as three power chords stacked in octaves, an octave doubling with a note in
between, or a cluster. It would be written as half steps above the note, like the named chords
(`M`, `dom7`) are, or as scale steps, like the numbered ones (`3`, `7`), so that it follows the
scale. It would also fix most of the problem with The Entertainer described above: Joplin's
right hand is mostly a melody note doubled an octave down with a note between, a shape no
built-in symbol has, so each hand had to be split across three tracks.

A custom scale type would be one octave of half steps, as `ScaleType` values are, and a named
scale could then use it as its type. The user noted on 2026-11-08 that a user's scale type is
independent of any root, so it's entered as half steps from the root rather than as note names,
for instance by toggling keys on the Scale page's keyboard drawn from C
(`tui/components/keyboard.py`). Things to settle: names have to fit the pattern editor's
5-character chord cell and be told apart from the built-in symbols, the chord and scale pickers
would need a page for the song's own, and renaming or deleting one has to update or refuse its
uses, as with everything else.

When custom chord types come, the MIDI import ("Import MIDI, what's left") is updated to use them, the
user's wish of 2026-11-10: notes that start and end together in a shape no built-in symbol has
become a chord of the set's own on the Chord row rather than extra tracks.

### African scales

Consider adding scale types from African traditions to the built-in list, on 2026-11-07 the
user's request. Many of them don't sit on twelve equal half steps: the equiheptatonic scales of
the Chopi timbila and of Ugandan and Mozambican xylophone music divide the octave into seven
roughly equal steps, and the equipentatonic scales of the Gogo and much of East Africa into five,
so a `ScaleType` built from half steps can only approximate them, and the approximation may not
sound right without microtuning, which llamatron doesn't do and MIDI only manages with pitch bend
or a tuning table in the synth. Worth including anyway where a twelve-note approximation is in
use already, such as the anhemitonic pentatonic shapes common across West Africa and the
Ethiopian kiñit (tezeta, bati, ambassel and anchihoye), which are pentatonic modes that fit twelve
notes. Each would be one octave of half steps, like every `ScaleType`, so adding them is a list
change plus a page in the scale picker, and the picker's names would need to fit. A microtuning
note in the guide would say what's approximate.

## Morphing

### More morph types

Morphing today only moves notes from one pattern to the other, sweeping in from the left, the
right or the middle. Other kinds of morph worth exploring would slowly move between the two
patterns' other settings too, such as averaging velocities, probabilities or CC values across the
repeats, rather than only swapping notes.

### Morphers as objects

Morph strategies could become their own object type, MORPHERS, defined by name with their
settings like arps and AutoRatchets are, and then picked on a clip in place of today's
`morph_style`. The details haven't been discussed yet.

## Songs with very many patterns

`examples/by_genre/ragtime/entertainer.yml` is a whole piece written eight bars at a time, and it has 81
patterns on six tracks over 20 scenes, and had 107 over 38 when its phrases were four bars. That's a realistic size for a full composition, and it
shows where a plain list of patterns starts to strain:

- **Seeing what belongs together.** Names like `A 1-4 treble 1` group themselves by section and
  by track only by convention. The list could group or sort by a name's prefix, or by the track
  a pattern is used on, or show only the patterns one track or one scene uses.
- **Knowing where a pattern is used.** The Patterns page counts each pattern's uses in USED,
  and `/` searches every list; listing the uses is "Where a pattern is used" below.
- **Going straight from a clip to its morph target or its chain.** `P` (Pattern) opens a
  clip's pattern from Arrange and the clip page; the same could work for its `morph_to`
  pattern and for its chain.
- **Making many patterns at once.** Typing in a long piece means making one pattern per phrase
  per track. Copying a scene's patterns to new names in one step, or naming new patterns from
  their scene and track, would cut that down.
- **Size on disk.** The file is about 50 KB and still reads well in a diff, so the file format
  isn't the limit yet.

### The notes a pattern plays, under every step

The pattern editor's description line says what the step under the cursor plays, which the user
likes, and would really like to see for every step at once: a blank line under the step grid,
then a row in a lighter colour with the actual note each step plays, like `C3  E3  G3  --  C4`,
lined up under the steps so the eye can read the melody without moving the cursor. The
description line of the step under the cursor could then go, with that space used for the
default a blank cell would get when the cursor is on one, such as `Default gate: 1/16`, where a
row has a default to show; a blank Note cell has nothing to show, so the space stays empty there.

What it touches: `PatternDrawing` already works out what one step plays for `describe()`, through
the current song's scale and the editor's `cell_text`, so the row is that per step, fitted to the
same cell width as the grid, and scrolling sideways with it, with the lighter colour being
`Style.DIM` because the tracker draws with the terminal's own colours only. The 80 by 24 budget
is the constraint: the grid grows by two lines (the blank one and the notes); a drum pattern's row would show the drum note letters
and a chord step the chord's name or its lowest note. The defaults shown for a blank cell come
from `composition/defaults.py` and the set's step size, which the Gate row's default is.

### A way home, now that pages can jump

`P` (Pattern) was the first jump, and it settled what going back means: Esc goes back to the page
the jump came from, the crumbs show the path taken (`ARRANGE › clip: (scene 1, lead) › pattern:
tune`), and a page that comes back redraws from the current set and follows renames. What's
left to think about: getting to the main screen could take many presses of Esc once more jumps
exist, so a key that goes straight there may be needed; and if a pattern could jump to the clips
that use it, the stack could grow without end, so a jump to a page already on the stack might
go back to it instead of opening it again.

## A tree sidebar, to try on a branch

The user's idea from 2026-11-07, to be described more later: a sidebar beside the page, drawn as a
tree whose nodes expand and collapse, so that what's under each song (its tracks, scenes and
clips, and the set's shared patterns, scales, generators, chains and grooves above them) can be
seen at a glance, along with where you are and what you're looking at. It may not work out, so
it's something to try on a branch rather than build straight in.

What it would touch, roughly: every page is laid out for 80 columns, and the pattern editor and
the Arrange grid use all of them, so the sidebar would have to fold away or only show on wider
terminals, or replace the crumbs on the top line rather than sit beside the page. Textual has a
`Tree` widget, which would need checking against the rule that the tracker draws with bold, dim,
reverse video and box characters only. If the tree can also be moved in, it becomes the first way
to jump between pages that isn't up or down one level, which is the question under "What Tab
means, once pages can jump".

## Tests with less hard coding

Many of the text UI tests reach a setting by pressing a counted number of keys, like down, down,
enter, which breaks whenever a page gains or reorders a field, and has to be worked out again by
hand each time. The tests should instead ask each page where things are and navigate there, using
the same ordered lists that the page draws from: its fields, its rows and its keys.
`select_field(label)` on `UITest` in `test/ui_testing.py` is a start, for settings pages: it finds a
field by its label in the page's own `fields()` and presses up or down as far as needed. The
same idea could cover list rows, pattern editor rows and dialog options, and then the existing
tests could be changed over to it. The aim is tests that a person can read, and change,
without counting key presses.

## Ideas from other trackers

Look through other trackers for features worth borrowing, the way the Cirklon and the Elektron
Monomachine have already given llamatron note grab, registers, step directions, CC slides
and its arpeggiator. Ones worth a look include Renoise, OpenMPT, Furnace and SunVox on the
computer, LSDJ on the Game Boy, and the Polyend Tracker and Dirtywave M8 as hardware. Things to
look for: how they handle long songs and many patterns (see above), effect columns and per-step
commands, groove and swing, pattern chaining and song order, and how they keep everything
reachable from the keyboard.

## Pattern generators on the Patterns page

Tools on the Patterns page that write a new pattern, or fill one in, from a few choices: a
melody, a bassline, a chord progression, a drum beat and so on. They'd be different from today's
generators, which change a clip at render time in a chain: these would write ordinary steps into
a pattern once, which can then be edited by hand like any other. They'd live beside the clip
generators in `src/llamatron/generators`, or in a package of their own for pattern mutators.

Making them intuitive will take some thought, so nothing is decided yet. Questions to settle
first:

- **Where they live.** A key on the Patterns page that makes a new pattern, a key in the pattern
  editor that fills in or rewrites the rows under the cursor, or both.
- **How few choices are enough.** Something like "bassline, 16 steps, follows these chords" is
  easy to pick, but every extra setting makes the dialog harder to use.
- **Trying again.** A generated pattern is rarely right the first time, so generating again with
  another seed, and undoing, should each be one key.
- **Following the song.** Writing degrees rather than notes keeps a generated pattern following
  the scale, as everything else does. A bassline or melody could also take its chords from
  another pattern, the way a grab takes notes from a track.

## Wizards for large changes

Bigger tools, possibly opened with `W`, for changes too large to make by hand comfortably:
starting a song from a template (a set of tracks, scales and empty scenes for a style), or
utility work like renaming a set of patterns, copying a section to a new key, or splitting a
long pattern into phrases. W already saves under a new name on the Set File page, so the key
would need some thought.

llamatron must not become an AI music generator, so a wizard never decides the music for you.
Every wizard asks plenty of questions and does only what the answers say, and what it makes is
ordinary patterns, tracks and scenes that can be edited afterwards. To be explored later.

### (Medium priority) Style wizards for starter songs

Very interesting to the user. Wizards that make a starter song in a
style, which the user then edits like any other: every pattern, track and scene stays ordinary
and editable. Styles the user mentioned:

- country rock, with options named in the spirit of artists without copying them, like "Neil"
  and "LargeBirds"
- classic metal, and the new wave of British heavy metal
- classical composers' styles
- jazz, in its various modes
- blues, especially 12-bar blues and its variations

The rules:

- It's a fun starting point, not an AI generator. Each wizard asks key questions every time, so
  the user has to make the human choices: how long the song is, which scale to use from a list
  the style suggests, and so on.
- Styles, not songs: nothing copies a real piece's melody or arrangement, so there's no copyright
  problem. A style is things like its chord progressions, rhythms, tempos, scales and form.
- Songs consider key changes where the style has them, such as a modulation up for a last
  chorus, which scenes' own scales can already do.
- Each style needs research before it's written, and styles can be added and improved over time.
- It needs its own package, perhaps `src/llamatron/wizards/`, with one module per style, to keep
  the code clean.

What it touches in the code: wizards would build songs through the composition objects, which
is how every change is made now. It likely
shares code with the pattern generators above, and blues and jazz progressions would want the
scale chords and per-scene scales that already exist. The wizard key is still to be decided (see
above, and the hotkey review).

### A construction wizard: genre first, then questions

The user's idea from 2026-11-08, growing the style wizards above into a bigger, smarter one,
and a very big research project:

- **Genre, then subgenre.** The wizard first asks for a genre, like rock, country, blues,
  classical, rap or electronic, and then a subgenre. Electronic must include at least minimal
  techno and acid, and each style has its own minor variations worth modelling.
- **Questions, not decisions.** It asks about the keys to use, whether to include key changes
  and how many, how many tracks, how many of them are rhythm tracks, and whether percussion is
  one combined track or several. Desired song length and feeling are asked too.
- **Drum maps.** A combined percussion track should follow Live's drum rack MIDI note maps, as
  discussed on the internet, as far as that can be found out (see "Named drum maps").
- **Research.** Every genre needs research into its styles and composition rules, so that the
  wizard is smart, and the code object-oriented: a style is an object with its rules, which
  subgenres refine.
- **Names people can work with.** Patterns are named very deliberately, so that it's easy to
  find and tweak them afterwards, and scales are named after the parts of the song they belong
  to, so that people can edit or rename a part's scale easily.
- **Renames must be safe** for this to work: renaming any object updates everything that refers
  to it (a rule in CLAUDE.md, checked by `test/test_renames.py`).

## Import MIDI, what's left

The user's direction: when the import is refined, it should use the genre library (`dev_notes/GENRE_PLAN.md`)
to decide how to break a song into patterns and scenes, recognizing its form and sections, and where a part is better
described as a simpler pattern with a generator (an arpeggiator, a strum, a ratchet, a Euclidean rhythm) than as raw notes.

From the user on 2026-11-10. The import is built, underneath the tracker and from the main
screen's Import cell (`.claude/FORMAT.md`, "The MIDI import", and `.claude/TRACKER.md`,
"Importing a MIDI file"). What is left:

- **Ratchets.** An AutoRatchet's or an arp's slices of a step come in as notes on a finer step,
  which makes the ratchet and chain demos hundreds of short scenes; a run of equal notes inside
  a step could be one step with the Ratchet row.
- **Grooves.** A swing's offsets fall between any step, so the groove demo is the one example
  that doesn't play back the same; the import says the notes sit off the steps as a swing, a
  groove or a live performance plays them, and a groove could be worked out from them.
- **The Entertainer.** It makes 113 patterns at 32 steps and 95 at 64, against the demo's 81,
  which drops 19 notes and cuts others; when the import cuts it as well, its output replaces the
  demo, as the user asked.
- **Scene names.** Named after their bars for now; the user would like smarter names if a way
  is found.
- **The main screen's row of actions.** Five narrower cells, the Import cell called Import
  since `Import MIDI` didn't fit 16 columns; the user will comment on the arrangement.

## Live launching scenes in line with llamatron's

Noted 2026-11-07. In llamatron a scene finishes before the next starts, and the exported
Arrangement View lays the scenes end to end at exactly those lengths. Session View is different:
launching a scene fires its clips together at the next launch quantization boundary (a bar by
default, counted by the time signature), each clip then loops on its own, and nothing waits for a
scene to finish. So a scene whose length isn't a whole number of bars (it lasts as long as its
longest non-looping clip) drifts from where the Arrangement put it when launched by hand. Two
things could help: the Arrange page showing a scene's length in bars and marking one that doesn't
divide evenly; and writing Live's scene follow actions, which can advance to the next scene after
a set time, so that Session View plays the set the way llamatron does. The second needs checking
against the template and proving in Live, and it's the same auto-advance idea as the real-time
playback design below, on Live's side.

## An analyzer that checks a set for problems and makes recommendations

From the user on 2026-11-11, while designing the Harmonizer, a generator that keys off a track
it names: deleting that track would set the name to nothing and leave the harmonizer doing
nothing, which is fine for now, but a set can quietly stop doing what was meant. The idea is an
analyzer that reads a set and reports such things, with recommendations: a generator naming a
track that is gone, a register bound to a lane with no CC number, a condition comparing
registers nothing changes, an add past a register's limit, a pattern no clip plays, a scene that
waits forever. What it needs: a list of checks, each a function of the set returning findings in
the tracker's words, run on demand from a page or the command line, and perhaps on save; some
checks overlap the uses and corrections the tracker already has (`tui/uses.py`,
`composition/corrections.py`), which it would build on rather than repeat. Undecided: where its
report shows, whether it can fix what it finds, and which checks come first. The user added, while
designing Progression: it could flag things that don't make sense, like a progression on a drum
track (which does nothing), recommend features, and perhaps refactor a song.

## Smoothing a bound CC lane

From the user on 2026-11-11, while designing register binding, where a track's CC lane bound to a
register sends a CC event whenever the register changes. A register changes in steps, so a bound
filter jumps from one value to the next, which is right for a rhythmic effect and harsh for a
sweep. The idea is a smoothness setting, per bound lane on the track or per register, that ramps
from the old value to the new over a length, as the Slide row ramps a CC row to its next value
today (a value sent every `SLIDE_STEP`, and two points in a Live envelope). Undecided: whether the
ramp runs over a fixed length, like a 1/16, or all the way to the register's next change, which
only the timeline knows, as Slide knows the next CC value; whether it is one setting for the
track or one per lane; and how a ramp that crosses the end of a clip is cut, since a bound lane
sends nothing on a track whose slot is empty.

## Pitch bend

From the user on 2026-11-10, with the MIDI import's CCs. Pitch bend isn't a CC: it's a MIDI
message of its own, with values from -8192 to 8191, and llamatron has no way to send it, in a
pattern, an export or real time, so the import leaves it out and counts it. The user doesn't care
for pitch bend much in electronic music, so it waits. Before it's built, find a good public
domain MIDI song that uses pitch bend, for `examples/midi/`, to prove it works by the round trip
(`internal_tools/test_all_sample_midi_against_import.sh`). Claude offered a fifth kind of lane that a track's
CC setting names, `PB` say, whose 0 to 127 are sent as pitch bend with 64 as no bend, about 3
cents a level over a bend of two semitones; the Live set already has a pitch bend target on every
MIDI track (`exporters/ableton_project.py`).

## Real-time MIDI, what's left

Real-time playback is built: the Instruments section and the main screen's Real Time switch, the
Realtime Sender Process, Space on Arrange with every start by hand at the next bar, `L`
(Listen) on the clip page and in the pattern editor, the lights, the clock and Ctrl+T
(`.claude/FORMAT.md`, "Real-time playback"; `.claude/TRACKER.md`, "Real-time playback"). The exports stay exactly as they were. What the
user's design of 2026-11-07 and 2026-11-09 still has in it, to do one item at a time:

- **Edits while playing never stop playback.** Today an edit is heard at the next launch: the
  transport renders the song again when something is launched after the set changed, and what
  plays keeps its events. The design: each playing clip is a queue of passes of its pattern, an
  edit re-renders and replaces the passes not yet started, and the clip takes the change when
  its pattern comes round. `PlaybackEngine.drop(tag=, after=)` is there for it. The lag report
  (`internal_tools/realtime_report.sh`) times the render of `test/sample_sets/heavy_chain.yml` against a
  pass for this reason, since an edit has to be rendered before the old passes run out.
- **On the Patterns page, a pattern that's playing has a green dot beside it.** Today only
  Arrange, the clip page and the pattern editor show what plays.
- **More follow actions, like Live's.** From the user on 2026-11-10, with the Advance field's
  "With Scene", "Next" and "Off": Live's "Previous", "First" and "Last" could follow, each a
  value of `FollowAction` that `Player._send_starts` turns into a scene other than the one
  below, with the same Launch together rule when the start arrives. "Any" and "Other", Live's
  random ones, would take the song's seed. Nothing in the format changes but the list of
  choices.
- **Looping a scene, to consider.** The user asked on 2026-11-09 whether a scene that loops makes
  sense once playback is in real time: the scene plays again and again until another is
  launched, where a scene's Repeat is a fixed count (the Scene page stops Repeat at 999, which
  the user thinks is more than anyone needs). An export has to end, so a looping scene would
  have to be ignored when exporting, playing its Repeat as it does now, or warned about, in the
  export dialog and on the command line. Which of the two is to decide. For the code it would be
  a scene setting that is off by default, so no file needs migrating, read only by real-time
  playback and never by `SongRenderer` or the exporters. How it sits with a looping clip needs
  settling first, since a scene whose every clip loops already plays until the human starts
  something else, which stops an export today.
- **Testing over the wire with a receiver**, from the user on 2026-11-07: a small program the
  tests spin up, which makes itself visible as a MIDI device (a virtual port through
  python-rtmidi's `open_virtual_port` on a Mac or Linux, or the IAC driver) and records every
  event with its time, so that what the tracker sends over a real port is compared with the MIDI
  export, every example and demo through it, the timing errors reported to the user with
  Claude's opinion of whether they would sound tight. Today the suite holds the player to the
  export inside the process (`test/test_realtime.py`) and the report measures the Realtime
  Sender Process on recording outputs, which open no port.
- **MIDI clock**, so that other gear follows, from the same sender.
- **The timestamped and compiled senders**, kept in reserve from Claude's proposals of
  2026-11-07 in case Python ever drifts: timestamped output through CoreMIDI or the ALSA
  sequencer (PortMidi exposes it portably, python-rtmidi doesn't; Windows has no such queue), a
  compiled scheduler in process (a CPython extension, or Rust through PyO3), or a helper program
  in Rust or C fed over a pipe. The Realtime Sender Process measured within 0.11 ms on every
  event (`internal_tools/midi_timing_spike.py`, `internal_tools/midi_spike.sh`), so none is needed yet.

## Buttons: rows on a page that do what a key does

The Set File page already has Save and Open rows that do what Ctrl+S and Ctrl+O do, so that the page
can be worked with the arrow keys alone, and the user wants that idea finished and named: a
"button" is a row on a page, drawn like the menu rows on the main screen, that Enter presses and
that shows the hotkey it stands for, so nothing is reachable only by a key. The Set File page has
Save and Open buttons below its settings, and the clip page Play and Stop; Save as is still `W`
alone. Buttons are for places where a Ctrl+ or
other shortcut has a logical home on the page too; the rest of the UI is easy enough to move
around that it doesn't need them yet. Where they'd go next:

- **The pattern editor**: a Munge button right after the step grid, which opens the munge dialog
  and shows `M`, so that munging moves out of the footer and the footer gets shorter.
- **Real-time MIDI**: Play and Stop buttons on the Scene page, as the clip page has. The pattern
  editor keeps to the `L` key alone, since the page is full, by the user's choice of 2026-11-09.
- **Claude's other candidates, to weigh**: an Export button on the Song page already exists as a
  row, which is the same idea; a Rename button on the editors that rename with `N`; Load over on
  the pattern editor beside Munge; New set and Save as on the Set File page; Add at the bottom of
  every list, which the `+` row is already; and a Help button is probably not worth a row, since
  F1 is on every legend.

The footer stays the key legend for the page's own keys, as "F1 as the hotkey dialog, and a
shorter footer" below describes, so a button's key still shows there. What it would mean for the
code: `Button` in `screens/field.py` exists, made by
`FieldPage.button` and drawn below the settings after a blank line with its key's name in front,
as the main menu draws a row, so what's left is a Save as button on the Set File page, a cursor
position below the grid in the pattern editor, which is new for it, and a check in
`test/test_tui_pages.py` that every button's key is still in `keys()`, so pressing the key and the
button do the same.

## Naming the CC numbers in the track editor's picker

From the user on 2026-11-08, to confirm when it comes up. The track editor's CC 1 to CC 4 fields
take a number from 0 to 127, typed or nudged, and the MIDI specification gives most of those
numbers a standard purpose: 1 is the mod wheel, 7 volume, 10 pan, 11 expression, 64 the sustain
pedal, 71 resonance, 74 brightness, which is the filter cutoff on most synths, and so on. Enter on
one of those fields would open a picker listing every number with its name beside it, like
`74  brightness (filter cutoff)`, searchable as every picker is by typing, so that typing `filt`
finds the number for a filter sweep without looking it up, and the unnamed numbers would be
listed as numbers alone. The pattern editor's CC row labels, which say the lane's number, like
`CC 1 (74)`, could add the name where the cell width allows. What it would mean for the code: a
table of the standard names in `music/midi.py`, the CC fields' Enter opening a `ChoiceDialog`
built from it in place of the number prompt (`MSG_CC_PROMPT`), with `+` and `-` still stepping the
number, and the names as `MSG_` constants since they're shown.

## A Settings page, from a YAML dotfile

A Settings page in the app, reached from the main screen, whose values live in a dotfile in the
user's home directory, `~/.llamatron`, written as YAML and read through `safe_yaml.load_safely`
like everything else. The settings are the user's own preferences rather than anything a set
stores, so they never go in a set file, and every one has a default so that no dotfile at all
means the program as it is today. What they could hold:

- **Streamlining the app**: hiding features the user never uses, such as pages, pattern editor
  rows or whole export kinds in the Ctrl+X dialog (someone who never writes MIDI files sees only
  the Live set), so that the legends and dialogs get shorter.
- **Defaults for new songs and sets**: real-time MIDI on by default once it exists, default MIDI
  channels for tracks, default track names for a new song (`kick`, `bass`, `lead` instead of
  `track 1`), a default tempo, time signature or scale.
- **Starter content**: a set file whose patterns (and perhaps scales, chains and grooves) are
  added to every new set automatically, so that a personal library follows the user around; this
  overlaps with "A library of patterns, chains and arps" below and could be how that starts.

What it would mean for the code: a `Settings` object in `support/` or a package of its own, read
once at start with defaults for everything, passed to the app rather than read from a global;
`Document` and the pages ask it for defaults where they use `composition/defaults.py` today, so
the file format's defaults stay what they are and the user's defaults only apply to what the
tracker creates; the Ctrl+X dialog and the legends filter their lists through it; and the page
itself is a `FieldPage` that writes the dotfile back. Tests set a dotfile path explicitly so that
they never read the developer's own.

## Colour, switched on in the song

From the user on 2026-11-08: a `colour` setting on the Song page, off by default, that lets the
tracker draw in colour; today it draws with bold, dim, reverse video and box characters only,
because terminal backgrounds differ (`.claude/UX.md`, "Drawing"). To discuss before anything is
built: how colour is best used, which things would carry it (the beat lines, the selected row,
the gauge, the tie bars, the status line) and whether the terminal's theme can be detected, which
Textual tries through the terminal's reported background and which not every terminal answers.
If it can't be, two palettes, one for dark terminals and one for light, chosen in the same
setting, each checked on a real terminal of its kind. A later idea: once a Settings page exists
("A Settings page, from a YAML dotfile" below), the setting moves there, since colour is the
user's preference rather than the song's, and the dotfile in the home directory is where it
belongs. What it would mean for the code: `Style` in `tui/drawing.py` is the one place styles are
named, so a palette is a mapping from each of its names to a Rich style, picked when the app
starts and whenever the setting changes, and `screen_text` in the tests reads only reverse video,
so colours need a test of their own that checks the palette is applied and nothing else changes.

Added by the user on 2026-11-08: once there's colour, each kind of page gets a stripe of its own
colour down the left edge of the screen, drawn with block characters from under the header to the
legend, so that a glance says which page is open, because some pages start to feel the same: the
list pages, the settings pages and the editors each read alike. One colour per kind of page, or
per page, is to be decided with the palette. What it would mean for the code: a `STRIPE` colour
name on each `Page` class, or one per base class, drawn by `Page.draw` as the first column of
every body line when colour is on, with the body a column narrower, so no page lays it out itself.
The user added on 2026-11-08 that the main screen's cells take the same colours as the stripes of
the pages they open, so the grid is a key to the stripes.

Added by the user on 2026-11-09: the piano roll's cursor box, the bold double bars either side of
the cursor's cell and the double rule that boxes it against an octave divider, takes a colour of
its own once there's colour. And rather than a setting, colour should switch itself on: look up
whether Textual can tell that the terminal supports colour and engage it automatically, ignoring
the idea that colour needs a user preference, choosing colours that look good first on a dark
terminal and are still not bad on a light one. If Textual can switch to its dark theme on its own,
that's the ideal. What to look up: Textual's `theme`, `available_themes` and `register_theme` (the
app runs with `ansi_color=True` today, which keeps the terminal's own sixteen colours), whether it
asks the terminal for its background colour and exposes the answer, Rich's `Console.color_system`
for the colour depth, and the `COLORTERM` and `NO_COLOR` environment variables, which a terminal
sets and a person can set to switch colour off.

## Ctrl+ keys for the rest of what's global, to discuss

Save is Ctrl+S, Open is Ctrl+O, Export is Ctrl+X, Help is F1 and About is F2, so that the
plain letters are always local to the screen in question and free to change, as the user decided
on 2026-11-07; Quit became the plain Q on the main screen alone on 2026-11-08, because Ctrl+Q was awkward to type. New and Save As are still plain letters on the Set File page, and whether they count
as global and should move to Ctrl+ keys too is to discuss. Ctrl+C, Ctrl+Z and a few others are taken by the
terminal, and on a Mac F1 needs Fn unless the function keys are set to standard keys.

## uv instead of venv and pip, to discuss

Someone suggested using `uv` for setting up and controlling the Python environment, in place of
`python3 -m venv .venv` and `pip install -e .`. The user wants to discuss whether this makes
sense or is a good idea before anything changes, on 2026-11-07, and asked for it only to be noted
for now.

What it would touch, if it were done: INSTALL.md, the setup commands in README.md, GUIDE.md and
CLAUDE.md, `internal_tools/test.sh`, `user_scripts/demos_to_live_sets.sh`, `llamatron.sh` and `internal_tools/make_docs.sh`, which all
assume `.venv/bin/python`, and the note in INSTALL.md about building PyYAML with libyaml. Things
to weigh: uv is much faster at installing and can pin the Python version too, but it's one more
tool to install first, where venv ships with Python, and the instructions would need to stay
right for people who don't have it.

## Exporting to other DAWs

Today llamatron exports an Ableton Live set, one MIDI file of the whole song, MIDI stems or a
folder of MIDI clips. Which other DAWs get a project format of their own is to be decided
(2026-11-09): for now the stems and the single MIDI file are the way into any other DAW, and
real-time MIDI will be the other. When one is chosen, a new kind is one subclass of `Exporter`
(`src/llamatron/exporters/exporter.py`) listed in `src/llamatron/exporters/exports.py`, sharing
the note timing in `src/llamatron/exporters/timing.py`, so it mainly needs to write the format.

## An Optimizer Wizard

A wizard that takes a song entered in a plain way, such as every note typed out (as a MIDI import
would give), and rewrites it with fewer, more reusable patterns and generators. It should do
this without needing much AI, by searching rather than guessing.

The search would try rewrites like these, each of which can be checked exactly:

- two patterns that are the same become one;
- patterns that differ only by moving along the scale become one pattern plus a transpose,
  where the tracks allow it;
- repeated equal notes become a Ratchet, or an AutoRatchet in a chain;
- a run of notes that walks a chord becomes the chord plus an arpeggiator;
- a passage that repeats becomes a clip with a repeat count.

The method would be a search with a cost, rather than minimax, which is for games against an
opponent. The cost could be something like the number of patterns plus the number of steps, and
the search could be greedy (always take the rewrite that saves most) or a beam or
branch-and-bound search that tries a few paths. The rule that matters most: a rewrite is only
kept if the song still renders exactly the same notes, compared event by event, so the wizard
can never change the music. Like every wizard, it would ask before each kind of change, and
show what it would do.

## A Metrics Wizard, and transforms that enrich a melody

### Metrics

A wizard that reports on a song and suggests things to look at, without changing anything:

- how long each scene and the song are, and how often each pattern is used, including unused
  patterns;
- each track's range of notes, and notes that fall outside a typical instrument's range;
- how busy each scene is, in notes per bar for each track;
- notes outside the scale, and tracks that clash, such as a half step apart on a strong beat;
- velocities that never change, or clips much shorter than their scene;
- how much repeats exactly, which hints at where an Optimizer Wizard could help.

### Transforms

Ways to make a basic melody or part richer, each one a choice the user makes, and repeatable
with a seed:

- passing tones and neighbor tones between melody notes;
- chord extensions, turning triads into sevenths, ninths and more;
- syncopation, swing, and moving notes ahead of the beat;
- ornaments such as trills, turns and grace notes;
- octave doubling, and a harmony line in thirds or sixths;
- reharmonizing a chord progression with substitute chords.

Some of these could be generators that run in a chain at render time, so that the plain pattern
stays as written and the transform can be turned off. Others could be pattern mutators, which rewrite a pattern's steps
once, so they can be edited afterwards. Either way, nothing is generated unless the user asks,
and what comes out is ordinary patterns and settings.

## A llama that runs across the bottom of the screen

Asked for by the user on 2026-11-08: a small llama drawn in ASCII block characters that runs
across the bottom of the screen when the program starts, and runs across again every time the
set is saved, each run in the opposite direction to the last. An export runs a llama too, but one
that's somehow different from the save's, perhaps two llamas running together, to be decided when
the idea is picked up. The first thought was a llama that stood on the main screen until the
first key press; the running one replaced it the same day. What the llamas look like is to be
discussed then, with sketches to iterate on first, as with every drawing. What it would mean for the code: the drawing as a tuple of `MSG_`
lines, like the About dialog's cow (`MSG_COW`), and a mirrored copy for the way back; a Textual
timer on the app that moves the llama a column or two at a time along the line above the legend,
or over the status line, which every page shares, so that it runs on whatever page is open;
`Document.save` and the export telling the app which happened, which starts the next run with
the right llama or llamas; the app remembering
which way the last run went; and the run leaving the keys working throughout, since it's only a
drawing. The tests would step the timer by hand rather than wait, and check that a save starts a
run the other way.

## Explaining the row under the cursor

Asked for by the user on 2026-11-08. The main screen does it already: the dim line under the grid
says what the selected cell is for (`MSG_ABOUT`). What is left: the list and settings pages could
explain their rows the same way, like a field's meaning on the Song page.

## Where a pattern is used

A pattern shows where it's played: the Patterns page counts its uses in USED, and the next step
is a way to see them, as a list of song, scene and track, like the list shown when deleting a
used pattern is refused, from the Patterns page or the editor. What it would mean for the code:
`uses_of` in `tui/uses.py` already puts the uses into words, so a key on the Patterns page
or the editor that shows them in a `MessageDialog`, or a column, is most of it.

## Tidying away unused patterns

From the user on 2026-11-10, with the MIDI import, since a bad import is undone by deleting its
song. Deleting a song offers to delete the patterns that song used and no other song uses, in a
question that lists them. The Patterns page gets a key that deletes every pattern no song uses,
after a confirmation that says how many. What it would mean for the code: `uses_of` and the
Patterns page's USED count already know which patterns are unused, so it's a question after the
Songs page's delete and a key on the Patterns page, each one undo step. Undecided: the key's
letter, and whether the question lists the patterns or only counts them.

## Function keys for the most important things

Some things that matter most could take the other function keys, F3 and up, since one key is
easier to type than Ctrl and a letter: candidates are Save, Export and Open. On a Mac the
function keys need Fn unless they're set to standard keys, which weighs against it. To discuss
with "Ctrl+ keys for the rest of what's global" below, since both are about what's global.

## More ideas from Claude, noted for later

These came from building the demos. The user chose which to keep.

### Song order, given that scenes are already ordered

Most trackers have an order list naming sections in the order they play, with repeats, so that
"A, A, B, B, A" is five short entries rather than twenty copied scenes. The Entertainer demo has
20 scenes because every repeat is written out. But llamatron's scenes already play in order, top to
bottom, so how an order list would fit needs thinking about first. It could be a separate list
that refers to scenes, scenes could get a way to say "play scene 3 again here", or a scene's
`repeat` might already cover most of it. Live has its own idea of scenes, which matters too.

### Pickups, if they can be intuitive in the pattern

A way to write a pickup, the notes before the first full bar, as the music has it. Simple Gifts
starts with a two-note pickup, which had to be moved to the front of the pattern so that it loops
cleanly. Only worth doing if it reads naturally in the pattern editor, such as marking where bar
one starts within a pattern. A clip setting that starts it partway through is the other way.

### Transpose on a clip

Today transpose is set on a track and moves every clip on it. A clip's own transpose would let
one pattern play at different pitches in different places on the same track, which is the most
common kind of reuse in songs, and would let an Optimizer Wizard merge many more patterns.

### Grooves, what's left

Timing grooves were built on 2026-11-07, as decided with the user: a `grooves` section of rows of
cells, the factory grooves, the song's, scene's and track's choices with `false` switching
grooving off, applied in the exporters' timing so that all four exports groove the same. What's
still open:

- **A groove override on a clip**, decided on 2026-11-07: a `groove` on a cell, a name or `false`
  like a scene's or a track's, with the highest priority of all, so that a clip's choice wins
  over its track's, then the scene's, then the song's, and `off` anywhere still plays straight.
  It's one setting on `ClipSlot`, a Groove field on the clip page built by `screens/groove_choice.py`,
  a fourth argument to `Song.groove_at`, and the rename and uses code that the other three have.
- **Velocity in grooves**: see "Accents on beats: velocity in grooves".
- **Random timing jitter** in a groove, which would use the song's seed like probability does.
- **Polyrhythms**: parts in different meters against each other, such as a track in 7 against 4,
  and what that means for scene lengths.
- **Notes off the grid.** A note between two cells, such as a 32nd in a 16th groove, takes the
  amount of the cell it falls in. Live moves such notes towards the groove's positions instead;
  whether that's wanted can be decided when a groove with short notes sounds wrong.
- **The last note of a clip.** A note delayed past the end of its clip is cut there, as every note
  is, so a swung last 16th is a little shorter. Letting it run into the next scene would mean
  clips that overlap, which Live doesn't do.

### Sequencer inspiration from the MPCs, to think about

The user wants a pass over the best-loved MPCs (the MPC60, MPC3000 and MPC2000XL especially) for
ideas, once grooves exist: their groove and swing patterns and what made the feel famous, note
repeat, the 16 levels mode, timing correct and shift timing, and any other quirks of their
sequencers that a step tracker could borrow, in the spirit of `docs/WHY_LLAMATRON.md`.

### (Low priority) Named drum maps

Drum patterns name hits by note letter and octave, so a kick is "C, octave 1".
A map on a drum track, like `kick: C1`, would make drum patterns easier to read. But the user
uses a separate instrument in Live for each drum track, so it would need testing in a way they
don't usually work, and drum maps differ between instruments in Live anyway.

### (Low priority) A library of patterns, chains and arps

A file of reusable parts that any song could copy from, and the base for song
templates. The difficulty is keeping it from being confusing in the text UI, alongside each
song's own patterns and generators.

## Performance hot spots

CLAUDE.md holds the standing rule: profile with cProfile over the examples, prefer doing less work
to new number types, prove with `internal_tools/compare_exports.py` that a speedup changed nothing, and
test both paths of any shortcut. The 2026-11-08 work did that for estimating, grabs, clip
lengths, notes, numbers (`Rational`) and YAML reading. One candidate noticed then is still
unmeasured:

- **Rendering a Live set.** Each track is a deep copy of the template's track, and every
  shared id is renumbered by walking the whole tree. That's fine for a few tracks, but worth
  measuring for songs with many tracks and scenes, since the Live set is now the slowest part of
  rendering a big song.

Efficiency shouldn't cost readability, which matters more here: a faster version only goes in
where it's measurably needed, and stays as clear as what it replaces.

## Sections: groups of scenes, with their own overrides

Group scenes into sections, so that a long piece, such as a large classical performance in
several movements, stays manageable in the tracker. A section is a named run of scenes in
order, like the verse, the chorus, or a movement, and it can also change how its scenes play,
so a section can be played again in a different key or with other changes. By default every
song has one section holding all its scenes, so every song written so far just has one
section, and nothing about it changes.

The user suggested it might be called a Stanza. Claude's suggestion is "Section", which says what
it is more plainly. A classical piece might call
its sections movements, which a section's name can say.

### What a section could override

These are Claude's suggestions, to be decided. Each resolves at render, like scales do today,
so binding stays as late as possible, and the order would be clip, then scene, then section,
then song:

- **Key.** The section's scale, so that playing it again in G major moves every degree.
- **Transpose.** Moving every track along the scale, on top of each track's own transpose.
- **Tempo.** Its own tempo, or a ramp across the section, as scenes have.
- **Dynamics.** Scaling every velocity, like playing the whole section softer, from pp to ff.
- **Which tracks play.** Muting tracks for the section, to thin it out the second time.
- **Seed.** A different seed, so that probability and random directions give a new take.
- **Generators.** Swapping one arp or chain for another throughout, like a busier arpeggio on
  the repeat.
- **Time signature.**
- **Groove,** chosen like a scene's, between the scene's choice and the song's.

### Playing a section again with changes

Repeating a section with different settings is where sections meet the song order idea. A song
could have a list of section entries in play order, where each entry names a section and can
override its settings, like `A`, `A` in G major, `B`, `A` softer. The scenes stay in order
inside each section, which answers the open question in "Song order, given that scenes are
already ordered": the order list arranges sections, not scenes.

### What it touches

- **The file format.** Following the inline rule, sections would hold their scenes inside
  them, each with its settings, which is a structural change that the file's `version` marks. A
  file without sections loads as one section holding all its scenes, by the defaults rule.
- **The Arrange page.** Scenes grouped under section headings, which could fold away, with keys
  to jump between sections, and a section's settings page.
- **Organizing patterns.** Patterns could be grouped by section too, so that the pattern list
  shows only a section's patterns, and names like `A 1-4 treble 1` in The Entertainer wouldn't
  need the section in them. But that conflicts with names being unique across the song (see
  "Every object has a unique name" below), so whether a pattern belongs to a section, or is
  only tagged or filtered by one, needs deciding.
- **Live.** Session View has no sections. Playing a section again with a different key needs
  new clips, so each section entry would become its own run of scenes in the Live set. In
  Arrangement View, Live's locators could mark where each section starts.
- **The many-patterns ideas,** which sections would help with, and The Entertainer, whose
  strains (Intro, A, B, C trio, D) are exactly sections, with the trio in another key.

## Every object has a unique name

All objects must have unique names. Patterns, tracks, scales, arps, AutoRatchets and chains
already do, within each kind, because the file stores them by name. The exception is scenes:
their names are optional and can repeat, which is why the grid's `ClipRow` and `ClipColumn` have
ids today. Making this a rule means:

- **Scenes always get a name,** and a unique one. A new scene already gets a name like
  `scene 3`, so mostly this means refusing duplicates, and naming the unnamed scenes in older
  files when they load, by the defaults rule.
- **Unique within a kind, or across all kinds?** A pattern and a chain both called `bass` don't
  clash today, because every reference says what kind it names. Unique within each kind is
  probably enough, but this needs deciding, and sections may change the answer if patterns
  belong to sections.
- **Ids may become unnecessary.** With unique scene names, the ids on `ClipRow` and `ClipColumn`,
  which exist only because names could repeat, could perhaps go, and the clip tree's file names,
  which use ids, could use names instead.

## Small demo tasks, to do in one batch

Gathered on 2026-11-07 so that they can all be done at once, since each touches `examples/`,
`docs/DEMOS.md` and `test/test_demos.py` together:

- **The grab demo doesn't make a good song.** It should take the original melody and not have
  different voices come in at different times: four voices alternate singing notes, so voice 1
  sings note 1, voice 2 note 2, and so on. The full grab-track voice should be silent, but the
  music should start immediately with all voices active for the full track.
- **The arpeggiator demo** is good in the first section and then halfway into the synthwave
  section; the rest should be dropped. A lot of the other demos are EXCELLENT.
- **Redundancy.** The minimal techno example seems unneeded now that there's a morph demo,
  `18_techno_morph.yml`. (acid_techno was replaced by `22_registers.yml`, and retro_chill was rewritten
  on 2026-11-07 as an original piece and renamed `08_tie.yml`.)
- **The tie demo** could be replaced by a public domain song, as the other demos are, written with
  ties instead of gate lengths, since the original piece doesn't sound great.

## Gauges for the generators: the auto ratchet counts, a stutter and the groove editor

From the user on 2026-11-08, to sketch and iterate on before anything is built, with the gauge
and piano roll work's component focus: steps that can only go up and down so many points read
better as gauges than as numbers. The arp's offsets editor is such a gauge now, built from
`SignedGauge` in `tui/components/signed_gauge.py`. The auto ratchet's counts, a cycle of how many
slices each note is cut into, could be short gauges too, and a stutter, which llamatron doesn't
have yet, would be the same kind of row. The user wants a proposed sketch of each, drawn the way
the pattern editor sketches were, to iterate on before deciding. What it would mean for the code:
`SignedGauge` reused by the groove editor in place of its one-row drawing, since a groove's cells
are signed percentages too, and a counts row for the auto ratchet editor in place of its text
field.

## A gauge dialog for picking a number cell's value

From the user on 2026-11-08, to sketch before anything is built: Enter on a cell that holds a
number in the pattern editor, Velocity, Prob, a CC row, Octave or a register change like `AX +=`,
would open a dialog with a gauge, the way Enter on the Chord row opens the chord picker, so that
a value can be picked by sight, with the arrows moving along the gauge and digits still typing.
The register note and velocity rows are toggles, so they'd have no such dialog. The user wants
example sketches first, drawn the way the pattern editor sketches were, before deciding. What it
would mean for the code: a dialog in `tui/dialogs/` drawn from the gauge pieces the Degree row
and `SignedGauge` already have, and an Enter key on `NumberRow`, `ControlRow`, `CcRow` and
`OctaveRow`, which today only take digits and `+/-`.

## Arpeggiators that make chords

Asked for on 2026-11-07, to design later: an arpeggiator setting that turns a step into a chord
by putting a chord type on that step, so that an arp over a line can play, say, the third note
of each cycle as a triad and the rest as single notes. Today an arp only splits chords into
notes; this would let it build them too, like the offsets row but holding chord symbols.

## Reviewing every hotkey in the text UI

Review the letter keys on every page of the text UI, to see whether any could be more logical,
and only change them if it's warranted. This needs discussing before anything changes. Making
one key more logical can mean moving another to free its letter, so the review should look at
every page together. Every key binding is in `src/llamatron/tui/keybindings.py`, one class for each page, and
`internal_tools/keys.sh` prints them all, or every binding that has one key (`internal_tools/keys.sh --key s`), so that's the
complete list to work from.

Things already worth a look:

- **The same letter meaning different things on different pages,** like the letter that opens a
  page from the main screen also sorting lists, or the one that moves a row down also removing a
  step in the pattern editor.
- **Letters that are text in some places.** On a drum pattern's Note row, the note letters type
  notes, so any editor key on one of those letters isn't available there.
- **Letters chosen because the obvious one was taken.** Some of the pattern editor's
  whole-pattern actions moved into the Reconfigure dialog, which freed letters, so the question is
  whether the remaining letters on each page are the obvious ones.
- **Whether every page offers the same key for the same kind of action,** such as renaming,
  copying, deleting and moving up or down, wherever those apply.

## Grouping the F1 dialog's keys

From the user on 2026-11-08. The F1 dialog lists the keys that work everywhere, a blank line and
then the page's own keys, in two columns in the order the page's `keys()` gives them, and on the
pages with many keys, the pattern editor above all, that's getting messy: related keys sit apart
and a reader has to scan the whole list to find the one for moving, or for a note, or for the
whole pattern. The idea is to group them, so that related things sit together under a short
heading, like `Moving` (the arrows and the jumps to the ends), `Notes` (drawing, cutting,
lengthening and erasing a note), `The pattern` (sizing, inserting and removing steps,
reconfiguring) and `Views` (switching between the roll and the rows), each group in its own two
columns with a blank line between, the way the everywhere keys already sit apart.

What it would mean for the code: a binding in `tui/keybindings.py` would take a group, a constant from a
small class of group names in `strings/legends.py`, and `HelpDialog.key_columns` would lay out one
block per group in the order the groups are declared, falling back to one block for a page that
names no groups, so that the pages can be grouped one at a time. The legend wouldn't change. The
test that every page's help fits an 80 by 24 console (`test/test_tui_pages.py`) keeps its hold,
so the dialog may need to scroll, or to put the headings in the columns' first rows, on the
pattern editor.

## Using the tracker with the basic keys alone: the arrows, Tab, Space, Enter and Esc

From the user on 2026-11-08: audit every flow in the tracker to see that most of it can be used
with the basic keys, the arrows, Tab, Space, Enter and Esc, typing only when a text or number dialog asks for it,
so that the letter keys stay as shortcuts for people who know them and nobody needs them. There
are many letters to remember now, and the point is to make the tracker intuitive, with less to
remember, by giving every action a way to be reached without a letter. The user knows some keys
will stay; which, and how the pattern editor's views are reached, is for the audit to propose.

What the audit would look at, page by page, with what's already there:

- **The main screen and the list pages** are nearly there: Up and Down move, Enter opens, and
  every list has a `+` row where Enter adds. Rename, copy, move, sort and delete are letters only
  (`N`, `C`, `U/D`, `S`, `Bksp`), so a row would need a way to reach them: a dialog of actions on
  the selected row, perhaps on a second Enter or on Tab, or action buttons under the list the way
  the settings pages have `Button`s.
- **The settings pages** are there: Up and Down pick a field, Left and Right change it, Enter
  types or chooses, Space or Enter toggles, and the action rows are `Button`s reached with the
  cursor.
- **The pattern editor** is the furthest away: the rows' values are typed or nudged with `[`/`]`
  on every row that takes a number (Degree, Octave, Gate, Velocity, Prob, Ratchet, Ratchet
  Offset, the CC rows and the register change rows like `BX+=`, all through
  `PatternRow.adjust_keys`), and the whole-pattern actions sit behind `R`, `S`, `I` and `D`,
  which could join the Reconfigure dialog or a sidebar of buttons. No key needs Shift since
  2026-11-09 (`.claude/UX.md`), so the audit proposes no Shift or Ctrl with an arrow.
- **Arrange** reaches every clip, scene and track with the arrows and opens them with Enter, but
  copying, pasting, inserting and deleting are letters; the same dialog of actions would serve.
- **The dialogs that search** (the pickers and the list pages' `/`) should say so: a picker's
  search starts as soon as something is typed, which nothing announces, and a list page's search
  is behind `/`, which the legend no longer shows. The user wants these to be a richer dialog,
  one that tells you that `/` or typing opens the search, shows the search field and its state,
  and perhaps offers the search as a row or button, so that it's found without being known.

Each page's `keys()` is the complete list of what it can do, so the audit can walk every page
from those and write up, per page, which actions have no letterless way to them and what that
way would be, before anything changes. The user wants that write-up, and an opinion on how to
group each page's keys in the F1 dialog, once the queued work is done. It belongs with the hotkey review and the grouped F1
dialog above, since all three are about there being less to remember.

## Euclidean sequencing

Evaluate whether llamatron can already do Euclidean rhythms, which spread a number of hits as
evenly as possible across a number of steps (like 3 hits in 8 steps, which gives the tresillo), or
whether it needs a feature. Today a Euclidean rhythm can be typed by hand into a pattern, since
steps are now all the same length, and a pattern's play direction and repeats work on it as on
any other. What's missing is a way to make one without working it out: perhaps a pattern
generator on the Patterns page (see "Pattern generators on the Patterns page") that fills a row
from hits, steps and a rotation, or a chain generator that does it at render time. To be decided.

## Features the demos underuse

`internal_tools/demo_features.py` (`internal_tools/demo_features.sh`) prints which features each set in `examples/`
uses, and which none or only one does. Each demo teaches one feature (see `docs/DEMOS.md`),
so a feature without one is a candidate for a new demo or for a scene in an existing one. When
it was first run, no demo used: clip names, a song seed, a time signature other than 4/4, a
pattern's own time signature, or a set of several songs. Only the tie demo used ties and slides,
only the ratchet demo used ratchet offsets, only the registers demo used register note rows and
resets, and only the direction demo set a pattern's direction. The existing demos stay as they
are; the gaps are for the new demo below.

### A demo of several songs in one set

A new demo set that covers what no other demo does: it holds several songs, uses clip names, gives
a song a seed, plays in time signatures other than 4/4, and gives at least one pattern a time
signature of its own. Its purpose is mostly coverage, but it has to be musically interesting
rather than chaff: the songs are in one genre, still to choose, and the point of putting them in one
set is that they share patterns intelligently, the way a set of songs for one concert would, with
a pattern playing in more than one song, perhaps at another tempo, scale or time signature, and
with each song adding patterns of its own. It should use plenty of the other features too, chosen
because the music wants them, like the other demos do. Nothing in `examples/` plays in 3/4 or
6/8 yet, so at least one song should. It gets an entry in `docs/DEMOS.md`, a description that
says what to keep when changing it, and a place in `HAND_WRITTEN` in `test/test_demos.py` unless
it's written through `test/demo_sources/make_demos.py`. The genre and the tunes are to be decided
with the user first.

## Risers, horns and filter sweeps, with smooth automation

Techno often has risers and horn-like swells: a long sustained note while its loudness, filter or
another sound setting moves underneath it. Filter sweeps are the same idea on any sound. Earlier
we talked about how the Elektron Monomachine's parameter locks work (a value set on a step, as
other gear does too), and llamatron's CC rows and Slide already work that way. What needs making
sure of is that when MIDI automation is drawn, the transitions are smooth, not stepped. This may
need a test, and the user checking the result in Ableton Live.

What the code does today, and what it means for this:

- **Velocity can't change during a note.** In MIDI, velocity is sent once, when a note starts,
  so a held note can't swell by velocity. A riser on one long note needs a CC instead, such as
  CC 11 (expression), CC 7 (volume) or a filter cutoff the synth listens to, set in the track's
  `cc` numbers. Velocity, and the registers, can only change from note to note.
  The GUIDE should say so where risers come up.
- **Long notes:** a gate can now be up to 4 whole notes, but it's cut at the end of the
  pattern, so a riser longer than one pattern needs the Tie row, or a long pattern.
- **Slides:** a step with `slide` ramps each CC value to that lane's next value. Live gets two
  envelope points and draws a straight line between them, which is smooth. The `.mid` files get
  a value every `SLIDE_STEP`, which is stepped at a fine grain. Things to check: whether
  `SLIDE_STEP` is fine enough to sound smooth on a slow sweep, since a CC only has 128 values
  anyway; what a slide does when the lane has no later value in the pattern, and across the
  end of a pass into the next repeat; and the hold points (a held value gets a second point at
  the moment of the next one), which have never been confirmed in Live.
- **Shapes:** Live draws straight lines, so a riser that should curve, like an exponential
  filter sweep, would need several points or Live's curved segments. The curve format in a
  `.als` isn't known yet, so that would mean saving a set from Live with a curve and reading it.
- **Testing:** a test can check that the envelope points and the `.mid` control changes are
  where they should be and move in one direction without jumps, but only listening in Live
  proves the result is smooth. A riser scene in a demo would give the user something to check.

## Refactoring the tests to the program's style rules

**Deferred by the user on 2026-11-06.** The tests are held to the same style rules as the
program (see CLAUDE.md), and new tests follow them, but most existing tests were written before
the rules and still need refactoring:

- **Format strings and messages as constants.** Tests build many strings inline, with f-strings
  and `.format`, like `f'« {item.shown_label()} »'`. Each should be a named constant at the top of
  its test file, or in a shared test module when several files use it.
- **Limits and meaningful numbers named.** Literals like `128` for "just past the top" should
  come from the program's constants (`MAX_REGISTER_VALUE + 1`), and a number that means
  something, like a register's maximum, should be a named variable, so that two 3s that mean
  different things can't be confused. `test/test_registers.py` is an example of the style.
- **Shown text through the program's constants.** When a test checks text the program shows,
  like a row label, a key's name, a page's title or a message, it imports the program's constant
  for it (`ROW_LABELS[Row.DEGREE]`, `ERR_SCENE_NO_SUCH_SCALE`) instead of writing the words out
  again, so that renaming something in the program changes the tests with it. Every shown string
  is a `MSG_`, `ERR_` or `HELP_` constant now, so the tests, mostly `test_tui_pages.py` and
  `test_tui_document.py`, can swap their literals over, along with the drawing they wrap them in,
  like the `│` before a row label, which can be a helper in the test file.
- **Demo tests read from the YAML.** A test of a demo checks values it reads from the demo's
  file, not values written into the test, so that hand edits to a demo don't break it.
- **One constant per line.** `src/` has none left; some tests still define several constants
  on one line with tuple syntax, and these need splitting too.

It's mechanical but wide: the text UI tests alone are thousands of lines. Doing it a test file at
a time, with the full suite passing after each, keeps it safe, and it fits with the earlier note
on making the tests less hard-coded.

## What pycodestyle flags, to look at or ignore

`internal_tools/pep8.sh` runs pycodestyle with the exclusions in `setup.cfg`, for a look rather than as a rule.
On 2026-11-07 the user asked for the remaining kinds of report to be noted here, to investigate
whether they matter and, if nothing changes, to add them to the ignore list:

- **An import below module-level code (E402).** All five are in `test/demo_sources/make_demos.py`:
  it puts the test folder on `sys.path` before importing `gate_conversion` from there, which is
  marked `noqa`, and the four llamatron imports after that line could simply move above it. One
  cause, and a two-minute change if it's wanted; otherwise ignore E402.
- **A lambda assigned to a name (E731).** The list pages' are gone, each now a method named
  `open_item`. What is left is in `test/demo_sources/make_demos.py`. The project's own rule for
  unclear lines would favour a named function, so pycodestyle and the style agree here, but each
  is one short line.
- **Continuation line indentation (E128) and three blank lines (E303).** Cosmetic, under thirty
  reports in all on 2026-11-07, with no conflict with the style; fix once or ignore.

## The Registers page as a grid

The Registers page (`R` on the main screen) lists sixteen settings in one column: AX default, AX
minimum, AX maximum, AX wraps, then the same for BX, CX and DX. The user wants it drawn as a grid
like the pattern editor's instead, with the registers' names, AX, BX, CX and DX, across the top
and one row for each kind of setting down the side: default, minimum, maximum and wraps. Each
value is then a cell, four columns by four rows, which reads at a glance and is much shorter.

What it touches in the code: `RegistersPage` in `src/llamatron/tui/screens/registers_page.py` is a
`FieldPage`, a column of `Field`s, so it would become a page that draws its own grid, with a
cursor that moves in both directions like the pattern editor's, and the keys depending on the
row under the cursor: digits, `+` and `-`, `Enter` and `Bksp` on the number rows, and `Space` or
`Enter` on the wraps row. The grid drawing of the pattern editor (`screens/grid_drawing.py`) could be
shared, since it's the same box characters and reverse-video cursor. `Document.set_register_setting` and the
refusal messages stay as they are, and `test_tui_pages.TestRegistersPage` would change with the
keys. The help text would need rewriting for the new keys.

## Melodic figures for melody generators

Short melodic figures, a few notes each, counted across many works: which turns of phrase a style favours, how a figure is
elaborated and ornamented. An experiment to recognize styles by them was started and deleted, the user's choice, since figures
may only be collected from sources clearly in the public domain (classical scores, folk tunes, ragtime), where styles are
already recognized best. The idea kept is the other use: a melody generator that builds a line from a style's favoured
figures and its ways of varying one.

What it touches in the code: a table of figures per style measured from the public-domain corpus alone, a new module in
`src/llamatron/genres/hearing/` to cut a lead into figures, and a generator in `src/llamatron/generators/` that reads the table.
No melody of a copyrighted work is ever read (`.claude/GENRES.md`, "Only What Can Be Acted On").


## Code Examples

The user's idea, to be discussed once the genre work has rested for a while. A top-level folder, `code_examples/`, of scripts
the user calls "code example" tasks, which Claude may generate when asked. Together they show the "API" for llamatron, marked
unstable, since the classes underneath are internal and change freely. Every code example builds its set from llamatron's own
objects, never from YAML, unless the user says otherwise for one. The first three:

- a script that imports a MIDI file named on its command line and saves it as a YAML set;
- a basic song exactly like the hello world demo;
- a more complex song with several clips, generators and chains and a few other settings changed, sounding more or less like
  one of the demos.

It means: a folder and a README saying the API is unstable; tests that run each example and hold the second to the hello world
demo's music; the GPL header and the code rules on each script; a decision on whether the website gets a page for them.

## Chords From a Named Scale, and Typed Chords

What is left of the chords that leave the scale, now that a step and a progression's chord have a Scale, a Quality and Tensions
and one Chord dialog. Not built: borrowing from a named scale with a root of its own (only a scale type on the clip's root is
borrowed); typing a chord as a numeral or a name in the Chord dialog; shortcuts for the dominant of the next chord and the
tritone substitute; the piano roll's thin lines for a chord's tensions.

## TiMidity as a Second Synthesizer

The user's idea, to consider. TiMidity supported beside FluidSynth as what makes sound with no DAW. When both are installed
the tracker asks which to use as it starts; an environment variable sets the default and skips the question; when only one is
installed there is no question.

It means: TiMidity found, started, waited for and ended as FluidSynth is; an instrument's device able to name either; the
question at startup and the variable that answers it; the WAV export and the scripts that make and record the demos choosing
the same way; an install script that offers it; and the pages on FluidSynth saying so.
