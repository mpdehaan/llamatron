# Synth Ideas

Wanted work on the built-in synths, drum engines and effects: what each idea is, never its status or order (those are in
`.claude/planning/QUEUE.md`). An agreed design moves to `.claude/planning/DESIGNS.md`; an idea leaves this file once built.
The professor's research is in `.claude/notes/synthesis/`.

## The Instrument Page

- **The Amp stage's rest** (DESIGNS.md, "The Amp stage and the one vactrol module"): the low-pass gate as an Amp type; one
  vactrol module everywhere, Response (in place of Cell, with a migration), Memory, Age and Stability; the gate's Trigger
  (Filter tab: Trigger, Gate, Env 1 to Env 3; Amp tab: Trigger, Gate, Env 1), Mode (Filter tab Lowpass or Both; Amp tab VCA,
  Lowpass or Both), Signal (Oscillator, Ping or Both) with Ping time.
- **Built-in modulation**: beneath each envelope, LFO and filter, routes of its own, off by default, each choosing
  Destination, Via and Amount from the Mod Matrix's values, so that the Mod Matrix drops to four fully custom slots. Env 1 stays
  wired to the Amp always; Env 2 stays wired to the filter, with a "Disconnect filter" switch. Mockup first.
- **New-instrument choices**: Blank, Sampled (FluidSynth, where installed), Synth, Drum Synth or External MIDI, beside Normal
  and Percussion, each choosing a few settings that can still be changed. Mockup first.
- **The Engine tab** (DESIGNS.md, "The Instrument page's Engine tab and presets"): Off, MIDI, FluidSynth and LlamaSynth, its
  migration, engine and block presets; with it, a Glide switch on the MIDI engine, as if it were a synth.
- **The Mod Matrix's destinations**: which to drop (Drive and the like need not be destinations), a discussion; later, some
  effects' settings as destinations, effect by effect.
- **A one-voice instrument's note priority**: lowest, highest or last, beside today's lowest-of-a-chord.
- **The instrument on the Track page**: the assigned instrument's settings drawn below the track's own, editable there.
- **The Instruments page as a rack**: a mockup of every instrument's tab rows in one column, each expanded or collapsed and
  saved with the set; if built, the single Instrument page goes.
- **Presets** for the built-in synths: a discussion.

## The Engines

- **Every engine and effect redesigned from the professor's research** (`FLAVORS.md` and the rest): each engine's settings
  discussed with a mockup of its Synth tab, one a reply. The professor first reviews every engine, drum and effect proposed and
  says which merge and which stay apart. Each drum engine declares a hard playable range in octaves, clamping or refusing notes
  past it, shown on its mockup.
- **MechaDrum split** into one engine a drum ("MechaDrum Kick", "MechaDrum Snare", ...), each with its own settings after the
  drum machine's manual's drum configurations, and presets per drum type; its demo updated.
- **The vactrol's age**: an old cell behaving less predictably strike to strike, within a musical range Claude proposes.
- **Asheville's polyphonic mode**, after the late-1970s polyphonic analogs: every key its own voice, a shared filter and
  contours either paraphonic or per voice.
- **Durham**: a homage to the classic analog bass pedal synth, on its modern descendant's panel, exposing only what that panel
  has; the filter very nearly perfect (the D'Angelo-Välimäki ladder). Research in `MONOSYNTHS.md`, "Durham"; mockup first.
- **Spectral**: a filter type, a bank of band filters, only what
  their knobs, sliders and switches control, no new patching; built together with the planned Harm engine, renamed Spectral.
  Research both panels, then a mockup.
- **Drone**: a drone instrument of held, slowly moving oscillators, yet sounding only through the Amp, Env 1
  opening it, as every engine does. Research its panel, then a mockup.
- **A brass synth**, somewhat after Stringy, for the bright, stabbing synth brass of early-1980s rock and pop keyboard anthems,
  as simple as the vintage brass ensemble keyboards (research which to follow).
- **Brass and wind** among the physical modelling ideas.
- **A Choir engine**, after the mono groovebox's choir voice (`CHOIR_AND_PLUCK.md`).
- **The talking-toy voice**: a buzz or noise through a tenth-order all-pole filter stepping 40 frames a second through vowel and
  consonant frames chosen per step, 4-bit coefficients, from our own formant targets; its name is open (`MODULAR_IDEAS.md`).
- **The other engines and effects** starred in `ALL_INSTRUMENTS.md` and `ALL_EFFECTS.md`, drums included, once their names,
  groups, presets and block swapping are settled (open there: the low-pass gate's Strike and Gate, the Effects field, the engine
  dialog's columns, a picker column of engines and of effects).
- **Kept for engines when built**: through-zero FM and ADAA folders (ComplexOsc), integrated wavetables (Wavetable),
  phase-locked footages (Stringy, Combo Organ), synced-square PWM (Monorail, Chirpy), the NES triangle (DustCart, BitArcade),
  Rings' resonator (the Resonator filter), sst-filters' further models (licence checked).
- **More of FluidSynth** exposed as an engine of the backend.

## The Effects

- **Variance**: an effect, subtle, lo-fi, an evolving undercurrent under
  melodies. Its manual's PDF is saved; extract and research, then a mockup.
- **The professor's effect plans**: Legend's Mode A on Freeverb3's Progenitor (GPL-2.0+); the Spring on stretched all-passes
  after Surge's ChowDSP spring (GPL-3.0+); Tape Echo's Time as tape speed, one speed curve for every head; Dattorro's centre-tap
  chorus feedback; setBfree's rotary geometry; CHOW Tape's loss filter; EQ bands as trapezoidal SVFs with Vicanek's matched
  designs; Drive's ADAA with 2x at the top.
