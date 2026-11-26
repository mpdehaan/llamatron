# Arranging Advice, Question by Question

Advice on arranging, written in reply to 24 questions about the song wizard's
design, kept nearly whole: what one energy number flattens, what each player
does at each level, the curves of a song, how a section differs on its return,
joins and the harmony at a join, bridges, solo shapes, ornaments, trading,
hooks and riffs by kind, the hook in each electronic subgenre, what makes two
players different people, how a band shares space, section lengths, and what
gives a machine away in each genre. "Your" and "the sketch" speak of the
wizard's design at the time; the generators named are llamatron's. (practice
throughout)

## Where a Program Is Musically Naive: The Short List


1. **One energy number mixes up "big" and "busy".** They often move in
   opposite directions. A drummer at full energy plays fewer, heavier cymbal
   notes than at medium energy. Keep one visible number, but split it inside
   (Q1).
2. **Energy must not rewrite the tune.** A chorus tune has to be the same
   notes every time. Energy changes who doubles it and how it's decorated (Q2,
   Q14).
3. **Harmony at the joins is your largest gap,** larger than anything about
   fills. A fill into a section that the chords did not set up sounds pasted
   on (Q7).
4. **The band never does anything together.** Real bands push a chord an
   eighth early, stop together, and hit accents together. Nothing in the
   design does this (Q5, Q24).
5. **More gauges will not make players differ.** Players differ in vocabulary
   and in what they leave out. Scaling the same figure seven ways gives the
   same bassist seven times (Q17).
6. **"Peak two thirds through, then return" is the wrong default for a rock
   solo.** Most rock solos end at the top and hand off to the chorus. Blues
   and funk solos have other shapes entirely (Q9).
7. **"The opposite of what came before" is half right.** In a quiet song the
   bridge is the peak. The rule needs a budget of two or three contrasts and a
   list of things that never change (Q8).
8. **The tune needs to breathe.** A sung line played on an instrument with no
   rests is the fastest way to sound like a machine (Q24).
9. **Electronic music is not verse and chorus.** It needs its own section
   words, its own joins and the opposite attitude to variation (Q3, Q16, Q23).
10. **Velocity headroom.** If verses are written near 127, nothing can grow.
    Ordinary playing belongs at 80 to 100 (Q24).

---

## The model as a whole

### Q1. Is one energy number a sound spine?

It is a good spine and a bad skeleton. Keep it as the one number a beginner
sees. Do not let players read it directly.

What it flattens:

- **Size and busyness are different things.** A half-time chorus is huge and
  sparse. A funk verse is busy and quiet. A breakdown is small but tense.
- **Level and direction are different things.** A pre-chorus is not "energy
  6". It is "rising from 5 to 7". A section needs a slope as well as a level.
- **Tension is separate from both.** A held dominant chord with almost nobody
  playing has low energy and high tension.

What I would build:

- **Visible:** one Energy number per section, plus a small "within the
  section" choice: level, rising, falling. Rising is the default for a
  pre-chorus and for the last 2 bars before a big join.
- **Inside:** each subgenre template turns Energy into two values, **Size**
  (loudness, thickness, sustain, width of register, number of players) and
  **Busy** (notes per bar, subdivision). The mapping is a pair of curves per
  subgenre.
  - Rock ballad: Size rises steeply, Busy hardly moves.
  - Punk: both nearly flat and high. Contrast comes from drop-outs.
  - Funk: Size comes from adding players. No single part gets louder or
    busier.
  - House and techno: Size is the count of layers and how open the hats and
    filter are. Velocity barely changes.
- **Advanced users** get a second column to override Busy by hand. A beginner
  never sees it.

Three more rules that matter as much as the split:

- **Stagger the thresholds.** If every player changes at energy 5 and again at
  8, the band sounds like one switch. Give each player its own change points,
  with some players (a steady bassist) changing only twice across the whole
  range.
- **Contrast is what's heard.** A chorus at 8 after a verse at 4 sounds bigger
  than a chorus at 9 after a verse at 7. Add a song-wide Contrast setting
  (narrow to wide) that stretches or squeezes the curve.
- **Ten steps is more than players can express.** Each player really has four
  or five states. Use the fine steps for velocity and for who is in.

### Q2. What changes at energy 2, 5, 8 and 10?

Rock is the baseline in each table. The differences by genre follow.

**Drums**

| Energy | Timekeeping | Snare | Kick | Cymbals and extras |
|---|---|---|---|---|
| 2 | None, or soft closed hat or ride ticks | None, or cross-stick on 4 (or 2 and 4) | Beat 1 only, or none | No crashes. A shaker or tambourine can replace the kit |
| 5 | Closed hat eighths, beats accented | Full snare on 2 and 4, velocity near 95 | 1 and 3 plus one pickup | Crash on the section's first bar only |
| 8 | Half-open hat eighths, or ride | Rimshot strength (115+), a few ghost notes | Follows the bass, 3 to 5 hits a bar | Crash every 4 or 8 bars |
| 10 | Quarter notes on the crash or wide-open hat | Full. Snare on every beat only inside a build | Driving eighths or locked to the riff | Crash every 2 bars, tambourine on top |

The point a program gets wrong: from 5 to 10 the timekeeping hand plays
**fewer** notes (sixteenths or eighths closed, then eighths open, then
quarters on a crash). Weight replaces activity.

- **Sixties pop:** the drummer stays simple at every level. Energy lives in
  the percussion layer: tambourine on 2 and 4, then eighths, then sixteenths,
  plus handclaps. "Big studio" adds toms, timpani and castanets. Few crashes.
- **Soul:** the snare gets a companion on the backbeat (tambourine, handclap,
  guitar chop). The kit pattern changes little.
