# Work Queue

The work the user has agreed to and that isn't built yet, in the order it will be built, kept by Claude (the user's
rule). Each item says what was agreed, so that the queue survives a conversation being summarized. An item is removed as
soon as it's built, a request made while Claude works is put where the user says (the bottom unless told otherwise), and the
user may reorder it at any time. Ideas not yet agreed live in `dev_notes/IDEAS.md`.

## Next

Items 1 to 7 are parked while the genre library is built; item 8 is current.

1. **Sections and order on the object pages (23, 24 B).** Name first, the rest alphabetical, sequences keeping their order
   (Start/End/Over/Then, Lowest/Highest, CC 1 to 4, AX to DX). Song: Performance, Writing. Scene: Articulate, Density,
   Registers, Swell, Tempo & Groove. Clip: Articulate, Density, Playing, Strum, Swell. Track: CC Lanes, Euclid, Octave Range,
   Register Binding, Strum. Arpeggiator: Registers, Run. Drift: Notes, Registers, Run, Velocity & Probability. No "Advanced".
2. **Descriptions beside values (25).** On object pages, dim, cropped with an ellipsis, the whole text on the status line
   when the cursor's field is cut.
3. **Button bars.** One row of boxed buttons per page, as built for the Set File, Song and clip pages, Down from the last
   field to reach it; a button that can't act is very light grey (but readable on a light background):
   - lists: Open, Preview, New;
   - Song page: Arrange and Export (Export moves here from the main screen, whose Export cell goes; Ctrl+X stays a quiet
     alias off the everywhere keys, 39 A);
   - Set File page: Import, adding songs to the set (moves from the main screen);
   - Scene page: Play scene, Scene View;
   - clip page: one Play/Stop button (26 A), Open pattern (greyed when it can't act);
   - generator editors: Example;
   - Instrument editor: Stop all notes, the usual MIDI panic for stuck notes (all notes off and all sound off, CC 123 and
     CC 120, and note offs, on that instrument's device and channel; only with a MIDI device), and Test (a chromatic run
     halfway between the configured octaves; disabled for a drum instrument for now); the track editor gets Stop all notes
     too.
   Buttons that pick what a page works from use `U` (Use…, 62): the Example's source pattern, the pattern editor's track to
   listen through, the clip page's instrument to listen through.
4. **The actions menu (43 A).** F1 becomes a menu of every action on the page with its key, moved through with the arrows,
   narrowed by typing, Enter doing the action; Tab still turns to the page's description.
5. **`Z` (Size) on every editor of steps (37 A).** The pattern editor's `S` (Size) becomes `Z`, and `Z` sets the count
   directly on the groove, offsets, chords and step-row editors; the groove editor gets a `R` (Reconfigure) menu holding its
   cell length and rename.
6. **The Example inset (31, 32 B).** An Example button, or `P`, on a generator's list or editor opens an Inset Window showing
   a source pattern as written against through the generator, `V` switching, PgUp/PgDn a bar, `-`/`=` zoom, `U` picking the
   source, which is kept as a generator setting (an unknown name dropped silently); "(example pattern)", a scale run, first
   and the default.
7. **List previews.** `P` and Space (42 A) on list pages open a preview, patterns first; the pattern editor's piano roll
    and the preview draw notes outside the scale in a colour nothing else uses (51 C).

8. **The genre library**, whose plan is `dev_notes/GENRE_PLAN.md`: the jazz chord study first (a development downloader, pooled
   statistics, and the chords the tracker cannot yet express), then the learnt tables, then the generator as a script. It is
   what is being worked on now; items 1 to 7, the tracker's interface, stay parked in their order until the user says otherwise.

## Beside the Genre Library

- **A blog post** (the user means to ask): mostly genre detection, what the library can generate, and what Claude does today
  when asked for a homage and which part of that is code in llamatron; transitions a small part, said plainly as they are.
  Nothing overstated.

## Later

- The demos' docs proposals and screenshots for every example on Arrange (SVG, the grid cropped, at most 160 wide and 24
  lines, rebuilt only when examples change).
- Moving `build_docs.sh` and `publish_docs.sh` to a `dev_scripts/` folder (asked, unanswered).
- Ideas to discuss: a crumb symbol for the page's kind; register naming; a tutorial explaining Scene View.

## Last

- The visualizers: fire, aquarium, boxes, a green WarGames-style command centre, and "unix" (a fake prompt, numbered `.llama`
  files and llama folders, nothing real from the computer and no real commands run); the batch recorder reading each song's
  visualizer; a track keeping one colour in the piano roll visualizer (47).
- "Arrange/Perform" as the main screen's Arrange cell while Real Time is on.
- New demos, each with an original melody and chords in the manner of its source, filed by genre, then a rethink of how the
  homage genres are subdivided so that rock isn't too full:
  `hey_claude` (Hey Jude), `crazy_planet` (Gary Jules's "Mad World"), `not_north_song` (Alabama's "Song of the South"),
  `dont_drink` (Alice Cooper's "Poison"), `sometimes_i_feel` (the Allman Brothers Band's "Whipping Post", a heavy intro, a
  short version, with rock), `noisy_bleeps` (IDM after Autechre: plucks, clicks and odd General MIDI sounds, the style looked
  up first), `radio_radio_radio` (Van Morrison's "Caravan"), `not_forgetting_yet` (The Call's "I Still Believe", 1980s, with
  saxophone), `nonlocal_musicians` (Creedence Clearwater Revival's "Travelin' Band", with rock), and in a new metal genre
  `no_madness` (Iron Maiden's "Can I Play with Madness"), `bad_weather` (Deep Purple's "Stormbringer"),
  `ineffective_ranchers` (Pantera's "Cowboys from Hell", in their style); then `low_volume` ("The Sound of Silence"),
  `more_pale` (organ, "A Whiter Shade of Pale"), `want_invisibility` (Rockwell's "Somebody's Watching Me"),
  `listen_to_how_it_goes` (Santana's "Oye Como Va"), `parenthetical` (Sigur Rós's "( )"), `am_destroyed_already`
  (post-rock after This Will Destroy You), `electricity_present` (jazz fusion after Jeff Beck's "Wired"),
  `superman_will_dislike` (3 Doors Down's "Kryptonite"). A hip hop genre comes back later, when the user says what it needs.
- The user's ratings of a handful of demos, aspect by aspect, as ground truth for the genre library, much later, when
  nothing else is next.
- **Organizing `internal_tools/`** (the user's ask, last in the queue): a talk about how the support folder is laid out, now that
  the genre library's tools have their own folder, `internal_tools/analysis_and_generation/`.
