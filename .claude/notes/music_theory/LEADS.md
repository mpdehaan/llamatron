# Leads

How a lead line, a guitar's above all, is composed. A note Claude wrote in
another conversation, kept nearly whole, names and all. (practice throughout)

Guitar leads are usually composed in one of three ways: improvised and then
fixed, written as a melody, or assembled from a vocabulary of licks. The
theory underneath is the same for all three. Land on the right notes at the
right moments, develop a small idea, and shape the whole solo into a story.

## Three Ways Leads Get Made

- **Improvise, then fix it.** Many famous solos started as improvisations. The
  player records take after take over the backing track, then keeps the best
  phrases or edits several takes together, and finally learns the result as a
  fixed part. David Gilmour's solos on "Comfortably Numb" are a well-known
  example of a solo edited together from several takes. Once a solo works, it
  is often played the same way live because the audience expects it.
- **Write it like a vocal melody.** David Gilmour, Brian May and Mark Knopfler
  are known for leads a person can sing. The approach is to treat the guitar
  as a second singer: hum the line first, then find it on the neck. Everything
  about hooks applies here (`HOOKS.md`): short phrases, repetition, one
  surprise, a contour with a peak. Pop and country solos often start by
  paraphrasing the vocal melody with ornaments, then break away from it.
- **Speak the language.** Blues and jazz players learn licks by transcribing
  other players, then recombine and bend them into their own phrases. It works
  like learning a language: fluency is built from stock phrases first, and new
  things are said with them after.

## The Core Theory: Target Notes

The idea that separates a lead that sounds deliberate from noodling in a scale
box is chord-tone targeting. Put chord tones on strong beats, especially at
the moment the chord changes. The strongest targets are the guide tones, the
3rd and 7th of each chord, because they define the chord's quality. Then
approach each target:

- by step from above or below,
- chromatically, from a half step away,
- with an enclosure: a note above, a note below, then the target.

There are two broad strategies. Playing over the changes means using one scale
for the whole progression, like minor pentatonic over a rock tune. It is easy
and sounds consistent, but it ignores the harmony. Playing the changes means
following each chord with its arpeggio or mode, as in jazz and much country.
It is harder and more specific.

The blues sits on purpose between the two. Players use minor pentatonic over
major chords, bend the flat 3 partway toward the 3, and mix major and minor
pentatonic. That friction between scale and chord is the "blue" sound.

A useful composing exercise is to write the skeleton first. Write a slow line
with one note per chord, moving by step through guide tones. Then decorate it
with passing tones, neighbor notes, arpeggios and bends. Baroque musicians
called this decoration diminution, and Schenkerian analysis is built on it: a
simple structural line underneath, elaborated on the surface. The solo sounds
free, but it is tied to the harmony.

## Developing an Idea

- **Motif development.** State a short idea, repeat it, sequence it up the
  scale, shift it rhythmically, extend it. A solo built from one motif sounds
  composed even when it is improvised.
- **Call and response.** Play a phrase, answer it, and leave space. B.B. King
  is the model. Phrases about the length of a breath sound like singing, and
  the gaps give the listener time to take them in.
- **Repeating licks against the meter.** Repeating a three-note lick over 4/4
  creates the same tension as a drummer's groups of three. It shows up all
  over classic rock solos as they build toward the climax.
- **Rhythmic variety.** Mix long held notes with fast bursts. Start phrases on
  different beats, not always on 1. Contrast triplets with sixteenths.

## The Arc

Most composed solos follow a shape:

- Start low, sparse and fairly slow.
- Build in register, density and intensity.
- Hit a climax, usually the highest note, the longest bend, or the fastest
  run, about two-thirds of the way through or at the end.
- Resolve back into the song.

This is tension and release at the scale of the whole solo, and it is why a
16-bar solo can feel like a short song inside the song.

## Technique as Composition

On guitar, much of a lead's identity is in how notes are articulated, not
which notes are played. Two players can play the same pitches and sound
nothing alike.

- **Bends**: half-step, whole-step, pre-bends, unison bends. Bending into a
  chord tone (2 up to 3, 4 up to 5, flat 7 up to the root) combines targeting
  and expression in one move.
- **Vibrato**: its width and speed are a player's fingerprint.
- **Legato**: hammer-ons, pull-offs and slides, for smooth fast lines.
- **Double stops**: two-note figures like Chuck Berry's.
- **Harmonics, tremolo picking, the whammy bar, volume swells.**

The fretboard shapes the lines too. Moving along one string gives a different
contour than moving across strings in one position. Three notes per string
makes fast runs easier. Alternating a moving line with an open string gives
the pedal-tone licks of Thin Lizzy and Iron Maiden, which descend from Bach's
violin writing.

## Genre Flavors

- **Blues**: minor pentatonic with the blue note, expressive bends, call and
  response with the singer.
- **Rock**: pentatonic boxes, repeating licks, double stops, a climactic bend.
- **Country**: major pentatonic with chromatic passing tones, hybrid picking,
  "chicken pickin'", bends that imitate a pedal steel guitar (bending one
  string while holding another).
- **Jazz**: guide-tone lines, bebop scales, enclosures, "outside" playing that
  slips a half step away from the key and back.
- **Neoclassical metal**: harmonic minor and phrygian dominant, sweep-picked
  arpeggios, scalar sequences in groups of four or six.
- **Harmony leads**: twin guitars in diatonic thirds or sixths (Thin Lizzy,
  Iron Maiden, the Allman Brothers), or Brian May's stacked guitar choirs.
- **Ambient and post-rock**: the delay is part of the composition. The Edge's
  dotted-eighth delay turns a simple line into interlocking rhythmic
  counterpoint.
- **Highlife and soukous**: bright, high, interlocking loops that cycle
  instead of building to a climax.

## In llamatron

Two parts of the model help here. Because patterns store degrees, a
twin-guitar harmony lead is the same pattern two scale degrees up, so it stays
in key automatically, with thirds that change between major and minor as the
scale requires. And the skeleton-then-decorate method could be a generator:
take a guide-tone line from the progression and add passing and neighbor tones
from the seed.

The gap is pitch bend. Pattern rows include CC lanes and a slide but no pitch
bend, and the import is said to drop pitch bend. For guitar-style leads on a
synth, a bend lane with ramps, plus an optional vibrato, would make the
biggest difference, since bends and vibrato carry most of a lead's expression.
(What llamatron has is to be checked against the code.)

## Synth Leads

- A synth lead sits about two octaves over the bass: the bass in octaves 2 and
  3, the lead's home in 4 and 5, its peak an octave higher. A lead in the
  bass's register is mud. To show an instrument's range, move a phrase up an
  octave for the last section rather than writing a wider line. (practice)
- Portamento and accent are marks, used rarely: a glide on one to three steps
  in sixteen, aimed at an octave jump or a target note, never into the same
  pitch, where it does nothing; accents on two to four steps a bar, mostly off
  the beat, best after a rest. Where the marks fall changes from section to
  section, not bar to bar. Marks on every bar become the line itself and
  sound squeaky and unsteady. (practice)
- The slide must finish inside one step at the song's tempo; a slide longer
  than the step leaves every note bending and sounds out of tune. (practice)
- Vibrato is delayed, narrow (about a quarter tone) and only on held notes;
  vibrato on every note of a square wave sounds seasick. (practice)
- On an acid voice an accent is a velocity at or over the instrument's accent
  threshold (Fishline: 110 by default), so a loud step is an accent whether
  meant or not: ordinary notes stay below it. The accent's filter climb
  belongs to the turnaround, once in four or eight bars, not every bar.
  (practice, and llamatron's mapping)