- **Funk:** the groove is the identity and barely changes from 4 to 10. Energy
  adds open-hat barks, more ghost notes and a harder accent on beat 1.
- **Disco:** four-on-the-floor at every level. Energy opens the hat on the
  offbeats, moves hats to sixteenths and adds congas.
- **Blues:** energy is almost all velocity. Slow blues runs from a cross-stick
  whisper to crashing triplets. Shuffles move from hat to ride.

**Bass**

| Energy | What the bass does |
|---|---|
| 2 | Silent, or one long low root per chord |
| 5 | Roots in the kick's rhythm, with a fifth or an approach note into each chord change |
| 8 | Steady eighth-note roots, or a moving line with passing tones. Octave jump at phrase ends, short runs into new sections |
| 10 | Eighths with octave leaps, higher runs at turnarounds, a pedal on V under builds, doubling the riff with the guitar |

- **Rock:** the top of the range is pumping eighths on the root. More notes
  than that sounds less powerful.
- **Sixties pop and soul:** the bass is melodic even at 5, with chromatic
  approach notes and syncopation. A root-bound bass is wrong here at any
  level.
- **Funk:** the opposite of rock. Space is the style. Energy adds sixteenth
  syncopation, dead notes and octave pops while staying locked to the kick.
- **Blues:** 2 is a two-feel (roots on 1 and 3), 5 is a walking boogie line in
  quarters, 8 is the shuffled eighth-note version.
- **Disco:** octaves from 7 upward.

**Rhythm guitar**

| Energy | What the guitar does |
|---|---|
| 2 | Silent, or single picked notes, or one held chord per bar |
| 5 | Palm-muted eighths on two or three low strings, or chops on 2 and 4 |
| 8 | Open strummed chords on 5 or 6 strings, ringing, eighths with a few sixteenths |
| 10 | Ringing whole-note power chords, or all-down eighths, with a second part doubling higher |

Guitarify already holds these states: its bars (chug, folk strum, arena, all
down, held), Strings, Let ring and Upstroke strings are exactly the dials
energy should turn.

- **Funk:** the guitar never gets bigger. Three top strings, sixteenth
  scratching, and energy changes only how many strokes sound against how many
  are muted.
- **Soul:** the backbeat chop with the snare, at every level.
- **Sixties pop:** picked arpeggios and jangle more than strumming.
- **Blues:** a boogie figure (fifth to sixth) at 5, ninth-chord stabs and
  slides at 8.

**Keys**

| Energy | What the keys do |
|---|---|
| 2 | One held note or a two-note pad, middle register |
| 5 | Three-note voicings, half notes or light syncopation, between C3 and C5 |
| 8 | Eighth-note chords on piano, or organ held at full expression, right hand adding an octave |
| 10 | Both hands, right-hand octaves or high tremolo, a glissando into the section |

Organ ignores velocity. Its energy is controller 11 (expression) and the
rotary speed, so the wizard has to write controller lanes for organ parts or
they will sound flat at every level.

**Horns** (soul and funk)

| Energy | What the horns do |
|---|---|
| 2 | Silent |
| 5 | Long soft notes, unison or two parts, behind the tune |
| 8 | Stabs in three-part harmony answering the tune, falls at phrase ends |
| 10 | A riff in octave unison in the top register, rips up into held notes, swells |

Horns must be silent for whole sections, usually the first verse. Unison
sounds powerful and harmony sounds wide, so save unison for the top.

**The tune**

| Energy | What changes |
|---|---|
| 2 | Lowest third of the range, short phrases, long rests |
| 5 | Middle of the range |
| 8 | Upper third, longer notes on strong beats, doubled a third above |
| 10 | The song's highest note, stacked harmony, a varied tail on repeats |

Read this table as a plan made when the tune is written (verse low, chorus
high), not as a live control. Energy applied per occurrence may change
doubling, harmony and the last notes of a phrase. It must never recompose a
chorus.

### Q3. Which preset curves are worth offering?

Keep your four and add these:

| Curve | What it does | Where it belongs |
|---|---|---|
| Slow burn | One long climb from almost nothing to the top at the end | Rock ballad, soul ballad, slow blues, southern soul, big studio |
| Starts big | Opens at 8, drops to the verse | Punk, bubblegum, british invasion, hi-nrg, disco |
| Loud and quiet | Verses at 3, choruses at 9, wide jumps | Hard rock, new wave |
| Adds a player each section | Terraced entry, nobody leaves | Funk, new orleans, house, minimal techno |
| Build and drop, twice | Intro, build, drop, breakdown, build, bigger drop, outro | House, trance, dubstep, drum and bass, big beat, electro |
| One long breakdown | As above, with a long quiet middle and the biggest peak after it | Trance |
| Chorus by chorus | Each 12-bar chorus a step higher, a dip where the solo starts, the top at the last chorus | Every blues subgenre, rock and roll |
| Comes home quiet | Builds to a peak, then a soft last verse or ending | Folk rock, folk pop, waltz ballad |
| Swell and fade | Rises slowly to the middle and recedes | Ambient, downtempo |

Two things beyond the list:

- "Level" is the right default for techno, minimal techno and funk, and it
  needs small variation inside it or it is dead.
- A "drop before the last chorus" (a stripped first pass of the final chorus)
  is a switch that can sit on top of any curve. Do not make it a curve of its
  own.

### Q4. How should verse 2 differ from verse 1, and chorus 2 from chorus 1?

The rule is: **add one or two things at each return, keep the tune, and make
each addition last the whole section.** Things that come and go draw attention
to the arranger.

Verse 2:

