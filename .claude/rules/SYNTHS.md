# How the built-in synths sound

The rules for the sound of every built-in engine, effect, filter and modulator (the user's). `.claude/rules/RUST.md`
holds how their code is written, and `.claude/notes/synthesis/` the research they draw on.

- Before an engine, effect, filter or modulator is built or changed, its chapter in `.claude/notes/synthesis/` is read,
  and what the work teaches is added to the chapter, written as a textbook.
- Nothing aliases by accident: every wave with a jump is band-limited, every bright corner is corrected, and every
  curve that shapes the sound is anti-aliased by antiderivatives, oversampling or both. Aliasing stays only where it
  is the instrument's own sound, such as Bitcrush's rate or a chip's converter, and the code says so.
- Analog character comes from modelling its causes: drift, free-running phase, saturation where the circuit
  saturates, and spread between parts. Every random source is seeded from the instrument and the note, so that every
  render is the same.
- Nothing clicks or zips: a setting that moves while a note sounds is smoothed, a delay's read head never jumps, and an
  envelope restarts from where it is.
- Every loop that saturates is guarded against blowing up and resets itself if it does; denormals are flushed; and
  coefficients are worked out at a control rate wherever every sample's is not needed.
- A change to how something sounds comes with a test that measures it, such as the stray tones in a high note's
  spectrum, beside the test that hears it through the tracker. Its cost per sample per voice is timed before and after,
  and given in the recap.
- Sound comes first in the synthesis: where a costlier algorithm sounds better, it is chosen over a cheap one, its cost
  per sample per voice measured and reported; no two engines, filters or effects of a kind may sound alike, held by a
  test that measures how far apart they are.
- The synthesis notes hold a chapter for each kind of device (each filter, each drum, each effect), with its full
  mathematics and coefficients.
- No filter self-oscillates or runs away into feedback, at any setting: full Resonance and full Drive give a peak that
  rings when the sound excites it and always dies away, never a tone of its own; a test holds every filter to it, its
  ringing from an impulse decaying within a set time and silence staying silent.
- A voice's oscillators run free, as analog oscillators do: each starts a note at a phase drawn on its own, seeded by
  the note, never all at one phase, since oscillators that start together lock, and two in tune add up to one fixed
  wave rather than mixing. A sub-oscillator is its oscillator divided down and stays locked to it, switching only where
  its oscillator's cycle begins. A test of every engine with several oscillators holds both, hearing two in tune mix.
- Nothing is connected that a person cannot see and undo (`.claude/rules/UX.md`, "Nothing hidden"): one part of a voice
  moves another only through a setting shown on its page or a Mod Matrix route. The fixed connections are Env 1 to the
  Amp and Env 2 to the cutoff through the filter's Env amount, each shown on screen with its way out (Disconnect
  filter); a new fixed connection needs the user's yes.
- Every oscillator has a Detune in cents and a Fine in tenths of a cent, each a destination of the Mod Matrix, so that
  any oscillator can beat slowly against another or be moved by a modulator, as the slow chaotic modulators make most
  of.

