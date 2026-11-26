# Synth Ideas

Wanted work on the built-in synths, drum engines and effects: what each idea is, never its status or order (those are in
`.claude/planning/QUEUE.md`). An agreed design moves to `.claude/planning/DESIGNS.md`; an idea leaves this file once built.
The professor's research is in `.claude/notes/synthesis/`.

## The Instrument Page

- **Built-in modulation**: Beneath each envelope, LFO and filter, routes of its own, off by default, each choosing
  Destination, Via and Amount from the Mod Matrix's values, so that the Mod Matrix drops to four fully custom slots. Env 1 stays
  wired to the Amp always; Env 2 stays wired to the filter, with a "Disconnect filter" switch. Mockup first.
- **New-instrument choices**: Blank, Sampled (FluidSynth, where installed), Synth, Drum Synth or External MIDI, beside Normal
  and Percussion, each choosing a few settings that can still be changed. Mockup first.
- **The Engine tab** (DESIGNS.md, "The Instrument page's Engine tab and presets"): Off, MIDI, FluidSynth and LlamaSynth, its
  migration, engine and block presets; with it, a Glide switch on the MIDI engine, as if it were a synth.
- **The Mod Matrix's destinations**: Which to drop (Drive and the like need not be destinations), a discussion; later, some
  effects' settings as destinations, effect by effect.
- **More kinds of LFO**: today an LFO is Sine, Triangle, Saw up, Saw down, Square or Sample & Hold, with its Speed and Rate,
  Key, Retrigger and Each scene. The kinds found in LFO plugins and in modular designs (the slope and function generators,
  looping envelopes, multi-phase LFOs, random and chaotic sources), as candidates, each to be chosen with the user:
  - Symmetry and Curve, one continuous shape from saw down through triangle to saw up, bent from logarithmic to exponential,
    as a slope generator's rise and fall are (Tides, MIT, is the open design to follow).
  - Smooth random: a random value each cycle, glided to rather than stepped, with a Slew, beside Sample & Hold.
  - Fade in: the LFO's depth rising over a time after each note, the delayed vibrato of the classic polysynths.
  - Tempo sync: the Rate as a division of the beat, dotted and triplet included, beside a rate in hertz.
  - Phase: where in its cycle the LFO starts, and across a chord's voices a spread, so that the voices move apart, as a
    multi-phase LFO's outputs do.
  - One shot: the LFO played once at each note and held at its end, an extra envelope, as a looping envelope switched to
    single.
  - Steps: a short drawn row of levels, eight or sixteen, played as the LFO's shape with a Slew between them, as a curve
    sequencer does.
  - Chaos: a smooth, never-repeating motion from a chaotic system, started from a seed so it is the same every playing.
    A system moves in two or three dimensions at once, so a chaotic LFO gives two or three related outputs (X, Y, Z), each
    a Mod Matrix source of its own, moving two or three things together, never in step yet never unrelated. Candidates:
    the Lorenz attractor (two lobes it flips between unpredictably, the best-known); the Rössler attractor (a simpler,
    smoother spiral that now and then leaps out); Chua's circuit (the electronic double scroll, the analog chaos
    circuit); the jerk systems and slow chaotic circuits ( four very slow flavours,
    minutes a cycle, for drifting pads); Thomas', Aizawa's, Halvorsen's and Dadras' attractors; the logistic and Hénon
    maps, stepped rather than smooth, beside Sample & Hold; a double pendulum or a Duffing oscillator, which feel
    physical; predator and prey (Lotka-Volterra), two populations rising and falling in turn; and the rungler,
    a shift register fed back by two oscillators, a stepped pattern that almost repeats. Each would offer a Chaos amount
    (how wild, from a near loop to full chaos) and its speed; all must be kept bounded and numerically safe (a fixed step,
    clamped, restarted from the seed if it ever escapes), and are cheap at control rate. Research which few sound most
    musical before choosing.
  - Burst: a few cycles at each note, then still, for ratchets and trills.
  - One LFO moving another's Rate or depth, through the Mod Matrix's Via or the built-in routes.
  - **Chaos**: one modulator holding the chaotic systems above as a choice of System (Lorenz, Rössler and the others
    researched), with a Chaos amount and a speed, its X, Y and Z as Mod Matrix sources.
  - **Drawn on screen**: each modulator draws what it is doing in its box (a chaotic system's path, the snails' traces,
    a tide's four outputs), worked out on the screen's side only while its box is on screen, and only if cheap.
  - **Snail**: three slow chaotic circuits, made to suit llamatron's pages: three slow chaotic
    circuits, each travelling around two strange attractors at its own pace (the original's about 15 to 30 seconds, 60
    to 90 seconds, and 30 to 40 minutes a trip), two of them with a Lean, which sets which attractor it lingers around
    rather than its speed, the third with none; its own inputs left out. Each circuit's X and Y are Mod Matrix sources
    (the original's Z, its Y inverted, is the Mod Matrix's negative Amount), and a mix of the three, the first and third
    added and the second taken away, split into its rising and falling halves, as the original's difference rectifier
    does. Never restarted by a note; the same every playing from its seed. Its circuit's equations, a jerk-type chaotic
    system, to be found and checked before building.
  - A tidal modulator, after Mutable Instruments' Tides (2018), whose firmware is open (MIT,
    `pichenettes/eurorack`, `tides2/`), so its algorithms can be followed and credited above each: a rise and a fall
    ("flow and ebb") that loops as an LFO or runs once at a note as an envelope. Its Ramp mode is AD (one shot from zero,
    whatever the note's length), Cyclic (a looping LFO, a note restarting it at its rise) or AR (rising while held, falling
    at release, each from where it is). Frequency spans four octaves either way around a range's centre (1/8 Hz for slow
    movements, 2 Hz for rhythms, 130.8 Hz for tones). Shape bends the rise and fall; Slope splits the cycle's time between
    rise and fall; Smoothness is a two-pole low-pass one way and a wavefolder the other. Its four outputs, each a Mod
    Matrix source here, are related by an Output mode and a Shift: four shapes taken along its chain; one signal crossfaded
    from output to output; the same shape shifted in time (a phase between outputs, or a different Slope each); or each at
    its own ratio of the frequency, polyrhythmic LFOs or, at audio rate, just-intonation chords. Synced to the tempo, its
    Frequency becomes a ratio of the beat. At audio rate its Shape and Slope change meaning (stronger timbres, pulse
    width) and its Shape and Smoothness narrow at high pitches to stay unaliased.
