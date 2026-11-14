# Patterns

A pattern is a row of steps that clips play, written once and shared. This page covers the Patterns page and the pattern editor, with its piano roll and its rows.

![The Patterns page](screenshots/patterns.svg)

## Patterns Page

Patterns hold the notes, and belong to the set, so every song can play them. Press `P` on the main screen to open the Patterns page. The list shows each pattern's type, notes or drums, its number of steps, how long one play lasts at the current song's tempo, and how many clips use it in every song.

| Key | What it does |
| --- | --- |
| `A` | Adds a pattern and opens it. A new pattern starts one bar long in the current song's time signature at the set's step size: 16 steps in 4/4 at 1/16, 12 in 3/4 or 6/8, or 16 when a bar isn't a whole number of steps. |
| `Enter` | Edits the selected pattern. |
| `N` | Renames the pattern, updating every clip that uses it. |
| `C` | Copies the pattern. |
| `M` | Picks the pattern up: `↑↓` carry it, and `Enter` drops it. |
| `S` | Sorts the list by name. |
| `Bksp` | Deletes the pattern, once nothing uses it. |

## Piano Roll

![The piano roll, on a bass pattern](screenshots/pattern_editor.svg)

A pattern that isn't a drum pattern opens on its piano roll. Each column is a step, and each row is one note of the scale, highest at the top, labelled with the note and its octave in the Set File page's octave labels and then the degree, such as `E3   3`. A rule runs across the grid where each octave starts. When the pattern plays under more than one scale, the rows are labelled with the octave and degree alone, such as `oct3  3`, and the header says so.

### Drawing

A note is a bar that fills its cell. A note held over several steps is one unbroken bar running through the dividers, while two notes back to back keep the divider between them, so `█████│█████` is two notes and `███████████` is one held note. A note shorter than a step, from an entry size such as 1/32 on sixteenth steps or a short gate typed on the rows, fills only part of its cell, `███  `, as near as five columns can show, and a gate of a step and a half fills a cell and a half, so the bar ends where the sound does.

A sharp or flat has a row of its own between the two degrees it falls between, labelled dim with the note alone, such as `D#3`. The row appears while a note, or a chord's note, of the pattern is on it, and disappears when the last one goes, so a pattern that stays in its scale shows only the scale, and the cursor can reach a pitch outside the scale only where a note already has one.

A note that grabs its pitch from the clip's Grab track shows a `G` inside its bar in reverse video, `▓▓G▓▓`. The `G` is all the roll shows of such a note: a chord on a grabbing note has no thin lines, and the line describing the step says `the grabbed note`, because what is grabbed depends on the other track and isn't known until the song plays.

The cursor's cell stands between two bold double bars, `║▓▓▓▓▓║`, shaded on a note and a reversed blank on an empty cell. The rows outside the octaves of the one track that plays the pattern are dim and marked off with dots. The roll scrolls up and down through the octaves to keep the cursor on screen, and sideways as the rows do.

