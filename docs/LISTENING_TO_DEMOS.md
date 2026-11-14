# Listening to the Demos

Hearing the examples llamatron comes with needs no synthesizer, DAW or MIDI player. Three scripts turn every example into a WAV file through FluidSynth, a free software synthesizer, and play the file you pick in the terminal. This page covers those scripts on a Mac; run each from the project folder.

Many of these songs are created relatively quickly and by (gulp) AI as the project was in initial stages.  Not llamatron, exactly, though they all feature llamatron structures!.  If played with FluidSynth they may not sound as good as if you made better instrument choices like using a commercial VST, AU, or Component plugin or hardware synthesizer for each track.  We are gradually improving various demos and they may change quite a bit over time. Where a video is shown below a demo, the video may be obsolete, because the demo song has been rewritten or the application's UX or visualizers have changed since it was recorded.

## FluidSynth

The scripts need FluidSynth, which `sh user_scripts/install_fluidsynth.sh` installs, as [FluidSynth](FLUIDSYNTH.md) describes. The next script installs FluidSynth itself when it is missing, so installing it beforehand only gets that step out of the way.

## WAV Files

```
sh user_scripts/demos_to_wavs.sh
```

Each time it runs, the script:

1. makes sure FluidSynth and the SoundFont are installed, installing them if they aren't;
2. makes the preview MIDI files first, with `sh user_scripts/demos_to_midi.sh`, which exports every example as one General MIDI file into `previews/`, with drums on channel 10 and every other track on the General MIDI sound its instrument chose, and writes `previews/DEMOS.md`, a table of every set with what it plays, how long it lasts and the features it uses;
3. plays each preview through FluidSynth into a WAV file beside it, such as `previews/classic_strum.wav`, faster than real time, a whole three-minute song in about a second;
4. normalizes each WAV file, raising the whole file until its loudest moment is 1 dB below the most a WAV file can hold, the usual headroom when music is prepared for streaming. Every demo is then about as loud as the next and none distorts, while the quiet and loud parts of a song keep their difference, so the Bolero still grows.

To make only some of the files, name their previews, such as `sh user_scripts/demos_to_wavs.sh previews/classic_strum.mid`.

The files are named after the set, such as `previews/classic_strum.wav`, or after the set and the song when a set's song has another name. `previews/` is ignored by git, and the script only ever writes WAV files there, replacing the ones it made before; it never deletes anything. To start afresh, delete the folder yourself and run the script again.

## Playback

```
sh user_scripts/play_demo.sh
```

The script lists the demos' WAV files, numbered, and plays the one whose number you type, with a line showing the time played, the demo's length and a bar filling across. The script builds nothing, so it starts at once; run it again to play another. `sh user_scripts/play_demo.sh classic_strum` plays a demo by name and `sh user_scripts/play_demo.sh 12` by its number, skipping the list, and `--list` prints the list alone. Before a demo plays, the script says its number and what the demo is.

The script plays with `afplay`, macOS's own command-line audio player, which plays the file through your speakers and exits, without opening Music or adding the file to a library. `Ctrl+C` stops playback, and `afplay previews/classic_strum.wav` plays a file directly. The WAV files also play in any other player, and can be shared or uploaded as they are.

## Preview MIDI Files

The preview MIDI files play in any General MIDI player. On a Mac, double-clicking a file in the Finder, or `open previews/classic_strum.mid` from the command line, opens it in whatever app plays MIDI. GarageBand, free from the App Store, opens a MIDI file as a project of tracks you can play; QuickTime Player no longer plays MIDI files.

## Sound Quality

The previews won't sound as good as llamatron through a DAW, since a plain MIDI player has only one basic sound for each of General MIDI's 128 instruments. For the real thing, export a set as a Live set or as MIDI stems and give each track an instrument you like, or play the set into your DAW in real time over MIDI, as [Playing Live](PLAYING_LIVE.md) describes. To hear a demo while watching it, open it in the tracker, which plays every example through FluidSynth as it comes: press `A` for Arrange, move to the top left corner, and press `Space`.

To make a WAV file of your own song, `Ctrl+X` in the tracker offers WAV (FluidSynth), which renders the tracks whose instrument plays through FluidSynth, as [Exporting](EXPORTING.md) describes.
