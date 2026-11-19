# Clips

A clip is what a track plays in a scene: a pattern, and the settings that change how the pattern plays there. This page covers the clip page.

![The Clip page](screenshots/clip.svg)

## Clips on Arrange

A clip sits where a scene's row and a track's column meet on Arrange, so the clip page's crumb pairs the two, such as `ARRANGE › clip: (verse, bass)`. The crumbs always say where `ESC` goes back to. The pattern editor opened with `P` from a clip reads `ARRANGE › pattern: bass line` when opened from Arrange, `ARRANGE › clip: (verse, bass) › pattern: bass line` when opened from the clip page, and `PATTERNS › bass line` only when the Patterns page opened it.

## Clip Settings

| Setting | What it does |
| --- | --- |
| Name | A name of the clip's own, shown on the grid and used for the clip in Live and in the clip tree's file names. Without one, the clip goes by its pattern's name. `Bksp` clears it. |
| Patterns | The patterns the clip plays, one after another, as one long pattern (see Pattern Lists below). A clip of 1 pattern is a list of 1. `A`, or `ENTER` on the `+` row, adds a pattern; `Bksp` takes the pattern under the cursor out of the list, which deletes no pattern; `M` picks the pattern up, the arrows carry it and `ENTER` drops it; `ENTER` or `J` opens the pattern in the pattern editor, and `ESC` comes back. |
| Scale | A scale of the clip's own, which wins over the scene's and the song's, so that one track can play in another key or mode. `ENTER` picks one, and `Bksp` goes back to the scene's, shown with where it comes from, such as `A Minor (from scene)`. |
| Chains | The chains of generators the clip runs, in order. `ENTER` opens the list, where `A` adds a chain, `M` moves one and `Bksp` takes one out; `Bksp` on the field clears them all. A clip runs its own chains first, then its scene's, then its track's. See [Chains](CHAINS.md). |
| Pattern order | Which pattern of the list comes next, each pass through the list (see Pattern Lists below). |
| Step direction | Overrides the play direction of the steps inside each pattern of the list, and of the pattern the clip morphs to. `Bksp` goes back to each pattern's own direction, shown as `forward (from pattern)` or the like, or `(each pattern)` for a list of several. |
| Repeat | How many times the clip plays its whole list of patterns, from 1 to 9999, before staying silent while the scene's other clips finish. |
| Loop | Plays the clip until the scene's longest clip that doesn't loop is done. `Space` or `ENTER` toggles it. |
| Morph to | With Repeat above 1, a second pattern to change into across the repeats. |
| Morph direction | `left`, `right` or `middle`: where the change sweeps in from. |
| Velocity | How loud the clip plays, as a percentage of each note's written velocity, over its scene's Velocity. Blank takes the scene's, shown as `80% (from scene)`, or 100%. See [Velocity and Velocity Ramps](SCENES.md#velocity-and-velocity-ramps). |
| Grab track | Another track in the scene, whose notes the pattern's Grab steps play. `Bksp` sets none. |
| Advance | What the clip does in real-time playback when it finishes, as described under Advance below. `ENTER` chooses. A clip that sets none shows the set's default, such as `With Scene (from set)`. |
| + Strum | A section, closed until opened, like the track editor's: Strum direction `(track)` takes the track's strum, shown as the direction it takes, such as `down (from track)`, `off` strums nothing whatever the track says, and any other direction strums this clip its own way. See [Strum](generators/STRUM.md). |
| + Velocity Ramp In, + Velocity Ramp Out | Sections, closed until opened, like the Scene page's, that fade this clip in and out. Each field set here wins over the scene's. See [Velocity and Velocity Ramps](SCENES.md#velocity-and-velocity-ramps). |
| + Density, + Articulate | Sections, closed until opened, like the Scene page's, shaping this clip across its own length. A shape set here wins over the scene's, and a generator in the clip's chains wins over both. |
| + Set Registers, + Increment Registers | Sections, closed until opened, that set each register to a value as the clip starts and add an amount every time the clip's pattern starts over. See [Set Registers and Increment Registers](REGISTERS.md#set-registers-and-increment-registers). |
| + Bypass Generators When, + Skip Playback When | Sections of statements about the registers, read each time the clip's pattern starts over: the first lets a pass go by the clip's generators untouched, and the second makes the clip sit a pass out. See [Conditional Execution](REGISTERS.md#conditional-execution). |
| Play, Stop | Buttons under the settings, which do what `L` (Listen) does: play the clip in real time as its scene would, with its chains, grabs, scale and direction, again and again until `L` is pressed again or Stop is. When the clip's track has no instrument, a list asks which of the set's instruments to listen through, for this listening alone. While the Real Time switch is off, the clip plays through General MIDI in [FluidSynth](FLUIDSYNTH.md) instead, the piano, or the drum kit for drums. See [Playing Live](PLAYING_LIVE.md). |

## Pattern Lists

A riff-based song is often a few bars said in different orders: the riff three times and then an answer, or three bars of a beat and a fill. A clip's list of patterns writes that down directly. The patterns play one after another as one long pattern, each at its own step size and in its own direction, and Repeat counts passes through the whole list. A pattern may be in a list more than once, and is named, never copied, so a change to the pattern is heard everywhere the pattern is listed. Drum patterns and patterns of notes never share a list. On Arrange, a clip of several patterns shows its first pattern and a count of the others, such as `riff-a +3`.

Pattern order chooses which pattern comes next. Every order plays every entry of the list once a pass, so a pass always lasts the same time. The names are the pattern directions, each meaning for whole patterns what the direction means for steps. For a list of `a`, `b`, `c`:

| Pattern order | First pass | Second pass |
| --- | --- | --- |
| forward | a b c | a b c |
| reverse a | a c b | a c b |
| reverse b | c b a | c b a |
| alternate | a b c | c b a |
| pendulum | a b c | b a c |
| random | drawn | drawn again |
| first, then random | a, then the others drawn | a, then drawn again |

A Restart When or Stop When statement on a step of any pattern in the list acts on the whole list: the list starts over, or the clip stops.

## Morphing

Morph to and Morph direction appear only when Repeat is above 1, and setting Repeat back to 1 removes the morph. The pattern being morphed to is looped or cut to the clip's length, and follows the clip's Direction when the clip has one; otherwise it follows its own pattern's direction, so a clip set to `eitherway` can finish its morph playing the second pattern backwards. A pattern with no notes morphs too, carrying its CC values and register changes across. The pattern being morphed to never grabs, and uses the registers without adding to them.

## Grabbing Notes

Grab track works like the Cirklon's note grab, and changes only the steps that the pattern's Grab row marks. Each marked step plays the note that the other track most recently started, at or before that step: the note the other track is playing, or the last note it played if it is silent. If the other track hasn't played anything yet, the step keeps its own note, or stays silent if the step has none.

When the other track plays a chord, the step takes the chord's root, the note the chord was built on, whatever its inversion or voice leading. A grab step with nothing on its Chord row plays that one note, and a grab step with a chord on its Chord row plays the chord with the grabbed note at the bottom: when the bass plays D and the step's chord is `m7`, the step plays D, F, A and C. The scale chords, `3` to `13`, add notes of the clip's scale above the grabbed note. A grab hears the other track after that track's chains run, so grabbing from an arpeggiated track takes the arpeggio's notes. Every other step, and everything else about the clip, such as its rhythm and velocity, stays the clip's own, and the grabbing track's transpose still applies.

Because grabbing is set on the clip, one pattern can grab from different tracks in different clips. A clip can grab from a track that grabs from another, but never in a circle: the clip page refuses a grab that would close a circle and says which clips to change, pasting a clip drops such a grab, and a set file with a circle stops exporting with a message naming the tracks.

## Advance

Advance is Live's follow action: what a clip does in real-time playback when it finishes. No export reads it.

- "With Scene" starts the clip directly below when the whole scene is done.
- "Next" starts the clip directly below as soon as this clip's own repeats end, whatever the rest of the scene is doing.
- "Off" starts nothing, so the track falls silent until something launches it.

A scene is done when every clip in it that doesn't loop has finished its repeats. A looping clip loops on until the scene below starts, so a scene whose every clip loops plays until you start something else. When the scene below has Launch together on, a start reaching any of its clips launches the whole scene and stops everything still playing in the scene above. A clip that sets nothing shows the File/Global page's Default follow action as its own.

## Clip Strum and Chains

A clip's sections set its own strum and shapes, over those of its track and its scene. In `examples/learning/13_classic_strum.yml`, this clip strums by the beat with a tight spread:

![A clip's Strum section open](screenshots/clip_strum.svg)

`ENTER` on a clip's Chains field opens the list of chains the clip runs, where `A` adds one:

![A clip's chains](screenshots/chain_list.svg)