- Keeps one element from chorus 1: the tambourine stays, or the snare stays
  full where verse 1 had cross-stick.
- The bass moves a little more.
- An answering instrument appears in the gaps of the tune. Verse 1 has no
  answers.
- One new player enters, usually a pad or a second guitar.
- The tune keeps its contour. Its rhythm may change slightly at phrase starts
  and ends, as different words would cause.
- Common alternative: verse 2 starts stripped (bass and drums for 4 bars),
  then the rest returns.

Chorus 2 is chorus 1 plus one layer: a harmony above the tune, busier
tambourine, or a counter-line. Chorus 1 should hold something back so there is
something to add.

The last chorus gets everything: top harmony, lead fills in the gaps, more
crashes, a repeat, perhaps a key change.

A useful order of additions, from least to most noticeable: percussion layer,
bass activity, doubling, counter-line, wider register, new instrument.

Also vary these or the listener hears a loop:

- Never the same fill twice running.
- The last two bars of each verse differ, because each leads somewhere
  different.
- After the bridge, a stripped verse 3 is common.

---

## Joins

### Q5. Is the list of joins complete and correctly sorted?

The sorting is right. "Pickup" and "straight in" work in both directions. The
list is missing the things a band does together and everything harmonic.

Missing, rising:

- **Push.** The whole band plays the new section's first chord an eighth note
  early. It is everywhere in rock, soul and funk, and programs never do it.
- **Stops (hits).** The band plays two to four accents together in the last
  bar. Central to blues, rock and roll and soul.
- **Bass walk-up or walk-down** to the new root. Soul, blues, sixties pop.
- **Riser.** An accelerating snare roll (quarters, eighths, sixteenths,
  thirty-seconds), a controller sweep opening, the kick removed for the last
  bars. Electronic only.
- **Glissando or rip.** Piano glissando in rock and roll, horn rip in soul.
- **Extra bar or short bar.** The section is stretched or cut so the next one
  arrives late or early.
- **Key lift.** The last chorus arrives a half or whole step up.

"Build" should have variants: snare on every beat, tom build, rising bass
line, crescendo.

Missing, falling:

- **Drop to one.** Only drums, or only bass, carries on.
- **Tail and breath.** The last note of the tune hangs, then a bar of space.
- **Stop and whisper.** Silence, then the next section starts small.
- **Dovetail.** The last bar of one section is the first bar of the next.
- **Slow down and hold.** Ballads and endings.
- **Filter down or layer out.** Electronic.

A naming problem: in blues, "turnaround" means the last two bars of every
12-bar chorus. It happens at every chorus, rising or falling. Call your
intro-material join a "re-intro".

By subgenre:

| Subgenre | Belongs | Sounds wrong |
|---|---|---|
| Rock and roll | Stops, piano glissando, snare pickup | Risers, long builds |
| Punk | Straight in, stick count, stop and slam | Ring over, long builds, slowing down |
| Hard rock, arena rock | Big tom fills, drop-out, held dominant, ring over, push | |
| Rock ballad | Cymbal swell, slowing down, build | Stop and slam early in the song |
| New wave | Straight in, short mechanical snare fills | Loose tom fills |
| Sixties pop | Snare pickup, tambourine roll, key lift, timpani roll (big studio) | Crash-heavy fills |
| Soul | Horn pickup, bass walk-up, stops, push | Risers |
| Funk | Hits on beat 1, the break (everyone out but drums) | Tom fills with crashes |
| Disco | Open-hat build, descending tom fill, a rising string run | Slowing down |
| Blues | The turnaround figure, stop-time, triplet pickup | Risers, straight-sixteenth fills |
| House, techno, trance | Kick removed, snare-roll riser, filter opening, one layer in or out | Tom fills, crashes in minimal techno, slowing down |
| Dubstep | A beat of silence before the drop | |
| Drum and bass | Chopped-break fills, bass drop | |
| Ambient | Overlap and crossfade only | Every kind of fill and stop |

### Q6. Is the size of the energy change the right rule?

It is the right first factor. Six more should weigh in:

- **Which boundary it is.** Into the last chorus and out of the bridge outrank
  everything. Into the first chorus should be modest, because the song has to
  save something.
- **What was used last time.** Never the same join twice running.
- **Tempo.** Size fills in seconds, not beats. A fill wants roughly half a
  second to two seconds. A one-bar drop-out at 70 BPM lasts over three
  seconds, which is too long, so use one beat.
- **The chord at the boundary.** If the section ends on an unstable chord, a
  build or a hold works. If it ends on the tonic, use a pickup or go straight
  in.
- **Whether the tune has pickup notes.** If the tune starts before the bar
  line, the join must leave room for it. A busy fill under a pickup is
  clutter. Drop-out plus pickup is the natural pair.
- **The direction of the change.** Large falls want a hard drop. Small falls
  want a ring over.

A boundary with no energy change (verse into verse) still needs a small
marker.

### Q7. What should the harmony do at a join?

This is the most valuable thing you could add. Give every section an ending
type: **closed** (ends on I), **open** (ends on a chord that wants to move) or
**loop** (ends wherever the loop ends). Then set the last bar from the first
chord of the next section.

The approach chords, in order of usefulness:

| Approach | Example in C | Where |
|---|---|---|
| The dominant | G or G7, then C | Everywhere except modal rock, punk and funk vamps |
| Suspended dominant resolving | Gsus4, G, then C | Pre-chorus, end of bridge |
| The subdominant (plagal) | F, then C | Rock, soul |
| The flat seventh | B♭, then C | Rock, hard rock |
| Tonic turned into a dominant | C, C7, then F | Into any section starting on IV: soul, blues, sixties pop, rock and roll |
| Dominant of the dominant | D7, G7, then C | Sixties pop, jump blues |
| A diatonic walk in the bass | C, Dm, Em, then F | Soul, sixties pop |
| A half step above | D♭7, then C | Blues endings, jump blues |

