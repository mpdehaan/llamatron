# Clips

A clip is what a track plays in a scene: a pattern, and the settings that
change how the pattern plays there. This page covers the clip page.

![The Clip page](screenshots/clip.svg)

## Clips on Arrange

A clip sits where a scene's row and a track's column meet on Arrange, so the
clip page's crumb pairs the two, such as `ARRANGE › clip: (verse, bass)`. The
crumbs always say where `ESC` goes back to. The pattern editor opened with `P`
from a clip reads `ARRANGE › pattern: bass line` when opened from Arrange,
`ARRANGE › clip: (verse, bass) › pattern: bass line` when opened from the clip
page, and `PATTERNS › bass line` only when the Patterns page opened it.

## Clip Settings

The clip page shows the clip's Name and its list of Patterns, then a box of
tabs holding the rest of its settings, then a Listen button. The tabs are
Settings, then Velocity, Shapes and Reset Draws, then the generators in the
order the clip runs them: Chords, Arp, Guitarify, Timing and Phrasing, the
built-in generators, and last More Generators, whose generators run after
every built-in, on what the built-ins made.

In the list of Patterns, `A` (add pattern), or ENTER on `+ (New)`, adds a
pattern at the end of the list: one the set has, of the clip's kind, or a new
blank one named after the track. `Bksp` takes the pattern under the cursor out
of the list, which deletes no pattern, though a clip always keeps one. `M`
(move pattern) picks the pattern up, `↑` and `↓` carry it along the list, and
ENTER, ESC or `M` drops it, the whole move one undo step. `J` (jump to pattern)
opens the pattern under the cursor.

On the row of tabs, `←` and `→`, or `[` and `]`, choose a tab, stopping at the
first and the last; `↓` goes into the tab. Inside it, `↑` and `↓` keep to a
column: at a column's foot `↓` leaves the box for what is below it, and `↑`
from below comes back in at the foot of the first column; `←` and `→` go to
the setting beside in the next column, the nearest by line, and change
nothing. `[` and `]` change a value, and `ENTER` types or chooses one. `Tab`
goes to the row of tabs from anywhere on the page. The tab chosen stays chosen
on the next clip page until another is chosen. Where the tabs are wider than
the box, `<` and `>` stand at the ends for the tabs hidden that way. The box
keeps the height of its tallest tab, so choosing a tab moves nothing below it.

| Setting | What it does |
| --- | --- |
| Name | A name of the clip's own, shown on the grid and used for the clip in Live and in the clip tree's file names. Without one, the clip goes by its pattern's name. `Bksp` clears it. |
| Patterns | The patterns the clip plays, one after another, as one long pattern (see Pattern Lists below). A clip of 1 pattern is a list of 1. `A`, or `ENTER` on the `+ (New)` row, adds a pattern; `Bksp` takes the pattern under the cursor out of the list, which deletes no pattern; `M` picks the pattern up, the arrows carry it and `ENTER` drops it; `ENTER` or `J` opens the pattern in the pattern editor, and `ESC` comes back. |
| Listen | A button under the box, which does what `L` (Listen) does: it plays the clip in real time as its scene would, with its generators, grabs, scale and direction, again and again until `L` or the button is pressed again, the page is left or a song is played from Arrange. When the clip's track has no instrument, a list asks which of the set's instruments to listen through, for this listening alone, except on a drum track, which plays General MIDI's drum kit in [FluidSynth](FLUIDSYNTH.md) where it is installed. While no track of the song plays through an instrument that can sound, the clip plays through General MIDI in [FluidSynth](FLUIDSYNTH.md) instead, the piano, or the drum kit for drums. See [Playing Live](PLAYING_LIVE.md). |

The Settings tab has two columns. Order says how the clip plays its patterns:

| Setting | What it does |
| --- | --- |
| Pattern order | Which pattern of the list comes next, each pass through the list (see Pattern Lists below). |
| Step direction | Overrides the play direction of the steps inside each pattern of the list, and of the pattern the clip morphs to. `Bksp` goes back to each pattern's own direction, shown as `forward (from pattern)` or the like, or `(from each pattern)` for a list of several. |
| Repeat | How many times the clip plays its whole list of patterns, from 1 to 9999, before staying silent while the scene's other clips finish. |
| Loop | Plays the clip until the scene's longest clip that doesn't loop is done. `Space` or `ENTER` toggles it. |
| Morph to | With Repeat above 1, a second pattern to change into across the repeats. |
| Morph direction | `left`, `right` or `middle`: where the change sweeps in from. |
| Follow action | What the clip does in real-time playback when it finishes, as described under Follow Action below. `ENTER` chooses. A clip that sets none shows the set's default, such as `With Scene (from set)`. |

Playing holds the rest:

| Setting | What it does |
| --- | --- |
| Scale | A scale of the clip's own, which wins over the scene's and the song's, so that one track can play in another key or mode. `ENTER` picks one, and `Bksp` goes back to the scene's, shown with where it comes from, such as `A Minor (from scene)`. |
| Grab track | Another track in the scene, whose notes the pattern's Grab steps play. `Bksp` sets none. |

The other tabs:

