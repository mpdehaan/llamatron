# Credits

In addition to llamatron, Copyright (C) 2026 Michael DeHaan, released under
the GNU General Public License, version 3 or later, this code has benefitted
from research and work from the open source projects below.

## Code llamatron Uses

llamatron's built-in synths use other people's open work where it already
models a sound well, only under licences compatible with llamatron's own. The
implementations are llamatron's own, read from theirs, and a comment above
every algorithm in the code names the work it follows and its licence.

| Work | Author | Licence | What llamatron uses |
| --- | --- | --- | --- |
| [sst-filters](https://github.com/surge-synthesizer/sst-filters) | the Surge Synth Team, 2019 to 2025 | GPL-3.0-or-later | The Sallen-Key filter's model of the resonant two-pole circuit, adapted there from Odin 2 (`src/backend/src/voice/sallen_key.rs`) |
| [Odin 2](https://github.com/TheWaveWarden/odin2) | TheWaveWarden | GPL-3.0-or-later | The resonant two-pole filter sst-filters adapted, after Will Pirkle's virtual-analog design |
| [Streams](https://github.com/pichenettes/eurorack/tree/master/streams), Mutable Instruments | Emilie Gillet, 2014 | MIT | The vactrol's light history: a cell tiring under light and resting in the dark (`src/backend/src/voice/envelopes.rs`) |
| [stmlib](https://github.com/pichenettes/stmlib) | Emilie Gillet | MIT | The polyBLEP that smooths the jumps of the LFOs' saws and square and of Asheville's waves (`src/backend/src/voice/modulation.rs`, `src/backend/src/voice/asheville.rs`) |
| [Plaits](https://github.com/pichenettes/eurorack/tree/master/plaits), Mutable Instruments | Emilie Gillet, 2016 | MIT | Asheville's variable-shape waves and its Snap, the detuning curve that settles on unison, fifths and octaves (`src/backend/src/voice/asheville.rs`) |
| [reSID](https://github.com/libsidplayfp/resid) | Dag Lem, 2010 | GPL-2.0-or-later | The SID engine's waveform converter: the uneven, unterminated resistor ladder its saw, triangle and noise go through (`src/backend/src/voice/tables.rs`) |
| [Open303](https://sourceforge.net/p/open303/code) | Robin Schmidt, www.rs-met.com, 2009 | MIT | Fishline's saw and square, the coupling filters around the Diode filter, the Diode filter itself and its measured Env amount mapping (`src/backend/src/voice/acid.rs`) |

## Research Consulted

These projects were read to check how sounds really behave and to choose
designs, as references beside the instruments' own manuals; where llamatron
takes an algorithm from one, it moves to the table above.

| Project | Licence | What was read |
| --- | --- | --- |
| [Mutable Instruments eurorack](https://github.com/pichenettes/eurorack) | MIT (the STM32 modules), GPL-3.0-or-later (Edges, Grids, Branches) | Oscillators, filters, envelopes and effects across Plaits, Braids, Rings, Elements, Clouds, Beads, Warps, Tides, Stages and Peaks |
| [VCV Fundamental](https://github.com/VCVRack/Fundamental) | GPL-3.0-or-later | The VCO's minBLEP and sync, the VCF's ladder, the wavetable VCO, the ADSR |
| [Befaco for VCV](https://github.com/VCVRack/Befaco) | GPL-3.0-or-later | Through-zero FM, DPW waves and ADAA wavefolding |
| [Bogaudio Modules](https://github.com/bogaudio/BogaudioModules) | GPL-3.0-or-later | Oscillators, multimode filters and the low-pass gate |
| [Audible Instruments](https://github.com/VCVRack/AudibleInstruments) | GPL-3.0-or-later | The Ripples OTA filter emulation |
| [Surge XT](https://github.com/surge-synthesizer/surge) | GPL-3.0-or-later | Its oscillators, including the Modern oscillator's DPW |
| [sst-waveshapers](https://github.com/surge-synthesizer/sst-waveshapers) | GPL-3.0 | Wavefolders with antiderivative anti-aliasing |
| [Ladder models](https://github.com/ddiakopoulos/MoogLadders) | each model its own: ISC, LGPL-3.0, Unlicense, BSD | Ladder filter models, among them the improved D'Angelo and Välimäki model |
| [libsidplayfp](https://github.com/libsidplayfp/libsidplayfp) | GPL-2.0-or-later | The SID chip's waveforms, envelopes and filter |