Progression already has the Quality and #/b rows, so all of these can be
written today. What's missing is the rule that edits the last bar.

Section by section:

- **Pre-chorus:** starts on IV or ii, chords change twice as fast, ends on a
  held V.
- **Verse into chorus without a pre-chorus:** the last bar or two of the verse
  go to V, IV or ♭VII.
- **Chorus into verse:** the chorus ends closed on I. A V in the last half bar
  restarts the verse.
- **Bridge:** starts away from I and ends on V held for one or two bars.
  Before a key lift, it ends on V of the new key.
- **Blues:** bars 11 and 12 are the turnaround (I, IV, I, V). The last chorus
  replaces it with an ending.
- **Minor keys:** the V chord should be major (borrowed from harmonic minor),
  or use ♭VII.
- **The lift by mode:** verse in the relative minor, chorus in the major. It
  is one scene scale change.

Where not to do any of this:

- Loop-based music (house, techno, funk vamps). Texture marks the joins and
  the loop just continues.
- Modal rock, punk and funk. A textbook V7 to I there sounds like a school
  exercise.

Endings: V to I, IV to I, ♭VII to I, or a deceptive cadence (V to vi), a tag,
then the real one. A song that fades can end unresolved.

---

## Bridges, solos, trading

### Q8. Can a program be trusted with "the bridge is the opposite"?

Yes, with four limits.

1. **A budget of two or three contrasts.** One harmonic, one textural, and at
   most one melodic.
2. **A list of things that stay:** tempo, key centre (unless a key change is
   the chosen contrast), the core instruments and the groove family.
3. **A thread back to the song.** The bridge tune should borrow a rhythm from
   the verse or the hook with new pitches. Without a thread it is another
   song.
4. **The direction depends on the song.** In a loud song the bridge drops. In
   a quiet or level song the bridge **rises** and is often the peak.
   "Opposite" has to be measured against the song's average, and above all
   against the chorus, since the chorus sits on both sides of it.

Contrasts in order of importance:

1. Starting away from the tonic (IV, vi, ii, ♭VI) and ending on V. This one
   alone makes a bridge.
2. A change of texture or energy.
3. The tune in an unused register with a different phrase rhythm.
4. Chords changing at a different rate.
5. Half time. Strong, so never combine it with a key change and new
   instrumentation.

The template should also name the kind of bridge, because genres differ:

| Kind | Genres |
|---|---|
| Middle eight (new chords, new tune) | Sixties pop, british invasion, rock, soul |
| The B of an AABA form, starting on IV | Rock and roll, sixties pop, jump blues |
| A new vamp on another chord, full band | Funk |
| Breakdown | Disco, punk (often bass alone), all dance music |
| The solo is the bridge | Hard rock, arena rock |
| None | 12-bar blues, much punk |

### Q9. One solo shape for every instrument?

No. It fits composed rock and pop solos and misfits the rest. Offer the shape
as a choice with a default per subgenre:

| Shape | What it is | Where |
|---|---|---|
| Climb | Starts low, ends on the peak, hands off to the chorus | Hard rock, arena rock, rock ballad. The usual rock shape |
| Arc | Peak two thirds through, then return | Solos followed by a quiet section |
| Paraphrase | The tune, decorated | Sixties pop, new wave, synth-pop, folk rock |
| Call and response | Two bars of phrase, two bars of space, in three lines per 12 bars | All blues |
| Riff | One lick repeated with variation, hot throughout | Rock and roll, jump blues, punk |
| Cycle | A rhythmic figure over a vamp that shifts but doesn't build | Funk, new orleans |
| Chorus by chorus | Each pass through the form a step up | Blues, jazz later |

Lengths differ too: punk solos are 4 to 8 bars and plain on purpose, and the
electronic genres have no solos.

The most important ornament for each instrument, using notes, velocity and
length only:

| Instrument | Ornament | How |
|---|---|---|
| Guitar | Slide or hammer-on into a note | A short grace note a step or half step below, overlapping the main note, softer |
| Bass | Ghost notes | Very short, very soft notes between the real ones |
| Piano | The crushed note | Minor third struck just before, or with, the major third |
| Organ | The swell | Controller 11 on held notes. Needs a controller lane |
| Sax and trumpet | The fall | A fast descending run after a note, each note softer |
| Drums | Flam and ghost notes | A soft grace hit 20 to 30 ms early. Ghost notes at velocity 20 to 40 |
| The sung tune | Anticipation and legato | Notes arriving an eighth early, overlapped inside a phrase, a gap at each breath |

Second tier: double stops and tremolo picking (guitar), octave pops (bass),
octave tremolo and glissando (piano), trills between notes a third apart
(horns), press rolls (drums).

### Q10. How much of a guitar lead is lost without pitch bend?

It depends on the genre:

- **Blues:** most of it. The bend is the voice, and the note between the minor
  and major third cannot be played at all.
- **Rock, hard rock, arena rock, rock ballad:** a great deal.
- **Rock and roll, british invasion, folk rock:** some. Double stops and
  slides carry more.
- **Punk, new wave, funk, sixties pop:** little.

Grace-note slides and hammer-ons recover perhaps a third of the loss.

**Add the bend lane.** Reasons:

- Vibrato is already within reach: controller 1 (the mod wheel) is vibrato on
  most General MIDI sounds, and you have controller lanes. The wizard could
  add it today, delayed, on long notes only.
