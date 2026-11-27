# Synthesis Notes

Research for the built-in synths and effects, written like a textbook: principles, algorithms and open
implementations, from papers and open-source code only, each open project named with its licence, and no commercial
reference of any kind.

- `DELAYS.md`: delay lines, fractional reads, moving delay times, feedback structures, the bucket-brigade device and
  its digital models.
- `TAPE.md`: magnetic tape and its machines: hysteresis and its solvers, bias, play-head losses and head bump,
  equalisation standards, hiss, wow and flutter and their modulated-delay realisation, dropouts and crinkle, a second
  generation, azimuth, and the costs of each stage in a per-instrument callback.
- `QUALITY_RESEARCH.md`: character and quality in the virtual-analog building blocks: oscillator anti-aliasing (BLEP,
  DPW, BLAMP, mip-mapped tables), analog drift, zero-delay-feedback filters and their nonlinear solvers (ladder, diode,
  OTA, Sallen-Key, SVF), oversampling, antiderivative anti-aliasing, drive and bitcrushing, envelopes, the low-pass
  gate and vactrol, the analog drum circuits, LFOs, the Baxandall tone control and numerical hygiene.
- `EFFECTS_RESEARCH.md`: chorus, ensemble, flanger, phaser, tremolo and auto-pan, the rotary speaker, algorithmic
  reverbs (Freeverb, feedback delay networks, the Dattorro plate, randomly modulated halls), spring reverb, tape echo,
  telephone colour, stutter, equalisers, the spectral band filter and the wandering-delay variance effect.
- `ENGINES_RESEARCH.md`: FM and phase modulation, unison and chord voices, wavetables, additive and West Coast
  oscillators, the tonewheel and combo organs, string machines and synth brass, formant choirs, linear-predictive
  speech, plucked, modal, bowed and blown physical models, the piano, chip voices, bytebeat, noise voices, drum
  machines and drones.
- `MODULATORS_RESEARCH.md`: chaotic systems and their safe integration, slow jerk circuits, the function generator,
  the random looping shift register, the bouncing ball, Kuramoto coupled oscillators, smooth random sources and
  followers, and the modulation matrix.
- `BITCRUSHING.md`: digital degradation: sample-rate reduction (whole-sample and fractional holds, band-limited
  steps, reconstruction, jitter, rates that follow the note), quantisers and number formats, bits muted, forced,
  inverted and rearranged, the converter as one table, dither, mu-law and A-law, gain-ranging converters and ladder
  errors, early sampler converters, folding, wrapping, rectifiers and zero-crossing tricks, table waveshapers,
  wavetable oscillators with digital character, the tone filter and separate dry and wet, and their costs.
- `HARD_DIGITAL.md`: hard digital synthesis: shift-register noise and the chips' registers, clocked, looping and
  filtered noise, dust and particles, dividers and integer pitch, bytebeat and its semantics, bit-wise oscillators and
  Walsh functions, digital cross-modulation, phase distortion and accumulator truncation, chaotic maps, cellular
  automata, Collatz sequences, dynamic stochastic and fractal synthesis, glitch techniques, circuit-bent toys as
  algorithms, the harsh-noise wall, and destroyer distortions with their safety and costs.
- `WAVETABLES.md`: wavetable synthesis and the stacked saw: table sizes, band-limited mip levels and their spacing and
  crossfades, per-block spectra, interpolation orders and their images, normalisation, phase alignment, crossfade and
  spectral morphing, phase, spectral and amplitude warps, tables from harmonics, formulas, drawings, recordings and
  long ensemble tables, integrated wavetables, building tables off the callback, tables as LFOs, drums, chip, organ
  and waveshaper voices, the published measurements of a 1990s seven-saw oscillator, denser stacks, unison in open
  synthesizers, detune distributions, phase at note-on, and the costs and loudness of a stack.
- `CHIP_TABLES.md`: the measured and derived data of three sound chips (the 1982 home computer's chip in both revisions, the 1989 handheld console, the 1983 home console) from the open emulators, with their licences: oscillators, ladder converters, combined waveforms, shift registers, envelopes, filters, period, duty, length and mixer tables, high-pass corners, wave memory at power-on, which aliasing is the chip's own, and band-limiting by tables, band-limited steps and polyBLEP.
