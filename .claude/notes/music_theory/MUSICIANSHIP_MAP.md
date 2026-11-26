# The Map of Musicianship

How the bodies of musical knowledge fit together, for building the
`music_theory` package and every feature that asks it. Mostly practice; the
order of analysis and the warnings are judgment.

## The Bodies of Knowledge, in the Order They Depend on Each Other

1. **Pitch**: pitch classes and spelling, intervals, consonance by context
   (melodic, harmonic, against the bass), register and the low zone where
   close intervals turn to mud.
2. **Collections**: scales and modes, keys and how near two keys are, chord
   qualities, tensions and avoid notes, voicings.
3. **Harmony**: function (home, away, wanting home), progressions and their
   families, cadences, borrowing and secondary chords, harmonic rhythm,
   modulation, reharmonization that keeps each melody note's role.
4. **Voice leading**: kinds of motion, the nearest move, tendency tones
   resolving; the classical rules are preferences a style turns up or down.
5. **Time**: meter and beat strength, accent profiles (backbeat, four on the
   floor, swing), syncopation, push and drag.
6. **Groove**: the kit's voices by job (time, backbeat, colour, punctuation),
   beats as roles rather than notes, fills by size and by where they lead,
   kick and bass locking.
7. **Melody**: contour and one climax, chord tones against passing, neighbour
   and suspended notes, motif and its development (repeat, sequence,
   inversion, augmentation, fragmentation), singability (range, recovering
   from a leap, breath).
8. **Form**: phrase, period and sentence, open and closed endings, section
   kinds, joins, the energy arc, how parts change from one section to the
   next.
9. **Arrangement**: roles in a band (tune, counter-line, comping, pad, bass,
   groove, colour), texture, who leaves room for whom, register allocation,
   doubling.
10. **Performance**: dynamics by section and role, articulation, a player's
    decoration of a plain part.
11. **Style**: genres as layers of habits with shares over everything above,
    each with a parent.
12. **Perception**: tension from harmony, dissonance, register, density and
    rhythm; expectation; repetition against novelty.

## Four Kinds of Statement (judgment)

Facts (definitions and arithmetic); principles with a reason and exceptions;
preferences, which are costs and never refusals; and style data with measured
shares. Most of what is called theory beyond intervals is preference. A style
can turn any preference to nothing: a techno loop without a cadence, or
parallel fifths in a power-chord riff, is never a fault.

## Reading a Song, in Order (judgment)

Each step leans on the ones before, and confidence falls as it goes, so each
answer carries its confidence and a runner-up: grid and tempo (given in
llamatron); the roles of the tracks, by behaviour rather than name (the lowest
sustained line is the bass, the highest and most varied the tune); key and
mode, weighting long notes, strong beats and the bass's last notes (the
relative minor is often a coin toss); chords, cut at the harmonic rhythm and
named by the tones on strong beats with the bass first; functions and
cadences; phrases, from cadences and the tune's rests; form, from which
sections resemble each other (boundaries are surer than names); motifs and
hooks under transformation; groove; the energy curve, honest only as relative.

## What Accompanying and Fixing Need (practice)

- A bass from chords: roots on strong beats, approach notes, inversions for a
  smooth line, locking with the kick.
- Comping and pads: voicings near each other, below the tune, rhythms that
  leave the tune room.
- A counter-line: contrary motion, active where the tune rests, consonant on
  strong beats.
- Harmonizing a tune: chords whose tones cover its long and strong notes,
  chosen by function and the style's progressions.
- Drums for a song: the kit's vocabulary by section, fills scaled to how much
  the next section rises.
- Fixing is a failed principle plus the least change that satisfies it: a long
  off-chord note on a strong beat that never resolves; a section that never
  arrives; voices crowding the same octave or a close interval low down;
  nothing changing across sections; a hook never repeated or placed; every
  part hitting the same places; a tune outside a singable range; a last chorus
  no bigger than the first.

## Warnings (judgment)

- Textbook theory is mostly about chorales and functional harmony. Much
  electronic, funk, metal and drone music is modal, riff-based, static,
  timbral or rhythmic first; groove, texture, energy and repetition are as
  central as harmony.
- Rules that refuse make prim music; costs and explanations do better.
- An analysis that states one answer misleads whatever acts on it.
- Render-time code reads tables worked out once, never walks rich theory
  objects per note.

## Where llamatron's Code Holds Music Today (a convenience, never a limit)

- The octave's twelve is defined in about ten places; chord knowledge exists
  three times: `model/values/` (scale, chords, progressions), the song
  wizard's `melody.py` (its own half-step tables, `chord_notes`, which treats
  any chord with a sharp or flat as major), and the measuring tools under
  `py_legacy/internal_tools/analysis_and_generation/measuring/hearing/`.
- The wizard holds theory that belongs in the package: unstable degrees for
  open endings (`melody.py`), long notes against the chord and short ones
  passing (`music_theory/harmony/tune_fit.py`), feels and beat levels
  (`music_theory/composing/shaping.py`), hook rhythms counted in eighths of a
  4/4 bar (`music_theory/hooks/tag_bars.py`, the hook's own bar in
  `hook_bars.py`), joins and fills by energy
  (`music_theory/composing/joins.py`, `section_joins.py`), making room for the
  tune (`interplay.py`), loudness by section and role (`loudness*.py`),
  section plans (`song_plan.py`), and families of progressions inside the
  style templates.
- The munges (`model/objects/pattern_munges.py`) are musical transformations;
  the Chords generator's following and voicing (`engine/generators/chords/`)
  are chord-scale theory and nearest-voice motion; the Musician generator's
  backing off is interplay.
- The words "cadence" and "tension" appear nowhere in the code.
