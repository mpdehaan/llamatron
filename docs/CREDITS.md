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
| [sst-filters](https://github.com/surge-synthesizer/sst-filters) | the Surge Synth Team, 2019 to 2025 | GPL-3.0-or-later | The Sallen-Key filter's model of the resonant two-pole circuit, adapted there from Odin 2 (`src/backend/src/filters/sallen_key.rs`), and the Multimode's saturating band state, after its ResonanceWarp (`src/backend/src/filters/mod.rs`) |
| [sst-effects](https://github.com/surge-synthesizer/sst-effects) | the Surge Synth Team | GPL-3.0-or-later | MultiTap's crossfade to a changed tap time: half the delay long, held between 10 and 500 ms, a change during a fade waiting for it to end (`src/backend/src/effects/multitap.rs`) |
| [hiir](http://ldesoras.free.fr/prod.html#src_hiir) | Laurent de Soras | WTFPL | The halfband that oversamples the saturating filters: its polyphase all-pass design's coefficients, after its Upsampler2x and Downsampler2x (`src/backend/src/dsp/oversample.rs`) |
| [chowdsp_utils](https://github.com/Chowdhury-DSP/chowdsp_utils) | Jatin Chowdhury | GPL-3.0 (its DSP modules) | MultiTap's Analog mode: the bucket-brigade device's input and output filters as sums of complex one-poles and their stepping at the clock's ticks, after Martin Holters and Julian Parker, "A Combined Model for a Bucket Brigade Device and its Input and Output Filters", DAFx-18 (`src/backend/src/effects/bucket_brigade.rs`) |
| [Odin 2](https://github.com/TheWaveWarden/odin2) | TheWaveWarden | GPL-3.0-or-later | The resonant two-pole filter sst-filters adapted, after Will Pirkle's virtual-analog design |
| [Streams](https://github.com/pichenettes/eurorack/tree/master/streams), Mutable Instruments | Emilie Gillet, 2014 | MIT | The vactrol's light history: a cell tiring under light and resting in the dark (`src/backend/src/envelopes/mod.rs`) |
| [stmlib](https://github.com/pichenettes/stmlib) | Emilie Gillet | MIT | The polyBLEP that smooths the jumps of the LFOs', Basic's, the SID pulse's and Asheville's waves, and the one-sample-delayed BLEP of the SID's hard sync (`src/backend/src/dsp/blep.rs`); the soft limit the OTA saturates through (`src/backend/src/filters/mod.rs`) |
| [Plaits](https://github.com/pichenettes/eurorack/tree/master/plaits), Mutable Instruments | Emilie Gillet, 2016 | MIT | Asheville's variable-shape waves and its Snap, the detuning curve that settles on unison, fifths and octaves (`src/backend/src/oscillators/asheville.rs`), the band-limited hard sync of the SID (`src/backend/src/oscillators/mod.rs`), and Bitcrush's Rate, its holds falling between samples (`src/backend/src/effects/mod.rs`) |
| [VCV Fundamental](https://github.com/VCVRack/Fundamental) | VCV and Andrew Belt | GPL-3.0-or-later | The OTA's saturating stages, each stage's gain scaled by its own saturation, after its VCF (`src/backend/src/filters/mod.rs`) |
| [reSID](https://github.com/libsidplayfp/resid) | Dag Lem, 2010 | GPL-2.0-or-later | The SID engine's waveform converter: the uneven, unterminated resistor ladder its saw, triangle and noise go through (`src/backend/src/oscillators/tables.rs`) |
| [Open303](https://sourceforge.net/p/open303/code) | Robin Schmidt, www.rs-met.com, 2009 | MIT | Oh3's saw and square, the coupling filters around the Diode filter, the Diode filter itself and its measured Env amount mapping (`src/backend/src/filters/diode.rs`) |

## Research Consulted

These projects were read to check how sounds really behave and to choose
designs, as references beside the instruments' own manuals; where llamatron
takes an algorithm from one, it moves to the table above.

| Project | Licence | What was read |
| --- | --- | --- |
| [Mutable Instruments eurorack](https://github.com/pichenettes/eurorack) | MIT (the STM32 modules), GPL-3.0-or-later (Edges, Grids, Branches) | Oscillators, filters, envelopes and effects across Plaits, Braids, Rings, Elements, Clouds, Beads, Warps, Tides, Stages and Peaks |
| [VCV Fundamental](https://github.com/VCVRack/Fundamental) | GPL-3.0-or-later | The VCO's minBLEP and sync, the VCF's oversampling, the wavetable VCO, the ADSR |
| [Befaco for VCV](https://github.com/VCVRack/Befaco) | GPL-3.0-or-later | Through-zero FM, DPW waves and ADAA wavefolding |
| [Bogaudio Modules](https://github.com/bogaudio/BogaudioModules) | GPL-3.0-or-later | Oscillators, multimode filters and the low-pass gate |
| [Audible Instruments](https://github.com/VCVRack/AudibleInstruments) | GPL-3.0-or-later | The Ripples OTA filter emulation |
| [Surge XT](https://github.com/surge-synthesizer/surge) | GPL-3.0-or-later | Its oscillators, including the Modern oscillator's DPW |
| [sst-waveshapers](https://github.com/surge-synthesizer/sst-waveshapers) | GPL-3.0 | Wavefolders with antiderivative anti-aliasing |
| [Ladder models](https://github.com/ddiakopoulos/MoogLadders) | each model its own: ISC, LGPL-3.0, Unlicense, BSD | Ladder filter models, among them the improved D'Angelo and Välimäki model |
| [libsidplayfp](https://github.com/libsidplayfp/libsidplayfp) | GPL-2.0-or-later | The SID chip's waveforms, envelopes and filter |

## Public Domain Music

llamatron's song wizard is built on music theory measured from public domain
music, in files that carry no restricting licence of their own: scores and
traditional tunes were read for how real melodies, harmonies
and phrases behave, and only those measurements went into the program. None
of the music is shipped with llamatron. Classical and traditional pieces from
these collections also appear in some of the demos, such as the mashups. The
song wizard will soon import downloaded corpus songs quickly, as patterns and
scenes to start from.

| Collection | Edited or kept by | Terms | What it holds | Folder |
| --- | --- | --- | --- | --- |
| [Scott Joplin's piano works](https://github.com/craigsapp/joplin) | Craig Stuart Sapp | public domain music, the encoding its editor's | Ragtime | `joplin` |
| [Chopin's mazurkas](https://github.com/craigsapp/chopin-mazurkas) | Craig Stuart Sapp | public domain music, the encoding its editor's | Piano | `chopin-mazurkas` |
| [Haydn's piano sonatas](https://github.com/craigsapp/haydn-piano-sonatas) | Craig Stuart Sapp | public domain music, the encoding its editor's | Piano | `haydn-piano-sonatas` |
| [Mozart's piano sonatas](https://github.com/craigsapp/mozart-piano-sonatas) | Craig Stuart Sapp | public domain music, the encoding its editor's | Piano | `mozart-piano-sonatas` |
| [Beethoven's piano sonatas](https://github.com/craigsapp/beethoven-piano-sonatas) | Craig Stuart Sapp | public domain music, the encoding its editor's | Piano | `beethoven-piano-sonatas` |
| [Beethoven's string quartets](https://github.com/craigsapp/beethoven-string-quartets) | Craig Stuart Sapp | public domain music, the encoding its editor's | Strings | `beethoven-string-quartets` |
| [Bach's Art of Fugue](https://github.com/craigsapp/art-of-the-fugue) | Craig Stuart Sapp | public domain music, the encoding its editor's | Counterpoint | `bach-art-of-fugue` |
| [Vivaldi's Opus 6](https://github.com/craigsapp/vivaldi-op6) | Craig Stuart Sapp | public domain music, the encoding its editor's | Concertos | `vivaldi-op6` |
| [Public Domain Song Anthology](https://doi.org/10.18130/V3/C4RD06) | David Berger and Chuck Israels, University of Virginia | CC0 | Lead sheets of songs out of copyright | `song-anthology` |
| [The Session's tunes](https://github.com/adactio/TheSession-data) | The Session | published openly for reuse; the tunes are traditional | Traditional dance tunes | `thesession` |

### Downloading the Corpus

The corpus is downloaded only by a person who wants it, for study, into
`output/corpus/`, which git ignores; nothing downloaded is committed or passed
on. From llamatron's top folder:

```
sh user_scripts/fetch_corpus.sh                 # asks collection by collection, with each one's size and terms
sh user_scripts/fetch_corpus.sh joplin thesession   # only the named collections
```

A collection is named by its folder in the table above, such as `joplin` or
`thesession`. The script asks before each download.
[User Scripts](USER_SCRIPTS.md) describes the script.