The two lines over the grid show the pattern's settings in aligned columns: Steps, Step size, Drum and Direction, and under them Time, Scale and Entry, the entry size, which is how long a note `Space` draws lasts; `(song's)` marks a value the pattern takes from the song. The labels down the left take the same width in both views, so the step columns stay in place when `Tab` switches views.

### The Pencil

The roll is one pencil. `Space`, or `Enter`, draws a note of the entry size at the cursor, writing the note on its step and a tie on each further step it covers, so the rows show exactly what was painted; only an entry size shorter than a step writes a gate. `Space` on a note at the cursor's pitch erases that note with every step it holds, from any of the note's cells, exactly as `Bksp` does, so `Space` turns a note on and off. A note drawn again is a new note of the entry size, and `Ctrl+Z` brings back an erased note.

A note drawn at another pitch inside a held note cuts the held note where the new one starts, and the rest of the old note carries on after the new one as a note of its own, so drawing never silences anything to the right. A note whose gate reached over the new note's step is cut to end where the new note starts, and a note running past the end of the pattern is cut there.

### Piano Roll Keys

| Key | What it does |
| --- | --- |
| Arrows | Move along the steps, and up and down a note of the scale, stopping at the edges. |
| `Home`, `End` | Go to the first and last step. |
| `Space`, `Enter` | Draw a note of the entry size at the cursor, or erase the note under the cursor. |
| `H` | Picks the chord of the note under the cursor, from any of its cells, with `(none)` at the top to make it a single note again. A chord's other notes are drawn as thin dim lines on their own rows, as long as the note, and follow the note rather than being edited on their own. |
| `[` (shrink), `]` (stretch) | Drag the end of the note under the cursor a step earlier or later, from any of its cells. A note shorter than a step becomes a whole step first, and the drag stops at one step and at the next note on the row. On a note whose length is a gate, stretching adds a tie after the gate's reach. |
| `K` | The knife: splits the held note under the cursor at the cursor's step, so the rest of the note is a note of its own at the same pitch. |
| `.` | Cycles the note under the cursor through sharp, flat and natural. The note moves to the row that sounds it, a row of its own between two degrees, and the cursor follows. |
| `Bksp` | Takes out the note under the cursor, with the steps it held. |
| `G` | Marks the note under the cursor to grab its pitch from the clip's Grab track, or unmarks it. |
| `E` | Picks the entry size from a list: the song's, or one of the step sizes from 1/64 to a whole note. The entry size is the pattern's own setting, and the Song page's Entry size is what a pattern starts with. |
| `Tab` | Switches to the rows, and back. The pattern editor opens in the view you left it in. |

The legend under the roll keeps to drawing, while `K` and `G` still work there; `F1` lists them. The keys that work on the whole pattern, `S` and `R`, described under Editor Keys below, work on the roll too. Steps are inserted and removed in the rows view.

Velocity, probability and the other values are set on the rows, as are dotted and triplet gates; the roll draws the bar of what sounds. A chord can be picked in either view: `H` on the roll's note and `Enter` on the Chord row's cell open the same [Chord Selector](#chord-selector). The roll shows a named chord's other notes where they sound in the scale the pattern plays under, so C minor in C major shows its E♭ on a dim `D#3` row between D and E, and shows none of them when the pattern plays under more than one scale; a scale chord's notes are degrees and always show. Drum patterns have no roll, and open on their rows.

## Rows View