- A bend lane can also produce vibrato itself, as a small wobble.
- Bends are scale-aware in your model. "Bend this degree to the next degree"
  gives one or two half steps automatically.
- It serves more than guitar: bass slides, horn scoops and falls, synth leads,
  drum-and-bass and dubstep bass.

Shapes worth generating: bend up to the next degree, bend and release,
pre-bend and release, slide in from below, and the quarter-tone curl on the
minor third.

Practical limits: bend is per channel, so a bending lead must be one note at a
time on its own channel, and the range should be set (two half steps is
standard).

### Q11. Is 4, 4, 2, 2, 1, 1 a good trading default?

Not as written: it adds up to 14 bars and fits no form. Trading has to fill
the form exactly.

| Form | Scheme |
|---|---|
| 12 bars | 4, 4, 2, 2. Or 4, 4, 4 with the next chorus in twos |
| 16 bars | 4, 4, 2, 2, 1, 1, 1, 1 |
| 32 bars | 4, 4, 4, 4, 2, 2, 2, 2, 1, 1, 1, 1, then 4 together |

Three things make it sound like trading:

- **Each answer uses the phrase before it:** the same rhythm, or starting on
  the note the other player ended on.
- **The two players sit in different registers.**
- **They finish together,** in unison or in thirds. That is the payoff.

Where it belongs:

- **Yes:** all blues (guitar against piano or harmonica), jump blues and rock
  and roll (sax and guitar), hard rock and arena rock (two guitars, ending in
  harmony), new orleans, southern soul (horn against organ). Later: jazz and
  jam music, where it is central.
- **No:** punk, new wave, sixties pop, ballads, disco and all the electronic
  genres.
- **Drums trade** only in jump blues and jazz.

Blues already trades inside every line: two bars of tune, two bars of answer.
That should be the default texture of a blues verse, before any solo.

---

## Hooks and riffs

### Q12. Choosing and shaping a hook in a text interface

Your four-candidates idea is right as a first step. The trouble is everything
after it. I would use this order.

**1. Show each candidate in four or five lines.** A rhythm row, a degree row,
and a one-line description in plain words:

```
 2  low, off the beat, one leap up at the end
    x..x.x..x.......|x..x.x....x.x...
    3..3.2..1.......|3..3.2....5.6...
```

The description matters. It proves the candidates differ and gives a person
with no theory something to choose by.

**2. Hear it, always twice in a row.** A hook shows itself on the repeat. Keys
to switch what plays with it: alone, with drums, with chords, and "in place"
(the last two bars of the verse, then the hook).

**3. Keep, then ask for more in a chosen direction.** Three requests cover it:

- Same rhythm, new notes.
- Same notes, new rhythm.
- Something else entirely.

Locking rhythm and pitch separately is the most useful control in the whole
panel.

**4. Shape the kept hook with single keys, each heard at once:**

- Start earlier or later (pickup, on the beat, after the beat).
- Move one note up or down.
- Hold the last note longer.
- Remove a note.
- Change the last note (closed on 1, 3 or 5, or left open).
- Swap the odd detail for another kind.

Then one key opens it in the pattern editor, because it is just a pattern.

**5. Choose how the chorus uses it,** shown in letters: A A A B, A B A B, A A'
A B.

Two more ways in, both better than choosing from a list for many people:

- **Tap it.** The person taps a rhythm on the space bar over a loop and the
  program supplies the notes.
- **Words for rhythm only.** The person types a title or phrase. The program
  takes the rhythm from its syllables and stresses and throws the words away.
  This is how sung hooks get their rhythm, and speech rhythm is what machine
  hooks lack.

### Q13. Rules for candidates that differ in kind

Do not make candidates by varying one seed. Draw each from a different family,
then reject any that are too close to one already shown (compare the onset
rows and the contour).

Pitch families:

- **Chant:** one note repeated, with one neighbour.
- **Arch:** up to a peak and down.
- **Falling line:** starts high and steps down.
- **Leap and fill:** a leap up at the start, then steps back down.
- **Rocking:** two notes a third apart, back and forth.
- **Rising sequence:** a three-note cell repeated a step higher.
- **Long-note hook:** a few short pickup notes into one long note on the
  downbeat.

Rhythm families:

- On the beat, long notes (the anthem).
- Anticipations before beats 3 and 1.
- Starts before the bar line.
- Starts after beat 1.
- Three plus three plus two.
- Even eighths with one gap.

Rules for every candidate:

- 4 to 9 notes a bar.
- Range within a sixth.
- At most one leap larger than a fourth, followed by a step back.
- **Something inside it repeats.** A hook with no internal repetition is not a
  hook.
- The longest note is a chord tone, or the second or sixth of the scale.
- Its rhythm differs from the verse's rhythm. Busy verse, broad chorus.

Odd details, exactly one per candidate:

1. One note arrives an eighth early.
2. A rest where a note is expected, such as an empty downbeat.
3. One wide leap (a sixth, seventh or octave) in a stepwise line.
4. One note from outside the scale: the flat seventh, the flat third or the
   flat sixth.
5. A long note that is not in the chord and resolves late, or never.
6. A three-note cell repeated across the beat, so the accents shift.
7. A hook one and a half bars long that repeats early.
8. A repeat that is cut short.
9. An ending on an unexpected degree (2 or 6).
10. A sudden change of pace: a triplet, or a burst of sixteenths.
11. The last note thrown up or down an octave.
12. One note repeated more times than seems reasonable.

### Q14. How a hook varies across a song

The principle: **the head is the identity and the tail is where variation
goes.** The first three or four notes never change.

