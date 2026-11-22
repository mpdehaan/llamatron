# Guitarify

A keyboard plays a chord as a stack of notes struck together and held. A guitar plays the same chord across six strings, one note a string, and a hand strikes those strings in a rhythm: a strum down, a strum up, a muted strum, the bass string, one string picked alone. Guitarify plays a clip's chords and notes that way, on any instrument, so a pattern that is only a row of chords becomes a strummed or picked part.

Guitarify has two modes, its Mode the first setting on its page:

- **Guitar**, the default, plays a part as a guitar's two hands would. It has two halves, and each can be switched off: Shape, the Left Hand, is the fretting hand, which decides the notes of each chord; Strokes, the Right Hand, is the other hand, which decides when each string sounds.
- **Strum** leaves the chords as written and strums each one at the very end of the clip, after its chains and its shapes, the way a hand crosses the strings: its notes start one after another, each lasting to the chord's end. It has a Direction and shares Spread, Fade, Loose timing and Upstroke strings with Guitar mode, so switching modes keeps them.

## Strum

| Setting | What it does |
| --- | --- |
| Direction | The order the strings sound in: "by the beat", the default, down on each beat and up between, as a hand moves; "down", low to high; "up", high to low; "down up", alternating chord by chord. |

Spread, Fade, Loose timing and Upstroke strings are as Strokes describes below. A chord's strum is drawn from the song's seed, so it plays the same every time. The last Guitarify in Strum mode a clip's chains name strums the clip; a single note is left alone.

## Shape

Shape holds each chord as a hand can hold it: at most one note on each string, every note within four frets of the hand's position, and the chord's lowest written note in the bass wherever a string can reach it. C, E and G written close together become C, E, G, C and E across five strings, the open C chord. A hand with too few strings for a chord leaves the fifth out first and the root out last.

| Setting | What it does |
| --- | --- |
| Shape chords | Switches the section on or off. Off leaves every chord as written. |
| Tuning | The open strings: standard, drop D, open G, open D or DADGAD. |
| Position | Where the hand is: "open", which uses the open strings and the first three frets, or a fret from 1 to 12, which uses that fret and the three above. |
| Capo | The fret a capo clamps, which raises every string. |
| Strings | How many strings are played, from 3 to 6, counted from the highest, so 4 leaves out the two lowest. |
| Single notes | What becomes of a step that holds one note: "leave" keeps the note; "power chord" plays the root, the fifth above and the octave on the low strings; "scale chord" plays the chord the note's place in the scale builds; "octave" adds the same note an octave up; "third above" adds the scale's third above the note, as two guitars play one tune in harmony; "double stop" adds the note a fourth below. |
| Color | How every chord is voiced: "as written"; "add 9", which adds the ninth; "sus 2" and "sus 4", which move the third down or up to the neighboring note; "no third", which leaves the third out. |

## Strokes

Strokes plays a bar of strokes, one stroke a cell, on whatever chord or note sounds at that moment. The bar follows the song's bars and goes round for as long as the clip plays. A single note is played by every stroke.

