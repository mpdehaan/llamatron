# The llamatron guide

llamatron is a tracker for your terminal. Unlike most trackers, it does not output live music, but aims to output MIDI and Ableton Live sets. 

You write patterns of notes, put them on tracks in scenes, and render the song as an Ableton Live set or a folder of MIDI clips. This guide covers installing llamatron, loading and rendering a song, building a first song step by step, and then every feature of each page.

## Installing

You need Python 3.15 and git. Clone the repository, make a virtual environment inside it, and install llamatron into that environment:

```
git clone https://github.com/mpdehaan/llamatron.git
cd llamatron
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

This installs the `llamatron` command into `.venv/bin`, along with the Live set that renders are built from. `-e` means the command runs the code in the folder you cloned, so a `git pull` updates it without installing again.

To type plain `llamatron` instead of `.venv/bin/llamatron`, activate the environment in each new terminal with `source .venv/bin/activate`. From the project folder, `./llamatron.sh` also works without activating anything.

## Starting

```
llamatron                            # a new, empty song
llamatron examples/retro_chill.yml   # open a song file
```

Run it from the project folder for now. The load page starts in `examples/` when there's one in the current folder, and saves and renders go into `songs/` and `output/` there.

The terminal needs to be at least 80 by 24. llamatron draws with only bold, dim, reverse video and box characters, so it suits any colour scheme.

## Finding your way around

Every screen is laid out the same way:

- **Top line:** where you are, like `llamatron › PATTERNS › lead`, followed by how long the song, scene, clip or pattern you're looking at lasts, the song's name and `● unsaved` if there are changes to save.
- **Middle:** the page itself, with the selected item in reverse video.
- **Status line:** messages, such as what was just saved, or why a key did nothing.
- **Bottom:** every key that works right now, each shown as a reversed label. The keys change with what's under the cursor, and a key that isn't shown does nothing.

A few rules hold everywhere:

- `H` shows help for the page you're on.
- `Tab` goes back. It never quits.
- `Q` quits, from the main screen only, and asks first if there are unsaved changes.
- Upper and lower case are the same key.
- `Bksp` and `Delete` are the same key.
- Nothing is saved or rendered until you ask on the Song page.

Lists work the same way on every page. Up and down select, and a list you can add to has a `+` row at the bottom, where `Enter` adds, the same as pressing `+`. Deleting something that's still in use is refused, with a list of what uses it. Otherwise it asks first.

Settings pages also work the same way. Up and down select a setting, left and right or `+` and `-` change it, `Enter` types a value or opens a list to choose from, and `Bksp` clears it where that makes sense.

Dialogs show their own keys:

- **Lists:** `Enter` chooses and `Tab` cancels.
- **Text:** type, `Bksp` erases, `Enter` finishes and `Tab` cancels.
- **Questions:** `Y` is yes, and `N` or `Tab` is no.

### The main screen

The main screen shows the song's name, length, tempo and scale, and how many patterns, tracks and scenes it has. Each letter opens a page:

| Key | Page | What it's for |
| --- | --- | --- |
| `S` | Song | Tempo, scale, seed and defaults, plus load, save and render |
| `P` | Patterns | The notes, in a grid of steps |
| `T` | Tracks | The columns of the song |
| `C` | Chains | Lists of generators that clips can use |
| `G` | Generators | Arpeggiators and AutoRatchets |
| `Z` | Scales | The named scales that the song and its scenes use |
| `A` | Arrange | Scenes and clips, in the order they play |
| `Q` | Quit | Asks first if there are unsaved changes |

## Loading, saving and rendering

All of this is on the Song page, so press `S` from the main screen.

- **`L` loads** a song file. It starts in `examples/`, where `Enter` opens a file or goes into a folder, and `../` goes up a folder.
- **`N` starts** a new song.
- **`S` saves** the song. If it hasn't been saved before, it asks for a file name first, starting from `songs/untitled.yml`, and adds `.yml` if you leave it off. Folders are made as needed.
- **`W` saves** under a new name, and asks before replacing another file.
- **`R` renders** an Ableton Live set to `output/<song name>/<song name>.als`.
- **`M` renders** a clip tree: one MIDI file per clip, in `output/<song name>/`, named by scene, track and pattern.

Loading or starting a new song asks first if there are unsaved changes.

The song name is the file name without `.yml`, so an unsaved song renders to `output/untitled/`. A render asks before replacing an earlier one, and replacing it loses anything you saved over that set in Live. To keep work you've done in Live, save it under another name in Live.

In Live, each llamatron track is a MIDI track with its clips in Session View, and the scenes are also laid end to end in Arrangement View. Scenes keep their names, and each clip is named after the pattern it plays. The tracks have no instruments, so drop one onto each track to hear it.

### From the command line

`--to` renders a song without opening the tracker:

```
llamatron examples/minimal_techno.yml --to ableton
llamatron examples/minimal_techno.yml --to cliptree --out output/my_song
llamatron examples/minimal_techno.yml --to ableton --replace
```

- **`--out`** picks the folder to write to. The default is `output/<song name>`.
- **`--replace`** removes that song's earlier render first, so you can render again and listen.
- **`--template`** picks a different Live set to build from.

These three only work with `--to`. `./run_examples.sh` renders every song in `examples/` as a Live set, replacing earlier renders.

Cliptree is intended for DAWS other than Ableton Live.  This project was made with Ableton 12.3, so any future version should theoretically work with the Ableton export modes.

## Making a first song

This builds a short song with a melody and a kick drum. The order matters a little, because a clip needs a pattern and a track to exist before it can be added.

### 1. Check the song settings

Start `llamatron` with no song, then press `S`. A new song is 120 BPM in C major. Change the tempo with left and right, or press `Enter` and type a number. Leave everything else alone for now, and press `Tab` to go back.

### 2. Write a melody pattern

Press `P` for Patterns, then `+`, and call the pattern `lead`. The pattern editor opens with 16 empty steps, each as long as the song's step size, a 1/16 note.

The cursor starts on the Degree row of step 1. Degrees are notes of the scale, so in C major 1 is C, 2 is D, 3 is E, and so on up to 7. To write a melody:

1. Type `3`, then press right, type `2`, press right, type `1`, press right, type `2`.
2. Typing never moves the cursor, so you always press right yourself. A step with no degree is a rest, and shows as a blank.
3. `Bksp` on a degree turns it back into a rest.

Every step lasts the same time, the pattern's step size, so each note starts where its step is. To make a note sound longer, press down to the Gate row and use `+` and `-` to step through lengths, or `*` to double and `/` to halve. A gate can be longer than its step, so a note can ring on while the next steps play, up to the end of the pattern. A blank gate lasts one step. The line under the grid shows the note the cursor is on, like `Step 1: E3 in C Major, gate 1/16`.

Press `Tab` to go back to the list. It shows how long the pattern lasts.

### 3. Write a drum pattern

Press `+` again and call this one `kick`. Press `T` to make it a drum pattern. The top row is now called Note, and takes note letters instead of degrees, because drums don't follow a scale.

Type `C` on steps 1, 5, 9 and 13. A new drum note goes in octave 1, so C is C1 (MIDI 36), which is the first pad of a Drum Rack in Live. Press `Tab` twice to get back to the main screen.

### 4. Add tracks

Press `T` for Tracks, then `+`, and call it `lead`. Add another called `drums`. These become the tracks in Live, in the order listed. Press `Tab`.

### 5. Arrange a scene

Press `A` for Arrange. Scenes are rows and tracks are columns, and a `+` is an empty cell where a clip can go.

1. Press `Enter` on the `+` at the bottom to add a scene.
2. Press right to move onto the scene's `lead` cell, and press `Enter`. Choose `lead`. The clip page opens.
3. Set Repeat to 4 with right or `+`, so the melody plays four times. Press `Tab`.
4. Press right to move onto the `drums` cell, press `Enter` and choose `kick`. Select Loop and press `Enter` to turn it on, so the kick keeps playing for as long as the melody does. Press `Tab`.

A scene lasts as long as its longest clip that doesn't loop, so at least one clip in every scene must not loop. The grid marks the clips, so `lead ×4` repeats and `kick ∞` loops, and the line at the bottom shows how long the clip and the scene last.

To add a second section, press `C` on the scene's name to copy the scene, then change its clips.

### 6. Save and render

Press `Tab`, then `S` for the Song page. Press `S` to save, and type a name like `songs/first.yml`. Press `R` to render a Live set, then open `output/first/first.als` in Live, and put an instrument on each track.

## Every page in detail

### Song

Press `S` from the main screen.

| Setting | What it does |
| --- | --- |
| Title | The song's name, for anyone reading or sharing the file, such as in git. It doesn't change how the song plays, and `Bksp` clears it. |
| Author | Who wrote it, also just for people reading the file |
| Tempo | Beats per minute for the whole song, from 10 to 999. A scene can set its own. |
| Scale | The song's scale, from the Scales page. A scene can use another. `Bksp` sets no scale, and then patterns with degrees can't render. |
| Seed | Decides every random choice, so a song renders the same every time: which notes probability drops, random play directions and random arpeggiators. Change it for a different take. |
| Step size | How long each step of a pattern is, unless the pattern sets its own, from 1/64 to a whole note. `Enter` chooses from the list. A pattern's own step size is set in the pattern editor with `E`. |
| Default octave | The octave a new note gets, numbered as Live numbers them. |
| Default drum octave | The octave a new drum note gets. |

The keys `L`, `N`, `S`, `W`, `R` and `M` are under [Loading, saving and rendering](#loading-saving-and-rendering).

#### Description

Press `D` on the Song page. The description is notes about the song, as long as you like, for anyone reading or sharing its file, such as what each scene is for or what to try. It doesn't change how the song plays. The Song page shows how many lines it has, and the description is saved at the top of the song file, where it reads as plain text.

The page opens for reading, and `↑` and `↓` scroll it. `E` starts editing: typing adds text at the cursor, `Enter` starts a new line, `Bksp` erases, and the arrows move the cursor. While you're editing, letters are text, so `H` types an h. `Tab` stops editing, and `Tab` again goes back. `Bksp`, while reading, clears the whole description after asking.

Octaves go from -2 to 8 and are numbered the way Live labels notes, so degree 1 of C major in octave 3 is middle C (C3, MIDI 60).

### Scales

Press `Z` from the main screen. A scale has a name and is a root note with a kind. A new song has one called `C Major`.

The name can be anything, which is the point. Call a scale `main` and use it everywhere, and changing what `main` is later moves the whole song into the new key. The song chooses a scale, and each scene can choose another one. A clip uses its scene's scale, or else the song's.

| Key | What it does |
| --- | --- |
| `+` | Add a scale: choose a root, then a kind, then a name |
| `Enter` | Change the root and kind |
| `N` | Rename it, which updates the song and every scene that uses it |
| `C` | Copy it |
| `U` / `D` | Move it up or down the list |
| `Bksp` | Delete it, once nothing uses it. To delete the song's scale, clear it on the Song page first. |

The root is chosen on a keyboard, with each flat under the sharp it shares a key with:

```
 C   C#   D   D#   E   F   F#   G   G#   A   A#   B
     Db       Eb           Gb       Ab       Bb