- **Envelopes drawn**: on the Envelopes tab, each envelope's shape drawn in its box from its settings, redrawn as they
  change, and a moving mark along it while a note fires it, worked out on the screen's side as the gauges' live markers
  are, only while the tab is on screen.
- **A spectrogram on the Instrument page**: in the upper right, beside the settings above the tabs, the instrument's sound
  as a spectrogram: low notes at the bottom, time scrolling left, brightness its loudness; drawn only while the page is
  on screen.
- **A one-voice instrument's note priority**: Lowest, highest or last, beside today's lowest-of-a-chord.
- **The instrument on the Track page**: The assigned instrument's settings drawn below the track's own, editable there.
- **The Instruments page as a rack**: A mockup of every instrument's tab rows in one column, each expanded or collapsed and
  saved with the set; if built, the single Instrument page goes.
- **Presets** for the built-in synths: a discussion.

## The Engines

- **Every engine and effect redesigned from the professor's research** (`FLAVORS.md` and the rest): each engine's settings
  discussed with a mockup of its Synth tab, one a reply. The professor first reviews every engine, drum and effect proposed and
  says which merge and which stay apart. Each drum engine declares a hard playable range in octaves, clamping or refusing notes
  past it, shown on its mockup.
- **MechaDrum split** into one engine a drum ("MechaDrum Kick", "MechaDrum Snare", ...), each with its own settings after the
  drum machine's manual's drum configurations, and presets per drum type; its demo updated.
- **The vactrol's age**: An old cell behaving less predictably strike to strike, within a musical range Claude proposes.
- **Asheville's polyphonic mode**, after the late-1970s polyphonic analogs: every key its own voice, a shared filter and
  contours either paraphonic or per voice.
