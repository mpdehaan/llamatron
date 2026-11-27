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