| Setting | What it does |
| --- | --- |
| Play strokes | Switches the section on or off. Off leaves each chord struck once, where the pattern wrote the chord. |
| Bar | The bar of strokes, shown by the name of the ready-made bar the cells match, or as "custom". ENTER opens the bar's editor. |
| Let ring | A struck string sounds until a later stroke strikes the same string or the chord ends, as picked chords do. Off stops every string at the next stroke. |
| Spread | The time between one string of a strum and the next, in milliseconds whatever the tempo. |
| Fade | How much quieter the last string of a strum is than the first, up to 50%. |
| Loose timing | How much each gap between strings varies, up to 50%, drawn at random. |
| Upstroke strings | How many of the top strings an upstroke catches, or "all". |
| Approach | How a new chord is reached: "off" plays the chord where the pattern wrote the chord; "from below" and "from above" first play the chord one fret lower or higher for a sixteenth. The first chord of a clip is never approached. |
| Restart | When the bar starts over, as [Generators](../GENERATORS.md#restart) describes. |

Spread, Fade, Loose timing and Upstroke strings are shared with Strum mode.

## Bar Editor

The bar's editor shows one cell a column, with the stroke above and the accent below. Left and Right move along the cells, `[` and `]` change the stroke under the cursor, Space or ENTER accents the cell, `I` inserts a cell, `D` removes one, `S` steps the cell length and `R` picks a ready-made bar. A bar holds up to 32 cells.

| Stroke | Drawn | What plays |
| --- | :---: | --- |
| nothing | `—` | Nothing new: what was struck before sounds on. |
| down | `↓` | Every string, low to high. |
| up | `↑` | The top strings, high to low. |
| mute | `x` | Every string, short and quiet, as a palm-muted or scratched strum. |
| stab | `!` | Every string, low to high, at full loudness and stopped halfway through the cell, whatever Let ring says. |
| bass | `B` | The lowest string. |
| muted bass | `b` | The lowest string, stopped halfway through the cell and a little soft unless accented, as a palm-muted low note. |
| alt bass | `A` | The fifth of the chord where a string plays one, and otherwise the second lowest string. |
| squeal | `^` | One note two octaves above the chord's lowest, short and at full loudness, as a pinched harmonic. |
| string 1 to string 4 | `1` to `4` | One string, counted from the highest. A string the chord lacks plays the nearest string the chord has. |

Where a bar has any accented cell, the strokes without an accent play a little softer.

The ready-made bars are folk strum, boom-chick, travis pick, crosspick, four to the bar, backbeat, boogie, shuffle, scratch, all down, arena, chug, gallop, thrash, tremolo, chime, roll up, roll down, held, skank, disco, pedal riff, five beat, strum and click, slow pick, four stomps and power groove. Picking one replaces the strokes, the accents and the cell length together, and the bar can be edited from there. A rolled chord is the roll up or the roll down bar with Let ring on.

## Applying the Generator

Switch on the Guitarify tab of a clip or a track, or add a Guitarify to a chain, as `guitarify: name`, and give clips that chain. A Progression before the Guitarify in the same chain moves one written chord through a song's chords, and the Guitarify then plays each. `examples/learning/21_guitarify.yml` plays twenty short scenes, each a way a guitar is played, from one pattern of chords a scene.

## Settings by Genre

The Guitarify demo, `examples/learning/21_guitarify.yml`, plays twenty short examples, each a scene of its own on one guitar. The table lists, for each example, the fields of the Guitarify editor that were changed from their defaults, under the editor's two sections, with the values as the editor shows them. An empty cell means every field of that section was left alone. The demo's tracks are named after their guitars, and the tempo is the scene's.

| Genre | Example Name | Guitar | BPM | Shape | Strokes |
| --- | --- | --- | --- | --- | --- |
| country | porch | steel | 104 | | Bar: boom-chick, 8 cells of 1/8 |
| country | thumb and fingers | steel | 96 | | Bar: travis pick, 8 cells of 1/8<br>Let ring: on |
| bluegrass | crosspick | steel | 126 | | Bar: crosspick, 8 cells of 1/8<br>Let ring: on |
| jazz | four to the bar | jazz | 132 | Position: fret 3<br>Strings: 4 | Bar: four to the bar, 4 cells of 1/4<br>Spread: 4 ms |
| blues | open g | steel | 84 | Tuning: open G | Bar: folk strum, 8 cells of 1/8<br>Let ring: on<br>Spread: 14 ms |
| rock and roll | boogie | clean | 152 | Single notes: power chord | Bar: boogie, 8 cells of 1/8<br>Spread: 2 ms |
| surf | tremolo | clean | 150 | Position: fret 5 | Bar: tremolo, 16 cells of 1/16 |
| folk | campfire | steel | 96 | | Bar: folk strum, 8 cells of 1/8 |
| folk rock | chime | clean | 116 | | Bar: chime, 8 cells of 1/8<br>Let ring: on |
| soul | backbeat | clean | 104 | Position: fret 4<br>Strings: 4 | Bar: backbeat, 8 cells of 1/8<br>Spread: 3 ms |
| funk | scratch | muted | 100 | Position: fret 6<br>Strings: 4 | Bar: scratch, 16 cells of 1/16<br>Spread: 2 ms |
| singer-songwriter | harp | nylon | 80 | | Bar: roll up, 8 cells of 1/8<br>Let ring: on |
| hard rock | arena | overdriven | 120 | Single notes: power chord | Bar: arena, 8 cells of 1/8<br>Let ring: on<br>Spread: 2 ms |
| punk | three chords loud | distortion | 184 | Single notes: power chord | Bar: all down, 8 cells of 1/8<br>Spread: 2 ms<br>Fade: 0 |
| metal | gallop | distortion | 150 | Single notes: power chord | Bar: gallop, 16 cells of 1/16<br>Spread: 2 ms<br>Fade: 0 |
| metal | thrash | distortion | 190 | Single notes: power chord | Bar: thrash, 16 cells of 1/16<br>Spread: 2 ms<br>Fade: 0 |
| metal | low and slow | distortion | 70 | Tuning: drop D<br>Single notes: power chord | Bar: held, 4 cells of 1/4<br>Let ring: on<br>Spread: 2 ms<br>Fade: 0 |
| alternative | quiet loud | overdriven | 110 | | Bar: custom, 32 cells of 1/8<br>Let ring: on |
| blues | shuffle | clean | 120 | Strings: 4 | Bar: shuffle, 12 cells of 1/12<br>Spread: 4 ms |
| finale | last chord | steel | 92 | | Bar: custom, 32 cells of 1/8<br>Let ring: on |

A Bar shown as custom was written by hand in the bar editor: quiet loud plays two bars picked string by string and then two strummed, and last chord three bars strummed and then one rolled from the bass string up. Opening the demo and pressing `ENTER` on the Bar of each shows the strokes. A switch that is on, which the editor shows as `●`, is written as on.
