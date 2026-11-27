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
