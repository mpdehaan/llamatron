# Draws

A draw is a short list of numbers that the whole song shares, and each time a step of a pattern uses the draw it takes the next
number and adds it to its note or its velocity. The song has eight, AD to HD, beside the four registers.

A register counts, and a draw deals. Think of a draw as a deck of cards laid out in a row. A drummer who plays a little louder on
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

Press `D` on the main screen to open the Draws page. Each draw is a section, closed until `Space` or `ENTER` opens it, with these
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

In the pattern editor, the section Use Draws, after Use Registers, has three rows for each draw:

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

Stop When, Restart When and Mute When on a step, and the Skip Playback When and Bypass Generators When tables, can name a draw
wherever they can name a register: as what is tested, as the number it is compared with, or as what a sum is compared with. A
draw is drawn at most once for each pattern step, before anything on that step is tested, so the conditions and the Note+= and
Vel+= rows of one step all see the one value drawn. A step draws when its Note+= or Vel+= rows use the draw, or when one of its
conditions names a draw whose Conditions redraw is on; a condition on a step that draws nothing looks at the value the draw last
gave.

Skip Playback When and Bypass Generators When are tested as a clip's pattern starts a pass, and they belong to the pass's first
step: a draw they name whose Conditions redraw is on is drawn there, once, with that step's own draws, and the whole pass starts
from that value. A pass the clip sits out still draws when something tests or uses the draw, and draws nothing when nothing does.

So a hi-hat with Vel+=CD and Mute When CD = 0 drops out whenever its own hit draws a 0, and a bell with Mute When BD < 2, where
BD redraws, plays the rhythm its own draws make.

## A Scene's Reset Draws

On the Scene page, a Reset toggle for each draw, after the registers' Reset toggles, makes the scene reset the draw as it first starts, not on its repeats, sending it back to its first slot or a serial draw to a new
round, so that a verse's melody starts the same way every time the verse comes round.

The demo [`examples/learning/28_draws.yml`](../examples/learning/28_draws.yml) plays draws from a count-in to twelve-tone rows,
melodies and gates.
