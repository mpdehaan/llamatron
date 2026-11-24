# Sheet Music and Learning Packets

A song made in llamatron can be printed as a learning packet: a PDF that
teaches the song by its melody and its chords, for someone sitting at a piano.
This page covers what a packet holds, how its chords are read, and making one
from the command line. [Exporting](EXPORTING.md) covers Live sets, MIDI files
and WAV audio.

## What a Packet Holds

A packet is one PDF, `<set>_<song>__packet.pdf`, beside the set, of these
pages, in the order a learner reads them:

| Page | What it shows |
| --- | --- |
| Piano roll | The melody as boxes on a lane for each half step, each in its scale degree's colour and named with its letter, over the counting (`1 & 2 &`) and the chords, each with its Roman numeral. Each section starts a row with its name; a section played several times in a row is drawn once, its name saying how many times. Along the foot of every page, the chord changes on it, each chord on a small keyboard, the keys that stay blue and those that move red. |
| Chord changes | Every move from one chord to the next, in the order the song first makes it and with how many times, both chords on keyboards, the second voiced as near the first as it can be, and the same in words: `stay: C`, `move: E→F, G→A`, `add B`, `lift E`. |
| Chord chart | A card for each chord, in the order the song first plays them, with its Roman numerals, how many bars it lasts in the song, and its closest voicing on a keyboard, named as fingering: `C F A, 2nd inversion`. A power chord says `no third`. |
| Chord sequence | The whole song's chords section by section, a cell for each bar, with the key named where it changes and what it is in the song's main key: `Key: F major (IV of C major)`. |

## The Tune and the Chords

A packet reads the song the way a lead sheet is written: one tune, with the
chords under it. You choose which tracks go in, every track with pitched notes
to start with and the drums never, and llamatron merges them into one, played
as they sound after every generator and groove. A piano's right hand often
holds the tune and some of the chords, and its left hand the bass and the rest;
merged, it no longer matters which track holds what.

- **The tune** is the highest note at each moment, each note lasting until the
  next begins. Where the top line drops into a low group of notes while the
  tune rests, such as a bass, that group is left out.
- **The chords** are worked out from all the notes, a bar at a time, or each
  half of a bar of four beats or more where the halves clearly differ: the
  chord whose notes sound longest in the bar wins, with the chords of the key
  preferred, the home chord most and then IV and V, and a chord rooted on the
  bass. A chord is named in the key of the scene playing.

## How the Chords Are Read

The chords are printed at one of three levels:

| Level | What it prints |
| --- | --- |
| Sevenths (the default) | Triads and the seventh chords: 7, maj7, m7, dim7, m7b5. A seventh is printed only where the accompaniment plays it for a good part of the bar, never for the tune's own note or a passing note. |
| Triads | Major, minor and diminished triads. |
| As played | Every beat's chord as heard. |

A bar holding only a root and its fifth, with no third, prints as a power
chord, such as `C5`, at every level.

A chord is numbered in its key by what it does: in C major, D7 is `V7/V` and
F#dim7 `vii°7/V`, chords leading to the chord after the slash, and a chord
borrowed from the minor key is numbered by its root, such as `iv` for Fm.

## Sections

A song whose scenes set their Section, on the Scene page, has a section
wherever the setting changes, named after it. Any other song has a section at
every scene, named after the scene, and a scene played again in a row is
counted rather than printed again.

## From the UI

`Ctrl+X`, then `PDF …`, opens the PDF page for the current song:

- The packet's pages, in two columns, each ticked with `Space` or `ENTER`.
- Chords, the level the chords are printed at: `[` and `]` step it, `ENTER`
  picks.
- Every track in a row with its role, and a dot under IN where it goes into
  the packet, `Space` or `ENTER` to choose; a drums track can't go in.
- The export directory and the file it writes, saying when it replaces one.
- Export and CANCEL.

`Tab` goes to the next part. While Export can't go on, it is dim and the line
above it says why: nothing is
ticked or no track is chosen. The page remembers its choices for each song until
llamatron quits.

## From the Command Line

`user_scripts/export_pdf.sh` makes a song's packet:

```
sh user_scripts/export_pdf.sh examples/by_genre/ragtime/entertainer.yml
sh user_scripts/export_pdf.sh my_song.yml --song chorus_idea --pages piano_roll,chord_chart --chords-level triads
sh user_scripts/export_pdf.sh my_song.yml --tracks lead,piano --output-dir ~/printouts
```

[User Scripts](USER_SCRIPTS.md#export_pdfsh) lists its options.