- **Durham**: A homage to the classic analog bass pedal synth, on its modern descendant's panel, exposing only what that panel
  has; the filter very nearly perfect (the D'Angelo-Välimäki ladder). Research in `MONOSYNTHS.md`, "Durham"; mockup first.
- **Spectral**: A filter type, a bank of band filters, only what
  their knobs, sliders and switches control, no new patching; built together with the planned Harm engine, renamed Spectral.
  Research both panels, then a mockup.
- **Drone**: A drone instrument of held, slowly moving oscillators, yet sounding only through the Amp, Env 1
  opening it, as every engine does. Research its panel, then a mockup.
- **A brass synth**, somewhat after Stringy, for the bright, stabbing synth brass of early-1980s rock and pop keyboard anthems,
  as simple as the vintage brass ensemble keyboards (research which to follow).
- **Brass and wind** among the physical modelling ideas.
- **A Choir engine**, after the mono groovebox's choir voice (`CHOIR_AND_PLUCK.md`).
- **The talking-toy voice**: A buzz or noise through a tenth-order all-pole filter stepping 40 frames a second through vowel and
  consonant frames chosen per step, 4-bit coefficients, from our own formant targets; its name is open (`MODULAR_IDEAS.md`).
- **The other engines and effects** starred in `ALL_INSTRUMENTS.md` and `ALL_EFFECTS.md`, drums included, once their names,
  groups, presets and block swapping are settled (open there: the low-pass gate's Strike and Gate, the Effects field, the engine
  dialog's columns, a picker column of engines and of effects).
- **Kept for engines when built**: Through-zero FM and ADAA folders (ComplexOsc), integrated wavetables (Wavetable),
  phase-locked footages (Stringy, Combo Organ), synced-square PWM (Monorail, Chirpy), the NES triangle (DustCart, BitArcade),
  Rings' resonator (the Resonator filter), sst-filters' further models (licence checked).
- **More of FluidSynth** exposed as an engine of the backend.
- **The agreed engines' designs**: ComplexOsc (one engine for the classic West Coast and the modern complex oscillator), Hurt
  (after the harmonic oscillator, now to become Spectral), the Choir, and the modular study's engines (Formant Blip,
  Bytecrunch, Flock and the rest), as agreed in `.claude/planning/DESIGNS.md`, "Built-in engines agreed and not yet built".

## The Effects

- **Variance**: an effect, subtle, lo-fi, an evolving undercurrent under
  melodies: a short delay whose time wanders at random, then a low-pass gate that recovers the tone. Its panel, from its
  manual: Rate, how far apart the random pitch wanders fall, from rare to nervous; Damp, how softened and drawn out each
  wander is, from near instant to so slow it stops sounding like pitch modulation; Depth, how far, its range kept
  subtle; Mix and Volume; and LPG, how much the sound's own envelope opens the recovery filter. Still to research: the
  delay's times, the random source's character and the recovery filter's response; then a mockup.
- **The professor's effect plans**: Legend's Mode A on Freeverb3's Progenitor (GPL-2.0+); the Spring on stretched all-passes
  after Surge's ChowDSP spring (GPL-3.0+); Tape Echo's Time as tape speed, one speed curve for every head; Dattorro's centre-tap
  chorus feedback; setBfree's rotary geometry; CHOW Tape's loss filter; EQ bands as trapezoidal SVFs with Vicanek's matched
  designs; Drive's ADAA with 2x at the top.

## More Synth Ideas

In the order of their priority, the highest first.

- **An organ engine and a rotary speaker effect**: A built-in organ engine that plays the classic organ sounds: the
  tonewheel organ, with nine drawbars at the footages 16', 5 1/3', 8', 4', 2 2/3', 2', 1 3/5', 1 1/3' and 1', a percussion
  on the second or third harmonic, fast or slow, soft or normal, key click and a little leakage between wheels; and the two
  transistor combo organs of the sixties, the bright, reedy British one and the thin, buzzy Italian one, each with its own
  tabs or stops and its vibrato. Fully polyphonic, every note sounding at once as an organ's does, with no envelope beyond
  the key's on and off. Undecided: whether the three are one engine with a Model setting or three engines; which settings
  become the engine's eight Synth Control rows (drawbars, percussion, vibrato and the speaker's speed are the likely ones);
  and its name, since no maker's name may be used. A rotary speaker effect for the effect blocks: a horn and a drum turning
  at their own speeds, Slow and Fast, each speeding up and slowing down with its own inertia when the speed is switched,
  with the pitch wobble, the swirl of level and the stereo spread they make, and the overdrive of the amplifier before them.
  Its speed switch is the setting a player reaches for while playing, so it is a likely Synth Control row. Needs the
  professor's notes on both before building, and stereo (the Pan work) for its spread.
