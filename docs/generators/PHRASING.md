# Phrasing

Phrasing ends each line of a tune early, as a singer stops for air, so that a tune which fills every bar is heard as lines with a breath between them. Add Phrasing to a chain on the clip that plays the tune.

## Lines and Breaths

A line is as long as Line says, counted from the clip's start. Each line ends early by its breath: a note that would start inside the breath is left out, and a note still sounding when the breath starts stops there. Line Lengths says which lines of each pair take the longer breath, so that the lines differ in length as sung lines do.

## Early Notes

Early Notes is how many lines of every four have a note that arrives early. In such a line, the first note that starts a bar or the middle of a bar, after a note at least a quarter long, starts an eighth early, and the note before stops to make room.

## No Breath

A note on a step marked in the pattern's No Breath row, in the Band section of the [pattern editor's rows](../PATTERNS.md), is left exactly as written: Phrasing neither stops the note early nor moves the note. Mark the notes of a hook, so that the hook's held note plays whole.

## By Section

The By Section table gives Breath, Line Lengths and Early Notes a value of their own for a kind of section, such as a longer breath in every chorus. A scene's Section says which kind the scene is, and "(same)" takes the value above the table.

## Settings

| Setting | What it does |
| --- | --- |
| Name | `ENTER` renames it, and every chain using it follows. |
| Line | How long a line is: "1 bar", "2 bars" or "4 bars". |
| Breath | How early a line ends: "off", "short", "medium" or "long". |
| Line lengths | Which line of each pair is the shorter: "long, short", "short, long" or "even". |
| Early notes | How many lines of every four have a note that arrives an eighth early, 0 to 4. |
| By Section | Breath, Line lengths and Early notes for each kind of section. |

## Applying the Generator

`examples/learning/25_phrasing.yml` plays a verse and a chorus as written and then through Phrasing, with the chorus's hook marked in the No Breath row.
