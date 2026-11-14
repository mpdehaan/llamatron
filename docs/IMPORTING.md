# Importing

A MIDI file, from a DAW, a website or anywhere else, can become a song of the set, with its tracks, patterns and scenes worked out for you, playing every note the file plays. This page covers the import dialog and what an import makes.

## Starting an Import

`M` on the main screen, or `Enter` on the main screen's Import cell, imports a MIDI file as a new song of the set, named after the file. The file picker starts in your home directory, where `Enter` goes into a folder or picks a `.mid` file. A dialog then says what the file holds, its tracks, bars, time signature, tempo and keys, and asks how to import it.

## Import Settings

| Setting | What it does |
| --- | --- |
| Song name | The file's name, numbered when the set already has a song of that name, such as `entertainer 2`. `Enter` renames it. |
| Longest pattern | 8, 16, 32, 64 or 128 steps, 32 to begin with; `[` and `]` step through them. Longer patterns mean fewer patterns and scenes, while shorter ones are easier to edit. |
| Use unique names | On to begin with, so every pattern the import makes gets a name of its own. When off, a pattern the set already has, the same in every setting but its name, is used rather than making another. `Space` or `Enter` toggles it. |
| Chords | "as chords" puts notes that start and end together, in a chord's shape, on the Chord row; "as extra tracks" gives each such note a track of its own. |
| Import CCs | On to begin with. Each track of the file brings in up to four CCs, one for each of a track's CC lanes: first the mod wheel (CC 1), volume (CC 7) and the sustain pedal (CC 64), in that order and only those the track sends, then the track's other CCs, the most sent first, such as a filter sweep. A sweep comes in as values with Slide on. CCs past the fourth are left out, as is pitch bend, which isn't a CC and which llamatron can't send; the dialog says what was left out. When off, no CC comes in. |
| Step size | "auto", the longest step the file's notes fit, worked out for each pattern, or a fixed size from 1/32 to 1/4 for every pattern. |

The dialog works the import out again whenever a setting changes, so the line under the settings always says how many tracks, patterns and scenes the import will make, and anything it has to change, such as notes moved to the nearest step. When many notes sit a little off the steps, as a swing, a groove or a live performance plays them, the warning says so; the import moves them to the nearest step and makes no groove.

`I`, or `Enter` on Import, imports, and `Esc` or Cancel leaves the set as it was. The new song becomes the current song, and a dialog says what it was imported as, what it holds, and every warning, or "Import complete with no warnings.", with one OK button. `Ctrl+Z` takes the whole import away again.

## What an Import Makes

The song plays every note the file plays, for as long as the file plays it.

- **Scenes** start only where no note is held across, and at each change of key or tempo in the file, with the scene's Scale set to the key, so a theme that returns in another key uses the same pattern. Scenes are named after the bars they play, such as `bars 1-4`.
- **Tracks** come from the file's tracks: drums become a track for each sound, named such as `kick` and `closed hat`; a track that plays both hands splits into its treble and bass; and overlapping notes within a track spread over tracks lettered `a`, `b` and so on.
- **Patterns** are reused: a phrase that returns uses its pattern again, and a bar played several times becomes one pattern with the clip's Repeat set. Patterns are named after their track and numbered, such as `lead 1`.
- **CC values** land on the step at which they are sent. When a recorded sweep's values fall between steps, the patterns take steps short enough to stay within a few values of the file, and the dialog says how many messages fell between steps.

The files in `examples/midi/` are public domain tunes to try the import on.
