# Draws

A draw is a short list of numbers that the whole song shares, and each time a step of a pattern uses the draw it takes the next
number and adds it to its note or its velocity. The song has four, AD, BD, CD and DD, beside the four registers.

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

Stop When, Restart When and Mute When on a step, and the Skip Playback When and Bypass Generators When tables, can read a draw
wherever they can read a register: as what is tested, as the number it is compared with, or as what a sum is compared with. A
condition looks at the value the draw last gave, without drawing, unless the draw's Conditions redraw is on: then a step whose
condition reads the draw draws from it first, and that is the step's one draw from it.

So a hi-hat with Vel+=CD and Mute When CD = 0 drops out whenever the hit before it drew a 0, and a bell with Mute When BD < 2,
where BD redraws, plays the rhythm its own draws make.

## A Scene's Reset Draws

A scene can reset draws as it first starts, not on its repeats, sending each back to its first slot or a serial draw to a new
round, so that a verse's melody starts the same way every time the verse comes round.

The demo [`examples/learning/30_draws.yml`](../examples/learning/30_draws.yml) plays every kind of draw, from a count-in to
twelve-tone rows, melodies, drums and gates.