```

Left and right move along the keys, and up and down switch between a sharp and its flat. A scale rooted on a flat spells its notes with flats, and any other root spells them with sharps.

The kind is then chosen from two pages. The line underneath shows the notes of the one under the cursor, like `D dorian: D E F G A B C`. Up and down move within a column, and left and right move to the next column.

The top line names both pages, with the one you're on highlighted, and shows `PgDn ▸` when there's a page after it or `◂ PgUp` when there's one before. `PgDn` and `PgUp` change page, and so do left and right past the edge of a page. Neither goes round from the last page to the first. The picker opens on the page holding the scale's current kind.

**Common**

| Group | Kinds |
| --- | --- |
| Modes | major, ionian, dorian, phrygian, lydian, mixolydian, minor, aeolian, natural minor, locrian |
| Minor & major | harmonic minor, melodic minor, harmonic major |
| Symmetric | chromatic, whole tone, whole half dim, half whole dim, augmented |
| Pentatonic & blues | major pentatonic, minor pentatonic, blues, major blues, egyptian |

**Jazz & world**

| Group | Kinds |
| --- | --- |
| Melodic minor | melodic minor, dorian flat2, lydian augmented, lydian dom, mixolydian flat6, locrian natural2, altered |
| Jazz | bebop dom, bebop major, prometheus |
| Middle East & Europe | phrygian dom, double harmonic, hungarian minor, hungarian major, ukrainian dorian, persian, neapolitan minor, neapolitan major, enigmatic |
| East Asia | hirajoshi, in sen, iwato, kumoi, yo, ryukyu |
| India | todi, marwa, purvi |

Ionian is the same scale as major, and aeolian and natural minor are the same as minor. Melodic minor is on both pages, the second time leading its modes, which spell out flat and natural: dorian flat2 is dorian ♭2. Ryukyu is the Okinawan scale. The ragas are their twelve-note versions. The picker shortens "diminished" to "dim" and "dominant" to "dom" to fit, but song files keep the full names, like `whole_half_diminished`.

The list shows each scale's notes, how many there are and how many things use it.

### Patterns

Press `P` from the main screen. Patterns hold the notes. The list shows each one's type (notes or drum), its step count, how long one play lasts at the song tempo, and how many clips use it.

| Key | What it does |
| --- | --- |
| `+` | Add a pattern and open it |
| `Enter` | Edit the selected pattern |
| `N` | Rename it, which updates every clip that uses it |
| `C` | Copy it |
| `U` / `D` | Move it |
| `S` | Sort the list by name |
| `Bksp` | Delete it, once nothing uses it |

#### The pattern editor

Each column is a step and each row is one kind of value. The grid is as wide as the pattern's step count, and wraps onto more blocks when the screen is narrow. Typing never moves the cursor and never grows the grid, so you always move with the arrow keys, which wrap around at the edges.

When typing numbers, digits build up in a cell, so `1` then `2` makes 12. A new number starts once you move the cursor, or when the next digit would go out of range.

A step with no degree or note is empty, which is a rest, and the rows below it are blank for that step. Every step lasts the pattern's step size, shown at the top with the number of steps. A step with a note sounds for its gate, which can run on past later steps but stops at the end of the pattern, and a new note gets the song's default octave and a blank gate, which lasts one step.

The keys that work everywhere in the editor are:

| Key | What it does |
| --- | --- |
| Arrows | Move |
| `A` | Step the rows under Degree through normal, advanced and CC rows |
| `F` | Flip: reverse every step after the cursor |
| `S` | Swap what's before the cursor with what's after it |
| `L` | Load a copy of another pattern over this one, asking first if this one has notes |
| `R` | Resize the pattern to a number of steps, from 1 to 4096. It asks first if steps with something in them would be cut. |
| `E` | The pattern's own step size, typed as a whole number or a fraction like 1/8. Leave it blank to use the song's. |
| `T` | Drum on or off. Notes and drums use different values, so changing it clears the notes, after asking. |
| `P` | The play direction |
| `I` | Insert an empty step before the step at the cursor |
| `X` | Remove the step at the cursor, while there's more than one |
| `N` | Rename the pattern |
| `M` | The add limit for Note Add and Velocity Add. Advanced rows only. |
| `Tab` | Back |

The cursor stays on its step after `F` and `S`, so pressing either again undoes it. On a drum pattern's Note row, `A` and `F` type the notes A and F, so move to another row to use them as commands.

#### Normal rows

| Row | Values | Keys |
| --- | --- | --- |
| Degree | 1 up to the size of the scale, where 1 is the root | Digits, `+` `-`, `Bksp` empties the step |
| Note (drum patterns) | A to G | Letters, `Bksp` empties the step |
| Gate | How long the note sounds, in whole notes, like 1/16 or 5/16. Blank is one step. | `+` `-` step through 1/64, 1/32, 1/16, 1/8, 1/4, 1/2, 1, 2 and 4. `*` doubles, `/` halves, `Enter` types a whole number or a fraction, and `Bksp` makes it one step. |
| Dot | `d` makes the gate dotted, half as long again, and `t` makes it a triplet, two thirds as long, so 1/16 with `d` is 3/32 | `Space` or `+` goes to the next one, `-` back, `Bksp` clears |
| #/b | Sharp or flat: moves the note a half step up or down | `Space` or `+` goes to the next one, `-` back, `Bksp` clears |
| Octave | -2 to 8, as Live numbers them | Digits, `+` `-`, `Bksp` sets the default |
| Chord | Builds a chord on the note | `Enter` to choose, `Space` or `+` goes to the next one, `-` back, `Bksp` clears |
| Velocity | 1 to 127, default 127 | Digits, `+` `-`, `Enter` to type, `Bksp` sets the default |
| Prob | Chance of playing, 0 to 100, default 100 | Digits, `+` `-`, `Enter` to type, `Bksp` sets the default |
| Glide | `*` makes the note run slightly into the next one, which a synth with glide turned on slides across. A blank is off. | `Space` toggles, `Bksp` turns it off |

The highest degree you can type is the size of the largest scale the pattern plays in. If a scene uses a smaller scale, a degree past its top wraps up an octave.

Glide does nothing before a rest or before the same pitch. Probability is rolled when you render, using the song's seed, once for each repeat and each ratchet slice. A render plays the same every time until you change the seed.

`Enter` on the Chord row opens every chord at once, with `(none)` at the top and a column for each family: triads (with the sixths), sevenths, ninths, elevenths and thirteenths, and scale chords. The rows line up, so the first three of each family are dominant, major and minor. Up and down move within a column, and up from the top reaches `(none)`. Left and right move to the next column. The line underneath names the selected chord, `Enter` chooses it and `Tab` cancels. `+` and `-` step through the same chords, going down each column in turn.

There are two kinds of chord.

**Named chords** are built in exact half steps up from the note, ignoring the scale, so they can play notes outside it. In C major, `M` on degree 3 is E major, which includes G#. The notes shown are on C:

| Chord | What it builds | On C |
| --- | --- | --- |
| `M` | Major | C E G |
| `m` | Minor | C E♭ G |
| `dim` | Diminished | C E♭ G♭ |
| `aug` | Augmented | C E G♯ |
| `sus2` | Suspended second | C D G |
| `sus4` | Suspended fourth | C F G |
| `pow` | Power chord | C G |
| `M6` | Major sixth | C E G A |
| `m6` | Minor sixth | C E♭ G A |
| `dom7` | Dominant seventh | C E G B♭ |
| `M7` | Major seventh | C E G B |
| `m7` | Minor seventh | C E♭ G B♭ |
| `mM7` | Minor-major seventh | C E♭ G B |
| `dim7` | Diminished seventh | C E♭ G♭ A |
| `m7b5` | Half-diminished | C E♭ G♭ B♭ |
| `aug7` | Augmented seventh | C E G♯ B♭ |
| `augM7` | Augmented major seventh | C E G♯ B |
| `7sus4` | Seventh, suspended fourth | C F G B♭ |
| `dom9` | Dominant ninth | C E G B♭ D |
| `M9` | Major ninth | C E G B D |
| `m9` | Minor ninth | C E♭ G B♭ D |
| `add9` | Added ninth | C E G D |
| `madd9` | Minor added ninth | C E♭ G D |
| `dom11` | Dominant eleventh | C E G B♭ D F |
| `M11` | Major eleventh | C E G B D F |
| `m11` | Minor eleventh | C E♭ G B♭ D F |
| `dom13` | Dominant thirteenth | C E G B♭ D F A |
| `M13` | Major thirteenth | C E G B D F A |
| `m13` | Minor thirteenth | C E♭ G B♭ D F A |

**Scale chords** are the plain numbers. They stack every other note of the scale, so they use only notes in it. The scale decides whether each one is major, minor or diminished, and they change when the scale does. The notes shown are on degree 1 of C major:

| Chord | What it builds | On degree 1 of C major |
| --- | --- | --- |
| `5` | Root and fifth | C G |
| `3` | Triad | C E G |
| `7` | Seventh | C E G B |
| `9` | Ninth | C E G B D |
| `11` | Eleventh | C E G B D F |
| `13` | Thirteenth | C E G B D F A |

In C major, `3` on degree 2 is D minor, and `5` on degree 7 is B and F, a diminished fifth. A `13` uses every note of a seven-note scale. In pentatonic, blues and other scales without seven notes, every other note isn't a third, so scale chords sound less like their names. A plain number always means a scale chord, which is why the named dominant chords are `dom7` to `dom13`.

Drum patterns have no Chord row.

#### Advanced rows

Press `A` to see these instead of the normal rows, and again for the CC rows. Degree stays at the top of every set, and the editor remembers which rows you were on as you move between patterns. The header shows the source pattern and the add limit.

| Row | Values | What it does |
| --- | --- | --- |
| Ratchet | 1 to 16 | Splits the step into that many equal notes in the same time |
| Ratchet Offset | -24 to 24 | Moves each ratchet note that much further along the scale than the last one. In a drum pattern it moves by half steps instead. |
| Note Add | -24 to 24 | Adds to a running total that moves notes along the scale |
| Velocity Add | -127 to 127 | Adds to a running total of velocity |
| Grab | `*` or blank | Plays the note that the clip's Grab track most recently played instead of this step's own, or the lowest note of a chord |

Unset values show a dot. The number rows take digits, `+` and `-`, or `Enter` to type, and `Bksp` sets them back. Grab is toggled with `Space`.

Note Add and Velocity Add work like the accumulators on a Sequentix Cirklon:

- Each total starts at zero when a clip starts.
- A total applies from the step that adds to it onwards, and carries on across repeats.
- A total clears once it goes past the pattern's add limit in either direction. The limit defaults to 36, and `M` changes it.
- Velocity stays between 1 and 127.
- A note pushed out of the MIDI range moves to the nearest octave that fits.

Grab works like the Cirklon's note grab, taking notes from the track that each clip names in Grab track. See [Clips](#clips) for how it works.

#### CC rows

Press `A` twice from the normal rows to see these. They send MIDI CC values, like the Cirklon's aux rows, and each track decides which CC number each row sends, so the same pattern can move different controls on different tracks.

| Row | Values | What it does |
| --- | --- | --- |
| CC 1 to CC 4 | 0 to 127 | Sends that value at the start of the step. A dot sends nothing, so the last value holds. |
| Slide | `*` or blank | Ramps each of this step's CC values to that row's next value, instead of jumping, like slide on an Elektron Monomachine |

CC rows and Slide can be set on a rest, so a sweep can carry on through silence. The number rows take digits, `+` and `-`, or `Enter` to type, and `Bksp` clears them. A ratchet doesn't repeat the values, and probability doesn't drop them. With Rhythm from, the CC rows come from the rhythm pattern.

In a Live set, each CC becomes a clip envelope, and Live draws a slide as a straight line. In MIDI files, a slide is sent as a new value every 1/64 note.

#### Play directions

`P` sets the order the steps play in. Names follow the Cirklon.

| Direction | Order |
| --- | --- |
| forward | First step to last |
| reverse a | Step 1, then backward from the last |
| reverse b | Last step to first |
| alternate | Forward, then reverse |
| pendulum | Forward and back without repeating the ends |
| random | Any step |
| brownian | On 50% of the time, back 25%, stay 25% |
| eitherway | On or back, 50% each |

Whatever the direction, one pass through a pattern lasts as long as playing it forward does, with the last step cut to fit. A direction can't change how long a clip or scene is.

Positions carry on across repeats. The random directions use the song's seed, kept separate from the one probability uses, so changing a direction never changes which notes probability drops. A clip can override the direction.

### Tracks

Press `T` from the main screen. Tracks are the columns on the Arrange page, and become tracks in Live in the same order. The list shows each track's type, whether it's muted, its transpose, its CC numbers and how many clips it has.

| Key | What it does |
| --- | --- |
| `+` | Add a track |
| `Enter` | Open its settings |
| `N` | Rename it, which updates every scene |
| `C` | Copy it along with all its clips |
| `U` / `D` | Move it |
| `Bksp` | Delete it and its clips, after asking |

A track's settings apply to every clip on it:

| Setting | What it does |
| --- | --- |
| Drum | `*` marks a drum track, which is never transposed. `Enter` toggles it. |
| Mute | `*` makes the track start switched off in Live, so it's silent until you switch it on. Its clips are still written, so you can switch it on to hear them, and other tracks can still grab notes from it. It's meant for tracks that only feed grabs. `Enter` toggles it. |
| Transpose | Moves every note on the track along the scale when rendering, from -24 to 24, without changing its patterns. In a seven-note scale, 7 is an octave. Drum patterns are never transposed, on any track. |
| CC 1 to CC 4 | The CC number that each of a pattern's CC rows sends on this track, from 0 to 127. `Bksp` sets none, so that row sends nothing here. CC 1 is usually the mod wheel and CC 74 the filter cutoff. |

### Generators

Press `G` from the main screen, then `Enter` on Arpeggiators or AutoRatchets. A generator changes a clip's notes when you render. To use one, add it to a chain, then choose the chain on a clip.

Both lists use the same keys:

| Key | What it does |
| --- | --- |
| `+` | Add one |
| `Enter` | Edit its settings |
| `N` | Rename it, which updates every chain |
| `C` | Copy it |
| `U` / `D` | Move it |
| `Bksp` | Delete it, once no chain uses it |

#### Arpeggiators

An arpeggiator plays each chord one note at a time, and keeps going for as long as the chord lasts. Rests pass through unchanged. Single notes do too, unless the arpeggiator has offsets or an octave range, which lets one note make a melody.

| Setting | What it does |
| --- | --- |
| Step | How long each note of the chord plays, from 1/256 to a whole note |
| Order | `up` or `down` by pitch, `up_down`, `down_up`, or `random` |
| Octave range | Plays the chord again in up to 4 octaves, from 1, which is just the chord |
| Octave jump | `after chord` plays the whole chord before moving up an octave, so C E G becomes C E G C E G. `after each note` plays each note in every octave first, so it becomes C C E E G G. |
| Offsets | The arpeggiator's own steps, like the Elektron Monomachine's. `Enter` edits them, and `Bksp` removes them. |
| Seed | The seed for `random`. `Bksp` goes back to the song's seed. |

Offsets are a row of 1 to 16 steps, and the first edit starts them with 8 steps of 0. Each step plays the next note of the chord, moved that many notes along the scale, or by half steps when there's no scale. A blank step is silent, and the next step plays the note it would have played. The steps start again with each chord, so a length that doesn't fit the chord makes a new rhythm against it.

In the offsets editor, left and right move, digits type an offset, `+` and `-` change it, and `Space` makes a step silent or plays it again. `I` inserts a step and `X` removes one.

#### AutoRatchets

An AutoRatchet chops each note or chord into quick equal repeats in the same time. It works through a repeating list of counts, so `1 1 4` leaves two notes alone and then chops the third into four. Rests don't use up a count.

Press `Enter` on Counts and type whole numbers of 1 or more, with spaces between them. A new AutoRatchet starts with `2`.

### Chains

Press `C` from the main screen. A chain is a list of generators that run on a clip when it renders, from top to bottom, each working on what the last one made. A clip chooses one chain.

The chain list:

| Key | What it does |
| --- | --- |
| `+` | Add a chain |
| `Enter` | Edit its steps |
| `N` | Rename it, which updates every clip |
| `C` | Copy it |
| `U` / `D` | Move it |
| `Bksp` | Delete it, once no clip uses it |

Inside a chain:

| Key | What it does |
| --- | --- |
| `+` | Add a step: an arpeggiator or AutoRatchet, made first on the Generators page |
| `Enter` | Change the step to another generator |
| `C` | Copy the step |
| `U` / `D` | Move it |
| `Bksp` | Remove it |

Order matters. An AutoRatchet before an arpeggiator ratchets the chords and then arpeggiates the repeats, while the other way round ratchets each arpeggiated note.

### Arrange

Press `A` from the main screen. Scenes are the rows and tracks are the columns. The first column holds the scene names, with each scene's repeat count and length. Scenes play from top to bottom, and a `+` is an empty cell. Arrows move around the grid, and it scrolls when there are more tracks than fit.

The keys depend on what's under the cursor:

| Where | Key | What it does |
| --- | --- | --- |
| Anywhere | `+` | Add a scene below the selected one |
| The `+` row at the bottom | `Enter` | Add a scene at the end |
| A scene's name | `Enter` | Open the scene's settings |
| A scene's name | `C` | Copy the scene and all its clips |
| A scene's name | `Bksp` | Delete the scene and its clips, after asking |
| An empty cell | `Enter` | Choose a pattern, add a clip and open it |
| A clip | `Enter` | Edit the clip |
| A clip | `C` | Copy the clip |
| A clip | `Bksp` | Delete the clip, after asking |
| A cell, after copying a clip | `V` | Paste the copied clip here, replacing what's there |
| A scene or cell | `U` / `D` | Move the selected scene up or down |

Marks after a clip's pattern name show its settings:

| Mark | Meaning |
| --- | --- |
| `×3` | Repeats 3 times |
| `∞` | Loops |
| `~` | Morphs to another pattern |
| `d` | Has its own play direction |
| `r` | Takes its rhythm from another pattern |
| `g` | Grabs notes from another track |

The line at the bottom shows how long the selected clip and scene last, and anything that would stop the scene rendering.

#### Scenes

A scene starts all of its clips together, and lasts as long as its longest clip that doesn't loop, times its repeats. It has no length of its own.

| Setting | What it does |
| --- | --- |
| Name | What it's called |
| Scale | A scale for its clips instead of the song's. `Bksp` goes back to the song's. |
| Tempo | A tempo instead of the song's. `Bksp` goes back to the song's. |
| Tempo ramps to | Moves the tempo from Tempo to this across the scene's repeats. `Bksp` turns the ramp off. |
| Repeat | Plays the whole scene this many times |

The page shows how long the scene lasts and any problem, such as every clip looping.

#### Clips

A clip is one pattern on one track in one scene.

| Setting | What it does |
| --- | --- |
| Pattern | The pattern it plays |
| Chain | Generators to run on it when rendering. `Bksp` sets none. |
| Repeat | How many times it plays, before staying silent while the scene's other clips finish |
| Loop | Plays until the scene's longest clip that doesn't loop is done. `Enter` toggles it. |
| Direction | Overrides the play direction of its patterns. `Bksp` goes back to the patterns' own. |
| Morph to | With Repeat above 1, a second pattern to change into across the repeats |
| Morph direction | `left`, `right` or `middle`: where the change sweeps in from |
| Rhythm from | Another pattern to take the rhythm from, while Pattern gives the notes |
| Grab track | Another track in this scene, whose notes Pattern's Grab steps play. `Bksp` sets none. |

Morph to and Morph direction only appear when Repeat is above 1, and setting Repeat back to 1 removes the morph. The pattern being morphed to is looped or cut to the clip's length, and is played as written.

Rhythm from combines two patterns step by step:

- **The rhythm** gives the step size, Gate and Dot, which steps are rests, Velocity, Prob, Ratchet, Glide and the CC rows, and decides how long the clip is.
- **The clip's Pattern** gives Degree, #/b, Octave and Chord.
- **Each step** of the rhythm that isn't a rest plays the next note, and rests in the notes are skipped.
- **The notes carry on** across repeats and loops, so a five-note melody over a four-step rhythm drifts against it on purpose.

Grab track works like the Cirklon's note grab, and only changes the steps that Grab marks in the advanced rows. Each marked step plays the note that the other track most recently started, at or before that moment: the note it's playing, or the last note it played if it's silent. If it hasn't played anything yet, the step keeps its own note. If the other track played a chord, the step takes its lowest note, and a grab step never plays a chord of its own, even if its Chord row has one. It hears the other track after its chain, so grabbing from an arpeggiated track takes the arpeggio's notes. Every other step, and everything else about the clip, such as its rhythm and velocity, stays its own. This track's transpose still applies.

Because it's set on the clip, one pattern can grab from different tracks in different clips. A clip can grab from a track that grabs from another, but not in a circle. The clip page refuses a grab that would go round in a circle, and says which clips to change, and pasting a clip drops a grab that would. A song file with a circle stops rendering with a message naming the tracks.

A clip's Direction also applies to its rhythm pattern, but not to a morph's target, which plays as written and doesn't grab.

## Song files

Songs are saved as YAML, and each file records the version of llamatron that saved it, which the top of every page shows too. The format is mainly for llamatron to read, but it stays readable so that songs can be compared in version control, and the files in `examples/` show every part of it. The songs in `examples/` whose names end in `_demo` each show one feature, a scene at a time, and `examples/DEMOS.md` describes them. Every setting has a default, so a file can leave out anything it doesn't need, and a file written by an older version still loads. Patterns are stored the way the editor shows them, with one list per row, so a change in the tracker makes a small change to the file.
