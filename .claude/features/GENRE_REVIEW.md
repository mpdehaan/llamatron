# The Band Genres' Review

What Claude understands of a music expert's review of the band genres' style templates (rock, sixties pop, soul and funk, blues,
experimental), and what was agreed with the user about it. The review was read from a file of the user's outside the repository;
nothing of it is copied here, no band, player or work is named, and no melody is written down. The reviewer read the templates
and never the code, and heard nothing, so every number is a starting point to correct by ear, one subgenre at a time. A subgenre's
own figures, shares, forms and chords are read from the review when that subgenre is worked on, with the user's leave for the path.

## The One Idea

A template holds a genre's notes and not yet its decisions: who the band is, what each section is for, how long a thing lasts,
what is emphasised, how the players relate, and what makes this song itself. A result sounds generic where those were not decided.

## Agreed, In The Order It Is Built

One genre at a time, rock first, alternating with the electronic stages (band step 1 for rock, electronic stage 1, and so on).

1. **Data only.** Shares by subgenre on every trait, so that a value with no share for a subgenre is offered last and never drawn
   by chance; corrected drum and bass bars; forms with real bar counts (twelve-bar verses, sixteen-bar verses in fast songs, short
   intros in sixties pop); the chords by subgenre; a song plan for every genre with numbers by subgenre.
2. **A figure for each kind of section, and loudness levels.** A player's figure may differ in a verse, a chorus and a bridge, the
   default played where a section has none. Loudness is four named levels in a bar, ghost, soft, normal and accent, each
   instrument's numbers in the template and by subgenre; values between them come from offsets, a beat profile by subgenre and
   phrase offsets (a line's highest and longest note louder, its last softer, the bar before a bigger section climbing); a small
   random amount last. A player's panel has a closed Loudness heading with a Dynamics gauge, flat to dramatic, and the four numbers.
   Loudness and timing are apart: a song may be on the grid and strongly accented.
   Built: the four levels, the snare's ghost notes, the lean on the beat for the drums in funk and the ballads, Dynamics and the
   Loudness heading (`.claude/features/MACRO_COMPOSER.md`, "Loudness levels"). A figure for a kind of section is built too, with the first
   verse and chorus figures written. Waiting: a gate by section, figures by section for the keys, horns and voices, the lean on
   players of notes, the phrase offsets and the random amount.
3. **The controller ramp**, straight after the loudness levels (`.claude/IDEAS.yml`): organ loudness and rotary speed, string and
   pad entries, the piano's pedal and the electronic rises wait on it. Pitch bend waits; grace notes and late vibrato stand in.
4. **The riff done as the review has it**, proved on hard rock: one or two bars said four times, mostly the root, starting on the
   root on beat 1, two to four accents off the beat as power chords with short muted roots between, a tail that leads back, a gap
   for the voice; the bass an octave under or on its accents; the kick on its accents. It stays on the home chord, moves whole, or
   changes its tail into the next chord. The guitar alone says it before the band comes in.
   Built, and on by default in hard rock (`.claude/features/MACRO_COMPOSER.md`, "A riff of chords on its accents"), but for the tail
   that changes into the next chord and the guitar alone before the band.
5. **One staged section** for long solos, jams and drum solos: passes round the chords, stages of 8 or 16 bars each with one
   device (theme, answering, repeated figure, climb, held notes, stops, a second player trading, together, peak), never the same
   twice running, the band rising a step a stage, an Energy that climbs across it. A jam is the same on a vamp of one or two
   chords with two or three waves of falling and building, the lead passing between guitar and keys, a stretch where both weave,
   a change of feel or mode, and the song's riff as the way back. A drum solo's stages: the riff's rhythm, round the kit, triplets
   between hands and foot, quiet, over a steady foot pattern (which lets a listener follow), rolls, peak, and a call that cues
   the band. A closing solo may jump the tempo, creep faster and end by slowing into a held chord.
   Built so far: each solo after a song's first takes another shape with ideas of its own (`.claude/features/MACRO_COMPOSER.md`,
   "Staged solos"). The stages inside one solo, the jam and the drum solo's stages are not built.
6. **A monotony report** in `internal_tools/`: for each player and section, the share of bars the same as an earlier bar, run
   before and after each step.
7. **Instruments, in this order:** keyboard solos with organ and piano backing; backing singers; horns; strings.

## Ideas Kept For Their Step