| Place | Treatment |
|---|---|
| Intro | A plain statement or a fragment, often on another instrument |
| Verse | Absent, or its rhythm hidden in the bass or guitar |
| Chorus 1 | Exact |
| Chorus 2 | Exact tune, with a harmony or answer added around it |
| Bridge | Absent, so its return is fresh. At most its rhythm on new notes |
| Solo | May begin by quoting it, then leaves |
| Last chorus | Exact first time. On repeats: a harmony above, a higher ending, a held last note |
| Ending | Shortened to its last few notes and repeated, or stated once plainly |

Inside a chorus: statement, repeat (moved to fit the chord if needed), a
variation or something new, then the closing line.

A riff is different. It is exact every time, and its variation is where it
plays: stopping for the tune, returning in the gaps, moving with the chords,
doubled by the bass.

To show this in the interface, list each occurrence with a short tag: exact,
with harmony, tail varied, fragment, rhythm only, on bass.

### Q15. One mechanism or several?

One object, several kinds. The stored thing is the same in every case: a short
pattern in scale degrees. The same audition panel and the same variation tags
serve all of them. What differs is how each is generated, what it is judged
against, and where it goes.

| Kind | Generated as | Judged | Placed |
|---|---|---|---|
| Riff | Low, 1 or 2 bars, pentatonic or blues notes around the root, a strong downbeat and syncopation after it | With drums | Under verses and intro, stopping or thinning for the tune |
| Sung hook | Singable, middle to high, with the rules in Q13 | Alone | Chorus |
| Stab figure | A rhythm of 2 to 4 hits. Pitches come from the chord | Against the tune | In the tune's gaps |
| Electronic loop | 1 bar (or 3 or 5 steps against 16), few pitches | In the full groove, over 16 bars | Throughout, varied by controllers and by adding or removing notes |

Two consequences:

- A rock song usually has both a riff and a sung hook, and they should
  contrast: riff low and syncopated, hook high and broad.
- A riff should be written **before** the chords, because the riff implies
  them.

### Q16. The hook in the electronic subgenres

| Subgenre | What the hook usually is |
|---|---|
| House | The rhythm of a chord stab, or the bass line |
| Techno, minimal techno | A one-bar figure on one or two pitches, plus slow change of tone over 16 to 32 bars |
| Electro | The drum pattern itself, plus a short robotic riff |
| Synth-pop | A real tune: a synth riff in the intro and a sung chorus |
| Hi-nrg, italo | An octave-jumping sixteenth bass under a bright simple lead |
| Trance | A sixteenth-note chord figure whose top notes trace a slow tune, revealed in the breakdown |
| Drum and bass | The break and a bass riff of two to four long notes |
| Big beat | A break plus a distorted rock-style riff |
| Dubstep | The rhythm of the bass's tone changing, at half time |
| Ambient | A texture, an interval, or loops of unequal length drifting apart |
| Downtempo | A chord vamp and a bass figure |
| Chiptune | A strong tune over very fast arpeggios standing in for chords |

What a notes-only program can do:

- **Treat a rhythm as a hook.** Generate stab and bass rhythms with the same
  candidate panel.
- **Treat a controller lane as a hook.** Write named shapes into the lanes:
  opening over 16 bars, a rhythmic gate, a wobble that changes rate each bar.
  Tell the user which controller it is so they can map it.
- **Treat accent, length and slide as a hook.** An acid line is three or four
  pitches made interesting by which notes are loud, short or tied. Glide,
  Shorten and velocity already do this.
- **Use unequal lengths.** A 3-, 5- or 7-step figure against 16 steps.
- **Use adding and removing.** Density over 16 or 32 bars is the arrangement.

Half the hook in these genres is the sound, which the program cannot make. The
realistic aim is a pattern that becomes a hook once the user puts a sound on
it, with a line of advice saying what kind of sound.

---

## Players

### Q17. Gauges that make two players different people

First the blunt part: weakness (f) will not be fixed by gauges. Three things
do more:

- **Player types.** A type chooses a different family of figures and sets the
  gauges together, because real traits come in bundles. Examples: the anchor,
  the busy one, the melodic one, the minimalist, the showman.
- **Signature cells.** From the seed, give each player two or three small
  figures of their own that recur: a drummer's favourite fill, a bassist's
  favourite approach to a new chord.
- **A velocity and timing profile.** In MIDI these are the most audible
  signatures. The pattern of loud and soft on a hi-hat identifies a drummer
  faster than the notes do.

With that said, the gauges:

**Drummer**

| Gauge | One end | Other end |
|---|---|---|
| Placement | Laid back | On top of the beat |
| Hands | Even hats, no ghost notes | Strongly accented hats, many ghost notes |
| Kick | Simple, on the beats | Syncopated, following the bass |
| Fills | Rare, on the snare | Frequent, around the toms |
| Cymbals | Dry and tight | Washy: open hats, ride, crashes |
| Power | Light touch, wide dynamics | Heavy hitter, everything loud |

**Bassist**

| Gauge | One end | Other end |
|---|---|---|
| Line | Roots | Melodic, with passing and chromatic notes |
| Lock | With the kick | Around the kick |
| Length | Short and muted | Long and connected |
| Register | Stays low | Roams up high |
| Rhythm | On the beat | Pushing ahead of chord changes |
| Runs | None | A run at every phrase end |

**Rhythm guitarist**

| Gauge | One end | Other end |
|---|---|---|
| Size | Two or three strings | All six, open chords |
| Sustain | Choppy and muted | Ringing |
| Rhythm | Simple, with the snare | Busy sixteenths |
| Part | Chords | Single-note lines and picked figures |
| Position | Low, open | High up the neck |
| Movement | Plain chords | Chords decorated with added and suspended notes |

