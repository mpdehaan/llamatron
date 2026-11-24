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

## The Melody and the Chords

Each track plays one part in the packet: the melody, the chords, or left out.
Several melody tracks are merged into one line, the highest note at each
moment, and several chord tracks are heard together, so that a tune or its
chords passed from one instrument to another across the song still read as
one part. Each track starts in the part its notes play: the most tune-like
line is the melody, chordal tracks are the chords, and the bass, the drums and
the other lines are left out. Where the tune line plays only a few notes, the
highest chord track carries the tune instead, as a pianist's right hand does.

## How the Chords Are Read

The chords are heard from the chord tracks' notes as they play, after every
generator and groove, and printed at one of three levels:

| Level | What it prints |
| --- | --- |
| Sevenths (the default) | Triads and the seventh chords: 7, maj7, m7, dim7, m7b5. A 9th, 11th, 13th or added note is dropped back to its seventh. |
| Triads | Major, minor, diminished and augmented triads, and anything smaller. |
| As played | Every beat's chord as heard. |

At Triads and Sevenths, a chord is heard across a bar in 2/4, 3/4 and 6/8 and
half a bar in 4/4, so that a stride's bass on one beat and its chord on the
next read as one chord; a new root, or the tritone of a dominant arriving,
starts a new chord inside it. A power chord or any other two-note chord stays
as it is at every level, unless the melody sounds its third, when it is named
as that triad. Triads prints no bass after a slash; Sevenths prints one only
where the bass walks by step, or before the chord it leads into, as in
`C/G G7 C`.

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
- Every track in a row with its role, and a dot under MELODY, CHORDS or LEFT
  OUT: `Left` and `Right` choose the column, `Space` or `ENTER` takes it.
- The export directory and the file it writes, saying when it replaces one.
- Export and CANCEL.

`Tab` goes to the next part. Export refuses, saying why, while nothing is
ticked or no track plays a part a page needs, and warns when a drums track is
chosen as chords. The page remembers its choices for each song until
llamatron quits.

## From the Command Line

`user_scripts/export_pdf.sh` makes a song's packet:

```
sh user_scripts/export_pdf.sh examples/by_genre/ragtime/entertainer.yml
sh user_scripts/export_pdf.sh my_song.yml --song chorus_idea --pages piano_roll,chord_chart --chords-level triads
sh user_scripts/export_pdf.sh my_song.yml --melody lead,fiddle --chords piano,guitar --output-dir ~/printouts
```

[User Scripts](USER_SCRIPTS.md#export_pdfsh) lists its options.