- **Fills by the join.** The plan owns fills in every genre: a marker at a 4-bar phrase's end, up to a beat at an 8-bar phrase's
  end, half a bar into a new section, a whole bar into the last chorus. A level changes how a fill is played, never how often.
  Blues keeps a small fill at bars 4 and 8 and a larger at bar 12.
  Built (`.claude/features/MACRO_COMPOSER.md`, "Fills by the join, and markers"), but for half a bar against a whole bar as sizes
  of their own.
- **What a level never does:** change the kick or snare that names the subgenre, fill over the tune, move the bass off the root
  on a new chord's first beat, play more when Energy is low, or decide placement. Ahead of or behind the beat is a trait of its own.
- **Chords:** two chords in a bar, a chord over two bars, a quality for every degree (triad, sevenths, ninth, power), and a
  progression that says its own length so that a section takes it.
  Two chords in a bar are built (`.claude/features/MACRO_COMPOSER.md`, "Two chords in a bar"), with the blues' turnarounds.
- **Swing** by subgenre as a percent, applied as the song's groove.
  Built with the factory grooves (`.claude/features/MACRO_COMPOSER.md`, "Swing by subgenre"); a percent of the song's own is not.
- **Monotony's remedies:** a section changes one thing at its halfway point; its last bar leads somewhere; a return differs; a
  verse and a chorus have several shapes; the band does a thing together (a pushed chord, a bar of stops, a unison tail); one
  chord swapped on a second pass; which bars vary is drawn per song; the answering player rotates.
- **Hooks:** one, two or four bars; kinds of answer (lower on the same rhythm, the last notes again, one long note, left to an
  instrument, none); a hook that ends the line; several plans of a chorus; the verse avoiding the hook's top note and rhythm.
  Two checks: the hook's rhythm differs from every verse line's, and the hook holds a cell that repeats. A catchy song stacks
  several simple hooks, reaches the chorus within a minute, and leaves a gap after the hook.
- **Structure by subgenre:** how many verses before a chorus, section lengths, and how likely a chorus, a pre-chorus, a bridge, a
  solo, a fade and a key lift are; the Form questions' usual answers and another take's draw come from these.
- **Percussion** comes in by Energy, usually at the chorus; more kinds as bars (shaken tambourine, shaker, maracas, clap figures).
  Coming in by Energy is built (`.claude/features/MACRO_COMPOSER.md`, "Percussion by Energy"); the new kinds of bar are not.
- **Who solos** by subgenre: keys and horns far more often than the templates have. A solo style is a block of the lead writer's
  settings with devices and how often each is used: ladder, notes a bar, share of silence, phrase length, long notes and where
  they land, placement, register. Guitar styles by plain name: slow singing, blues-rock, chordal, sustained, tapped, riff-rock,
  classical speed, twin harmony, slide, echo. Keyboard devices as notes: a sequence, a crushed note, a trill, a smear, a tremolo,
  a glissando, a left-hand figure, octaves. Saxophone: honk, scoop, fall, scream, riff, turn, and a breath every four bars.
- **Organ:** one velocity; loudness by an expression controller; notes shared by two chords tied; very short comped chords; two
  or three notes with the root left to the bass; fourths and fifths under distortion; rotary speed as a controller, sped up a bar
  before a chorus; it rests for whole sections and comes in with a swell. Roles: pad, comping, vamping, bubbling, stabs, swell,
  riff, held top note, left-hand bass, smear.
- **Piano:** a left and a right figure; the left thins when a bassist plays; a chord's top note louder; chords rolled slightly on
  slow songs; the sustain pedal pressed after each new chord. Kinds of backing by plain name, each a rule for each hand.
- **Synthesizer** in a band: pad, riff, block chords over one bass note, sequence, lead with glide, bass, doubling, strings.
- **Backing singers** are made after the lead is phrased, stop together, are softer than the lead and never cross it; jobs: with
  the tune, three parts, held vowels, echo, answer, unison shout, wordless figure, the lift, descant. A plan by kind of section.
- **Horns and strings** as optional groups in every genre, sized on the Band panel, each with a job by kind of section and an
  Energy under which they are silent; one pad at a time; ranges held; each player a track.
- **Written echo:** a note again three sixteenths later at half its velocity, and once more at a quarter.

## Waiting For A Discussion Of Their Own

Strains (a set of picks drawn whole inside a subgenre, shown as Variant under Subgenre); a lean toward jazz or math in three
strengths, each value it sets saying so; a kept band; a song's one signature device; a Sharing setting for how much room the
players leave (in unison, interlocking, arranged, loose, all at once), two rules always on: shared accents and one player on top
in a solo; kinds of drummer by plain name (the composer, the heavy hitter, the polyrhythmist, the wild one), a type able to switch
a rule off; new rock subgenres (psychedelic, space, jam, math) and metal.