![The pattern editor's rows, on a bass pattern](screenshots/pattern_editor_rows.svg)

Each column is a step, and each row is one kind of value. The grid is as wide as the pattern's step count, and a pattern wider than the screen scrolls sideways as the cursor moves, with `steps 1-11 ›` at the right of the header saying which steps are shown. Typing never moves the cursor and never grows the grid, so moving is always done with the arrows, which stop at the edges.

### Degree Gauge

Degree is drawn as a gauge: a bar in each step's column rising to the note's degree, with one row per note of the scale, labelled with the scale's notes down the left, and the degree as a number under the bars, where the cursor sits. The header's second line names the scale the gauge is drawn in, the scale the pattern plays under, or the song's when no clip plays the pattern; when the pattern plays under more than one scale, the rows are numbered instead, and the header says so. Octave sits right under the gauge. Degree and Octave stay at the top whatever rows are showing, while the rows beneath them scroll on a short screen; on a taller terminal nothing scrolls.

### Typing Numbers

Digits build up a number in a cell, so `1` then `2` makes 12. A new number starts once the cursor moves, or when the next digit would go out of range.

### Steps, Rests and Beats

A step with no degree or note is empty, which is a rest. The rows that only a note can hold, such as Octave, Velocity and Chord, show a light `/` on an empty step, and their keys leave the legend while the cursor is there. The rows a rest can hold, Tie, CC 1 to 4, Slide and every register row, stay open; Tie shows `/` on a step with a note, which can't take a tie.

Every step lasts the pattern's step size, shown at the top with the number of steps. The header's second line shows the time signature the pattern is drawn in, the song's unless the pattern sets its own through `R` (Reconfigure). A step that starts a beat has a bold number and a bold double line down its left edge, so a 16-step pattern in 4/4 is marked at 1, 5, 9 and 13, and in 6/8 at 1, 7 and 13. The beat marking changes only what is drawn. A step with a note sounds for its gate, which can run on past later steps but stops at the end of the pattern; a new note gets the song's default octave and a blank gate, which lasts one step.

## Editor Keys

These keys work throughout the rows view:

| Key | What it does |
| --- | --- |
| `Esc` | Goes back. |
| Arrows | Move. |
| `Home`, `End` | Go to the first and last step. |
| `PgUp`, `PgDn` | Jump to the previous or next section heading under Octave, stopping at the first and the last. |
| `Tab` | Switches to the piano roll. |
| `I` | Inserts an empty step before the cursor's step. |
| `D` | Removes the cursor's step, while there is more than one. |
| `S` | Sizes the pattern: a number of steps, from 1 to 4096. Resizing asks first if steps with something in them would be cut. |
| `R` | Reconfigures the pattern, from the list below. |
| `L` | Listen: plays the pattern in real time, again and again, until `L` is pressed again, through the one track that plays it, or through any of the tracks that play it when they share an instrument. Otherwise a list asks which track to listen through, and a track that plays the pattern nowhere plays it in a scene of its own, in a copy of the song, where Grab steps play their own note. See [Playing Live](PLAYING_LIVE.md). |
| `Bksp` | Clears the cursor's step, on the Degree row. |
| `[`, `]` | Adjust the value at the cursor, down and up, on every row that holds a number; `-`, `+` and `=` do the same. |

## Reconfigure

`R` (Reconfigure) opens a list of changes to the whole pattern, which keeps the legend short:

| Choice | What it does |
| --- | --- |
| `munge` | Rearrange the steps around the cursor, choosing from the list below |
| `load over` | Load a copy of another pattern over this one, asking first if this one has notes |
| `step size` | The pattern's own step size, typed as a whole number or a fraction like 1/8. Leave it blank to use the song's. |
| `time signature` | The pattern's own time signature, typed like 3/4, for a pattern in another meter than the song. Leave it blank to use the song's. The time signature changes which steps are marked as beats, and the grid of the pattern's clips in Live. |
| `drum on` or `drum off` | Notes and drums use different values, so changing between them clears the notes, and always asks first. |
| `direction` | The play direction |
| `rename` | Rename the pattern |

`munge` opens a list of ways to rearrange the steps around the cursor:

| Choice | What it does |
| --- | --- |
| reverse after step | Reverse every step after the cursor |
| reverse before step | Reverse every step before the cursor |
| reverse | Reverse the whole pattern |
| pivot around step | Swap what's before the cursor with what's after it |
| randomize | Shuffle the steps into a random order. The shuffle is an ordinary edit, not seeded, so every randomize is different. |

The cursor stays on its step, so choosing the same reverse or pivot again undoes it. On a drum pattern's Note row, `D` types the note D, so move to another row to remove a step.

## Rows and Sections

Degree and Octave stay at the top, and under them the rows come in sections that open and close like an accordion. Each section is headed by a row of the grid with a rule above and below it and no step dividers across it, labelled `+` and the section's name while closed, such as `+ Advanced`, and `-` and the name while open. The cursor moves onto a heading like any row, keeping its step, and the heading's name shows in reverse video; `Space` or `Enter` opens or closes the section, and `PgDn` and `PgUp` jump from heading to heading.

Basics and Timing start open, and the editor remembers which sections are open, for every pattern, for as long as it runs. When the open rows don't fit the screen, they scroll to keep the cursor's row in view. The sections, in the order a step works them out, are:

- **Basics:** #/b, Velocity;
- **Chord:** Chord, Tension, Scale, Inversion;
- **Timing:** Tie, Gate, Dot, Glide;
- **Advanced:** Probability, Ratchet, Ratchet Offset, Grab;
- **CCs:** CC 1 to CC 4, Slide;
- **Reg. Mod:** the rows that change the registers;
- **Reg. Apply:** the rows that use the registers;
- **Reg. Cond:** the conditions that decide whether a note sounds.

### Basic and Timing Rows

| Row | Values | Keys |
| --- | --- | --- |
| Degree | The gauge, 1 up to the size of the scale, where 1 is the root | Digits, `[` `]`, `Bksp` empties the step |
| Note (drum patterns) | A to G, with no gauge | Letters, `Bksp` empties the step |
| Octave | -2 to 8 with Live's labels, 0 to 10 with llamatron's (see Octave labels on the Set File page) | Digits, `[` `]`, `Bksp` sets the default |
| Tie | `●` on an empty step after a note holds the note through that step. See below. | `Space` or `Enter` toggles, `Bksp` turns it off. Only on empty steps. |
| Gate | How long the note sounds, in whole notes, like 1/16 or 5/16. Blank is one step. | `[` `]` step through 1/64, 1/32, 1/16, 1/8, 1/4, 1/2, 1, 2 and 4, `Enter` types a whole number or a fraction, and `Bksp` makes it one step. |
| Dot | `d` makes the gate dotted, half as long again, and `t` makes it a triplet, two thirds as long, so 1/16 with `d` is 3/32 | `Space` or `Enter` goes to the next one, `[` (dec) and `]` (inc) step back and forward, `Bksp` clears |
| #/b | Sharp or flat: moves the note a half step up or down | `Space` or `Enter` goes to the next one, `[` (dec) and `]` (inc) step back and forward, `Bksp` clears |
| Chord | Builds a chord on the note | `Enter` to choose from the list, `Space` goes to the next one, `[` (dec) and `]` (inc) step back and forward, `Bksp` clears |
| Inversion | Which of the chord's notes is at the bottom: blank for root position, `1` moves the chord's lowest note up an octave, `2` the lowest two and `3` the lowest three, which only a chord of four notes or more has, so a triad plays `3` as `2`. A step with no chord shows `/`, and the piano roll draws the chord's other notes where the inversion plays them. | `Space` or `Enter` goes to the next one, `[` (dec) and `]` (inc) step back and forward, `Bksp` clears |
| Velocity | 1 to 127, default 127 | Digits, `[` `]`, `Enter` to type, `Bksp` sets the default |
| Glide | `●` makes the note run slightly into the next one, which a synth with glide turned on slides across. A blank is off. | `Space` or `Enter` toggles, `Bksp` turns it off |

When the scale is known, the Degree gauge is as tall as the scale, five rows for a pentatonic scale and seven for a major one, and a degree can't go past it: `]` at the top and `[` at the bottom stay where they are, and the status line says `top of C Major: change the octave on the Octave row`, since the gauge and the Octave row together make the note. A file can hold a degree past the scale's top, such as 9 in a seven-note scale; the editor shows and plays it as degree 2 an octave higher, and writes it back within the scale when nudged. When the scale isn't known, the gauge has seven numbered rows, any degree up to the largest scale the pattern plays in can be typed, and a degree above the rows fills the gauge and marks its number with `▲`.

### Ties

Tie draws a note out across the steps after it. Put a note on one step, then press `Space` on the empty steps that follow, and the note keeps sounding through every tied step: a sixteenth note followed by three ties is a quarter note, and the piano roll shows it as one bar.

Ties win over the gate: a note with ties after it sounds to the end of its ties whatever its gate says, so the ties you see are the length that plays, and the line under the grid says when a gate is being overridden. A note with no ties after it keeps its gate, so lengths can be drawn with ties or typed as gates. The Tie row works only on empty steps, because a tied step plays nothing of its own, and typing a degree on a tied step removes the tie, so the note ends there and later ties hold the new note. Emptying a note with `Bksp` also clears the ties that followed it, so no bar is left hanging onto an earlier note. In detail:

- A tie after an empty step holds nothing and is silent, as is a tie after a note that probability dropped.
- Ties go in the order the steps play, so with a play direction a tie holds whichever note played just before it.
- A tie on the first step of a pattern holds the last note of the pass before it, across repeats and loops of the same clip, which a gate can't do, since gates stop at the end of the pattern. At the very start of a clip nothing comes before the tie, so the tie is silent, including at the start of a new scene.
- A tie holds a whole chord, or the last slice of a ratchet, and glide on the note acts at the end of the held note.
- A tied step can still send CC values and change registers, like any empty step. During a morph, a tie on the first step follows the clip's own pattern.

### Glide and Probability

Glide does nothing before a rest or before the same pitch. Probability, on the Advanced rows, is rolled each time the song plays or exports, once for each repeat and each ratchet slice. A note that probability drops is silent however long its gate, and the note after it plays as normal. A song with a seed plays the same every time until the seed changes, and a song without one rolls afresh each time.

### Chords

The Chord section holds everything about a step's chord: the Chord row, the Tension row, the Scale row and the Inversion row. `Enter` on the Chord, Tension or Scale row opens the [Chord Selector](#chord-selector), and on each of the three rows `[`, `]` and `Space` step through the choices, stopping at the first and the last; the Scale row steps through every scale type in the Chord Selector's order. While the cursor rests on a step that holds a chord, the status line names the chord and its notes.

A step whose Scale is set takes its degree and its scale chord from that scale type on the clip's root, which is how a chord is borrowed: in C major, degree 6 with the Scale "Minor" and the chord `3` plays A flat major. A tension is added above the chord's root, so `dom7` on degree 5 with `b9` and `13` plays G B D F A♭ E. A single note takes no tensions.

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

**Scale chords** are the plain numbers. Scale chords stack every other note of the scale, so they use only notes in it. The scale decides whether each one is major, minor or diminished, and they change when the scale does. The notes shown are on degree 1 of C major:

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

## Advanced

![The pattern editor on the advanced rows](screenshots/pattern_editor_advanced.svg)

Open the `Advanced` section to see these: `PgDn` to its heading and `Space`.

| Row | Values | What it does |
| --- | --- | --- |
| Probability | Chance of playing, 0 to 100, default 100 | Digits, `[` `]`, `Enter` to type, `Bksp` sets the default |
| Ratchet | 1 to 16 | Splits the step into that many equal notes in the same time |
| Ratchet Offset | -24 to 24 | Moves each ratchet note that much further along the scale than the last one. In a drum pattern it moves by half steps instead. |
| Grab | `●` or blank | Plays the note that the clip's Grab track most recently played instead of this step's own, or the root of a chord, however the chord is inverted or voiced. A chord on the step's Chord row is built on the grabbed note. The Grab row works on an empty step too: marking one gives it the root in the default octave as a note of its own, so the step has a velocity and a gate like any other, and a marked step can't hold a chord. |

Gate and Dot are in Timing, with Tie, because ties draw a note's length where you can see it, and most patterns need nothing else. Unset values show a dot. The number rows take digits, `[` (dec) and `]` (inc), or `Enter` to type, and `Bksp` sets them back. Grab is toggled with `Space`.

Grab works like the Cirklon's note grab, taking notes from the track that each clip names in Grab track. See [Clips](CLIPS.md) for how it works.

## CCs

![The pattern editor on the CC rows](screenshots/pattern_editor_cc.svg)

Open the `CCs` section to see these. The CC rows send MIDI CC values, like the Cirklon's aux rows, and each track decides which CC number each row sends, so the same pattern can move different controls on different tracks.

| Row | Values | What it does |
| --- | --- | --- |
| CC 1 to CC 4 | 0 to 127 | Sends that value at the start of the step. A dot sends nothing, so the last value holds. The row's label says which CC number the lane sends on the tracks that play the pattern, like `CC 1 (74)`, or `(off)` when it sends nothing there, or `(?)` when the tracks send different numbers; a pattern no track plays yet shows the plain `CC 1`. |
| Slide | `●` or blank | Ramps each of this step's CC values to that row's next value, instead of jumping, like slide on an Elektron Monomachine |

CC rows and Slide can be set on a rest, so a sweep can carry on through silence. The number rows take digits, `[` (dec) and `]` (inc), or `Enter` to type, and `Bksp` clears them. A ratchet doesn't repeat the values, and probability doesn't drop them.

In a Live set, each CC becomes a clip envelope, and Live draws a slide as a straight line. In MIDI files, a slide is sent as a new value every 1/64 note.

## Reg. Mod, Reg. Apply and Reg. Cond

The song has four registers, AX, BX, CX and DX: numbers the whole song shares, which pattern steps change and use as the song plays. Their settings are on the [Registers](REGISTERS.md) page. They're for changes that build up from bar to bar, like a note that climbs each time a riff comes round, or a fade.

The `Reg. Mod` section holds the rows that change the registers, `Reg. Apply` the rows that use them, and `Reg. Cond` the conditions a note needs to sound.

![The pattern editor on the register rows](screenshots/pattern_editor_registers.svg)

![The pattern editor on the register change rows](screenshots/pattern_editor_register_changes.svg)

| Row | Values | What it does |
| --- | --- | --- |
| AX+Note to DX+Note | `+`, `-` or blank | `+` moves the note up the scale by the register's value and `-` moves it down; blank leaves it. `Space` or `Enter` cycles the three, `[` (dec) and `]` (inc) step back and forward, and `Bksp` clears. Not in drum patterns. Can be set on an empty step, where nothing moves. |
| AX+Vel to DX+Vel | `+`, `-` or blank | `+` adds the register's value to the velocity and `-` takes it off, keeping the velocity between 1 and 127; blank leaves it. The same keys. Can be set on an empty step, where nothing changes. |
| AX= to DX= | blank, or a value | Sets the register to this value when the step plays, before anything adds to it, held between the register's Minimum and Maximum; blank leaves it. `]` (inc) on a blank step gives the register's Minimum in the current song, `[` (dec) on the Minimum gives blank again, and `Bksp` clears. |
| AX+= to DX+= | minus to plus the register's Allowed Inc Max | Adds this much to the register when the step plays, or takes it away. `[` (dec) and `]` (inc) stop at the register's Allowed Inc Max on the [Registers](REGISTERS.md) page, 20 unless changed, the narrowest of the songs that play the pattern. |
| AX,BX, AX,CX, AX,DX | `<`, `>`, `=` or blank | The note sounds only when AX is less than, more than or the same as that register, after the step's own changes; blank makes no comparison, and when a step has several, every one has to hold. A step that fails sounds nothing, a ratchet's slices all together and a chord whole, and its changes still happen. `Space` or `Enter` cycles them, `[` (dec) and `]` (inc) step back and forward, and `Bksp` clears. Only a note's step can hold one. |

How they work:

- A step sets the registers, then adds to them, then uses them, then checks its conditions, so a step's own `=` and `+=` already change its note.
- Every step sets and adds, even an empty one or one that probability or a condition silences, so a change can go on a step with no note. Putting it on the last step of a pattern means the first time through plays as written.
- A step that uses several registers adds all their values together, each added or subtracted as its row says. A register's value can be negative too, so `-` on a register holding -3 moves the note up three.
- A ratcheted step adds once, and every slice uses the same value.
- The registers are shared by every track, so one track can change a register that others use. Within a scene, steps are taken in time order, and steps at the same moment in track order. Only one track adding to a register usually makes the most sense.
- Values carry on from scene to scene, unless a scene resets them (see [Scenes](SCENES.md)).
- A morph's target pattern uses the registers but doesn't add to them.
- A note pushed out of the MIDI range moves to the nearest octave that fits.

The register change rows take digits, `[` (dec) and `]` (inc), or `Enter` to type a negative number, and `Bksp` clears them, and every register row can be set on an empty step: no register setting is ever locked out for want of a note, and erasing a note leaves the step's register rows as they are. The rows that use registers are toggled with `Space` or `Enter`.

## Play Directions

`direction`, under `R`, sets the order the steps play in. Names follow the Cirklon.

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

Positions carry on across repeats. The random directions draw their own random numbers, separate from the ones probability uses, so changing a direction never changes which notes probability drops, and a song with a seed chooses the same way every export. A clip can override the direction.

## Chord Selector

![The Chord Selector with the flyout of the Common scales open](screenshots/chord_selector.svg)

The Chord Selector chooses a step's chord in one place. `Enter` on the Chord, Tension or Scale row of the rows view opens it, and so does `H` on a note of the piano roll. It holds three lists side by side: the chord's quality, with `(single note)` at the top; its tensions, the notes added on top, such as a flat ninth; and the scale the step borrows its notes from, with `(the clip's own)` at the top.

| Key | What it does |
| --- | --- |
| Arrows | Up and Down move within a list, Left and Right from list to list, stopping at the edges. |
| `Tab` | Goes to the next list, and round to the first. |
| `Space` | On a tension, turns it on or off. |
| `Space`, `Enter` | On a category of scales, opens its flyout; on `(the clip's own)`, borrows no scale. |
| `Enter` | On a quality or a tension, takes the chord. |
| `Esc` | Cancels, changing nothing. |

The scale list, the last of the three, holds categories: Common, Modes, Harmonic & Melodic, Pentatonic & Blues, Symmetric, Jazz, Mid. East & Europe, East Asia and India. A category opens a flyout of its scale types, a box drawn over the Chord Selector, a little down and to the right. In the flyout, Up and Down move, `Enter` picks a scale type and closes the flyout, and `Esc` or Left closes the flyout with nothing changed. After a pick the cursor goes on to the qualities, so that the next `Enter` takes the chord, and the category shows the scale type picked. Common holds the six scales most often borrowed from, which are also found in their own categories.

The lines under the lists say what the chord comes to as the choice moves: its name in the scale it is drawn from, its name in the clip's own scale when it borrows another, and its exact notes. The pattern underneath shows the chord at the same time: the piano roll draws the chord's other notes as thin green lines, and the rows show the values in their cells. Cancelling puts the step back as it was.