**Keyboard player**

| Gauge | One end | Other end |
|---|---|---|
| Hands | One hand, sparse | Two hands, full |
| Sustain | Stabs | Pads |
| Colour | Plain triads | Sevenths, ninths, suspensions |
| Rhythm | On the beat | Syncopated |
| Answers | Stays in the part | Fills every gap in the tune |
| Register | Middle | High sparkle |

**Lead player**

| Gauge | One end | Other end |
|---|---|---|
| Pace | Few long notes | Many fast notes |
| Approach | Sings a tune | Runs patterns and licks |
| Space | Short phrases, long rests | Continuous |
| Notes | Chord tones only | Blue notes and notes from outside |
| Drama | Narrow and level | Wide, climbing to high peaks |
| Ornament | Plain | Heavily decorated |

### Q18. Which belong to the subgenre and which to the player?

**The subgenre sets:**

- The vocabulary of figures and fills.
- The timekeeping surface and the swing.
- How rich the chords may be.
- The instrument's job in the band.
- The allowed range of every gauge.

**The player owns:**

- Placement (behind or ahead).
- Touch and dynamic range.
- Space against busyness.
- Repetition against invention.
- Signature cells.
- Amount of ornament.
- How much they react to energy (steady or dramatic).
- How much they answer others.
- Preferred register.

The way to make both true: store player gauges as positions within the genre's
window, not as absolute values. A busy player in punk still plays roots, only
with more of them. Then one imaginary player can be carried from genre to
genre and stay recognisable.

Three gauges are shared: syncopation, lock with the kick, and fill frequency.
The genre sets the centre and the player shifts it.

### Q19. How should the band share space?

Ten rules, in order of how much they help:

1. **Home registers.** Bass below about C3. Chord instruments between C3 and
   C5. The tune above the top note of the chords. Voice Leading's octave
   limits can enforce this.
2. **The left hand stays out.** When there is a bassist, the keyboard plays
   nothing below C3.
3. **One busy part at a time.** If one chord instrument plays sixteenths or
   eighths, the other sustains or plays half as often. The template should
   pair them: one chops, one holds.
4. **The tune has right of way.** While it sounds, nothing else plays in its
   register, and accompaniment velocities stay under it, at about 80 percent.
5. **One answerer at a time.** When the tune rests for two beats or more, a
   single chosen player fills. Rotate the job by section: guitar in verse 1,
   keys in verse 2, horns in the chorus.
6. **One fill at a time.** At a phrase end, the drummer fills or the bass
   runs, never both.
7. **No close notes down low.** No thirds below about C3 and no tight chords
   below E3.
8. **Double on purpose.** Bass and guitar on a riff in octaves, horns in
   unison on the hook. Two parts a step apart in the same register by accident
   is the thing to prevent.
9. **Limit who is in.** By energy: one or two players at 2, three or four at
   5, five or six at 8, everyone at 10.
10. **One pad at most** in the middle register.

A simple budget if you want a number: count note starts per bar across the
chord instruments, set a ceiling per energy level, and when the ceiling is
passed, thin the player with the lowest priority using Density.

---

## The wizard itself

### Q20. The large decisions, in order

For a person who knows what they like and has no theory:

1. **Mood:** bright, bittersweet, dark, tense. This picks the scale and the
   family of chord progressions. Show the resulting scale as derived, marked
   "(from mood)".
2. **Length:** short, single, extended. This sets the form.
3. **The curve** of the song, with the bar chart. The chart is the best thing
   on the page.
4. **Contrast:** even to dramatic. How far apart the quietest and loudest
   sections are.
5. **Starts with:** riff first, drums first, builds in, straight in, chorus
   first.
6. **The middle:** bridge, solo, breakdown, bridge and solo, none.
7. **Ends with:** big finish, fade, sudden stop, quiet close, back to the
   start.
8. **Band:** stripped, full band, wall of sound.

A ninth if there is room: **Performance**, from tight and polished to loose
and live. It scales every player's timing, variation and fills at once.

Never show that person:

- Chord numerals or cadence types.
- Chord change rate, inversions or voice leading.
- "Follows the key or the chords" under that name. Call it "plays safe"
  against "follows the chords closely".
- Swing percentages, velocity numbers or register numbers.
- Channels and controller numbers.
- Twelve-tone rows.

"Scale" on the first page is already a theory question. Mood should replace it
there.

### Q21. What to call the page and "energy"

Two names in the sketch collide with words llamatron already uses:

- **"Shape"** already means Density, Swell and Articulate, which the generator
  documentation calls shapes.
- **"Arrangement"** is too close to the Arrange page.

For the page I would use **Song Plan**. Working musicians also say "roadmap"
for the order of sections, and that would be my second choice.

For the curve preset I would use **Arc**, which avoids the collision.

Keep **Energy**. Non-musicians understand it at once and producers use the
same word. The alternatives are worse:

- "Dynamics" means loudness only.
- "Density" is taken.
- "Level" sounds like a volume control.
- "Intensity" is acceptable but no clearer.

If the second dimension is ever shown, call it **Busy**.

### Q22. Should section lengths follow tempo?

Yes for song genres. Think in seconds: a verse wants 20 to 30, a chorus 15 to
25, an intro 5 to 15, a bridge 12 to 20. A bar of 4/4 lasts 240 divided by the
tempo.

| Tempo | Verse | Chorus |
|---|---|---|
| Under 90 | 8 bars | 8 bars |
| 90 to 140 | 16 bars first time, 8 after | 8 bars, doubled at the end |
| Over 140 | 16 bars | 16 bars |

Better than tempo alone: count passes of the chord loop. A section should hold
two or four passes.

