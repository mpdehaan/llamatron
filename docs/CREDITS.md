# Credits

llamatron's built-in synths use other people's open work where it already
models a sound well, under licences compatible with llamatron's own, the GNU
General Public License, version 3 or later. Each is credited here and in a
comment above every algorithm taken from it in the code.

| Work | Author | Licence | What llamatron uses |
| --- | --- | --- | --- |
| [sst-filters](https://github.com/surge-synthesizer/sst-filters) | the Surge Synth Team, 2019 to 2025 | GPL-3.0-or-later | The Sallen-Key filter's model of the resonant two-pole circuit, adapted there from Odin 2 (`src/backend/src/voice/sallen_key.rs`) |
| [Odin 2](https://github.com/TheWaveWarden/odin2) | TheWaveWarden | GPL-3.0-or-later | The resonant two-pole filter sst-filters adapted, after Will Pirkle's virtual-analog design |
| [Streams](https://github.com/pichenettes/eurorack/tree/master/streams), Mutable Instruments | Emilie Gillet, 2014 | MIT | The vactrol's light history: a cell tiring under light and resting in the dark (`src/backend/src/voice/envelopes.rs`) |
| [Open303](https://sourceforge.net/p/open303/code) | Robin Schmidt, www.rs-met.com, 2009 | MIT | Fishline's saw and square, the coupling filters around the Diode filter, the Diode filter itself and its measured Env amount mapping (`src/backend/src/voice/acid.rs`) |
