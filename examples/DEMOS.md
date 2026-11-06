# Demos

The songs in this folder whose names end in `_demo` are meant to teach, while the others, like
`acid_techno.yml`, are meant to sound good. Each demo takes one feature of llamatron and shows
it a scene at a time, so you can hear what the feature
does and read how it's set up. Most of them play a well-known tune, so that you can hear what a
feature changes.

Open any of them in the tracker to look around:

```
llamatron examples/arpeggiator_demo.yml
```

Or render one straight to a Live set, then open it in Live and put an instrument on each track:

```
llamatron examples/arpeggiator_demo.yml --to ableton --replace
```

Live names every clip after its scene, so the cells in Session View say what each one shows.
Launch the scenes from the top, one at a time. Every demo also has a description, which
explains it in more detail than this page and says what to keep in mind when changing it. It's
at the top of the file, and in the tracker, `D` on the Song page shows it.

## The demos

### Scales: `scale_demo.yml`

Every scale llamatron knows, each run up an octave and back down from D, one scene per scale, in
the order of the scale picker. Use it to preview a scale before choosing one. It shows that a
scene can set its own scale, and that a degree past the top of a scale wraps up an octave.

### Arpeggiator: `arpeggiator_demo.yml`

The verse of What Shall We Do With the Drunken Sailor, with its chords played through a different
arpeggiator in every scene: step lengths, orders, octave ranges and jumps, offsets, and then
combinations of them. The tune plays alongside, plainly, so you can mute it and hear only the
arpeggio.

### Ratchets: `ratchet_demo.yml`

The first line of Ode to Joy, slowed down to long notes, and then chopped up. The scenes named
Ratchet use a pattern's own Ratchet, Ratchet offset and Probability rows. The scenes named
AutoRatchet leave the pattern alone and do the chopping in a chain instead.

### Chains: `chain_demo.yml`

Simple Gifts on a single track, growing from a plain tune into a hymn, then synthwave, then happy
metal, using only five patterns and a chain for each scene. It shows that a chain runs its steps
in order, so an arpeggiator followed by an AutoRatchet sounds different from the other way round.

### Grabs and hocketing: `grab_demo.yml`

The Wellerman, held by a muted track called SILENT melody, with four other tracks taking turns
to play its notes by grabbing them. That's called hocketing. Give each voice a different sound
to hear the tune pass between them.

### Arranging with few patterns: `arrangement_demo.yml`

The Wellerman again, with eight parts built from only four note patterns. The harmony is the
melody patterns transposed on its track, the bass grabs the roots of the pad's chords, and a
counter-line grabs the melody in its own rhythm. Read this one to see how to set up a song so
that changing one pattern changes every part that follows it.

### Morphing: `morph_demo.yml`

A 16-step minimal techno groove whose bass and lead slowly turn into other patterns over 8 or
16 bars, in each morph style. The lead turns into the opening of Für Elise.

### Directions: `direction_demo.yml`

The theme of In the Hall of the Mountain King played in each of the step directions, from
forward and the two reverses to pendulum, random and brownian. It also shows that a clip's
direction overrides its pattern's.

### Classical, with only patterns: `basic_classical_demo.yml`

The opening of Pachelbel's Canon in D for three violins and a cello, using nothing but patterns
and scenes, the way you might copy a score in. Because it's a canon, the violins share the same
patterns, each a scene behind the one before.

### A whole piece: `entertainer_demo.yml`

All of Scott Joplin's The Entertainer, with its repeats, about four minutes. Each scene is four
bars, lining up with the sheet music, and the right and left hands are on separate tracks. It's
here to show how a long piece feels in the tracker, with over a hundred patterns. A pattern
plays one note or one chord symbol at a time, so each hand is split into three voices: treble 1
is the melody, treble 2 and 3 the notes under it, bass 1 the lowest note of the left hand, and
bass 2 and 3 the notes above it.

## Silent tracks

A track whose name has SILENT in it is muted: its settings have `mute: true`, so Live starts
with it switched off. Its clips are still written, so you can switch it on to hear what's
there, and other tracks can still grab notes from it. That's what silent tracks are for.

## Where the tunes come from

Every tune is in the public domain. The notes and tempos were taken from these transcriptions,
and each demo's description says which one it used:

- Drunken Sailor, Simple Gifts, Ode to Joy, In the Hall of the Mountain King and Pachelbel's
  Canon: the transcriptions at [flutetunes.com](https://www.flutetunes.com), using their tempos.
- The Wellerman: the sung setting, with lyrics and chords, at
  [The Session](https://thesession.org/tunes/20383) (setting 8). No original tempo is known,
  so 100 BPM is an estimate.
- Für Elise: written from the well-known opening.
- The Entertainer: the [Mutopia Project](https://www.mutopiaproject.org)'s typesetting of the
  1902 edition, which its typesetter placed in the public domain, at its tempo of 72.

`test/demo_sources/make_demos.py` wrote the first version of every demo, from notes written
into it and, for The Entertainer, from `test/demo_sources/entertainer.mid`, which is kept there
with its LilyPond source so that nothing has to be downloaded again. Running it overwrites every
demo, including any changes made by hand, so it's only for starting over.

The tests load, render and save every demo on each run, without checking what they play, so
editing a demo is safe as long as it still loads. They also run the generator into a temporary
folder and check what it writes against its sources: that The Entertainer it makes plays the
notes of `entertainer.mid`, and that the hocketing voices it makes add up to the melody.