Where the rule does not apply:

- **Blues:** 12 bars at any tempo. A slow blues chorus can last most of a
  minute and should.
- **Dance music:** blocks of 8, 16 and 32 bars by convention, with long intros
  and endings for mixing.

Second verse shorter: yes by default in rock, pop and soul **when verse 1 is
16 bars**. If verse 1 is 8, leave verse 2 at 8. Not in blues, folk rock or
folk pop, where every verse is a full verse.

Check the total as well. The sketch adds up to 2:08 at 120 BPM. That suits
punk and sixties pop and is short for arena rock or a ballad.

### Q23. The genre list

**Too broad for one template:**

- **House.** Deep, piano and acid house are three different things. Acid is
  missing altogether, and llamatron already has the tools and a demo for it.
- **Funk.** One-chord vamp funk and smooth, chord-rich funk share little.
- **Punk.** Early punk, hardcore and pop-punk.
- **New wave.** Angular guitar bands and synth bands.
- **Dubstep.** The sparse early style and the later aggressive one.
- **Drum and bass.** At least a smooth and a dark variety.

**Could be merged:**

- The three shuffles, if they differ only in feel. One template with a feel
  choice.
- "Sixties soul" and "soul pop" overlap. Define them by region and sound or
  merge them.
- The four serial subgenres are one template with four line-ups.
- Minimal techno could be a setting of techno.

**Missing, that users will look for:**

- Hip-hop (boom bap, trap, lo-fi). The largest gap.
- Modern pop. The list has sixties pop and nothing later.
- Country and bluegrass. Guitarify already has the picking styles.
- Reggae and dub, alongside the planned ska.
- Metal. The demos have it and the wizard does not.
- Eighties pop and synthwave, which the people who buy synthesizers love.
- Indie and alternative rock.
- Latin styles: bossa nova, salsa, cumbia, reggaeton.
- Fifties ballads in 12/8.
- Motorik rock, which suits a sequencer unusually well.
- Under Experimental: **minimalism** (phasing, additive process, patterns of
  unequal length). It fits llamatron better than serialism does.

**The mistake that gives a machine away, by genre:**

| Genre | The tell |
|---|---|
| Rock | Every chord change lands on beat 1 for every player, forever. No pushes, no stops, nothing played together |
| Sixties pop | A busy modern drum beat and a root-bound bass, where a simple beat with tambourine and a melodic bass belong |
| Soul and funk | Every part sounds complete alone. In funk each part should sound unfinished until the others join |
| Blues | The lead plays straight through all 12 bars with no space and no answer |
| Electronic | Too much variation and humanised timing, where the style wants exact repetition and one change at a time |
| Serial | The row played left to right in one octave in even notes, like a scale exercise. Real serial writing leaps between octaves, uses silence, and stacks parts of the row as chords |

### Q24. What was not asked

1. **Breath and phrasing in the tune.** Lines of two or four bars with rests
   between, a range of about a tenth, notes connected inside a phrase. Even a
   fake line of syllables (eight, then six, then eight, then six) gives a
   better rhythm than any melody gauge.
2. **Ensemble figures.** A shared rhythm that every player reads in chosen
   bars: hits in an intro, a push into a chorus, a stop before the last line.
   This is what makes a band sound rehearsed.
3. **Velocity headroom.** Patterns default to 127. The wizard should write
   normal playing at 80 to 100 so that accents and the last chorus have
   somewhere to go.
4. **The pre-chorus.** Your list of possible new sections has post-chorus,
   turnaround and breakdown, and no pre-chorus. It matters more than all
   three.
5. **Forms other than verse and chorus.** AABA (sixties pop, rock and roll),
   12-bar strophic (blues), verse with a refrain line (folk rock), a vamp
   (funk), and intro, build, drop, breakdown, outro (dance music). The Song
   Plan rows should use the right words for the genre.
6. **Small tempo changes.** Scenes can carry their own tempo. Live bands play
   choruses one to three BPM faster and slow down at the end. Never in
   electronic genres.
7. **Endings as written figures.** A blues ending lick, a rock last chord with
   a cymbal wash, a soul vamp that fades by velocity. The intro deserves the
   same: built from the hook or the chorus chords, not generic.
8. **Key choice by instrument.** Guitar genres sit best in E, A, D and G,
   where open strings work. Horn genres sit in F, B♭ and E♭.
9. **Compound time.** Soul ballads, slow blues and fifties ballads are in
   12/8. Fills and energy states are different there: fills are in triplets.
10. **Backing voices.** Thirds and sixths under the tune, held "ooh" pads, and
    echoes of the last words of a line.
11. **Re-rolling one thing.** "A new take of the bass only", "a new bridge
    only", with everything else locked. This matters as much as the quality of
    the first result.
12. **Life after Apply.** If the plan is stored in the song, a person can
    change one section's energy later and regenerate that section without
    losing hand edits elsewhere.
13. **Choosing instead of averaging.** On the tension you named: within a
    subgenre, pick one coherent variant by seed (riff-led or chord-led, for
    example) and commit to it. A blend of all variants is the mud.
14. **One silence.** Alongside "one surprise", a single moment where the whole
    band stops.
15. **Accidental resemblance.** A generator of narrow, stepwise,
    familiar-shaped hooks will now and then produce the opening of a famous
    tune by chance. Easy re-rolling is the practical answer.
16. **How you will judge it.** Three listening tests:
    - Mute each part in turn. A real part leaves a hole.
    - Solo each part. It should sound like something a person would play.
    - Look at each section in the piano roll. Sections should look different
      from each other.

    A report per demo of notes per bar by player and section, and of the share of identical bars, would catch regressions.