| Tab | What it holds |
| --- | --- |
| Velocity | Across its top, the clip's Velocity: how loud it plays, as a percentage, stacking on its scene's, its track's and its instrument's, blank being 100%. Under it, Velocity Ramp In and Velocity Ramp Out, like the Scene page's, which fade this clip in and out; each ramp field set here wins over the scene's. See [Velocity and Velocity Ramps](SCENES.md#velocity-and-velocity-ramps). |
| Shapes | Density and Articulate, like the Scene page's, shaping this clip across its own length. A shape set here wins over the scene's, and a generator the clip runs wins over both. |
| Reset Draws | A Reset toggle for each draw that holds a value in the song, which sends the draw back to its first slot as the clip starts, on its scene's first play alone. See [Draws](DRAWS.md#reset-draws-on-a-scene-and-a-clip). |
| Chords, Arp, Guitarify, Timing, Phrasing | The clip's built-in generators, one of each, with the settings of the generator's own page: Enabled first, then its Mode where it has one, then its columns. A built-in is off until Enabled is switched on; its tab shows `●` after its name while on and `○`, dim, while off. A clip's built-in that is on stands in for its track's of the same kind. They run in that order, all before the clip's list of generators. `ENTER` on a part, such as the Arp's Offsets, opens that part's page on the clip's built-in. See [Generators](GENERATORS.md). |
| Generators | On the More Generators tab, the Generators field: the generators of the set the clip runs, in order, each shown with its kind, such as `Chain: fills, Timing: rolls`. `ENTER` opens the list, where `A` adds any of the set's generators, a chain among them, `M` moves one and `Bksp` takes one out; `Bksp` on the field clears them all. A clip runs its own list first, then its scene's, then its track's. See [Generators](GENERATORS.md) and [Chain](generators/CHAIN.md). |

## Pattern Lists

A riff-based song is often a few bars said in different orders: the riff three
times and then an answer, or three bars of a beat and a fill. A clip's list of
patterns writes that down directly. The patterns play one after another as one
long pattern, each at its own step size and in its own direction, and Repeat
counts passes through the whole list. A pattern may be in a list more than
once, and is named, never copied, so a change to the pattern is heard
everywhere the pattern is listed. Drum patterns and patterns of notes never
share a list. On Arrange, a clip of several patterns shows its first pattern
and a count of the others, such as `riff-a +3`.

Pattern order chooses which pattern comes next. Every order plays every entry
of the list once a pass, so a pass always lasts the same time. The names are
the pattern directions, each meaning for whole patterns what the direction
means for steps. For a list of `a`, `b`, `c`:

| Pattern order | First pass | Second pass |
| --- | --- | --- |
| forward | a b c | a b c |
| reverse a | a c b | a c b |
| reverse b | c b a | c b a |
| alternate | a b c | c b a |
| pendulum | a b c | b a c |
| random | drawn | drawn again |
| first, then random | a, then the others drawn | a, then drawn again |

A Restart When or Stop When statement on a step of any pattern in the list
acts on the whole list: the list starts over, or the clip stops.

## Morphing

Morph to and Morph direction appear only when Repeat is above 1, and setting
Repeat back to 1 removes the morph. The pattern being morphed to is looped or
cut to the clip's length, and follows the clip's Direction when the clip has
one; otherwise it follows its own pattern's direction, so a clip set to
`eitherway` can finish its morph playing the second pattern backwards. A
pattern with no notes morphs too, carrying its CC values across. The pattern
being morphed to never grabs.

## Grabbing Notes

Grab track works like a step sequencer's note grab, and changes only the steps that
the pattern's Grab row marks. Each marked step plays the note that the other
track most recently started, at or before that step: the note the other track
is playing, or the last note it played if it is silent. If the other track
hasn't played anything yet, the step keeps its own note, or stays silent if
the step has none.

When the other track plays a chord, the step takes the chord's root, the note
the chord was built on, whatever its inversion or voice leading. A grab step
with nothing on its Chord row plays that one note, and a grab step with a
chord on its Chord row plays the chord with the grabbed note at the bottom:
when the bass plays D and the step's chord is `m7`, the step plays D, F, A and
C. The scale chords, `3` to `13`, add notes of the clip's scale above the
grabbed note. A grab hears the other track after that track's chains run, so
grabbing from an arpeggiated track takes the arpeggio's notes. Every other
step, and everything else about the clip, such as its rhythm and velocity,
stays the clip's own, and the grabbing track's transpose still applies.

Because grabbing is set on the clip, one pattern can grab from different
tracks in different clips. A clip can grab from a track that grabs from
another, but never in a circle: the clip page refuses a grab that would close
a circle and says which clips to change, pasting a clip drops such a grab, and
a set file with a circle stops exporting with a message naming the tracks.

## Follow Action

Follow action is Live's word: what a clip does in real-time playback when it
finishes. No export reads it.

- "With Scene" starts the clip directly below when the whole scene is done.
- "Next" starts the clip directly below as soon as this clip's own repeats
  end, whatever the rest of the scene is doing.
- "Off" starts nothing, so the track falls silent until something launches it.

A scene is done when every clip in it that doesn't loop has finished its
repeats. A looping clip loops on until the scene below starts, so a scene
whose every clip loops plays until you start something else. When the scene
below has Launch together on, a start reaching any of its clips launches the
whole scene and stops everything still playing in the scene above. A clip that
sets nothing shows the File/Global page's Follow action, under Defaults as its own.

## Clip Chains

A clip's sections set its own shapes, over those of its scene. A strum comes
from a [Guitarify](generators/GUITARIFY.md) in Strum mode in the clip's
chains.

`ENTER` on a clip's Generators field opens the list of generators the clip
runs, where `A` adds one:

![A clip's chains](screenshots/chain_list.svg)
