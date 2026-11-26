# Synth Ideas

Wanted work on the built-in synths, drum engines and effects: what each idea is, never its status or order (those are in
`.claude/planning/QUEUE.md`). An agreed design moves to `.claude/planning/DESIGNS.md`; an idea leaves this file once built.
The professor's research is in `.claude/notes/synthesis/`.

## The Instrument Page

- **Modulators for MIDI instruments**: an instrument playing FluidSynth or an External MIDI device gets the Modulators
  and Mod Matrix tabs, the tabs that make no sense for it hidden (an instrument with no engine gets none). Its Mod Matrix
  destinations are a CC by number, Velocity, Note (scale degrees, an amount of 0 to +12, separate from Pitch), Octave
  (0 to +4, kept within the instrument's or track's octave range) and Glide (the pattern step's own glide, turned on or
  off as the modulator crosses its middle, where the engine plays glides; left out where it cannot); Note, Octave and
  Glide are offered to built-in synths too.
  The Realizer applies them to the pattern as rendered, reading each modulator at each step's time, so that what plays
  live is what the exports write: a chord on a moved step moves along the scale, taking the scale's quality there (C
  major up a degree in C major is D minor); a tied or glided note keeps the note it started on; a CC goes out ahead of
  its step's notes, only when its value changes, at most every 1/64 note, how often a setting of the MIDI tab with a
  default chosen from research into what devices handle.
- **Modulators moving each other's rates**: a modulator as a Mod Matrix source for another's Rate, so that one LFO
  speeds and slows another, rates only for now.
- **Demos of the new modulators**: a demo for each new kind as it is built, LFO+ (Fade in, Tempo, Smooth random), Snail,
  Chaos, Tide, Turing, Bounce and Swarm, each made to show what the modulator does to music, and kept to the synth demos'
  rules (DEMO_IDEAS.md).
- **Disconnect filter**: a switch on Env 2 that unhooks it from the filter, leaving Env 2 free for the Mod Matrix.
- **New-instrument choices**: Blank, Sampled (FluidSynth, where installed), Synth, Drum Synth or External MIDI, beside Normal
  and Percussion, each choosing a few settings that can still be changed. Mockup first.
- **The Engine tab** (DESIGNS.md, "The Instrument page's Engine tab and presets"): Off, MIDI, FluidSynth and LlamaSynth, its
  migration, engine and block presets; with it, a Glide switch on the MIDI engine, as if it were a synth.
- **The Mod Matrix's destinations**: Which to drop (Drive and the like need not be destinations), a discussion; later, some
  effects' settings as destinations, effect by effect.
- **Modulator modules**: each Modulators tab slot holds a module chosen by its Type, and beside LFO and LFO+ the Type
  offers Snail, Chaos, Tide, Turing, Bounce and Swarm, a module of several outputs adding them to the Mod Matrix's sources
  while chosen (`.claude/planning/DESIGNS.md`, "Modulator modules on the LFOs tab"). What each module is:
  - **Chaos**: a chaotic system's path in three dimensions, X, Y and Z, never repeating; System is Lorenz (two lobes it
    flips between), Rössler (a smoother spiral that now and then leaps out), Chua (the electronic double scroll),
    Thomas, Pendulum (a double pendulum) or Predator & prey (Lotka-Volterra); a Chaos amount from a near loop to full
    chaos, and a speed; bounded and numerically safe, restarted from its seed if it ever escapes. Other systems kept for
    later: the jerk systems, Aizawa, Halvorsen, Dadras, the logistic and Hénon maps, the Duffing oscillator, the
    rungler (a shift register clocked and fed by its own oscillators).
  - **Snail**: three slow chaotic circuits, each travelling around two
    strange attractors at its own pace (about 20 seconds, 75 seconds and 35 minutes a trip at a Pace of x1), two with a
    Lean setting which attractor it lingers around, the third with none; each circuit's X and Y, and a mix of the three
    (the first and third added, the second taken away) split into its rising and falling halves, as outputs. Never
    restarted by a note. Its circuit's equations, a jerk-type system, to be found and checked before building.
  - **Tide**: a function generator of four related outputs, read from open firmware (MIT, `pichenettes/eurorack`,
    `tides2/`): a rise and a fall, Mode Loop, Once (AD) or Held (AR); Speed and Rate; Bend (the rise and fall from logarithmic to
    exponential); Slope (rise against fall); Smooth (a low-pass one way, a wavefolder the other); four outputs related by
    Outputs (Shapes, Phases, Ratios) and a Spread; at audio rate its Shape and Slope change meaning and narrow at high
    pitches to stay unaliased.
  - **Turing**: a random loop of 8 or 16 steps that repeats and slowly changes as a Change gauge allows, from locked to
    always new, after an open-hardware design.
  - **Bounce**: a ball dropped at each note, its bounces shrinking and speeding up to rest, for ratchets, dub delays and
    falling sweeps.
  - **Swarm**: four slow oscillators drifting into step and back out of it as their Pull rises and falls (coupled
    oscillators, Kuramoto).
