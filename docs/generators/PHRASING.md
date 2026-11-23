# Phrasing

A tune written step by step plays every note at one loudness and fills every
bar, which is how a music box plays. A singer or a horn player delivers the
same tune in lines, the sentences of the tune: each line starts gently, grows
toward its most important note and falls away, and a breath follows before the
next line starts. Phrasing plays a tune that way. The pattern stays exactly as
written, no note is left out and no pitch changes, so another delivery is
another setting and never another tune.

A musician reaches for Phrasing when a tune sounds stiff or run together.
Switch on the Phrasing tab of the clip that plays the tune, or add Phrasing to
a chain on that clip.

## Line

Line says how long one sentence of the tune is: "1 bar", "2 bars" or "4 bars",
counted from the clip's start. Most sung tunes move in lines of 2 bars.
Everything else on the page happens once for each line.

## Breath

A singer has to breathe, and the breath is what tells a listener that one line
has ended and another begins. Breath makes a silence after each line by ending
the line's last note early. With "none" the lines run together. With "quick"
the last note gives up an eighth note, and with "deep" a quarter note. The
last note is only shortened, by half of the note at most, and where the tune
already rests at the end of a line nothing is cut.

## Rise and Fall

A player does not give every note of a line the same weight. A line grows
toward its main note, which Phrasing takes to be the longest note that starts
on a strong beat in the line's second half, and the notes after the main note
fall away, the last note softest. A note that starts a bar is a touch louder.
The main note stays as loud as written and the notes around the main note are
played softer: by a small amount with "a little", by a clear amount with "a
lot", and not at all with "none".

## Notes

Notes says how the notes inside a line are joined. With "choppy" each note is
cut short and a space follows, as a player tonguing every note plays. With
"flowing" each note is held until the next note starts, which closes the gaps
in a tune written with short notes; a note followed by the same pitch stops a
moment early, so that the second note is heard to start. With "as written"
each note lasts as long as the pattern says. A tune whose notes already touch
sounds the same with "flowing" as with "as written".

## Settings

| Setting | Choices | A new Phrasing starts with |
| --- | --- | --- |
| Name | `ENTER` renames it, and every chain using it follows. | |
| Line | "1 bar", "2 bars", "4 bars" | "2 bars" |
| Breath | "none", "quick", "deep" | "quick" |
| Rise and fall | "none", "a little", "a lot" | "a little" |
| Notes | "choppy", "as written", "flowing" | "as written" |

## Applying the Generator

`examples/learning/23_phrasing.yml` plays one tune as written and then with
one setting changed in each scene, so that each setting is heard alone, and
ends with a verse and a chorus sung with the settings together.
