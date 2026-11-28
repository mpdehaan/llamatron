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
- **Demos of the new modulators**: a demo for each new kind as it is built, the LFO's Fade in, Sync and Smooth random,
  and Snail, each made to show what the modulator does to music, and kept to the synth demos'
  rules (DEMO_IDEAS.md).
- **New-instrument choices**: Blank, Sampled (FluidSynth, where installed), Synth, Drum Synth or External MIDI, beside Normal
  and Percussion, each choosing a few settings that can still be changed. Mockup first.
- **The Engine tab's rest** (DESIGNS.md, "The Instrument page's Engine tab and presets"): engine and block presets; and a
  Glide switch on the MIDI engine, on unless set off, a glided step's note overlapping the next as today, off striking
  each note afresh, sending no CC.
- **The Mod Matrix's destinations**: Which to drop (Drive and the like need not be destinations), a discussion; later, some
  effects' settings as destinations, effect by effect.
- **Snail**: a Type of a Modulators slot beside LFO (`.claude/planning/DESIGNS.md`, "Snail"): three slow chaotic
  circuits, Slow, Slower and Slowest (about 20 seconds, 2 minutes and 30 minutes a cycle), each travelling around two
  attractors, Slow and Slower each with a gauge of its name setting which attractor it lingers around, Slowest with
  none; each circuit's X, Y and Z as Mod Matrix sources, and the two gauges as destinations. Never restarted by a note.
- **Snail's faster mode**: a switch on the Snail turning it from its slow circuits to faster chaotic systems, each a
  path in three dimensions, X, Y and Z, never repeating: Lorenz (two lobes it flips between), Rössler (a smoother
  spiral that now and then leaps out), Chua (the electronic double scroll), Thomas, a double pendulum, or predator and
  prey (Lotka-Volterra), with a speed and an amount from a near loop to full chaos; bounded and numerically safe,
  restarted from its seed if it ever escapes.
- **Loop**: a Type of a Modulators slot beside LFO and Snail (`.claude/planning/DESIGNS.md`, "Loop"): a loop of random
  steps, synced to the song, that repeats and changes as slowly as its Change allows, read at x1, x2, x4 and ÷2 as four
  Mod Matrix sources that stay in step, with Change as its destination.
- **Modulators drawn**, later, at a calm rate: each module draws what it is doing in its box (the snails' traces, a
  chaotic system's path), worked out on the screen's side only while its box is on screen, and only if
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
- **The drum instruments**: drums made by kind of synthesis, each drum its own settings (at most eight, named for what they
  do), chosen per drum track's instrument as today: MechaDrum, the basic kit of classic analog-style circuits (Kick, Punch
  Kick, Sine Kick, Morph Kick, Snare, Clap, Closed and Open Hat, Cymbal, Tom and Conga, Rim, Cowbell, Claves, Zap, Noise and
  Impulse); FM Drum (FM Kick, Snare, Tom, Hat, Cymbal, Clap and Cowbell); Physical Drum (Struck Kick, Snare and Tom, Hand
  Drum, Mallets, Shaker, Bloom Cymbal, Wood and Metal); and Karplus Drum (Classic, Pluck Tom, Snare, Hollow, Metal, Harmonic
  Drum, Buzz, Body Drum, Boom, then Bars and Bowls and a Mesh). Every drum plays as a live voice, sample by sample, like any
  synth's: its trigger fires the envelopes and restarts the LFOs, every drum setting is a destination of the mod matrix, and
  every tab works, nothing hidden; a drum starts with Env 1 not on the Amp (its own decay makes its loudness), Env 2 not on
  the filter and the Filter set to (none), each available to switch on. Every drum shares Drum FX (AM, one EQ band, a
  filter, rate reduction and drive); each hit's loudness is matched to a reference rather than its peak normalised; nothing of today's drums is kept for older sets; presets per drum and the demo updated
  (`.claude/notes/synthesis/`, the drum chapters).