- **One-voice instruments shared by tracks**: a one-voice instrument already plays one note at a time, keeping a chord's
  lowest note and sliding only where notes overlap; still to discuss, raised by the Hocket, which hands notes to tracks that
  may play notes of their own: whether overlaps are judged per track or across every track sharing the instrument, and
  whether llamatron warns of them.
- **Built-in synths: FM**: A built-in FM family after the first built-in synths: FM drums first, then two- and four-operator
  tonal FM, plain FM's index movable live each chunk, feedback approximated by tables (.claude/notes/synthesis/MACHINES.md).
- **Built-in synths: Unison and Chord**: Unison saws and pulses with subs, and a Chord instrument that plays up to four
  pitches for every note, so that a simple pattern played through a major chord instrument fills out at once, which is fun
  to write with (.claude/notes/synthesis/MACHINES.md).
- **Built-in synths: Modal and Plucked**: Modal drums and tuned percussion, toms, marimba and bells as decaying modes, and
  Karplus-Strong plucks and drums, each hit rendered when its note arrives and kept for replay
  (.claude/notes/synthesis/MACHINES.md).
- **Built-in drums: 8oh and 9oh**: Drum machines in the manner of the two classic analog drum machines of 1980 and 1983, the
  bridged-T kicks with their long decays, the first's cowbell, clap, toms and its six-oscillator metallic hats and cymbal,
  and the second's noisier snare and punchy kick, as built-in drum machines with plain names
  (.claude/notes/synthesis/MACHINES.md and DRUMS.md hold the techniques).
- **Built-in instruments: presets of the user's own**: On the Instrument page, saving a built-in instrument's settings as a
  preset of the user's own: a block's type and values as a block preset, the whole instrument as an engine preset (its list
  of block and preset pairs), and the four FX blocks together as an effects preset, each under a name the user gives, listed
  after the factory presets in their pickers under a heading of their own. Kept in a personal library,
  ~/.llamatron/presets.yml, which every set shares (21 B), never in the set file; a set using a preset of the user's own
  still holds every value itself, so it plays the same on another computer. Undecided: the key that saves (S is taken on
  some pages), and what happens when a preset of the user's own is renamed or deleted while sets name it.
- **Effects buses**: Buses, so that several instruments can send to shared effects, such as one reverb, edited on a page of
  their own. Not now: llamatron has no buses yet, and the first built-in effects belong to each instrument.
- **Synth Master Bus and Drum Master Bus**: The user's idea for shared effects without a full bus system: two fixed buses,
  shown on the Song page for now, "Synth Master Bus" and "Drum Master Bus", through which every built-in instrument plays
  (not FluidSynth's), the drums through the Drum bus and every other engine through the Synth bus. Not a send bus:
  everything is routed through it, each bus holding a few effect blocks of its own (the user's note read "w plugins",
  perhaps two; to ask) applied to the summed mix of its instruments, such as one reverb for the whole kit. Only worth doing
  if the summed mix can be kept from clipping: the output guard already soft-clips the whole mix, and a bus would need
  headroom before its effects. Subject to a performance discussion: a bus costs one effect chain on a chunk for all its
  instruments, cheaper than one an instrument. Undecided: which page holds the buses later, whether a song or the set owns
  them, and how a drum engine on a melodic track is routed. The fuller Buses idea elsewhere in this file is the later
  version.
- **Kits of instruments saved for every set**: Save a song's current instruments, built-in sounds and MIDI instruments
  alike, as a named kit kept in the user's own ~/.llamatron/ folder rather than in any set, so that every set can load it;
  and load a kit into a song, adding its instruments. Undecided: whether a kit holds the tracks that use the instruments
  too, and how a name clash is resolved.
- **More than six Synth Control rows**: Offering more than six Synth Control rows for an engine, if the six prove too few
  and the audio process keeps its timing with more.
- **Random pitch steps within a Sweep Drum hit**: The Sweep Drum's third kind of in-hit modulation, random steps, the pitch
  jumping to a new random value several times a hit, as the late-1970s drum synthesizers' sample and hold did. Only with a
  modulator attached, never random on its own, and only if it is cheap to render; it may never be built.