- **Modulators drawn**, later, at a calm rate: each module draws what it is doing in its box (a chaotic system's path,
  the snails' traces, a tide's four outputs), worked out on the screen's side only while its box is on screen, and only if
  cheap.
- **Envelopes drawn**, later, at a calm rate: on the Envelopes tab, each envelope's shape drawn in its box from its settings, redrawn as they
  change, and a moving mark along it while a note fires it, worked out on the screen's side as the gauges' live markers
  are, only while the tab is on screen.
- **A spectrogram on the Instrument page**, later, at a calm rate: in the upper right, beside the settings above the tabs, the instrument's sound
  as a spectrogram: low notes at the bottom, time scrolling left, brightness its loudness; drawn only while the page is
  on screen.
- **Gauges stepped in big and small moves**: a synth gauge moved in blocks, as the piano roll's gauges move, `[` and
  `]` for a big move and other keys for a small one, perhaps with Shift (which UX.md allows nowhere today, so the keys are
  part of the discussion), the size of each move chosen gauge by gauge, since every gauge's range differs. A discussion,
  with the ranges laid out, before anything is built.
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
- **Drone**: A drone instrument of held, slowly moving oscillators, yet sounding only through the Amp, Env 1 opening it, as
  every engine does. A design, then a mockup.
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

## Mixing

- **The Bus page**: The Real Time switch goes, real time always on, and its place on the main screen opens a Bus page
  showing the Master Bus and the FX buses, so that several instruments can send to shared effects, such as one reverb.
  Built on a mixer: each instrument's own buffer, already kept, given a level, a pan and its sends, cheap since it costs a
  few multiplications a sample; a bus costs only its effects, once for all its instruments. The Synth Master Bus and
  Drum Master Bus idea below is a smaller first step toward it.
- **Pan on every instrument**: built-in and FluidSynth alike; FluidSynth's by CC 10 on the instrument's channel, the
  built-in synths' through the mixer.
- **FluidSynth through the effects**: FluidSynth playing each MIDI channel into a stereo pair of its own, so that each
  FluidSynth instrument gets the effect blocks, pan and the buses as a built-in synth does; FluidSynth's own reverb and
  chorus stay outside the chains.
- **Stereo**: every voice of a built-in synth stays mono and every instrument has a Pan; an instrument's effect chain
  turns stereo from its first stereo effect (a ping-pong delay, chorus, reverb or the rotary speaker), so that an
  instrument with none pays nothing. Stereo voices, such as unison spread across the field, come later.
- **A load meter**: llamatron measures each instrument's share of the time it has for each chunk of audio, shown on the
  Instrument page and the Bus page, the whole set's share shown in the header, where room is found, and the status line
  warning past about 70%. No track limit; using more cores is the next idea. Its place and form to discuss.
- **The instruments on several cores**: exporting first, each instrument rendering the whole song on a core of its own,
  summed in a fixed order so that every export is byte for byte the same. Then playback: a fixed pool of workers, one
  for each performance core but one, joining the sound card's real-time workgroup so that the system keeps them on the
  performance cores; each block's instruments handed out as jobs, the callback taking jobs too, the buffers summed in a
  fixed order. The pool is used only when the load meter shows the set needs it, past about a quarter of the block's
  time, lighter sets staying on one thread, both paths tested. Buses make a block two rounds, the instruments, then the
  buses; FluidSynth is one job, with its own setting for more cores measured; splitting one heavy instrument's voices
  across workers only if the meter shows it is needed.

## The Effects

- **Bax**: an effect after Peter Baxandall's published tone circuit of 1952, two gauges, Bass and Treble, each cutting or
  boosting a shelf.
- **Chorus**: a chorus effect, its design drawn from the best open-source choruses, studied when the time comes, with
  their licences checked.
- **Pre FX**: two slots before the filter, run for each sounding note, offering only the effects that keep no memory:
  Drive, Bitcrush and every filter as an effect. The effect blocks after the filter stay as they are. An effect with
  memory, a delay or a reverb, is left out there, since it would cost once a note and echo each note apart.
- **Spectral**: An effect, not a filter type: a bank of band filters splitting the sound into bands, each band's level
  set and moved, with no new patching; built together with the planned Harm engine, renamed Spectral.
  A design, then a mockup.
- **Variance**: an effect, subtle, lo-fi, an evolving undercurrent under melodies: a short delay whose time wanders at
  random, then a low-pass gate that recovers the tone. Its settings: Rate, how far apart the random pitch wanders fall, from
  rare to nervous; Damp, how softened and drawn out each wander is, from near instant to so slow it stops sounding like
  pitch modulation; Depth, how far, its range kept subtle; Mix and Volume; and LPG, how much the sound's own envelope opens
  the recovery filter. Still to research: the delay's times, the random source's character and the recovery filter's
  response; then a mockup.
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
