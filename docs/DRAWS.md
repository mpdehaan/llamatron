# Draws

A draw is a short list of numbers that the whole song shares, and each time a step of a pattern uses the draw it takes the next
number and adds it to its note or its velocity. The song has eight, AD to HD.

A draw deals. Think of a draw as a deck of cards laid out in a row. A drummer who plays a little louder on
every other hit is a draw of 0 and 20 moving forward; a singer who climbs a step on each line of a verse is a draw of 0, 1, 2 and 3;
a composer writing twelve-tone music, who uses every pitch of the octave once before using any again, is a draw of 0 to 11 dealt at
random. The notes in the pattern stay as they are written, and the draw decides how far each moves each time it plays, so one
pattern of four plain notes can play a different melody on every pass.

## How a Draw Moves

Each draw has a direction, which says which slot comes next:

| Direction | What comes next |
| --- | --- |
| forward, reverse_a, reverse_b, alternate, pendulum, random, brownian, eitherway | The slots in the same order a pattern's steps play in under that direction. |
| serial | Every slot once, in a random order, before any slot comes again: a new order each round. |
| any | A slot at random every time, so the same value can come twice in a row, and a value held by two slots comes twice as often. |

A blank slot is passed over without using up a draw, so a draw of 0, blank, 5 gives 0, 5, 0, 5. A draw with no value in any slot
adds nothing. Every value runs from -99 to 99, and a draw's Value Min and Value Max keep its slots within a narrower range.

A draw belongs to the song, not to a pattern or a track. Every track that uses AD takes from the same AD, so two tracks using it at
one moment take two values, in the order of the tracks, and a draw carries on from one scene to the next where the last left it.

## The Draws Page

Press `D` on the main screen to open the Draws page. Each draw is a section, a blank line apart, closed until `Space` or `ENTER` opens it, with these
settings and, after them, its strip:

| Setting | Default | What it does |
| --- | --- | --- |
| Direction | forward | Which slot comes next, as the table above says. |
| Slots | 8 | How many slots the strip holds. New slots are blank, and slots past a smaller count are taken away. |
| Value Min | -99 | The lowest value a slot can hold. Raising it moves every slot below it up to it. |
| Value Max | 99 | The highest value a slot can hold. Lowering it moves every slot above it down to it. |
| Conditions redraw | off | Whether a condition that reads the draw draws from it, as described under Draws in Conditions. |

The strip is a row of boxes, the slots numbered above their values. On the strip, `Left` and `Right` move between the slots, `[`
and `]` make the slot under the cursor less and more, a digit puts that number in the slot at once, `ENTER` types any value and
`Bksp` makes the slot blank. While the song plays,
the slot each draw last took its value from is lit in violet, and a closed draw's heading says which slot it is.

## Use Draws

In the pattern editor, the section Use Draws, after CCs, has three rows for each draw that holds a value in the current
song: every draw starts empty, so a song using no draws has no Use Draws section at all, and the section and a draw's rows appear
as soon as a value is put in the draw's strip on the Draws page. Marks on the rows of a draw emptied again stay in the pattern and
come back with the rows. The rows of each draw shown are:

| Row | What a step does |
| --- | --- |
| Note+=AD | Adds the draw's next value to the step's note, along the scale (`+`), or takes it away (`-`). A drum pattern has no scale, so the row is only for melodic patterns. |
| Vel+=AD | Adds the draw's next value to the step's velocity (`+`), or takes it away (`-`). |
| Reset AD | Sends the draw back to its first slot, or a serial draw to a new round, before the step draws. |

`Space` or `ENTER` steps a Note+= or Vel+= cell through `+`, `-` and blank, and switches a Reset cell on and off. A step that uses a
draw on both its note and its velocity takes one value for both: a step draws from a draw once, however many of its rows use it,
and a step that uses no draw takes nothing from it. A step draws whether its note sounds or not, so a step that probability or a
condition silences still moves the draw on.

## Draws in Conditions

Stop When, Restart When and Mute When on a step, and the Bypass Generators When tables, name a draw as what is tested, as the
number it is compared with, or as what a sum is compared with. A
draw is drawn at most once for each pattern step, before anything on that step is tested, so the conditions and the Note+= and
Vel+= rows of one step all see the one value drawn. A step draws when its Note+= or Vel+= rows use the draw, or when one of its
conditions names a draw whose Conditions redraw is on; a condition on a step that draws nothing looks at the value the draw last
gave.

Bypass Generators When is tested as a clip's pattern starts a pass, and they belong to the pass's first
step: a draw they name whose Conditions redraw is on is drawn there, once, with that step's own draws, and the whole pass starts
from that value.

So a hi-hat with Vel+=CD and Mute When CD = 0 drops out whenever its own hit draws a 0, and a bell with Mute When BD < 2, where
BD redraws, plays the rhythm its own draws make.

## Conditional Execution

Conditional Execution lets the draws decide what plays. A table of up to 4 statements about the draws is read each time a clip's
pattern starts over, and when any one statement is true, the notes of that pass go by generators untouched. The table, Bypass
Generators When, is on three pages:

| Where | What a true statement leaves out |
| --- | --- |
| A generator's page | That generator, wherever a chain names it. |
| A chain's statements, `W` in the chain editor | The whole chain. |
| The Scene page | Every chain each of the scene's clips runs. |

So a guitar can stop strumming after its pattern has played 4 times, or an arpeggio can rest in every other bar.

Each line of a table is one statement, read from left to right:

| Statement | True when |
| --- | --- |
| `ignored` | Never. A line set to `ignored` does nothing. |
| `AD < 4` | AD is less than 4. The comparisons are `<`, `<=`, `=`, `>=`, `>` and `!=`. |
| `AD odd`, `AD even` | AD is odd, or even. |
| `AD % 3 = 0` | The remainder of AD divided by 3 is 0, which is every third count. The sums are `+`, `-`, `%`, `*` and `/`, and the result is compared with the number at the end. |
| `AD + BD > CD` | A draw may stand wherever a number does. |

The sums are in whole numbers: a division rounds down, and a remainder is counted from 0 upward. A typed 0 is refused after `/`
and `%`, and when a draw that divides holds 0 the statement counts as true.

The lines are drawn as a grid of five columns, one a part, each as wide as its widest value, so the table keeps its size as a line
fills. Left and Right move between the parts of a line and `ENTER` changes the part under the cursor: the draw, the operator, and
then a number or a draw. `Bksp` sets the line back to `ignored`.

A step of a pattern can hold a statement of its own, which is read as the step is reached and stops the clip, starts the pattern
over or mutes the step: see [Stop When, Restart When and Mute When](PATTERNS.md#stop-when-restart-when-and-mute-when).

## Reset Draws on a Scene and a Clip

The Scene page and the clip page each have a Reset Draws tab, with a Reset toggle for each draw that holds a value in the song,
and the line "No draws configured" while none does. A scene resets a draw as it first starts, not on its repeats, sending it back
to its first slot, or a serial draw to a new round, so that a verse's melody starts the same way every time the verse comes
round. A clip resets a draw as it starts, on its scene's first play alone, after the tracks to its left have taken their draws at
that moment and before any of its own steps draws, so that one part can start a draw afresh while the others carry on.

The demo [`examples/learning/28_draws.yml`](../examples/learning/28_draws.yml) plays draws from a count-in to twelve-tone rows,
melodies and gates.