- **The vactrol's age**: An old cell behaving less predictably strike to strike, within a musical range Claude proposes.
- **Asheville's later-version features**, after the later three-oscillator ladder monosynths and their rack versions:
  - Sync, Osc 2 hard-synced to Osc 1, starting its cycle again each time Osc 1's begins, each jump band-limited and
    Osc 2's sub restarting with it, so that sweeping Osc 2's Tune gives the tearing sync lead;
  - FM 3→1, an amount from 0 to 10 beside Ring, Osc 3 moving Osc 1's frequency linearly, so that the pitch stays
    centred as the depth rises, for bells and metallic basses;
  - an Osc 3 Key switch at audio speed, so that Osc 3 can be a drone or a fixed-pitch modulator under a moving note;
  - Mod Matrix destinations for each oscillator's pitch alone and for the Continuous model's Shape;
  - a Glide shape for every engine, Exponential (Asheville's default), Constant time and Constant rate, and Key priority
    (Low, High, Last), Low for Asheville by default;
  - a filter mode of two filters, High-pass then Low-pass in series with a Spacing between them, then Dual low-pass,
    two ladders in parallel panned apart with a Spacing, once the second ladder's cost is measured.
- **Asheville-Poly**, an engine after the divide-down polyphonic instruments of the late 1970s: every note divided down
  from two shared, slightly detuned master oscillators, so that octaves never beat and every note shimmers alike, each
  note keyed in as an organ's is, with its own simple filter, envelope and amp, velocity-sensitive; a Resonators effect
  of three band-passes, Low, Mid and High, each with Freq, Q and Level, mixed with the dry sound, usable by any
  instrument; and starting points for strings, a choir-like pad, organ, piano, brass and clavinet sounds.
- **Asheville's polyphonic mode**, after the late-1970s polyphonic analogs: every key its own voice, a shared filter and
  contours either paraphonic or per voice.
- **The table oscillators' level and bands**: the band-limited tables Pocket, SID and Oh3 read made right: one gain a
  waveform, taken from its full-band table (or the largest peak across its bands, for headroom), in place of each
  band's own peak, so that a narrow pulse no longer plays 5 to 11 dB louder above 4 kHz nor steps in level at each
  octave; two bands an octave, or neighbouring bands crossfaded, so that a note just above a band's bottom keeps its top
  octave; the tables cached by cycle and rate and shared, rather than built again at each compile; a phase precise
  enough for low notes, a four-point read under about 100 Hz, and guard samples so that a read never wraps. A shared
  band-limited step module, after SameBoy's kernel (MIT), for the chips' noise and steps. Each change measured by
  spectrum and level and timed before and after (`.claude/rules/SYNTHS.md`). The research is in
  `.claude/notes/synthesis/WAVETABLES.md` and `CHIP_TABLES.md`.
- **SID closer to its chip**: its noise clocked 16 shifts a tone cycle, as the chip's is, two octaves lower than today,
  band-limited; the converter's test held to the ladder's own weights and the dip at mid-cycle, the leakage dropped or
  kept only with the saturation curve; the combined waveforms from reSIDfp's model (GPL-2.0-or-later), with a choice of
  the chip's two revisions and the envelope's 8-bit converter; later, the filter, the later revision's linear cutoff
  first (`.claude/notes/synthesis/CHIP_TABLES.md`).
  Beside the chip's own sound: the combined waveforms; the chip's filter as a Filter type, its mixed modes and the first
  revision's distortion; three oscillators to a voice, each with its wave, level, transpose and tune, ring and sync
  chained from the one before, in place of the hidden second; a fixed pitch for the second oscillator; an arpeggio
  Speed of one to four frames a step and a Chord mode that cycles a held chord; a Frame rate of 50, 60, 100 or 200 Hz;
  the Chip revision, and the first revision's thump at note-on; and Ring kept on every wave, the SID page saying that
  this goes beyond the chip, which rings only the triangle.
- **Pocket closer to its chip**: the wave channel on its own clock, an octave under the pulses' for one register value,
  and notes under 64 Hz played as the chip plays them; the noise on the chip's grid of divisors and shifts,
  band-limited; and, as a faithful mode, levels from silence to full with the console's 28 Hz high-pass, which gives
  its soft ticks and thumps, with the sweep's step of 0 checked against SameBoy (`CHIP_TABLES.md`).
- **DustCart from the open tables**: DustCart built from Mesen2's tables (GPL-3.0), cross-checked against
  Game_Music_Emu (LGPL-2.1-or-later): the duty sequences, the stepped triangle, the noise periods and the short mode's
  loop, the sample channel's rates, the sweep's two complements, the console's mixer folded into each channel's levels
  and its output filters; the triangle's buzz kept as its own sound, silenced at periods that would alias
  (`CHIP_TABLES.md`).
- **Durham**: A homage to the classic analog bass pedal synth, on its modern descendant's panel, exposing only what that panel
  has; the filter very nearly perfect (the D'Angelo-Välimäki ladder). Research in `MONOSYNTHS.md`, "Durham"; mockup first.
- **Drone**: A drone instrument of held, slowly moving oscillators, yet sounding only through the Amp, Env 1 opening it, as
  every engine does, drawing on the professor's research into a classic boutique drone synth's ideas: its special LFOs,
  its tone and how its voices interact. A design, then a mockup.
- **A speech synth**: a voice that speaks or sings words, the words to say written in a field of their own on each
  scene, so that the voice says that scene's words as its clips play.
- **A riser synth**: an instrument dedicated to rises, sweeps and build-ups (risers, falls, impacts and whooshes for
  transitions), after the professor's research into the dedicated riser instruments of sample-based producers' tools. A
  note only triggers it: One Shot, the default, plays a rise whose length is set on its panel in bars, beats or seconds,
  counted over the song's tempo, so that every curve lands on its target at the end; Until release rises while the note is
  held and fires the impact when it is let go, for playing by hand.
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
  phase-locked footages (Stringy, Combo Organ), synced-square PWM (Monorail, Chirpy), the 1980s home console's stepped triangle (DustCart, BitArcade),
  Rings' resonator (the Resonator filter), sst-filters' further models (licence checked).
- **More of FluidSynth** exposed as an engine of the backend.
- **The agreed engines' designs**: ComplexOsc (one engine for the classic West Coast and the modern complex oscillator), Hurt
  (after the harmonic oscillator, now to become Spectral), the Choir, and the modular study's engines (Formant Blip,
  Bytecrunch, Flock and the rest), as agreed in `.claude/planning/DESIGNS.md`, "Built-in engines agreed and not yet built".

## Mixing

- **The Bus page**: The place on the main screen where the Real Time switch stood, which the Instruments cell spans
  for now, opens a Bus page
  showing the Master Bus and the FX buses, so that several instruments can send to shared effects, such as one reverb.
  Built on a mixer: each instrument's own buffer, already kept, given a level, a pan and its sends, cheap since it costs a
  few multiplications a sample; a bus costs only its effects, once for all its instruments. The Synth Master Bus and
  Drum Master Bus idea below is a smaller first step toward it.
- **The mixer on each track**: the mixer is shown on each track rather than on the instrument, for ease of use: every
  track has a Pan, from 0 to 100, 50 the middle by default, and a Volume, 100% by default, on the Track page, so that
  tracks sharing an instrument are panned and levelled apart. A track playing an instrument is its own instance of it,
  sharing the instrument's settings, not one sound shared by every track. Everything is stereo, FluidSynth included,
  each FluidSynth instrument played into a stereo pair of its own where the library allows (FluidSynth through the
  effects, below), which opens the way to panning and chorus effects; Pan is a destination of the mod matrix. A
  FluidSynth instrument is panned by the mixer too, never by General MIDI's pan, wherever FluidSynth's output allows, so
  that the effects move its place smoothly as they move a built-in synth's. How the instrument's own Pan, which the
  General MIDI export uses today, meets the track's is settled with the design.
  A Mixer page opens from the main screen with `M` (Mixer), in the cell where the Real Time switch stood; to start it
  offers only modes and drive, and no effects bus.
  Each track and bus has a character stage: Drive (compensated, so it changes colour rather than loudness), Amount (a blend
  with the stage's clean path) and Character: Tube (a push-pull cell at rest), Warm Tube (a single-ended stage leaning more
  as it gets louder), Iron (a transformer saturating the bass more than the treble), Desk (a class-A amplifier with a light
  transformer) and Tube and Iron (the whole chain).
- **A tube compressor and limiter**, for buses: a variable-gain tube cell whose distortion grows as it compresses, a soft
  knee hardening toward limiting, a release that follows the programme; Input, Threshold, Knee, Time (six settings of its
  own, two following the programme), Link (stereo, dual or mid and side), Output, Mix and Colour, clean to dirty.
- **An equaliser colour stage**: four bands with shelf or bell, broad curves that narrow as they are boosted, stepped
  frequencies of its own, two gain ranges, inside a driven amplifier and transformer chain so that a boost changes the
  grain; Drive and Colour.
- **FluidSynth through the effects**: FluidSynth playing each MIDI channel into a stereo pair of its own, so that each
  FluidSynth instrument gets the effect blocks, pan and the buses as a built-in synth does; FluidSynth's own reverb and
  chorus stay outside the chains.
- **Stereo**: every voice of a built-in synth stays mono and every instrument has a Pan; an instrument's effect chain
  turns stereo from its first stereo effect (a ping-pong delay, chorus, reverb or the rotary speaker), so that an
  instrument with none pays nothing. Stereo voices, such as unison spread across the field, come later. With it,
  MultiTap's tap rows gain a third cell, each tap's place from left to right, and a ping-pong choice.
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

- **Chorus**: a chorus effect, its design drawn from the best open-source choruses, studied when the time comes, with
  their licences checked.
- **Bitcrush rebuilt as an 8-bit converter**: Bitcrush becomes a desktop 8-bit crusher with switchable bits, its
  settings in this order: Drive, -12 to +15 dB, +3 dB untouched, into a soft diode-style clip anti-aliased as Drive's
  curves are; Rate, the converter's clock, 250 Hz to 30 kHz, 12 kHz; Fold, 0 to 100%, 0%, a plain gauge, folding each
  held value past a threshold; Bits, a row of eight cells, the top bit first at the left (8 7 6 5 4 3 2 1), each stepped
  between on (`●`), off (`·`) and inverted (`◆`), every bit on untouched; Filter, Low pass, Band pass or High pass, Low
  pass; Cutoff, 20 Hz to 15 kHz, 9 kHz; Q, 0.5 to 4, 0.7, gentle; and Dry and Wet as two gauges, 0% and 100%, in place of
  Mix. The sound passes Drive, a hold at the clock with its steps smoothed, the fold, the converter with the bit switches
  as one table of 256 levels, a DC blocker and the filter; the clock's aliasing is kept as the sound, a bit switched
  crossfades over about 10 ms, and the wet signal has a safety limiter. Today's Bits, Rate and Mix go, with no migration.
  The research is in `.claude/notes/synthesis/BITCRUSHING.md`.
- **Bitcrush's Jitter and mu-law converter**: a Jitter gauge wobbling the converter's clock, and a choice of converter,
  linear or mu-law, which compresses quiet sounds before the bits as telephone audio does.
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
- **The envelopes let go of the LPG**: with the filter set to LPG, the low-pass gate is the note's envelope, so neither
  envelope chops it up again: Env 1 stays enabled, to modulate anything, but is no longer routed to the amp, and Env 2
  loses its route to the filter, the "(filter2)" its page shows, so that it no longer reaches the LPG. Nothing is written
  under either; Env 1's heading simply no longer says "(amp)". To make the path plain, the instrument's tabs put Filter and Amp ahead of
  Envelopes, and Mod Matrix right after Modulators: Oscillators, Filter, Amp, Envelopes, Modulators, Mod Matrix, then
  the rest, the documents' synth pages following the same order.
- **Sine first on the Basic oscillators**: the Basic engine's oscillators start on a sine wave, and the sine stands at
  the top of the list of waves, since a sine makes a fine kick.
- **NoiseBuster**, a family of glitch and noise voices and effects, bright and alive, sharing a clock locked to the note
  (aliasing landing on harmonics, a Grain control) and band-limited steps at exact edge times: Shift-Register Tone (a
  register oscillator whose Tone changes timbre at constant pitch, from square through buzzes to noise, with fractional
  Tone, a second register modulating the first, a shape layer and built-in clamp and gate for percussion), Six-Mode Strike
  (a drum voice from kicks to bells), Industrial Saw (six saws, sync as a formula, a modulus destroyer, a tracking filter,
  a coherent rate blur and one envelope sent to many stages), Staged Destroyer (an effect whose stage order is a control),
  Twin-Formant Oscillator, then Clamp Gate, Tracking Crusher, Operator Crossfade PM, Spectrum Builder, Folding Chorus,
  Lattice Noise, register ring and gate effects, a formant bank and a binary rhythm source.
- **New filter characters**, named for how they sound: Bite (a two-pole diode-bridge filter with low, band and high
  inputs, gritty, unstable and vocal, biting hard when driven), Break (an overloaded-integrator filter whose resonance
  shrieks and crunches, sounding broken in a musical way), Buzz (unbuffered CMOS inverters as an SVF, buzzy and raspy
  with strong even harmonics), Sizzle (a bright, sizzling diode ladder), Vowel (three
  to five resonant band-passes morphing between vowels) and Comb (a delay tuned to the note, with damping and saturation
  in its loop); and a Pole Mix option on the OTA and the Ladder, mixing their stages' outputs, its choices the
  responses the mixes make: high-pass, band-pass, notch and those between.
- **Synths on several threads**: first a timing tool that plays a dense set and reports the synths' load and its peak,
  so that every change to the synthesis is measured against it; then each audio block's instruments shared among a few
  worker threads made at start-up, at least three, more as the computer's cores allow with some left for everything
  else, so that a less powerful computer gains as much as it can; the built-in synths are not expected to run beside a
  DAW's own synths played over MIDI, so they may take that share of the computer. The workers allocate nothing and take no locks, a late worker's
  instruments are rendered by the callback itself so that nothing drops out, and each worker ends with its owner.
- **The Mod Matrix names each destination by its block**: every block of an instrument offers what can be moved in it,
  and the Destination picker names each by its block and setting, such as `Oscillator / Pitch`, `Filter / Cutoff`,
  `LFO 1 / Rate` and `FX 1 / Mix`, grouped by block in the blocks' order. Each component declares what it offers the
  Mod Matrix in one standard form in its registry entry (each setting a route may move, with its label, range and
  reach), so that more of a component is made movable by adding to its entry.
- **Steps, a per-frame table for every engine**: a table of up to 32 rows played at a frame rate (the engine's own, a
  fixed rate, or the tempo), each row holding lanes for a note (relative or fixed), a level, a pulse width or duty, a
  wave, a noise period and a pan, with a loop point and a release point, as a tracker's instrument table is. It is a
  tab of its own and a Mod Matrix source; the chip engines show its common uses as simple fields of their own
  (Arpeggio, Duty steps, Drop, Vibrato delay), and the SID's Arpeggio becomes its Note lane.
- **Glissando and LFO extras**: Glissando, gliding in semitone steps, among the Glide shapes; an LFO One-shot and a
  Start phase.

