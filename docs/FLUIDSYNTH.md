# FluidSynth

FluidSynth is a free software synthesizer. llamatron uses it to play a set with no synthesizer, no DAW and no MIDI setup: every demo plays through FluidSynth as the demo comes, and the WAV export renders through FluidSynth. This page covers installing FluidSynth, how the tracker uses FluidSynth, and what to do when nothing sounds.

## When to Use FluidSynth

FluidSynth is the quickest way to hear llamatron: install it once, open any demo and press `Space`. FluidSynth plays General MIDI sounds, one basic sound for each of 128 instruments, which is enough to compose with and to share a song as audio. For the real thing, play the tracks through your own synthesizers or a DAW instead, as [MIDI Setup](MIDI_SETUP.md) describes, or export a Live set and give each track an instrument you like. A set can mix the two, some tracks through FluidSynth and others through MIDI ports.

## Installation

On a Mac, from the project folder:

```
sh user_scripts/install_fluidsynth.sh
```

The script needs Homebrew, the Mac's package manager, and offers to install it if it isn't there, installing nothing unless you say yes. The script then installs FluidSynth with Homebrew and downloads the free GeneralUser GS SoundFont, the sounds FluidSynth plays, into `~/soundfonts`. On an Apple Silicon Mac it uses only the Apple Silicon Homebrew in `/opt/homebrew`, never an Intel copy in `/usr/local`, which would install Intel programs. Running it again does nothing that's already done.

## Tracker Integration

- **Instruments.** An instrument whose Device is `*FluidSynth` plays through FluidSynth; [Instruments](INSTRUMENTS.md) describes the setting, its automatic channels and its General MIDI sound. Every demo's instruments play this way.
- **Starting and stopping.** The tracker starts FluidSynth itself the first time something plays through it, waits until it is ready so that no note is lost, and ends it when the tracker quits, however it quits.
- **Where the tracker looks.** The tracker looks for FluidSynth in `/opt/homebrew`, then `/usr/local`, then the folders on your PATH, and for the SoundFont in `~/soundfonts`, where the install script puts them.
- **Sound.** FluidSynth plays to the Mac's default audio output, at a level set so that the loudest demo peaks just below full scale.
- **When FluidSynth isn't installed.** Opening a set whose tracks play through FluidSynth says so in a dialog, and playing tells you to run the install script.

## WAV Files

The WAV (FluidSynth) export renders a song's FluidSynth tracks to a WAV file faster than real time, as [Exporting](EXPORTING.md) describes, and [Listening to the Demos](LISTENING_TO_DEMOS.md) turns every demo into WAV files the same way.
