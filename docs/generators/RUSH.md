# Rush

A Rush is a row of steps, each on or off, as [Generators](../GENERATORS.md#rows-of-steps) describes. A note starting on a step that is on plays the note a little early, ahead of the beat, on top of the groove. The first note of a clip can't move before the clip.

## Settings

![A Rush's settings](../screenshots/rush_editor.svg)

| Setting | What it does |
| --- | --- |
| Name | `Enter` renames it, and every chain using it follows. |
| Step | How long each step of the row lasts: `(pattern)`, the clip's pattern's step size, or a time from the list every time setting shares. |
| Amount | The Rush amount, 15% of a step by default, up to half a step. |
| Steps | The row, from 1 to 16 steps. `Enter` opens it. |
| Restart | When it starts over, as [Generators](../GENERATORS.md#restart) describes. |

## Applying the Generator

Add the Rush generator to a chain, as `rush: name`, and give clips that chain. The drop of `examples/learning/14_acid_glide.yml` loosens its drums with a Rush and Drags.
